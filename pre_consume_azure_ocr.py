#!/usr/bin/env python3
import sys
import os
import fitz  # PyMuPDF
import logging
import tempfile
import shutil
import time
import requests

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

def log_pdf_info(pdf_path):
    try:
        size_kb = os.path.getsize(pdf_path) / 1024
        logger.info(f"Final PDF size: {size_kb:.1f} KB")

        doc = fitz.open(pdf_path)
        all_text = ""
        for page in doc:
            all_text += page.get_text()

        logger.debug(f"Extracted OCR text from final PDF:\n{all_text[:3000]}{'...' if len(all_text) > 3000 else ''}")
    except Exception as e:
        logger.warning(f"Failed to log PDF info: {e}")

def request_searchable_pdf(input_pdf, output_pdf, max_wait=30):
    if not endpoint or not key:
        logger.error("Azure credentials not set.")
        sys.exit(1)

    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze"           "?_overload=analyzeDocument&api-version=2024-11-30&output=pdf"

    headers = {
        "Content-Type": "application/pdf",
        "Ocp-Apim-Subscription-Key": key
    }

    with open(input_pdf, "rb") as f:
        response = requests.post(url, headers=headers, data=f)

    if response.status_code == 202:
        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            logger.error("No Operation-Location header in response.")
            sys.exit(1)

        logger.info("Azure accepted request, waiting for processing...")

        elapsed = 0
        while elapsed < max_wait:
            time.sleep(1)
            elapsed += 1
            poll = requests.get(operation_location, headers={"Ocp-Apim-Subscription-Key": key})
            poll_json = poll.json()
            status = poll_json.get("status", "").lower()
            logger.debug(f"Polling attempt at {elapsed}s: status={status}")
            if status == "succeeded":
                try:
                    result_url = poll_json["analyzeResult"]["contentUrl"]
                except KeyError:
                    logger.error("No 'contentUrl' found in analyzeResult")
                    sys.exit(1)

                logger.debug(f"Result PDF URL: {result_url}")
                result_response = requests.get(result_url)
                if result_response.status_code == 200:
                    with open(output_pdf, "wb") as out:
                        out.write(result_response.content)
                    return
                else:
                    logger.error(f"Failed to download result PDF: {result_response.status_code}")
                    sys.exit(1)
            elif status == "failed":
                logger.error("Azure OCR failed during processing.")
                sys.exit(1)

        logger.error("Azure OCR polling timed out after %d seconds.", max_wait)
        sys.exit(1)

    else:
        logger.error(f"Azure OCR request failed: {response.status_code} {response.text}")
        sys.exit(1)

def main():
    input_path = sys.argv[1]
    logger.info(f"Start Azure OCR for: {input_path}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output_pdf = os.path.join(tmpdir, "azure_ocr_output.pdf")

            request_searchable_pdf(input_path, temp_output_pdf)
            logger.info("Azure OCR processing and download successful")

            removed = remove_empty_pages(temp_output_pdf)
            logger.info(f"Removed {removed} empty pages")

            shutil.copyfile(temp_output_pdf, input_path)
            logger.info(f"Original file replaced with Azure searchable PDF: {input_path}")

            log_pdf_info(input_path)

            print(input_path)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
