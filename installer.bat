@echo off
color 0A
					 
echo Installing Soul of Waifu        
echo.
echo Creating virtual environment...
python -m venv lib
call lib\Scripts\activate

echo ===========================================
echo           Installing dependencies         
echo ===========================================
echo Installing dependencies... Please wait.

python -m pip install --upgrade --force-reinstall pip
pip install av
pip install pyworld
pip install tensorboardX
pip install edge-tts
pip install openai
pip install requests
pip install qasync
pip install PyQt6
pip install PyOpenGL
pip install onnxruntime
pip install live2d-py
pip install transformers
pip install psutil
pip install git+https://github.com/kramcat/CharacterAI.git

echo    ==============================================================
echo    Please select an installation option:
echo.
echo      [1] Install PyTorch with CUDA support (for GPU acceleration)
echo      [2] Install PyTorch for CPU only (no GPU required)
echo.
echo    ==============================================================
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    echo ^| Installing PyTorch with CUDA support...                     ^|
    echo. 
    pip install torch==2.5.1 torchvision torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
) else if "%choice%"=="2" (
    echo ^| Installing PyTorch for CPU...                               ^|
    echo.
    pip install torch==2.5.1 torchvision torchaudio==2.5.1
) else (
    echo ^| Invalid choice. Please restart the installer and try again. ^|
    pause
    exit /b
)

pip install torchcrepe
pip install openai-whisper
pip install sounddevice
pip install soundfile
pip install SpeechRecognition
pip install coqui-tts
pip install pydub
pip install elevenlabs
pip install git+https://github.com/JarodMica/rvc-python
pip install PyCharacterAI
pip install aiohttp
pip install mistralai
pip install sentencepiece==0.2.0
pip install sacremoses
pip install translators
pip install vosk
pip install pyaudio
pip install numpy==1.25.2
pip install resources\data\fairseq-0.12.3-cp311-cp311-win_amd64.whl

echo ===================================================
echo.
echo            The installation is complete!
echo       You can start the program via start.bat
echo.
echo ===================================================

call lib\Scripts\deactivate.bat
pause
@echo Press any key to continue. . .
