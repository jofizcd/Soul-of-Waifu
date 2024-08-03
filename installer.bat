@echo Welcome to the installer of Soul of Waifu
@echo off
cd /d %~dp0
call python -m venv data
call data\Scripts\activate
pip install torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118
pip install pygame aiohttp aiofiles translators 
pip install SpeechRecognition soundfile elevenlabs qasync silero_tts characterai
pip install PyQt6 PySide6 numpy==1.26.4
python main.py
deactivate