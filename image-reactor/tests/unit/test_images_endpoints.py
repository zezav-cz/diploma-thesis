"""Unit tests for images API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.http.v1 import images
from tests.fixtures.factories import create_image, create_image_data


@pytest.fixture
def app():
    """Create a FastAPI app for testing without lifespan events."""
    app = FastAPI()
    app.include_router(images.router, prefix="/v1")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_image_repository():
    """Create a mock image repository."""
    mock = AsyncMock()
    mock.create_image = AsyncMock()
    mock.get_image_by_id = AsyncMock()
    mock.get_image_by_path = AsyncMock()
    mock.delete_image = AsyncMock()
    return mock


@pytest.fixture
def mock_attempts_repository():
    """Create a mock failed download attempts repository."""
    mock = AsyncMock()
    mock.delete_failed_download_attempt_by_link = AsyncMock()
    return mock


@pytest.mark.api
@pytest.mark.unit
class TestCreateImageEndpoint:
    """Tests for POST /v1/images endpoint."""

    def test_create_image_success(self, client, mock_image_repository, mock_attempts_repository):
        """Test successful image creation."""
        # Prepare test data
        image_data = create_image_data(
            link="https://example.com/test.jpg",
            store_collection="test-collection",
            filepath="/images/test.jpg",
            extension="jpg",
            width=1920,
            height=1080,
        )
        created_image = create_image(
            id=1,
            stored_at=datetime.now(),
            **image_data.model_dump(),
        )
        mock_image_repository.create_image.return_value = created_image
        mock_attempts_repository.delete_failed_download_attempt_by_link.return_value = True

        # Make request
        with (
            patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository),
            patch("app.routers.http.v1.images.get_repository_attempts", return_value=mock_attempts_repository),
        ):
            response = client.post(
                "/v1/images",
                json={
                    "link": image_data.link,
                    "store_collection": image_data.store_collection,
                    "filepath": image_data.filepath,
                    "hashsum": image_data.hashsum,
                    "extension": image_data.extension,
                    "width": image_data.width,
                    "height": image_data.height,
                },
            )

        # Assert response
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == created_image.id
        assert data["link"] == created_image.link
        assert data["store_collection"] == created_image.store_collection
        assert data["filepath"] == created_image.filepath
        assert data["extension"] == created_image.extension
        assert data["width"] == created_image.width
        assert data["height"] == created_image.height
        assert data["stored_at"] == created_image.stored_at.isoformat()
        assert data["hashsum"] == created_image.hashsum
        mock_image_repository.create_image.assert_called_once()
        mock_attempts_repository.delete_failed_download_attempt_by_link.assert_called_once_with(image_data.link)

    def test_create_image_validation_error(self, client):
        """Test image creation with invalid data."""
        # Missing required fields
        response = client.post(
            "/v1/images",
            json={
                "link": "https://example.com/test.jpg",
                # Missing other required fields
            },
        )

        assert response.status_code == 422  # Validation error

    def test_create_image_invalid_width(self, client):
        """Test image creation with invalid width."""
        image_data = create_image_data()

        response = client.post(
            "/v1/images",
            json={
                "link": image_data.link,
                "store_collection": image_data.store_collection,
                "filepath": image_data.filepath,
                "hashsum": image_data.hashsum,
                "extension": image_data.extension,
                "width": 0,  # Invalid: must be > 0
                "height": image_data.height,
            },
        )

        assert response.status_code == 422

    def test_create_image_database_error(self, client, mock_image_repository, mock_attempts_repository):
        """Test image creation when database error occurs."""
        image_data = create_image_data()
        mock_image_repository.create_image.side_effect = Exception("Database error")

        with (
            patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository),
            patch("app.routers.http.v1.images.get_repository_attempts", return_value=mock_attempts_repository),
        ):
            response = client.post(
                "/v1/images",
                json={
                    "link": image_data.link,
                    "store_collection": image_data.store_collection,
                    "filepath": image_data.filepath,
                    "hashsum": image_data.hashsum,
                    "extension": image_data.extension,
                    "width": image_data.width,
                    "height": image_data.height,
                },
            )

        # Assert status code is 500 Internal Server Error
        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestGetImageByIdEndpoint:
    """Tests for GET /v1/images/{image_id} endpoint."""

    def test_get_image_by_id_success(self, client, mock_image_repository):
        """Test successful retrieval of image by ID."""
        image = create_image(id=42)
        mock_image_repository.get_image_by_id.return_value = image

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get("/v1/images/42")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        mock_image_repository.get_image_by_id.assert_called_once_with(42)

    def test_get_image_by_id_not_found(self, client, mock_image_repository):
        """Test retrieval when image doesn't exist."""
        mock_image_repository.get_image_by_id.return_value = None

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get("/v1/images/999")

        assert response.status_code == 404
        response.json()
        mock_image_repository.get_image_by_id.assert_called_once_with(999)

    def test_get_image_by_id_invalid_id(self, client):
        """Test retrieval with invalid ID format."""
        response = client.get("/v1/images/invalid")

        assert response.status_code == 422  # Validation error

    def test_get_image_by_id_database_error(self, client, mock_image_repository):
        """Test retrieval when database error occurs."""
        mock_image_repository.get_image_by_id.side_effect = Exception("Database connection lost")

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get("/v1/images/1")

        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestGetImageByPathEndpoint:
    """Tests for GET /v1/images/by-path endpoint."""

    def test_get_image_by_path_success(self, client, mock_image_repository):
        """Test successful retrieval of image by path."""
        image = create_image(store_collection="test-collection", filepath="/images/test.jpg")
        mock_image_repository.get_image_by_path.return_value = image

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get(
                "/v1/images/by-path",
                params={
                    "store_collection": "test-collection",
                    "filepath": "/images/test.jpg",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["store_collection"] == "test-collection"
        assert data["filepath"] == "/images/test.jpg"
        mock_image_repository.get_image_by_path.assert_called_once_with("test-collection", "/images/test.jpg")

    def test_get_image_by_path_not_found(self, client, mock_image_repository):
        """Test retrieval when image doesn't exist at path."""
        mock_image_repository.get_image_by_path.return_value = None

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get(
                "/v1/images/by-path",
                params={
                    "store_collection": "nonexistent",
                    "filepath": "/missing.jpg",
                },
            )

        assert response.status_code == 404
        response.json()
        mock_image_repository.get_image_by_path.assert_called_once_with("nonexistent", "/missing.jpg")

    def test_get_image_by_path_missing_params(self, client):
        """Test retrieval with missing query parameters."""
        # Missing both parameters
        response = client.get("/v1/images/by-path")
        assert response.status_code == 422

        response = client.get("/v1/images/by-path", params={"store_collection": "test"})
        assert response.status_code == 422

        response = client.get("/v1/images/by-path", params={"filepath": "/test.jpg"})
        assert response.status_code == 422

    def test_get_image_by_path_database_error(self, client, mock_image_repository):
        """Test retrieval when database error occurs."""
        mock_image_repository.get_image_by_path.side_effect = Exception("Query timeout")

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.get(
                "/v1/images/by-path",
                params={
                    "store_collection": "test",
                    "filepath": "/test.jpg",
                },
            )

        assert response.status_code == 500
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestDeleteImageEndpoint:
    """Tests for DELETE /v1/images/{image_id} endpoint."""

    def test_delete_image_success(self, client, mock_image_repository):
        """Test successful image deletion."""
        mock_image_repository.delete_image.return_value = True

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.delete("/v1/images/1")

        assert response.status_code == 200
        assert response.content == b"{}"
        mock_image_repository.delete_image.assert_called_once_with(1)

    def test_delete_image_not_found(self, client, mock_image_repository):
        """Test deletion when image doesn't exist."""
        mock_image_repository.delete_image.return_value = False

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.delete("/v1/images/999")

        assert response.status_code == 404
        response.json()
        mock_image_repository.delete_image.assert_called_once_with(999)

    def test_delete_image_invalid_id(self, client):
        """Test deletion with invalid ID format."""
        response = client.delete("/v1/images/invalid")
        assert response.status_code == 422

    def test_delete_image_database_error(self, client, mock_image_repository):
        """Test deletion when database error occurs."""
        mock_image_repository.delete_image.side_effect = Exception("Constraint violation")

        with patch("app.routers.http.v1.images.get_repository_images", return_value=mock_image_repository):
            response = client.delete("/v1/images/1")

        assert response.status_code == 500
        # Assert response is valid JSON
        response.json()


@pytest.mark.api
@pytest.mark.unit
class TestImagesEndpointsIntegration:
    """Integration tests for all images endpoints."""

    def test_all_images_endpoints_exist(self, client):
        """Test that all images endpoints are accessible."""
        # Note: These will fail with various errors but should not return 404
        endpoints_methods = [
            ("POST", "/v1/images"),
            ("GET", "/v1/images/1"),
            ("GET", "/v1/images/by-path"),
            ("DELETE", "/v1/images/1"),
        ]

        for method, endpoint in endpoints_methods:
            if method == "POST":
                response = client.post(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            else:
                response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404, f"{method} {endpoint} returned 404"
