@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Soul of Waifu v2.4.0 Installer
color 0A

cd /d "%~dp0"
set "PYTHON=%CD%\app\data\envs\sow\python.exe"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

echo Welcome to Soul of Waifu v2.4.0 Installer
echo.

if not exist "%PYTHON%" (
    echo INSTALLATION ERROR: Runtime Python was not found:
    echo %PYTHON%
    echo You may not have downloaded the program through the Releases section. Please download the archive from there.
    pause
    exit /b 1
)

echo [1/5] Activating and verifying bundled Python environment...
call app\data\Scripts\activate.bat app/data/envs/sow || goto :install_error
"%PYTHON%" --version || goto :install_error

echo.
echo ==============================================================
echo Please select PyTorch installation:
echo [1] CUDA (cu128) - Recommended for GPU
echo [2] CPU only
echo ==============================================================
choice /c 12 /n /m "Enter choice [1/2]: "
set "choice=%errorlevel%"

echo [2/5] Installing pinned NumPy, Pillow and PyTorch...
"%PYTHON%" -m pip install --no-cache-dir numpy==1.26.4 pillow==11.3.0 || goto :install_error

if "%choice%"=="1" (
    echo Installing PyTorch with CUDA support...
    "%PYTHON%" -m pip install --no-cache-dir torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu128 || goto :install_error
) else if "%choice%"=="2" (
    echo Installing PyTorch CPU...
    "%PYTHON%" -m pip install --no-cache-dir torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 || goto :install_error
) else (
    echo Invalid choice.
    pause
    exit /b 1
)

echo [3/5] Installing application dependencies...

echo Installing shared pinned dependencies first...
"%PYTHON%" -m pip install --no-cache-dir scikit-learn==1.4.2 scipy==1.13.1 aiohttp==3.11.13 requests==2.32.3 sounddevice==0.5.1 soundfile==0.13.1 pydub==0.25.1 psutil==7.0.0 huggingface-hub==0.36.0 hf_transfer==0.1.9 transformers==4.57.3 torchcodec==0.10.0 av==18.0.0 python-multipart==0.0.32 uvicorn==0.51.0 || goto :install_error

"%PYTHON%" -m pip install --no-cache-dir PyQt6==6.9.0 PyQt6-WebEngine==6.9.0 qasync==0.27.1 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir mss==10.2.0 ddgs==9.14.4 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir discord.py==2.7.1 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir sentence-transformers==5.1.0 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir openai==1.70.0 mistralai==1.5.0 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir edge-tts==7.2.7 elevenlabs==1.52.0 kokoro==0.9.4 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir qwen-tts==0.1.1 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir faster-whisper==1.2.1 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir translators==6.0.1 GPUtil==1.4.0 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir PyOpenGL==3.1.9 live2d-py==0.5.4 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir tiktoken==0.11.0 PyYAML==6.0.2 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir praat-parselmouth==0.4.7 PyAudio==0.2.14 || goto :install_error
"%PYTHON%" -m pip install --no-cache-dir antlr4-python3-runtime==4.9.3 portalocker==3.2.0 tensorboardX==2.6.4 || goto :install_error

echo Installing Coqui TTS / XTTSv2 (latest compatible fork)...
"%PYTHON%" -m pip install --no-cache-dir coqui-tts[codec]==0.27.5 || goto :install_error

echo Installing RVC support dependencies...
"%PYTHON%" -m pip install --no-cache-dir pyworld==0.3.5 torchcrepe==0.0.24 uvicorn==0.51.0 omegaconf==2.3.0 || goto :install_error

echo [4/5] Checking dependency metadata...
"%PYTHON%" -m pip check
if errorlevel 1 (
    echo WARNING: Dependency metadata conflicts were found above.
    echo The required runtime imports will still be tested before success is reported.
)

echo [5/5] Smoke test...
"%PYTHON%" -c "import aiohttp, discord, mss, numpy, torch, transformers, PyQt6; from app.utils.character_cards import CharactersCard; print('Core imports OK')" || goto :install_error
"%PYTHON%" -c "from app.utils.text_to_speech import TTSWorker; from app.utils.speech_to_text import STTWorker; print('Speech imports OK')" || goto :install_error

echo =====================================================
echo Installation completed successfully!
echo All required runtime imports passed.
echo =====================================================
echo [1] Start the program
echo [2] Exit
set /p post_install_choice="Enter your choice: "
if "%post_install_choice%"=="1" goto :start

echo Exiting.
pause
exit /b 0

:start
call start.bat
exit /b %errorlevel%

:install_error
set "INSTALL_EXIT_CODE=%errorlevel%"
if "%INSTALL_EXIT_CODE%"=="0" set "INSTALL_EXIT_CODE=1"
echo.
echo =====================================================
echo INSTALLATION ERROR: A required command failed.
echo Exit code: %INSTALL_EXIT_CODE%
echo =====================================================
pause
exit /b %INSTALL_EXIT_CODE%
