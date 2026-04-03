import spacy
import re

# Load models once (important for performance)
try:
    medical_nlp = spacy.load("en_core_sci_sm")  # Use available medical model
except OSError:
    medical_nlp = None  # Fallback if model not available

try:
    general_nlp = spacy.load("en_core_web_sm")  # Use available general model
except OSError:
    general_nlp = None  # Fallback if model not available


def extract_entities(text):
    entities = {
        "patient_name": None,
        "doctor_name": None,
        "hospital_name": None,
        "hospital_pincode": None,
        "diseases": [],
        "amount": None,
        "dates": []
    }

    # Helper function to clean names
    def clean_name(name):
        if not name:
            return name
        # Remove everything after newline
        name = name.split('\n')[0].strip()
        # Remove everything after these junk words
        junk_words = ['SIGNATURE', 'Signature', 'Guardian', 
                      'Staff', 'Stamp', 'Date', 'Patient',
                      'Authorized', 'Acknowledgement', 'GUARDIAN']
        for j in junk_words:
            if j in name:
                name = name[:name.index(j)].strip()
        # Remove trailing punctuation and spaces
        name = name.strip('.,/\\-_ ')
        return name if name else None

    # ---------- MEDICAL NER (DISEASE) ----------
    # Try explicit diagnosis patterns first (higher priority)
    diag_patterns = [
        # Apollo estimate: "DIAGNOSIS\nTriple Vessel Coronary Artery Disease"
        r'DIAGNOSIS\s*\n\s*([A-Za-z][A-Za-z\s]{5,80}?)(?:\n|$)',
        # Inline: "Diagnosis: Triple Vessel..."
        r'Diagnosis\s*[:\-]\s*([A-Za-z][A-Za-z\s]{5,80}?)(?:\n|\.|$)',
        # "diagnosed with Triple Vessel..."
        r'diagnosed\s+(?:with|as)\s+([A-Za-z][A-Za-z\s]{5,80}?)(?:\n|\.|requiring)',
    ]
    for diag_pattern in diag_patterns:
        match = re.search(diag_pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            disease = match.group(1).strip()
            if len(disease) > 4 and disease.lower() not in ['details','n/a','none']:
                entities["diseases"].append(disease.title())
                break  # Found explicit diagnosis, stop searching
    
    # If no explicit diagnosis found, use NER fallback
    if not entities["diseases"] and medical_nlp:
        for ent in medical_nlp(text).ents:
            if ent.label_ == "DISEASE":
                clean = re.sub(r"[^a-zA-Z\s]", "", ent.text).strip().lower()
                if len(clean) > 3:
                    entities["diseases"].append(clean.title())

    # Remove duplicates
    entities["diseases"] = list(set(entities["diseases"]))

    # ---------- GENERAL NER ----------
    if general_nlp:
        for ent in general_nlp(text).ents:
            context = text[max(0, ent.start_char - 40): ent.start_char].lower()

            # PERSON
            if ent.label_ == "PERSON":
                name = ent.text.strip()

                # Doctor detection
                if re.search(r"\bdr\.?\b", context):
                    if not entities["doctor_name"]:
                        entities["doctor_name"] = name

                # Patient detection
                elif re.search(r"\bpatient\b|\bname\b", context):
                    name = re.sub(
                        r"\b(dob|age|yrs?|years?)\b.*",
                        "",
                        name,
                        flags=re.I
                    ).strip()
                    name = clean_name(name)  # Apply name cleaning

                    if not entities["patient_name"]:
                        entities["patient_name"] = name

            # DATE
            if ent.label_ == "DATE":
                clean_date = ent.text.strip()
                if clean_date not in entities["dates"]:
                    entities["dates"].append(clean_date)

    # ---------- HOSPITAL NAME ----------
    hospital = re.search(
        r"([A-Z][A-Za-z\s]{3,}(?:Hospital|Hospitals|Medical Center|Clinic|Institute))",
        text
    )
    if hospital:
        entities["hospital_name"] = hospital.group().strip()

    # ---------- PIN CODE ----------
    pin = re.search(r"\b\d{6}\b", text)
    if pin:
        entities["hospital_pincode"] = pin.group()

    # ---------- AMOUNT EXTRACTION (INDIAN FORMAT) ----------
    # ---------- AMOUNT EXTRACTION (FINAL PAYABLE PRIORITY) ----------
    amount_candidates = []

    # Priority 1: ESTIMATED TOTAL patterns first
    estimated_total_patterns = [
        # "ESTIMATED TOTAL (₹) 9,33,000.00"
        r'ESTIMATED\s+TOTAL\s*\([^)]*\)\s*([0-9,]+(?:\.[0-9]{2})?)',
        # "ESTIMATED TOTAL (₹)\n9,33,000.00" — newline between
        r'ESTIMATED\s+TOTAL[^\n]*\n\s*([0-9,]+(?:\.[0-9]{2})?)',
        # "ESTIMATED TOTAL 9,33,000"
        r'ESTIMATED\s+TOTAL[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
        # "TOTAL ESTIMATE 9,33,000"
        r'TOTAL\s+ESTIMATE[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
        # "TOTAL AMOUNT 9,33,000"  
        r'TOTAL\s+AMOUNT[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
    ]
    for pattern in estimated_total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1).replace(',', ''))
            if 10000 <= val <= 20000000:
                entities["amount"] = val
                break  # Found ESTIMATED TOTAL, stop searching

    # If no ESTIMATED TOTAL found, use fallback patterns
    if not entities["amount"]:
        for match in re.finditer(r"\b\d{1,3}(?:,\d{2,3})+\b", text):
            raw_amount = match.group()
            normalized = int(raw_amount.replace(",", ""))

            context = text[max(0, match.start() - 50): match.end() + 50].lower()
            score = 0

            # 🔥 STRONG PRIORITY (must win)
            if "estimated payable amount" in context:
                score += 10

            # Medium priority
            if "total estimated cost" in context or "total cost" in context:
                score += 6

            # LOW priority (should lose)
            if "additional charges" in context:
                score -= 5

            amount_candidates.append((score, normalized))

        if amount_candidates:
            amount_candidates.sort(reverse=True)
            entities["amount"] = amount_candidates[0][1]


    return entities
