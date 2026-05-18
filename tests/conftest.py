"""Pytest configuration."""

import pytest


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-testing-only")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
