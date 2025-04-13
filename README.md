# Azure OCR Pre-Consume Script for Paperless-ngx

This script allows Paperless-ngx to use Azure Document Intelligence instead of local OCR (Tesseract).

## Features

- Accepts PDFs or images (JPG, PNG, TIFF)
- Sends documents to Azure Form Recognizer
- Extracts OCR text and overlays it invisibly on the original PDF
- Returns the new PDF for Paperless-ngx to consume

## Usage

### 1. Clone and set up

```bas
git clone <your-repo-url>
cd azure_ocr_preconsume
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your Azure credentials

```bash
export AZURE_FORM_RECOGNIZER_ENDPOINT="https://<your-endpoint>.cognitiveservices.azure.com/"
export AZURE_FORM_RECOGNIZER_KEY="<your-key>"
```

### 3. Configure Paperless-ngx

Add to your environment:

```bash
export PAPERLESS_CONSUMER_PRE_CONSUME_SCRIPT=/path/to/pre_consume_azure_ocr.py
```

Paperless will now use this script before importing a document.

## License

MIT
