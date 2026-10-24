@echo off
title GestureOS — Simulation Mode
cd /d "%~dp0"
cls
echo ======================================================================
echo             STARTING GESTUREOS IN SIMULATION MODE
echo       Zero-risk dry-run testing with synthetic camera & mock controls
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run_gestureos.py" --simulation
) else (
    python "run_gestureos.py" --simulation
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Simulation stopped with code %ERRORLEVEL%
    pause
)
