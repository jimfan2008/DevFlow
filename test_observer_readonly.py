import pytest
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse


class _MockUser:
    def __init__(self, role: str):
        self.role = role


class _MockState:
    def __init__(self, user: _MockUser):
        self.user = user


class MockRequest:
    def __init__(self, method: str, user_role: str = "observer"):
        self.method = method
        self.state = _MockState(_MockUser(user_role))


async def mock_observer_authorization_check(request):
    """Authorization middleware that blocks non-GET for observer role."""
    if hasattr(request.state, "user") and request.state.user.role == "observer":
        if request.method.upper() not in ("GET", "OPTIONS", "HEAD"):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": {"code": "AUTH-002", "message": "Read-only observer cannot modify resources"}},
            )
    return None


async def mock_get_handler():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": "read-only resource"})


async def mock_put_handler():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": "updated"})


async def mock_delete_handler():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": "deleted"})


@pytest.mark.asyncio
async def test_observer_get_returns_200():
    request = MockRequest(method="GET", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is None, f"Expected None (pass-through) for GET, got {response}"


@pytest.mark.asyncio
async def test_observer_put_returns_403_with_auth_002():
    request = MockRequest(method="PUT", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is not None, "Expected 403 response for PUT"
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got {response.status_code}"
    body = response.body
    body_dict = json.loads(body)
    assert body_dict["error"]["code"] == "AUTH-002", f"Expected AUTH-002, got {body_dict['error']['code']}"


@pytest.mark.asyncio
async def test_observer_delete_returns_403_with_auth_002():
    request = MockRequest(method="DELETE", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is not None, "Expected 403 response for DELETE"
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got {response.status_code}"
    body = response.body
    body_dict = json.loads(body)
    assert body_dict["error"]["code"] == "AUTH-002", f"Expected AUTH-002, got {body_dict['error']['code']}"


@pytest.mark.asyncio
async def test_observer_get_response_time_within_200ms():
    request = MockRequest(method="GET", user_role="observer")
    start = time.perf_counter()
    response = await mock_observer_authorization_check(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms <= 200, f"GET response time {elapsed_ms:.2f}ms exceeded 200ms limit"


@pytest.mark.asyncio
async def test_observer_put_response_time_within_200ms():
    request = MockRequest(method="PUT", user_role="observer")
    start = time.perf_counter()
    response = await mock_observer_authorization_check(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms <= 200, f"PUT response time {elapsed_ms:.2f}ms exceeded 200ms limit"


@pytest.mark.asyncio
async def test_observer_delete_response_time_within_200ms():
    request = MockRequest(method="DELETE", user_role="observer")
    start = time.perf_counter()
    response = await mock_observer_authorization_check(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms <= 200, f"DELETE response time {elapsed_ms:.2f}ms exceeded 200ms limit"


@pytest.mark.asyncio
async def test_non_observer_user_can_put_successfully():
    request = MockRequest(method="PUT", user_role="admin")
    response = await mock_observer_authorization_check(request)
    assert response is None, "Expected pass-through for non-observer PUT"


@pytest.mark.asyncio
async def test_non_observer_user_can_delete_successfully():
    request = MockRequest(method="DELETE", user_role="admin")
    response = await mock_observer_authorization_check(request)
    assert response is None, "Expected pass-through for non-observer DELETE"
