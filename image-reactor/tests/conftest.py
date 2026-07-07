"""Pytest configuration and shared fixtures."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.internal.config import Settings

# Mock get_settings at module import time to prevent validation errors during test collection
# This must be done before app.main is imported by any test module
_mock_settings = Settings(
    database_url="postgresql://mock:mock@localhost/mock",
    verbose_api_exceptions=False,
)

# Start patching get_settings globally to handle imports during test collection
_settings_patcher = patch("app.internal.config.get_settings", return_value=_mock_settings)
_settings_patcher.start()


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture
def mock_db():
    """Create a mock database instance for unit tests."""
    mock = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock application settings globally for all tests."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.verbose_api_exceptions = False

    with patch("app.internal.exception_handler.get_settings", return_value=mock_settings):
        yield mock_settings
