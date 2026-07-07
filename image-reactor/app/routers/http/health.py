"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, Response, status
from loguru import logger

from app.domains.models import HealthResponse
from app.services.database import get_database

router = APIRouter(tags=["Health"])


def get_api_info() -> dict[str, str]:
    """Get API information and paths."""
    return {
        "health": "/health",
        "health_ready": "/health/ready",
        "health_live": "/health/live",
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check the health status of the API and database connection",
)
async def health_check() -> HealthResponse:
    """Perform health check on the service and database."""
    logger.trace("Health check requested")
    db = get_database()
    db_healthy = await db.health_check()

    logger.bind(status="healthy" if db_healthy else "unhealthy").trace("Health check completed")
    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        database="connected" if db_healthy else "disconnected",
        timestamp=datetime.now(),
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
)
async def readiness_check(response: Response) -> dict[str, str]:
    """Check if service is ready."""
    logger.trace("Readiness check requested")
    db = get_database()
    if not await db.health_check():
        logger.warning("Service not ready - database unavailable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "database_unavailable"}

    logger.trace("Service ready")
    return {"status": "ready"}


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if the service is alive",
)
async def liveness_check() -> dict[str, str]:
    """Check if service is alive."""
    logger.trace("Liveness check requested")
    return {"status": "alive"}
