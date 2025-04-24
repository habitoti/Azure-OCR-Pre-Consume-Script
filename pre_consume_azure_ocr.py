#!/usr/bin/env python3
import sys
import os
import tempfile
import fitz  # PyMuPDF
import logging
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


def convert_image_to_pdf(image_path):
    img = Image.open(image_path).convert("RGB")
    fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    img.save(tmp_pdf_path, "PDF")
    return tmp_pdf_path

def prepare_pdf_for_ocr(input_path):
    # Return tuple: (actual_pdf_path, is_temp_file)
    if input_path.lower().endswith(".pdf"):
        return input_path, False
    else:
        logger.info(f"Converting {input_path} to PDF.")
        pdf_path = convert_image_to_pdf(input_path)
        return pdf_path, True

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
    doc.close()

def main():
    if len(sys.argv) != 2:
        logger.error("Usage: pre_consume_azure_ocr.py <input.pdf>")
        sys.exit(1)

    input_path = sys.argv[1]
    pdf_path, was_temp = prepare_pdf_for_ocr(input_path)

    if not endpoint or not key:
        logger.error("Azure credentials not set.")
        sys.exit(1)

    if is_pdf_searchable(pdf_path):
        logger.info("✔ PDF is already searchable – skipping Azure OCR.")
        print(input_path)
        return

    if cutoff_limit > 0:
        logger.info(f"Start OCR with text cutoff at {cutoff_limit} chars for {input_path}")
    else:
        logger.info(f"Start OCR for {input_path}")

    try:

        texts = run_azure_ocr(pdf_path)
        fd, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        overlay_text(pdf_path, texts, output_path)
        logger.debug("Overlay text applied")

        logger.info(f"Final output written to {output_path}")
        print(output_path)

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
