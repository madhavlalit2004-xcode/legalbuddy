import time
from datetime import datetime
from app.core.config import settings
from app.core.exceptions import FileParsingException, EmptyDocumentException
from app.core.logging import get_logger
from app.models.schemas import UploadDocumentResponse
from app.utils.file_utils import save_uploaded_file, get_file_size_mb, delete_file
from app.utils.pdf_extractor import extract_text_from_pdf
from app.utils.text_chunker import chunk_pages
from app.utils.legal_extractor import extract_insights
from app.services.embedding_service import get_embeddings_batch
from app.services.vector_store import add_chunks

logger = get_logger(__name__)


def ingest_document(file_bytes: bytes, filename: str) -> UploadDocumentResponse:
    start_time = time.time()
    file_path = None

    try:
        document_id, file_path = save_uploaded_file(file_bytes, filename)
        file_size_mb = get_file_size_mb(file_bytes)
        logger.info("ingestion started", document_id=document_id, filename=filename)

        pages = extract_text_from_pdf(file_bytes, filename)

        chunks = chunk_pages(
            pages,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            min_chunk_length=settings.MIN_CHUNK_LENGTH
        )

        if not chunks:
            raise EmptyDocumentException(message="Document was parsed but produced no usable text chunks")

        chunk_texts = [c.text for c in chunks]
        embeddings = get_embeddings_batch(chunk_texts)

        if len(embeddings) != len(chunks):
            logger.warning("embedding count mismatch, trimming to align", chunks=len(chunks), embeddings=len(embeddings))
            chunks = chunks[:len(embeddings)]

        chunk_insights = [extract_insights(c.text) for c in chunks]

        chunk_ids = [f"{document_id}_{c.chunk_index}" for c in chunks]
        metadatas = [
            {"document_id": document_id, "page_number": c.page_number, "chunk_index": c.chunk_index, "filename": filename}
            for c in chunks
        ]

        add_chunks(chunk_ids=chunk_ids, embeddings=embeddings, texts=chunk_texts[:len(embeddings)], metadatas=metadatas)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info("ingestion complete", document_id=document_id, chunks=len(chunks), elapsed_ms=round(elapsed_ms, 1))

        return UploadDocumentResponse(
            document_id=document_id,
            filename=filename,
            file_size_mb=file_size_mb,
            page_count=len(pages),
            upload_timestamp=datetime.utcnow(),
            chunk_count=len(chunks),
            status="processed",
            message=f"Document processed successfully into {len(chunks)} chunks across {len(pages)} pages."
        )

    except Exception:
        if file_path:
            logger.warning("ingestion failed, cleaning up saved file", file_path=file_path)
            delete_file(file_path)
        raise