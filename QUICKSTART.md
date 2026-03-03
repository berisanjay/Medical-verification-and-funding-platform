# Medical Document Verification - Quick Start Guide

## 🎯 What This System Does

This is a **production-ready** medical document verification system that:
- ✅ Extracts information from medical documents using OCR
- 🧠 Uses AI/NLP to identify patient names, diseases, amounts, hospitals, etc.
- 🔍 Detects fraud by comparing multiple documents
- ⚠️ Flags inconsistencies and missing information
- 💾 Stores verification results in MongoDB
- 🌐 Provides a beautiful web interface

## 🚀 Quick Start (Windows)

### 1. Prerequisites
Install these first:
- **Python 3.8+**: https://www.python.org/downloads/
- **Node.js 14+**: https://nodejs.org/
- **Tesseract OCR**: https://github.com/UB-Mannheim/tesseract/wiki
- **Poppler**: https://github.com/oschwartz10612/poppler-windows/releases
- **MongoDB**: https://www.mongodb.com/try/download/community

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd medical-crowdfunding-verification

# Run installation script
install_windows.bat
```

### 3. Start the System
```bash
start_windows.bat
```

This opens 4 windows:
1. MongoDB server
2. Flask API (Python backend)
3. Node.js server
4. Your web browser with the application

### 4. Use the Application
1. Open http://localhost:3000 in your browser
2. Upload medical documents (PDF or images)
3. Click "Verify Documents"
4. View verification results

## 🚀 Quick Start (Linux/Mac)

### 1. Prerequisites
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip nodejs npm tesseract-ocr poppler-utils mongodb

# macOS
brew install python node tesseract poppler mongodb-community
```

### 2. Installation
```bash
# Clone and install
git clone <your-repo-url>
cd medical-crowdfunding-verification
chmod +x install.sh
./install.sh
```

### 3. Start the System
```bash
chmod +x start.sh
./start.sh
```

## 📁 Project Structure

```
medical-crowdfunding-verification/
│
├── flask-backend/              # Python/Flask API
│   ├── app.py                 # Main API server
│   ├── nlp/                   # Medical entity extraction
│   ├── ocr/                   # Document OCR processing
│   └── validation/            # Fraud detection logic
│
├── node-backend/              # Node.js file upload server
│   └── server.js             # Express server
│
├── frontend/                  # Web interface
│   └── public/
│       └── index.html        # Single-page application
│
└── docs/                      # Documentation
    ├── API.md                # API reference
    ├── DEPLOYMENT.md         # Production deployment guide
    └── TEST_DOCUMENTS.md     # How to create test documents
```

## 🔧 How It Works

### 1. Document Upload
User uploads medical documents through the web interface

### 2. OCR Processing
- Tesseract extracts text from PDFs and images
- Handles multiple pages
- Works with scanned documents

### 3. NLP Entity Extraction
spaCy + SciSpacy extract:
- Patient name
- Doctor name
- Hospital name & pincode
- Diseases/diagnoses
- Treatment dates
- Medical costs

### 4. Validation
Checks for:
- **Mandatory fields**: Patient, disease, date, hospital, amount
- **Patient name consistency** across documents
- **Hospital consistency**
- **Date logic** (no future dates, reasonable ranges)
- **Amount logic** (bill shouldn't exceed estimate)

### 5. Risk Scoring
Calculates risk score 0-100:
- **0-29**: ✅ VERIFIED
- **30-69**: ⚠️ NEEDS CLARIFICATION
- **70-100**: 🚨 HIGH RISK

### 6. Storage
Saves results to MongoDB for future reference

## 📊 Sample Output

```json
{
  "final_status": "VERIFIED",
  "risk_score": 15,
  "total_documents": 2,
  "cross_document_issues": [],
  "documents": [
    {
      "filename": "estimate.pdf",
      "document_type": "ESTIMATE",
      "entities": {
        "patient_name": "Suresh Kumar",
        "hospital_name": "Yashoda Hospitals",
        "diseases": ["Angioplasty"],
        "amount": "4,95,000"
      },
      "issues": []
    }
  ]
}
```

## 🛠️ Configuration

### Flask Backend (.env)
```env
FLASK_ENV=development
MONGO_URI=mongodb://localhost:27017/
DB_NAME=medical_verification
```

### Node Backend (.env)
```env
PORT=3000
FLASK_API_URL=http://127.0.0.1:5000
```

## 🧪 Testing

### Test with Sample Documents
1. Create a medical estimate PDF with:
   - Patient name, hospital, diagnosis, amount, date
2. Create a medical bill PDF with:
   - Same patient, hospital
   - Different amount
3. Upload both and verify

### Expected Results
- System should extract all entities
- Cross-validate patient names
- Compare amounts
- Generate risk score

## 🌐 API Endpoints

### Node.js (Port 3000)
- `POST /upload` - Upload and verify documents
- `GET /verification/:id` - Get verification by ID
- `GET /verifications` - List all verifications
- `GET /health` - Health check

### Flask (Port 5000)
- `POST /verify` - Verify documents
- `GET /health` - Health check

## 🔐 Security Features

- ✅ File type validation
- ✅ File size limits (50MB)
- ✅ Input sanitization
- ✅ CORS protection
- 🔜 Authentication (JWT) - coming soon
- 🔜 Rate limiting - coming soon

## 📈 Future Enhancements

- [ ] Hospital database integration
- [ ] Duplicate claim detection
- [ ] ML-based fraud scoring
- [ ] User authentication & roles
- [ ] Real-time notifications
- [ ] Mobile app
- [ ] Cloud deployment templates

## 🐛 Common Issues

### "Tesseract not found"
Add to PATH: `C:\Program Files\Tesseract-OCR\`

### "Poppler not found"
Add to PATH: `C:\poppler\Library\bin`

### "MongoDB connection failed"
Start MongoDB:
- Windows: `net start MongoDB`
- Linux: `sudo systemctl start mongodb`
- Mac: `brew services start mongodb-community`

### "spaCy model not found"
```bash
cd flask-backend
source venv/bin/activate
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
```

## 📚 Documentation

- **README.md**: Full documentation
- **docs/API.md**: Complete API reference
- **docs/DEPLOYMENT.md**: Production deployment guide
- **docs/TEST_DOCUMENTS.md**: Creating test documents

## 💡 Use Cases

1. **Medical Crowdfunding Platforms**
   - Verify documents before campaign approval
   - Detect duplicate/fraudulent claims

2. **Insurance Companies**
   - Validate medical bills
   - Cross-check estimates and bills

3. **Hospitals**
   - Validate billing consistency
   - Audit medical records

4. **Healthcare Regulators**
   - Monitor fraud patterns
   - Ensure compliance

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

- GitHub Issues: Report bugs or request features
- Documentation: Check docs/ folder
- Email: [Your contact]

## 📄 License

MIT License - See LICENSE file

---

**Built with ❤️ for healthcare transparency and fraud prevention**

---

## 🎓 Learning Resources

### For Beginners
- Flask Tutorial: https://flask.palletsprojects.com/
- Express.js Guide: https://expressjs.com/
- MongoDB Basics: https://university.mongodb.com/

### Advanced Topics
- spaCy Documentation: https://spacy.io/
- Tesseract OCR Guide: https://tesseract-ocr.github.io/
- Medical NLP: Research papers on SciSpacy

---

**Version**: 1.0.0
**Last Updated**: January 2024
