# Azure OCR Pre-Consume Script for Paperless-ngx

This script enables Azure Document Intelligence as the OCR engine for [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx). It generates a searchable PDF by overlaying recognized text onto the original document. Empty pages are removed based on visual and textual content.

## Features

- ✅ Uses Azure Document Intelligence for high-quality OCR, includinhg handwriting
- ✅ Adds invisible text overlay using `PyMuPDF`
- ✅ Removes (almost) empty pages, i.e. visually empty or with less than 5 characters recognizable text
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

Admittedly, I haven't tested the docker setup, as I am running it bare metal. So any feedback whether this setup (copy/pasted from elsewhere) works is appreciated, so I can update it accordingly.

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

- When you set a content cutoff, only as many pages as will fit into the total character limit will be made searchable for Paperless-ngx. As a rule of thumb, about 2000 characters make up a completly filled text page. You'll need about 500 tokens to have AI look at that page later on, e.g. with paperless-ai. So if you have for example an 8K token limit per prompt on your model (or just don't want to spend more per query), you'll be on the safe side with a 15-20k character limit, or about 8-10 pages (might be more or less depending on type of document). This leaves sufficient space for the actual prompt that describes what AI should do with the content.
- Azure Document Intelligence must support PDF input (v4.0+ REST API).
- Logging entries are prefixed with `[azure.ocr]` for easy filtering.

---

MIT License © 2025

