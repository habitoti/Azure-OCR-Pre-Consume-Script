#!/usr/bin/env python3
import sys
import os
import tempfile
import fitz  # PyMuPDF
import logging
import shutil
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient


# Logging setup
log_dir = os.environ.get("PAPERLESS_LOGGING_DIR", f"{os.environ.get("PAPERLESS_DATA_DIR")}/log")
log_path = f"{log_dir}/paperless.log"
logger = logging.getLogger("azure.ocr")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_path)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Azure credentials
endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY")

def run_azure_ocr(pdf_path):
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", document=f)
        result = poller.result()

    pages_text = []
    for page in result.pages:
        page_text = "\n".join([line.content for line in page.lines])
        pages_text.append(page_text)

    total_chars = sum(len(t) for t in pages_text)
    logger.info(f"OCR successful, {len(pages_text)} pages returned, {total_chars} characters")
    return pages_text

def overlay_text(pdf_path, texts, out_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        if i < len(texts):
            text = texts[i]
            rect = page.rect
            page.insert_textbox(rect, text, fontsize=1.0, overlay=True)
    doc.save(out_path, garbage=4, deflate=True, clean=True, incremental=False)

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
    input_path = os.environ.get("DOCUMENT_WORKING_PATH")
    if not input_path:
        logger.error("DOCUMENT_WORKING_PATH not set.")
        sys.exit(1)

    logger.debug(f"Start simple overlay OCR on: {input_path}")

    if not endpoint or not key:
        logger.error("Azure credentials not set.")
        sys.exit(1)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_pdf = os.path.join(temp_dir, "ocr_overlay.pdf")
            final_pdf = os.path.join(temp_dir, "cleaned.pdf")

            texts = run_azure_ocr(input_path)
            overlay_text(input_path, texts, temp_pdf)
            # logger.debug("Simple text overlay applied using insert_textbox")

            removed = remove_empty_pages(temp_pdf, texts, final_pdf)
            if removed > 0: 
                logger.info(f"Removed {removed} empty pages")

            shutil.copyfile(final_pdf, input_path)
            logger.debug("Replaced working file with OCR-enhanced version")

            size_kb = os.path.getsize(input_path) / 1024
            logger.debug(f"Final PDF size: {size_kb:.1f} KB")

            print(input_path)

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
