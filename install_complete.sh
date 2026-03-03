#!/bin/bash

echo "========================================"
echo "Medical Crowdfunding Platform - Setup"
echo "========================================"
echo

echo "[1/6] Installing Python dependencies..."
cd "$(dirname "$0")/flask-backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "[2/6] Downloading spaCy models..."
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm

echo
echo "[3/6] Installing Node.js dependencies..."
cd "$(dirname "$0")/node-backend"
npm install

echo
echo "[4/6] Checking system requirements..."

echo "Checking MongoDB..."
if command -v mongod &> /dev/null; then
    echo "MongoDB found: OK"
else
    echo "WARNING: MongoDB not found"
    echo "Please install MongoDB:"
    echo "  Ubuntu/Debian: sudo apt-get install mongodb"
    echo "  macOS: brew install mongodb-community"
    echo "  And start the service"
fi

echo
echo "Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo "Tesseract OCR found: OK"
else
    echo "WARNING: Tesseract OCR not found"
    echo "Please install Tesseract:"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
    echo "  macOS: brew install tesseract"
fi

echo
echo "Checking Poppler..."
if command -v pdftotext &> /dev/null; then
    echo "Poppler found: OK"
else
    echo "WARNING: Poppler not found"
    echo "Please install Poppler:"
    echo "  Ubuntu/Debian: sudo apt-get install poppler-utils"
    echo "  macOS: brew install poppler"
fi

echo
echo "[5/6] Creating environment files..."
cd "$(dirname "$0")/flask-backend"
if [ ! -f ".env" ]; then
    echo "Creating Flask .env file..."
    cp .env.example .env
    echo "Please edit flask-backend/.env with your configuration"
fi

cd "$(dirname "$0")/node-backend"
if [ ! -f ".env" ]; then
    echo "Creating Node.js .env file..."
    cp .env.example .env
    echo "Please edit node-backend/.env with your configuration"
fi

echo
echo "[6/6] Setup complete!"
echo
echo "========================================"
echo "NEXT STEPS:"
echo "========================================"
echo "1. Start MongoDB service"
echo "2. Configure your .env files with:"
echo "   - MongoDB connection string"
echo "   - JWT secret key"
echo "   - Stripe API keys (for payments)"
echo "   - Email settings (for notifications)"
echo
echo "3. Run the platform:"
echo "   - Terminal 1: cd flask-backend && source venv/bin/activate && python app.py"
echo "   - Terminal 2: cd node-backend && npm start"
echo "   - Browser: http://localhost:3000/crowdfunding.html"
echo
echo "========================================"
