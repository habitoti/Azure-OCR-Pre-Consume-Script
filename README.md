# Azure OCR Pre-Consume Script for Paperless-ngx

This script enables Azure Document Intelligence as the OCR engine for [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx). It generates a searchable PDF by overlaying recognized text onto the original document. 
Azure Document Intelligence offers superior recognition quality—even for handwritten notes, receipts, or poor-quality scans. Pricing is very affordable, at approximately $1.40 per 1,000 pages, regardless of how much content each page contains. It’s also significantly faster than the built-in Tesseract OCR: even very long documents are processed in seconds.

Downstream from Paperless-ngx, I’m using the excellent [Paperless-AI](https://github.com/clusterzx/paperless-ai). Thanks to its flexible query mechanism, it delivers great results for tagging and metadata extraction—especially now that the OCR content is nearly perfect. However, as of now, Paperless-AI does not limit the amount of content passed into the prompt. Since my Azure OpenAI GPT-4o-mini model is limited to 8k tokens per prompt, very large documents may not be processed at all.

To address this, I’ve added an optional content cutoff that limits the amount of recognized text. In practice, most everyday documents are short enough, and even longer ones usually have the important content within the first few pages. Setting a cutoff of 15,000 to 20,000 characters helps reduce prompt size without sacrificing relevant context.

## Features

- ✅ Uses Azure Document Intelligence for high-quality OCR, including handwriting (for PDF document input only!)
- ✅ Adds invisible text overlay using `PyMuPDF`
- ✅ Optional character cutoff for OCR content to restrict content size and so number of tokens required for further AI processing (default: off). For caveats, see notes below.
- ✅ Detailed logging in `paperless.log`

## Configuration

The script uses the following configuration variables:

| Variable                       | Description                                 | Required |
|--------------------------------|---------------------------------------------|----------|
| `AZURE_FORM_RECOGNIZER_ENDPOINT` | Endpoint of your Azure resource             | Yes      |
| `AZURE_FORM_RECOGNIZER_KEY`      | Azure API Key                               | Yes      |
| `OCR_CONTENT_CUTOFF`             | Max character count (default: 0/no cutoff) | No   |

These paperless-ngx configuration variables need to be set:

| Variable                       | Description                                 | Required |
|--------------------------------|---------------------------------------------|----------|
| `PAPERLESS_OCR_MODE`             | Needs to be set to "skip" so that no additional OCR takes place afterwards | Yes   |
| `PAPERLESS_PRE_CONSUME_SCRIPT`   | Full path to the pre-consume script | Yes   |

## Installation (Bare Metal)

1. Install system dependencies:

```bash
sudo apt install python3-pip poppler-utils
pip install azure-ai-formrecognizer pymupdf
```

2. Save the script as `pre_consume_azure_ocr.py`, make it executable:

```bash
chmod +x /opt/azure_ocr_preconsume/pre_consume_azure_ocr.py
```

3. Set configuration:

```paperless.conf
AZURE_FORM_RECOGNIZER_ENDPOINT=https://<your-endpoint>.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=<your-key>
OCR_CONTENT_CUTOFF=15000
PAPERLESS_OCR_MODE=skip
PAPERLESS_PRE_CONSUME_SCRIPT=<full path of pre-consume script>
```

## Docker Setup

> **Note:** Admittedly, I haven't tested the docker setup, as I am running it bare metal. So any feedback whether this setup (copy/pasted from elsewhere) works is appreciated, so I can update it accordingly.

If running inside the Paperless Docker container:

1. Mount the script into the container:

```yaml
volumes:
  - ./azure_ocr_preconsume:/scripts/azure_ocr_preconsume
```

2. Define environment variables in `docker-compose.override.yml` or `.env`:

```yaml
environment:
  AZURE_FORM_RECOGNIZER_ENDPOINT: https://<your-endpoint>.cognitiveservices.azure.com/
  AZURE_FORM_RECOGNIZER_KEY: <your-key>
  OCR_CONTENT_CUTOFF: 15000
  PAPERLESS_OCR_MODE: skip
  PAPERLESS_PRE_CONSUME_SCRIPT: <full path of pre-consume script>
```

## Notes

- Supports for now only PDF documents (as Paperless-NGX doesn't allow for changing of filetype during the pre_consume step). Other formats are handed back untouched for Paperless to proceed scanning itself.
- When you set a content cutoff, only as many pages as fit within the total character limit will be made searchable by Paperless-ngx. As a rule of thumb, a fully filled text page contains roughly 2,000 characters. To process that content with AI tools like Paperless-AI, you’ll typically need around 500 tokens per page. For example, if your model has an 8k token limit per prompt (or if you simply want to reduce processing cost), a cutoff of 15,000 to 20,000 characters—equivalent to about 8–10 pages—is a safe and practical choice. The exact number of pages may vary depending on the document type and density. This approach also ensures there’s enough room left in the prompt for the actual instructions to the AI, such as what kind of tags or metadata should be extracted.
- Azure Document Intelligence must support PDF input (v4.0+ REST API).
- Logging entries are prefixed with `[azure.ocr]` for easy filtering.
- If the implemented fallback mechanisms to determine the path of the logfile don't work for your setup, you can set the PAPERLESS_LOGGING_DIR environment variable.

---

MIT License © 2025

