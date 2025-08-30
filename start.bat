@echo off
title Soul of Waifu v2.2.0
color 0A

echo ====================
echo Soul of Waifu v2.2.0                     
echo ====================
echo.

echo Activating virtual environment...
call app\data\Scripts\activate.bat app/data/envs/sow
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment!
    echo Please check if you have installed the program from the Releases section.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Starting application...
echo.

python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application crashed with error code %errorlevel%
    echo Please check the logs folder for more details.
    echo.
    echo Press any key to exit...
    pause >nul
)

echo.
echo ==================
echo Application closed
echo ==================
echo.

pause
@echo Press any key...
