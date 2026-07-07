"""Database connection pool management."""

import asyncpg
from loguru import logger

from app.internal.config import Settings


def log_query(query_record):
    if query_record.exception:
        logger.bind(exception=query_record.exception, query=query_record.query, args=query_record.args, elapsed=query_record.elapsed).error("Query failed")
    else:
        logger.bind(query=query_record.query, args=query_record.args, elapsed=query_record.elapsed).trace("Executing query")


async def setup_connection(conn):
    """
    This function runs for every new connection created in the pool.
    """
    conn.add_query_logger(log_query)


class Database:
    """Database connection pool manager."""

    def __init__(self, settings: Settings) -> None:
        """Initialize database manager."""
        self.settings = settings
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create database connection pool."""
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return

        try:
            logger.info("Creating database connection pool")

            # Enable asyncpg logging for query tracing when log level is TRACE
            setup_hook = None
            if self.settings.log_level.upper() == "TRACE":
                setup_hook = setup_connection

            self.pool = await asyncpg.create_pool(
                dsn=str(self.settings.database_url),
                min_size=self.settings.db_pool_min_size,
                max_size=self.settings.db_pool_max_size,
                max_queries=self.settings.db_pool_max_queries,
                max_inactive_connection_lifetime=self.settings.db_pool_max_inactive_connection_lifetime,
                command_timeout=60,
                setup=setup_hook,
            )
            logger.bind(min_size=self.settings.db_pool_min_size, max_size=self.settings.db_pool_max_size).info("Database pool created")
        except Exception as e:
            logger.bind(error=str(e)).error("Failed to create database pool", exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool is None:
            logger.warning("Database pool does not exist")
            return

        try:
            logger.info("Closing database connection pool")
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
        except Exception as e:
            logger.bind(error=str(e)).error("Error closing database pool", exc_info=True)
            raise

    async def health_check(self) -> bool:
        """Check database connection health."""
        if self.pool is None:
            logger.error("Database pool is not initialized")
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.bind(error=str(e)).error("Database health check failed")
            return False

    def get_pool(self) -> asyncpg.Pool:
        """Get database connection pool."""
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self.pool


# Global database instance
db = Database(settings=None)  # Will be initialized in app startup


def get_database() -> Database:
    """Get database instance."""
    return db
