Azure OCR Pre-Consume Script for Paperless-ngx

This script enables Azure Document Intelligence (prebuilt-read model) as the OCR engine for Paperless-ngx. It generates a searchable PDF by overlaying recognized text onto the original document. Empty pages are removed based on visual and textual content.

Features
	•	✅ Uses Azure Document Intelligence (v4.0+ endpoint)
	•	✅ Adds invisible text overlay using PyMuPDF
	•	✅ Replaces the working file directly (DOCUMENT_WORKING_PATH)
	•	✅ Skips Paperless’ internal OCR when text is detected
	•	✅ Removes empty pages (low pixel content and <5 characters)
	•	✅ Optional character cutoff for OCR content (default: 15,000)
	•	✅ Detailed logging in paperless.log

Configuration

The script uses the following environment variables:

Variable	Description	Required
AZURE_FORM_RECOGNIZER_ENDPOINT	Endpoint of your Azure resource	Yes
AZURE_FORM_RECOGNIZER_KEY	Azure API Key	Yes
OCR_CONTENT_CUTOFF	(Optional) Max character count (default: 15000)	No
PAPERLESS_LOGGING_DIR	(Optional) Path to logging directory	No
PAPERLESS_DATA_DIR	Used if PAPERLESS_LOGGING_DIR is not set	No

Installation (Bare Metal)
	1.	Install system dependencies:

sudo apt install python3-pip poppler-utils
pip install azure-ai-formrecognizer pymupdf

	2.	Save the script as pre_consume_azure_ocr.py, make it executable:

chmod +x /opt/azure_ocr_preconsume/pre_consume_azure_ocr.py

	3.	Set environment variables in your systemd unit or /etc/environment, e.g.:

AZURE_FORM_RECOGNIZER_ENDPOINT=https://<your-endpoint>.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=<your-key>
OCR_CONTENT_CUTOFF=12000

	4.	Register the script in Paperless settings as a pre-consume hook.

Docker Setup

If running inside the Paperless Docker container:
	1.	Mount the script into the container:

  volumes:
    - ./azure_ocr_preconsume:/scripts/azure_ocr_preconsume

	2.	Define environment variables in docker-compose.override.yml or .env:

environment:
  AZURE_FORM_RECOGNIZER_ENDPOINT: https://<your-endpoint>.cognitiveservices.azure.com/
  AZURE_FORM_RECOGNIZER_KEY: <your-key>
  OCR_CONTENT_CUTOFF: 12000

	3.	Reference the script path in Paperless settings:

  PAPERLESS_CONSUMER_PRE_CONSUME_SCRIPT: /scripts/azure_ocr_preconsume/pre_consume_azure_ocr.py

Notes
	•	Azure Document Intelligence must support PDF input (v4.0+ REST API).
	•	Logging entries are prefixed with [azure.ocr] for easy filtering.

⸻

MIT License © 2025