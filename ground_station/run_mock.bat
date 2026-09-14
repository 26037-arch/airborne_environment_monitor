@echo off
cd /d "%~dp0"
python main.py --mock
if errorlevel 1 pause

