"""
Train Medical Document Models
Run this script to train models on your hospital documents
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.medical_document_trainer import MedicalDocumentTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main training function"""
    logger.info("🏥 Starting Medical Document Model Training")
    logger.info("=" * 50)
    
    # Initialize trainer
    trainer = MedicalDocumentTrainer()
    
    # Check training data
    images_path = trainer.images_path
    genuine_path = os.path.join(images_path, "genuine")
    forged_path = os.path.join(images_path, "forged")
    
    logger.info(f"Training data path: {images_path}")
    logger.info(f"Genuine documents folder: {genuine_path}")
    logger.info(f"Forged documents folder: {forged_path}")
    
    # Count documents
    genuine_count = len([f for f in os.listdir(genuine_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff'))]) if os.path.exists(genuine_path) else 0
    forged_count = len([f for f in os.listdir(forged_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.tiff'))]) if os.path.exists(forged_path) else 0
    
    logger.info(f"Found {genuine_count} genuine documents")
    logger.info(f"Found {forged_count} forged documents")
    
    if genuine_count == 0:
        logger.error("❌ No genuine documents found!")
        logger.info(f"Please place your genuine hospital documents in: {genuine_path}")
        logger.info("Supported formats: .jpg, .jpeg, .png, .pdf, .tiff")
        return
    
    if forged_count == 0:
        logger.warning("⚠️  No forged documents found!")
        logger.info("The model will train with only genuine documents (unsupervised learning)")
        logger.info("For better results, add some forged/fake documents to: {forged_path}")
    
    # Start training
    try:
        logger.info("🚀 Starting model training...")
        summary = trainer.train_all_models()
        
        logger.info("✅ Training completed successfully!")
        logger.info("=" * 50)
        logger.info("Training Summary:")
        logger.info(f"  - Total documents: {summary['total_documents']}")
        logger.info(f"  - Genuine documents: {summary['genuine_documents']}")
        logger.info(f"  - Forged documents: {summary['forged_documents']}")
        logger.info(f"  - CNN model trained: {summary['models_trained']['cnn']}")
        logger.info(f"  - BERT model trained: {summary['models_trained']['bert']}")
        logger.info(f"  - Models saved to: {trainer.model_path}")
        
        logger.info("🎉 Your models are now ready to use!")
        logger.info("The system will automatically use your trained models for document verification.")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        logger.error("Please check your training data and try again.")

if __name__ == "__main__":
    main()
