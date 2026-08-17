import os
import io
import re
import uuid
import queue
import time
import shutil
import torch
import asyncio
import logging
import edge_tts
import threading
import contextlib
import numpy as np
import soundfile as sf
import sounddevice as sd
from typing import Optional

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

def fix_rvc_sample_rate(file_path, base_file_path=None, target_sr=48000):
    if not file_path or not os.path.exists(file_path):
        return file_path
    try:
        data, sr = sf.read(file_path, dtype='float32')

        if sr != target_sr:
            if base_file_path and os.path.exists(base_file_path):
                data_base, sr_base = sf.read(base_file_path, dtype='float32')
                dur_base = len(data_base) / sr_base
                if dur_base > 0:
                    target_sr = int(round(len(data) / dur_base))

            sf.write(file_path, data, target_sr)
            logger.info(f"[RVC Fix] Corrected header from {sr} Hz to {target_sr} Hz")
    except Exception as e:
        logger.warning(f"Failed to fix RVC sample rate: {e}")
    return file_path

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

            rvc_params = (model_name, f0up_key, index_rate, protect)
            if getattr(self, "_current_rvc_params", None) != rvc_params:
                await asyncio.to_thread(self.rvc.load_model, model_name)
                self._current_rvc_params = rvc_params

            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            fix_rvc_sample_rate(rvc_output_file, base_output_file)

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

            rvc_params = (model_name, f0up_key, index_rate, protect)
            if getattr(self, "_current_rvc_params", None) != rvc_params:
                await asyncio.to_thread(self.rvc.load_model, model_name)
                self._current_rvc_params = rvc_params

            await asyncio.to_thread(self.rvc.infer_file, wav_file, rvc_output_file)

            fix_rvc_sample_rate(rvc_output_file, wav_file)

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

            rvc_params = (model_name, f0up_key, index_rate, protect)
            if getattr(self, "_current_rvc_params", None) != rvc_params:
                await asyncio.to_thread(self.rvc.load_model, model_name)
                self._current_rvc_params = rvc_params

            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            fix_rvc_sample_rate(rvc_output_file, base_output_file)

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

            rvc_params = (model_name, f0up_key, index_rate, protect)
            if getattr(self, "_current_rvc_params", None) != rvc_params:
                await asyncio.to_thread(self.rvc.load_model, model_name)
                self._current_rvc_params = rvc_params
            
            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            fix_rvc_sample_rate(rvc_output_file, base_output_file)

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

                if variant == "VoiceDesign" and model_size != "1.7B":
                    logger.warning(
                        f"Qwen3-TTS: VoiceDesign is only available as 1.7B, "
                        f"got model_size='{model_size}'. Falling back to 1.7B."
                    )
                    model_size = "1.7B"

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
        qwen_ref_text = char_config.get("qwen_cloning_ref_text", "")
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
                            if qwen_ref_text:
                                wavs, sr = self.model.generate_voice_clone(
                                    ref_audio=qwen_ref_path,
                                    ref_text=qwen_ref_text,
                                    **generation_params
                                )
                            else:
                                logger.warning(
                                    f"Qwen3-TTS: no 'qwen_cloning_ref_text' set for "
                                    f"'{character_name}'; using x_vector_only_mode "
                                    f"(cloning quality may be reduced)."
                                )
                                wavs, sr = self.model.generate_voice_clone(
                                    ref_audio=qwen_ref_path,
                                    x_vector_only_mode=True,
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

            rvc_params = (model_name, f0up_key, index_rate, protect)
            if getattr(self, "_current_rvc_params", None) != rvc_params:
                await asyncio.to_thread(self.rvc.load_model, model_name)
                self._current_rvc_params = rvc_params

            await asyncio.to_thread(self.rvc.infer_file, base_output_file, rvc_output_file)

            fix_rvc_sample_rate(rvc_output_file, base_output_file)

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

    def add_audio_file(self, file_path, persist=False):
        self.interrupt_flag = False
        self.queue.put((file_path, persist))

    def clear_queue(self):
        self.interrupt_flag = True
        with self.queue.mutex:
            for item in list(self.queue.queue):
                file_path, persist = item if isinstance(item, tuple) else (item, False)
                if persist:
                    continue
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            self.queue.queue.clear()

    def run(self):
        logger.info("Audio Playback Worker Started")
        while self.is_running:
            try:
                item = self.queue.get(timeout=0.1)

                if item is None:
                    self.queue.task_done()
                    continue

                file_path, persist = item if isinstance(item, tuple) else (item, False)

                if self.interrupt_flag:
                    if not persist:
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
                    if not persist:
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
    segment_saved_signal = pyqtSignal(str, str)

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

        self.tts_mode = self.configuration_settings.get_main_setting("tts_voicing_mode") or 0
        self.tts_custom_regex = self.configuration_settings.get_main_setting("tts_custom_regex") or ""

        self._in_tts_quote = False
        self._in_asterisk = False

        self.xtts = XTTSv2_SOW_System()
        self.edge = EdgeTTS()
        self.kokoro = KokoroTTS_SOW_System()
        self.silero = SileroTTS_SOW_System()
        self.qwen = Qwen3TTS_SOW_System()
        self.eleven = ElevenLabs()

        self.playback_worker = AudioPlaybackWorker(self.device_index)
        self.playback_worker.start()

    def add_text(self, text, message_id=None):
        if not text:
            return
            
        text = self.clean_text_for_speech(text)
        if not text:
            return

        raw_sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        max_chunk_len = 450 
        
        def _enqueue(chunk_text):
            if chunk_text:
                self.queue.put((chunk_text, message_id))

        for sentence in raw_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(sentence) > max_chunk_len:
                if current_chunk:
                    _enqueue(current_chunk)
                    current_chunk = ""
                
                sub_chunks = re.split(r'(?<=[,;])\s', sentence)
                for sub in sub_chunks:
                    sub = sub.strip()
                    if len(sub) > max_chunk_len:
                        for i in range(0, len(sub), max_chunk_len):
                            _enqueue(sub[i:i+max_chunk_len])
                    else:
                        _enqueue(sub)
            else:
                if len(current_chunk) + len(sentence) + 1 > max_chunk_len:
                    _enqueue(current_chunk)
                    current_chunk = sentence
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
        
        if current_chunk:
            _enqueue(current_chunk)

    def _persist_segment_for_replay(self, source_file, message_id):
        if not source_file or not os.path.exists(source_file):
            return None

        segment_dir = os.path.join(
            os.getcwd(), "app", "data", ".soul", self.character_name, "tts_audio", message_id
        )
        os.makedirs(segment_dir, exist_ok=True)

        existing = [f for f in os.listdir(segment_dir) if f.lower().endswith((".wav", ".mp3"))]
        next_index = len(existing) + 1
        ext = os.path.splitext(source_file)[1] or ".wav"
        segment_filename = f"seg_{next_index:04d}{ext}"
        destination = os.path.join(segment_dir, segment_filename)

        shutil.copyfile(source_file, destination)

        return f"tts_audio/{message_id}/{segment_filename}"

    def clean_text_for_speech(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        mode = self.tts_mode
        regex = self.tts_custom_regex

        # --- Mode 0: Voice Everything ---
        if mode == 0:
            return re.sub(r"[*_~`#]", "", text).strip()

        # --- Mode 1: Voice Only Quotes ---
        elif mode == 1:
            result = []
            parts = re.split(r'(["“”«»])', text)
            for part in parts:
                if part in ('"', "“", "”", "«", "»"):
                    self._in_tts_quote = not self._in_tts_quote
                    if not self._in_tts_quote:
                        result.append(" ")
                    continue
                if self._in_tts_quote:
                    result.append(part)
            return re.sub(r"[*_~`#]", "", "".join(result)).strip()

        # --- Mode 2: Ignore Asterisks ---
        elif mode == 2:
            result = []
            parts = re.split(r"(\*|_)", text)
            for part in parts:
                if part in ("*", "_"):
                    self._in_asterisk = not self._in_asterisk
                    if not self._in_asterisk:
                        result.append(" ")
                    continue
                if not self._in_asterisk:
                    result.append(part)
            return re.sub(r"[*_~`#]", "", "".join(result)).strip()

        # --- Mode 3: Voice Outside Quotes ---
        elif mode == 3:
            result = []
            parts = re.split(r'(["“”«»])', text)
            for part in parts:
                if part in ('"', "“", "”", "«", "»"):
                    if part in ("“", "«"):
                        self._in_tts_quote = True
                    elif part in ("”", "»"):
                        self._in_tts_quote = False
                    else:
                        self._in_tts_quote = not self._in_tts_quote

                    if not self._in_tts_quote:
                        result.append(" ")
                    continue

                if not self._in_tts_quote:
                    result.append(part)

            return re.sub(r"[*_~`#]", "", "".join(result)).strip()

        # --- Mode 4: Custom Regex ---
        elif mode == 4:
            if not regex:
                return re.sub(r"[*_~`#]", "", text).strip()
            try:
                matches = re.findall(regex, text)
                if matches:
                    extracted = []
                    for m in matches:
                        if isinstance(m, tuple):
                            val = next((g for g in m if g), "")
                            extracted.append(val)
                        else:
                            extracted.append(m)
                    return " ".join(extracted).strip()
                return ""
            except re.error:
                return re.sub(r"[*_~`#]", "", text).strip()

        return text.strip()
    
    def clear_queue(self):
        with self.queue.mutex:
            self.queue.queue.clear()
        self.discard_current = True
        self._in_tts_quote = False
        self._in_asterisk = False
        if hasattr(self, 'playback_worker'):
            self.playback_worker.clear_queue()

    def run(self):
        logger.info(f"TTS Worker Started ({self.tts_method})")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            try:
                item = self.queue.get(timeout=0.5)

                if item is None:
                    self.queue.task_done()
                    continue

                text, message_id = item if isinstance(item, tuple) else (item, None)

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
                        
                        if message_id:
                            try:
                                relative_path = self._persist_segment_for_replay(output_file, message_id)
                                if relative_path:
                                    self.segment_saved_signal.emit(message_id, relative_path)
                            except Exception as e:
                                logger.error(f"Failed to persist TTS segment for replay: {e}")

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

class _AudioChunk:
    __slots__ = ("file_path", "text", "message_id", "persist", "is_poison")

    def __init__(self, file_path: Optional[str] = None, text: str = "",
                 message_id: Optional[str] = None, persist: bool = False,
                 is_poison: bool = False):
        self.file_path = file_path
        self.text = text
        self.message_id = message_id
        self.persist = persist
        self.is_poison = is_poison

class PipelinedTTSWorker(QThread):
    audio_ready_signal = pyqtSignal(str)
    segment_saved_signal = pyqtSignal(str, str)
    lipsync_signal = pyqtSignal(float)
    queue_empty_signal = pyqtSignal()

    AUDIO_BUFFER_SIZE = 2
    LIPSYNC_POLL_SEC = 0.05
    TTS_TIMEOUT_SEC = 30

    def __init__(self, tts_method, character_name, voice_id=None, language="en"):
        super().__init__()

        self.text_queue = queue.Queue()

        self.is_running = True
        self.discard_current = False
        self._interrupt_flag = threading.Event()

        self.tts_method = tts_method
        self.character_name = character_name
        self.voice_id = voice_id
        self.language = language

        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

        self.tts_mode = self.configuration_settings.get_main_setting("tts_voicing_mode") or 0
        self.tts_custom_regex = self.configuration_settings.get_main_setting("tts_custom_regex") or ""

        self._in_tts_quote = False
        self._in_asterisk = False

        self._tts_engines_initialized = False
        self.xtts = None
        self.edge = None
        self.kokoro = None
        self.silero = None
        self.qwen = None
        self.eleven = None

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._audio_buffer: Optional[asyncio.Queue] = None
        self._producer_task: Optional[asyncio.Task] = None
        self._player_task: Optional[asyncio.Task] = None

    def _ensure_tts_engines(self):
        if self._tts_engines_initialized:
            return
        from app.utils.text_to_speech import (
            XTTSv2_SOW_System, EdgeTTS, KokoroTTS_SOW_System,
            SileroTTS_SOW_System, Qwen3TTS_SOW_System, ElevenLabs
        )
        self.xtts = XTTSv2_SOW_System()
        self.edge = EdgeTTS()
        self.kokoro = KokoroTTS_SOW_System()
        self.silero = SileroTTS_SOW_System()
        self.qwen = Qwen3TTS_SOW_System()
        self.eleven = ElevenLabs()
        self._tts_engines_initialized = True
        logger.info(f"[PipelinedTTS] engines initialized for method='{self.tts_method}'")

    def add_text(self, text, message_id=None):
        if not text:
            return

        self.discard_current = False
        self._interrupt_flag.clear()

        text = self.clean_text_for_speech(text)
        if not text:
            return

        raw_sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        max_chunk_len = 450

        def _enqueue(chunk_text):
            if chunk_text:
                self.text_queue.put((chunk_text, message_id))

        for sentence in raw_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) > max_chunk_len:
                if current_chunk:
                    _enqueue(current_chunk)
                    current_chunk = ""
                sub_chunks = re.split(r'(?<=[,;])\s', sentence)
                for sub in sub_chunks:
                    sub = sub.strip()
                    if len(sub) > max_chunk_len:
                        for i in range(0, len(sub), max_chunk_len):
                            _enqueue(sub[i:i+max_chunk_len])
                    else:
                        _enqueue(sub)
            else:
                if len(current_chunk) + len(sentence) + 1 > max_chunk_len:
                    _enqueue(current_chunk)
                    current_chunk = sentence
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence

        if current_chunk:
            _enqueue(current_chunk)

    def clean_text_for_speech(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        mode = self.tts_mode
        regex = self.tts_custom_regex

        # --- Mode 0: Voice Everything ---
        if mode == 0:
            return re.sub(r"[*_~`#]", "", text).strip()

        # --- Mode 1: Voice Only Quotes ---
        elif mode == 1:
            result = []
            parts = re.split(r'(["“”«»])', text)
            for part in parts:
                if part in ('"', "“", "”", "«", "»"):
                    self._in_tts_quote = not self._in_tts_quote
                    if not self._in_tts_quote:
                        result.append(" ")
                    continue
                if self._in_tts_quote:
                    result.append(part)
            
            cleaned = re.sub(r"[*_~`#]", "", "".join(result)).strip()

            if not cleaned and not any(q in text for q in ('"', "“", "”", "«", "»")):
                no_actions = re.sub(r"\*[^*]+\*", "", text)
                no_actions = re.sub(r"_[^_]+_", "", no_actions)
                cleaned = re.sub(r"[*_~`#]", "", no_actions).strip()

            return cleaned

        # --- Mode 2: Ignore Asterisks ---
        elif mode == 2:
            result = []
            parts = re.split(r"(\*|_)", text)
            for part in parts:
                if part in ("*", "_"):
                    self._in_asterisk = not self._in_asterisk
                    if not self._in_asterisk:
                        result.append(" ")
                    continue
                if not self._in_asterisk:
                    result.append(part)
            return re.sub(r"[*_~`#]", "", "".join(result)).strip()

        # --- Mode 3: Voice Outside Quotes ---
        elif mode == 3:
            result = []
            parts = re.split(r'(["“”«»])', text)
            for part in parts:
                if part in ('"', "“", "”", "«", "»"):
                    if part in ("“", "«"):
                        self._in_tts_quote = True
                    elif part in ("”", "»"):
                        self._in_tts_quote = False
                    else:
                        self._in_tts_quote = not self._in_tts_quote

                    if not self._in_tts_quote:
                        result.append(" ")
                    continue

                if not self._in_tts_quote:
                    result.append(part)

            return re.sub(r"[*_~`#]", "", "".join(result)).strip()

        # --- Mode 4: Custom Regex ---
        elif mode == 4:
            if not regex:
                return re.sub(r"[*_~`#]", "", text).strip()
            try:
                matches = re.findall(regex, text)
                if matches:
                    extracted = []
                    for m in matches:
                        if isinstance(m, tuple):
                            val = next((g for g in m if g), "")
                            extracted.append(val)
                        else:
                            extracted.append(m)
                    return " ".join(extracted).strip()
                return ""
            except re.error:
                return re.sub(r"[*_~`#]", "", text).strip()

        return text.strip()

    def clear_queue(self):
        with self.text_queue.mutex:
            self.text_queue.queue.clear()
        self.discard_current = True
        self._interrupt_flag.set()
        self._in_tts_quote = False
        self._in_asterisk = False
        if self._loop and self._audio_buffer and self._loop.is_running():
            def _drain():
                while not self._audio_buffer.empty():
                    try:
                        self._audio_buffer.get_nowait()
                    except asyncio.QueueEmpty:
                        break
            self._loop.call_soon_threadsafe(_drain)
        try:
            self.lipsync_signal.emit(0.0)
        except Exception:
            pass
        logger.info("[PipelinedTTS] queue cleared, playback interrupted")

    def stop(self):
        self.is_running = False
        self.discard_current = True
        self._interrupt_flag.set()
        self.text_queue.put(None)

        if self._loop and self._loop.is_running():
            for task in (self._producer_task, self._player_task):
                if task and not task.done():
                    self._loop.call_soon_threadsafe(task.cancel)

        try:
            sd.stop()
        except Exception:
            pass

        self.quit()
        self.wait()
        logger.info("[PipelinedTTS] worker stopped")

    def run(self):
        logger.info(f"PipelinedTTSWorker started (method={self.tts_method}, "
                    f"buffer={self.AUDIO_BUFFER_SIZE})")

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._audio_buffer = asyncio.Queue(maxsize=self.AUDIO_BUFFER_SIZE)

        self.discard_current = False
        self._interrupt_flag.clear()

        self._producer_task = self._loop.create_task(self._producer_loop())
        self._player_task = self._loop.create_task(self._player_loop())

        try:
            self._loop.run_until_complete(
                asyncio.gather(self._producer_task, self._player_task,
                               return_exceptions=True)
            )
        except Exception as e:
            logger.error(f"[PipelinedTTS] run() error: {e}", exc_info=True)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            logger.info("[PipelinedTTS] run() exited")

    async def _producer_loop(self):
        logger.info("[PipelinedTTS] producer loop started")

        while self.is_running:
            try:
                item = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.text_queue.get(timeout=0.5)
                )
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[PipelinedTTS] producer get error: {e}")
                continue

            if item is None:

                logger.info("[PipelinedTTS] producer received poison pill")
                await self._audio_buffer.put(_AudioChunk(is_poison=True))
                break

            text, message_id = item
            if not text:
                continue

            self.discard_current = False
            self._interrupt_flag.clear()

            logger.info(f"[PipelinedTTS] producer: generating '{text[:40]}...'")

            try:
                self._ensure_tts_engines()
            except Exception as e:
                logger.error(f"[PipelinedTTS] engine init failed: {e}")
                continue

            output_file = None
            try:
                output_file = await asyncio.wait_for(
                    self._generate_wav(text),
                    timeout=self.TTS_TIMEOUT_SEC
                )
            except asyncio.TimeoutError:
                logger.error(f"[PipelinedTTS] TTS timed out for: '{text[:40]}...'")
                continue
            except asyncio.CancelledError:
                logger.info("[PipelinedTTS] producer cancelled")
                break
            except Exception as e:
                logger.error(f"[PipelinedTTS] TTS generation error: {e}", exc_info=True)
                continue

            if self.discard_current:
                logger.info(f"[PipelinedTTS] producer: discarding '{text[:40]}...' (interrupted)")
                if output_file and os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except Exception:
                        pass
                continue

            if not output_file or not os.path.exists(output_file):
                logger.warning(f"[PipelinedTTS] producer: no output file for '{text[:40]}...'")
                continue

            try:
                import base64
                b64_audio = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: base64.b64encode(open(output_file, "rb").read()).decode("utf-8")
                )
                self.audio_ready_signal.emit(b64_audio)
            except Exception as e:
                logger.error(f"[PipelinedTTS] base64 encoding error: {e}")

            if message_id:
                try:
                    relative_path = await asyncio.get_event_loop().run_in_executor(
                        None, self._persist_segment_for_replay, output_file, message_id
                    )
                    if relative_path:
                        self.segment_saved_signal.emit(message_id, relative_path)
                except Exception as e:
                    logger.error(f"[PipelinedTTS] persist error: {e}")

            chunk = _AudioChunk(
                file_path=output_file,
                text=text,
                message_id=message_id,
                persist=False,
            )
            try:
                await self._audio_buffer.put(chunk)
                logger.info(f"[PipelinedTTS] producer: enqueued '{text[:40]}...' "
                            f"(buffer now has {self._audio_buffer.qsize() + 1} items)")
            except asyncio.CancelledError:
                try:
                    if output_file and os.path.exists(output_file):
                        os.remove(output_file)
                except Exception:
                    pass
                break

        logger.info("[PipelinedTTS] producer loop ended")

    async def _player_loop(self):
        logger.info("[PipelinedTTS] player loop started")

        while self.is_running:
            try:
                chunk = await self._audio_buffer.get()
            except asyncio.CancelledError:
                logger.info("[PipelinedTTS] player cancelled")
                break
            except Exception as e:
                logger.error(f"[PipelinedTTS] player get error: {e}")
                continue

            if chunk is None or chunk.is_poison:
                logger.info("[PipelinedTTS] player received poison pill")
                break

            if not chunk.file_path or not os.path.exists(chunk.file_path):
                logger.warning(f"[PipelinedTTS] player: missing file '{chunk.file_path}'")
                continue

            if self._interrupt_flag.is_set():
                logger.info(f"[PipelinedTTS] player: skipping '{chunk.text[:40]}...' (interrupted)")
                try:
                    if not chunk.persist and os.path.exists(chunk.file_path):
                        os.remove(chunk.file_path)
                except Exception:
                    pass
                continue

            logger.info(f"[PipelinedTTS] player: playing '{chunk.text[:40]}...'")
            await self._play_audio_with_lipsync(chunk.file_path, chunk.persist)

            if self._audio_buffer.empty() and self.text_queue.empty() and not self._interrupt_flag.is_set():
                try:
                    self.queue_empty_signal.emit()
                except Exception:
                    pass

        try:
            self.lipsync_signal.emit(0.0)
        except Exception:
            pass

        logger.info("[PipelinedTTS] player loop ended")

    async def _play_audio_with_lipsync(self, file_path: str, persist: bool):
        try:
            data, samplerate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sf.read(file_path, dtype='float32')
            )
        except Exception as e:
            logger.error(f"[PipelinedTTS] read error: {e}")
            try:
                if not persist and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return

        if data is None or len(data) == 0:
            logger.warning(f"[PipelinedTTS] empty audio data for '{file_path}'")
            try:
                if not persist and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return

        try:
            sd.play(data, samplerate, device=self.device_index)
        except Exception as e:
            logger.error(f"[PipelinedTTS] sd.play error: {e}")
            try:
                if not persist and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return

        duration = len(data) / samplerate
        chunk_size = max(1, int(samplerate * self.LIPSYNC_POLL_SEC))
        total_samples = len(data)

        is_stereo = data.ndim > 1
        if is_stereo:
            data_mono = data.mean(axis=1)
        else:
            data_mono = data

        slept = 0.0
        sample_idx = 0
        try:
            while slept < duration:
                if self._interrupt_flag.is_set():
                    sd.stop()
                    self.lipsync_signal.emit(0.0)
                    logger.info(f"[PipelinedTTS] player: interrupted at {slept:.2f}/{duration:.2f}s")
                    break

                end_idx = min(sample_idx + chunk_size, total_samples)
                current_chunk = data_mono[sample_idx:end_idx]
                if len(current_chunk) > 0:
                    rms = float(np.sqrt(np.mean(current_chunk ** 2)))
                    mouth_open = min(rms * 5.0, 1.0)
                    try:
                        self.lipsync_signal.emit(mouth_open)
                    except Exception:
                        pass

                await asyncio.sleep(self.LIPSYNC_POLL_SEC)
                slept += self.LIPSYNC_POLL_SEC
                sample_idx += chunk_size

        except asyncio.CancelledError:
            sd.stop()
            try:
                self.lipsync_signal.emit(0.0)
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error(f"[PipelinedTTS] lipsync loop error: {e}")
        finally:

            try:
                self.lipsync_signal.emit(0.0)
            except Exception:
                pass

            if not self._interrupt_flag.is_set():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, sd.wait)
                except Exception:
                    pass

            try:
                if not persist and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    async def _generate_wav(self, text: str) -> Optional[str]:
        method = self.tts_method
        if method == "XTTSv2":
            return await self.xtts.generate_speech_with_xttsv2_sow_system(
                text, self.language, self.character_name)
        elif method == "Edge TTS":
            return await self.edge.generate_speech_with_edge_tts_sow_system(
                text, self.character_name)
        elif method == "Kokoro":
            return await self.kokoro.generate_speech_with_kokoro(
                text, self.character_name)
        elif method == "Silero":
            return await self.silero.generate_speech_with_silero(
                text, self.character_name)
        elif method == "Qwen-3 TTS":
            return await self.qwen.generate_speech_with_qwen3(
                text, self.character_name)
        elif method == "ElevenLabs":
            return await self.eleven.generate_speech_with_elevenlabs_sow_system(
                text, self.voice_id)
        else:
            logger.error(f"[PipelinedTTS] unknown TTS method: {method}")
            return None

    def _persist_segment_for_replay(self, source_file, message_id):
        if not source_file or not os.path.exists(source_file):
            return None

        segment_dir = os.path.join(
            os.getcwd(), "app", "data", ".soul",
            self.character_name, "tts_audio", message_id
        )
        os.makedirs(segment_dir, exist_ok=True)

        existing = [f for f in os.listdir(segment_dir)
                    if f.lower().endswith((".wav", ".mp3"))]
        next_index = len(existing) + 1
        ext = os.path.splitext(source_file)[1] or ".wav"
        segment_filename = f"seg_{next_index:04d}{ext}"
        destination = os.path.join(segment_dir, segment_filename)

        shutil.copyfile(source_file, destination)
        return f"tts_audio/{message_id}/{segment_filename}"
