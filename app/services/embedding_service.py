import hashlib
import math
import re
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import EmbeddingException
from app.core.logging import get_logger

logger = get_logger(__name__)

_FALLBACK_DIMENSIONS = 384
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@lru_cache(maxsize=1)
def _get_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("loading sentence transformer", model=settings.EMBEDDING_MODEL)
        return SentenceTransformer(settings.EMBEDDING_MODEL)
    except Exception as exc:
        logger.warning(
            "sentence transformer unavailable, using hash embeddings",
            model=settings.EMBEDDING_MODEL,
            error=str(exc),
        )
        return None


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _hash_embedding(text: str) -> list[float]:
    vector = [0.0] * _FALLBACK_DIMENSIONS
    tokens = _TOKEN_RE.findall(text.lower())

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % _FALLBACK_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    return _normalize(vector)


def _validate_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise EmbeddingException(message="Cannot embed empty text.")
    return cleaned


def get_embedding(text: str) -> list[float]:
    cleaned = _validate_text(text)
    model = _get_sentence_transformer()

    if model is None:
        return _hash_embedding(cleaned)

    try:
        embedding = model.encode(
            cleaned,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding.tolist()
    except Exception as exc:
        logger.warning("sentence transformer embedding failed, using hash embedding", error=str(exc))
        return _hash_embedding(cleaned)


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    cleaned_texts = [_validate_text(text) for text in texts]
    if not cleaned_texts:
        return []

    model = _get_sentence_transformer()

    if model is None:
        embeddings = [_hash_embedding(text) for text in cleaned_texts]
        logger.info("batch hash embedding complete", total=len(embeddings))
        return embeddings

    try:
        embeddings = model.encode(
            cleaned_texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        result = embeddings.tolist()
        logger.info("batch sentence transformer embedding complete", total=len(result))
        return result
    except Exception as exc:
        logger.warning("batch sentence transformer embedding failed, using hash embeddings", error=str(exc))
        embeddings = [_hash_embedding(text) for text in cleaned_texts]
        logger.info("batch hash embedding complete", total=len(embeddings))
        return embeddings
