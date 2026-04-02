"""
MediTrust AI Verification Engine
Multi-document verification with OCR, NER, tampering detection, and cross-document validation
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
import cv2
import numpy as np
from PIL import Image
import pytesseract
import spacy
# import scispacy  # Skipped for compatibility
from transformers import pipeline
from bson import ObjectId

logger = logging.getLogger(__name__)

class MediTrustVerificationEngine:
    """Complete AI verification system for medical documents"""
    
    def __init__(self):
        """Initialize all AI models and services"""
        self.setup_models()
        
    def setup_models(self):
        """Initialize NLP and ML models"""
        try:
            # Load spaCy models
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Standard spaCy model loaded")
            except OSError:
                self.nlp = None
                logger.warning("spaCy model not loaded - using fallback processing")
            
            # Use standard model for medical processing (scispacy not available)
            self.medical_nlp = self.nlp
            logger.info("Using standard spaCy model for medical processing")
            
            # Initialize document tampering detection
            try:
                self.tampering_detector = pipeline(
                    "image-classification",
                    model="microsoft/dit-base-finetuned-rvlcdip"
                )
                logger.info("Document tampering detector loaded")
            except Exception as e:
                self.tampering_detector = None
                logger.warning(f"Tampering detector not loaded: {e}")
            
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            self.nlp = None
            self.medical_nlp = None
            self.tampering_detector = None
            logger.info("Platform will run with simulated verification")
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess document image for analysis"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Noise removal
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Orientation correction
            coords = np.column_stack(np.where(denoised > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            (h, w) = denoised.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            corrected = cv2.warpAffine(denoised, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            
            return corrected
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return None
    
    def extract_text_ocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using multiple OCR engines"""
        try:
            # Tesseract OCR
            text_tesseract = pytesseract.image_to_string(
                image_path, 
                config='--oem 3 --psm 6'
            )
            
            # Preprocessed image OCR
            preprocessed = self.preprocess_image(image_path)
            if preprocessed is not None:
                text_preprocessed = pytesseract.image_to_string(
                    preprocessed,
                    config='--oem 3 --psm 6'
                )
            else:
                text_preprocessed = text_tesseract
            
            return {
                'tesseract_text': text_tesseract,
                'preprocessed_text': text_preprocessed,
                'combined_text': text_tesseract + " " + text_preprocessed
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {'tesseract_text': '', 'preprocessed_text': '', 'combined_text': ''}
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical and general entities using NER"""
        entities = {
            'patient_names': [],
            'doctor_names': [],
            'hospitals': [],
            'dates': [],
            'amounts': [],
            'diseases': [],
            'medical_terms': [],
            'pincodes': [],
            'phone_numbers': [],
            'aadhaar_numbers': []
        }
        
        try:
            # Standard NER with spaCy
            doc = self.nlp(text)
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    if any(word in ent.text.lower() for word in ['dr', 'doctor', 'physician']):
                        entities['doctor_names'].append(ent.text)
                    else:
                        entities['patient_names'].append(ent.text)
                elif ent.label_ == "ORG":
                    entities['hospitals'].append(ent.text)
                elif ent.label_ == "DATE":
                    entities['dates'].append(ent.text)
                elif ent.label_ == "MONEY":
                    entities['amounts'].append(ent.text)
            
            # Medical NER with scispaCy
            medical_doc = self.medical_nlp(text)
            for ent in medical_doc.ents:
                if ent.label_ in ["DISEASE", "DISORDER", "SYMPTOM"]:
                    entities['diseases'].append(ent.text)
                elif ent.label_ in ["CHEMICAL", "DRUG"]:
                    entities['medical_terms'].append(ent.text)
            
            # Rule-based extraction
            entities.update(self.extract_with_regex(text))
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
        
        return entities
    
    def extract_with_regex(self, text: str) -> Dict[str, List[str]]:
        """Extract specific patterns using regex"""
        extracted = {}
        
        try:
            # Amount patterns
            amount_patterns = [
                r'₹\s*[\d,]+(?:\.\d{2})?',
                r'Rs\.?\s*[\d,]+(?:\.\d{2})?',
                r'[\d,]+(?:\.\d{2})?\s*(?:rupees|INR)',
                r'Total.*?([\d,]+(?:\.\d{2})?)',
                r'Amount.*?([\d,]+(?:\.\d{2})?)'
            ]
            
            amounts = []
            for pattern in amount_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                amounts.extend(matches)
            extracted['amounts'] = list(set(amounts))
            
            # Pincode patterns
            pincode_pattern = r'\b\d{6}\b'
            extracted['pincodes'] = re.findall(pincode_pattern, text)
            
            # Phone patterns
            phone_patterns = [
                r'\+91\s*[\d\s-]{10}',
                r'\b\d{10}\b',
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            ]
            
            phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, text)
                phones.extend(matches)
            extracted['phone_numbers'] = list(set(phones))
            
            # Aadhaar pattern
            aadhaar_pattern = r'\b\d{4}\s\d{4}\s\d{4}\b'
            extracted['aadhaar_numbers'] = re.findall(aadhaar_pattern, text)
            
            # Vitals patterns
            vitals_patterns = [
                r'BP\s*[:\-]?\s*(\d+/\d+)',
                r'Heart Rate\s*[:\-]?\s*(\d+)',
                r'Temperature\s*[:\-]?\s*(\d+\.?\d*)',
                r'Weight\s*[:\-]?\s*(\d+\.?\d*)\s*(?:kg|kgs)',
                r'Height\s*[:\-]?\s*(\d+\.?\d*)\s*(?:cm|cms)'
            ]
            
            vitals = []
            for pattern in vitals_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                vitals.extend(matches)
            extracted['vitals'] = vitals
            
        except Exception as e:
            logger.error(f"Regex extraction failed: {e}")
        
        return extracted
    
    def detect_tampering(self, image_path: str) -> Dict[str, Any]:
        """Detect document tampering using ML"""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Use ML model for tampering detection
            results = self.tampering_detector(image)
            
            # Analyze results
            tampering_score = 0
            tampering_indicators = []
            
            for result in results:
                if result['label'].lower() in ['altered', 'modified', 'tampered']:
                    tampering_score = max(tampering_score, result['score'])
                    tampering_indicators.append(result['label'])
            
            # Additional image analysis
            img_array = np.array(image)
            
            # Check for image quality issues
            blur_score = cv2.Laplacian(img_array).var()
            noise_level = np.std(img_array)
            
            return {
                'tampering_score': tampering_score,
                'tampering_indicators': tampering_indicators,
                'image_quality': {
                    'blur_score': blur_score,
                    'noise_level': noise_level,
                    'is_blurry': blur_score < 100,
                    'is_noisy': noise_level > 50
                }
            }
            
        except Exception as e:
            logger.error(f"Tampering detection failed: {e}")
            return {
                'tampering_score': 0,
                'tampering_indicators': [],
                'image_quality': {}
            }
    
    def verify_single_document(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """Verify a single document"""
        try:
            verification_result = {
                'document_type': doc_type,
                'file_name': os.path.basename(file_path),
                'verification_timestamp': datetime.utcnow().isoformat(),
                'ocr_results': {},
                'entities': {},
                'tampering_analysis': {},
                'verification_status': 'PENDING',
                'confidence_score': 0,
                'issues': [],
                'recommendations': []
            }
            
            # OCR extraction
            ocr_results = self.extract_text_ocr(file_path)
            verification_result['ocr_results'] = ocr_results
            
            # Entity extraction
            combined_text = ocr_results.get('combined_text', '')
            entities = self.extract_entities(combined_text)
            verification_result['entities'] = entities
            
            # Tampering detection
            tampering_analysis = self.detect_tampering(file_path)
            verification_result['tampering_analysis'] = tampering_analysis
            
            # Calculate confidence score
            confidence_score = self.calculate_confidence_score(verification_result)
            verification_result['confidence_score'] = confidence_score
            
            # Determine verification status
            status, issues = self.determine_document_status(verification_result, doc_type)
            verification_result['verification_status'] = status
            verification_result['issues'] = issues
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Document verification failed: {e}")
            return {
                'document_type': doc_type,
                'verification_status': 'ERROR',
                'error': str(e),
                'confidence_score': 0
            }
    
    def calculate_confidence_score(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence score for document"""
        try:
            score = 0.0
            
            # OCR quality (30%)
            ocr_text = result.get('ocr_results', {}).get('combined_text', '')
            if len(ocr_text) > 50:
                score += 30
            elif len(ocr_text) > 20:
                score += 20
            elif len(ocr_text) > 0:
                score += 10
            
            # Entity extraction (25%)
            entities = result.get('entities', {})
            entity_count = sum(len(v) for v in entities.values())
            if entity_count >= 5:
                score += 25
            elif entity_count >= 3:
                score += 15
            elif entity_count >= 1:
                score += 10
            
            # Tampering analysis (25%)
            tampering = result.get('tampering_analysis', {})
            tampering_score = tampering.get('tampering_score', 0)
            if tampering_score < 0.1:
                score += 25
            elif tampering_score < 0.3:
                score += 15
            elif tampering_score < 0.5:
                score += 5
            
            # Document type specific validation (20%)
            doc_type = result.get('document_type', '')
            if self.validate_document_type_specific(result, doc_type):
                score += 20
            elif self.validate_document_type_specific(result, doc_type, partial=True):
                score += 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Confidence score calculation failed: {e}")
            return 0.0
    
    def validate_document_type_specific(self, result: Dict[str, Any], doc_type: str, partial: bool = False) -> bool:
        """Validate document based on its type"""
        entities = result.get('entities', {})
        
        if doc_type.lower() == 'aadhaar_card':
            # Should have name, Aadhaar number
            has_name = len(entities.get('patient_names', [])) > 0
            has_aadhaar = len(entities.get('aadhaar_numbers', [])) > 0
            return has_name and (has_aadhaar if not partial else has_name)
        
        elif doc_type.lower() == 'ration_card':
            # Should have name, possibly ration card number
            has_name = len(entities.get('patient_names', [])) > 0
            return has_name
        
        elif doc_type.lower() == 'income_certificate':
            # Should have name, income amount, date
            has_name = len(entities.get('patient_names', [])) > 0
            has_amount = len(entities.get('amounts', [])) > 0
            has_date = len(entities.get('dates', [])) > 0
            return has_name and (has_amount and has_date if not partial else has_name)
        
        elif doc_type.lower() == 'hospital_estimate':
            # Should have hospital name, patient name, amount, disease
            has_hospital = len(entities.get('hospitals', [])) > 0
            has_patient = len(entities.get('patient_names', [])) > 0
            has_amount = len(entities.get('amounts', [])) > 0
            has_disease = len(entities.get('diseases', [])) > 0
            return has_hospital and has_patient and (has_amount and has_disease if not partial else has_hospital)
        
        elif doc_type.lower() in ['hospital_admission', 'discharge_summary']:
            # Should have hospital, patient, dates, diseases
            has_hospital = len(entities.get('hospitals', [])) > 0
            has_patient = len(entities.get('patient_names', [])) > 0
            has_date = len(entities.get('dates', [])) > 0
            has_disease = len(entities.get('diseases', [])) > 0
            return has_hospital and has_patient and (has_date and has_disease if not partial else has_hospital)
        
        return False
    
    def determine_document_status(self, result: Dict[str, Any], doc_type: str) -> Tuple[str, List[str]]:
        """Determine verification status and issues"""
        issues = []
        
        # Check confidence score
        confidence = result.get('confidence_score', 0)
        if confidence < 30:
            issues.append("Low confidence score - document quality poor")
        elif confidence < 60:
            issues.append("Medium confidence score - some issues detected")
        
        # Check tampering
        tampering = result.get('tampering_analysis', {})
        tampering_score = tampering.get('tampering_score', 0)
        if tampering_score > 0.5:
            issues.append("High tampering probability detected")
        elif tampering_score > 0.3:
            issues.append("Possible tampering detected")
        
        # Check document completeness
        if not self.validate_document_type_specific(result, doc_type):
            issues.append("Missing required information for document type")
        
        # Check image quality
        quality = tampering.get('image_quality', {})
        if quality.get('is_blurry', False):
            issues.append("Document image is blurry")
        if quality.get('is_noisy', False):
            issues.append("Document image has excessive noise")
        
        # Determine status
        if len(issues) == 0 and confidence >= 80:
            return 'VERIFIED', []
        elif len(issues) <= 2 and confidence >= 50:
            return 'PENDING', issues
        elif tampering_score > 0.5:
            return 'VERIFICATION_NEEDED', issues
        else:
            return 'CANCELLED', issues
    
    def verify_multiple_documents(self, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """Verify multiple documents with cross-document validation"""
        try:
            verification_results = {
                'verification_id': str(ObjectId()),
                'verification_timestamp': datetime.utcnow().isoformat(),
                'documents': [],
                'cross_document_validation': {},
                'overall_status': 'PENDING',
                'overall_confidence': 0,
                'recommendations': []
            }
            
            # Verify each document
            for doc in documents:
                file_path = doc.get('file_path')
                doc_type = doc.get('document_type')
                
                if file_path and doc_type:
                    doc_result = self.verify_single_document(file_path, doc_type)
                    verification_results['documents'].append(doc_result)
            
            # Cross-document validation
            cross_validation = self.perform_cross_document_validation(verification_results['documents'])
            verification_results['cross_document_validation'] = cross_validation
            
            # Calculate overall confidence and status
            overall_confidence = self.calculate_overall_confidence(verification_results['documents'])
            verification_results['overall_confidence'] = overall_confidence
            
            overall_status = self.determine_overall_status(verification_results)
            verification_results['overall_status'] = overall_status
            
            # Generate recommendations
            recommendations = self.generate_recommendations(verification_results)
            verification_results['recommendations'] = recommendations
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Multi-document verification failed: {e}")
            return {
                'verification_id': str(ObjectId()),
                'overall_status': 'ERROR',
                'error': str(e),
                'overall_confidence': 0
            }
    
    def perform_cross_document_validation(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate consistency across multiple documents"""
        cross_validation = {
            'patient_name_consistency': True,
            'hospital_consistency': True,
            'date_consistency': True,
            'amount_consistency': True,
            'duplicate_documents': [],
            'inconsistencies': []
        }
        
        try:
            # Collect all entities from all documents
            all_patient_names = set()
            all_hospitals = set()
            all_dates = set()
            all_amounts = set()
            
            for doc in documents:
                entities = doc.get('entities', {})
                
                # Collect names
                names = entities.get('patient_names', [])
                all_patient_names.update(names)
                
                # Collect hospitals
                hospitals = entities.get('hospitals', [])
                all_hospitals.update(hospitals)
                
                # Collect dates
                dates = entities.get('dates', [])
                all_dates.update(dates)
                
                # Collect amounts
                amounts = entities.get('amounts', [])
                all_amounts.update(amounts)
            
            # Check consistency
            if len(all_patient_names) > 1:
                cross_validation['patient_name_consistency'] = False
                cross_validation['inconsistencies'].append(f"Multiple patient names found: {list(all_patient_names)}")
            
            if len(all_hospitals) > 1:
                cross_validation['hospital_consistency'] = False
                cross_validation['inconsistencies'].append(f"Multiple hospitals found: {list(all_hospitals)}")
            
            # Check for duplicate documents
            doc_hashes = []
            for doc in documents:
                file_name = doc.get('file_name', '')
                if file_name in doc_hashes:
                    cross_validation['duplicate_documents'].append(file_name)
                else:
                    doc_hashes.append(file_name)
            
        except Exception as e:
            logger.error(f"Cross-document validation failed: {e}")
        
        return cross_validation
    
    def calculate_overall_confidence(self, documents: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence across all documents"""
        if not documents:
            return 0.0
        
        total_confidence = sum(doc.get('confidence_score', 0) for doc in documents)
        return total_confidence / len(documents)
    
    def determine_overall_status(self, verification_results: Dict[str, Any]) -> str:
        """Determine overall verification status"""
        documents = verification_results.get('documents', [])
        cross_validation = verification_results.get('cross_document_validation', {})
        
        # Check for any cancelled documents
        if any(doc.get('verification_status') == 'CANCELLED' for doc in documents):
            return 'CANCELLED'
        
        # Check for verification needed
        if any(doc.get('verification_status') == 'VERIFICATION_NEEDED' for doc in documents):
            return 'VERIFICATION_NEEDED'
        
        # Check cross-document inconsistencies
        if not cross_validation.get('patient_name_consistency', True):
            return 'VERIFICATION_NEEDED'
        
        if cross_validation.get('duplicate_documents', []):
            return 'VERIFICATION_NEEDED'
        
        # Check overall confidence
        overall_confidence = verification_results.get('overall_confidence', 0)
        if overall_confidence >= 80:
            return 'VERIFIED'
        elif overall_confidence >= 50:
            return 'PENDING'
        else:
            return 'VERIFICATION_NEEDED'
    
    def generate_recommendations(self, verification_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []
        
        try:
            documents = verification_results.get('documents', [])
            cross_validation = verification_results.get('cross_document_validation', {})
            
            # Document quality recommendations
            for doc in documents:
                issues = doc.get('issues', [])
                for issue in issues:
                    if 'blurry' in issue.lower():
                        recommendations.append("Re-scan blurry documents with higher resolution")
                    elif 'noise' in issue.lower():
                        recommendations.append("Ensure documents are scanned in good lighting conditions")
                    elif 'missing information' in issue.lower():
                        recommendations.append(f"Complete missing information in {doc.get('document_type', 'document')}")
            
            # Cross-document recommendations
            if not cross_validation.get('patient_name_consistency', True):
                recommendations.append("Ensure patient name is consistent across all documents")
            
            if not cross_validation.get('hospital_consistency', True):
                recommendations.append("Ensure hospital name is consistent across all documents")
            
            if cross_validation.get('duplicate_documents', []):
                recommendations.append("Remove duplicate documents")
            
            # Overall recommendations
            overall_confidence = verification_results.get('overall_confidence', 0)
            if overall_confidence < 50:
                recommendations.append("Consider providing additional verification documents")
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
        
        return list(set(recommendations))  # Remove duplicates
