@echo off
title Soul of Waifu v2.3.0
color 0A

echo =============================================
echo  Soul of Waifu v2.3.0 - Starting Application
echo =============================================
echo.

cd /d "%~dp0"
echo [1/4] Setting working directory...
echo    Current directory: %cd%
echo    Successfully switched to script location.
echo.

set FFMPEG_PATH=%cd%\app\ffmpeg\bin
set PATH=%FFMPEG_PATH%;%PATH%
echo [2/4] Configuring ffmpeg path...
echo    ffmpeg binaries path added: %FFMPEG_PATH%
echo.

echo Checking: Is ffmpeg accessible...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo    ERROR: ffmpeg not found!
    echo    Please make sure the "app\ffmpeg\bin" folder exists
    echo    and contains the executable files: ffmpeg.exe, ffprobe.exe and ffplay.exe
    echo.
    echo    ffmpeg is required for audio/video processing.
    echo    Download it and place it in the specified folder.
    echo.
    echo    Press any key to exit...
    pause >nul
    exit /b 1
) else (
    echo    SUCCESS: ffmpeg found and working correctly.
)
echo.

echo [3/4] Activating virtual environment...
echo    Expected location: app\data\Scripts\activate.bat
echo    Running: call app\data\Scripts\activate.bat app/data/envs/sow
call app\data\Scripts\activate.bat app/data/envs/sow
echo    SUCCESS: Virtual environment activated.
echo    Python and required dependencies are now loaded in isolated environment.
echo.

echo [4/4] Starting main application: main.py...
echo.

python main.py
if %errorlevel% neq 0 (
    echo.
    echo ===================================================
    echo  CRITICAL ERROR: Application exited with code %errorlevel%
    echo ===================================================
    echo.
    echo    An error occurred while running main.py.
    echo    Possible causes:
    echo      - Missing or corrupted Python dependencies.
    echo      - Damaged main.py or other modules.
    echo      - Permission issues or antivirus interference.
    echo.
    echo    Please check the "logs/" folder for detailed error logs.
    echo    Consider restarting the script or reinstalling the app.
    echo.
    echo    Press any key to exit...
    pause >nul
    exit /b %errorlevel%
) else (
    echo.
    echo ===================================
    echo  Application terminated gracefully
    echo ===================================
)

echo.
echo ================================
echo  Soul of Waifu - Execution Done
echo ================================
echo.
echo    The application was launched and closed successfully.
echo    Thank you for using Soul of Waifu!
echo.
pause
echo    Press any key to close this window...
