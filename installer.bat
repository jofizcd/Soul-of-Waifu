@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Soul of Waifu v2.3.1 Installer
color 0A

echo Welcome to Soul of Waifu v2.3.1 Installer
echo.

if not exist "app\data\" (
    echo INSTALLATION ERROR: Data folder was not found.
    echo You may not have downloaded the program through the Releases section. Please download the archive from there.
    pause
    exit /b 1
)

echo [1/6] Activating Miniconda3...
cd /d "%~dp0"
call app\data\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ACTIVATING ERROR: Failed to activate Miniconda3
    pause
    exit /b 1
)

echo [2/6] Activating virtual environment...
call app\data\Scripts\activate.bat app\data\envs\sow
if %errorlevel% neq 0 (
    echo ACTIVATING ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/6] Upgrading pip and installing PyTorch...
python -m pip install --upgrade pip setuptools wheel

echo.
echo ==============================================================
echo Please select PyTorch installation:
echo [1] CUDA (cu128) - Recommended for GPU
echo [2] CPU only
echo ==============================================================
set /p choice="Enter choice (1 or 2): "
if "%choice%"=="1" (
    echo Installing PyTorch with CUDA support...
    pip install --no-cache-dir torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu128
) else if "%choice%"=="2" (
    echo Installing PyTorch CPU...
    pip install --no-cache-dir torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0
) else (
    echo Invalid choice.
    pause
    exit /b 1
)

echo [4/6] Installing core dependencies (with version pins)...

pip install --no-cache-dir --force-reinstall numpy==1.26.4

pip install --no-cache-dir PyQt6==6.9.0 PyQt6-WebEngine==6.9.0 qasync==0.27.1
pip install --no-cache-dir sentence-transformers==5.1.0
pip install --no-cache-dir openai==1.70.0 mistralai==1.5.0
pip install --no-cache-dir edge-tts==7.2.7 elevenlabs==1.52.0 kokoro==0.9.4
pip install --no-cache-dir faster-whisper
pip install --no-cache-dir playwright==1.52.0
playwright install
pip install --no-cache-dir translators==6.0.1 psutil==7.0.0 GPUtil==1.4.0
pip install --no-cache-dir sounddevice==0.5.1 soundfile==0.13.1 pydub==0.25.1
pip install --no-cache-dir PyCharacterAI PyOpenGL==3.1.9 live2d-py==0.5.4
pip install --no-cache-dir scikit-learn==1.4.2 aiohttp==3.11.13 requests==2.32.3
pip install --no-cache-dir tiktoken==0.11.0 PyYAML==6.0.2 pillow==11.3.0 ipython==9.4.0

pip install --no-cache-dir huggingface-hub==0.36.0 hf_transfer==0.1.9
pip install --no-cache-dir transformers==4.57.3

pip install --no-cache-dir av praat-parselmouth scipy==1.13.1
pip install --no-cache-dir python-multipart PyAudio tensorboardX
pip install --no-cache-dir antlr4-python3-runtime==4.9.3 portalocker==3.2.0

echo Installing Coqui TTS / XTTSv2 (latest compatible fork)...
pip install --no-cache-dir coqui-tts[codec]

echo Installing RVC support dependencies...
pip install --no-cache-dir pyworld torchcrepe uvicorn omegaconf==2.3.0
pip install --no-cache-dir --force-reinstall torchcodec==0.10.0

echo [5/6] Final checks...
python -m pip check

echo [6/6] Smoke test (basic imports)...
python -c "import torch, numpy, transformers, PyQt6; print('Core imports OK')"
python -c "from TTS.api import TTS; print('Coqui TTS import OK')" || echo WARNING: Coqui TTS import failed - possible version conflict!

echo =====================================================
echo Installation completed successfully!
echo If there are warnings from pip check - RVC and Coqui may have minor conflicts.
echo =====================================================
echo [1] Start the program
echo [2] Exit
set /p post_install_choice="Enter your choice: "
if "%post_install_choice%"=="1" (
    call start.bat
) else (
    echo Exiting.
    pause
)
