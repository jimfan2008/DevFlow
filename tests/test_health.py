"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint returns application info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "DevFlow"
    assert data["status"] == "running"


def test_openapi_endpoint(client: TestClient) -> None:
    """Test OpenAPI schema endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "info" in response.json()


def test_docs_available(client: TestClient) -> None:
    """Test that documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
