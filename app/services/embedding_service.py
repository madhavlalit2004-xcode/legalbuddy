import httpx
from app.core.config import settings
from app.core.exceptions import OllamaUnreachableException, ModelNotFoundException
from app.core.logging import get_logger

logger = get_logger(__name__)

# How many times to retry a failed embedding call before giving up
_MAX_RETRIES = 3


def _call_ollama_embedding(text: str) -> list[float]:
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": settings.OLLAMA_EMBEDDING_MODEL,
        "prompt": text
    }

    # 10s per attempt, 3 attempts = worst case ~30s before failing.
    # Long enough for a slow local model, short enough not to hang a web request.
    timeout_seconds = 10.0
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = httpx.post(url, json=payload, timeout=timeout_seconds)

            if response.status_code == 404:
                # Model not pulled/found on this Ollama instance
                logger.warning("ollama model not found", model=settings.OLLAMA_EMBEDDING_MODEL)
                raise ModelNotFoundException(
                    message=f"Embedding model '{settings.OLLAMA_EMBEDDING_MODEL}' not found in Ollama. "
                            f"Run: ollama pull {settings.OLLAMA_EMBEDDING_MODEL}"
                )

            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding")
            if not embedding:
                raise ValueError("Ollama response missing 'embedding' field")

            return embedding

        except ModelNotFoundException:
            # Don't retry this — retrying won't make the model appear
            raise

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
            last_error = e
            logger.warning(
                "ollama embedding call failed, retrying",
                attempt=attempt,
                max_retries=_MAX_RETRIES,
                error=str(e)
            )

    # All retries exhausted — Ollama is genuinely unreachable
    logger.warning("ollama unreachable after retries", error=str(last_error))
    raise OllamaUnreachableException(
        message=f"Could not reach Ollama at {settings.OLLAMA_BASE_URL} after {_MAX_RETRIES} attempts."
    )


def get_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    return _call_ollama_embedding(text)


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    failed_count = 0

    for i, text in enumerate(texts):
        try:
            embedding = get_embedding(text)
            embeddings.append(embedding)
        except OllamaUnreachableException:
            # If Ollama is down, every subsequent call will fail too — stop immediately
            logger.warning("ollama unreachable, aborting batch", completed=i, total=len(texts))
            raise
        except ValueError:
            # Empty text for this particular chunk — skip it, don't kill the whole batch
            logger.warning("skipping empty text in batch", index=i)
            failed_count += 1
            continue

    logger.info(
        "batch embedding complete",
        total=len(texts),
        succeeded=len(embeddings),
        skipped=failed_count
    )
    return embeddings