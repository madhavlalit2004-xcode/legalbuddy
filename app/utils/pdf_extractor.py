from typing import NamedTuple
import io
import re
import pdfplumber
import fitz
from app.core.exceptions import InvalidPDFException, EmptyDocumentException, FileParsingException
from app.core.logging import get_logger

logger = get_logger(__name__)

class PageText(NamedTuple):
    page_number: int
    text: str

def _clean_extracted_text(raw: str) -> str:
    text = raw.replace("\x00", "")
    text = re.sub(r"[^\S\n]+", " ", text)

    lines = text.split("\n")
    lines = [l for l in lines if not re.fullmatch(r"[\d\s\-_]{1,10}", l.strip())]
    text = "\n".join(lines)

    return text.strip()

def _extract_with_pdfplumber(file_bytes: bytes) -> list[PageText]:

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        result = []

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            cleaned = _clean_extracted_text(text)
            result.append(PageText(page_number = i + 1, text=cleaned))

        logger.info("pdfplumber extracted", pages=len(result))
        return result
    
def _extract_with_pymupdf(file_bytes: bytes) -> list[PageText]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    result = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if not text:
            continue
        cleaned = _clean_extracted_text(text)
        result.append(PageText(page_number= i + 1, text = cleaned))

    doc.close()
    logger.info("pymupdf extracted", pages=len(result))
    return result

def extract_text_from_pdf(file_bytes: bytes, filename: str) -> list[PageText]:
    try:

        if file_bytes[:4] != b"%PDF":
            raise InvalidPDFException()

        pages = _extract_with_pdfplumber(file_bytes)
        total_chars = sum(len(p.text) for p in pages)

        if total_chars < 100:
            logger.warning("pdfplumber got little text, trying pymupdf", filename=filename)
            pages = _extract_with_pymupdf(file_bytes)

        if not pages:
            raise EmptyDocumentException()
    
    except (InvalidPDFException, EmptyDocumentException):
        raise
    except Exception as e:
        raise FileParsingException(str(e))
    
    logger.info("extraction complete", filename=filename, pages = len(pages))
    return pages