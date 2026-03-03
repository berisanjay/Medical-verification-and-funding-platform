"""
OCR Processing for Medical Documents
Supports PDF and Image files using Tesseract and pdf2image
"""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


class DocumentOCR:
    """OCR processor for medical documents"""
    
    def __init__(self):
        """Initialize OCR processor"""
        # Set Tesseract path for Windows (adjust if needed)
        if os.name == 'nt':  # Windows
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logger.info(f"Tesseract path set to: {tesseract_path}")
            else:
                logger.warning("Tesseract not found at default Windows path")
        
        # Verify Tesseract is available
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            raise RuntimeError("Tesseract OCR is not installed or not in PATH")
    
    def extract_text(self, filepath):
        """
        Extract text from document (PDF or Image)
        
        Args:
            filepath: Path to the document file
        
        Returns:
            Extracted text as string
        """
        try:
            # Determine file type
            file_extension = os.path.splitext(filepath)[1].lower()
            
            if file_extension == '.pdf':
                return self._extract_from_pdf(filepath)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.webp']:
                return self._extract_from_image(filepath)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
        
        except Exception as e:
            logger.error(f"OCR extraction error for {filepath}: {e}")
            raise
    
    def _extract_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Convert PDF to images
            # poppler_path needed for Windows
            poppler_path = None
            if os.name == 'nt':  # Windows
                potential_paths = [
                    r'C:\poppler\Library\bin',
                    r'C:\Program Files\poppler\Library\bin',
                    os.path.join(os.getcwd(), 'poppler', 'Library', 'bin')
                ]
                for path in potential_paths:
                    if os.path.exists(path):
                        poppler_path = path
                        break
            
            # Convert PDF pages to images
            if poppler_path:
                images = convert_from_path(pdf_path, poppler_path=poppler_path, dpi=300)
            else:
                images = convert_from_path(pdf_path, dpi=300)
            
            logger.info(f"Converted {len(images)} pages from PDF")
            
            # Extract text from each page
            all_text = []
            for i, image in enumerate(images):
                logger.info(f"Extracting text from page {i+1}")
                text = self._ocr_image(image)
                all_text.append(text)
            
            # Combine all pages
            combined_text = '\n\n'.join(all_text)
            logger.info(f"Extracted {len(combined_text)} characters from PDF")
            
            return combined_text
        
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise
    
    def _extract_from_image(self, image_path):
        """Extract text from image file"""
        try:
            logger.info(f"Processing image: {image_path}")
            
            # Open image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Perform OCR
            text = self._ocr_image(image)
            
            logger.info(f"Extracted {len(text)} characters from image")
            return text
        
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            raise
    
    def _ocr_image(self, image):
        """
        Perform OCR on a PIL Image object
        
        Args:
            image: PIL Image object
        
        Returns:
            Extracted text
        """
        try:
            # Configure Tesseract for better medical document recognition
            custom_config = r'--oem 3 --psm 6'
            
            # Perform OCR
            text = pytesseract.image_to_string(image, config=custom_config)
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"OCR error: {e}")
            raise
    
    def extract_with_confidence(self, filepath):
        """
        Extract text with confidence scores
        
        Returns:
            Dict with text and confidence data
        """
        try:
            # Get file extension
            file_extension = os.path.splitext(filepath)[1].lower()
            
            # Open image
            if file_extension == '.pdf':
                # For PDF, process first page only for confidence
                images = convert_from_path(filepath, dpi=300)
                image = images[0] if images else None
            else:
                image = Image.open(filepath)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
            
            if image is None:
                return {'text': '', 'confidence': 0}
            
            # Get OCR data with confidence
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Get text
            text = ' '.join([word for word in ocr_data['text'] if word.strip()])
            
            return {
                'text': text,
                'confidence': round(avg_confidence, 2),
                'word_count': len([w for w in ocr_data['text'] if w.strip()])
            }
        
        except Exception as e:
            logger.error(f"Confidence extraction error: {e}")
            return {'text': '', 'confidence': 0, 'word_count': 0}


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    ocr = DocumentOCR()
    
    # Test with a sample file (if exists)
    test_file = 'test_document.pdf'
    if os.path.exists(test_file):
        text = ocr.extract_text(test_file)
        print("Extracted Text:")
        print(text)
        print("\n" + "="*50)
        
        # Test with confidence
        result = ocr.extract_with_confidence(test_file)
        print(f"\nConfidence: {result['confidence']}%")
        print(f"Word Count: {result['word_count']}")
    else:
        print(f"Test file {test_file} not found")
