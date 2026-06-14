from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from app.core.config import settings

# ── Enums ────────────────────────────────────────────────────────────────────
# Defines allowed risk levels — used to classify how dangerous a clause is
class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# Defines allowed values for legal insight types — restricts to known clause categories
class InsightType(str, Enum):
    obligation = "obligation"
    penalty = "penalty"
    termination = "termination"
    risk = "risk"
    definition = "definition"
    deadline = "deadline"
    confidentiality = "confidentiality"
    indemnification = "indemnification"
    governing_law = "governing_law"

# ── Document Schemas ──────────────────────────────────────────────────────────
# Lightweight snapshot of a document — used when listing all uploaded documents
class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    file_size_mb: float
    page_count: int
    upload_timestamp: datetime

# Returned after a document is uploaded and processed — extends DocumentSummary
class UploadDocumentResponse(DocumentSummary):
    chunk_count: int
    status: str = "processed"
    message: str

# ── Query Schemas ─────────────────────────────────────────────────────────────
# What the user sends when asking a legal question — validated strictly
class QueryRequest(BaseModel):
    query: str 
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Strips whitespace and rejects empty or blank questions before they hit business logic
    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query can not be empty")
        return v
    
# ── Legal Intelligence Schemas ────────────────────────────────────────────────
# A single piece of legal intelligence extracted from a chunk of text
class LegalInsight(BaseModel):
    insight_type: InsightType
    risk_level: RiskLevel
    description: str
    matched_keywords: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)

# A single search result — one chunk of the legal document that matched the query
class ChunkResult(BaseModel):
    chunk_id: str
    text: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    page_number: int
    insights: list[LegalInsight] = Field(default_factory=list)

# ── Response Schemas ──────────────────────────────────────────────────────────
# Full response to a legal query — wraps all matching chunks with a risk summary
class QueryResponse(BaseModel):
    query: str
    total_results: int
    results: list[ChunkResult] = Field(default_factory=list)
    aggregate_insights: dict = Field(default_factory=dict)
    processing_time_ms: float

# ── Common Schemas ────────────────────────────────────────────────────────────
# Returned by /health endpoint — confirms app is running correctly
class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    app_name: str = Field(default=settings.APP_NAME)
    version: str = Field(default=settings.APP_VERSION)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Returned on any error — mirrors LegalBuddyException fields for consistency
class ErrorResponse(BaseModel):
    error_code: str 
    message: str  
    status_code: int 