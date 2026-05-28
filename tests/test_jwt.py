"""Tests for JWT authentication utilities."""

import pytest
from jose import jwt as jose_jwt

from app.jwt import create_access_token, verify_access_token
from app.config import get_settings


def test_create_access_token() -> None:
    """Test JWT token creation."""
    payload = {"sub": "test_user", "role": "admin"}
    token = create_access_token(payload)

    # Verify token is a valid JWT
    settings = get_settings()
    decoded = jose_jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_token_verification() -> None:
    """Test token verification."""
    payload = {"sub": "test_user"}
    token = create_access_token(payload)
    verified = verify_access_token(token)

    assert verified is not None
    assert verified["sub"] == "test_user"


def test_invalid_token() -> None:
    """Test verification of invalid token."""
    invalid_token = "invalid.token.here"
    result = verify_access_token(invalid_token)

    assert result is None


def test_expired_token() -> None:
    """Test verification of expired token."""
    # Create a token that already expired
    payload = {"sub": "test_user", "exp": 0}  # Expired at epoch
    token = create_access_token(payload, expires_minutes=-1)
    result = verify_access_token(token)

    assert result is None


def test_token_expiry() -> None:
    """Test custom token expiration."""
    payload = {"sub": "test_user"}
    token = create_access_token(payload, expires_minutes=5)
    decoded = verify_access_token(token)

    assert decoded is not None
    assert decoded["exp"] is not None
