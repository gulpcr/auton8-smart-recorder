@echo off
REM Quick launcher for Enhanced UI
REM Automatically activates venv and runs the app

echo.
echo ===============================================
echo   Test Recorder - Professional Edition
echo ===============================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set UTF-8 encoding
set PYTHONIOENCODING=utf-8

REM Run the enhanced app
echo Starting enhanced UI...
echo.
python -m recorder.app_enhanced

REM Deactivate on exit
deactivate
