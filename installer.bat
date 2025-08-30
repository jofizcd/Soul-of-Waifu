@echo off
title Soul of Waifu v2.2.0 Installer
color 0A

echo Welcome to Soul of Waifu v2.2.0 Installer

if not exist "app\data\" (
    echo INSTALLATION ERROR: Data folder was not found.
    echo You may not have downloaded the program through the Releases section. Please download the archive from there.
    pause
    exit /b 1
)

echo [1/5] Activating Miniconda3...
echo.
cd /d "%~dp0"
call app\data\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ACTIVATING ERROR: Failed to activate Miniconda3
    pause
    exit /b 1
)

echo [2/5] Activating a virtual environment...
echo.
call app\data\Scripts\activate.bat app/data/envs/sow
if %errorlevel% neq 0 (
    echo ACTIVATING ERROR: Failed to activate a virtual environment
    pause
    exit /b 1
)

echo [3/5] Installing PyTorch with CUDA...
echo.
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
    pip install torch==2.5.1 torchvision torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124  
) else if "%choice%"=="2" (
    echo ^| Installing PyTorch for CPU...                               ^|
    pip install torch==2.5.1 torchvision torchaudio==2.5.1
) else (
    echo ^| Invalid choice. Please restart the installer and try again. ^|
    pause
    exit /b
)

echo [4/5] Installing dependencies...
echo.
pip install PyQt6==6.9.0
pip install PyQt6-WebEngine==6.9.0
pip install qasync==0.27.1
pip install transformers==4.46.2
pip install sentence-transformers==5.1.0
pip install openai==1.70.0
pip install mistralai==1.5.0
pip install edge-tts==7.0.0
pip install coqui-tts
pip install elevenlabs==1.52.0
pip install kokoro==0.9.4
pip install openai-whisper
pip install SpeechRecognition==3.14.1
pip install vosk==0.3.45
pip install playwright==1.52.0
playwright install
pip install translators==6.0.1
pip install huggingface-hub==0.34.4
pip install hf-xet==1.1.7
pip install psutil==7.0.0
pip install GPUtil==1.4.0
pip install sounddevice==0.5.1
pip install soundfile==0.13.1
pip install pydub==0.25.1
pip install PyCharacterAI
pip install PyOpenGL==3.1.9
pip install live2d-py==0.5.4
pip install scikit-learn==1.7.1
pip install aiohttp==3.11.13
pip install requests==2.32.3
pip install tiktoken==0.11.0
pip install PyYAML==6.0.2
pip install pillow==11.3.0
pip install ipython==9.4.0
if %errorlevel% neq 0 (
    echo INSTALLATION ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [5/5] Installing additional dependencies...
echo.
pip install av
pip install praat-parselmouth
pip install python-multipart
pip install pyworld
pip install PyAudio
pip install torchcrepe
pip install uvicorn
pip install tensorboardX
pip install antlr4-python3-runtime==4.9.3
pip install portalocker==3.2.0
pip install omegaconf==2.3.0
pip install numpy==1.25.2

echo =====================================================
echo = The installation has been completed successfully! =
echo =           Now you can start the program           =
echo =====================================================
echo [1] Start the program
echo [2] Exit
set /p post_install_choice="Enter your choice: "

if "%post_install_choice%"=="1" (
    call start.bat
) else if "%post_install_choice%"=="2" (
    exit /b 
) else (
    echo Invalid choice. Exiting.
    pause
)
