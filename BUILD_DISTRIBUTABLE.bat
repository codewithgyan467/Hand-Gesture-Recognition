@echo off
title GestureOS — Build Distributable Package
cd /d "%~dp0"
cls
echo ======================================================================
echo                 GESTUREOS PRODUCTION PACKAGING TOOL
echo          Compiling standalone Windows distributable package
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/3] Verifying PyInstaller availability...
"%PYTHON_EXE%" -m pip install pyinstaller --quiet

echo [2/3] Building standalone executable with PyInstaller...
cd GestureOS
"%PYTHON_EXE%" -m PyInstaller --clean gestureos.spec
cd ..

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Packaging failed with code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo [3/3] Copying runtime folders and assets into dist/GestureOS...
if not exist "GestureOS\dist\GestureOS\models" mkdir "GestureOS\dist\GestureOS\models"
copy /y "GestureOS\models\hand_landmarker.task" "GestureOS\dist\GestureOS\models\" >nul

if not exist "GestureOS\dist\GestureOS\profiles" mkdir "GestureOS\dist\GestureOS\profiles"
copy /y "GestureOS\profiles\*.json" "GestureOS\dist\GestureOS\profiles\" >nul

copy /y "GestureOS\README.md" "GestureOS\dist\GestureOS\" >nul
copy /y "START_GESTUREOS.bat" "GestureOS\dist\GestureOS\" >nul
copy /y "START_SIMULATION_MODE.bat" "GestureOS\dist\GestureOS\" >nul

echo.
echo ======================================================================
echo [SUCCESS] GestureOS standalone distribution package is ready!
echo Output folder: %~dp0GestureOS\dist\GestureOS\
echo ======================================================================
echo.
pause
