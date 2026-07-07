"""Unit tests for failed downloads attempts API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.models import FailedDownloadAttemptCreate
from app.routers.http.v1 import failed_downloads_attempts
from tests.fixtures.factories import create_failed_download_attempt


@pytest.fixture
def app():
    """Create a FastAPI app for testing without lifespan events."""
    app = FastAPI()
    app.include_router(failed_downloads_attempts.router, prefix="/v1")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_repository():
    """Create a mock failed downloads attempts repository."""
    mock = AsyncMock()
    mock.record_failed_download = AsyncMock()
    mock.get_failed_download_attempt_by_id = AsyncMock()
    mock.get_failed_download_attempts_by_image_id = AsyncMock()
    mock.get_failed_download_attempts = AsyncMock()
    return mock


@pytest.mark.api
@pytest.mark.unit
class TestRecordFailedDownloadEndpoint:
    """Tests for POST /v1/failed-downloads-attempts/fail endpoint."""

    def test_record_failed_download_success(self, client, mock_repository):
        """Test successful failed download recording."""
        # Prepare test data
        request_data = {
            "link": "https://example.com/test.jpg",
            "error_message": "Connection timeout",
            "http_status": 408,
        }
        created_attempt = create_failed_download_attempt(
            id=1,
            image_id=10,
            image_link=request_data["link"],
            error_message=request_data["error_message"],
            http_status=request_data["http_status"],
            attempted_at=datetime.now(),
        )
        mock_repository.record_failed_download.return_value = created_attempt

        # Make request
        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.post(
                "/v1/failed-downloads-attempts/fail",
                json=request_data,
            )

        # Assert response
        assert response.status_code == 201
        response.json()
        # Verify the repository was called with a FailedDownloadAttemptCreate object
        call_args = mock_repository.record_failed_download.call_args[0][0]
        assert isinstance(call_args, FailedDownloadAttemptCreate)
        assert call_args.link == request_data["link"]
        assert call_args.error_message == request_data["error_message"]
        assert call_args.http_status == request_data["http_status"]
        assert call_args.attempt_status == "failed"

    def test_record_failed_download_validation_error(self, client):
        """Test failed download recording with invalid data."""
        # Missing required fields
        response = client.post(
            "/v1/failed-downloads-attempts/fail",
            json={
                # Missing link
                "error_message": "Connection timeout",
            },
        )

        assert response.status_code == 422  # Validation error
        response.json()

    def test_record_failed_download_empty_link(self, client):
        """Test failed download recording with empty link."""
        response = client.post(
            "/v1/failed-downloads-attempts/fail",
            json={
                "link": "",
                "error_message": "Some error",
            },
        )

        assert response.status_code == 422

    def test_record_failed_download_database_error(self, client, mock_repository):
        """Test failed download recording when database error occurs."""
        request_data = {
            "link": "https://example.com/test.jpg",
            "error_message": "Connection timeout",
            "http_status": 408,
        }
        mock_repository.record_failed_download.side_effect = Exception("Database error")

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.post(
                "/v1/failed-downloads-attempts/fail",
                json=request_data,
            )

        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestGetFailedDownloadAttemptEndpoint:
    """Tests for GET /v1/failed-downloads-attempts/{attempt_id} endpoint."""

    def test_get_failed_download_attempt_success(self, client, mock_repository):
        """Test successful retrieval of failed download attempt by ID."""
        attempt = create_failed_download_attempt(id=42)
        mock_repository.get_failed_download_attempt_by_id.return_value = attempt

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/42")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        mock_repository.get_failed_download_attempt_by_id.assert_called_once_with(42)

    def test_get_failed_download_attempt_not_found(self, client, mock_repository):
        """Test retrieval when failed download attempt doesn't exist."""
        mock_repository.get_failed_download_attempt_by_id.return_value = None

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/999")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        mock_repository.get_failed_download_attempt_by_id.assert_called_once_with(999)

    def test_get_failed_download_attempt_invalid_id(self, client):
        """Test retrieval with invalid ID format."""
        response = client.get("/v1/failed-downloads-attempts/invalid")

        assert response.status_code == 422  # Validation error

    def test_get_failed_download_attempt_database_error(self, client, mock_repository):
        """Test retrieval when database error occurs."""
        mock_repository.get_failed_download_attempt_by_id.side_effect = Exception("Database connection lost")

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/1")

        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestListFailedDownloadAttemptsEndpoint:
    """Tests for GET /v1/failed-downloads-attempts/failed endpoint."""

    def test_list_failed_download_attempts_default_params(self, client, mock_repository):
        """Test listing failed download attempts with default parameters."""
        attempts = [
            create_failed_download_attempt(id=1),
            create_failed_download_attempt(id=2),
        ]
        mock_repository.get_failed_download_attempts.return_value = attempts

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/failed")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_repository.get_failed_download_attempts.assert_called_once_with(None, None, 100, 0)

    def test_list_failed_download_attempts_with_pagination(self, client, mock_repository):
        """Test listing with custom limit and offset."""
        attempts = [create_failed_download_attempt(id=i) for i in range(10)]
        mock_repository.get_failed_download_attempts.return_value = attempts

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get(
                "/v1/failed-downloads-attempts/failed",
                params={"limit": 10, "offset": 20},
            )

        assert response.status_code == 200
        response.json()
        mock_repository.get_failed_download_attempts.assert_called_once_with(None, None, 10, 20)

    def test_list_failed_download_attempts_with_date_range(self, client, mock_repository):
        """Test listing with date range filter."""
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()
        attempts = [create_failed_download_attempt(id=1)]
        mock_repository.get_failed_download_attempts.return_value = attempts

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get(
                "/v1/failed-downloads-attempts/failed",
                params={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verify the repository was called with ISO formatted dates
        call_args = mock_repository.get_failed_download_attempts.call_args[0]
        assert call_args[0] == from_date.isoformat()
        assert call_args[1] == to_date.isoformat()

    def test_list_failed_download_attempts_invalid_date_range(self, client):
        """Test listing with from_date > to_date."""
        from_date = datetime.now()
        to_date = datetime.now() - timedelta(days=7)

        response = client.get(
            "/v1/failed-downloads-attempts/failed",
            params={
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
            },
        )

        assert response.status_code == 400
        response.json()

    def test_list_failed_download_attempts_limit_validation(self, client):
        """Test listing with invalid limit values."""
        # Limit too small
        response = client.get(
            "/v1/failed-downloads-attempts/failed",
            params={"limit": 0},
        )
        assert response.status_code == 422

        # Limit too large
        response = client.get(
            "/v1/failed-downloads-attempts/failed",
            params={"limit": 1001},
        )
        assert response.status_code == 422

    def test_list_failed_download_attempts_offset_validation(self, client):
        """Test listing with invalid offset value."""
        response = client.get(
            "/v1/failed-downloads-attempts/failed",
            params={"offset": -1},
        )
        assert response.status_code == 422

    def test_list_failed_download_attempts_empty_result(self, client, mock_repository):
        """Test listing when no attempts exist."""
        mock_repository.get_failed_download_attempts.return_value = []

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/failed")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_failed_download_attempts_database_error(self, client, mock_repository):
        """Test listing when database error occurs."""
        mock_repository.get_failed_download_attempts.side_effect = Exception("Connection lost")

        with patch("app.routers.http.v1.failed_downloads_attempts.get_repository", return_value=mock_repository):
            response = client.get("/v1/failed-downloads-attempts/failed")

        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestFailedDownloadsAttemptsEndpointsIntegration:
    """Integration tests for all failed downloads attempts endpoints."""

    def test_all_failed_downloads_attempts_endpoints_exist(self, client):
        """Test that all failed downloads attempts endpoints are accessible."""
        # Note: These will fail with various errors but should not return 404
        endpoints_methods = [
            ("POST", "/v1/failed-downloads-attempts/fail"),
            ("GET", "/v1/failed-downloads-attempts/1"),
            ("GET", "/v1/failed-downloads-attempts/failed"),
        ]

        for method, endpoint in endpoints_methods:
            response = client.post(endpoint, json={}) if method == "POST" else client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404, f"{method} {endpoint} returned 404"
