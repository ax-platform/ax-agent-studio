@echo off
REM Windows startup script for aX Agent Studio Dashboard
REM Simply runs the Python script which handles everything cross-platform

cd /d "%~dp0\.."
python scripts\start_dashboard.py
