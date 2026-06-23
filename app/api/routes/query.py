from fastapi import APIRouter, status

from app.core.logging import get_logger
from app.models.schemas import QueryRequest, QueryResponse
from app.services.search_service import search_documents

logger = get_logger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
async def query_documents(request: QueryRequest) -> QueryResponse:
    logger.info(
        "query request received",
        query=request.query,
        document_id=request.document_id,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )

    return await search_documents(request)
