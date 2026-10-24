@echo off
title StudyGuard — AI Meme Monitor (Simulation Mode)
cd /d "%~dp0"
cls
echo ======================================================================
echo           STARTING STUDYGUARD IN DRY-RUN SIMULATION MODE
echo ======================================================================
echo.
echo Running automated cycles with simulated camera & live meme audio alerts:
echo   [1] Reading Book Phase
echo   [2] Closing Book -> "Kyu nahi ho rahi padhai?"
echo   [3] Phone Usage  -> "Abeyy padhai likhai karo!"
echo   [4] Water Drink  -> "Pani pani!"
echo.
echo Hotkeys: [B] Book, [C] Close, [P] Phone, [W] Water, [M] Mute, [Q] Quit
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "study_guard.py" --simulation %*
) else (
    python "study_guard.py" --simulation %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Simulation stopped with code %ERRORLEVEL%
    pause
)
