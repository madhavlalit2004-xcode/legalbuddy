import httpx
import re

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import ChunkResult

logger = get_logger(__name__)

NOT_FOUND_MESSAGE = "not found in the provided documents"
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


class GenerationService:
    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout_seconds: float = settings.OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate_answer(self, query: str, context_chunks: list[ChunkResult]) -> str | None:
        if not context_chunks:
            return NOT_FOUND_MESSAGE

        prompt = self._build_prompt(query=query, context_chunks=context_chunks)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": settings.TEMPERATURE,
                            "num_predict": settings.MAX_TOKENS,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(
                "answer generation failed",
                query=query,
                model=self.model,
                error=str(exc),
            )
            return self._build_extractive_fallback(query, context_chunks)

        payload = response.json()
        answer = payload.get("response", "").strip()
        return answer or self._build_extractive_fallback(query, context_chunks)

    def _build_prompt(self, query: str, context_chunks: list[ChunkResult]) -> str:
        context = "\n---\n".join(
            f"Source chunk {index + 1} (page {chunk.page_number}):\n{chunk.text}"
            for index, chunk in enumerate(context_chunks)
        )

        return (
            "Answer the question using ONLY the context below. "
            f'If not found, say "{NOT_FOUND_MESSAGE}".\n\n'
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )

    def _build_extractive_fallback(self, query: str, context_chunks: list[ChunkResult]) -> str:
        query_terms = {
            term
            for term in re.findall(r"[a-z0-9]+", query.lower())
            if len(term) > 2 and term not in STOPWORDS
        }
        if not query_terms:
            return NOT_FOUND_MESSAGE

        clause_answer = self._extract_matching_clause(query_terms, context_chunks)
        if clause_answer:
            return f"Based on the retrieved documents: {clause_answer}"

        candidates: list[tuple[int, int, str]] = []
        seen_sentences: set[str] = set()

        for chunk in context_chunks:
            normalized_text = " ".join(chunk.text.split())
            sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
            for sentence in sentences:
                cleaned = " ".join(sentence.split())
                if not cleaned or cleaned in seen_sentences:
                    continue

                sentence_terms = set(re.findall(r"[a-z0-9]+", cleaned.lower()))
                overlap = len(query_terms & sentence_terms)
                if overlap:
                    seen_sentences.add(cleaned)
                    candidates.append((overlap, len(cleaned), cleaned))

        if not candidates:
            return NOT_FOUND_MESSAGE

        candidates.sort(key=lambda item: (-item[0], item[1]))
        supporting_text = " ".join(sentence for _, _, sentence in candidates[:3])
        return f"Based on the retrieved documents: {supporting_text}"

    def _extract_matching_clause(self, query_terms: set[str], context_chunks: list[ChunkResult]) -> str | None:
        clause_pattern = re.compile(
            r"(?:^|\s)(\d+\.\s+([A-Z][A-Za-z ]+):\s+.*?)(?=\s+\d+\.\s+[A-Z][A-Za-z ]+:\s+|$)"
        )

        for chunk in context_chunks:
            normalized_text = " ".join(chunk.text.split())
            for match in clause_pattern.finditer(normalized_text):
                clause_text = match.group(1).strip()
                heading = match.group(2).lower()
                heading_terms = set(re.findall(r"[a-z0-9]+", heading))
                if query_terms & heading_terms:
                    return clause_text

        return None


generation_service = GenerationService()
