"""Unit tests for repositories with mocked database."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.schema import Schema
from app.repositories.failed_downloads_attempts_repository import FailedDownloadsAttemptsRepository
from app.repositories.image_repository import ImageRepository
from tests.fixtures.factories import create_failed_download_attempt_data, create_image_data


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg connection pool."""
    pool = MagicMock()
    connection = MagicMock()  # Use MagicMock instead of AsyncMock
    transaction = MagicMock()

    # Setup async context manager for acquire
    acquire_context = AsyncMock()
    acquire_context.__aenter__.return_value = connection
    acquire_context.__aexit__.return_value = None
    pool.acquire.return_value = acquire_context

    # Setup async context manager for transaction
    # Must be a regular MagicMock, not AsyncMock
    transaction_context = MagicMock()
    transaction_context.__enter__ = MagicMock(return_value=transaction)
    transaction_context.__exit__ = MagicMock(return_value=None)
    transaction_context.__aenter__ = AsyncMock(return_value=transaction)
    transaction_context.__aexit__ = AsyncMock(return_value=None)
    connection.transaction.return_value = transaction_context

    # Mock async methods on connection
    connection.fetchrow = AsyncMock()
    connection.execute = AsyncMock()
    connection.fetch = AsyncMock()
    connection.fetchval = AsyncMock()

    return pool


@pytest.fixture
def image_repository(mock_pool):
    """Create ImageRepository with mocked pool."""
    return ImageRepository(mock_pool)


@pytest.fixture
def failed_downloads_repository(mock_pool):
    """Create FailedDownloadsAttemptsRepository with mocked pool."""
    return FailedDownloadsAttemptsRepository(mock_pool)


@pytest.mark.unit
class TestImageRepository:
    """Tests for ImageRepository with mocked database."""

    async def test_create_image_new(self, image_repository, mock_pool):
        """Test creating a new image."""
        # Arrange
        image_data = create_image_data(link="https://example.com/image.jpg")

        # Get the mocked connection from the pool fixture
        connection = mock_pool.acquire.return_value.__aenter__.return_value

        # Mock the insert operation
        connection.fetchrow.return_value = {
            Schema.images.ID: 1,
            Schema.images.LINK: image_data.link,
            Schema.images.STORE_COLLECTION: image_data.store_collection,
            Schema.images.FILEPATH: image_data.filepath,
            Schema.images.DATABASE_ID: image_data.database_id,
            Schema.images.ITEM_ID: image_data.item_id,
            Schema.images.PROPERTY_NAME: image_data.property_name,
            Schema.images.IMAGE_NUMBER: image_data.image_number,
            Schema.images.HASHSUM: image_data.hashsum,
            Schema.images.EXTENSION: image_data.extension,
            Schema.images.WIDTH: image_data.width,
            Schema.images.HEIGHT: image_data.height,
            Schema.images.STORED_AT: None,
        }

        # Act
        result = await image_repository.create_image(image_data)

        # Assert
        assert result.id == 1
        assert result.link == image_data.link
        assert result.store_collection == image_data.store_collection
        assert result.database_id == image_data.database_id
        assert result.item_id == image_data.item_id
        assert result.property_name == image_data.property_name
        assert result.image_number == image_data.image_number
        assert connection.fetchrow.call_count == 1  # just insert

    async def test_get_image_by_id_found(self, image_repository, mock_pool):
        """Test getting image by ID when it exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        image_id = 123

        connection.fetchrow.return_value = {
            Schema.images.ID: image_id,
            Schema.images.LINK: "https://example.com/image.jpg",
            Schema.images.STORE_COLLECTION: "test_collection",
            Schema.images.FILEPATH: "/path/to/image.jpg",
            Schema.images.DATABASE_ID: "db01",
            Schema.images.ITEM_ID: 456,
            Schema.images.PROPERTY_NAME: "photo",
            Schema.images.IMAGE_NUMBER: 1,
            Schema.images.HASHSUM: "0" * 64,
            Schema.images.EXTENSION: "jpg",
            Schema.images.WIDTH: 1920,
            Schema.images.HEIGHT: 1080,
            Schema.images.STORED_AT: None,
        }

        # Act
        result = await image_repository.get_image_by_id(image_id)

        # Assert
        assert result is not None
        assert result.id == image_id
        assert result.link == "https://example.com/image.jpg"
        connection.fetchrow.assert_called_once()

    async def test_get_image_by_id_not_found(self, image_repository, mock_pool):
        """Test getting image by ID when it doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = None

        # Act
        result = await image_repository.get_image_by_id(999)

        # Assert
        assert result is None
        connection.fetchrow.assert_called_once()

    async def test_get_image_by_link_found(self, image_repository, mock_pool):
        """Test getting image by link when it exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        test_link = "https://example.com/test.jpg"

        connection.fetchrow.return_value = {
            Schema.images.ID: 456,
            Schema.images.LINK: test_link,
            Schema.images.STORE_COLLECTION: "test_collection",
            Schema.images.FILEPATH: "/path/to/test.jpg",
            Schema.images.DATABASE_ID: "db01",
            Schema.images.ITEM_ID: 789,
            Schema.images.PROPERTY_NAME: "photo",
            Schema.images.IMAGE_NUMBER: 2,
            Schema.images.HASHSUM: "0" * 64,
            Schema.images.EXTENSION: "jpg",
            Schema.images.WIDTH: 800,
            Schema.images.HEIGHT: 600,
            Schema.images.STORED_AT: None,
        }

        # Act
        result = await image_repository.get_image_by_link(test_link)

        # Assert
        assert result is not None
        assert result.id == 456
        assert result.link == test_link
        connection.fetchrow.assert_called_once()

    async def test_get_image_by_link_not_found(self, image_repository, mock_pool):
        """Test getting image by link when it doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = None

        # Act
        result = await image_repository.get_image_by_link("https://nonexistent.com/image.jpg")

        # Assert
        assert result is None

    async def test_get_image_by_path_found(self, image_repository, mock_pool):
        """Test getting image by path when it exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        store_collection = "test_collection"
        filepath = "/path/to/image.jpg"

        connection.fetchrow.return_value = {
            Schema.images.ID: 789,
            Schema.images.LINK: "https://example.com/image.jpg",
            Schema.images.STORE_COLLECTION: store_collection,
            Schema.images.FILEPATH: filepath,
            Schema.images.DATABASE_ID: "db01",
            Schema.images.ITEM_ID: 101,
            Schema.images.PROPERTY_NAME: "photo",
            Schema.images.IMAGE_NUMBER: 3,
            Schema.images.HASHSUM: "0" * 64,
            Schema.images.EXTENSION: "jpg",
            Schema.images.WIDTH: 1024,
            Schema.images.HEIGHT: 768,
            Schema.images.STORED_AT: None,
        }

        # Act
        result = await image_repository.get_image_by_path(store_collection, filepath)

        # Assert
        assert result is not None
        assert result.id == 789
        assert result.store_collection == store_collection
        assert result.filepath == filepath

    async def test_get_image_by_path_not_found(self, image_repository, mock_pool):
        """Test getting image by path when it doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = None

        # Act
        result = await image_repository.get_image_by_path("nonexistent", "/no/such/path.jpg")

        # Assert
        assert result is None

    async def test_delete_image_success(self, image_repository, mock_pool):
        """Test deleting an image that exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 1"

        # Act
        result = await image_repository.delete_image(123)

        # Assert
        assert result is True
        connection.execute.assert_called_once()

    async def test_delete_image_not_found(self, image_repository, mock_pool):
        """Test deleting an image that doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 0"

        # Act
        result = await image_repository.delete_image(999)

        # Assert
        assert result is False
        connection.execute.assert_called_once()

    async def test_transaction_rollback_on_error(self, image_repository, mock_pool):
        """Test that transaction is properly handled on error."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await image_repository.create_image(create_image_data())

        assert "Database error" in str(exc_info.value)


@pytest.mark.unit
class TestFailedDownloadsAttemptsRepository:
    """Tests for FailedDownloadsAttemptsRepository with mocked database."""

    async def test_get_failed_download_attempt_by_id_found(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempt by ID when it exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        attempt_id = 123
        test_link = "https://example.com/image.jpg"

        connection.fetchrow.return_value = {
            Schema.failed_downloads_attempts.ID: attempt_id,
            Schema.failed_downloads_attempts.LINK: test_link,
            Schema.failed_downloads_attempts.DATABASE_ID: "db01",
            Schema.failed_downloads_attempts.ITEM_ID: 789,
            Schema.failed_downloads_attempts.PROPERTY_NAME: "photo",
            Schema.failed_downloads_attempts.IMAGE_NUMBER: 1,
            Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
            Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
            Schema.failed_downloads_attempts.ERROR_MESSAGE: "Connection timeout",
            Schema.failed_downloads_attempts.HTTP_STATUS: 500,
            Schema.failed_downloads_attempts.IMAGE_LINK: test_link,
            Schema.failed_downloads_attempts.TRIES: 3,
        }

        # Act
        result = await failed_downloads_repository.get_failed_download_attempt_by_id(attempt_id)

        # Assert
        assert result is not None
        assert result.id == attempt_id
        assert result.link == test_link
        assert result.attempt_status == "failed"
        assert result.error_message == "Connection timeout"
        assert result.http_status == 500
        connection.fetchrow.assert_called_once()

    async def test_get_failed_download_attempt_by_id_not_found(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempt by ID when it doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = None

        # Act
        result = await failed_downloads_repository.get_failed_download_attempt_by_id(999)

        # Assert
        assert result is None
        connection.fetchrow.assert_called_once()

    async def test_record_failed_download_new_attempt(self, failed_downloads_repository, mock_pool):
        """Test recording a new failed download attempt."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        test_link = "https://example.com/image.jpg"

        attempt_data = create_failed_download_attempt_data(link=test_link, attempt_status="failed", error_message="Connection timeout", http_status=500)

        # Mock that no existing attempt is found, then new one is created
        connection.fetchrow.side_effect = [
            None,  # No existing attempt found
            {  # Insert new failed download attempt
                Schema.failed_downloads_attempts.ID: 100,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: attempt_data.database_id,
                Schema.failed_downloads_attempts.ITEM_ID: attempt_data.item_id,
                Schema.failed_downloads_attempts.PROPERTY_NAME: attempt_data.property_name,
                Schema.failed_downloads_attempts.IMAGE_NUMBER: attempt_data.image_number,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Connection timeout",
                Schema.failed_downloads_attempts.HTTP_STATUS: 500,
                Schema.failed_downloads_attempts.TRIES: 1,
            },
        ]

        # Act
        result = await failed_downloads_repository.record_failed_download(attempt_data)

        # Assert
        assert result.id == 100
        assert result.link == test_link
        assert result.attempt_status == "failed"
        assert result.error_message == "Connection timeout"
        assert result.http_status == 500
        assert connection.fetchrow.call_count == 2  # find + insert

    async def test_record_failed_download_update_existing(self, failed_downloads_repository, mock_pool):
        """Test recording failed download when attempt already exists - increments tries."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        test_link = "https://example.com/existing-image.jpg"

        attempt_data = create_failed_download_attempt_data(link=test_link, attempt_status="failed", error_message="Not found", http_status=404)

        # Mock that existing attempt is found, then updated
        connection.fetchrow.side_effect = [
            {  # Existing attempt found
                Schema.failed_downloads_attempts.ID: 200,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: "old_db",
                Schema.failed_downloads_attempts.ITEM_ID: 999,
                Schema.failed_downloads_attempts.PROPERTY_NAME: "old_prop",
                Schema.failed_downloads_attempts.IMAGE_NUMBER: 5,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Old error",
                Schema.failed_downloads_attempts.HTTP_STATUS: 500,
                Schema.failed_downloads_attempts.TRIES: 2,
            },
            {  # Updated attempt
                Schema.failed_downloads_attempts.ID: 200,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: attempt_data.database_id,
                Schema.failed_downloads_attempts.ITEM_ID: attempt_data.item_id,
                Schema.failed_downloads_attempts.PROPERTY_NAME: attempt_data.property_name,
                Schema.failed_downloads_attempts.IMAGE_NUMBER: attempt_data.image_number,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Not found",
                Schema.failed_downloads_attempts.HTTP_STATUS: 404,
                Schema.failed_downloads_attempts.TRIES: 3,  # Incremented
            },
        ]

        # Act
        result = await failed_downloads_repository.record_failed_download(attempt_data)

        # Assert
        assert result.id == 200
        assert result.link == test_link
        assert result.attempt_status == "failed"
        assert result.error_message == "Not found"
        assert result.http_status == 404
        assert connection.fetchrow.call_count == 2  # find + update

    async def test_get_failed_download_attempts_no_filters(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempts without date filters."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        test_link = "https://example.com/image.jpg"

        connection.fetch.return_value = [
            {
                Schema.failed_downloads_attempts.ID: 1,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: "db01",
                Schema.failed_downloads_attempts.ITEM_ID: 100,
                Schema.failed_downloads_attempts.PROPERTY_NAME: "photo",
                Schema.failed_downloads_attempts.IMAGE_NUMBER: 1,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Error 1",
                Schema.failed_downloads_attempts.HTTP_STATUS: 500,
                Schema.failed_downloads_attempts.IMAGE_LINK: test_link,
                Schema.failed_downloads_attempts.TRIES: 1,
            },
            {
                Schema.failed_downloads_attempts.ID: 2,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: "db02",
                Schema.failed_downloads_attempts.ITEM_ID: 200,
                Schema.failed_downloads_attempts.PROPERTY_NAME: "photo",
                Schema.failed_downloads_attempts.IMAGE_NUMBER: 2,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Error 2",
                Schema.failed_downloads_attempts.HTTP_STATUS: 404,
                Schema.failed_downloads_attempts.IMAGE_LINK: test_link,
                Schema.failed_downloads_attempts.TRIES: 1,
            },
        ]

        # Act
        result = await failed_downloads_repository.get_failed_download_attempts(limit=100, offset=0)

        # Assert
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
        connection.fetch.assert_called_once()

    async def test_get_failed_download_attempts_with_date_filters(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempts with date range filters."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        from_date = "2024-01-01T00:00:00"
        to_date = "2024-12-31T23:59:59"
        test_link = "https://example.com/image.jpg"

        connection.fetch.return_value = [
            {
                Schema.failed_downloads_attempts.ID: 5,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: "db03",
                Schema.failed_downloads_attempts.ITEM_ID: 500,
                Schema.failed_downloads_attempts.PROPERTY_NAME: "photo",
                Schema.failed_downloads_attempts.IMAGE_NUMBER: 3,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime(2024, 6, 15, 12, 0, 0),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Filtered error",
                Schema.failed_downloads_attempts.HTTP_STATUS: 503,
                Schema.failed_downloads_attempts.IMAGE_LINK: test_link,
                Schema.failed_downloads_attempts.TRIES: 2,
            },
        ]

        # Act
        result = await failed_downloads_repository.get_failed_download_attempts(from_date=from_date, to_date=to_date, limit=50, offset=10)

        # Assert
        assert len(result) == 1
        assert result[0].id == 5
        assert result[0].http_status == 503
        connection.fetch.assert_called_once()

    async def test_get_failed_download_attempts_pagination(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempts with pagination."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        test_link = "https://example.com/image.jpg"

        connection.fetch.return_value = [
            {
                Schema.failed_downloads_attempts.ID: 101,
                Schema.failed_downloads_attempts.LINK: test_link,
                Schema.failed_downloads_attempts.DATABASE_ID: "db04",
                Schema.failed_downloads_attempts.ITEM_ID: 1000,
                Schema.failed_downloads_attempts.PROPERTY_NAME: "photo",
                Schema.failed_downloads_attempts.IMAGE_NUMBER: 4,
                Schema.failed_downloads_attempts.ATTEMPTED_AT: datetime.now(),
                Schema.failed_downloads_attempts.ATTEMPT_STATUS: "failed",
                Schema.failed_downloads_attempts.ERROR_MESSAGE: "Page 2 item",
                Schema.failed_downloads_attempts.HTTP_STATUS: 500,
                Schema.failed_downloads_attempts.IMAGE_LINK: test_link,
                Schema.failed_downloads_attempts.TRIES: 1,
            },
        ]

        # Act
        result = await failed_downloads_repository.get_failed_download_attempts(limit=10, offset=20)

        # Assert
        assert len(result) == 1
        assert result[0].id == 101
        connection.fetch.assert_called_once()

    async def test_get_failed_download_attempts_empty_result(self, failed_downloads_repository, mock_pool):
        """Test getting failed download attempts when none exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetch.return_value = []

        # Act
        result = await failed_downloads_repository.get_failed_download_attempts()

        # Assert
        assert len(result) == 0
        connection.fetch.assert_called_once()

    async def test_transaction_rollback_on_record_failed_download_error(self, failed_downloads_repository, mock_pool):
        """Test that transaction is properly handled on error during record_failed_download."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.side_effect = Exception("Database error")

        attempt_data = create_failed_download_attempt_data()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await failed_downloads_repository.record_failed_download(attempt_data)

        assert "Database error" in str(exc_info.value)

    async def test_delete_failed_download_attempt_by_link_success(self, failed_downloads_repository, mock_pool):
        """Test deleting a failed download attempt by link when it exists."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 1"
        test_link = "https://example.com/image.jpg"

        # Act
        result = await failed_downloads_repository.delete_failed_download_attempt_by_link(test_link)

        # Assert
        assert result is True
        connection.execute.assert_called_once()

    async def test_delete_failed_download_attempt_by_link_not_found(self, failed_downloads_repository, mock_pool):
        """Test deleting a failed download attempt by link when it doesn't exist."""
        # Arrange
        connection = mock_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 0"
        test_link = "https://example.com/nonexistent.jpg"

        # Act
        result = await failed_downloads_repository.delete_failed_download_attempt_by_link(test_link)

        # Assert
        assert result is False
        connection.execute.assert_called_once()
