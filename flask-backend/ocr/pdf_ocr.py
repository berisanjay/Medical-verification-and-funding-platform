from pdf2image import convert_from_path
import pytesseract
import os

POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"

def ocr_pdf(pdf_path):
    text = ""
    images = convert_from_path(
        pdf_path,
        dpi=300,
        poppler_path=POPPLER_PATH
    )

    for img in images:
        text += pytesseract.image_to_string(img)

    return text
