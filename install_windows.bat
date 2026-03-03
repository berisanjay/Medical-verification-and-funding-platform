@echo off
REM Windows Installation Script for Medical Document Verification System
REM Run this as Administrator

echo ========================================
echo Medical Document Verification Setup
echo ========================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python found!

REM Check Node.js
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo Node.js found!

REM Check Tesseract
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Tesseract OCR not found in PATH
    echo Please install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo Default path: C:\Program Files\Tesseract-OCR\
    echo.
) else (
    echo Tesseract found!
)

REM Check Poppler
echo Checking Poppler...
pdftotext -v >nul 2>&1
if errorlevel 1 (
    echo WARNING: Poppler not found in PATH
    echo Please install from: https://github.com/oschwartz10612/poppler-windows/releases
    echo Add C:\poppler\Library\bin to PATH
    echo.
) else (
    echo Poppler found!
)

echo.
echo ========================================
echo Installing Flask Backend
echo ========================================
cd flask-backend

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python packages...
pip install -r requirements.txt

echo Downloading spaCy models...
python download_models.py

echo Creating .env file...
if not exist .env (
    copy .env.example .env
    echo .env file created from .env.example
    echo Please edit .env file with your settings
)

deactivate
cd ..

echo.
echo ========================================
echo Installing Node.js Backend
echo ========================================
cd node-backend

echo Installing Node packages...
call npm install

echo Creating .env file...
if not exist .env (
    copy .env.example .env
    echo .env file created from .env.example
)

cd ..

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start MongoDB (if using local MongoDB)
echo 2. Edit .env files in flask-backend and node-backend directories
echo 3. Run start_windows.bat to start all services
echo.
pause
