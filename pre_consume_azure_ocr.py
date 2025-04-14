#!/usr/bin/env python3
import sys
import os
import tempfile
import fitz  # PyMuPDF
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from utils import image_to_pdf

# Azure Credentials from ENV
endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY")

if not endpoint or not key:
    print("Azure credentials not set", file=sys.stderr)
    sys.exit(1)

client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

def run_azure_ocr(pdf_path):
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

def remove_empty_pages(pdf_path, texts, out_path):
    doc = fitz.open(pdf_path)
    for i in reversed(range(len(doc))):  # rückwärts, damit Indizes stabil bleiben
        if i >= len(texts) or len(texts[i].strip()) < 5:
            doc.delete_page(i)
    doc.save(out_path)

def main():
    input_path = sys.argv[1]
    file_ext = os.path.splitext(input_path)[1].lower()
    temp_dir = tempfile.mkdtemp()
    
    if file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        temp_pdf = os.path.join(temp_dir, "converted.pdf")
        image_to_pdf(input_path, temp_pdf)
        source_pdf = temp_pdf
    else:
        source_pdf = input_path

    texts = run_azure_ocr(source_pdf)
    ocr_pdf = os.path.join(temp_dir, "with_ocr.pdf")
    cleaned_pdf = input_path.replace(".pdf", "_ocr_cleaned.pdf")

    overlay_text(source_pdf, texts, ocr_pdf)
    remove_empty_pages(ocr_pdf, texts, cleaned_pdf)

    print(cleaned_pdf)

if __name__ == "__main__":
    main()
