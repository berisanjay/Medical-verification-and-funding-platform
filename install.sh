#!/bin/bash
# Installation script for Linux/macOS
# Medical Document Verification System

set -e

echo "========================================"
echo "Medical Document Verification Setup"
echo "========================================"
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Install Python 3.8+ from https://www.python.org/downloads/"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

# Check Node.js
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Install Node.js from https://nodejs.org/"
    exit 1
fi
echo "✓ Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm is not installed"
    exit 1
fi
echo "✓ npm found: $(npm --version)"

# Check Tesseract
echo "Checking Tesseract OCR..."
if ! command -v tesseract &> /dev/null; then
    echo "⚠ WARNING: Tesseract OCR not found"
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
    echo "  macOS: brew install tesseract"
else
    echo "✓ Tesseract found: $(tesseract --version | head -n 1)"
fi

# Check Poppler
echo "Checking Poppler..."
if ! command -v pdftotext &> /dev/null; then
    echo "⚠ WARNING: Poppler not found"
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install poppler-utils"
    echo "  macOS: brew install poppler"
else
    echo "✓ Poppler found"
fi

# Check MongoDB
echo "Checking MongoDB..."
if ! command -v mongod &> /dev/null; then
    echo "⚠ WARNING: MongoDB not found"
    echo "Install from: https://www.mongodb.com/docs/manual/installation/"
else
    echo "✓ MongoDB found"
fi

echo ""
echo "========================================"
echo "Installing Flask Backend"
echo "========================================"
cd flask-backend

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Downloading spaCy models..."
python download_models.py

echo "Creating .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ .env file created from .env.example"
    echo "  Please edit .env file with your settings"
else
    echo "✓ .env file already exists"
fi

deactivate
cd ..

echo ""
echo "========================================"
echo "Installing Node.js Backend"
echo "========================================"
cd node-backend

echo "Installing Node packages..."
npm install

echo "Creating .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ .env file created from .env.example"
else
    echo "✓ .env file already exists"
fi

cd ..

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Start MongoDB (if using local MongoDB):"
echo "   sudo systemctl start mongodb  # Linux"
echo "   brew services start mongodb-community  # macOS"
echo ""
echo "2. Edit .env files in flask-backend/ and node-backend/"
echo ""
echo "3. Start the application:"
echo "   ./start.sh"
echo ""
