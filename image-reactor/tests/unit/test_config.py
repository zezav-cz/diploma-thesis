"""Unit tests for configuration management."""

import os
from ipaddress import IPv4Address
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.internal.config import ENV_PREFIX, Settings, get_settings

_database_url_dict = {
    f"{ENV_PREFIX}DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/test_db",
}


@pytest.mark.unit
class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self):
        """Test that Settings loads with default values when only DATABASE_URL is provided."""
        with patch.dict(os.environ, _database_url_dict, clear=True):
            settings = Settings(_env_file=None)
            assert "test_db" in str(settings.database_url)
            assert settings.db_pool_min_size == 10
            assert settings.db_pool_max_size == 20
            assert settings.db_pool_max_queries == 50000
            assert settings.db_pool_max_inactive_connection_lifetime == 300.0
            assert settings.log_level == "INFO"
            assert settings.log_format == "JSON"
            assert settings.host == IPv4Address("0.0.0.0")  # noqa: S104
            assert settings.port == 8000
            assert settings.verbose_api_exceptions is False
            assert settings.expose_metrics is True

    def test_database_url_missing(self):
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError) as _:
            Settings(_env_file=None)

    def test_settings_from_environment(self):
        """Test that Settings loads from environment variables."""
        with patch.dict(
            os.environ,
            {
                f"{ENV_PREFIX}DATABASE_URL": "postgresql://user:pass@testhost:5433/testdb",
                f"{ENV_PREFIX}DB_POOL_MIN_SIZE": "5",
                f"{ENV_PREFIX}DB_POOL_MAX_SIZE": "15",
                f"{ENV_PREFIX}LOG_LEVEL": "DEBUG",
                f"{ENV_PREFIX}LOG_FORMAT": "TXT",
                f"{ENV_PREFIX}HOST": "127.0.0.1",
                f"{ENV_PREFIX}PORT": "9000",
                f"{ENV_PREFIX}VERBOSE_API_EXCEPTIONS": "true",
                f"{ENV_PREFIX}DB_POOL_MAX_QUERIES": "100000",
                f"{ENV_PREFIX}DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME": "600.5",
                f"{ENV_PREFIX}EXPOSE_METRICS": "false",
            },
            clear=True,
        ):
            settings = Settings(_env_file=None)
            assert "user:pass@testhost:5433/testdb" in str(settings.database_url)
            assert settings.db_pool_min_size == 5
            assert settings.db_pool_max_size == 15
            assert settings.log_level == "DEBUG"
            assert settings.log_format == "TXT"
            assert settings.host == IPv4Address("127.0.0.1")
            assert settings.port == 9000
            assert settings.verbose_api_exceptions is True
            assert settings.db_pool_max_queries == 100000
            assert settings.db_pool_max_inactive_connection_lifetime == 600.5
            assert settings.expose_metrics is False


@pytest.mark.unit
@patch.dict(os.environ, _database_url_dict, clear=True)
class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        """Test that get_settings returns the same instance (cached)."""
        # Clear the cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance due to lru_cache
        assert settings1 is settings2

    def test_get_settings_cache_can_be_cleared(self):
        """Test that cache can be cleared."""
        get_settings.cache_clear()

        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()

        # After clearing cache, might get different instance
        # (depends on timing, but cache_clear should work without error)
        assert isinstance(settings1, Settings)
        assert isinstance(settings2, Settings)
