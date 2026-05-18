"""Tests for application configuration."""

import os
from unittest.mock import patch

import pytest

from app.config import get_settings, Settings


def test_settings_load_from_env() -> None:
    """Test settings are loaded from environment variables."""
    settings = Settings()

    assert settings.app_name == "DevFlow"
    assert settings.jwt_algorithm == "HS256"
    assert settings.db_pool_size == 10
    assert settings.database_url is not None


def test_settings_debug_mode() -> None:
    """Test debug mode property."""
    settings = Settings()
    assert isinstance(settings.is_debug, bool)


def test_settings_override_env() -> None:
    """Test that environment variables can override defaults."""
    with patch.dict(os.environ, {"APP_DEBUG": "true", "APP_PORT": "9000"}):
        # Clear cache to reload settings
        get_settings.cache_clear()
        settings = Settings()

        assert settings.app_debug is True
        assert settings.app_port == 9000


def test_settings_property() -> None:
    """Test that config properties work correctly."""
    settings = Settings()

    # Test is_debug property
    assert settings.is_debug == settings.app_debug

    # Test db_url property
    assert settings.database_url == settings.database_url
