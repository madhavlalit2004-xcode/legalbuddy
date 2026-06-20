from typing import Generator
from app.utils.pdf_extractor import PageText
from app.core.logging import get_logger
from dataclasses import dataclass
import re

@dataclass
class TextChunk:
    text: str
    page_number: int
    chunk_index: int
    char_start: int
    char_end: int

_HEADING_RE = re.compile(r"^(?:ARTICLE|SECTION)\s+[\dIVX]+|^\d{1,3}\.\d{0,3}\s+[A-Z]|^[A-Z]{5,}$", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"])")

logger = get_logger(__name__)

def _split_on_sentences(text: str) -> list[str]:
    return _SENTENCE_RE.split(text)

def _sliding_window(tokens: list[str], chunk_size: int, overlap: int) -> Generator[list[str], None, None]:
    i = 0
    step = chunk_size - overlap
    while i < len(tokens):
        chunk = tokens[i:i + chunk_size]
        yield chunk
        i += step

def _build_page_offsets(pages: list[PageText]) -> list[tuple[int, int, int]]:
    offset = []
    pos = 0
    for page in pages:
        start = pos
        end = pos + len(page.text)
        offset.append((start, end, page.page_number))
        pos = end + 2
    return offset

def _find_page_for_offset(offset, char_pos) -> int:
    for start, end, page_num in offset:
        if start <= char_pos < end:
            return page_num
    return offset[-1][2]

def chunk_pages(pages: list[PageText], chunk_size: int, chunk_overlap: int, min_chunk_length: int) -> list[TextChunk]:
    offsets = _build_page_offsets(pages)
    full_text = "\n\n".join(page.text for page in pages)

    sections = _HEADING_RE.split(full_text)

    chunks: list[TextChunk] = []
    chunk_index = 0
    search_cursor = 0   
    
    for section in sections:
        if not section or not section.strip():
            continue
        paragraphs = section.split("\n\n")

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue    
            tokens = paragraph.split()

            if len(tokens) <= chunk_size:
                char_start = full_text.find(paragraph, search_cursor)
                if char_start == -1:
                    char_start = search_cursor  # fallback safety
                char_end = char_start + len(paragraph)
                search_cursor = char_end

                if len(paragraph.strip()) < min_chunk_length:
                    continue

                page_num = _find_page_for_offset(offsets, char_start)
                chunks.append(TextChunk(
                    text=paragraph.strip(),
                    page_number=page_num,
                    chunk_index=chunk_index,
                    char_start=char_start,
                    char_end=char_end
                ))
                chunk_index += 1

            else:
                sentences = _split_on_sentences(paragraph)
                sentence_tokens = " ".join(sentences).split()
                
                for window in _sliding_window(sentence_tokens, chunk_size, chunk_overlap):
                    chunk_text = " ".join(window)
                    
                    char_start = full_text.find(chunk_text, search_cursor)
                    if char_start == -1:
                        char_start = full_text.find(chunk_text)
                        if char_start == -1:
                            char_start = search_cursor
                    char_end = char_start + len(chunk_text)

                    if len(chunk_text.strip()) < min_chunk_length:
                        continue
                    
                    page_num = _find_page_for_offset(offsets, char_start)
                    chunks.append(TextChunk(
                        text=chunk_text.strip(),
                        page_number=page_num,
                        chunk_index=chunk_index,
                        char_start=char_start,
                        char_end=char_end
                    ))
                    chunk_index += 1

                search_cursor = full_text.find(paragraph, search_cursor) + len(paragraph)
    
    logger.info("chunking complete", total_chunks=len(chunks))
    return chunks