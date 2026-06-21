import time
from app.core.exceptions import EmptyDocumentException
from app.core.logging import get_logger
from app.models.schemas import QueryRequest, QueryResponse, ChunkResult, LegalInsight
from app.services.embedding_service import get_embedding
from app.services.vector_store import query_similar
from app.utils.legal_extractor import extract_insights, aggregate_insights

logger = get_logger(__name__)


def search_documents(request: QueryRequest) -> QueryResponse:
    start_time = time.time()

    logger.info("search started", query=request.query, document_id=request.document_id, top_k=request.top_k)

    query_embedding = get_embedding(request.query)

    raw_matches = query_similar(
        query_embedding=query_embedding,
        top_k=request.top_k,
        document_id=request.document_id
    )

    filtered_matches = [
        m for m in raw_matches
        if m["similarity_score"] >= request.similarity_threshold
    ]

    if not filtered_matches:
        logger.info("search returned no results above threshold", query=request.query,
                    raw_count=len(raw_matches), threshold=request.similarity_threshold)

    chunk_results: list[ChunkResult] = []
    all_chunk_insights: list[list[LegalInsight]] = []

    for match in filtered_matches:
        insights = extract_insights(match["text"])
        all_chunk_insights.append(insights)

        chunk_results.append(ChunkResult(
            chunk_id=match["chunk_id"],
            text=match["text"],
            similarity_score=match["similarity_score"],
            page_number=match["page_number"],
            insights=insights
        ))

    aggregate_summary = aggregate_insights(all_chunk_insights)
    elapsed_ms = (time.time() - start_time) * 1000

    logger.info("search complete", query=request.query, results_returned=len(chunk_results),
                overall_risk=aggregate_summary["overall_risk"], elapsed_ms=round(elapsed_ms, 1))

    return QueryResponse(
        query=request.query,
        total_results=len(chunk_results),
        results=chunk_results,
        aggregate_insights=aggregate_summary,
        processing_time_ms=round(elapsed_ms, 1)
    )