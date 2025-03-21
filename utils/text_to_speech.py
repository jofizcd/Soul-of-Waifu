import os
import io
import torch
import asyncio
import numpy as np
import soundfile as sf
import sounddevice as sd

from TTS.api import TTS
from pydub import AudioSegment
from elevenlabs.client import AsyncElevenLabs

from configuration import configuration
from rvc_python.infer import RVCInference

class ElevenLabs:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.eleven_labs_api = self.configuration_api.get_token("ELEVENLABS_API_TOKEN")
        self.eleven = AsyncElevenLabs(api_key=self.eleven_labs_api)
        
        self.audio_cache = AudioSegment.empty()

    async def generate_speech_with_elevenlabs(self, text, voice_id):
        """
        Asynchronous function for speech generation via ElevenLabs.
        """
        try:
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
            print(f"Error: {e}")

    async def play_audio(self, audio):
        """
        It plays audio through a sounddevice.
        """
        try:
            samples = np.array(audio.get_array_of_samples())
            sample_rate = audio.frame_rate

            await asyncio.to_thread(sd.play, samples, samplerate=sample_rate)
            await asyncio.to_thread(sd.wait)
        except Exception as e:
            print(f"Error: {e}")

    def clear_audio_cache(self):
        self.audio_cache = AudioSegment.empty()

class XTTSv2:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.tts = None
        self.rvc = None
        self.tts_loaded = False
        self.rvc_loaded = False
    
    async def _load_tts(self):
        """
        Загружает модель TTS, если она еще не загружена.
        """
        if not self.tts_loaded:
            print("Loading TTS model...")
            try:
                self.tts = TTS(model_name='tts_models/multilingual/multi-dataset/xtts_v2', progress_bar=True).to(self.device)
                self.tts_loaded = True
                print("TTS model loaded successfully.")
            except Exception as e:
                print(f"Error loading TTS model: {e}")
                raise RuntimeError("Failed to load TTS model.")

    async def _load_rvc(self):
        """
        Загружает модель RVC, если она еще не загружена.
        """
        if not self.rvc_loaded:
            print("Loading RVC model...")
            try:
                self.rvc = RVCInference(models_dir="assets/rvc_models", device="cuda:0" if torch.cuda.is_available() else "cpu:0")
                self.rvc_loaded = True
                print("RVC model loaded successfully.")
            except Exception as e:
                print(f"Error loading RVC model: {e}")
                raise RuntimeError("Failed to load RVC model.")

    async def generate_speech_with_xttsv2(self, text, language, character_name):
        await self._load_tts()

        configuration_data = self.configuration_characters.load_configuration()
        
        xttsv2_voice_type = configuration_data["character_list"][character_name]["xttsv2_voice_type"]
        xttsv2_rvc_enabled = configuration_data["character_list"][character_name]["xttsv2_rvc_enabled"]
        xttsv2_rvc_file = configuration_data["character_list"][character_name]["xttsv2_rvc_file"]

        if xttsv2_voice_type == "Female Calm":
            await asyncio.to_thread(
                self.tts.tts_to_file,
                text=text,
                speaker_wav="resources/voices/calm_female.wav",
                language=language,
                file_path="resources/sounds/output.wav"
            )
        elif xttsv2_voice_type == "Female":
            await asyncio.to_thread(
                self.tts.tts_to_file,
                text=text,
                speaker_wav="resources/voices/female.wav",
                language=language,
                file_path="resources/sounds/output.wav"
            )
        elif xttsv2_voice_type == "Male":
            await asyncio.to_thread(
                self.tts.tts_to_file,
                text=text,
                speaker_wav="resources/voices/male.wav",
                language=language,
                file_path="resources/sounds/output.wav"
            )

        if xttsv2_rvc_enabled:
            await self._load_rvc()

            model_name = os.path.splitext(os.path.basename(xttsv2_rvc_file))[0]
            available_models = self.rvc.list_models()
            if model_name not in available_models:
                raise ValueError(f"Model {model_name} not found. Available models: {available_models}")

            await asyncio.to_thread(self.rvc.load_model, model_name)
            
            await asyncio.to_thread(
                self.rvc.infer_file,
                "resources/sounds/output.wav",
                "resources/sounds/output_rvc.wav"
            )

            output_file = "resources/sounds/output_rvc.wav"
        else:
            output_file = "resources/sounds/output.wav"

        await self.play_audio(output_file)

    async def play_audio(self, file_path):
        loop = asyncio.get_event_loop()

        def _play():
            try:
                data, samplerate = sf.read(file_path, dtype='float32')
                sd.play(data, samplerate)
                sd.wait()
            except Exception as e:
                print(f"Error: {e}")

        await loop.run_in_executor(None, _play)

    def clear_audio_cache(self):
        self.audio_cache = AudioSegment.empty()
        