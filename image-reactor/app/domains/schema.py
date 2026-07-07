"""Database schema constants for table and column names."""


class ImagesTable:
    """Schema for images table."""

    TABLE = "images"

    # Column names
    ID = "id"
    LINK = "link"
    STORE_COLLECTION = "store_collection"
    FILEPATH = "filepath"
    DATABASE_ID = "database_id"
    ITEM_ID = "item_id"
    PROPERTY_NAME = "property_name"
    IMAGE_NUMBER = "image_number"
    HASHSUM = "hashsum"
    EXTENSION = "extension"
    WIDTH = "width"
    HEIGHT = "height"
    STORED_AT = "stored_at"


class FailedDownloadsAttemptsTable:
    """Schema for failed_downloads_attempts table."""

    TABLE = "failed_download_attempts"

    # Column names
    ID = "id"
    DATABASE_ID = "database_id"
    ITEM_ID = "item_id"
    PROPERTY_NAME = "property_name"
    IMAGE_NUMBER = "image_number"
    ATTEMPTED_AT = "attempted_at"
    ATTEMPT_STATUS = "attempt_status"
    ERROR_MESSAGE = "error_message"
    HTTP_STATUS = "http_status"
    LINK = "link"
    TRIES = "tries"

    # Joined columns (aliases)
    IMAGE_LINK = "image_link"


class Schema:
    """Centralized database schema."""

    images = ImagesTable
    failed_downloads_attempts = FailedDownloadsAttemptsTable
