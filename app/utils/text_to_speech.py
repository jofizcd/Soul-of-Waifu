import os
import io
import re
import uuid
import queue
import time
import torch
import asyncio
import logging
import base64
import aiohttp
import edge_tts
import contextlib
import numpy as np
import soundfile as sf
import sounddevice as sd

from TTS.api import TTS
from kokoro import KPipeline
from pydub import AudioSegment
from elevenlabs.client import AsyncElevenLabs
from qwen_tts import Qwen3TTSModel

from PyQt6.QtCore import QThread, pyqtSignal

from app.configuration import configuration
from rvc_python.infer import RVCInference

import torch.serialization
try:
    from fairseq.data.dictionary import Dictionary
    torch.serialization.add_safe_globals([Dictionary])
except ImportError:
    pass

logger = logging.getLogger("Text-To-Speech Module")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "app", "models", "hf_cache")

os.environ["HF_HOME"] = CACHE_DIR
os.environ["HUGGINGFACE_HUB_CACHE"] = CACHE_DIR

os.makedirs(CACHE_DIR, exist_ok=True)

class ElevenLabs:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.audio_cache = AudioSegment.empty()
        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")
        self.output_dir = "app/voices/elevenlabs_audio"
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_speech_with_elevenlabs(self, text, voice_id):
        try:
            self.eleven_labs_api = self.configuration_api.get_token("ELEVENLABS_API_TOKEN")
            self.eleven = AsyncElevenLabs(api_key=self.eleven_labs_api)

            audio_stream = await self.eleven.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2",
                stream=True
            )
            audio_data = b""
            async for chunk in audio_stream:
                audio_data += chunk

            audio_stream_io = io.BytesIO(audio_data)
            new_audio = await asyncio.to_thread(AudioSegment.from_file, audio_stream_io, format="mp3")
            self.audio_cache += new_audio
            await self.play_audio(new_audio)
        except Exception as e:
            logger.error(f"Error: {e}")

    async def generate_speech_with_elevenlabs_sow_system(self, text, voice_id):
        try:
            self.eleven_labs_api = self.configuration_api.get_token("ELEVENLABS_API_TOKEN")
            self.eleven = AsyncElevenLabs(api_key=self.eleven_labs_api)

            audio_stream = await self.eleven.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2",
                stream=True
            )
            audio_data = b""
            async for chunk in audio_stream:
                audio_data += chunk

            audio_stream_io = io.BytesIO(audio_data)
            new_audio = await asyncio.to_thread(AudioSegment.from_file, audio_stream_io, format="mp3")

            unique_id = uuid.uuid4().hex
            output_file = os.path.join(self.output_dir, f"output_{unique_id}.wav")
            await asyncio.to_thread(new_audio.export, output_file, format="wav")
            return output_file
        except Exception as e:
            logger.error(f"ElevenLabs Error: {e}")
            return None

    async def play_audio(self, audio):
        try:
            samples = np.array(audio.get_array_of_samples())
            sample_rate = audio.frame_rate
            sd.default.device = self.device_index
            await asyncio.to_thread(sd.play, samples, samplerate=sample_rate)
            await asyncio.to_thread(sd.wait)
        except Exception as e:
            logger.error(f"Error: {e}")

    def clear_audio_cache(self):
        self.audio_cache = AudioSegment.empty()


class InworldTTS:
    def __init__(self):
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()
        self.output_dir = "app/voices/inworld_audio"
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_speech_with_inworld(self, text, character_name):
        api_key = self.configuration_api.get_token("INWORLD_API_TOKEN")
        character = self.configuration_characters.load_configuration()["character_list"][character_name]
        provider = self.configuration_settings.get_main_setting("tts_providers") or {}
        inworld = provider.get("Inworld", {})
        voice_id = character.get("inworld_voice_id") or inworld.get("default_voice_id", "Dennis")
        model_id = character.get("inworld_model_id") or inworld.get("default_model_id", "inworld-tts-2")
        voice_id = voice_id.strip()
        model_id = model_id.strip()

        if not api_key or not voice_id or not model_id:
            logger.error("Inworld TTS is not configured")
            return None

        payload = {
            "text": text,
            "voiceId": voice_id,
            "modelId": model_id,
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 22050},
        }
        headers = {"Authorization": f"Basic {api_key}", "Content-Type": "application/json"}

        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.inworld.ai/tts/v1/voice", json=payload, headers=headers) as response:
                    if response.status != 200:
                        logger.error("Inworld TTS request failed with status %s", response.status)
                        return None
                    data = await response.json()

            audio_content = data.get("audioContent") or data.get("result", {}).get("audioContent")
            if not audio_content:
                logger.error("Inworld TTS response has no audio content")
                return None

            output_file = os.path.join(self.output_dir, f"output_{uuid.uuid4().hex}.wav")
            audio_data = base64.b64decode(audio_content, validate=True)
            await asyncio.to_thread(self._write_audio, output_file, audio_data)
            return output_file
        except (aiohttp.ClientError, ValueError, OSError) as error:
            logger.error("Inworld TTS generation failed (%s)", type(error).__name__)
            return None

    @staticmethod
    def _write_audio(output_file, audio_data):
        with open(output_file, "wb") as audio_file:
            audio_file.write(audio_data)


class XTTSv2_SOW_System:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

    def _load_tts_sync(self):
        if not self.tts_loaded:
            try:
                self.tts = TTS(model_name='tts_models/multilingual/multi-dataset/xtts_v2', progress_bar=True).to(self.device)
                self.tts_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self, f0up_key, index_rate, protect):
        if not self.rvc_loaded:
            logger.info("Loading RVC model...")
            try:
                def _init():
                    return RVCInference(
                        models_dir="assets/rvc_models",
                        device="cuda:0" if torch.cuda.is_available() else "cpu:0",
                        f0up_key=f0up_key, index_rate=index_rate, protect=protect
                    )
                self.rvc = await asyncio.to_thread(_init)
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def generate_speech_with_xttsv2_sow_system(self, text=None, language=None, character_name=None):
        await asyncio.to_thread(self._load_tts_sync)

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][character_name]

        xttsv2_voice_type = char_config["voice_type"]
        xttsv2_rvc_enabled = char_config["rvc_enabled"]
        xttsv2_rvc_file = char_config["rvc_file"]

        speaker_wav_map = {
            "Female Calm": "app/voices/calm_female.wav",
            "Female": "app/voices/female.wav",
            "Male": "app/voices/male.wav"
        }
        speaker_wav = speaker_wav_map.get(xttsv2_voice_type)
        if not speaker_wav:
            raise ValueError(f"Unknown voice type: {xttsv2_voice_type}")

        os.makedirs("app/voices/xttsv2_audio", exist_ok=True)
        unique_id = uuid.uuid4().hex
        base_output_file = f"app/voices/xttsv2_audio/output_{unique_id}.wav"

        await asyncio.to_thread(
            self.tts.tts_to_file,
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=base_output_file
        )

        if xttsv2_rvc_enabled and xttsv2_rvc_file:
            f0up_key   = char_config.get("rvc_f0up_key",   0)
            index_rate = char_config.get("rvc_index_rate", 0.75)
            protect    = char_config.get("rvc_protect",    0.5)

            await self._load_rvc(f0up_key, index_rate, protect)

            model_name = os.path.splitext(os.path.basename(xttsv2_rvc_file))[0]
            rvc_output_file = f"app/voices/xttsv2_audio/output_rvc_{unique_id}.wav"

            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            try:
                await asyncio.to_thread(os.remove, base_output_file)
            except OSError as e:
                logger.warning(f"Could not remove temp file {base_output_file}: {e}")

            return rvc_output_file

        return base_output_file


class EdgeTTS:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.rvc = None
        self.rvc_loaded = False
        self.output_dir = "app/voices/edge_tts_audio"
        os.makedirs(self.output_dir, exist_ok=True)
        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    async def _load_rvc(self, f0up_key, index_rate, protect):
        if not self.rvc_loaded:
            logger.info("Loading RVC model...")
            try:
                def _init():
                    return RVCInference(
                        models_dir="assets/rvc_models",
                        device="cuda:0" if torch.cuda.is_available() else "cpu:0",
                        f0up_key=f0up_key, index_rate=index_rate, protect=protect
                    )
                self.rvc = await asyncio.to_thread(_init)
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def _convert_mp3_to_wav(self, mp3_file, wav_file):
        def _convert():
            audio = AudioSegment.from_mp3(mp3_file)
            audio.export(wav_file, format="wav")
        await asyncio.to_thread(_convert)

    async def _generate_base(self, text, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][character_name]

        voice_type = char_config["voice_type"]
        rvc_enabled = char_config["rvc_enabled"]
        rvc_file = char_config["rvc_file"]

        unique_id = uuid.uuid4().hex
        audio_file = os.path.join(self.output_dir, f"output_{unique_id}.mp3")
        wav_file = os.path.join(self.output_dir, f"output_{unique_id}.wav")

        try:
            communicate = edge_tts.Communicate(text, voice_type)
            await communicate.save(audio_file)
        except Exception as e:
            logger.error(f"Error when generating EdgeTTS audio: {e}")
            return None

        try:
            await self._convert_mp3_to_wav(audio_file, wav_file)
            await asyncio.to_thread(os.remove, audio_file)
        except Exception as e:
            logger.error(f"Error when converting MP3 to WAV: {e}")
            return None

        if rvc_enabled and rvc_file:
            f0up_key   = char_config.get("rvc_f0up_key",   0)
            index_rate = char_config.get("rvc_index_rate", 0.75)
            protect    = char_config.get("rvc_protect",    0.5)

            await self._load_rvc(f0up_key, index_rate, protect)
            model_name = os.path.splitext(os.path.basename(rvc_file))[0]
            rvc_output_file = os.path.join(self.output_dir, f"output_rvc_{unique_id}.wav")

            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(self.rvc.infer_file, wav_file, rvc_output_file)

            try:
                await asyncio.to_thread(os.remove, wav_file)
            except OSError as e:
                logger.warning(f"Could not remove temp file {wav_file}: {e}")

            return rvc_output_file

        return wav_file

    async def generate_speech_with_edge_tts(self, text, character_name):
        output_file = await self._generate_base(text, character_name)
        if output_file:
            await self.play_audio(file_path=output_file)

    async def generate_speech_with_edge_tts_sow_system(self, text, character_name):
        return await self._generate_base(text, character_name)

    async def play_audio(self, file_path):
        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')
                sd.default.device = self.device_index
                sd.play(data, samplerate)
                sd.wait()
            except Exception as e:
                logger.error(f"Error: {e}")
        await asyncio.to_thread(_play)

    def stop_audio(self):
        sd.stop()


class KokoroTTS_SOW_System:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

    async def _load_tts(self):
        if not self.tts_loaded:
            try:
                def _init():
                    return KPipeline(lang_code='a')
                self.pipeline = await asyncio.to_thread(_init)
                self.tts_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self, f0up_key, index_rate, protect):
        if not self.rvc_loaded:
            logger.info("Loading RVC model...")
            try:
                def _init():
                    return RVCInference(
                        models_dir="assets/rvc_models",
                        device="cuda:0" if torch.cuda.is_available() else "cpu:0",
                        f0up_key=f0up_key, index_rate=index_rate, protect=protect
                    )
                self.rvc = await asyncio.to_thread(_init)
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def generate_speech_with_kokoro(self, text, character_name):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][character_name]
        kokoro_voice_name = char_config["voice_type"]
        kokoro_rvc_enabled = char_config["rvc_enabled"]
        kokoro_rvc_file = char_config["rvc_file"]

        def _generate():
            generator = self.pipeline(text, voice=kokoro_voice_name)
            chunks = []
            for _, _, audio in generator:
                chunks.append(audio)
            return chunks

        all_audio = await asyncio.to_thread(_generate)

        if not all_audio:
            logger.warning("Kokoro generated empty audio for this chunk. Skipping.")
            return None

        full_audio = np.concatenate(all_audio)
        os.makedirs("app/voices/kokoro_audio", exist_ok=True)
        unique_id = uuid.uuid4().hex
        base_output_file = f"app/voices/kokoro_audio/kokoro_output_{unique_id}.wav"
        await asyncio.to_thread(sf.write, base_output_file, full_audio, 24000)

        if kokoro_rvc_enabled and kokoro_rvc_file:
            f0up_key   = char_config.get("rvc_f0up_key",   0)
            index_rate = char_config.get("rvc_index_rate", 0.75)
            protect    = char_config.get("rvc_protect",    0.5)

            await self._load_rvc(f0up_key, index_rate, protect)
            model_name = os.path.splitext(os.path.basename(kokoro_rvc_file))[0]
            rvc_output_file = f"app/voices/kokoro_audio/output_rvc_{unique_id}.wav"

            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            try:
                await asyncio.to_thread(os.remove, base_output_file)
            except OSError as e:
                logger.warning(f"Could not remove temp file {base_output_file}: {e}")

            return rvc_output_file

        return base_output_file


class SileroTTS_SOW_System:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

    async def _load_tts(self):
        if not self.tts_loaded:
            try:
                self.model, _ = await asyncio.to_thread(
                    torch.hub.load,
                    repo_or_dir='snakers4/silero-models',
                    model='silero_tts',
                    language='ru',
                    speaker='v5_3_ru',
                    trust_repo=True,
                    force_reload=False,
                    verbose=True
                )
                self.model.to(self.device)
                self.tts_loaded = True
                logger.info("Silero TTS loaded successfully")
            except Exception as e:
                raise RuntimeError(f"Failed to load Silero TTS: {e}")

    async def _load_rvc(self, f0up_key, index_rate, protect):
        if not self.rvc_loaded:
            logger.info("Loading RVC model...")
            try:
                def _init():
                    return RVCInference(
                        models_dir="assets/rvc_models",
                        device="cuda:0" if torch.cuda.is_available() else "cpu:0",
                        f0up_key=f0up_key, index_rate=index_rate, protect=protect
                    )
                self.rvc = await asyncio.to_thread(_init)
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def generate_speech_with_silero(self, text, character_name):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][character_name]

        silero_voice = char_config.get("voice_type", "xenia")
        silero_rvc_enabled = char_config.get("rvc_enabled", False)
        silero_rvc_file = char_config.get("rvc_file")

        os.makedirs("app/voices/silero_audio", exist_ok=True)
        unique_id = uuid.uuid4().hex
        base_output_file = f"app/voices/silero_audio/silero_output_{unique_id}.wav"

        audio = await asyncio.to_thread(
            self.model.apply_tts,
            text=text,
            speaker=silero_voice,
            sample_rate=48000
        )
        await asyncio.to_thread(sf.write, base_output_file, audio.cpu().numpy(), 48000)

        if silero_rvc_enabled and silero_rvc_file:
            f0up_key   = char_config.get("rvc_f0up_key",   0)
            index_rate = char_config.get("rvc_index_rate", 0.75)
            protect    = char_config.get("rvc_protect",    0.5)

            await self._load_rvc(f0up_key, index_rate, protect)
            model_name = os.path.splitext(os.path.basename(silero_rvc_file))[0]
            rvc_output_file = f"app/voices/silero_audio/output_rvc_{unique_id}.wav"

            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            try:
                await asyncio.to_thread(os.remove, base_output_file)
            except OSError as e:
                logger.warning(f"Could not remove temp file {base_output_file}: {e}")

            return rvc_output_file

        return base_output_file

class Qwen3TTS_SOW_System:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

    async def _load_tts(self, character_name: str):
        if not self.tts_loaded:
            try:
                configuration_data = self.configuration_characters.load_configuration()
                char_config = configuration_data["character_list"].get(character_name, {})

                model_size = char_config.get("qwen_model_size", "1.7B")
                qwen_mode = char_config.get("qwen_mode", "presets")
                qwen_device = char_config.get("qwen_device", "cpu")

                if qwen_device == "cuda" and torch.cuda.is_available():
                    self.device = "cuda"
                    target_dtype = torch.bfloat16
                    target_device_map = "auto"
                else:
                    self.device = "cpu"
                    target_dtype = torch.float32
                    target_device_map = None

                if qwen_mode == "prompt":
                    variant = "VoiceDesign"
                elif qwen_mode == "cloning":
                    variant = "Base"
                else:
                    variant = "CustomVoice"

                model_name = f"Qwen/Qwen3-TTS-12Hz-{model_size}-{variant}"

                def _init():
                    model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        dtype=target_dtype,
                        device_map=target_device_map,
                        attn_implementation="sdpa",
                    )
                    
                    if target_dtype == torch.float32:
                        def clean_and_cast_to_float32(obj, visited=None):
                            if visited is None:
                                visited = set()
                            
                            obj_id = id(obj)
                            if obj_id in visited:
                                return
                            visited.add(obj_id)

                            if isinstance(obj, torch.nn.Module):
                                if hasattr(obj, "_hf_hook"):
                                    try:
                                        delattr(obj, "_hf_hook")
                                    except Exception:
                                        pass
                                try:
                                    obj.to(torch.float32)
                                except Exception:
                                    pass
                                for child in obj.children():
                                    clean_and_cast_to_float32(child, visited)
                            
                            elif hasattr(obj, "__dict__"):
                                for attr_name, attr_val in list(obj.__dict__.items()):
                                    if attr_name.startswith("__"):
                                        continue
                                    clean_and_cast_to_float32(attr_val, visited)
                            
                            elif isinstance(obj, (list, tuple)):
                                for item in obj:
                                    clean_and_cast_to_float32(item, visited)
                                    
                            elif isinstance(obj, dict):
                                for value in obj.values():
                                    clean_and_cast_to_float32(value, visited)

                        clean_and_cast_to_float32(model)
                            
                    return model

                self.model = await asyncio.to_thread(_init)
                self.tts_loaded = True
                
                logger.info(f"Qwen3-TTS {model_size}-{variant} loaded on {self.device.upper()} for '{character_name}'")

            except Exception as e:
                logger.error(f"Failed to load Qwen3-TTS for {character_name}: {e}")
                raise RuntimeError(f"Failed to load Qwen3-TTS: {e}")

    async def _load_rvc(self, f0up_key, index_rate, protect):
        if not self.rvc_loaded:
            logger.info("Loading RVC model for Qwen 3...")
            try:
                def _init():
                    return RVCInference(
                        models_dir="assets/rvc_models",
                        device="cuda:0" if torch.cuda.is_available() else "cpu:0",
                        f0up_key=f0up_key, index_rate=index_rate, protect=protect
                    )
                self.rvc = await asyncio.to_thread(_init)
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def generate_speech_with_qwen3(self, text: str, character_name: str):
        await self._load_tts(character_name)

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][character_name]

        qwen_mode = char_config.get("qwen_mode", "presets")
        voice_type = char_config.get("voice_type", "Serena")
        qwen_prompt = char_config.get("qwen_prompt", "")
        qwen_instruct = char_config.get("qwen_style_instruct", "")
        qwen_ref_path = char_config.get("qwen_cloning_ref_path", "")
        language = char_config.get("qwen_language", "English")

        qwen_rvc_enabled = char_config.get("rvc_enabled", False)
        qwen_rvc_file = char_config.get("rvc_file")

        os.makedirs("app/voices/qwen_audio", exist_ok=True)
        unique_id = uuid.uuid4().hex
        base_output_file = f"app/voices/qwen_audio/qwen_output_{unique_id}.wav"

        def _generate():
            try:
                generation_params = {
                    "text": text,
                    "language": language,
                    "max_new_tokens": 1500,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }

                with torch.no_grad():
                    if self.device == "cpu":
                        autocast_ctx = torch.amp.autocast(device_type="cpu", enabled=False)
                    else:
                        autocast_ctx = contextlib.nullcontext()

                    with autocast_ctx:
                        if qwen_mode == "cloning" and qwen_ref_path and os.path.exists(qwen_ref_path):
                            # Voice Cloning
                            wavs, sr = self.model.generate_clone(
                                reference_audio=qwen_ref_path,
                                **generation_params
                            )

                        elif qwen_mode == "prompt" and qwen_prompt:
                            # Voice Design
                            wavs, sr = self.model.generate_voice_design(
                                instruct=qwen_prompt,
                                **generation_params
                            )

                        else:
                            # Preset Voices (CustomVoice)
                            wavs, sr = self.model.generate_custom_voice(
                                speaker=voice_type, instruct=qwen_instruct,
                                **generation_params
                            )

                audio_data = wavs[0]
                if isinstance(audio_data, torch.Tensor):
                    audio_data = audio_data.detach().cpu().to(torch.float32).numpy()
                elif isinstance(audio_data, np.ndarray):
                    audio_data = audio_data.astype(np.float32)

                sf.write(base_output_file, audio_data, sr)
                return base_output_file

            except Exception as e:
                logger.error(f"Qwen3 TTS generation error: {e}")
                raise

        await asyncio.to_thread(_generate)

        if qwen_rvc_enabled and qwen_rvc_file:
            f0up_key = char_config.get("rvc_f0up_key", 0)
            index_rate = char_config.get("rvc_index_rate", 0.75)
            protect = char_config.get("rvc_protect", 0.5)

            await self._load_rvc(f0up_key, index_rate, protect)

            model_name = os.path.splitext(os.path.basename(qwen_rvc_file))[0]
            rvc_output_file = f"app/voices/qwen_audio/output_rvc_{unique_id}.wav"

            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            try:
                os.remove(base_output_file)
            except OSError:
                pass

            return rvc_output_file

        return base_output_file

class AudioPlaybackWorker(QThread):
    queue_empty_signal = pyqtSignal()
    lipsync_signal = pyqtSignal(float)

    def __init__(self, device_index):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True
        self.device_index = device_index
        self.interrupt_flag = False

    def add_audio_file(self, file_path):
        self.interrupt_flag = False
        self.queue.put(file_path)

    def clear_queue(self):
        self.interrupt_flag = True
        with self.queue.mutex:
            for file_path in list(self.queue.queue):
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            self.queue.queue.clear()
        try:
            sd.stop()
        except Exception:
            pass

    def run(self):
        logger.info("Audio Playback Worker Started")
        while self.is_running:
            try:
                file_path = self.queue.get(timeout=0.1)

                if file_path is None:
                    self.queue.task_done()
                    continue

                if self.interrupt_flag:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                    self.queue.task_done()
                    continue

                try:
                    data, samplerate = sf.read(file_path, dtype='float32')
                    sd.default.device = self.device_index
                    sd.play(data, samplerate)

                    duration = len(data) / samplerate
                    chunk_size = int(samplerate * 0.05)
                    slept = 0

                    while slept < duration:
                        if self.interrupt_flag:
                            sd.stop()
                            self.lipsync_signal.emit(0.0)
                            break

                        start_idx = int(slept * samplerate)
                        end_idx = min(start_idx + chunk_size, len(data))
                        current_chunk = data[start_idx:end_idx]

                        if len(current_chunk) > 0:
                            rms = np.sqrt(np.mean(current_chunk ** 2))
                            mouth_open = min(rms * 5.0, 1.0)
                            self.lipsync_signal.emit(float(mouth_open))

                        time.sleep(0.05)
                        slept += 0.05

                    self.lipsync_signal.emit(0.0)

                except Exception as e:
                    logger.error(f"Playback error: {e}")
                finally:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass

                self.queue.task_done()

                if self.queue.empty() and not self.interrupt_flag:
                    self.queue_empty_signal.emit()

            except queue.Empty:
                continue

    def stop(self):
        self.is_running = False
        self.interrupt_flag = True
        try:
            sd.stop()
        except Exception:
            pass
        self.queue.put(None)
        self.quit()
        self.wait()


class TTSWorker(QThread):
    audio_ready_signal = pyqtSignal(str)

    def __init__(self, tts_method, character_name, voice_id=None, language="en"):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True
        self.discard_current = False

        self.tts_method = tts_method
        self.character_name = character_name
        self.voice_id = voice_id
        self.language = language

        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

        self.xtts = XTTSv2_SOW_System()
        self.edge = EdgeTTS()
        self.kokoro = KokoroTTS_SOW_System()
        self.silero = SileroTTS_SOW_System()
        self.qwen = Qwen3TTS_SOW_System()
        self.eleven = ElevenLabs()
        self.inworld = InworldTTS()

        self.playback_worker = AudioPlaybackWorker(self.device_index)
        self.playback_worker.start()

    def add_text(self, text):
        if not text:
            return
            
        clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|;|:)\s')
        raw_sentences = sentence_end.split(clean_text)
        
        current_chunk = ""
        max_chunk_len = 450 
        
        for sentence in raw_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(sentence) > max_chunk_len:
                if current_chunk:
                    self.queue.put(current_chunk)
                    current_chunk = ""
                
                sub_chunks = re.split(r'(?<=[,;])\s', sentence)
                for sub in sub_chunks:
                    sub = sub.strip()
                    if len(sub) > max_chunk_len:
                        for i in range(0, len(sub), max_chunk_len):
                            self.queue.put(sub[i:i+max_chunk_len])
                    else:
                        self.queue.put(sub)
            else:
                if len(current_chunk) + len(sentence) + 1 > max_chunk_len:
                    self.queue.put(current_chunk)
                    current_chunk = sentence
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
        
        if current_chunk:
            self.queue.put(current_chunk)

    def clear_queue(self):
        with self.queue.mutex:
            self.queue.queue.clear()
        self.discard_current = True
        if hasattr(self, 'playback_worker'):
            self.playback_worker.clear_queue()

    def run(self):
        logger.info(f"TTS Worker Started ({self.tts_method})")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            try:
                text = self.queue.get(timeout=0.5)

                if text is None:
                    self.queue.task_done()
                    continue

                if text:
                    self.discard_current = False
                    logger.info(f"Generating Audio for: {text[:30]}...")
                    output_file = None

                    if self.tts_method == "XTTSv2":
                        output_file = loop.run_until_complete(
                            self.xtts.generate_speech_with_xttsv2_sow_system(text, self.language, self.character_name)
                        )
                    elif self.tts_method == "Edge TTS":
                        output_file = loop.run_until_complete(
                            self.edge.generate_speech_with_edge_tts_sow_system(text, self.character_name)
                        )
                    elif self.tts_method == "Kokoro":
                        output_file = loop.run_until_complete(
                            self.kokoro.generate_speech_with_kokoro(text, self.character_name)
                        )
                    elif self.tts_method == "Silero":
                        output_file = loop.run_until_complete(
                            self.silero.generate_speech_with_silero(text, self.character_name)
                        )
                    elif self.tts_method == "Qwen-3 TTS":
                        output_file = loop.run_until_complete(
                            self.qwen.generate_speech_with_qwen3(text, self.character_name)
                        )
                    elif self.tts_method == "ElevenLabs":
                        output_file = loop.run_until_complete(
                            self.eleven.generate_speech_with_elevenlabs_sow_system(text, self.voice_id)
                        )
                    elif self.tts_method == "Inworld":
                        output_file = loop.run_until_complete(
                            self.inworld.generate_speech_with_inworld(text, self.character_name)
                        )

                    if self.discard_current:
                        logger.info("TTS finished, but was interrupted. Discarding audio.")
                        if output_file and os.path.exists(output_file):
                            try:
                                os.remove(output_file)
                            except Exception:
                                pass
                        self.queue.task_done()
                        continue

                    if output_file:
                        try:
                            import base64
                            with open(output_file, "rb") as f:
                                b64_audio = base64.b64encode(f.read()).decode("utf-8")
                            self.audio_ready_signal.emit(b64_audio)
                        except Exception as e:
                            logger.error(f"Error encoding audio for web client: {e}")
                        
                        self.playback_worker.add_audio_file(output_file)

                    self.queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS Error: {e}")

    def stop(self):
        self.is_running = False
        self.discard_current = True
        self.queue.put(None)
        if hasattr(self, 'playback_worker'):
            self.playback_worker.stop()
        self.quit()
        self.wait()
