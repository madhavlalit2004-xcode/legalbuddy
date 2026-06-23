from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, status

from app.core.config import settings
from app.core.exceptions import FileNotPDForDOCXException, LegalBuddyException
from app.core.logging import get_logger
from app.models.schemas import DocumentSummary, UploadDocumentResponse
from app.services.ingestion_service import ingest_document
from app.services.vector_store import _get_collection, delete_document_chunks

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_uploaded_file_path(document_id: str) -> Path | None:
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        return None

    matches = list(upload_dir.glob(f"{document_id}.*"))
    return matches[0] if matches else None


def _metadata_to_summary(document_id: str, metadatas: list[dict]) -> DocumentSummary:
    first_metadata = metadatas[0] if metadatas else {}
    file_path = _get_uploaded_file_path(document_id)

    file_size_mb = 0.0
    upload_timestamp = datetime.utcnow()

    if file_path and file_path.exists():
        stat = file_path.stat()
        file_size_mb = round(stat.st_size / (1024 * 1024), 2)
        upload_timestamp = datetime.utcfromtimestamp(stat.st_mtime)

    page_numbers = [
        int(metadata.get("page_number", 0))
        for metadata in metadatas
        if metadata and metadata.get("page_number") is not None
    ]

    return DocumentSummary(
        document_id=document_id,
        filename=first_metadata.get("filename", document_id),
        file_size_mb=file_size_mb,
        page_count=max(page_numbers, default=0),
        upload_timestamp=upload_timestamp,
    )


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(file: UploadFile = File(...)) -> UploadDocumentResponse:
    if not file.filename:
        raise FileNotPDForDOCXException(message="Uploaded file must have a filename.")

    if not file.filename.lower().endswith(".pdf"):
        raise FileNotPDForDOCXException(message="Only PDF uploads are currently supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise LegalBuddyException(
            message="Uploaded file is empty.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPTY_FILE",
        )

    logger.info("document upload received", filename=file.filename, size_bytes=len(file_bytes))
    return ingest_document(file_bytes=file_bytes, filename=file.filename)


@router.get("/", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    collection = _get_collection()
    stored = collection.get(include=["metadatas"])

    grouped: dict[str, list[dict]] = {}
    for metadata in stored.get("metadatas", []):
        if not metadata:
            continue

        document_id = metadata.get("document_id")
        if not document_id:
            continue

        grouped.setdefault(document_id, []).append(metadata)

    summaries = [
        _metadata_to_summary(document_id, metadatas)
        for document_id, metadatas in grouped.items()
    ]
    summaries.sort(key=lambda document: document.upload_timestamp, reverse=True)
    return summaries


@router.delete("/{document_id}")
def delete_document(document_id: str) -> dict:
    deleted_chunks = delete_document_chunks(document_id)
    file_path = _get_uploaded_file_path(document_id)
    file_deleted = False

    if file_path and file_path.exists():
        file_path.unlink()
        file_deleted = True

    if deleted_chunks == 0 and not file_deleted:
        raise LegalBuddyException(
            message=f"Document '{document_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="DOCUMENT_NOT_FOUND",
        )

    logger.info(
        "document deleted",
        document_id=document_id,
        deleted_chunks=deleted_chunks,
        file_deleted=file_deleted,
    )

    return {
        "document_id": document_id,
        "deleted_chunks": deleted_chunks,
        "file_deleted": file_deleted,
        "message": "Document deleted successfully.",
    }