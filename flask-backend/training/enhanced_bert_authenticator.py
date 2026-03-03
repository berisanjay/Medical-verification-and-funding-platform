"""
Enhanced BERT Authenticator with Custom Training Support
Uses your trained models for better document authenticity detection
"""

import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
from datetime import datetime
import joblib

logger = logging.getLogger(__name__)

class EnhancedBERTAuthenticator:
    """Enhanced BERT authenticator that uses custom trained models"""
    
    def __init__(self, model_path="training_data/model"):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.cnn_model = None
        self.label_encoder = None
        self.use_custom_model = False
        
        # Try to load custom trained models
        self.load_custom_models()
        
        # Fallback to pre-trained if custom not available
        if not self.use_custom_model:
            self.load_pretrained_model()
    
    def load_custom_models(self):
        """Load custom trained models"""
        try:
            # Check if custom BERT model exists
            bert_model_path = os.path.join(self.model_path, "bert_model")
            if os.path.exists(bert_model_path):
                logger.info("Loading custom trained BERT model...")
                self.tokenizer = AutoTokenizer.from_pretrained(bert_model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(bert_model_path)
                self.use_custom_model = True
                logger.info("Custom BERT model loaded successfully")
            
            # Check if CNN model exists
            cnn_model_path = os.path.join(self.model_path, "cnn_model.h5")
            if os.path.exists(cnn_model_path):
                logger.info("Loading custom trained CNN model...")
                import tensorflow as tf
                self.cnn_model = tf.keras.models.load_model(cnn_model_path)
                
                # Load label encoder
                encoder_path = os.path.join(self.model_path, "label_encoder.pkl")
                if os.path.exists(encoder_path):
                    self.label_encoder = joblib.load(encoder_path)
                
                logger.info("Custom CNN model loaded successfully")
            
            # Check training summary
            summary_path = os.path.join(self.model_path, "training_summary.json")
            if os.path.exists(summary_path):
                import json
                with open(summary_path, 'r') as f:
                    summary = json.load(f)
                logger.info(f"Training data: {summary['total_documents']} documents")
                logger.info(f"Models trained: {summary['models_trained']}")
        
        except Exception as e:
            logger.error(f"Error loading custom models: {e}")
            self.use_custom_model = False
    
    def load_pretrained_model(self):
        """Load pre-trained BERT model as fallback"""
        try:
            logger.info("Loading pre-trained BERT model...")
            model_name = "bert-base-uncased"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
            logger.info("Pre-trained BERT model loaded")
        except Exception as e:
            logger.error(f"Error loading pre-trained model: {e}")
    
    def predict_with_bert(self, text):
        """Predict authenticity using BERT model"""
        try:
            if not self.tokenizer or not self.model:
                return {"prediction": "UNKNOWN", "confidence": 0.0}
            
            # Tokenize input
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding='max_length',
                max_length=512,
                return_tensors='pt'
            )
            
            # Get prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                prediction = torch.argmax(probabilities, dim=-1).item()
                confidence = probabilities[0][prediction].item()
            
            # Convert prediction to label
            if self.use_custom_model and self.label_encoder:
                # Use custom label encoder
                label = self.label_encoder.inverse_transform([prediction])[0]
            else:
                # Use standard labels
                label = 'genuine' if prediction == 1 else 'forged'
            
            return {
                "prediction": label.upper(),
                "confidence": confidence,
                "probabilities": probabilities[0].tolist()
            }
        
        except Exception as e:
            logger.error(f"BERT prediction error: {e}")
            return {"prediction": "UNKNOWN", "confidence": 0.0}
    
    def predict_with_cnn(self, image_path):
        """Predict authenticity using CNN model"""
        try:
            if not self.cnn_model:
                return {"prediction": "UNKNOWN", "confidence": 0.0}
            
            # Preprocess image
            import cv2
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = cv2.resize(image, (224, 224))
            image = image.astype(np.float32) / 255.0
            image = np.expand_dims(image, axis=0)
            
            # Get prediction
            prediction = self.cnn_model.predict(image)[0][0]
            confidence = float(prediction)
            
            # Convert to label
            label = 'genuine' if confidence > 0.5 else 'forged'
            final_confidence = confidence if confidence > 0.5 else 1 - confidence
            
            return {
                "prediction": label.upper(),
                "confidence": final_confidence
            }
        
        except Exception as e:
            logger.error(f"CNN prediction error: {e}")
            return {"prediction": "UNKNOWN", "confidence": 0.0}
    
    def predict_authenticity(self, text, entities, image_path=None):
        """Enhanced prediction using multiple models"""
        results = {}
        
        # BERT prediction
        bert_result = self.predict_with_bert(text)
        results['bert'] = bert_result
        
        # CNN prediction (if image provided and model available)
        if image_path and self.cnn_model:
            cnn_result = self.predict_with_cnn(image_path)
            results['cnn'] = cnn_result
        
        # Combine predictions
        if 'cnn' in results and 'bert' in results:
            # Weighted ensemble
            bert_weight = 0.6
            cnn_weight = 0.4
            
            # Convert to numeric scores
            bert_score = 1.0 if bert_result['prediction'] == 'GENUINE' else 0.0
            cnn_score = 1.0 if cnn_result['prediction'] == 'GENUINE' else 0.0
            
            combined_score = (bert_weight * bert_score + cnn_weight * cnn_score)
            combined_confidence = (bert_weight * bert_result['confidence'] + 
                                 cnn_weight * cnn_result['confidence'])
            
            final_prediction = 'GENUINE' if combined_score > 0.5 else 'FORGED'
            
            return {
                'prediction': final_prediction,
                'confidence': combined_confidence,
                'models_used': ['bert', 'cnn'],
                'individual_results': results
            }
        else:
            # Use only available model
            return bert_result
    
    def get_model_info(self):
        """Get information about loaded models"""
        info = {
            'use_custom_model': self.use_custom_model,
            'bert_available': self.tokenizer is not None and self.model is not None,
            'cnn_available': self.cnn_model is not None,
            'model_path': self.model_path
        }
        
        # Add training summary if available
        summary_path = os.path.join(self.model_path, "training_summary.json")
        if os.path.exists(summary_path):
            import json
            with open(summary_path, 'r') as f:
                info['training_summary'] = json.load(f)
        
        return info
