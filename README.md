# ⚖️ AI Legal Buddy

**AI-powered legal document analysis system** — upload contracts, agreements, and policies; ask natural language questions to surface obligations, risks, penalties, and key clauses using vector-similarity search and NLP.

---

## Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Tech Stack](#tech-stack)
5. [Quick Start](#quick-start)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Frontend](#frontend)
9. [Running Tests](#running-tests)
10. [Docker Deployment](#docker-deployment)
11. [Design Decisions](#design-decisions)
12. [Future Improvements](#future-improvements)

---

## Features

| Feature | Description |
|---|---|
| **PDF Ingestion** | Upload any PDF up to 50 MB; dual-parser strategy (pdfplumber → PyMuPDF fallback) |
| **Smart Chunking** | Hierarchy-aware chunking: section headings → paragraphs → sentences → sliding window with overlap |
| **Vector Embeddings** | `all-MiniLM-L6-v2` SentenceTransformer model; normalised cosine similarity |
| **ChromaDB Storage** | Persistent HNSW vector index with full metadata; content-hash deduplication |
| **Semantic Search** | Natural language queries converted to embeddings and matched against all stored chunks |
| **Legal Insight Extraction** | Rule-based NLP identifies: obligations, penalties, termination clauses, risks, deadlines, confidentiality, indemnification, governing law, definitions |
| **Risk Scoring** | Per-insight risk level (LOW / MEDIUM / HIGH / CRITICAL) with aggregate summary |
| **REST API** | FastAPI with Pydantic v2 validation, OpenAPI docs, structured error responses |
| **Web Frontend** | Zero-dependency HTML/CSS/JS interface for upload, query, and results |
| **Structured Logging** | JSON or console output via structlog; per-request timing headers |
| **Docker Support** | Multi-stage Dockerfile; docker-compose for one-command deployment |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     HTTP Client / Browser                 │
└────────────────────────┬─────────────────────────────────┘
                         │ REST API
┌────────────────────────▼─────────────────────────────────┐
│                    FastAPI Application                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  /upload    │  │   /query     │  │   /health       │  │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────┘  │
│         │                │                                 │
│  ┌──────▼──────┐  ┌──────▼───────┐                        │
│  │ Ingestion   │  │  Search      │                        │
│  │ Service     │  │  Service     │                        │
│  └──────┬──────┘  └──────┬───────┘                        │
│         │                │                                 │
│  ┌──────▼────────────────▼───────┐                        │
│  │       Embedding Service        │                        │
│  │   (SentenceTransformer)        │                        │
│  └──────┬────────────────┬───────┘                        │
│         │                │                                 │
│  ┌──────▼──────┐  ┌──────▼───────┐                        │
│  │ PDF Extract │  │  ChromaDB    │                        │
│  │ + Chunker   │  │  (HNSW)      │                        │
│  └─────────────┘  └──────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

### Ingestion Pipeline

```
PDF bytes
   │
   ▼
[Size Guard + Hash Dedup]
   │
   ▼
[PDF Text Extraction]  ← pdfplumber → PyMuPDF fallback
   │
   ▼
[Text Cleaning]  ← strip nulls, collapse whitespace, remove page numbers
   │
   ▼
[Smart Chunking]  ← section headings → paragraphs → sentences → sliding window
   │
   ▼
[Batch Embedding]  ← SentenceTransformer all-MiniLM-L6-v2 (normalised)
   │
   ▼
[ChromaDB Upsert]  ← chunk_id, embedding, text, metadata
```

### Query Pipeline

```
Natural language query
   │
   ▼
[Query Embedding]  ← same model as ingestion
   │
   ▼
[ChromaDB ANN Search]  ← cosine similarity, optional document_id filter
   │
   ▼
[Similarity Threshold Filter]
   │
   ▼
[Legal Insight Extraction]  ← rule-based pattern matching per chunk
   │
   ▼
[Aggregate Risk Summary]
   │
   ▼
Structured JSON response
```

---

## Project Structure

```
ai-legal-buddy/
│
├── app/
│   ├── main.py                  # FastAPI app factory + lifespan
│   │
│   ├── api/
│   │   ├── router.py            # Central API router (v1)
│   │   └── routes/
│   │       ├── documents.py     # POST /upload, GET /documents, DELETE
│   │       ├── query.py         # POST /query
│   │       └── health.py        # GET /health
│   │
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (env validation)
│   │   ├── exceptions.py        # Domain exception hierarchy
│   │   └── logging.py           # structlog pipeline configuration
│   │
│   ├── services/
│   │   ├── embedding_service.py # SentenceTransformer singleton
│   │   ├── vector_store.py      # ChromaDB abstraction layer
│   │   ├── ingestion_service.py # Document ingestion orchestrator
│   │   └── search_service.py    # Semantic query orchestrator
│   │
│   ├── models/
│   │   └── schemas.py           # Pydantic v2 request/response schemas
│   │
│   └── utils/
│       ├── pdf_extractor.py     # pdfplumber + PyMuPDF extraction
│       ├── text_chunker.py      # Hierarchical smart chunker
│       ├── legal_extractor.py   # Rule-based NLP insight extractor
│       └── file_utils.py        # Hash, UUID, filename sanitisation
│
├── frontend/
│   └── index.html               # Single-file web UI (no build step)
│
├── tests/
│   ├── __init__.py
│   └── test_core.py             # Unit + integration tests
│
├── data/
│   └── uploads/                 # Uploaded PDFs (git-ignored)
│
├── chroma_db/                   # ChromaDB persistent storage (git-ignored)
│
├── .env                         # Environment variables
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── postman_collection.json
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI 0.111 + Uvicorn |
| **Validation** | Pydantic v2 |
| **AI / Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Vector DB** | ChromaDB (persistent HNSW) |
| **PDF Parsing** | pdfplumber (primary) + PyMuPDF (fallback) |
| **Logging** | structlog (JSON / console) |
| **Testing** | pytest + pytest-asyncio |
| **Containerisation** | Docker + docker-compose |

---

## Quick Start

### Prerequisites

- Python 3.10+ (3.11 recommended)
- pip

### 1. Clone and install

```bash
git clone https://github.com/yourname/ai-legal-buddy.git
cd ai-legal-buddy

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

> **Note:** The first run downloads the `all-MiniLM-L6-v2` model (~90 MB) to `~/.cache/huggingface/`.

### 2. Configure environment

```bash
cp .env .env.local   # optional: customise settings
```

Key variables (all have sensible defaults):

```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=512
CHUNK_OVERLAP=64
TOP_K_RESULTS=5
LOG_FORMAT=console   # human-readable during development
```

### 3. Run the server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Or via the module:

```bash
python app/main.py
```

### 4. Open the UI

Navigate to **http://localhost:8000** — the web interface loads automatically.

### 5. Explore the API docs

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

---

## Configuration

All settings are in `.env` and validated by `app/core/config.py`:

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model name |
| `EMBEDDING_BATCH_SIZE` | `32` | Chunks per encode batch |
| `CHUNK_SIZE` | `512` | Target chars per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap chars between chunks |
| `MIN_CHUNK_LENGTH` | `50` | Discard chunks shorter than this |
| `TOP_K_RESULTS` | `5` | Default search results |
| `SIMILARITY_THRESHOLD` | `0.3` | Minimum similarity score (0–1) |
| `MAX_FILE_SIZE_MB` | `50` | Upload size limit |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB data directory |
| `LOG_FORMAT` | `json` | `json` or `console` |
| `APP_ENV` | `development` | `development`, `staging`, `production` |

---

## API Reference

### `GET /api/v1/health`

System health check.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "components": {
    "api":             { "status": "ok" },
    "vector_store":    { "status": "ok", "detail": "142 chunks in collection" },
    "embedding_model": { "status": "ok", "detail": "model=all-MiniLM-L6-v2 dim=384" }
  },
  "uptime_seconds": 312.5
}
```

---

### `POST /api/v1/documents/upload`

Ingest a PDF. Multipart form-data.

**Form fields:**
- `file` — PDF file (required)
- `allow_duplicates` — boolean, default `false`

**Response `201`:**
```json
{
  "document_id": "a1b2c3d4-1234-...",
  "filename": "service_agreement.pdf",
  "total_pages": 12,
  "total_chunks": 48,
  "char_count": 24576,
  "ingested_at": "2024-01-15T10:30:00Z",
  "message": "Document successfully ingested"
}
```

**Error codes:** `400` invalid PDF · `409` duplicate · `413` too large · `422` no text

---

### `POST /api/v1/query/`

Semantic search with legal insight extraction.

**Request body:**
```json
{
  "query": "What are the termination conditions?",
  "document_id": "a1b2c3d4-...",   // optional — scope to one document
  "top_k": 5,
  "similarity_threshold": 0.25
}
```

**Response `200`:**
```json
{
  "query": "What are the termination conditions?",
  "document_id": "a1b2c3d4-...",
  "total_results": 3,
  "query_time_ms": 42.5,
  "aggregate_insights": {
    "overall_risk": "high",
    "insight_type_counts": { "termination": 3, "obligation": 2 },
    "risk_level_counts": { "low": 0, "medium": 1, "high": 2, "critical": 0 },
    "total_insights": 5
  },
  "results": [
    {
      "chunk_id": "a1b2c3d4-...__chunk_00012",
      "document_id": "a1b2c3d4-...",
      "filename": "service_agreement.pdf",
      "page_number": 7,
      "chunk_index": 12,
      "text": "Either party may terminate this Agreement...",
      "similarity_score": 0.8721,
      "word_count": 64,
      "insights": [
        {
          "insight_type": "termination",
          "risk_level": "high",
          "description": "Discusses termination, cancellation, or expiry conditions",
          "keywords_matched": ["terminate", "30 days", "written notice"]
        }
      ]
    }
  ]
}
```

---

### `GET /api/v1/documents/`

List all ingested documents.

---

### `DELETE /api/v1/documents/{document_id}`

Remove a document and all its indexed chunks.

---

## Frontend

The single-file frontend (`frontend/index.html`) is served at the root URL. No build step required.

**Features:**
- Drag-and-drop or click-to-browse PDF upload with progress bar
- Per-document scoping (click a document to search only within it)
- Expandable result cards with similarity score bars
- Colour-coded insight tags per legal category
- Aggregate risk level summary pills
- Live health indicator in the header
- Document deletion with confirmation

---

## Running Tests

```bash
# Install dev dependencies (included in requirements.txt)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

The test suite covers:

- Text chunker: size enforcement, page provenance, edge cases
- Legal extractor: obligation / penalty / termination / risk / deadline / confidentiality detection
- API endpoints: health, upload validation, query validation, error responses

---

## Docker Deployment

### Single container

```bash
docker build -t ai-legal-buddy .
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/chroma_db:/app/chroma_db \
  ai-legal-buddy
```

### docker-compose (recommended)

```bash
docker-compose up --build
```

Volumes ensure ChromaDB data and uploaded PDFs persist across container restarts.

---

## Design Decisions

**Why ChromaDB instead of Pinecone/Weaviate?**
ChromaDB runs fully embedded (no separate server process), making local development and Docker deployment trivial. It persists to disk via SQLite + HNSW. For production scale, swapping in Weaviate or Qdrant requires only changing `VectorStoreService`.

**Why rule-based insight extraction instead of an LLM?**
Rule-based extraction is fast (< 1 ms per chunk), deterministic, offline, and requires no API keys. An LLM layer can be added on top for deeper semantic understanding without changing the architecture.

**Why pdfplumber + PyMuPDF dual-parser?**
pdfplumber handles complex layouts (tables, multi-column) better; PyMuPDF is faster and more robust for simple text-heavy PDFs. The fallback strategy handles nearly all real-world PDFs without user intervention.

**Why Pydantic Settings?**
Environment variable validation at startup catches misconfiguration before any request is served. The `@lru_cache` singleton ensures `.env` is parsed exactly once.

**Why content-hash deduplication?**
Re-ingesting the same PDF would create duplicate chunks and degrade search quality. SHA-256 of the raw bytes catches exact duplicates regardless of filename.

---

## Future Improvements

- **LLM Integration**: Add an optional Claude / GPT-4 layer for natural language summaries of retrieved chunks
- **OCR Support**: Integrate Tesseract for scanned / image-based PDFs
- **Multi-document Comparison**: Side-by-side diff of two contracts
- **Clause Library**: Pre-indexed standard clause templates for similarity scoring
- **Authentication**: JWT-based API keys for multi-tenant use
- **Async Ingestion**: Background task queue (Celery / ARQ) for large PDF batches
- **Metadata Filters**: Filter by date, document type, or custom tags
- **Export**: Download extracted insights as structured JSON / CSV / DOCX
- **Streaming**: Server-Sent Events for real-time ingestion progress
- **Re-ranking**: Cross-encoder re-ranking pass on top-k results for higher precision

---

## License

MIT — see `LICENSE` for details.