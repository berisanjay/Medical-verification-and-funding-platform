"""
Cross-Document Validation and Fraud Detection
Validates consistency across multiple medical documents
"""
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class CrossDocumentValidator:
    """Validate consistency across multiple documents"""
    
    def __init__(self):
        """Initialize validator"""
        pass
    
    def validate_documents(self, documents):
        """
        Validate consistency across multiple documents
        
        Args:
            documents: List of document data dicts with entities
        
        Returns:
            List of validation issues found
        """
        issues = []
        
        if len(documents) < 2:
            # No cross-validation needed for single document
            return issues
        
        logger.info(f"Cross-validating {len(documents)} documents")
        
        # Extract entities from all documents
        all_patients = []
        all_doctors = []
        all_hospitals = []
        all_pincodes = []
        all_dates = []
        all_amounts = []
        
        for doc in documents:
            entities = doc.get('entities', {})
            
            if entities.get('patient_name'):
                all_patients.append(entities['patient_name'])
            if entities.get('doctor_name'):
                all_doctors.append(entities['doctor_name'])
            if entities.get('hospital_name'):
                all_hospitals.append(entities['hospital_name'])
            if entities.get('hospital_pincode'):
                all_pincodes.append(entities['hospital_pincode'])
            if entities.get('date'):
                all_dates.append(entities['date'])
            if entities.get('amount'):
                all_amounts.append(entities['amount'])
        
        # Validation 1: Patient Name Consistency
        issues.extend(self._validate_patient_names(all_patients))
        
        # Validation 2: Hospital Consistency
        issues.extend(self._validate_hospitals(all_hospitals, all_pincodes))
        
        # Validation 3: Date Consistency
        issues.extend(self._validate_dates(all_dates))
        
        # Validation 4: Amount Consistency
        issues.extend(self._validate_amounts(all_amounts, documents))
        
        # Validation 5: Doctor Consistency (warning only)
        issues.extend(self._validate_doctors(all_doctors))
        
        logger.info(f"Found {len(issues)} cross-document issues")
        return issues
    
    def _validate_patient_names(self, patient_names):
        """Validate that patient names are consistent"""
        issues = []
        
        if len(patient_names) < 2:
            return issues
        
        # Normalize names for comparison
        normalized_names = [self._normalize_name(name) for name in patient_names]
        
        # Check if all names match
        if len(set(normalized_names)) > 1:
            unique_names = list(set(patient_names))
            issues.append({
                'type': 'PATIENT_NAME_MISMATCH',
                'severity': 'HIGH',
                'description': f'Patient name mismatch across documents: {", ".join(unique_names)}',
                'details': {
                    'found_names': patient_names,
                    'unique_names': unique_names
                }
            })
        
        return issues
    
    def _validate_hospitals(self, hospital_names, pincodes):
        """Validate hospital consistency"""
        issues = []
        
        # Check hospital names
        if len(hospital_names) >= 2:
            normalized_hospitals = [self._normalize_name(h) for h in hospital_names]
            
            if len(set(normalized_hospitals)) > 1:
                issues.append({
                    'type': 'HOSPITAL_MISMATCH',
                    'severity': 'MEDIUM',
                    'description': f'Different hospitals mentioned: {", ".join(set(hospital_names))}',
                    'details': {
                        'hospitals': hospital_names
                    }
                })
        
        # Check pincodes
        if len(pincodes) >= 2:
            if len(set(pincodes)) > 1:
                issues.append({
                    'type': 'PINCODE_MISMATCH',
                    'severity': 'MEDIUM',
                    'description': f'Different pincodes found: {", ".join(set(pincodes))}',
                    'details': {
                        'pincodes': pincodes
                    }
                })
        
        # Check if any document is missing hospital info
        if len(hospital_names) == 0 and len(pincodes) == 0:
            issues.append({
                'type': 'MISSING_HOSPITAL_INFO',
                'severity': 'HIGH',
                'description': 'No hospital information found in any document',
                'details': {}
            })
        
        return issues
    
    def _validate_dates(self, dates):
        """Validate date consistency and logical order"""
        issues = []
        
        if len(dates) < 2:
            return issues
        
        # Parse dates
        parsed_dates = []
        for date_str in dates:
            parsed = self._parse_date(date_str)
            if parsed:
                parsed_dates.append(parsed)
        
        if len(parsed_dates) < 2:
            return issues
        
        # Check for unreasonable date ranges
        min_date = min(parsed_dates)
        max_date = max(parsed_dates)
        date_diff = (max_date - min_date).days
        
        if date_diff > 365:
            issues.append({
                'type': 'CONFLICTING_DATES',
                'severity': 'MEDIUM',
                'description': f'Dates span over {date_diff} days - potential inconsistency',
                'details': {
                    'dates': dates,
                    'date_range_days': date_diff
                }
            })
        
        # Check for future dates
        now = datetime.now()
        future_dates = [d for d in parsed_dates if d > now]
        if future_dates:
            issues.append({
                'type': 'FUTURE_DATE',
                'severity': 'HIGH',
                'description': 'Document contains future dates',
                'details': {
                    'dates': dates
                }
            })
        
        return issues
    
    def _validate_amounts(self, amounts, documents):
        """Validate amount consistency"""
        issues = []
        
        if len(amounts) < 2:
            return issues
        
        # Convert amounts to numbers
        numeric_amounts = []
        for amount in amounts:
            numeric = self._parse_amount(amount)
            if numeric:
                numeric_amounts.append(numeric)
        
        if len(numeric_amounts) < 2:
            return issues
        
        # Check for large discrepancies
        min_amount = min(numeric_amounts)
        max_amount = max(numeric_amounts)
        
        # If amounts differ by more than 20%, flag it
        if min_amount > 0 and (max_amount / min_amount) > 1.2:
            issues.append({
                'type': 'AMOUNT_DISCREPANCY',
                'severity': 'MEDIUM',
                'description': f'Significant amount variation: ₹{min_amount:,.0f} to ₹{max_amount:,.0f}',
                'details': {
                    'amounts': amounts,
                    'min_amount': min_amount,
                    'max_amount': max_amount,
                    'variation_percent': round(((max_amount - min_amount) / min_amount) * 100, 2)
                }
            })
        
        # Check document types for amount logic
        # Estimate should be >= Bill
        estimates = []
        bills = []
        
        for doc in documents:
            doc_type = doc.get('document_type', 'UNKNOWN')
            amount_str = doc.get('entities', {}).get('amount')
            if amount_str:
                amount_num = self._parse_amount(amount_str)
                if amount_num:
                    if doc_type == 'ESTIMATE':
                        estimates.append(amount_num)
                    elif doc_type == 'BILL':
                        bills.append(amount_num)
        
        if estimates and bills:
            max_bill = max(bills)
            min_estimate = min(estimates)
            
            if max_bill > min_estimate:
                issues.append({
                    'type': 'BILL_EXCEEDS_ESTIMATE',
                    'severity': 'HIGH',
                    'description': f'Bill amount (₹{max_bill:,.0f}) exceeds estimate (₹{min_estimate:,.0f})',
                    'details': {
                        'bill_amount': max_bill,
                        'estimate_amount': min_estimate
                    }
                })
        
        return issues
    
    def _validate_doctors(self, doctor_names):
        """Validate doctor consistency (warning only)"""
        issues = []
        
        if len(doctor_names) >= 2:
            normalized_doctors = [self._normalize_name(d) for d in doctor_names]
            
            if len(set(normalized_doctors)) > 1:
                issues.append({
                    'type': 'MULTIPLE_DOCTORS',
                    'severity': 'LOW',
                    'description': f'Multiple doctors mentioned: {", ".join(set(doctor_names))}',
                    'details': {
                        'doctors': doctor_names,
                        'note': 'This may be normal for multi-specialty treatment'
                    }
                })
        
        return issues
    
    def _normalize_name(self, name):
        """Normalize a name for comparison"""
        if not name:
            return ''
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove titles
        titles = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'mr', 'mrs', 'ms', 'dr', 'prof']
        for title in titles:
            normalized = normalized.replace(title, '')
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove dots and special characters
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized.strip()
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%Y-%m-%d',
            '%d/%m/%y',
            '%d-%m-%y',
            '%d %B %Y',
            '%d %b %Y',
            '%B %d, %Y',
            '%b %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # Try to extract date from string
        # Pattern: DD/MM/YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', date_str)
        if match:
            try:
                day, month, year = match.groups()
                year = int(year)
                if year < 100:
                    year += 2000
                return datetime(year, int(month), int(day))
            except:
                pass
        
        return None
    
    def _parse_amount(self, amount_str):
        """Parse amount string to number"""
        if not amount_str:
            return None
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', amount_str)
        
        try:
            return float(cleaned)
        except:
            return None


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    validator = CrossDocumentValidator()
    
    # Sample documents
    docs = [
        {
            'filename': 'estimate.pdf',
            'document_type': 'ESTIMATE',
            'entities': {
                'patient_name': 'Suresh Kumar',
                'hospital_name': 'Yashoda Hospitals',
                'hospital_pincode': '500082',
                'date': '15/01/2024',
                'amount': '4,95,000'
            }
        },
        {
            'filename': 'bill.pdf',
            'document_type': 'BILL',
            'entities': {
                'patient_name': 'Suresh K',
                'hospital_name': 'Yashoda Hospital',
                'hospital_pincode': '500082',
                'date': '20/01/2024',
                'amount': '5,10,000'
            }
        }
    ]
    
    issues = validator.validate_documents(docs)
    
    print("\nValidation Results:")
    print(f"Found {len(issues)} issues\n")
    
    for issue in issues:
        print(f"[{issue['severity']}] {issue['type']}")
        print(f"  {issue['description']}")
        print()
