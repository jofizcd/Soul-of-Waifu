import os
import io
import sys
import json
import torch
import audioop
import asyncio
import whisper
import numpy as np
import soundfile as sf
import sounddevice as sd
import speech_recognition as sr

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from io import BytesIO
from vosk import Model, KaldiRecognizer
from configuration.configuration import ConfigurationAPI, ConfigurationCharacters, ConfigurationSettings

class Speech_To_Text:
    """
    A class for speech recognition using three variants (Google STT, Vosk, and Whisper).
    """
    def __init__(self):
        self.configuration_settings = ConfigurationSettings()
        self.configuration_api = ConfigurationAPI()
        self.configuration_characters = ConfigurationCharacters()

        self.recognizer = sr.Recognizer()
        self.audio_data = None
        
        self.input_device_index = self.configuration_settings.get_main_setting("input_device")
        self.output_device_index = self.configuration_settings.get_main_setting("output_device")
        self.current_speech_to_text = self.configuration_settings.get_main_setting("stt_method")

    async def record_microphone(self, silence_timeout=2, chunk_duration=0.1):
        """
        Record audio from the microphone.
        """
        index = self.input_device_index + 1

        audio_data = await asyncio.to_thread(
            self._record_microphone_blocking,
            index,
            silence_timeout,
            chunk_duration
        )
        return audio_data

    def _record_microphone_blocking(self, index, silence_timeout, chunk_duration):
        with sr.Microphone(device_index=index, sample_rate=16000) as source:
            print("Start recording...")
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

            print("Finish recording...")

            final_audio = b''.join(audio_chunks)
            audio_data = sr.AudioData(final_audio, 16000, source.SAMPLE_WIDTH)
            return audio_data

    async def speech_recognition_google(self):
        """
        Using the Google Speech Recognition API for speech recognition from a microphone.
        """
        recognizer = sr.Recognizer()
        user_audio = None
        user_text = None
        
        while True:
            try:
                user_audio = await self.record_microphone()
                if self.current_speech_to_text == 0:
                    user_text = recognizer.recognize_google(user_audio)
                    break
                elif self.current_speech_to_text == 1:
                    user_text = recognizer.recognize_google(user_audio, language = "ru-RU")
                    break
            except sr.UnknownValueError:
                print("Speech recognition failed, new attempt...")
                continue
            except Exception as e:
                print(f"Error: {e}")
                break

        return user_text
    
    async def vosk_transcribe(self, audio_data):
        """
        Using one of the Vosk models for speech recognition from a microphone.
        """
        match self.current_speech_to_text:
            case 2:
                model_us = Model("resources/data/speech-to-text/vosk-model-en-us-0.22-lgraph")
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

            case 3:
                model_ru = Model("resources/data/speech-to-text/vosk-model-small-ru-0.22")
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
                user_text = await self.vosk_transcribe(user_audio)
                if user_text is None or user_text.strip() == "":
                    print("An empty result, a new attempt...")
                    continue

                print("You said:", user_text)
                break
            except Exception as e:
                print(f"Error: {e}")
                break

        return user_text

    async def speech_recognition_whisper(self):
        """
        Using the Whisper model for speech transcription.
        """
        user_audio = None
        user_text = None

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model(name="base", device=device, download_root="resources/data/speech-to-text/whisper-small", in_memory=True)

        while True:
            try:
                user_audio = await self.record_microphone()
                wav_data = user_audio.get_wav_data(convert_rate=16000, convert_width=2)

                audio_data, samplerate = sf.read(BytesIO(wav_data))
                audio_data = audio_data.astype(np.float32)

                user_text = model.transcribe(audio_data)
                print("You said:", user_text["text"])

                if user_text["text"] is None or user_text["text"].strip() == "" or user_text["text"].strip().lower() == "you":
                    print("An empty result or only 'you' is recognized, repeat recognition...")
                    continue 

                break
            except Exception as e:
                print(f"Error: {e}")
                break

        return user_text["text"]