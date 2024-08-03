#!/bin/bash

echo "Welcome to the installer of Soul of Waifu"

cd "$(dirname "$0")" || exit

python3 -m venv data

source data/bin/activate

pip install torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118 || exit 1
pip install pygame aiohttp aiofiles translators || exit 1
pip install SpeechRecognition soundfile elevenlabs qasync silero_tts characterai || exit 1
pip install PyQt6 PySide6 numpy==1.26.4 || exit 1

python main.py

deactivate