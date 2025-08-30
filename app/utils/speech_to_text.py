import os
import io
import sys
import json
import torch
import audioop
import asyncio
import whisper
import logging
import numpy as np
import soundfile as sf
import speech_recognition as sr

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from io import BytesIO
from vosk import Model, KaldiRecognizer

from app.configuration.configuration import ConfigurationAPI, ConfigurationCharacters, ConfigurationSettings

logger = logging.getLogger("Speech-To-Text Module")

class Speech_To_Text:
    """
    A class for speech recognition using two variants (Vosk and Whisper).
    """
    def __init__(self):
        self.configuration_settings = ConfigurationSettings()
        self.configuration_api = ConfigurationAPI()
        self.configuration_characters = ConfigurationCharacters()

        self.recognizer = sr.Recognizer()
        self.input_device_index = self.configuration_settings.get_main_setting("input_device")
        self.current_speech_to_text = self.configuration_settings.get_main_setting("stt_method")

    async def record_microphone(self, silence_timeout=2, chunk_duration=0.1):
        """
        Record audio from the microphone.
        """
        index = self.input_device_index + 1
        
        return await asyncio.to_thread(
            self.record_microphone_blocking,
            index,
            silence_timeout,
            chunk_duration
        )

    def record_microphone_blocking(self, index, silence_timeout, chunk_duration):
        with sr.Microphone(device_index=index, sample_rate=16000) as source:
            logger.info("Start recording...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio_chunks = []
            silence_counter = 0
            samples_per_chunk = int(16000 * chunk_duration)
            silence_threshold = self.recognizer.energy_threshold + 300

            while True:
                buffer = source.stream.read(samples_per_chunk)
                audio_chunks.append(buffer)

                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                if energy < silence_threshold:
                    silence_counter += chunk_duration
                    if silence_counter >= silence_timeout:
                        break
                else:
                    silence_counter = 0

            logger.info("Finish recording...")

            final_audio = b''.join(audio_chunks)
            return sr.AudioData(final_audio, 16000, source.SAMPLE_WIDTH)
    
    def vosk_transcribe(self, audio_data):
        """
        Using one of the Vosk models for speech recognition from a microphone.
        """
        match self.current_speech_to_text:
            case 0:
                model_us = Model("app/utils/speech-to-text/vosk-model-en-us-0.22-lgraph")
                recognizer = KaldiRecognizer(model_us, 16000)

                wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
                audio_stream = io.BytesIO(wav_data)
                while True:
                    chunk = audio_stream.read(4000)
                    if not chunk:
                        break
                    recognizer.AcceptWaveform(chunk)

                result = recognizer.Result()
                result_dict = json.loads(result)
                
                return result_dict.get("text", "")

            case 1:
                model_ru = Model("app/utils/speech-to-text/vosk-model-small-ru-0.22")
                recognizer = KaldiRecognizer(model_ru, 16000)

                wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
                audio_stream = io.BytesIO(wav_data)
                while True:
                    chunk = audio_stream.read(4000)
                    if not chunk:
                        break
                    recognizer.AcceptWaveform(chunk)

                result = recognizer.Result()
                result_dict = json.loads(result)
                
                return result_dict.get("text", "")

    async def speech_recognition_vosk(self):
        """
        A method for speech recognition using Vosk.
        """
        user_audio = None
        user_text = None

        while True:
            try:
                user_audio = await self.record_microphone()
                user_text = await asyncio.to_thread(self.vosk_transcribe, user_audio)
                if user_text is None or user_text.strip() == "" or user_text["text"].strip().lower() == "you" or user_text["text"].strip().lower() == "the":
                    logger.info("An empty result or only 'you', 'the' is recognized, repeat recognition...")
                    continue

                logger.info("You said: %s", user_text)
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break

        return user_text

    def whisper_transcribe(self, audio_data):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model(name="base", device=device, download_root="app/utils/speech-to-text/whisper-small", in_memory=True)

        wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)

        audio_np, samplerate = sf.read(BytesIO(wav_data))
        audio_np = audio_np.astype(np.float32)

        user_text = model.transcribe(audio_np)
        logger.info("You said: %s", user_text["text"])

        return user_text

    async def speech_recognition_whisper(self):
        """
        Using the Whisper model for speech transcription.
        """
        user_audio = None
        user_text = None

        while True:
            try:
                user_audio = await self.record_microphone()
                user_text = await asyncio.to_thread(self.whisper_transcribe, user_audio)

                if user_text["text"] is None or user_text["text"].strip() == "" or user_text["text"].strip().lower() == "you" or user_text["text"].strip().lower() == "the":
                    logger.info("An empty result or only 'you', 'the' is recognized, repeat recognition...")
                    continue 

                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break

        return user_text["text"]
    
    async def speech_recognition(self):
        if self.current_speech_to_text in (0, 1):                  # Vosk
            user_text = await self.speech_recognition_vosk()
        else:                                                      # Whisper
            user_text = await self.speech_recognition_whisper()

        return user_text