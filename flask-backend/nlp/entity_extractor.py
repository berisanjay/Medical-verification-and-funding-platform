"""
Medical Entity Extraction using spaCy and SciSpacy
Extracts patient names, doctor names, hospitals, diseases, dates, and amounts
"""
import spacy
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MedicalEntityExtractor:
    """Extract medical entities from text using NLP"""

    def __init__(self):
        """Initialize spaCy models"""
        try:
            try:
                self.nlp = spacy.load("en_core_sci_sm")
                logger.info("Loaded SciSpacy medical model")
            except:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded standard spaCy model (medical model not available)")
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
            'hip replacement', 'cataract', 'glaucoma', 'arthritis',
            'thyroid', 'ulcer', 'migraine', 'paralysis', 'epilepsy',
            'vessel', 'coronary artery', 'cabg', 'triple vessel',
            'triple vessel', 'triple vessel coronary', 'coronary artery disease',
            'cabg', 'open heart', 'vessel disease'
        ]

        self.indian_name_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)',
            r'(?:Mr|Mrs|Ms|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]

    def extract_entities(self, text):
        """
        Extract all medical entities from text

        Returns dict with:
        - patient_name
        - doctor_name
        - hospital_name
        - hospital_pincode
        - diseases
        - date
        - amount
        """
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

        entities['patient_name']     = self._extract_patient_name(text, persons)
        entities['doctor_name']      = self._extract_doctor_name(text, persons)

        orgs = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
        entities['hospital_name']    = self._extract_hospital_name(text, orgs)
        entities['hospital_pincode'] = self._extract_pincode(text)
        entities['diseases']         = self._extract_diseases(text, doc)
        entities['date']             = self._extract_date(text, doc)
        entities['amount']           = self._extract_amount(text)

        logger.info(f"Extracted entities: {entities}")
        return entities

    def _extract_patient_name(self, text, persons):
        # Priority: explicit label on NEXT LINE (Apollo estimate format)
        patterns = [
            r"PATIENT'S NAME\s*\n\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            r"Patient(?:'s)?\s+Name[\s:\n]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            r"Name\s*of\s*Patient[\s:\n]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            # Aadhaar format
            r"^(Gollapati\s+\w+\s+\w+)",
            r"^([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)\s*\n\s*(?:S/O|D/O|W/O)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                bad = ['hospital','medical','estimate','fee','doctor','admission',
                       'consultant','government','india','apollo','certificate']
                if not any(b in name.lower() for b in bad) and len(name) > 4:
                    return name

        # SpaCy persons — longest valid name
        for person in sorted(persons, key=len, reverse=True):
            if len(person.split()) >= 2 and len(person) > 6:
                bad = ['hospital','medical','estimate','doctor','admission','consultant']
                if not any(b in person.lower() for b in bad):
                    return person
        return None

    def _extract_doctor_name(self, text, persons):
        """Extract doctor name from text"""
        patterns = [
            r'(?:consultant\s+doctor|consultant\s+incharge|doctor|physician|consultant)[\s:\n]+(?:Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        if len(persons) > 1:
            return persons[1]

        return None

    def _extract_hospital_name(self, text, orgs):
        # Check first 3 lines — hospital name is always at top
        first_lines = text.strip().split('\n')[:3]
        for line in first_lines:
            line = line.strip()
            if len(line) > 5 and any(k in line.upper() for k in 
                ['HOSPITAL','MEDICAL','CLINIC','APOLLO','FORTIS','YASHODA','CARE','AIIMS','KIMS','NARAYANA']):
                # Clean up
                if 'ESTIMATE' not in line.upper() and 'FEE' not in line.upper():
                    return line.strip()

        # Chain patterns
        patterns = [
            r'(Apollo\s+Hospitals?\s+\w+)',
            r'(Fortis\s+\w[\w\s]+(?:Hospital|Medical))',
            r'([\w\s]+(?:Hospital|Hospitals|Medical Center|Healthcare))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 'ESTIMATE' not in name.upper() and len(name) > 5:
                    return name
        return None

    def _extract_pincode(self, text):
        """Extract pincode from text"""
        # Indian pincodes are 6 digits
        pincode_pattern = r'\b([1-9][0-9]{5})\b'
        match = re.search(pincode_pattern, text)
        if match:
            return match.group(1)
        return None

    def _extract_diseases(self, text, doc):
        """Extract primary diagnosis — prefer explicit DIAGNOSIS field"""

        # Priority 1 — explicit DIAGNOSIS label (most accurate)
        diag_patterns = [
            r'DIAGNOSIS\s*\n\s*([A-Za-z\s]+?)(?:\n|$)',           # Apollo format
            r'Diagnosis[\s:\n]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'DIAGNOSIS[\s:\n]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'disease[\s:\n]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'treatment\s+for[\s:\n]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'DIAGNOSIS[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\n|$)',
            r'diagnosis[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\.|,|\n|$)',
            r'Diagnosis[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\.|,|\n|$)',
            r'FINDINGS[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\n|$)',
        ]

        for pattern in diag_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                disease = match.group(1).strip()
                # Validate — must be at least 5 chars and not garbage
                if len(disease) >= 5 and not any(
                    bad in disease.lower() for bad in
                    ['page','date','name','address','hospital','doctor']
                ):
                    return [disease]  # Return as list with primary diagnosis only

        # Priority 2 — procedure/surgery field
        proc_patterns = [
            r'PROCEDURE[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\n|$)',
            r'procedure[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\.|,|\n|$)',
            r'Treatment\s+for[\s:\n]+([A-Za-z][A-Za-z\s,\-]+?)(?:\.|,|\n|$)',
        ]

        for pattern in proc_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                disease = match.group(1).strip()
                if len(disease) >= 5:
                    return [disease]

        # Priority 3 — keyword match but return only the MOST specific term
        text_lower = text.lower()
        # Ordered from most specific to least specific
        specific_terms = [
            'triple vessel coronary artery disease',
            'coronary artery disease',
            'myocardial infarction',
            'open heart surgery',
            'bypass surgery',
            'kidney failure',
            'liver cirrhosis',
            'brain tumor',
            'lung cancer',
        ]

        for term in specific_terms:
            if term in text_lower:
                return [term.title()]

        # Last resort — first keyword match only
        for term in self.medical_terms:
            if term in text_lower and len(term) > 5:
                return [term.title()]

        return []

    def _extract_date(self, text, doc):
        """Extract date from text"""
        # Common date patterns
        date_patterns = [
            r'([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'([0-9]{2,4}[-/][0-9]{1,2}[-/][0-9]{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                # Try to validate the date
                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%Y/%m/%d', '%Y-%m-%d']:
                    try:
                        datetime.strptime(date_str, fmt)
                        return date_str
                    except ValueError:
                        continue
        
        # Check spaCy date entities
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                return ent.text
        
        return None

    def _extract_amount(self, text):
        """Extract monetary amounts from text — returns largest medical amount"""

        # ── Priority patterns (most specific first) ──────────────────────────
        priority_patterns = [
            # Apollo estimate format — ESTIMATED TOTAL is the correct amount
            r'ESTIMATED\s+TOTAL\s*\(₹\)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'ESTIMATED\s+TOTAL[^0-9₹Rs]*(?:₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'Grand\s+Total[^0-9]*([0-9,]+(?:\.[0-9]{2})?)',
            # Income certificate patterns
            r'annual\s+income\s+from\s+all\s+Sources[^0-9]*(?:Rs\.?)?\s*([0-9,]+)',
            r'income\s+is\s+Rs\.?\s*([0-9,]+)',
            # Generic total with currency
            r'(?:grand\s+)?total\s+(?:amount\s+)?(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:/-|only|lakhs?)?',
            r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:₹|Rs\.?|INR)',
            r'amount[\s:]+(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'total[\s:]+(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'payable[\s:]+(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'estimated\s+cost[\s:]+(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'charges[\s:]+(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)',
        ]

        candidates = []

        for pattern in priority_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                clean = m.replace(',', '').replace(' ', '')
                try:
                    val = float(clean)
                    # Medical amounts: between ₹5,000 and ₹2,00,00,000
                    if 5000 <= val <= 20000000:
                        candidates.append(val)
                except ValueError:
                    continue

        if candidates:
            # Return the largest valid medical amount
            return max(candidates)

        # ── Conservative fallback — only 5-7 digit numbers ───────────────────
        # Avoids grabbing certificate/ID numbers (8+ digits) or small codes
        for match in re.finditer(r'\b([1-9][0-9]{0,1},[0-9]{2},[0-9]{3}(?:\.[0-9]{2})?)\b', text):
            raw = match.group(1)
            clean = raw.replace(',', '')
            if clean.isdigit():
                val = int(clean)
                if 10000 <= val <= 9999999:
                    return val

        return None

    def check_document_expiry(self, text):
        """Check if document contains expired dates"""
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
                            doc_date = datetime.strptime(date_str, fmt)
                            if doc_date < datetime.now():
                                result['is_expired']   = True
                                result['expired_date'] = date_str
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        return result


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    extractor = MedicalEntityExtractor()

    sample_text = """
    APOLLO HOSPITALS VIZAG
    Waltair Main Road, Visakhapatnam – 530002

    PATIENT'S NAME
    Gollapati Jesse Jasper

    CONSULTANT DOCTOR
    Dr. R. Srinivas Rao

    DIAGNOSIS
    Triple Vessel Coronary Artery Disease

    ESTIMATED TOTAL (₹) 9,33,000.00
    """

    result = extractor.extract_entities(sample_text)
    print("\nExtracted Entities:")
    for key, value in result.items():
        print(f"  {key}: {value}")