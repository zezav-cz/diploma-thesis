"""Unit tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.http import health


@pytest.fixture
def app():
    """Create a FastAPI app for testing without lifespan events."""
    app = FastAPI()
    app.include_router(health.router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    mock = AsyncMock()
    mock.health_check = AsyncMock()
    return mock


@pytest.mark.api
@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_healthy(self, client, mock_db):
        """Test health check when database is connected."""
        mock_db.health_check.return_value = True

        with patch("app.routers.http.health.get_database", return_value=mock_db):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        mock_db.health_check.assert_called_once()

    def test_health_check_unhealthy(self, client, mock_db):
        """Test health check when database is disconnected."""
        mock_db.health_check.return_value = False

        with patch("app.routers.http.health.get_database", return_value=mock_db):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "timestamp" in data
        mock_db.health_check.assert_called_once()


@pytest.mark.api
@pytest.mark.unit
class TestReadinessEndpoint:
    """Tests for /health/ready endpoint."""

    def test_readiness_check_ready(self, client, mock_db):
        """Test readiness check when service is ready."""
        mock_db.health_check.return_value = True

        with patch("app.routers.http.health.get_database", return_value=mock_db):
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ready"}
        mock_db.health_check.assert_called_once()

    def test_readiness_check_not_ready(self, client, mock_db):
        """Test readiness check when database is unavailable."""
        mock_db.health_check.return_value = False

        with patch("app.routers.http.health.get_database", return_value=mock_db):
            response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data == {"status": "not_ready", "reason": "database_unavailable"}
        mock_db.health_check.assert_called_once()


@pytest.mark.api
@pytest.mark.unit
class TestLivenessEndpoint:
    """Tests for /health/live endpoint."""

    def test_liveness_check(self, client):
        """Test liveness check always returns alive."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "alive"}


@pytest.mark.api
@pytest.mark.unit
class TestHealthEndpointsIntegration:
    """Integration tests for all health endpoints."""

    def test_all_health_endpoints_exist(self, client):
        """Test that all health endpoints are accessible."""
        endpoints = ["/health", "/health/ready", "/health/live"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not return 404
            assert response.status_code != 404
