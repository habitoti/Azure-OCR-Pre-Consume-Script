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
log_dir = "/usr/src/paperless/data" # hardcoded Docker install default
log_dir = f"{os.environ.get('PAPERLESS_DATA_DIR', log_dir)}/log"
log_dir = os.environ.get("PAPERLESS_LOGGING_DIR", log_dir)
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

# OCR Content Cutoff
DEFAULT_CUTOFF = 0 # i.e. no cutoff
cutoff_limit = int(os.environ.get("OCR_CONTENT_CUTOFF", DEFAULT_CUTOFF))

def is_pdf_searchable(pdf_path):
    with fitz.open(pdf_path) as doc:
        for page in doc:
            if page.get_text().strip():
                return True
    return False

def run_azure_ocr(pdf_path):
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", document=f)
        result = poller.result()

    pages_text = []
    current_length = 0
    for page in result.pages:
        page_text = "\n".join([line.content for line in page.lines])
        text_len = len(page_text)

        # Skip or trim based on cutoff
        if cutoff_limit > 0:
            if current_length >= cutoff_limit:
                break
            if current_length + text_len > cutoff_limit:
                remaining = cutoff_limit - current_length
                page_text = page_text[:remaining]
                text_len = len(page_text)  # adjust length after trimming

        pages_text.append(page_text)
        current_length += text_len

    if cutoff_limit > 0:
        logger.info(f"OCR successful, {len(pages_text)} pages returned (cutoff at {cutoff_limit} chars), total characters: {current_length}")
    else:
        logger.info(f"OCR successful, {len(pages_text)} pages returned, total characters: {current_length}")
        
    return pages_text

def overlay_text(pdf_path, texts, out_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        if i < len(texts):
            text = texts[i]
            rect = page.rect

            # Insert safe word on first page in white, visible to PDF parsers
            if i == 0:
                page.insert_text(
                    (1, 1),
                    "azure-ocr",
                    fontsize=1.0,
                    color=(1, 1, 1),
                    render_mode=0,
                    overlay=True
                )

            # Insert actual OCR content as invisible
            page.insert_textbox(
                rect,
                text,
                fontsize=1.0,
                color=(1, 1, 1),  # Ignored in invisible render mode
                render_mode=3,
                overlay=True
            )
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

    if cutoff_limit > 0:
        logger.info(f"Start OCR with text cutoff at {cutoff_limit} chars for {input_path}")
    else:
        logger.info(f"Start OCR for {input_path}")

    if not endpoint or not key:
        logger.error("Azure credentials not set.")
        sys.exit(1)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_pdf = os.path.join(temp_dir, "ocr_overlay.pdf")
            final_pdf = os.path.join(temp_dir, "cleaned.pdf")

            if is_pdf_searchable(input_path):
                logger.info("PDF already contains searchable text – skipping Azure OCR")
            else:
                texts = run_azure_ocr(input_path)
                overlay_text(input_path, texts, temp_pdf)
                logger.debug("Overlay text applied")

                removed = remove_empty_pages(temp_pdf, texts, final_pdf)
                if removed > 0:
                    logger.info(f"Removed {removed} empty pages")

                shutil.copyfile(final_pdf, input_path)
                logger.debug("Final file written back")

                size_kb = os.path.getsize(input_path) / 1024
                logger.debug(f"Final PDF size: {size_kb:.1f} KB")

            print(input_path)

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
