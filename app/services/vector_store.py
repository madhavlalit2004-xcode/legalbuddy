import chromadb
from app.core.config import settings
from app.core.exceptions import CollectionException, StorageException, EmbeddingException
from app.core.logging import get_logger

logger = get_logger(__name__)

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("chromadb collection ready", collection=settings.CHROMA_COLLECTION_NAME, path=settings.CHROMA_PERSIST_DIR)
        return _collection
    except Exception as e:
        logger.warning("failed to initialize chromadb", error=str(e))
        raise StorageException(message=f"Could not initialize vector storage: {e}")


def _distance_to_similarity(distance: float) -> float:
    similarity = 1.0 - distance
    return max(0.0, min(1.0, similarity))


def add_chunks(chunk_ids: list[str], embeddings: list[list[float]], texts: list[str], metadatas: list[dict]) -> None:
    if not chunk_ids:
        logger.warning("add_chunks called with empty list, nothing to do")
        return
    if not (len(chunk_ids) == len(embeddings) == len(texts) == len(metadatas)):
        raise EmbeddingException(message="chunk_ids, embeddings, texts, and metadatas must all be the same length")

    collection = _get_collection()
    try:
        collection.add(ids=chunk_ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        logger.info("chunks added to vector store", count=len(chunk_ids))
    except Exception as e:
        logger.warning("failed to add chunks to chromadb", error=str(e))
        raise StorageException(message=f"Failed to store chunks in vector database: {e}")


def query_similar(query_embedding: list[float], top_k: int = 5, document_id: str | None = None) -> list[dict]:
    collection = _get_collection()
    where_filter = {"document_id": document_id} if document_id else None

    try:
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where_filter)
    except Exception as e:
        logger.warning("chromadb query failed", error=str(e))
        raise StorageException(message=f"Vector search failed: {e}")

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    matches = []
    for i in range(len(ids)):
        metadata = metadatas[i] or {}
        matches.append({
            "chunk_id": ids[i],
            "text": documents[i],
            "similarity_score": _distance_to_similarity(distances[i]),
            "page_number": metadata.get("page_number", 0),
            "document_id": metadata.get("document_id", "")
        })

    logger.info("vector query complete", results_found=len(matches), document_id=document_id)
    return matches


def delete_document_chunks(document_id: str) -> int:
    collection = _get_collection()
    try:
        existing = collection.get(where={"document_id": document_id})
        chunk_ids = existing["ids"]
        if not chunk_ids:
            logger.info("no chunks found to delete", document_id=document_id)
            return 0
        collection.delete(ids=chunk_ids)
        logger.info("chunks deleted", document_id=document_id, count=len(chunk_ids))
        return len(chunk_ids)
    except Exception as e:
        logger.warning("failed to delete chunks", document_id=document_id, error=str(e))
        raise StorageException(message=f"Failed to delete document chunks: {e}")


def get_collection_count() -> int:
    collection = _get_collection()
    return collection.count()