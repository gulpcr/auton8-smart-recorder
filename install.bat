@echo off
REM Installation script for Call Intelligence System (Windows)

echo =============================================
echo Call Intelligence System - Installation
echo =============================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found

REM Create virtual environment
echo.
echo Creating virtual environment...
if not exist .venv (
    python -m venv .venv
    echo [OK] Virtual environment created
) else (
    echo [WARNING] Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo [OK] Virtual environment activated

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
echo [OK] pip upgraded

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Install Playwright browsers
echo.
echo Installing Playwright browsers...
python -m playwright install
echo [OK] Playwright browsers installed

REM Check Tesseract
echo.
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Tesseract not found
    echo Please download and install from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo Add to PATH: C:\Program Files\Tesseract-OCR
) else (
    echo [OK] Tesseract found
)

REM Download spaCy model
echo.
echo Downloading spaCy language model...
python -m spacy download en_core_web_sm
echo [OK] spaCy model downloaded

REM Create data directories
echo.
echo Creating data directories...
if not exist data\workflows mkdir data\workflows
if not exist data\screenshots mkdir data\screenshots
if not exist data\knowledge_base mkdir data\knowledge_base
if not exist data\rag_index mkdir data\rag_index
if not exist data\uploads mkdir data\uploads
if not exist models mkdir models
echo [OK] Data directories created

REM Optional: Download LLM model
echo.
set /p download_llm="Would you like to download a local LLM model? (y/n): "
if /i "%download_llm%"=="y" (
    echo.
    echo Downloading Llama 2 7B Chat (Q4_K_M, ~4GB^)...
    echo This may take several minutes...
    
    pip install huggingface-hub
    
    if not exist %USERPROFILE%\models mkdir %USERPROFILE%\models
    
    python -c "from huggingface_hub import hf_hub_download; import os; model_path = hf_hub_download(repo_id='TheBloke/Llama-2-7B-Chat-GGUF', filename='llama-2-7b-chat.Q4_K_M.gguf', local_dir=os.path.expanduser('~/models')); print(f'Model downloaded to: {model_path}')"
    
    echo [OK] LLM model downloaded
) else (
    echo [WARNING] Skipped LLM model download
    echo You can download manually later from:
    echo https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
)

REM Installation complete
echo.
echo =============================================
echo Installation Complete!
echo =============================================
echo.
echo To get started:
echo   1. Activate virtual environment: .venv\Scripts\activate.bat
echo   2. Run desktop app: python -m recorder.app_ml_integrated
echo   3. Or run API server: python -m uvicorn recorder.api.main:app --host 0.0.0.0 --port 8000
echo.
echo Documentation: README_PRODUCTION.md
echo API Docs: http://localhost:8000/docs (after starting API)
echo.

pause
