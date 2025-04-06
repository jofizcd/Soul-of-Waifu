@echo Starting the Soul of Waifu. . .
@echo off

cd /d %~dp0
set FFMPEG_PATH=%cd%\resources\data\ffmpeg\bin
set PATH=%FFMPEG_PATH%;%PATH%

echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg not found. Please ensure it is installed in the "ffmpeg" directory.
    pause
    exit /b 1
)

call lib\Scripts\activate

python main.py

call lib\Scripts\deactivate.bat

pause
@echo Press any key to close. . .
