# Medical Document Verification & Crowdfunding Fraud Detection

A full-stack medical document verification system that uses **OCR + NLP + Rule-based & Risk-based validation** to verify medical documents submitted for crowdfunding or insurance claims.

This project detects missing medical details, inconsistencies across documents, and potential fraud by analyzing uploaded images and PDFs.

---

## 🚀 Features

✅ **Multi-Document Upload**
- Upload multiple medical documents at once
- Supports Images (JPG, PNG, WEBP) and PDFs

🧠 **Intelligent Extraction (OCR + NLP)**
- Extracts:
  - Patient Name
  - Doctor Name
  - Hospital Name & Pincode
  - Diseases
  - Treatment Dates
  - Estimated/Payable Amount
- Uses:
  - Tesseract OCR
  - spaCy + SciSpacy medical NER

🔍 **Mandatory Field Enforcement**
- Verification fails early if mandatory fields are missing:
  - Patient name
  - Disease
  - Date
  - Hospital (name or pincode)
  - Amount

⚠️ **Cross-Document Fraud Detection**
- Patient name mismatch
- Conflicting dates
- Missing hospital details
- Bill exceeding estimate
- Risk-based scoring system:
  - ✅ VERIFIED
  - ⚠️ NEEDS_CLARIFICATION
  - 🚨 HIGH_RISK

🌐 **Frontend JSON Viewer**
- Modern, responsive UI
- Displays live verification JSON response
- Alerts user when mandatory fields are missing

💾 **MongoDB Integration**
- Stores all verification results
- Query past verifications
- Track verification history

---

## 🏗️ Architecture

```
Frontend (HTML + JS)
        ↓
Node.js (Express + Multer)
        ↓
Flask API (OCR + NLP + Validation)
        ↓
MongoDB (Data Storage)
```

---

## 📂 Project Structure

```
medical-crowdfunding-verification/
├── flask-backend/
│   ├── app.py                    # Main Flask application
│   ├── nlp/
│   │   └── entity_extractor.py   # Medical entity extraction
│   ├── ocr/
│   │   └── pdf_ocr.py            # OCR processing
│   ├── validation/
│   │   └── cross_document.py     # Cross-document validation
│   ├── requirements.txt          # Python dependencies
│   └── .env.example             # Environment configuration
│
├── node-backend/
│   ├── server.js                 # Express server
│   ├── package.json              # Node dependencies
│   └── .env.example             # Environment configuration
│
├── frontend/
│   └── public/
│       └── index.html           # Web interface
│
├── docs/
│   ├── API.md                   # API documentation
│   └── DEPLOYMENT.md            # Deployment guide
│
└── README.md                     # This file
```

---

## 🛠️ Tech Stack

### Backend
- **Python (Flask)** - Main API server
- **spaCy & SciSpacy** - Medical NLP
- **Tesseract OCR** - Text extraction
- **Poppler** - PDF processing
- **MongoDB** - Data persistence

### Node Layer
- **Node.js** - File upload handling
- **Express** - Web framework
- **Multer** - Multipart form data
- **Axios** - HTTP client

### Frontend
- **HTML + Vanilla JavaScript** - Clean, lightweight UI
- **No frameworks** - Pure web technologies

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 14+
- MongoDB (local or cloud)
- Tesseract OCR
- Poppler (for PDF support)

### 1️⃣ Clone Repository
```bash
git clone https://github.com/yourusername/medical-verification.git
cd medical-crowdfunding-verification
```

### 2️⃣ Install Tesseract OCR

#### Windows
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR\`
3. Add to PATH

#### Linux
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### macOS
```bash
brew install tesseract
```

### 3️⃣ Install Poppler (PDF Support)

#### Windows
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to: `C:\poppler\`
3. Add `C:\poppler\Library\bin` to PATH

Verify installation:
```bash
pdftotext -v
```

#### Linux
```bash
sudo apt-get install poppler-utils
```

#### macOS
```bash
brew install poppler
```

### 4️⃣ Install MongoDB

#### Windows
Download and install from: https://www.mongodb.com/try/download/community

#### Linux
```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

#### macOS
```bash
brew install mongodb-community
brew services start mongodb-community
```

### 5️⃣ Flask Backend Setup

```bash
cd flask-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy models
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run Flask server
python app.py
```

Flask runs on: **http://127.0.0.1:5000**

### 6️⃣ Node Backend Setup

```bash
cd node-backend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit .env if needed

# Run Node server
npm start
```

Node runs on: **http://localhost:3000**

### 7️⃣ Run Frontend

Simply open in browser:
```bash
cd frontend/public
# Open index.html in your browser
# Or use a local server:
python -m http.server 8080
```

Frontend available at: **http://localhost:8080**

---

## 🔄 API Flow

1. **Upload Documents** → `POST /upload` (Node.js)
2. **Forward to Flask** → `POST /verify` (Flask API)
3. **OCR Processing** → Extract text from PDFs/Images
4. **NLP Extraction** → Extract medical entities
5. **Validation** → Check mandatory fields
6. **Cross-Document Analysis** → Detect inconsistencies
7. **Risk Scoring** → Calculate final status
8. **Store in MongoDB** → Save verification results
9. **Return Results** → JSON response to frontend

---

## 📊 Sample Response

```json
{
  "final_status": "VERIFIED",
  "risk_score": 15,
  "total_documents": 2,
  "processed_documents": 2,
  "cross_document_issues": [],
  "documents": [
    {
      "filename": "estimate.pdf",
      "document_type": "ESTIMATE",
      "entities": {
        "patient_name": "Suresh Kumar",
        "doctor_name": "Dr. Rajesh Sharma",
        "hospital_name": "Yashoda Hospitals",
        "hospital_pincode": "500082",
        "diseases": ["Angioplasty", "Coronary Artery Disease"],
        "date": "15/01/2024",
        "amount": "4,95,000"
      },
      "issues": []
    }
  ],
  "verification_id": "65abc123def456",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

---

## 🧪 Use Cases

- Medical crowdfunding platforms (Ketto, Milaap)
- Insurance claim verification
- Hospital billing validation
- Fraud detection systems
- Healthcare compliance

---

## 📌 Future Enhancements

- [ ] Hospital database validation using pincode
- [ ] Duplicate claim detection
- [ ] ML-based fraud scoring (TensorFlow/PyTorch)
- [ ] Authentication & user roles (JWT)
- [ ] Cloud deployment (AWS/GCP/Azure)
- [ ] Real-time notifications
- [ ] Blockchain verification trail
- [ ] Mobile app (React Native)

---

## 🐛 Troubleshooting

### Tesseract not found
```bash
# Windows: Add to PATH
C:\Program Files\Tesseract-OCR\

# Or set in code
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Poppler not found
```bash
# Windows: Add to PATH
C:\poppler\Library\bin

# Or use in code
convert_from_path(pdf_path, poppler_path=r'C:\poppler\Library\bin')
```

### MongoDB connection failed
```bash
# Check if MongoDB is running
# Windows:
net start MongoDB

# Linux:
sudo systemctl status mongodb
```

### spaCy model not found
```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
```

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

## 🙏 Acknowledgments

- Tesseract OCR Team
- spaCy & SciSpacy developers
- Flask & Express communities
- MongoDB team

---

**Built with ❤️ for healthcare transparency**
