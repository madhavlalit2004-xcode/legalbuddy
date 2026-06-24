import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ["DEBUG"] = "1"
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.core.exceptions import FileNotPDForDOCXException, FileTooLargeException
from app.main import app
from app.models.schemas import InsightType, QueryRequest, RiskLevel
from app.services.embedding_service import _hash_embedding, get_embeddings_batch
from app.utils.file_utils import get_file_size_mb, validate_file_extension, validate_file_size
from app.utils.legal_extractor import aggregate_insights, extract_insights
from app.utils.pdf_extractor import PageText
from app.utils.text_chunker import chunk_pages


def test_query_request_strips_query_text() -> None:
    request = QueryRequest(query="  What are the termination terms?  ")

    assert request.query == "What are the termination terms?"
    assert request.top_k == 5
    assert request.similarity_threshold == 0.7


def test_query_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="   ")


def test_query_request_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="valid question", top_k=21)

    with pytest.raises(ValidationError):
        QueryRequest(query="valid question", similarity_threshold=1.5)


def test_file_extension_validation_accepts_pdf_and_docx() -> None:
    assert validate_file_extension("contract.PDF") == ".pdf"
    assert validate_file_extension("agreement.docx") == ".docx"


def test_file_extension_validation_rejects_unsupported_files() -> None:
    with pytest.raises(FileNotPDForDOCXException):
        validate_file_extension("notes.txt")


def test_file_size_helpers_measure_and_reject_oversized_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.utils.file_utils.settings.MAX_FILE_SIZE_MB", 1)

    assert get_file_size_mb(b"a" * 1024 * 1024) == 1.0

    with pytest.raises(FileTooLargeException):
        validate_file_size(b"a" * (1024 * 1024 + 1))


def test_chunk_pages_keeps_page_numbers_and_chunk_order() -> None:
    pages = [
        PageText(
            page_number=1,
            text="SECTION 1\nThe buyer shall pay all invoices within 30 days. This clause survives closing.",
        ),
        PageText(
            page_number=2,
            text="SECTION 2\nEither party may terminate this agreement without notice for material breach.",
        ),
    ]

    chunks = chunk_pages(
        pages,
        chunk_size=40,
        chunk_overlap=5,
        min_chunk_length=20,
    )

    assert chunks
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert {chunk.page_number for chunk in chunks} <= {1, 2}
    assert any("buyer shall pay" in chunk.text for chunk in chunks)


def test_extract_insights_detects_legal_patterns_and_escalates_risk() -> None:
    text = (
        "The contractor shall keep all trade secret information confidential indefinitely. "
        "Either party may terminate immediately without notice. "
        "The contractor shall indemnify and hold harmless the client for any and all claims."
    )

    insights = extract_insights(text)
    insight_types = {insight.insight_type for insight in insights}
    risks_by_type = {insight.insight_type: insight.risk_level for insight in insights}

    assert InsightType.obligation in insight_types
    assert InsightType.confidentiality in insight_types
    assert InsightType.termination in insight_types
    assert InsightType.indemnification in insight_types
    assert risks_by_type[InsightType.termination] == RiskLevel.high
    assert risks_by_type[InsightType.indemnification] == RiskLevel.critical


def test_aggregate_insights_summarizes_counts_and_highest_risk() -> None:
    first = extract_insights("The party shall pay damages for breach.")
    second = extract_insights("The vendor must indemnify the buyer for unlimited liability.")

    summary = aggregate_insights([first, second])

    assert summary["total_insights"] >= 3
    assert summary["overall_risk"] == RiskLevel.critical.value
    assert summary["counts_by_risk"][RiskLevel.critical.value] >= 1
    assert summary["counts_by_type"][InsightType.obligation.value] >= 1


def test_hash_embedding_is_stable_and_normalized() -> None:
    first = _hash_embedding("The contractor shall pay invoices within 30 days.")
    second = _hash_embedding("The contractor shall pay invoices within 30 days.")

    magnitude = sum(value * value for value in first) ** 0.5

    assert first == second
    assert len(first) == 384
    assert magnitude == pytest.approx(1.0)


def test_batch_embeddings_use_hash_fallback_when_model_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.embedding_service._get_sentence_transformer", lambda: None)

    embeddings = get_embeddings_batch(["First clause text.", "Second clause text."])

    assert len(embeddings) == 2
    assert all(len(embedding) == 384 for embedding in embeddings)


def test_app_registers_expected_routes() -> None:
    route_paths = {route.path for route in app.routes}

    assert "/" in route_paths
    assert "/api/v1/health/" in route_paths
    assert "/api/v1/health/ready" in route_paths
    assert "/api/v1/documents/" in route_paths
    assert "/api/v1/documents/upload" in route_paths
    assert "/api/v1/documents/{document_id}" in route_paths
    assert "/api/v1/query/" in route_paths


def test_root_serves_frontend_html() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI Legal Buddy" in response.text