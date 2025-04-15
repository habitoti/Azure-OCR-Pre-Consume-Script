# Azure OCR Pre-Consume Script for Paperless-ngx

This script allows Paperless-ngx to use Azure Document Intelligence instead of local OCR (Tesseract).

## Features

- Accepts PDFs or images (JPG, PNG, TIFF)
- Sends documents to Azure Form Recognizer
- Extracts OCR text and overlays it invisibly on the original PDF
- Returns the new PDF for Paperless-ngx to consume

## Usage

### 1. Clone and set up

```bash
git clone <this-repo-url>
cd azure_ocr_preconsume
pip install -r requirements.txt
chmod +x pre_consume_azure_ocr.py
```

### 2. Set your Azure credentials


Add to paperless.conf (bare metal) or to Docker setup:

``` Environment
PAPERLESS_PRE_CONSUME_SCRIPT=/path/to/pre_consume_azure_ocr.py
AZURE_FORM_RECOGNIZER_ENDPOINT="https://<your-endpoint>.cognitiveservices.azure.com/"
AZURE_FORM_RECOGNIZER_KEY="<your-key>"
```

Paperless will now use this script before importing a document.

## License

MIT
