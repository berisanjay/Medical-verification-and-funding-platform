def detect_document_type(text):
    t = text.lower()

    if "invoice" in t or "total amount" in t:
        return "FINAL_BILL"
    elif "check up" in t or "health report" in t or "lab report" in t:
        return "MEDICAL_REPORT"

    else:
        return "UNKNOWN"

