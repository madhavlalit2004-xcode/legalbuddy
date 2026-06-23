from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import HealthResponse
from app.services.vector_store import get_collection_count

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    logger.info("health check requested")
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready")
def readiness_check() -> dict:
    components = {
        "api": {"status": "ok"},
        "settings": {"status": "ok"},
        "vector_store": {"status": "unknown"},
    }

    status = "ready"

    try:
        chunk_count = get_collection_count()
        components["vector_store"] = {
            "status": "ok",
            "detail": f"{chunk_count} chunks in collection",
        }
    except Exception as exc:
        status = "degraded"
        components["vector_store"] = {
            "status": "error",
            "detail": str(exc),
        }

    logger.info("readiness check complete", status=status)

    return {
        "status": status,
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "components": components,
    }
