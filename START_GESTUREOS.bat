@echo off
title GestureOS — AI Touchless Interface
cd /d "%~dp0"
cls
echo ======================================================================
echo                     STARTING GESTUREOS PLATFORM
echo                AI-Powered Touchless Human-Computer Interface
echo ======================================================================
echo.
echo Launching GestureOS Desktop Dashboard...
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run_gestureos.py"
) else if exist "GestureOS\.venv\Scripts\python.exe" (
    "GestureOS\.venv\Scripts\python.exe" "run_gestureos.py"
) else (
    python "run_gestureos.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo GestureOS stopped with an error code: %ERRORLEVEL%
    echo Please check logs in GestureOS\logs\gestureos.log
    echo ======================================================================
    pause
)
