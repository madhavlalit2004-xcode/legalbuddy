import os
import uuid
from pathlib import Path
from app.core.config import settings
from app.core.exceptions import FileTooLargeException, FileNotPDForDOCXException
from app.core.logging import get_logger

logger = get_logger(__name__)

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_file_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        logger.warning("invalid file extension", filename=filename, ext=ext)
        raise FileNotPDForDOCXException(
            message=f"File '{filename}' has unsupported extension '{ext}'. Only PDF and DOCX are allowed."
        )
    return ext


def validate_file_size(file_bytes: bytes) -> None:
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        logger.warning("file too large", size_mb=round(size_mb, 2), limit_mb=settings.MAX_FILE_SIZE_MB)
        raise FileTooLargeException(
            message=f"File size {size_mb:.2f}MB exceeds the {settings.MAX_FILE_SIZE_MB}MB limit."
        )


def generate_document_id() -> str:
    return str(uuid.uuid4())


def generate_safe_filename(original_filename: str, document_id: str) -> str:
    ext = Path(original_filename).suffix.lower()
    return f"{document_id}{ext}"


def save_uploaded_file(file_bytes: bytes, filename: str) -> tuple[str, str]:
    validate_file_extension(filename)
    validate_file_size(file_bytes)

    document_id = generate_document_id()
    safe_filename = generate_safe_filename(filename, document_id)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    logger.info("file saved", document_id=document_id, filename=filename, path=str(file_path))
    return document_id, str(file_path)


def get_file_size_mb(file_bytes: bytes) -> float:
    return round(len(file_bytes) / (1024 * 1024), 2)


def delete_file(file_path: str) -> None:
    path = Path(file_path)
    if path.exists():
        path.unlink()
        logger.info("file deleted", path=file_path)
    else:
        logger.warning("file not found for deletion", path=file_path)