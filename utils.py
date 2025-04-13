import img2pdf
from PIL import Image
import os

def image_to_pdf(image_path, pdf_path):
    """Convert image (JPG, PNG) to PDF"""
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(image.filename))
    return pdf_path
