@echo off
echo ========================================
echo Medical Crowdfunding Platform - Setup
echo ========================================
echo.

echo [1/6] Installing Python dependencies...
cd /d "%~dp0flask-backend"

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing Python packages...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [2/6] Downloading spaCy models...
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm

echo.
echo [3/6] Installing Node.js dependencies...
cd /d "%~dp0node-backend"
npm install

echo.
echo [4/6] Checking system requirements...
echo Checking MongoDB...
mongod --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: MongoDB not found in PATH
    echo Please install MongoDB from: https://www.mongodb.com/try/download/community
    echo And add it to your system PATH
) else (
    echo MongoDB found: OK
)

echo.
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Tesseract OCR not found in PATH
    echo Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
    echo And add it to your system PATH
) else (
    echo Tesseract OCR found: OK
)

echo.
echo Checking Poppler...
pdftotext -v >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Poppler not found in PATH
    echo Please install Poppler from: https://github.com/oschwartz10612/poppler-windows/releases
    echo And add C:\poppler\Library\bin to your system PATH
) else (
    echo Poppler found: OK
)

echo.
echo [5/6] Creating environment files...
cd /d "%~dp0flask-backend"
if not exist ".env" (
    echo Creating Flask .env file...
    copy .env.example .env
    echo Please edit flask-backend\.env with your configuration
)

cd /d "%~dp0node-backend"
if not exist ".env" (
    echo Creating Node.js .env file...
    copy .env.example .env
    echo Please edit node-backend\.env with your configuration
)

echo.
echo [6/6] Setup complete!
echo.
echo ========================================
echo NEXT STEPS:
echo ========================================
echo 1. Start MongoDB service
echo 2. Configure your .env files with:
echo    - MongoDB connection string
echo    - JWT secret key
echo    - Stripe API keys (for payments)
echo    - Email settings (for notifications)
echo.
echo 3. Run the platform:
echo    - Terminal 1: cd flask-backend && venv\Scripts\activate && python app.py
echo    - Terminal 2: cd node-backend && npm start
echo    - Browser: http://localhost:3000/crowdfunding.html
echo.
echo ========================================
pause
