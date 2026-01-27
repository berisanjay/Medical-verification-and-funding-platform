def validate_document(doc_type, entities):
    issues = []

    if not entities["patient_name"]:
        issues.append("Patient name missing")

    if not entities["hospital_name"]:
        issues.append("Hospital name missing")

    if doc_type in ["ESTIMATE", "FINAL_BILL"] and not entities["amount"]:
        issues.append("Amount missing in billing document")

    return issues
