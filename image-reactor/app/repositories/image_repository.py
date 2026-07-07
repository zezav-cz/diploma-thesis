"""Repository for image-related database operations."""

import asyncpg
from loguru import logger

from app.domains.models import Image, ImageCreate
from app.domains.schema import Schema


class ImageRepository:
    """Repository for managing image metadata."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize repository with database pool."""
        self.pool = pool

    # Private query methods

    async def _find_image_by_id(self, conn: asyncpg.Connection, image_id: int) -> asyncpg.Record | None:
        """Find image by ID (internal query)."""
        return await conn.fetchrow(
            f"SELECT * FROM {Schema.images.TABLE} WHERE {Schema.images.ID} = $1 LIMIT 1",  # noqa: S608
            image_id,
        )

    async def _find_image_by_link(self, conn: asyncpg.Connection, link: str) -> asyncpg.Record | None:
        """Find image by link (internal query)."""
        return await conn.fetchrow(
            f"SELECT * FROM {Schema.images.TABLE} WHERE {Schema.images.LINK} = $1 LIMIT 1",  # noqa: S608
            link,
        )

    async def _find_image_by_path(
        self,
        conn: asyncpg.Connection,
        store_collection: str,
        filepath: str,
    ) -> asyncpg.Record | None:
        """Find image by store_collection and filepath (internal query)."""
        return await conn.fetchrow(
            f"SELECT * FROM {Schema.images.TABLE} WHERE {Schema.images.STORE_COLLECTION} = $1 AND {Schema.images.FILEPATH} = $2 LIMIT 1",  # noqa: S608
            store_collection,
            filepath,
        )

    async def _insert_image(self, conn: asyncpg.Connection, image: ImageCreate) -> asyncpg.Record:
        """Insert new image (internal query)."""
        return await conn.fetchrow(
            f"""
            INSERT INTO {Schema.images.TABLE} (
                {Schema.images.LINK}, {Schema.images.STORE_COLLECTION}, {Schema.images.FILEPATH},
                {Schema.images.DATABASE_ID}, {Schema.images.ITEM_ID},
                {Schema.images.PROPERTY_NAME}, {Schema.images.IMAGE_NUMBER},
                {Schema.images.HASHSUM}, {Schema.images.EXTENSION},
                {Schema.images.WIDTH}, {Schema.images.HEIGHT}, {Schema.images.STORED_AT}
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
            RETURNING *
            """,  # noqa: S608
            image.link,
            image.store_collection,
            image.filepath,
            image.database_id,
            image.item_id,
            image.property_name,
            image.image_number,
            image.hashsum,
            image.extension,
            image.width,
            image.height,
        )

    async def _delete_image(self, conn: asyncpg.Connection, image_id: int) -> str:
        """Delete image by ID (internal query)."""
        return await conn.execute(
            f"DELETE FROM {Schema.images.TABLE} WHERE {Schema.images.ID} = $1",  # noqa: S608
            image_id,
        )

    # Public repository methods

    async def create_image(self, image: ImageCreate) -> Image:
        """Create a new image record."""
        logger.debug("Creating image in database", link=image.link)
        async with self.pool.acquire() as conn:
            row = await self._insert_image(conn, image)
            return Image(**dict(row))

    async def get_image_by_id(self, image_id: int) -> Image | None:
        """Get image by ID."""
        logger.debug("Fetching image by ID from database", image_id=image_id)
        async with self.pool.acquire() as conn:
            row = await self._find_image_by_id(conn, image_id)

        if row:
            logger.debug("Image found in database", image_id=image_id)
            return Image(**dict(row))
        logger.debug("Image not found in database", image_id=image_id)
        return None

    async def get_image_by_link(self, link: str) -> Image | None:
        """Get image by link URL."""
        logger.debug("Fetching image by link from database", link=link)
        async with self.pool.acquire() as conn:
            row = await self._find_image_by_link(conn, link)

        if row:
            logger.debug("Image found in database by link", image_id=row[Schema.images.ID], link=link)
            return Image(**dict(row))
        logger.debug("Image not found in database by link", link=link)
        return None

    async def get_image_by_path(self, store_collection: str, filepath: str) -> Image | None:
        """Get image by store_collection and filepath."""
        logger.debug("Fetching image by path from database", store_collection=store_collection, filepath=filepath)
        async with self.pool.acquire() as conn:
            row = await self._find_image_by_path(conn, store_collection, filepath)

        if row:
            logger.debug("Image found in database by path", image_id=row[Schema.images.ID], store_collection=store_collection, filepath=filepath)
            return Image(**dict(row))
        logger.debug("Image not found in database by path", store_collection=store_collection, filepath=filepath)
        return None

    async def delete_image(self, image_id: int) -> bool:
        """Delete an image by ID.

        This will also cascade delete all associated failed downloads attempts due to
        the ON DELETE CASCADE constraint on the foreign key.

        Args:
            image_id: The database ID of the image to delete

        Returns:
            True if the image was deleted, False if it didn't exist
        """
        logger.debug("Deleting image from database", image_id=image_id)
        async with self.pool.acquire() as conn:
            result = await self._delete_image(conn, image_id)

        # result will be "DELETE 1" if successful, "DELETE 0" if not found
        deleted_count = int(result.split()[-1])
        if deleted_count > 0:
            logger.debug("Image deleted from database", image_id=image_id)
        else:
            logger.debug("Image not found for deletion in database", image_id=image_id)
        return deleted_count > 0
