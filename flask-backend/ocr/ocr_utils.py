from ocr.ocr import run_ocr
def run_ocr(file_path):
    """
    Converts image/PDF page to text using Tesseract OCR
    """
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    return text
