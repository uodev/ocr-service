# OCR Service

FastAPI-based OCR service with support for EasyOCR and LLM Vision OCR.

## Features

- **EasyOCR**: Offline text extraction with LLM-powered field parsing
- **LLM Vision OCR**: Direct text and field extraction using GPT-4o Vision API
- **Flexible Field Extraction**: Multiple input formats for defining extraction fields
- **Dockerized**: Easy deployment with Docker Compose
- **File Validation**: Supported formats and size validation

## Supported File Types

- Images: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`
- Documents: `.pdf`

Maximum file size: 10MB

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key

### Local Development

```bash
# Environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Install dependencies
uv sync

# Run server
uv run uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
# Build and run
docker compose up --build

# Or run in background
docker compose up -d
```

## API Endpoints

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "ocr-service"
}
```

### File Upload

```http
POST /file-upload
Content-Type: multipart/form-data

file: <image_file>
```

Response:
```json
{
  "file_id": "218fb967-e004-4671-8dbf-0405ff9401b3"
}
```

### OCR Processing

```http
POST /ocr
Content-Type: application/json
```

#### Field Format Options

**1. Simple Format (Type only):**
```json
{
  "file_id": "7336c241-e13a-4875-b41a-71a3873daa4a",
  "ocr": "easyocr",
  "fields": {
    "tax_id": "integer",
    "company_name": "string",
    "company_address": "string"
  }
}
```

**2. Description Format:**
```json
{
  "file_id": "7336c241-e13a-4875-b41a-71a3873daa4a",
  "ocr": "llm_ocr",
  "fields": {
    "tax_id": "10-digit tax identification number",
    "company_name": "Company or business name",
    "company_address": "Full address information"
  }
}
```

**3. Detailed Format (Full control):**
```json
{
  "file_id": "7336c241-e13a-4875-b41a-71a3873daa4a",
  "ocr": "easyocr",
  "fields": {
    "tax_id": {
      "name": "Tax ID",
      "description": "Extract the tax identification number from the document",
      "type": "integer"
    },
    "company_name": {
      "name": "Company Name",
      "description": "Extract the company name",
      "type": "string"
    }
  }
}
```

#### OCR Options

| Value | Description |
|-------|-------------|
| `easyocr` | EasyOCR (local) + LLM parsing - Fast and cost-effective |
| `llm_ocr` | GPT-4o Vision - For complex documents and handwriting |

#### Response

```json
{
  "file_id": "7336c241-e13a-4875-b41a-71a3873daa4a",
  "ocr": "easyocr",
  "result": {
    "tax_id": 1234567890,
    "company_name": "ACME Ltd.",
    "company_address": "123 Main Street, New York, NY"
  },
  "raw_ocr": "TAX CERTIFICATE Tax ID: 1234567890 ACME Ltd. 123 Main Street, New York, NY ..."
}
```

## OCR Methods

| Method | Description | Speed | Cost |
|--------|-------------|-------|------|
| `easyocr` | Local OCR + LLM parsing | Fast | Low (only LLM for parsing) |
| `llm_ocr` | GPT-4o Vision API | Slower | Higher (full Vision API) |

### When to use which?

- **easyocr**: Good for clear documents with readable text. Faster and cheaper.
- **llm_ocr**: Better for complex layouts, handwriting, or when EasyOCR struggles.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM parsing | Yes |
| `PORT` | Server port (default: 8000) | No |

## Project Structure

```
ocr-case/
├── app/
│   ├── main.py           # FastAPI application
│   ├── schemas.py        # Pydantic models
│   └── services/
│       └── ocr_service.py # OCR engine
├── storage/              # Uploaded files
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## License

MIT
