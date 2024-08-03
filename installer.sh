#!/bin/bash

echo "Welcome to the installer of Soul of Waifu"

cd "$(dirname "$0")"

python3 -m venv data  # Используем python3 для создания виртуального окружения

source data/bin/activate

pip install torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118
pip install pygame aiohttp aiofiles translators SpeechRecognition soundfile elevenlabs qasync silero_tts PyAudio characterai PyQt6 PySide6 numpy==1.26.4

python main.py

deactivate
