"""Application configuration management."""

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    JSON = "JSON"
    TXT = "TXT"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Logging configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description=f"Logging level ({', '.join([e.value for e in LogLevel])})",
    )
    log_format: LogFormat = Field(
        default=LogFormat.JSON,
        description=f"Log format ({', '.join([e.value for e in LogFormat])})",
    )

    kafka_brokers: str = Field(
        description="Comma-separated list of Kafka broker addresses"
    )
    kafka_topic: str = Field(
        default="embeder", description="Kafka topic to publish messages to"
    )
    kafka_consumer_group: str = Field(
        default="embeder-group", description="Kafka consumer group ID"
    )

    output_file: str = Field(
        default="/tmp/image_hashes.txt", description="File to write image hashes to"
    )
    http_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    seaweedfs_address: str = Field(
        description="Base address for SeaweedFS storage (e.g., http://localhost:8080)"
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=False,
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
