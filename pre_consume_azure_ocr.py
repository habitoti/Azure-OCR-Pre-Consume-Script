#!/usr/bin/env python3
import sys
import os
import tempfile
import fitz  # PyMuPDF
import logging
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from utils import image_to_pdf

# Logging setup (Paperless-Style)
log_path = "/opt/paperless/data/log/paperless.log"
logger = logging.getLogger("azure.ocr")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_path)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Azure credentials
endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY")

def run_azure_ocr(pdf_path):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Sending file to Azure OCR: {pdf_path}")
        logger.debug(f"OCR Endpoint: {endpoint}")
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", document=f)
        result = poller.result()

    pages_text = []
    for page in result.pages:
        page_text = "\n".join([line.content for line in page.lines])
        pages_text.append(page_text)
    return pages_text

def overlay_text(pdf_path, texts, out_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        if i < len(texts):
            text = texts[i]
            rect = page.rect
            page.insert_textbox(rect, text, fontsize=0.1, overlay=False)
    doc.save(out_path)

def is_visually_empty(page, threshold=10):
    pix = page.get_pixmap(dpi=50, colorspace="gray")
    pixel_data = pix.samples
    nonwhite_pixels = sum(1 for px in pixel_data if px < 250)
    return nonwhite_pixels < threshold

def remove_empty_pages(pdf_path, texts, out_path):
    doc = fitz.open(pdf_path)
    removed = 0
    for i in reversed(range(len(doc))):
        text_empty = i >= len(texts) or len(texts[i].strip()) < 5
        visual_empty = is_visually_empty(doc[i])
        if text_empty and visual_empty:
            doc.delete_page(i)
            removed += 1
    doc.save(out_path)
    return removed

def main():
    input_path = sys.argv[1]
    logger.info(f"Start pre_consume script for: {input_path}")

    file_ext = os.path.splitext(input_path)[1].lower()
    temp_dir = tempfile.mkdtemp()

    if not endpoint or not key:
        logger.error("Azure credentials not set")
        sys.exit(1)

    global client
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

    try:
        if file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            temp_pdf = os.path.join(temp_dir, "converted.pdf")
            image_to_pdf(input_path, temp_pdf)
            source_pdf = temp_pdf
        else:
            source_pdf = input_path

        texts = run_azure_ocr(source_pdf)
        total_chars = sum(len(t) for t in texts)
        logger.info(f"OCR successful, {len(texts)} pages returned, {total_chars} characters")

        ocr_pdf = os.path.join(temp_dir, "with_ocr.pdf")
        cleaned_pdf = input_path.replace(".pdf", "_ocr_cleaned.pdf")

        overlay_text(source_pdf, texts, ocr_pdf)
        logger.info("Overlay text complete")

        removed_pages = remove_empty_pages(ocr_pdf, texts, cleaned_pdf)
        logger.info(f"Empty pages removed: {removed_pages}; final file: {cleaned_pdf}")

        logger.info("Script finished successfully")
        print(cleaned_pdf)

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
