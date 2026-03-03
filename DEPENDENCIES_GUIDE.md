# Medical Crowdfunding Platform - Dependencies Guide

## 🚀 Quick Installation

### Windows Users
Run this command in your project root:
```bash
install_complete.bat
```

### Linux/Mac Users
Run these commands in your project root:
```bash
chmod +x install_complete.sh
./install_complete.sh
```

## 📋 Manual Installation Steps

### 1. System Requirements

#### Python 3.8+
```bash
# Check if installed
python --version

# Install if needed
# Windows: Download from python.org
# Ubuntu: sudo apt-get install python3 python3-pip
# macOS: brew install python
```

#### Node.js 14+
```bash
# Check if installed
node --version
npm --version

# Install if needed
# Download from nodejs.org
# Ubuntu: sudo apt-get install nodejs npm
# macOS: brew install node
```

#### MongoDB
```bash
# Windows: Download and install from mongodb.com
# Ubuntu: sudo apt-get install mongodb
# macOS: brew install mongodb-community

# Start service
# Windows: net start MongoDB
# Linux: sudo systemctl start mongodb
# macOS: brew services start mongodb-community
```

#### Tesseract OCR
```bash
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Ubuntu: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract

# Add to PATH (Windows)
# C:\Program Files\Tesseract-OCR\
```

#### Poppler (PDF Support)
```bash
# Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases
# Ubuntu: sudo apt-get install poppler-utils
# macOS: brew install poppler

# Add to PATH (Windows)
# C:\poppler\Library\bin
```

### 2. Python Dependencies

```bash
cd flask-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install packages
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy models
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
```

### 3. Node.js Dependencies

```bash
cd node-backend
npm install
```

### 4. Environment Configuration

#### Flask Backend (.env)
```env
FLASK_ENV=development
MONGO_URI=mongodb://localhost:27017/
DB_NAME=medical_crowdfunding
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
STRIPE_SECRET_KEY=sk_test_your-stripe-test-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=Medical Crowdfunding Platform
```

#### Node.js Backend (.env)
```env
PORT=3000
FLASK_API_URL=http://127.0.0.1:5000
```

## 🔧 Detailed Package List

### Python Packages (requirements.txt)

#### Core Framework
- **Flask==3.0.0** - Web framework
- **flask-cors==4.0.0** - Cross-origin resource sharing
- **flask-jwt-extended==4.6.0** - JWT authentication
- **Werkzeug==3.0.1** - WSGI utilities

#### AI/ML & NLP
- **transformers==4.36.0** - BERT and transformer models
- **torch==2.1.0** - PyTorch deep learning framework
- **spacy==3.7.2** - Natural language processing
- **scispacy==0.5.4** - Medical NLP models

#### OCR & Document Processing
- **pytesseract==0.3.10** - Tesseract OCR wrapper
- **pdf2image==1.17.0** - PDF to image conversion
- **Pillow==10.1.0** - Image processing

#### Database
- **pymongo==4.6.1** - MongoDB driver

#### Security & Authentication
- **bcrypt==4.1.2** - Password hashing

#### Payments & Notifications
- **stripe==7.6.0** - Stripe payment processing
- **flask-mail==0.9.1** - Email sending

#### Utilities
- **python-dotenv==1.0.0** - Environment variables
- **python-dateutil==2.8.2** - Date utilities
- **marshmallow==3.20.1** - Data validation

### Node.js Packages (package.json)

#### Core Framework
- **express==4.18.2** - Web framework
- **cors==2.8.5** - Cross-origin resource sharing
- **dotenv==16.3.1** - Environment variables

#### File Handling
- **multer==1.4.5-lts.1** - File upload handling

#### HTTP Client
- **axios==1.6.2** - HTTP requests
- **form-data==4.0.0** - Form data handling

#### Development
- **nodemon==3.0.2** - Auto-restart development server

## 🧪 Verification Commands

### Test Python Installation
```bash
cd flask-backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -c "import flask, spacy, torch, transformers, pymongo; print('All Python packages OK!')"
```

### Test Node.js Installation
```bash
cd node-backend
npm test  # or just run npm start to test
```

### Test System Dependencies
```bash
# Test Tesseract
tesseract --version

# Test Poppler
pdftotext -v

# Test MongoDB
mongod --version
```

## 🚨 Common Issues & Solutions

### Issue: "Tesseract not found"
**Solution**: Add Tesseract to system PATH
- Windows: `C:\Program Files\Tesseract-OCR\`
- Linux: Usually in PATH after installation
- macOS: Usually in PATH after brew install

### Issue: "Poppler not found"
**Solution**: Add Poppler to system PATH
- Windows: `C:\poppler\Library\bin`
- Linux/Mac: Usually in PATH after installation

### Issue: "MongoDB connection failed"
**Solution**: Start MongoDB service
- Windows: `net start MongoDB`
- Linux: `sudo systemctl start mongodb`
- macOS: `brew services start mongodb-community`

### Issue: "spaCy model not found"
**Solution**: Download models
```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
```

### Issue: "BERT model download fails"
**Solution**: Check internet connection and try again
```python
# Test BERT download
from transformers import AutoTokenizer, AutoModelForSequenceClassification
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
```

## 🎯 After Installation

1. **Start MongoDB service**
2. **Configure .env files** with your API keys
3. **Run the platform**:
   ```bash
   # Terminal 1: Flask Backend
   cd flask-backend
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python app.py
   
   # Terminal 2: Node.js Backend
   cd node-backend
   npm start
   
   # Browser
   open http://localhost:3000/crowdfunding.html
   ```

Your medical crowdfunding platform will be ready to use! 🏥💙
