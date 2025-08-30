import os
import io
import torch
import asyncio
import logging
import edge_tts
import numpy as np
import soundfile as sf
import sounddevice as sd

from TTS.api import TTS
from kokoro import KPipeline
from pydub import AudioSegment
from IPython.display import display, Audio
from elevenlabs.client import AsyncElevenLabs

from PyQt6.QtCore import QThread, pyqtSignal

from app.configuration import configuration
from rvc_python.infer import RVCInference

logger = logging.getLogger("Text-To-Speech Module")

class ElevenLabs:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.audio_cache = AudioSegment.empty()

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    async def generate_speech_with_elevenlabs(self, text, voice_id):
        """
        Asynchronous function for speech generation via ElevenLabs.
        """
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

class XTTSv2(QThread):
    started = pyqtSignal()
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    audio_played = pyqtSignal(str)

    def __init__(self, text=None, language=None, character_name=None, ui=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.language = language
        self.character_name = character_name

        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

        self.ui = ui

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    def run(self):
        self.started.emit()
        try:
            asyncio.run(self.generate_speech_with_xttsv2())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    async def _load_tts(self):
        if not self.tts_loaded:
            if self.ui != None:
                self.ui.loading_model_label.show()
                self.ui.loading_model_label.setText("Loading XTTSv2 model...")
            try:
                self.tts = TTS(model_name='tts_models/multilingual/multi-dataset/xtts_v2', progress_bar=True).to(self.device)
                self.tts_loaded = True
                if self.ui != None:
                    self.ui.loading_model_label.setText("TTS model loaded successfully!")
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self):
        if not self.rvc_loaded:
            if self.ui != None:
                self.ui.loading_model_label.show()
                self.ui.loading_model_label.setText("Loading RVC model...")
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0", f0up_key=1, index_rate=0.8, protect=0.7)
                self.rvc_loaded = True
                if self.ui != None:
                    self.ui.loading_model_label.setText("RVC model loaded successfully!")
            except Exception as e:
                raise RuntimeError(f"Failed to load RVC model: {e}")

    async def generate_speech_with_xttsv2(self):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"][self.character_name]

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

        if self.ui != None:
            self.ui.loading_model_label.setText("Generating audiofile...")

        await asyncio.to_thread(
            self.tts.tts_to_file,
            text=self.text,
            speaker_wav=speaker_wav,
            language=self.language,
            file_path="app/voices/xttsv2_audio/output.wav"
        )

        output_file = "app/voices/xttsv2_audio/output.wav"

        if xttsv2_rvc_enabled:
            await self._load_rvc()
            model_name = os.path.splitext(os.path.basename(xttsv2_rvc_file))[0]
            available_models = self.rvc.list_models()

            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")

            if self.ui != None:
                self.ui.loading_model_label.setText("Proccesing via RVC model...")
            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(
                self.rvc.infer_file,
                "app/voices/xttsv2_audio/output.wav",
                "app/voices/xttsv2_audio/output_rvc.wav"
            )
            output_file = "app/voices/xttsv2_audio/output_rvc.wav"

        if self.ui != None:
            self.ui.loading_model_label.setText("Audio is ready!")
        await self.play_audio(output_file)
        self.audio_played.emit(output_file)

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')
                sd.default.device = self.device_index
                sd.play(data, samplerate)
                sd.wait()
                if self.ui != None:
                    self.ui.loading_model_label.hide()
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                raise RuntimeError(f"Audio playback failed: {e}")

        await loop.run_in_executor(None, _play)
    
    def stop_audio(self):
        if self.ui != None:
            self.ui.loading_model_label.hide()
        sd.stop()

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

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    async def _load_tts(self):
        if not self.tts_loaded:
            try:
                self.tts = TTS(model_name='tts_models/multilingual/multi-dataset/xtts_v2', progress_bar=True).to(self.device)
                self.tts_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self):
        if not self.rvc_loaded:
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0", f0up_key=1, index_rate=0.8, protect=0.7)
                self.rvc_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load RVC model: {e}")

    async def generate_speech_with_xttsv2_sow_system(self, text=None, language=None, character_name=None,):
        await asyncio.to_thread(self._load_tts)

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

        await asyncio.to_thread(
            self.tts.tts_to_file,
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path="app/voices/xttsv2_audio/output.wav"
        )

        output_file = "app/voices/xttsv2_audio/output.wav"

        if xttsv2_rvc_enabled:
            await asyncio.to_thread(self._load_rvc)
            model_name = os.path.splitext(os.path.basename(xttsv2_rvc_file))[0]
            available_models = self.rvc.list_models()

            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")
            
            await asyncio.to_thread(self.rvc.load_model, model_name)
            await asyncio.to_thread(
                self.rvc.infer_file,
                "app/voices/xttsv2_audio/output.wav",
                "app/voices/xttsv2_audio/output_rvc.wav"
            )
            output_file = "app/voices/xttsv2_audio/output_rvc.wav"

        await self.play_audio(output_file)
        self.audio_played.emit(output_file)

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')
                sd.default.device = self.device_index
                sd.play(data, samplerate)
                sd.wait()
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                raise RuntimeError(f"Audio playback failed: {e}")

        await loop.run_in_executor(None, _play)
    
    def stop_audio(self):
        sd.stop()

class EdgeTTS:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.rvc = None
        self.rvc_loaded = False

        self.output_dir = "app\\voices\\edge_tts_audio"

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    async def _load_rvc(self):
        if not self.rvc_loaded:
            logger.info("Loading RVC model...")
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0")
                self.rvc_loaded = True
                logger.info("RVC model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')

                sd.default.device = self.device_index

                sd.play(data, samplerate)
                sd.wait()
            except Exception as e:
                logger.error(f"Error: {e}")

        await loop.run_in_executor(None, _play)
    
    def stop_audio(self):
        sd.stop()

    async def convert_mp3_to_wav(self, mp3_file, wav_file):
        audio = AudioSegment.from_mp3(mp3_file)
        audio.export(wav_file, format="wav")
        logger.info(f"The audio file has been successfully converted: {wav_file}")

    async def generate_speech_with_edge_tts(self, text, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        
        voice_type = configuration_data["character_list"][character_name]["voice_type"]
        rvc_enabled = configuration_data["character_list"][character_name]["rvc_enabled"]
        rvc_file = configuration_data["character_list"][character_name]["rvc_file"]

        audio_file = os.path.join(self.output_dir, "output.mp3")
        wav_file = os.path.join(self.output_dir, "output.wav")
        
        try:
            communicate = edge_tts.Communicate(text, voice_type)
            await communicate.save(audio_file)
            logger.info(f"The audio file was created successfully: {audio_file}")
        except Exception as e:
            logger.error(f"Error when generating audio: {e}")
            return
        
        try:
            await self.convert_mp3_to_wav(audio_file, wav_file)
        except Exception as e:
            logger.error(f"Error when converting MP3 to WAV: {e}")
            return

        if rvc_enabled:
            await self._load_rvc()

            model_name = os.path.splitext(os.path.basename(rvc_file))[0]
            available_models = self.rvc.list_models()
            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")

            await asyncio.to_thread(self.rvc.load_model, model_name)
            
            await asyncio.to_thread(
                self.rvc.infer_file,
                audio_file,
                "app/voices/edge_tts_audio/output_rvc.wav"
            )
            output_file = "app/voices/edge_tts_audio/output_rvc.wav"
        else:
            output_file = "app/voices/edge_tts_audio/output.wav"

        await self.play_audio(file_path=output_file)

        logger.info("Audio generation is complete.")

class KokoroTTS(QThread):
    started = pyqtSignal()
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    audio_played = pyqtSignal(str)

    def __init__(self, text=None, character_name=None, ui=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.character_name = character_name

        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.pipeline = None
        self.tts_loaded = False
        self.rvc = None
        self.rvc_loaded = False

        self.ui = ui

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")
    
    def run(self):
        self.started.emit()
        try:
            asyncio.run(self.generate_speech_with_kokoro(self.text, self.character_name))
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    async def _load_tts(self):
        if not self.tts_loaded:
            if self.ui != None:
                self.ui.loading_model_label.show()
                self.ui.loading_model_label.setText("Loading Kokoro model...")
            try:
                self.pipeline = KPipeline(lang_code='a')
                self.tts_loaded = True
                if self.ui != None:
                    self.ui.loading_model_label.setText("TTS model loaded successfully!")
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self):
        if not self.rvc_loaded:
            if self.ui != None:
                self.ui.loading_model_label.show()
                self.ui.loading_model_label.setText("Loading RVC model...")
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0", f0up_key=1, index_rate=0.8, protect=0.7)
                self.rvc_loaded = True
                if self.ui != None:
                    self.ui.loading_model_label.setText("RVC model loaded successfully!")
            except Exception as e:
                raise RuntimeError(f"Failed to load RVC model: {e}")

    async def generate_speech_with_kokoro(self, text, character_name):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        
        kokoro_voice_name = configuration_data["character_list"][character_name]["voice_type"]
        kokoro_rvc_enabled = configuration_data["character_list"][character_name]["rvc_enabled"]
        kokoro_rvc_file = configuration_data["character_list"][character_name]["rvc_file"]
        
        generator = self.pipeline(text, voice=kokoro_voice_name)
        all_audio = []
        for i, (gs, ps, audio) in enumerate(generator):
            logger.info(i, gs, ps)
            display(Audio(data=audio, rate=24000, autoplay=i==0))
            sf.write(f'app/voices/kokoro_audio/{i}.wav', audio, 24000)
            all_audio.append(audio)

        full_audio = np.concatenate(all_audio)
        sf.write("app/voices/kokoro_audio/kokoro_output.wav", full_audio, 24000)

        output_file = "app/voices/kokoro_audio/kokoro_output.wav"

        if kokoro_rvc_enabled:
            await self._load_rvc()

            model_name = os.path.splitext(os.path.basename(kokoro_rvc_file))[0]
            available_models = self.rvc.list_models()
            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")

            await asyncio.to_thread(self.rvc.load_model, model_name)
            
            await asyncio.to_thread(
                self.rvc.infer_file,
                "app/voices/kokoro_audio/kokoro_output.wav",
                "app/voices/kokoro_audio/output_rvc.wav"
            )

            output_file = "app/voices/kokoro_audio/output_rvc.wav"
        else:
            output_file = "app/voices/kokoro_audio/kokoro_output.wav"

        if self.ui != None:
            self.ui.loading_model_label.setText("Audio is ready!")
        await self.play_audio(output_file)

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')

                sd.default.device = self.device_index

                sd.play(data, samplerate)
                sd.wait()

                if self.ui != None:
                    self.ui.loading_model_label.hide()
            except Exception as e:
                logger.error(f"Error: {e}")

        await loop.run_in_executor(None, _play)
    
    def stop_audio(self):
        if self.ui != None:
            self.ui.loading_model_label.hide()
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

        self.device_index = self.configuration_settings.get_main_setting("output_device_real_index")

    async def _load_tts(self):
        if not self.tts_loaded:
            try:
                self.pipeline = KPipeline(lang_code='a')
                self.tts_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load TTS model: {e}")

    async def _load_rvc(self):
        if not self.rvc_loaded:
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0", f0up_key=1, index_rate=0.8, protect=0.7)
                self.rvc_loaded = True
            except Exception as e:
                raise RuntimeError(f"Failed to load RVC model: {e}")

    async def generate_speech_with_kokoro(self, text, character_name):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        
        kokoro_voice_name = configuration_data["character_list"][character_name]["voice_type"]
        kokoro_rvc_enabled = configuration_data["character_list"][character_name]["rvc_enabled"]
        kokoro_rvc_file = configuration_data["character_list"][character_name]["rvc_file"]
        
        generator = self.pipeline(text, voice=kokoro_voice_name)
        all_audio = []
        for i, (gs, ps, audio) in enumerate(generator):
            logger.info(i, gs, ps)
            display(Audio(data=audio, rate=24000, autoplay=i==0))
            sf.write(f'app/voices/kokoro_audio/{i}.wav', audio, 24000)
            all_audio.append(audio)

        full_audio = np.concatenate(all_audio)
        sf.write("app/voices/kokoro_audio/kokoro_output.wav", full_audio, 24000)

        output_file = "app/voices/kokoro_audio/kokoro_output.wav"

        if kokoro_rvc_enabled:
            await asyncio.to_thread(self._load_rvc)

            model_name = os.path.splitext(os.path.basename(kokoro_rvc_file))[0]
            available_models = self.rvc.list_models()
            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")

            await asyncio.to_thread(self.rvc.load_model, model_name)
            
            await asyncio.to_thread(
                self.rvc.infer_file,
                "app/voices/kokoro_audio/kokoro_output.wav",
                "app/voices/kokoro_audio/output_rvc.wav"
            )

            output_file = "app/voices/kokoro_audio/output_rvc.wav"
        else:
            output_file = "app/voices/kokoro_audio/kokoro_output.wav"

        await self.play_audio(output_file)

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')

                sd.default.device = self.device_index

                sd.play(data, samplerate)
                sd.wait()

            except Exception as e:
                logger.error(f"Error: {e}")

        await loop.run_in_executor(None, _play)
    
    def stop_audio(self):
        sd.stop()