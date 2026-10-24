@echo off
title StudyGuard — AI Meme Distraction & Hydration Monitor
cd /d "%~dp0"
cls
echo ======================================================================
echo                  STARTING STUDYGUARD AI MEME MONITOR
echo ======================================================================
echo.
echo Detecting:
echo   [1] Book Reading -> Book Closing: "Kyu Nahi Ho Rahi Padhai?"
echo   [2] Phone Distraction After Book: "Abeyy Padhai Likhai Karo!"
echo   [3] Drinking Water:               "Pani Pani!"
echo.
echo Hotkeys inside window:
echo   [B] Simulate Book Reading    [C] Simulate Book Closing
echo   [P] Simulate Phone In Use    [W] Simulate Drinking Water
echo   [M] Toggle Audio Mute        [R] Reset Stats
echo   [Q] Quit
echo.
echo Launching StudyGuard...
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "study_guard.py" %*
) else if exist "GestureOS\.venv\Scripts\python.exe" (
    "GestureOS\.venv\Scripts\python.exe" "study_guard.py" %*
) else (
    python "study_guard.py" %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo StudyGuard stopped with return code: %ERRORLEVEL%
    pause
)
