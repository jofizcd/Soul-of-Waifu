@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Soul of Waifu v2.4.7 Installer
color 0A

cd /d "%~dp0"

echo "=============================================================="
echo "Welcome to the Soul of Waifu installer!"
echo "=============================================================="
echo .


echo [1/3] Checking for Pixi...
set "PIXI_BIN_DIR=%~dp0.pixi-bin"
set "PIXI_EXE=%PIXI_BIN_DIR%\pixi.exe"
set "PIXI=pixi"
where pixi >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%PIXI_EXE%" (
        echo Using previously downloaded Pixi binary.
        set "PIXI=%PIXI_EXE%"
    ) else (
        echo Pixi not found on PATH. Downloading the standalone binary from GitHub...
        echo ^(This is saved locally into "%PIXI_BIN_DIR%" only - nothing is installed globally.^)
        if not exist "%PIXI_BIN_DIR%" mkdir "%PIXI_BIN_DIR%"
        set "PIXI_ARCH=x86_64"
        if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PIXI_ARCH=aarch64"
        set "PIXI_URL=https://github.com/prefix-dev/pixi/releases/latest/download/pixi-!PIXI_ARCH!-pc-windows-msvc.exe"
        echo "Downloading Pixi from !PIXI_URL!..."
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '!PIXI_URL!' -OutFile '%PIXI_EXE%'"
        if !errorlevel! neq 0 (
            echo INSTALLATION ERROR: Failed to download Pixi from GitHub.
            pause
            exit /b 1
        )
        if not exist "%PIXI_EXE%" (
            echo INSTALLATION ERROR: Pixi download did not produce an executable.
            pause
            exit /b 1
        )
        set "PIXI=%PIXI_EXE%"
    )
) else (
    echo Pixi is already installed and available on PATH.
)
echo.


echo [2/3] Installing dependencies via Pixi ^(pyproject.toml^)...
echo.
echo ==============================================================
echo Please select PyTorch installation:
echo [1] CUDA (cu128) - Recommended for GPU
echo [2] CPU only
echo ==============================================================
set /p choice="Enter choice (1 or 2): "
if "%choice%"=="1" (
    echo Installing dependencies with PyTorch with CUDA support...
    "%PIXI%" install -e gpu
) else if "%choice%"=="2" (
    echo Installing dependencies with CPU-only PyTorch...
    "%PIXI%" install -e cpu
) else (
    echo Invalid choice.
    pause
    exit /b 1
)
if %errorlevel% neq 0 (
    echo INSTALLATION ERROR: Failed to install PyTorch.
    pause
    exit /b 1
)
echo.

echo [3/3] Final checks...
"%PIXI%" run python -m pip check
"%PIXI%" run python -c "import torch, numpy, transformers, PyQt6; print('Core imports OK')"
"%PIXI%" run python -c "from TTS.api import TTS; print('Coqui TTS import OK')" || echo WARNING: Coqui TTS import failed - possible version conflict!

@REM If user chose CUDA, check if torch can access GPU
if "%choice%"=="1" (
    "%PIXI%" run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
)
echo.

echo =====================================================
echo Installation completed successfully!
echo NOTE: If there are warnings from pip check,
echo       RVC and Coqui may have minor conflicts.
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
