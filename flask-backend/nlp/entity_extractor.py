import spacy
import re

# Load models once (important for performance)
medical_nlp = spacy.load("en_ner_bc5cdr_md")
general_nlp = spacy.load("en_core_web_sm")


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

    # ---------- MEDICAL NER (DISEASE) ----------
    for ent in medical_nlp(text).ents:
        if ent.label_ == "DISEASE":
            clean = re.sub(r"[^a-zA-Z\s]", "", ent.text).strip().lower()
            if len(clean) > 3:
                entities["diseases"].append(clean)

    # Remove duplicates
    entities["diseases"] = list(set(entities["diseases"]))

    # ---------- GENERAL NER ----------
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

    for match in re.finditer(r"\b\d{1,3}(?:,\d{2,3})+\b", text):
        raw_amount = match.group()
        normalized = raw_amount.replace(",", "")

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
