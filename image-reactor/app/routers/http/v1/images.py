"""Image metadata API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from app.domains.models import Image, ImageCreate
from app.internal.exception_handler import handle_exception
from app.repositories.failed_downloads_attempts_repository import FailedDownloadsAttemptsRepository
from app.repositories.image_repository import ImageRepository
from app.services.database import get_database
from app.services.metrics import track_image_stored

router = APIRouter(prefix="/images", tags=["Images"])


def get_repository_images() -> ImageRepository:
    """Get image repository instance."""
    db = get_database()
    return ImageRepository(db.get_pool())


def get_repository_attempts() -> ImageRepository:
    """Get failed download attempts repository instance."""
    db = get_database()
    return FailedDownloadsAttemptsRepository(db.get_pool())


@router.post(
    "",
    response_model=Image,
    status_code=status.HTTP_201_CREATED,
    summary="Create image",
    description="Create a new image record in the database. The stored_at timestamp will be automatically set to NOW().",
)
async def create_image(image: ImageCreate) -> Image:
    """Create a new image record.

    Args:
        image: Image data to create (all fields except stored_at)

    Returns:
        Created image with id and stored_at timestamp

    Raises:
        HTTPException: If image creation fails (e.g., duplicate link)
    """
    logger.bind(link=image.link, store_collection=image.store_collection).info("Creating image")
    repo = get_repository_images()
    repo_failed = get_repository_attempts()

    try:
        created_image = await repo.create_image(image)
        logger.bind(id=created_image.id, link=created_image.link).info("Image created successfully")
        await repo_failed.delete_failed_download_attempt_by_link(image.link)

        # Track metrics
        track_image_stored(
            created_image.database_id or "none",
            created_image.store_collection,
        )

        return created_image
    except Exception as e:
        logger.bind(link=image.link, error=str(e)).error("Failed to create image", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message="Failed to create image",
            generic_detail="Failed to create image",
        ) from e


@router.get(
    "/by-path",
    response_model=Image,
    summary="Get image by path",
    description="Retrieve an image by its store_collection and filepath",
)
async def get_image_by_path(
    store_collection: str = Query(..., description="Storage collection name"),
    filepath: str = Query(..., description="File path within the collection"),
) -> Image:
    """Get image by path.

    Args:
        store_collection: Storage collection name
        filepath: File path within the collection

    Returns:
        Image record

    Raises:
        HTTPException: If image not found or query fails
    """
    logger.bind(collection=store_collection, filepath=filepath).debug("Getting image by path")
    repo = get_repository_images()

    try:
        image = await repo.get_image_by_path(store_collection, filepath)
        if not image:
            logger.bind(collection=store_collection, filepath=filepath).warning("Image not found by path")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image not found at {store_collection}/{filepath}",
            )
        logger.bind(id=image.id, collection=store_collection, filepath=filepath).debug("Image retrieved by path successfully")
        return image
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(collection=store_collection, filepath=filepath, error=str(e)).error("Failed to get image by path", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message=f"Failed to get image by path {store_collection}/{filepath}",
            generic_detail="Failed to get image",
        ) from e


@router.get(
    "/{image_id}",
    response_model=Image,
    summary="Get image by ID",
    description="Retrieve an image by its database ID",
)
async def get_image_by_id(image_id: int) -> Image:
    """Get image by ID.

    Args:
        image_id: The database ID of the image

    Returns:
        Image record

    Raises:
        HTTPException: If image not found or query fails
    """
    logger.bind(image_id=image_id).debug("Getting image by ID")
    repo = get_repository_images()

    try:
        image = await repo.get_image_by_id(image_id)
        if not image:
            logger.bind(id=image_id).warning("Image not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image with ID {image_id} not found",
            )
        logger.bind(id=image_id, link=image.link).debug("Image retrieved successfully")
        return image
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(image_id=image_id, error=str(e)).error("Failed to get image by ID", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message=f"Failed to get image by ID {image_id}",
            generic_detail="Failed to get image",
        ) from e


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete image by ID",
    description="Delete an image by its ID. This will also cascade delete all associated download attempts.",
)
async def delete_image(image_id: int) -> dict:
    """Delete image by ID.

    Args:
        image_id: The database ID of the image to delete

    Returns:
        Empty object indicating successful deletion

    Raises:
        HTTPException: If image not found or deletion fails
    """
    logger.bind(id=image_id).info("Deleting image")
    repo = get_repository_images()

    try:
        deleted = await repo.delete_image(image_id)
        if not deleted:
            logger.bind(id=image_id).warning("Image not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image with ID {image_id} not found",
            )
        logger.bind(id=image_id).info("Image deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(id=image_id, error=str(e)).error("Failed to delete image", exc_info=True)
        raise handle_exception(
            exception=e,
            log_message=f"Failed to delete image {image_id}",
            generic_detail="Failed to delete image",
        ) from e
    return {}
