@echo off
setlocal EnableExtensions

rem Edit this Git checkout. The adjacent Release directory supplies Python,
rem packages, FFmpeg, models, icons, and other large runtime-only files.
set "SOURCE_ROOT=%~dp0"
for %%I in ("%~dp0..\Soul-of-Waifu-v2.4.0") do set "RUNTIME_ROOT=%%~fI"
set "RUNTIME_PYTHON=%RUNTIME_ROOT%\app\data\envs\sow\python.exe"
set "RUNTIME_ACTIVATE=%RUNTIME_ROOT%\app\data\Scripts\activate.bat"

if /I "%~1"=="--help" goto :help

if not exist "%RUNTIME_PYTHON%" (
    echo Runtime not found: "%RUNTIME_ROOT%"
    echo Extract the v2.4.0 Release beside this Git checkout first.
    exit /b 1
)

"%RUNTIME_PYTHON%" "%SOURCE_ROOT%dev_sync.py" "%RUNTIME_ROOT%"
if errorlevel 1 exit /b %errorlevel%

if /I "%~1"=="--sync-only" exit /b 0

call "%RUNTIME_ACTIVATE%" "%RUNTIME_ROOT%\app\data\envs\sow"
if errorlevel 1 (
    echo Failed to activate the Release Python environment.
    exit /b 1
)

set "PATH=%RUNTIME_ROOT%\app\ffmpeg\bin;%PATH%"
pushd "%RUNTIME_ROOT%"
"%RUNTIME_PYTHON%" -c "import PyQt6, qasync, torch" >nul 2>&1
if errorlevel 1 (
    popd
    echo.
    echo Runtime packages are not installed yet.
    echo Run this once, without Administrator privileges:
    echo   "%RUNTIME_ROOT%\installer.bat"
    exit /b 1
)

"%RUNTIME_PYTHON%" main.py
set "APP_EXIT=%ERRORLEVEL%"
popd
exit /b %APP_EXIT%

:help
echo Usage:
echo   run-dev.bat             Sync Git source and launch the application.
echo   run-dev.bat --sync-only Sync Git source without launching.
exit /b 0
