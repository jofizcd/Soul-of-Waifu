@echo Welcome to the Soul of Waifu
@echo off
cd /d %~dp0
call data\Scripts\activate
python main.py
deactivate
pause
@echo Press any key to continue. . .
