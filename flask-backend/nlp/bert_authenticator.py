"""
BERT-based Document Authenticity Detection
Uses transformers to detect forged vs genuine medical documents
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
import numpy as np

logger = logging.getLogger(__name__)

class BERTDocumentAuthenticator:
    """BERT-based document authenticity detection"""
    
    def __init__(self):
        """Initialize BERT model for document classification"""
        try:
            # Use a pre-trained model for text classification
            # You can fine-tune this with medical documents later
            model_name = "bert-base-uncased"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name, 
                num_labels=2  # GENUINE vs FORGED
            )
            self.model.eval()
            logger.info("BERT model loaded for document authenticity detection")
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            # Fallback to rule-based detection
            self.model = None
            self.tokenizer = None
    
    def predict_authenticity(self, text, extracted_entities):
        """
        Predict if document is genuine or forged
        
        Args:
            text: Extracted text from document
            extracted_entities: Dict of extracted medical entities
        
        Returns:
            Dict with authenticity score and prediction
        """
        if self.model is None:
            return self._rule_based_detection(text, extracted_entities)
        
        try:
            # Prepare text for BERT
            features = self._extract_features(text, extracted_entities)
            input_text = self._prepare_input_text(features)
            
            # Tokenize and predict
            inputs = self.tokenizer(
                input_text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512,
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)
                confidence = probabilities.max().item()
                prediction = "GENUINE" if probabilities[0][1] > probabilities[0][0] else "FORGED"
                
            return {
                "prediction": prediction,
                "confidence": confidence,
                "genuine_probability": probabilities[0][1].item(),
                "forged_probability": probabilities[0][0].item(),
                "method": "BERT"
            }
            
        except Exception as e:
            logger.error(f"BERT prediction failed: {e}")
            return self._rule_based_detection(text, extracted_entities)
    
    def _extract_features(self, text, entities):
        """Extract features from text and entities"""
        features = {
            "has_patient_name": bool(entities.get("patient_name")),
            "has_doctor_name": bool(entities.get("doctor_name")),
            "has_hospital": bool(entities.get("hospital_name")),
            "has_disease": bool(entities.get("diseases")),
            "has_amount": bool(entities.get("amount")),
            "has_date": bool(entities.get("date")),
            "text_length": len(text),
            "word_count": len(text.split()),
            "medical_terms_count": self._count_medical_terms(text),
            "digit_count": sum(c.isdigit() for c in text),
            "special_char_count": sum(not c.isalnum() and not c.isspace() for c in text)
        }
        return features
    
    def _prepare_input_text(self, features):
        """Prepare input text for BERT based on features"""
        feature_text = " ".join([
            f"Patient: {'present' if features['has_patient_name'] else 'missing'}",
            f"Doctor: {'present' if features['has_doctor_name'] else 'missing'}",
            f"Hospital: {'present' if features['has_hospital'] else 'missing'}",
            f"Disease: {'present' if features['has_disease'] else 'missing'}",
            f"Amount: {'present' if features['has_amount'] else 'missing'}",
            f"Date: {'present' if features['has_date'] else 'missing'}",
            f"Words: {features['word_count']}",
            f"Medical terms: {features['medical_terms_count']}"
        ])
        return feature_text
    
    def _count_medical_terms(self, text):
        """Count medical terms in text"""
        medical_terms = [
            'diabetes', 'hypertension', 'cancer', 'tuberculosis', 'pneumonia',
            'asthma', 'arthritis', 'angioplasty', 'bypass', 'surgery',
            'fracture', 'infection', 'fever', 'covid', 'malaria', 'dengue',
            'heart attack', 'stroke', 'kidney', 'liver', 'appendicitis',
            'coronary', 'cardiac', 'myocardial', 'infarction', 'stent',
            'chemotherapy', 'dialysis', 'transplant', 'icu', 'emergency',
            'hospital', 'clinic', 'medical', 'doctor', 'physician', 'surgeon',
            'treatment', 'therapy', 'medication', 'prescription', 'diagnosis'
        ]
        text_lower = text.lower()
        return sum(1 for term in medical_terms if term in text_lower)
    
    def _rule_based_detection(self, text, entities):
        """Fallback rule-based detection"""
        score = 0
        max_score = 100
        
        # Mandatory fields check
        if entities.get("patient_name"):
            score += 20
        if entities.get("hospital_name"):
            score += 15
        if entities.get("diseases"):
            score += 15
        if entities.get("amount"):
            score += 15
        if entities.get("date"):
            score += 10
        
        # Text quality checks
        if len(text) > 100:
            score += 10
        if self._count_medical_terms(text) > 2:
            score += 10
        if entities.get("doctor_name"):
            score += 5
        
        confidence = score / max_score
        prediction = "GENUINE" if confidence > 0.6 else "FORGED"
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "genuine_probability": confidence,
            "forged_probability": 1 - confidence,
            "method": "RULE_BASED",
            "score": score
        }
