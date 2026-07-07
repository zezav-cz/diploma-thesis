"""Pydantic models for database entities."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PropertyMetadata(BaseModel):
    """Model for property metadata associated with an image."""

    database_id: str | None = Field(default=None, max_length=80, description="External database identifier")
    item_id: int | None = Field(default=None, description="External item identifier")
    property_name: str | None = Field(default=None, description="Name of the property")
    image_number: int | None = Field(default=None, description="Image number within the property")


class ImageCreate(PropertyMetadata):
    """Model for creating a new image record."""

    link: str = Field(description="Image URL")
    store_collection: str = Field(max_length=256, description="Storage collection name")
    filepath: str = Field(description="Local file path")
    hashsum: str = Field(description="File hash (hex string)")
    extension: str = Field(max_length=32, description="File extension")
    width: int = Field(description="Image width in pixels", gt=0)
    height: int = Field(description="Image height in pixels", gt=0)


class Image(ImageCreate):
    """Complete image model with database fields."""

    id: int
    stored_at: datetime | None = Field(default=None, description="Storage timestamp")

    model_config = ConfigDict(from_attributes=True)


class FailedDownloadAttemptCreate(PropertyMetadata):
    """Model for creating failed download attempt record."""

    attempt_status: str = Field(default="failed", description="Status of the attempt")
    error_message: str | None = Field(default=None, description="Error message if failed")
    http_status: int | None = Field(default=None, description="HTTP status code", gt=100, lt=600)
    link: str = Field(description="Image URL that was attempted", min_length=1)


class FailedDownloadAttempt(FailedDownloadAttemptCreate):
    """Complete failed download attempt model."""

    id: int
    attempted_at: datetime
    tries: int = Field(description="Number of download attempts")

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status: healthy or unhealthy")
    database: str = Field(description="Database status: connected or disconnected")
    timestamp: datetime = Field(description="Health check timestamp")
