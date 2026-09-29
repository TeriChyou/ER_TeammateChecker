@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run: python tools\setup_runtime.py
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m er_checker %*
if errorlevel 1 pause
