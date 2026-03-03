"""
Medical Document Training Pipeline
Trains models on your hospital documents for better authenticity detection
"""

import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import pytesseract
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime
import joblib
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import json

logger = logging.getLogger(__name__)

class MedicalDocumentTrainer:
    """Trains multiple models on medical documents"""
    
    def __init__(self, training_data_path="training_data"):
        self.training_data_path = training_data_path
        self.images_path = os.path.join(training_data_path, "images")
        self.model_path = os.path.join(training_data_path, "model")
        self.preprocessing_path = os.path.join(training_data_path, "preprocessing")
        
        # Create directories
        os.makedirs(self.images_path, exist_ok=True)
        os.makedirs(os.path.join(self.images_path, "genuine"), exist_ok=True)
        os.makedirs(os.path.join(self.images_path, "forged"), exist_ok=True)
        os.makedirs(self.model_path, exist_ok=True)
        os.makedirs(self.preprocessing_path, exist_ok=True)
        
        # Initialize models
        self.cnn_model = None
        self.bert_model = None
        self.label_encoder = LabelEncoder()
        
    def organize_training_data(self):
        """Organize training data from images folder"""
        logger.info("Organizing training data...")
        
        genuine_path = os.path.join(self.images_path, "genuine")
        forged_path = os.path.join(self.images_path, "forged")
        
        # Count images in each category
        genuine_count = len([f for f in os.listdir(genuine_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff'))])
        forged_count = len([f for f in os.listdir(forged_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff'))])
        
        logger.info(f"Found {genuine_count} genuine documents and {forged_count} forged documents")
        
        # Create labels CSV
        labels_data = []
        
        # Process genuine documents
        for filename in os.listdir(genuine_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff')):
                labels_data.append({
                    'filename': filename,
                    'filepath': os.path.join(genuine_path, filename),
                    'label': 'genuine'
                })
        
        # Process forged documents
        for filename in os.listdir(forged_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff')):
                labels_data.append({
                    'filename': filename,
                    'filepath': os.path.join(forged_path, filename),
                    'label': 'forged'
                })
        
        # Save labels
        labels_df = pd.DataFrame(labels_data)
        labels_path = os.path.join(self.training_data_path, "labels.csv")
        labels_df.to_csv(labels_path, index=False)
        logger.info(f"Created labels file: {labels_path}")
        
        return labels_df
    
    def preprocess_image(self, image_path, target_size=(224, 224)):
        """Preprocess image for CNN training"""
        try:
            # Read image
            if image_path.lower().endswith('.pdf'):
                # Convert PDF to image first
                import pdf2image
                images = pdf2image.convert_from_path(image_path)
                if images:
                    image = np.array(images[0])
                else:
                    return None
            else:
                image = cv2.imread(image_path)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resize
            image = cv2.resize(image, target_size)
            
            # Normalize
            image = image.astype(np.float32) / 255.0
            
            return image
        except Exception as e:
            logger.error(f"Error preprocessing {image_path}: {e}")
            return None
    
    def extract_text_features(self, image_path):
        """Extract text features using OCR"""
        try:
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image_path)
            
            # Basic text features
            features = {
                'text_length': len(text),
                'word_count': len(text.split()),
                'char_count': len(text.replace(' ', '')),
                'uppercase_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
                'digit_ratio': sum(1 for c in text if c.isdigit()) / max(len(text), 1),
                'special_char_ratio': sum(1 for c in text if not c.isalnum()) / max(len(text), 1),
                'text': text[:500]  # First 500 chars
            }
            
            return features
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            return None
    
    def create_cnn_model(self, input_shape=(224, 224, 3)):
        """Create CNN model for image classification"""
        model = models.Sequential([
            # Convolutional layers
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            
            # Flatten and dense layers
            layers.Flatten(),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        model.compile(optimizer='adam',
                     loss='binary_crossentropy',
                     metrics=['accuracy'])
        
        return model
    
    def train_cnn_model(self, labels_df):
        """Train CNN model on image data"""
        logger.info("Training CNN model...")
        
        # Prepare data
        images = []
        labels = []
        
        for _, row in labels_df.iterrows():
            image = self.preprocess_image(row['filepath'])
            if image is not None:
                images.append(image)
                labels.append(row['label'])
        
        if len(images) == 0:
            logger.error("No valid images found for training")
            return None
        
        # Convert to numpy arrays
        X = np.array(images)
        y = np.array(labels)
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
        
        # Create and train model
        self.cnn_model = self.create_cnn_model()
        
        # Train
        history = self.cnn_model.fit(
            X_train, y_train,
            epochs=20,
            batch_size=8,
            validation_data=(X_test, y_test),
            verbose=1
        )
        
        # Evaluate
        test_loss, test_acc = self.cnn_model.evaluate(X_test, y_test)
        logger.info(f"CNN Test Accuracy: {test_acc:.4f}")
        
        # Save model
        model_save_path = os.path.join(self.model_path, "cnn_model.h5")
        self.cnn_model.save(model_save_path)
        
        # Save label encoder
        encoder_save_path = os.path.join(self.model_path, "label_encoder.pkl")
        joblib.dump(self.label_encoder, encoder_save_path)
        
        # Plot training history
        self.plot_training_history(history, "cnn_training_history.png")
        
        return self.cnn_model
    
    def create_bert_model(self):
        """Create BERT model for text classification"""
        model_name = "bert-base-uncased"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
        
        return tokenizer, model
    
    def train_bert_model(self, labels_df):
        """Train BERT model on extracted text"""
        logger.info("Training BERT model...")
        
        # Extract text features
        texts = []
        labels = []
        
        for _, row in labels_df.iterrows():
            text_features = self.extract_text_features(row['filepath'])
            if text_features and text_features['text']:
                texts.append(text_features['text'])
                labels.append(row['label'])
        
        if len(texts) == 0:
            logger.error("No valid text found for training")
            return None
        
        # Create dataset
        class MedicalDocumentDataset(Dataset):
            def __init__(self, texts, labels, tokenizer, max_length=512):
                self.texts = texts
                self.labels = labels
                self.tokenizer = tokenizer
                self.max_length = max_length
                
                # Encode labels
                label_encoder = LabelEncoder()
                self.encoded_labels = label_encoder.fit_transform(labels)
                
            def __len__(self):
                return len(self.texts)
                
            def __getitem__(self, idx):
                text = self.texts[idx]
                label = self.encoded_labels[idx]
                
                encoding = self.tokenizer(
                    text,
                    truncation=True,
                    padding='max_length',
                    max_length=self.max_length,
                    return_tensors='pt'
                )
                
                return {
                    'input_ids': encoding['input_ids'].flatten(),
                    'attention_mask': encoding['attention_mask'].flatten(),
                    'labels': torch.tensor(label, dtype=torch.long)
                }
        
        # Create tokenizer and model
        tokenizer, model = self.create_bert_model()
        
        # Create dataset
        dataset = MedicalDocumentDataset(texts, labels, tokenizer)
        
        # Split dataset
        train_size = int(0.8 * len(dataset))
        test_size = len(dataset) - train_size
        train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=os.path.join(self.model_path, "bert_results"),
            num_train_epochs=3,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=os.path.join(self.model_path, "bert_logs"),
            logging_steps=10,
        )
        
        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset
        )
        
        # Train
        trainer.train()
        
        # Save model
        model_save_path = os.path.join(self.model_path, "bert_model")
        model.save_pretrained(model_save_path)
        tokenizer.save_pretrained(model_save_path)
        
        return model
    
    def plot_training_history(self, history, filename):
        """Plot training history"""
        plt.figure(figsize=(12, 4))
        
        # Plot training & validation accuracy
        plt.subplot(1, 2, 1)
        plt.plot(history.history['accuracy'])
        plt.plot(history.history['val_accuracy'])
        plt.title('Model Accuracy')
        plt.ylabel('Accuracy')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper left')
        
        # Plot training & validation loss
        plt.subplot(1, 2, 2)
        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model Loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper left')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.model_path, filename))
        plt.close()
    
    def train_all_models(self):
        """Train all models on the training data"""
        logger.info("Starting model training...")
        
        # Organize training data
        labels_df = self.organize_training_data()
        
        if len(labels_df) == 0:
            logger.error("No training data found!")
            return
        
        # Train CNN model
        cnn_model = self.train_cnn_model(labels_df)
        
        # Train BERT model
        bert_model = self.train_bert_model(labels_df)
        
        # Save training summary
        summary = {
            'training_date': datetime.now().isoformat(),
            'total_documents': len(labels_df),
            'genuine_documents': len(labels_df[labels_df['label'] == 'genuine']),
            'forged_documents': len(labels_df[labels_df['label'] == 'forged']),
            'models_trained': {
                'cnn': cnn_model is not None,
                'bert': bert_model is not None
            }
        }
        
        summary_path = os.path.join(self.model_path, "training_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Training completed!")
        logger.info(f"Training summary saved to: {summary_path}")
        
        return summary

# Usage example
if __name__ == "__main__":
    trainer = MedicalDocumentTrainer()
    summary = trainer.train_all_models()
    print("Training Summary:", summary)
