Medical Document Verification & Crowdfunding Fraud Detection

A full-stack medical document verification system that uses OCR + NLP + rule-based & risk-based validation to verify medical documents submitted for crowdfunding or insurance claims.

This project detects missing medical details, inconsistencies across documents, and potential fraud by analyzing uploaded images and PDFs.

🚀 Features
✅ Multi-Document Upload

Upload multiple medical documents at once

Supports Images (JPG, PNG, WEBP) and PDFs

🧠 Intelligent Extraction (OCR + NLP)

Extracts:

Patient Name

Doctor Name

Hospital Name

Hospital Pincode

Diseases

Treatment Dates

Estimated / Payable Amount

Uses:

Tesseract OCR

spaCy + SciSpacy medical NER

🔍 Mandatory Field Enforcement

Verification fails early if mandatory fields are missing:

Patient name

Disease

Date

Hospital (name or pincode)

Amount

⚠️ Cross-Document Fraud Detection

Patient name mismatch

Conflicting dates

Missing hospital details

Risk-based scoring system:

VERIFIED

NEEDS_CLARIFICATION

HIGH_RISK

🌐 Frontend JSON Viewer

Simple browser UI

Displays live verification JSON response

Alerts user when mandatory fields are missing

🏗️ Architecture
Frontend (HTML + JS)
        |
        v
Node.js (Express + Multer)
        |
        v
Flask API (OCR + NLP + Validation)

📂 Project Structure
medical-crowdfunding-verification/
├── flask-backend/
│   ├── app.py
│   ├── nlp/
│   │   └── entity_extractor.py
│   ├── ocr/
│   │   └── pdf_ocr.py
│   ├── validation/
│   │   └── cross_document.py
│   └── requirements.txt
│
├── node_backend/
│   ├── server.js
│   ├── package.json
│   └── uploads/
│
├── frontend/
│   └── public/
│       └── index.html
│
└── README.md

🛠️ Tech Stack
Backend

Python (Flask)

spaCy & SciSpacy

Tesseract OCR

Poppler (PDF support)

Node Layer

Node.js

Express

Multer

Axios

Frontend

HTML + Vanilla JavaScript

⚙️ Installation & Setup (Windows)
1️⃣ Clone Repository
git clone https://github.com/berisanjay/medical_verification_and_crowdfunding.git
cd medical-crowdfunding-verification

2️⃣ Install Tesseract OCR

Download:
https://github.com/UB-Mannheim/tesseract/wiki

Install to:

C:\Program Files\Tesseract-OCR\

3️⃣ Install Poppler (PDF Support)

Download Release zip from:
https://github.com/oschwartz10612/poppler-windows/releases

Extract to:

C:\poppler\


Add to PATH:

C:\poppler\Library\bin


Verify:

pdftotext -v

4️⃣ Flask Backend Setup
cd flask-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py


Flask runs on:

http://127.0.0.1:5000

5️⃣ Node Backend Setup
cd node_backend
npm install
node server.js


Node runs on:

http://localhost:3000

6️⃣ Run Frontend

Open in browser:

frontend/public/index.html

🔄 API Flow
Upload Documents

POST

/upload

Flask Verification Endpoint

POST

/verify

Sample Response
{
  "final_status": "VERIFIED",
  "cross_document_issues": [],
  "documents": [
    {
      "document_type": "ESTIMATE",
      "entities": {
        "patient_name": "Suresh Kumar",
        "hospital_name": "Yashoda Hospitals",
        "amount": "4,95,000",
        "diseases": ["angioplasty"]
      },
      "issues": []
    }
  ]
}

🧪 Use Cases

Medical crowdfunding platforms

Insurance claim verification

Hospital billing validation

Fraud detection systems

📌 Future Enhancements

Hospital database validation using pincode

Duplicate claim detection

ML-based fraud scoring

Authentication & user roles

Cloud deployment (GCP / AWS)

👨‍💻 Author

Sanjay Beri
Final Year Engineering Project
📌 GitHub: https://github.com/berisanjay