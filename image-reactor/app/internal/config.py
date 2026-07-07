"""Application configuration management."""

from enum import Enum
from functools import lru_cache

from pydantic import Field, IPvAnyAddress, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "IR_"


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

    # Database configuration
    database_url: PostgresDsn = Field(
        description="PostgreSQL database connection URL",
    )

    # Database pool configuration
    db_pool_min_size: int = Field(default=10, description="Minimum connection pool size", gt=0)
    db_pool_max_size: int = Field(default=20, description="Maximum connection pool size", gt=0)
    db_pool_max_queries: int = Field(
        default=50000,
        description="Number of queries after which a connection is closed",
        gt=0,
    )
    db_pool_max_inactive_connection_lifetime: float = Field(
        default=300.0,
        description="Maximum time in seconds a connection can remain idle",
        gt=0,
    )

    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, description=f'Logging level ({", ".join([e.value for e in LogLevel])})')
    log_format: LogFormat = Field(default=LogFormat.JSON, description=f'Log format ({", ".join([e.value for e in LogFormat])})')

    # Server configuration
    host: IPvAnyAddress = Field(default="0.0.0.0", description="Server host")  # noqa: S104
    port: int = Field(default=8000, description="Server port", gt=0, lt=65536)

    # Exception handling configuration
    verbose_api_exceptions: bool = Field(
        default=False,
        description="If True, return detailed internal exceptions in API responses. If False, only log them and return a generic error message.",
    )

    # Metrics configuration
    expose_metrics: bool = Field(
        default=True,
        description="If True, expose Prometheus metrics at /metrics endpoint",
    )

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=False,
        case_sensitive=False,
    )

    debug: bool = Field(  # TODO add to tests
        default=False,
        description="Enable debug mode with more verbose logging and error messages",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
