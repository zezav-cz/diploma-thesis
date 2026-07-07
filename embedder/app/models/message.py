"""Kafka message models."""

from pydantic import BaseModel, Field, HttpUrl


class UploadSuccessMessage(BaseModel):
    """Message received when an image upload is successful."""

    database_id: str
    item_id: int | None = None
    property_name: str
    image_number: int | None = None
    storage_collection: str
    storage_path: str
    original_url: HttpUrl
    width: int
    height: int
    extension: str
    hashsum: str = Field(alias="hashsum")
    uploaded_at: str
