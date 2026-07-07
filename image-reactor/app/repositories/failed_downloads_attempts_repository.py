"""Repository for failed downloads attempts-related database operations."""

from datetime import datetime

import asyncpg
from loguru import logger

from app.domains.models import FailedDownloadAttempt, FailedDownloadAttemptCreate
from app.domains.schema import Schema


class FailedDownloadsAttemptsRepository:
    """Repository for managing failed downloads attempts."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize repository with database pool."""
        self.pool = pool

    async def record_failed_download(self, failed_download_attempt_create: FailedDownloadAttemptCreate) -> FailedDownloadAttempt:
        """Record a failed download attempt with transaction.

        If a failed download attempt already exists for this link, it will be updated
        with the new information and tries will be incremented. Otherwise, a new
        record will be created.
        """
        logger.debug("Recording failed download in database", link=failed_download_attempt_create.link)
        async with self.pool.acquire() as conn, conn.transaction():
            # Try to find existing failed download attempt by link
            row = await conn.fetchrow(
                f"SELECT * FROM {Schema.failed_downloads_attempts.TABLE} WHERE link = $1 LIMIT 1",  # noqa: S608
                failed_download_attempt_create.link,
            )

            if row:
                # Record new try for existing failed download attempt - all fields except id and link, increment tries
                logger.debug("Recording new try for existing failed download attempt", link=failed_download_attempt_create.link, existing_id=row["id"])
                row = await conn.fetchrow(
                    f"""
                    UPDATE {Schema.failed_downloads_attempts.TABLE}
                    SET {Schema.failed_downloads_attempts.ATTEMPTED_AT} = NOW(),
                        {Schema.failed_downloads_attempts.ATTEMPT_STATUS} = $2,
                        {Schema.failed_downloads_attempts.ERROR_MESSAGE} = $3,
                        {Schema.failed_downloads_attempts.HTTP_STATUS} = $4,
                        database_id = $5,
                        item_id = $6,
                        property_name = $7,
                        image_number = $8,
                        tries = tries + 1
                    WHERE {Schema.failed_downloads_attempts.ID} = $1
                    RETURNING *
                    """,  # noqa: S608
                    row["id"],
                    failed_download_attempt_create.attempt_status,
                    failed_download_attempt_create.error_message,
                    failed_download_attempt_create.http_status,
                    failed_download_attempt_create.database_id,
                    failed_download_attempt_create.item_id,
                    failed_download_attempt_create.property_name,
                    failed_download_attempt_create.image_number,
                )
            else:
                # Create new failed download attempt
                logger.debug("Creating new failed download attempt", link=failed_download_attempt_create.link)
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO {Schema.failed_downloads_attempts.TABLE} (
                        link, {Schema.failed_downloads_attempts.ATTEMPTED_AT},
                        {Schema.failed_downloads_attempts.ATTEMPT_STATUS}, {Schema.failed_downloads_attempts.ERROR_MESSAGE},
                        {Schema.failed_downloads_attempts.HTTP_STATUS},
                        database_id, item_id, property_name, image_number, tries
                    )
                    VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, 1)
                    RETURNING *
                    """,  # noqa: S608
                    failed_download_attempt_create.link,
                    failed_download_attempt_create.attempt_status,
                    failed_download_attempt_create.error_message,
                    failed_download_attempt_create.http_status,
                    failed_download_attempt_create.database_id,
                    failed_download_attempt_create.item_id,
                    failed_download_attempt_create.property_name,
                    failed_download_attempt_create.image_number,
                )

        logger.debug("Failed download attempt recorded", link=failed_download_attempt_create.link, attempt_id=row["id"])
        # Convert row to dict and add image_link (same as link since we don't have image relationship)
        result_dict = dict(row)
        result_dict["image_link"] = result_dict.get("link")
        return FailedDownloadAttempt(**result_dict)

    async def get_failed_download_attempt_by_id(self, attempt_id: int) -> FailedDownloadAttempt | None:
        """Get failed download attempt by ID."""
        logger.debug("Fetching failed download attempt from database", attempt_id=attempt_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT *
                FROM {Schema.failed_downloads_attempts.TABLE}
                WHERE {Schema.failed_downloads_attempts.ID} = $1
                LIMIT 1
                """,  # noqa: S608
                attempt_id,
            )

        if row:
            logger.debug("Failed download attempt found in database", attempt_id=attempt_id)
            result_dict = dict(row)
            result_dict["image_link"] = result_dict.get("link")
            return FailedDownloadAttempt(**result_dict)
        logger.debug("Failed download attempt not found in database", attempt_id=attempt_id)
        return None

    async def get_failed_download_attempts(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FailedDownloadAttempt]:
        """Get all failed download attempts with optional time period filter and pagination.

        Args:
            from_date: Optional start date (inclusive) in ISO format
            to_date: Optional end date (inclusive) in ISO format
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of failed download attempt records, ordered by attempted_at DESC
        """
        logger.debug("Fetching failed download attempts from database", from_date=from_date, to_date=to_date, limit=limit, offset=offset)
        async with self.pool.acquire() as conn:
            query = f"""
                SELECT *
                FROM {Schema.failed_downloads_attempts.TABLE}
                WHERE {Schema.failed_downloads_attempts.ATTEMPT_STATUS} = 'failed'
            """  # noqa: S608
            params = []

            if from_date:
                # Convert ISO string to datetime object for PostgreSQL
                from_date_obj = datetime.fromisoformat(from_date) if isinstance(from_date, str) else from_date
                params.append(from_date_obj)
                query += f" AND {Schema.failed_downloads_attempts.ATTEMPTED_AT} >= ${len(params)}"

            if to_date:
                # Convert ISO string to datetime object for PostgreSQL
                to_date_obj = datetime.fromisoformat(to_date) if isinstance(to_date, str) else to_date
                params.append(to_date_obj)
                query += f" AND {Schema.failed_downloads_attempts.ATTEMPTED_AT} <= ${len(params)}"

            query += f" ORDER BY {Schema.failed_downloads_attempts.ATTEMPTED_AT} DESC"

            # Add LIMIT and OFFSET
            params.append(limit)
            query += f" LIMIT ${len(params)}"

            params.append(offset)
            query += f" OFFSET ${len(params)}"

            rows = await conn.fetch(query, *params)

        logger.debug("Failed download attempts fetched from database", count=len(rows), limit=limit, offset=offset)
        # Add image_link to each row (same as link since we don't have image relationship)
        return [FailedDownloadAttempt(**{**dict(row), "image_link": row["link"]}) for row in rows]

    async def delete_failed_download_attempt_by_link(self, link: str) -> bool:
        """Delete a failed download attempt by link.

        Returns:
            True if the attempt was deleted, False if it didn't exist
        """
        logger.debug("Deleting failed download attempt from database", link=link)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {Schema.failed_downloads_attempts.TABLE} WHERE {Schema.failed_downloads_attempts.LINK} = $1",  # noqa: S608
                link,
            )

        # result will be "DELETE 1" if successful, "DELETE 0" if not found
        deleted = result.endswith("1")
        if deleted:
            logger.debug("Failed download attempt deleted from database", link=link)
        else:
            logger.debug("Failed download attempt not found for deletion", link=link)

        return deleted
