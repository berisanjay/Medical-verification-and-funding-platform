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
            # Try to load medical model first
            try:
                self.nlp = spacy.load("en_core_sci_sm")
                logger.info("Loaded SciSpacy medical model")
            except:
                # Fallback to standard English model
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded standard spaCy model (medical model not available)")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
        
        # Medical terms dictionary for disease detection
        self.medical_terms = [
            'diabetes', 'hypertension', 'cancer', 'tuberculosis', 'pneumonia',
            'asthma', 'arthritis', 'angioplasty', 'bypass', 'surgery',
            'fracture', 'infection', 'fever', 'covid', 'malaria', 'dengue',
            'heart attack', 'stroke', 'kidney', 'liver', 'appendicitis',
            'coronary', 'cardiac', 'myocardial', 'infarction', 'stent',
            'chemotherapy', 'dialysis', 'transplant', 'icu', 'emergency'
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
            'patient_name': None,
            'doctor_name': None,
            'hospital_name': None,
            'hospital_pincode': None,
            'diseases': [],
            'date': None,
            'amount': None
        }
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Extract person names (potential patients and doctors)
        persons = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']
        
        # Extract patient name (usually first mentioned or after keywords)
        entities['patient_name'] = self._extract_patient_name(text, persons)
        
        # Extract doctor name
        entities['doctor_name'] = self._extract_doctor_name(text, persons)
        
        # Extract organization names (potential hospitals)
        orgs = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
        entities['hospital_name'] = self._extract_hospital_name(text, orgs)
        
        # Extract pincode
        entities['hospital_pincode'] = self._extract_pincode(text)
        
        # Extract diseases
        entities['diseases'] = self._extract_diseases(text, doc)
        
        # Extract dates
        entities['date'] = self._extract_date(text, doc)
        
        # Extract amount
        entities['amount'] = self._extract_amount(text)
        
        logger.info(f"Extracted entities: {entities}")
        return entities
    
    def _extract_patient_name(self, text, persons):
        """Extract patient name from text"""
        # Look for patterns like "Patient: Name" or "Patient Name: Name"
        patterns = [
            r'patient\s*(?:name)?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'name\s*(?:of\s*patient)?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'mr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'mrs\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'ms\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: first person mentioned
        if persons:
            return persons[0]
        
        return None
    
    def _extract_doctor_name(self, text, persons):
        """Extract doctor name from text"""
        patterns = [
            r'dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'doctor[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'physician[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'consultant[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: second person if multiple persons found
        if len(persons) > 1:
            return persons[1]
        
        return None
    
    def _extract_hospital_name(self, text, orgs):
        """Extract hospital name from text"""
        # Common hospital keywords
        hospital_keywords = ['hospital', 'medical', 'clinic', 'healthcare', 
                           'care', 'nursing', 'health', 'institute']
        
        # Look for organizations with hospital keywords
        for org in orgs:
            org_lower = org.lower()
            if any(keyword in org_lower for keyword in hospital_keywords):
                return org
        
        # Pattern matching
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Hospital|Medical|Clinic|Healthcare))',
            r'((?:Hospital|Medical|Clinic)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: first org if available
        if orgs:
            return orgs[0]
        
        return None
    
    def _extract_pincode(self, text):
        """Extract Indian pincode (6 digits)"""
        # Indian pincode pattern
        pattern = r'\b[1-9][0-9]{5}\b'
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None
    
    def _extract_diseases(self, text, doc):
        """Extract disease/diagnosis names"""
        diseases = []
        text_lower = text.lower()
        
        # Check for medical terms in our dictionary
        for term in self.medical_terms:
            if term in text_lower:
                diseases.append(term.title())
        
        # Look for diagnosis patterns
        patterns = [
            r'diagnosis[\s:]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'disease[\s:]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'condition[\s:]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
            r'treatment\s+for[\s:]+([A-Za-z\s,]+?)(?:\.|,|\n|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean and add
                disease = match.strip()
                if len(disease) > 3 and disease.lower() not in [d.lower() for d in diseases]:
                    diseases.append(disease.title())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_diseases = []
        for disease in diseases:
            disease_lower = disease.lower()
            if disease_lower not in seen:
                seen.add(disease_lower)
                unique_diseases.append(disease)
        
        return unique_diseases
    
    def _extract_date(self, text, doc):
        """Extract dates from text"""
        # SpaCy date entities
        dates = [ent.text for ent in doc.ents if ent.label_ == 'DATE']
        
        if dates:
            # Return the first date found
            return dates[0]
        
        # Pattern matching for common date formats
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD/MM/YYYY or DD-MM-YYYY
            r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}',  # YYYY/MM/DD or YYYY-MM-DD
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}'  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_amount(self, text):
        """Extract monetary amounts from text"""
        # Look for amount patterns with Rs, INR, ₹
        patterns = [
            r'(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]{2})?)',  # Rs 1,00,000
            r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:Rs\.?|INR|₹)',  # 1,00,000 Rs
            r'amount[\s:]+(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)',  # Amount: 1,00,000
            r'total[\s:]+(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)',  # Total: 1,00,000
            r'payable[\s:]+(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)'  # Payable: 1,00,000
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            amounts.extend(matches)
        
        if amounts:
            # Return the first (usually largest or most relevant) amount
            return amounts[0].strip()
        
        # Fallback: look for any large number (potential amount)
        large_numbers = re.findall(r'\b([0-9,]+)\b', text)
        for num in large_numbers:
            # Remove commas and check if it's a reasonable amount (> 1000)
            clean_num = num.replace(',', '')
            if clean_num.isdigit() and int(clean_num) > 1000:
                return num
        
        return None


# Test function
if __name__ == '__main__':
    extractor = MedicalEntityExtractor()
    
    # Sample medical text
    sample_text = """
    MEDICAL ESTIMATE
    
    Patient Name: Suresh Kumar
    Date: 15/01/2024
    
    Hospital: Yashoda Hospitals
    Address: Somajiguda, Hyderabad - 500082
    
    Doctor: Dr. Rajesh Sharma
    Consultant Cardiologist
    
    Diagnosis: Coronary Artery Disease requiring angioplasty
    
    Estimated Treatment Cost: Rs. 4,95,000/-
    """
    
    result = extractor.extract_entities(sample_text)
    print("\nExtracted Entities:")
    for key, value in result.items():
        print(f"{key}: {value}")
