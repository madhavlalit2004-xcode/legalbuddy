# AI Legal Buddy

AI Legal Buddy is a FastAPI-based legal document assistant. It lets you upload PDF legal documents, indexes their text into a local ChromaDB vector store, and answers natural-language questions with relevant source chunks, legal insight tags, risk summaries, and an optional generated answer through Ollama.

This project is built for local-first legal document exploration. It is not a replacement for professional legal advice.

## Features

- PDF upload and ingestion through a FastAPI REST API.
- Text extraction with `pdfplumber`, with PyMuPDF fallback for PDFs where the first parser extracts too little text.
- Text cleaning that removes null characters, collapses spacing, and filters simple page-number lines.
- Smart chunking by headings, paragraphs, and token windows with configurable overlap.
- Embeddings with `sentence-transformers` using `all-MiniLM-L6-v2` by default.
- Hash-based embedding fallback when the SentenceTransformer model cannot be loaded.
- Persistent local vector search with ChromaDB and cosine similarity.
- Query scoping across all documents or one selected document.
- Rule-based legal insight extraction for obligations, penalties, termination, risks, definitions, deadlines, confidentiality, indemnification, and governing law.
- Risk aggregation across retrieved chunks.
- Optional answer generation through a local Ollama model.
- Extractive fallback answer generation when Ollama is unavailable.
- Single-file browser frontend for upload, document selection, search, result viewing, health checks, and deletion.
- Pydantic request and response validation.
- Structured logging through `structlog`.
- Pytest coverage for schemas, chunking, insight extraction, embeddings, routes, and frontend serving.

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | FastAPI, Uvicorn |
| Validation | Pydantic v2, pydantic-settings |
| Embeddings | sentence-transformers, transformers |
| Vector store | ChromaDB persistent client |
| PDF parsing | pdfplumber, PyMuPDF |
| Optional generation | Ollama HTTP API |
| Frontend | Plain HTML, CSS, JavaScript |
| Testing | pytest, pytest-asyncio |
| Logging | structlog, rich |

## Project Structure

```text
ai_legal_buddy/
├── app/
│   ├── main.py                     # FastAPI app, CORS, frontend serving
│   ├── api/
│   │   ├── router.py               # API v1 router
│   │   └── routes/
│   │       ├── documents.py        # Upload, list, delete documents
│   │       ├── health.py           # Health and readiness checks
│   │       └── query.py            # Natural-language search endpoint
│   ├── core/
│   │   ├── config.py               # Environment-backed settings
│   │   ├── exceptions.py           # App exception classes and handlers
│   │   └── logging.py              # structlog setup
│   ├── models/
│   │   └── schemas.py              # Pydantic request/response models
│   ├── services/
│   │   ├── embedding_service.py    # SentenceTransformer and hash embeddings
│   │   ├── generation_service.py   # Ollama answer generation and fallback
│   │   ├── ingestion_service.py    # PDF ingestion pipeline
│   │   ├── search_service.py       # Query, retrieval, insights, answer orchestration
│   │   └── vector_store.py         # ChromaDB operations
│   └── utils/
│       ├── file_utils.py           # File validation, saving, deletion
│       ├── legal_extractor.py      # Rule-based legal insight extraction
│       ├── pdf_extractor.py        # PDF text extraction
│       └── text_chunker.py         # Page-aware text chunking
├── frontend/
│   └── index.html                  # Single-file web UI
├── tests/
│   └── test_core.py                # Unit and route tests
├── data/
│   └── uploads/                    # Uploaded files, created at runtime
├── chroma_db/                      # Persistent ChromaDB data
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```

## How It Works

### Ingestion Pipeline

```text
PDF upload
  -> file validation and local save
  -> PDF text extraction
  -> page-aware text cleaning
  -> legal text chunking
  -> embedding generation
  -> ChromaDB storage with document metadata
```

### Query Pipeline

```text
User question
  -> query embedding
  -> ChromaDB similarity search
  -> similarity threshold filtering
  -> legal insight extraction per chunk
  -> aggregate risk summary
  -> optional generated answer from Ollama
  -> structured JSON response
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

The first successful SentenceTransformer run may download the embedding model.

### 3. Configure environment

Copy the example file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set at least:

```env
SECRET_KEY="replace-with-a-local-secret"
```

## Running the App

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Then open:

- Frontend: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Optional Ollama Setup

The search endpoint calls Ollama to generate `generated_answer`. If Ollama is not running or the configured model is unavailable, the app falls back to an extractive answer from retrieved chunks.

Default settings:

```env
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"
OLLAMA_TIMEOUT_SECONDS=30
TEMPERATURE=0.7
MAX_TOKENS=2048
```

Example local setup:

```bash
ollama pull llama3
ollama serve
```

## Configuration

Important environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `AI Legal Buddy` | Application display/API name |
| `APP_VERSION` | `0.1.0` | Application version |
| `DEBUG` | `False` | FastAPI debug flag |
| `SECRET_KEY` | required | Required by settings validation |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS origins |
| `UPLOAD_DIR` | `./data/uploads` | Saved uploaded PDFs |
| `MAX_FILE_SIZE_MB` | `50` | Upload size limit |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage path |
| `CHROMA_COLLECTION_NAME` | `legal_docs` | Chroma collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `EMBEDDING_BATCH_SIZE` | `32` | Batch size for chunk embedding |
| `CHUNK_SIZE` | `1000` | Chunk target size in tokens/words |
| `CHUNK_OVERLAP` | `200` | Overlap for large chunks |
| `MIN_CHUNK_LENGTH` | `50` | Minimum chunk text length |
| `TOP_K_RESULTS` | `5` | Default result count setting |
| `SIMILARITY_THRESHOLD` | `0.7` | Default similarity threshold |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | `json` or `console` |

## API Reference

### Health

```http
GET /api/v1/health/
```

Returns basic application health.

```http
GET /api/v1/health/ready
```

Checks API, settings, and vector store readiness.

### Upload Document

```http
POST /api/v1/documents/upload
```

Multipart form field:

- `file`: PDF file

Example response:

```json
{
  "document_id": "generated-document-id",
  "filename": "contract.pdf",
  "file_size_mb": 1.24,
  "page_count": 12,
  "upload_timestamp": "2026-06-24T10:00:00Z",
  "chunk_count": 38,
  "status": "processed",
  "message": "Document processed successfully into 38 chunks across 12 pages."
}
```

### List Documents

```http
GET /api/v1/documents/
```

Returns uploaded/indexed document summaries.

### Delete Document

```http
DELETE /api/v1/documents/{document_id}
```

Deletes stored chunks from ChromaDB and removes the saved uploaded file when present.

### Query Documents

```http
POST /api/v1/query/
```

Request:

```json
{
  "query": "What are the termination conditions?",
  "document_id": "optional-document-id",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

Response:

```json
{
  "query": "What are the termination conditions?",
  "generated_answer": "Based on the retrieved documents: ...",
  "total_results": 2,
  "results": [
    {
      "chunk_id": "document-id_0",
      "text": "Either party may terminate...",
      "similarity_score": 0.86,
      "page_number": 4,
      "insights": [
        {
          "insight_type": "termination",
          "risk_level": "high",
          "description": "Detected termination language in this section",
          "matched_keywords": ["terminate", "without notice"],
          "confidence_score": 0.8
        }
      ]
    }
  ],
  "aggregate_insights": {
    "counts_by_type": {
      "termination": 1
    },
    "counts_by_risk": {
      "low": 0,
      "medium": 0,
      "high": 1,
      "critical": 0
    },
    "overall_risk": "high",
    "total_insights": 1
  },
  "processing_time_ms": 123.4
}
```

## Frontend

The frontend is served from `frontend/index.html` at `/`.

It supports:

- Drag-and-drop PDF upload.
- Document list refresh.
- Selecting one document as the search scope.
- Searching all documents when no document is selected.
- Top-K result control.
- Generated answer display.
- Result cards with page number, similarity score, matched text, and legal insight tags.
- Health/readiness indicator.
- Document deletion.

## Running Tests

```bash
pytest
```

The tests currently cover:

- Query validation.
- File extension and file size helpers.
- Page-aware chunking.
- Legal insight extraction and risk escalation.
- Aggregate insight summaries.
- Hash embedding fallback behavior.
- Expected FastAPI routes.
- Root frontend serving.

## Development Notes

- Only PDF uploads are accepted by the current API route, even though some utility validation supports `.docx`.
- ChromaDB data is stored locally in `chroma_db/`.
- Uploaded files are stored under `data/uploads/`.
- If the embedding model cannot load, the app continues with deterministic hash embeddings. This keeps development resilient but may reduce search quality.
- If Ollama is unavailable, search still works and generated answers fall back to retrieved text.

## Legal Disclaimer

AI Legal Buddy is a software tool for document search and summarization assistance. It can miss context, misclassify clauses, or generate incomplete answers. Always review the original document and consult a qualified legal professional before making legal decisions.
