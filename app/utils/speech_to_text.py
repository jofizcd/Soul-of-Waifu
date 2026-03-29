import os
import io
import sys
import json
import torch
import time
import pyaudio
import audioop
import asyncio
import logging
import wave
import numpy as np
import soundfile as sf

from PyQt6.QtCore import QThread, pyqtSignal
from faster_whisper import WhisperModel
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.configuration.configuration import ConfigurationAPI, ConfigurationCharacters, ConfigurationSettings

logger = logging.getLogger("Speech-To-Text Module")

class AudioInputWorker(QThread):
    voice_detected_signal = pyqtSignal()
    volume_signal = pyqtSignal(float)
    silence_detected_signal = pyqtSignal()
    audio_packet_ready = pyqtSignal(bytes)

    def __init__(self, input_device_index=None):
        super().__init__()
        self.input_device_index = input_device_index
        self.is_running = True
        
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 512
        
        logger.info("⏳ Loading Silero VAD model...")
        try:
            silero_local_path = os.path.join(os.getcwd(), "app", "utils", "speech-to-text", "silero-vad")

            if os.path.exists(silero_local_path):
                self.model, utils = torch.hub.load(repo_or_dir=silero_local_path,
                                                   model='silero_vad',
                                                   source='local',
                                                   force_reload=False)
            else:
                self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                                   model='silero_vad',
                                                   force_reload=False,
                                                   trust_repo=True)
            self.get_speech_timestamps, _, _, _, _ = utils
            logger.info("✅ Silero VAD Loaded successfully!")
        except Exception as e:
            logger.error(f"❌ Error loading Silero VAD: {e}")
            self.model = None

        self.frames = []
        self.silence_threshold = 45
        self.voice_threshold = 0.5

    def run(self):
        logger.info("🚀 Audio Worker Thread Started")
        p = pyaudio.PyAudio()

        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        logger.info(f"🎧 Found {numdevices} audio devices:")
        found_device = False
        
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = p.get_device_info_by_host_api_device_index(0, i).get('name')
                logger.info(f"   Device ID {i}: {name}")
                if self.input_device_index == i:
                    found_device = True

        if self.input_device_index is not None and not found_device:
            logger.warning(f"⚠️ Device ID {self.input_device_index} not found. Using Default.")
            self.input_device_index = None

        stream = None
        try:
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.SAMPLE_RATE,
                            input=True,
                            input_device_index=self.input_device_index,
                            frames_per_buffer=self.CHUNK_SIZE)
            logger.info("🎙️ Microphone stream opened successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to open microphone: {e}")
            return

        speaking = False
        silence_chunks = 0

        while self.is_running:
            try:
                if not self.model:
                    time.sleep(1)
                    continue

                data = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                
                audio_int16 = np.frombuffer(data, np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                tensor = torch.from_numpy(audio_float32)

                speech_prob = self.model(tensor, self.SAMPLE_RATE).item()
                rms = float(np.sqrt(np.mean(audio_float32 ** 2)))
                volume = min(1.0, rms * 22.0)
                self.volume_signal.emit(volume)

                if speech_prob > self.voice_threshold:
                    if not speaking:
                        speaking = True
                        self.voice_detected_signal.emit()
                        logger.info("🗣️ User started speaking")
                    
                    silence_chunks = 0
                    self.frames.append(data)
                
                else:
                    if speaking:
                        self.frames.append(data)
                        silence_chunks += 1
                        
                        if silence_chunks > self.silence_threshold:
                            speaking = False
                            self.silence_detected_signal.emit()
                            logger.info(f"🤫 User stopped. Sending {len(self.frames)} frames.")
                            
                            full_audio = b''.join(self.frames)
                            self.audio_packet_ready.emit(full_audio)
                            
                            self.frames = []
                            silence_chunks = 0
            
            except Exception as e:
                logger.error(f"⚠️ Error in audio loop: {e}")
                break

        logger.info("🛑 Stopping Audio Stream...")
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
        logger.info("✅ Audio Worker Stopped cleanly")

    def stop(self):
        self.is_running = False
        self.wait()

class STTWorker(QThread):
    text_ready_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, model_size="small", device="cuda", compute_type="float16"):
        super().__init__()
        self.queue = []
        self.is_running = True
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        self.model = None 

    def load_model(self):
        if self.model is None:
            logger.info(f"⏳ Loading Faster-Whisper ({self.model_size}) on {self.device}...")

            try:
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

                logger.info("✅ Faster-Whisper Loaded!")
                self.status_signal.emit("Model Loaded")
            except Exception as e:
                logger.error(f"❌ Error loading Whisper (Switching to CPU): {e}")
                self.device = "cpu"
                self.compute_type = "int8"
                
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                    
                logger.info("✅ Faster-Whisper Loaded on CPU!")

    def add_audio(self, audio_bytes):
        self.queue.append(audio_bytes)

    def run(self):
        self.load_model()
        
        logger.info("🚀 STT Loop Started")
        
        while self.is_running:
            if len(self.queue) > 0:
                audio_bytes = self.queue.pop(0)
                
                try:
                    audio_np = np.frombuffer(audio_bytes, np.int16).flatten().astype(np.float32) / 32768.0
                    segments, info = self.model.transcribe(audio_np, beam_size=5)
                    
                    full_text = ""
                    for segment in segments:
                        full_text += segment.text
                    
                    full_text = full_text.strip()
                    hallucinations = [
                        "субтитры создавал", "редактор субтитров", "спасибо за просмотр", 
                        "подписывайтесь на канал", "продолжение следует", 
                        "субтитры", "а. семенов", "перевод", "озвучка",
                        
                        "ВЕСЕЛАЯ МУЗЫКА", "СПОКОЙНАЯ МУЗЫКА", "ГРУСТНАЯ МЕЛОДИЯ", 
                        "ЛИРИЧЕСКАЯ МУЗЫКА", "ДИНАМИЧНАЯ МУЗЫКА", "ТАИНСТВЕННАЯ МУЗЫКА", 
                        "ТОРЖЕСТВЕННАЯ МУЗЫКА", "ИНТРИГУЮЩАЯ МУЗЫКА", "НАПРЯЖЕННАЯ МУЗЫКА", 
                        "ПЕЧАЛЬНАЯ МУЗЫКА", "ТРЕВОЖНАЯ МУЗЫКА", "МУЗЫКАЛЬНАЯ ЗАСТАВКА",
                        
                        "ПЕРЕСТРЕЛКА", "ГУДОК ПОЕЗДА", "РЁВ МОТОРА", "ШУМ ДВИГАТЕЛЯ", 
                        "СИГНАЛ АВТОМОБИЛЯ", "ЛАЙ СОБАК", "ПЕС ЛАЕТ", "КАШЕЛЬ", "ВЫСТРЕЛЫ", 
                        "ШУМ ДОЖДЯ", "ПЕСНЯ", "ПО ГРОМКОГОВОРИЧЕСКОМ ЯЗЫКЕ", "ПО ГРОМКОГОВОРИТЕЛЮ", 
                        "ВЗРЫВ", "ШУМ МОТОРА", "ПЛЕСК ВОДЫ", "ГУДОК АВТОМОБИЛЯ", "ЛАЙ СОБАКИ", 
                        "ПО ТВ.", "АПЛОДИСМЕНТЫ", "ГОРОДСКОЙ ШУМ", "ПОЛИЦИЯ", "ГОРОДСКОЙ ГУДОК", 
                        "СИГНАЛ МАШИНЫ", "СМЕХ", "СТУК В ДВЕРЬ", "ААААААААААААААААААААА", 
                        "ПОЛИЦЕЙСКАЯ СИРЕНА", "ЗВОНОК В ДВЕРЬ",
                        
                        "Спасибо за субтитры!", "Субтитры добавил DimaTorzok", 
                        "Субтитры подогнал «Симон»!", 
                        "Редактор субтитров М.Лосева Корректор А.Егорова",
                        "Редактор субтитров А.Синецкая Корректор А.Егорова",
                        "Редактор субтитров Т.Горелова Корректор А.Егорова",
                        "Редактор субтитров Е.Жукова Корректор А.Егорова",
                        "Редактор субтитров А.Семкин Корректор А.Егорова",
                        "Редактор субтитров А.Захарова Корректор А.Егорова",
                        
                        "Смотрите продолжение во второй части видео.", 
                        "Смотрите продолжение в следующей части.", 
                        "Смотрите продолжение в следующей части видео.", 
                        "Смотрите продолжение в 4 части видео.", 
                        "Смотрите продолжение в следующей серии...", 
                        "Смотрите продолжение во второй части.", 
                        "Продолжение следует...",
                        
                        "ПОДПИШИСЬ НА КАНАЛ", "ПОДПИШИСЬ!", "ПОДПИШИСЬ",
                        
                        "🦜", "💥", "😎", "🤨", "🤔", "Поехали!", "Поехали.", 
                        "Девушки отдыхают..."
                    ]

                    is_hallucination = any(h in full_text.lower() for h in hallucinations)

                    if full_text and not is_hallucination and len(full_text) > 2:
                        logger.info(f"📝 Text Recognized: {full_text}")
                        self.text_ready_signal.emit(full_text)
                    else:
                        logger.info("Empty audio fragment or hallucination ignored.")
                        
                except Exception as e:
                    logger.error(f"⚠️ STT Error: {e}")
            
            else:
                self.msleep(50) 
        
        logger.info("🛑 STT Worker Stopped")

    def stop(self):
        logger.info("Signaling Audio Worker to stop...")
        self.is_running = False
        self.queue.append(b'')
        self.quit()
        self.wait()
