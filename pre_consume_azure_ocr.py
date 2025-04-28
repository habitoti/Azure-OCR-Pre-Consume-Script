#!/usr/bin/env python3
import sys
import os
import traceback
import tempfile
import fitz  # PyMuPDF
import logging
import shutil
from pathlib import Path
from PIL import Image

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

# Logging setup
log_dir = "/usr/src/paperless/data" # hardcoded Docker install default
log_dir = f"{os.environ.get('PAPERLESS_DATA_DIR', log_dir)}/log"
log_dir = os.environ.get("PAPERLESS_LOGGING_DIR", log_dir)
log_path = f"{log_dir}/paperless.log"
logger = logging.getLogger("azure.ocr")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")    
try:
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    # Fallback auf STDERR
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.error(f"Could not write to log file at {log_path}, using stderr. Reason: {e}")

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


def main():

    if not endpoint or not key:
        logger.error("❌ Azure credentials not set")
        sys.exit(1)

    input_path = os.environ.get("DOCUMENT_WORKING_PATH")
    if not input_path:
        logger.error("❌ DOCUMENT_WORKING_PATH not set")
        sys.exit(1)

    src_file = Path(input_path).resolve()
    if not src_file.is_file():
        logger.error(f"❌ Input file missing: {src_file}")
        sys.exit(1)

    if not src_file.suffix.lower() == ".pdf":
        logger.info("Non-PDF input – skipping Azure OCR, letting Paperless handle it.")
        print(src_file)
        return

    if is_pdf_searchable(src_file):
        logger.info("PDF already contains searchable text – skipping Azure OCR")
        print(src_file)
        return

    if cutoff_limit > 0:
        logger.info(f"Start OCR with text cutoff at {cutoff_limit} chars for {src_file}")
    else:
        logger.info(f"Start OCR for {src_file}")

    texts = run_azure_ocr(src_file)

    # text overlay needs to be written to a different tmp-file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=os.path.dirname(input_path)) as tmp:
        tmp_pdf = Path(tmp.name)

    overlay_text(src_file, texts, tmp_pdf)
    logger.debug("Overlay text applied to {tmp_pdf}")

    shutil.move(tmp_pdf, src_file)
    logger.debug("Overlay file moved back to input")

    size_kb = os.path.getsize(src_file) / 1024
    logger.debug(f"Final PDF size: {size_kb:.1f} KB")

    print(src_file)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error(f"❌ {exc}")
        traceback.print_exc()
        sys.exit(1)
