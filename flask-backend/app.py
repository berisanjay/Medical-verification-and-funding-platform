from flask import Flask, request, jsonify
import os
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from nlp.entity_extractor import extract_entities
from validation.cross_document import cross_document_checks

# 🔹 Tesseract path (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 🔹 Poppler path (Windows)
POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"

app = Flask(__name__)

# ---------- OCR ----------
def run_ocr(path):
    """
    OCR for both IMAGE and PDF
    """
    text = ""

    if path.lower().endswith(".pdf"):
        pages = convert_from_path(path, dpi=300, poppler_path=POPPLER_PATH)
        for page in pages:
            text += pytesseract.image_to_string(page) + "\n"
    else:
        text = pytesseract.image_to_string(Image.open(path))

    return text


# ---------- DOCUMENT TYPE ----------
def detect_doc_type(text):
    t = text.lower()
    if "invoice" in t or "final bill" in t or "total amount" in t:
        return "FINAL_BILL"
    if "estimate" in t:
        return "ESTIMATE"
    if "prescription" in t or "rx" in t:
        return "PRESCRIPTION"
    if "check up" in t or "lab report" in t or "health report" in t:
        return "MEDICAL_REPORT"
    return "UNKNOWN"


# ---------- PER-DOCUMENT VALIDATION ----------
def validate(doc_type, ent):
    issues = []
    if doc_type in ["ESTIMATE", "FINAL_BILL"] and not ent["amount"]:
        issues.append("Amount missing")
    if not ent["patient_name"]:
        issues.append("Patient name missing")
    return issues


# ---------- GLOBAL MANDATORY CHECK ----------
def mandatory_check(aggregated):
    missing = []

    if not aggregated["patient_name"]:
        missing.append("patient_name")
    if not aggregated["diseases"]:
        missing.append("diseases")
    if not aggregated["dates"]:
        missing.append("dates")
    if not (aggregated["hospital_name"] or aggregated["hospital_pincode"]):
        missing.append("hospital")
    if not aggregated["amount"]:
        missing.append("amount")

    return missing


# ---------- API ----------
@app.route("/verify", methods=["POST"], strict_slashes=False)
def verify():
    files = request.files.getlist("documents")
    docs = []

    os.makedirs("temp", exist_ok=True)

    for f in files:
        path = os.path.join("temp", f.filename)
        f.save(path)

        try:
            text = run_ocr(path)
            entities = extract_entities(text)
            doc_type = detect_doc_type(text)
            issues = validate(doc_type, entities)

            docs.append({
                "document_type": doc_type,
                "entities": entities,
                "issues": issues
            })
        finally:
            if os.path.exists(path):
                os.remove(path)

    # -------- AGGREGATE ENTITIES --------
    aggregated = {
        "patient_name": None,
        "hospital_name": None,
        "hospital_pincode": None,
        "amount": None,
        "dates": set(),
        "diseases": set()
    }

    for d in docs:
        e = d["entities"]
        aggregated["patient_name"] = aggregated["patient_name"] or e["patient_name"]
        aggregated["hospital_name"] = aggregated["hospital_name"] or e["hospital_name"]
        aggregated["hospital_pincode"] = aggregated["hospital_pincode"] or e["hospital_pincode"]
        aggregated["amount"] = aggregated["amount"] or e["amount"]
        aggregated["dates"].update(e["dates"])
        aggregated["diseases"].update(e["diseases"])

    # -------- MANDATORY CHECK --------
    missing_fields = mandatory_check(aggregated)
    if missing_fields:
        return jsonify({
            "status": "MISSING_REQUIRED_FIELDS",
            "missing_fields": missing_fields,
            "message": "Upload documents containing all mandatory medical details"
        }), 400

    # -------- CROSS DOCUMENT CHECK --------
    cross_issues = cross_document_checks(docs)

    # -------- RISK SCORING --------
    risk_score = sum(len(d["issues"]) for d in docs)
    if cross_issues:
        risk_score += 2

    if risk_score == 0:
        status = "VERIFIED"
    elif risk_score <= 2:
        status = "NEEDS_CLARIFICATION"
    else:
        status = "HIGH_RISK"

    return jsonify({
        "final_status": status,
        "cross_document_issues": cross_issues,
        "documents": docs
    })


@app.route("/test")
def test():
    return jsonify({"status": "Flask API running"})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
