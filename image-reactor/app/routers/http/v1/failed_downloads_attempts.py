"""Failed downloads attempts API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from app.domains.models import FailedDownloadAttempt, FailedDownloadAttemptCreate
from app.internal.exception_handler import handle_exception
from app.repositories.failed_downloads_attempts_repository import FailedDownloadsAttemptsRepository
from app.services.database import get_database
from app.services.metrics import track_failed_attempt

router = APIRouter(prefix="/failed-downloads-attempts", tags=["Failed Downloads Attempts"])


def get_repository() -> FailedDownloadsAttemptsRepository:
    """Get failed downloads attempts repository instance."""
    db = get_database()
    return FailedDownloadsAttemptsRepository(db.get_pool())


@router.post(
    "/fail",
    response_model=FailedDownloadAttempt,
    status_code=status.HTTP_201_CREATED,
    summary="Record failed download attempt",
    description="Record a failed download attempt. If the image doesn't exist, creates a stub image record first.",
)
async def record_failed_download(request: FailedDownloadAttemptCreate) -> FailedDownloadAttempt:
    """Record a failed download attempt.

    If an image with the given link exists, adds a failed download attempt record to it.
    If no image exists, creates a stub image (with only the link) and then records the failed attempt.

    All operations are performed within a single database transaction to ensure atomicity.

    Args:
        request: Failed download information (link, error_message, http_status)

    Returns:
        Created failed download attempt record

    Raises:
        HTTPException: If the operation fails
    """
    logger.bind(
        link=request.link,
        error_message=request.error_message,
        http_status=request.http_status,
        status=request.attempt_status,
        database_id=request.database_id,
        item_id=request.item_id,
        property_name=request.property_name,
        image_number=request.image_number,
    ).info("Recording failed download attempt")

    repo = get_repository()

    try:
        # Create FailedDownloadAttemptCreate from request
        created_attempt = await repo.record_failed_download(request)
        logger.bind(id=created_attempt.id, link=request.link).info("Failed download attempt recorded")

        # Track metrics
        track_failed_attempt(
            created_attempt.database_id or "none",
            created_attempt.attempt_status,
        )

        return created_attempt
    except Exception as e:
        logger.bind(link=request.link, error=str(e)).error("Failed to record failed download attempt", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message="Failed to record failed download attempt",
            generic_detail="Failed to record failed download attempt",
        ) from e


@router.get(
    "/failed",
    response_model=list[FailedDownloadAttempt],
    summary="List failed download attempts",
    description="Retrieve all failed download attempts with optional time period filtering and pagination",
)
async def list_failed_download_attempts(
    from_date: Annotated[datetime | None, Query(description="Start date (inclusive) for filtering attempts")] = None,
    to_date: Annotated[datetime | None, Query(description="End date (inclusive) for filtering attempts")] = None,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 100,
) -> list[FailedDownloadAttempt]:
    """List failed download attempts with optional filtering and pagination.

    Args:
        from_date: Optional start date (inclusive) for filtering
        to_date: Optional end date (inclusive) for filtering
        offset: Number of records to skip (for pagination)
        limit: Maximum number of records to return (1-1000)

    Returns:
        List of failed download attempt records, ordered by attempted_at DESC

    Raises:
        HTTPException: If from_date > to_date or query fails
    """
    # Validate date range
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be less than or equal to to_date",
        )

    logger.bind(from_date=from_date, to_date=to_date, limit=limit, offset=offset).debug("Getting failed download attempts")
    repo = get_repository()

    try:
        # Convert datetime to ISO string for database query
        from_date_str = from_date.isoformat() if from_date else None
        to_date_str = to_date.isoformat() if to_date else None

        # Get paginated results from database (LIMIT/OFFSET applied at DB level)
        attempts = await repo.get_failed_download_attempts(from_date_str, to_date_str, limit, offset)

        logger.bind(count=len(attempts), limit=limit, offset=offset).debug("Failed download attempts retrieved")
        return attempts
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(error=str(e)).error("Failed to get failed download attempts", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message="Failed to get failed download attempts",
            generic_detail="Failed to get failed download attempts",
        ) from e


@router.get(
    "/{attempt_id}",
    response_model=FailedDownloadAttempt,
    summary="Get failed download attempt by ID",
    description="Retrieve a specific failed download attempt by its ID",
)
async def get_failed_download_attempt(attempt_id: int) -> FailedDownloadAttempt:
    """Get failed download attempt by ID.

    Args:
        attempt_id: The database ID of the failed download attempt

    Returns:
        Failed download attempt record

    Raises:
        HTTPException: If failed download attempt not found or query fails
    """
    logger.bind(attempt_id=attempt_id).debug("Getting failed download attempt by ID")
    repo = get_repository()

    try:
        attempt = await repo.get_failed_download_attempt_by_id(attempt_id)
        if not attempt:
            logger.bind(id=attempt_id).warning("Failed download attempt not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed download attempt with ID {attempt_id} not found",
            )
        logger.bind(id=attempt_id).debug("Failed download attempt retrieved")
        return attempt
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(id=attempt_id, error=str(e)).error("Failed to get failed download attempt", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message=f"Failed to get failed download attempt {attempt_id}",
            generic_detail="Failed to get failed download attempt",
        ) from e
