#!/usr/bin/env python3
import sys
import os
import fitz  # PyMuPDF
import logging
import tempfile
import shutil
import requests
from azure.core.credentials import AzureKeyCredential

# Logging setup (Paperless style)
log_path = "/opt/paperless/data/log/paperless.log"
logger = logging.getLogger("azure.ocr")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_path)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Azure setup
endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY")

def is_visually_empty(page, threshold=10):
    pix = page.get_pixmap(dpi=50, colorspace="gray")
    pixel_data = pix.samples
    nonwhite_pixels = sum(1 for px in pixel_data if px < 250)
    return nonwhite_pixels < threshold

def remove_empty_pages(pdf_path):
    doc = fitz.open(pdf_path)
    removed = 0
    for i in reversed(range(len(doc))):
        text = doc[i].get_text().strip()
        if len(text) < 5 and is_visually_empty(doc[i]):
            doc.delete_page(i)
            removed += 1
    doc.save(pdf_path)
    return removed

def request_searchable_pdf(input_pdf, output_pdf):
    if not endpoint or not key:
        logger.error("Azure credentials not set.")
        sys.exit(1)

    url = f"{endpoint}/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31-preview&outputContentFormat=application/pdf"
    headers = {
        "Content-Type": "application/pdf",
        "Ocp-Apim-Subscription-Key": key
    }

    with open(input_pdf, "rb") as f:
        response = requests.post(url, headers=headers, data=f)

    if response.status_code != 200:
        logger.error(f"Azure OCR request failed: {response.status_code} {response.text}")
        sys.exit(1)

    with open(output_pdf, "wb") as f:
        f.write(response.content)

    logger.debug("Azure OCR PDF saved to: %s", output_pdf)

def main():
    input_path = sys.argv[1]
    logger.info(f"Start Azure OCR for: {input_path}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output_pdf = os.path.join(tmpdir, "azure_ocr_output.pdf")

            request_searchable_pdf(input_path, temp_output_pdf)
            logger.info("Azure OCR request successful")

            removed = remove_empty_pages(temp_output_pdf)
            logger.info(f"Removed {removed} empty pages")

            shutil.copyfile(temp_output_pdf, input_path)
            logger.info(f"Original file replaced with Azure searchable PDF: {input_path}")

            print(input_path)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
