"""
Medical Entity Extraction using spaCy and SciSpacy
Fixed for Indian medical documents:
- Apollo Hospitals estimate format
- Aadhaar card format
- Income certificate format
"""
import spacy
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MedicalEntityExtractor:
    """Extract medical entities from text using NLP"""

    def __init__(self):
        try:
            try:
                self.nlp = spacy.load("en_core_sci_sm")
                logger.info("Loaded SciSpacy medical model")
            except:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded standard spaCy model")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise

        self.medical_terms = [
            'diabetes', 'hypertension', 'cancer', 'tuberculosis', 'pneumonia',
            'asthma', 'arthritis', 'angioplasty', 'bypass', 'surgery',
            'fracture', 'infection', 'fever', 'covid', 'malaria', 'dengue',
            'heart attack', 'stroke', 'kidney', 'liver', 'appendicitis',
            'coronary', 'cardiac', 'myocardial', 'infarction', 'stent',
            'chemotherapy', 'dialysis', 'transplant', 'icu', 'emergency',
            'bypass surgery', 'open heart surgery', 'knee replacement',
            'hip replacement', 'cataract', 'glaucoma',
            'thyroid', 'ulcer', 'migraine', 'paralysis', 'epilepsy',
            'vessel', 'coronary artery', 'cabg', 'triple vessel',
            'triple vessel coronary', 'coronary artery disease',
            'coronary artery disease', 'heart failure', 'valve',
            'thalassemia', 'hemophilia', 'sickle cell', 'dengue fever',
        ]

        # Words that are definitely NOT patient names
        self.name_blacklist = [
            'hospital', 'medical', 'clinic', 'india', 'estimate', 'government',
            'certificate', 'address', 'district', 'doctor', 'admission',
            'consultant', 'details', 'procedure', 'service', 'fee', 'charges',
            'apollo', 'fortis', 'yashoda', 'narayana', 'unique', 'authority',
            'registration', 'enrolment', 'information', 'aadhaar', 'aadhar',
            'waltair', 'visakhapatnam', 'andhra', 'pradesh', 'revenue',
            'department', 'tahsildar', 'mandal', 'village', 'ward',
        ]

    def extract_entities(self, text):
        entities = {
            'patient_name'    : None,
            'doctor_name'     : None,
            'hospital_name'   : None,
            'hospital_pincode': None,
            'diseases'        : [],
            'date'            : None,
            'amount'          : None
        }

        doc = self.nlp(text)
        persons = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']
        orgs    = [ent.text for ent in doc.ents if ent.label_ == 'ORG']

        entities['patient_name']     = self._extract_patient_name(text, persons)
        entities['doctor_name']      = self._extract_doctor_name(text, persons)
        entities['hospital_name']    = self._extract_hospital_name(text, orgs)
        entities['hospital_pincode'] = self._extract_pincode(text)
        entities['diseases']         = self._extract_diseases(text, doc)
        entities['date']             = self._extract_date(text, doc)
        entities['amount']           = self._extract_amount(text)

        logger.info(f"Extracted entities: {entities}")
        return entities

    # ── PATIENT NAME ──────────────────────────────────────────────────────────
    def _extract_patient_name(self, text, persons):
        """
        Extract patient name. Handles:
        1. Apollo estimate: PATIENT'S NAME\nGollapati Jesse Jasper
        2. Aadhaar: Name printed after VID line
        3. Income cert: ...H/o GOLLAPATI JESSE JASPER resident of...
        """

        # ── Priority 1: Explicit label on NEXT LINE (Apollo estimate) ─────────
        # "PATIENT'S NAME\nGollapati Jesse Jasper"
        match = re.search(
            r"PATIENT'S\s+NAME\s*\n\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            text, re.MULTILINE
        )
        if match:
            name = match.group(1).strip()
            if self._valid_name(name):
                return name

        # ── Priority 2: "Patient Name: ..." inline format ────────────────────
        match = re.search(
            r"Patient(?:'s)?\s+Name[\s:\-]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            text, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            if self._valid_name(name):
                return name

        # ── Priority 3: Income certificate format ────────────────────────────
        # "Sri/Srimathi/Kumari JOHN WESLEY F/o / M/o / H/o GOLLAPATI JESSE JASPER"
        match = re.search(
            r'(?:F/o|M/o|H/o|W/o)\s+([A-Z][A-Z\s]+?)(?:\s+resident|\s+of\b|\s+R/o)',
            text, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip().title()
            if self._valid_name(name) and len(name.split()) >= 2:
                return name

        # ── Priority 4: Name of Patient ───────────────────────────────────────
        match = re.search(
            r'Name\s+of\s+(?:the\s+)?[Pp]atient[\s:\-]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})',
            text, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            if self._valid_name(name):
                return name

        # ── Priority 5: Aadhaar — name before DOB line ───────────────────────
        # "Gollapati Jesse Jasper\nDOB: 06/11/2004"
        match = re.search(
            r'^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s*\n\s*(?:DOB|Date\s+of\s+Birth|पुट्टिन)',
            text, re.MULTILINE | re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            if self._valid_name(name):
                return name

        # ── Priority 6: SpaCy PERSON — longest valid name ────────────────────
        for person in sorted(persons, key=len, reverse=True):
            if len(person.split()) >= 2 and len(person) >= 6:
                if self._valid_name(person):
                    return person

        return None

    def _valid_name(self, name):
        """Check if extracted text is a valid person name"""
        if not name or len(name) < 4:
            return False
        name_lower = name.lower()
        # Reject if contains blacklisted words
        if any(bad in name_lower for bad in self.name_blacklist):
            return False
        # Reject if more than 5 words (too long for a name)
        if len(name.split()) > 5:
            return False
        # Reject if contains digits
        if re.search(r'\d', name):
            return False
        return True

    # ── DOCTOR NAME ───────────────────────────────────────────────────────────
    def _extract_doctor_name(self, text, persons):
        patterns = [
            # "CONSULTANT DOCTOR\nDr. R. Srinivas Rao"
            r'CONSULTANT\s+DOCTOR\s*\n\s*(?:Dr\.?\s+)?([A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+){1,3})',
            r'(?:Consultant\s+Incharge|Consultant\s+Doctor|Doctor|Physician)[\s:\n]+(?:Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z\.]+){1,3})',
            r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z\.]+){1,3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if len(name) >= 4:
                    return name
        return None

    # ── HOSPITAL NAME ─────────────────────────────────────────────────────────
    def _extract_hospital_name(self, text, orgs):
        """
        Extract hospital name. Apollo estimate has hospital name on FIRST LINE.
        """
        lines = text.strip().split('\n')

        # ── Priority 1: Check first 4 lines for hospital name ────────────────
        hospital_keywords = [
            'hospital', 'hospitals', 'medical', 'clinic', 'healthcare',
            'institute', 'centre', 'center', 'apollo', 'fortis', 'yashoda',
            'narayana', 'manipal', 'kims', 'care', 'aiims', 'nims',
            'medicover', 'star', 'sunshine', 'continental'
        ]
        bad_words = [
            'estimate', 'fee', 'fees', 'government', 'india', 'unique',
            'authority', 'identification', 'aadhaar', 'revenue', 'certificate'
        ]

        for line in lines[:4]:
            line = line.strip()
            if not line or len(line) < 4:
                continue
            line_lower = line.lower()
            if any(kw in line_lower for kw in hospital_keywords):
                if not any(bad in line_lower for bad in bad_words):
                    # Clean up extra whitespace
                    return re.sub(r'\s+', ' ', line).strip()

        # ── Priority 2: Named hospital chains anywhere in text ────────────────
        chain_patterns = [
            r'(Apollo\s+Hospitals?\s+\w+)',
            r'(Fortis\s+\w[\w\s]+?(?:Hospital|Medical|Healthcare))',
            r'(Yashoda\s+\w[\w\s]+?(?:Hospital|Medical)?)',
            r'(Narayana\s+\w[\w\s]+?(?:Hospital|Medical)?)',
            r'(Manipal\s+\w[\w\s]+?(?:Hospital|Medical)?)',
            r'(KIMS\s+\w[\w\s]*?(?:Hospital|Medical)?)',
            r'([A-Z][A-Za-z\s]+(?:Hospital|Hospitals|Medical Center|Healthcare|Clinic))',
        ]
        first_200 = text[:200]
        for pattern in chain_patterns:
            match = re.search(pattern, first_200, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not any(bad in name.lower() for bad in bad_words):
                    return name

        # ── Priority 3: SpaCy ORG entities ───────────────────────────────────
        for org in orgs:
            if any(kw in org.lower() for kw in hospital_keywords):
                if not any(bad in org.lower() for bad in bad_words):
                    return org

        return None

    # ── PINCODE ───────────────────────────────────────────────────────────────
    def _extract_pincode(self, text):
        pattern = r'\b([1-8][0-9]{5})\b'
        matches = re.findall(pattern, text)
        for match in matches:
            if not match.startswith(('19', '20', '18')):
                return match
        return None

    # ── DISEASES ──────────────────────────────────────────────────────────────
    def _extract_diseases(self, text, doc):
        """
        Extract diseases. Apollo estimate has:
        "DIAGNOSIS\nTriple Vessel Coronary Artery Disease"
        """
        diseases   = []
        text_lower = text.lower()

        # ── Priority 1: Explicit DIAGNOSIS label + next line ─────────────────
        # Apollo format: "DIAGNOSIS\nTriple Vessel Coronary Artery Disease"
        match = re.search(
            r'DIAGNOSIS\s*\n\s*([A-Za-z][A-Za-z\s]+?)(?:\n|$)',
            text, re.MULTILINE
        )
        if match:
            disease = match.group(1).strip()
            if len(disease) > 4 and disease.lower() not in ['details', 'n/a', 'none']:
                diseases.append(disease.title())

        # ── Priority 2: Inline diagnosis patterns ────────────────────────────
        inline_patterns = [
            r'[Dd]iagnosis[\s:\-]+([A-Za-z][A-Za-z\s,]+?)(?:\n|\.|$)',
            r'[Dd]iagnosed\s+(?:with|as)[\s:\-]+([A-Za-z][A-Za-z\s,]+?)(?:\n|\.|$)',
            r'[Cc]ondition[\s:\-]+([A-Za-z][A-Za-z\s,]+?)(?:\n|\.|$)',
        ]
        for pattern in inline_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                d = m.strip()
                if len(d) > 4 and d.lower() not in ['details','n/a','none','procedure']:
                    if d.lower() not in [x.lower() for x in diseases]:
                        diseases.append(d.title())

        # ── Priority 3: Medical terms dictionary ─────────────────────────────
        for term in self.medical_terms:
            if term in text_lower:
                # Avoid adding single generic words if specific diagnosis found
                if len(diseases) > 0 and len(term.split()) == 1 and len(term) < 8:
                    continue
                titled = term.title()
                if titled.lower() not in [d.lower() for d in diseases]:
                    diseases.append(titled)

        # ── Deduplicate ───────────────────────────────────────────────────────
        seen   = set()
        result = []
        for d in diseases:
            key = d.lower().strip()
            if key not in seen and len(key) > 3:
                seen.add(key)
                result.append(d)

        return result

    # ── DATE ──────────────────────────────────────────────────────────────────
    def _extract_date(self, text, doc):
        # SpaCy dates
        dates = [ent.text for ent in doc.ents if ent.label_ == 'DATE']
        if dates:
            return dates[0]

        # Admission date specifically (most relevant for medical docs)
        match = re.search(
            r'(?:Admission|Admitted)\s+Date[\s:\-]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            text, re.IGNORECASE
        )
        if match:
            return match.group(1)

        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    # ── AMOUNT ────────────────────────────────────────────────────────────────
    def _extract_amount(self, text):
        """
        Extract monetary amount. Priority:
        1. ESTIMATED TOTAL — Apollo estimate grand total (9,33,000)
        2. Generic total with currency
        3. Income certificate annual income (72,000)
        4. Fallback large number
        """

        # ── Priority 1: ESTIMATED TOTAL (Apollo estimate format) ─────────────
        # Text: "ESTIMATED TOTAL (₹) 9,33,000.00"
        # Use [^\d]* to skip any non-digit chars including (₹) and spaces
        match = re.search(
            r'ESTIMATED\s+TOTAL[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
            text, re.IGNORECASE
        )
        if match:
            val = self._clean_amount(match.group(1))
            if val and 10000 <= val <= 20000000:
                logger.info(f"Amount from ESTIMATED TOTAL: {val}")
                return val

        # ── Priority 2: Grand total / Net total ──────────────────────────────
        for pattern in [
            r'(?:Grand|Net|Final)\s+Total[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
            r'Total\s+Amount[^\d]*([0-9,]+(?:\.[0-9]{2})?)',
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = self._clean_amount(match.group(1))
                if val and 10000 <= val <= 20000000:
                    return val

        # ── Priority 3: Currency symbol + amount ─────────────────────────────
        # Collect all amounts with currency symbols
        candidates = []
        currency_patterns = [
            r'(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:₹|Rs\.?|INR)\b',
            r'(?:amount|total|payable|cost)[\s:]+([0-9,]+(?:\.[0-9]{2})?)',
        ]
        for pattern in currency_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                val = self._clean_amount(m.group(1))
                if val and 5000 <= val <= 20000000:
                    candidates.append(val)

        if candidates:
            # Return the LARGEST amount (usually the total/estimate)
            return max(candidates)

        # ── Priority 4: Income certificate — annual income ────────────────────
        # "annual income from all Sources ... is Rs. 72000"
        match = re.search(
            r'(?:annual\s+income|income)[^\d]*(?:Rs\.?|₹)?\s*([0-9,]+)',
            text, re.IGNORECASE
        )
        if match:
            val = self._clean_amount(match.group(1))
            if val and val >= 1000:
                return val

        # ── Fallback: largest reasonable number in doc ────────────────────────
        for m in re.finditer(r'\b(\d{1,2},\d{2},\d{3}|\d{5,7})\b', text):
            val = self._clean_amount(m.group(1))
            if val and 5000 <= val <= 9999999:
                return val

        return None

    def _clean_amount(self, s):
        """Convert string like '9,33,000.00' to float 933000.0"""
        try:
            clean = s.replace(',', '').replace(' ', '')
            return float(clean)
        except (ValueError, AttributeError):
            return None

    # ── EXPIRY CHECK ──────────────────────────────────────────────────────────
    def check_document_expiry(self, text):
        result = {'is_expired': False, 'expired_date': None}
        date_patterns = [
            r'valid\s+(?:till|until|upto|up to)[\s:]+([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'expiry\s+date[\s:]+([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'expires[\s:]+([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                        try:
                            if datetime.strptime(date_str, fmt) < datetime.now():
                                result['is_expired']   = True
                                result['expired_date'] = date_str
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
        return result


# ── Test with your actual documents ──────────────────────────────────────────
if __name__ == '__main__':
    extractor = MedicalEntityExtractor()

    print("\n" + "="*60)
    print("TEST 1: Apollo Hospital Estimate")
    print("="*60)
    estimate_text = """APOLLO HOSPITALS VIZAG
Waltair Main Road, Visakhapatnam - 530002
Andhra Pradesh, India
ESTIMATE OF MEDICAL FEES

PATIENT'S NAME
Gollapati Jesse Jasper
PATIENT'S ADDRESS
Visakhapatnam, Andhra Pradesh
CONSULTANT DOCTOR
Dr. R. Srinivas Rao
ADMISSION DATE
01-02-2026
DIAGNOSIS
Triple Vessel Coronary Artery Disease

Registration Fees 2000
Consultant Incharge Fees 120000
Surgery Charges 450000
ESTIMATED TOTAL (Rs) 9,33,000.00"""

    r = extractor.extract_entities(estimate_text)
    print(f"Hospital : {r['hospital_name']}")
    print(f"Patient  : {r['patient_name']}")
    print(f"Doctor   : {r['doctor_name']}")
    print(f"Disease  : {r['diseases']}")
    print(f"Amount   : {r['amount']}")

    print("\n" + "="*60)
    print("TEST 2: Income Certificate")
    print("="*60)
    income_text = """GOVERNMENT OF ANDHRA PRADESH
REVENUE DEPARTMENT
INCOME CERTIFICATE

This is to certify that the annual income from all Sources of
Sri/Srimathi/Kumari JOHN WESLEY F/o / M/o / H/o GOLLAPATI JESSE JASPER
resident of H.No. 29-2115, village WARD-1, Mandal Vinukonda,
District PALNADU of the State Andhra Pradesh is Rs. 72000
(Rupees Seventy Two Thousand Only).
The Aadhaar Number of the applicant is XXXX-XXXX-6241."""

    r = extractor.extract_entities(income_text)
    print(f"Patient  : {r['patient_name']}")
    print(f"Amount   : {r['amount']}")

    print("\n" + "="*60)
    print("TEST 3: Aadhaar Card")
    print("="*60)
    aadhaar_text = """Gollapati Jesse Jasper
DOB: 06/11/2004
MALE
S/O John Wesley
29-2119, Old Lic Building
Vinukonda, Guntur, Andhra Pradesh - 522647
2672 4988 6241"""

    r = extractor.extract_entities(aadhaar_text)
    print(f"Patient  : {r['patient_name']}")
    print(f"Pincode  : {r['hospital_pincode']}")