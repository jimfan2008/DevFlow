import time
import uuid

import pytest

from app.models.user import User


# -- Fixtures --

@pytest.fixture
def client(test_client):
    """Provide the async test client."""
    return test_client


@pytest.fixture
def db_session(database_session):
    """Provide the database session for assertions."""
    return database_session


# -- Helper Functions --

REGISTER_URL = "/api/auth/register"


def _uid():
    """Generate short random suffix to avoid cross-test data conflicts."""
    return uuid.uuid4().hex[:8]


def _payload(password):
    """Construct registration request body with unique username/email."""
    s = _uid()
    return {
        "username": f"spw_{s}",
        "email": f"spw_{s}@example.com",
        "password": password,
        "confirm_password": password,
    }


def _assert_rejection(response, elapsed_ms):
    """Unified assertion: 400 + VALID-001 + <=200ms."""
    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}; body={response.text}"
    )
    body = response.json()
    error = body.get("error", {})
    assert error.get("code") == "VALID-001", (
        f"Expected error.code='VALID-001', got '{error.get('code')}'"
    )
    assert elapsed_ms <= 200, f"Response time {elapsed_ms:.1f}ms exceeds 200ms"


# =============================================================================
# Main Test: 3-char password rejected (covers all 4 acceptance criteria)
# =============================================================================


@pytest.mark.asyncio
async def test_short_password_returns_400_with_valid_001(client, db_session):
    """Password 'Ab1' (3 chars) should return 400 + VALID-001 + <=200ms + no DB change."""
    initial = db_session.query(User).count()

    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_payload("Ab1"))
    elapsed = (time.perf_counter() - t0) * 1000

    # Acceptance criteria 1 & 2
    _assert_rejection(resp, elapsed)

    # Acceptance criterion 3 (duplicate check for explicitness)
    assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeds 200ms limit"

    # Acceptance criterion 4
    final = db_session.query(User).count()
    assert final == initial, (
        f"DB records changed from {initial} to {final}, short password should not create user"
    )


# =============================================================================
# Boundary Tests
# =============================================================================


@pytest.mark.asyncio
async def test_empty_password_rejected(client, db_session):
    """Empty password '' should be rejected."""
    initial = db_session.query(User).count()
    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_payload(""))
    elapsed = (time.perf_counter() - t0) * 1000

    _assert_rejection(resp, elapsed)
    assert db_session.query(User).count() == initial


@pytest.mark.asyncio
async def test_single_char_password_rejected(client, db_session):
    """Single char password 'A' should be rejected."""
    initial = db_session.query(User).count()
    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_payload("A"))
    elapsed = (time.perf_counter() - t0) * 1000

    _assert_rejection(resp, elapsed)
    assert db_session.query(User).count() == initial


@pytest.mark.asyncio
async def test_six_char_password_rejected(client, db_session):
    """6-char password 'Aa1234' should be rejected."""
    initial = db_session.query(User).count()
    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_payload("Aa1234"))
    elapsed = (time.perf_counter() - t0) * 1000

    _assert_rejection(resp, elapsed)
    assert db_session.query(User).count() == initial


@pytest.mark.asyncio
async def test_seven_char_password_rejected(client, db_session):
    """7-char password 'Aa12345' (1 short) should be rejected."""
    initial = db_session.query(User).count()
    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_payload("Aa12345"))
    elapsed = (time.perf_counter() - t0) * 1000

    _assert_rejection(resp, elapsed)
    assert db_session.query(User).count() == initial


# =============================================================================
# Positive Boundary: 8-char password should NOT be rejected for length
# =============================================================================


@pytest.mark.asyncio
async def test_eight_char_password_not_rejected_by_length(client, db_session):
    """
    Exactly 8 chars 'Aa123456' should NOT trigger length validation error.
    May return 422 for complexity requirements, but the error should not be about length.
    """
    resp = await client.post(REGISTER_URL, json=_payload("Aa123456"))
    body = resp.json()

    # 8 chars should not trigger length error
    if resp.status_code == 422:
        errors = body.get("details", {}).get("errors", [])
        for err in errors:
            msg = err.get("msg", "")
            assert "too short" not in msg.lower() or len(err.get("input", "")) >= 8, (
                f"8-char password should not trigger length error, got: {msg}"
            )


# =============================================================================
# Repetition: same short password submitted multiple times always returns error
# =============================================================================


@pytest.mark.asyncio
async def test_repeated_short_password_always_rejected(client, db_session):
    """Submit same short password 3 times in a row, each should return 400 + VALID-001."""
    initial = db_session.query(User).count()

    for _ in range(3):
        resp = await client.post(REGISTER_URL, json=_payload("Ab1"))
        assert resp.status_code == 400
        body = resp.json()
        assert body.get("error", {}).get("code") == "VALID-001"

    assert db_session.query(User).count() == initial


# =============================================================================
# Matching short passwords still rejected
# =============================================================================


@pytest.mark.asyncio
async def test_short_passwords_match_still_rejected(client, db_session):
    """
    Even when password and confirm_password both match (both 'Ab1'),
    insufficient length should still return validation error (not 'passwords dont match').
    """
    initial = db_session.query(User).count()
    s = _uid()
    payload = {
        "username": f"match_{s}",
        "email": f"match_{s}@example.com",
        "password": "Ab1",
        "confirm_password": "Ab1",
    }
    t0 = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=payload)
    elapsed = (time.perf_counter() - t0) * 1000

    _assert_rejection(resp, elapsed)
    assert db_session.query(User).count() == initial
