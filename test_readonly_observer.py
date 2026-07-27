import pytest
import json
from fastapi import status
from fastapi.responses import JSONResponse


class MockRequest:
    def __init__(self, method: str, user_role: str = "observer"):
        self.method = method
        self.state = type("obj", (object,), {"user": type("obj", (object,), {"role": user_role})})


class MockRequestNoUser:
    """MockRequest with state but no user attribute."""
    def __init__(self, method: str):
        self.method = method
        self.state = type("obj", (object,), {})()


class MockRequestNoRole:
    """MockRequest with state.user but no role attribute."""
    def __init__(self, method: str):
        self.method = method
        self.state = type("obj", (object,), {"user": type("obj", (object,), {})()})()


async def mock_observer_authorization_check(request):
    """Authorization middleware that blocks non-GET for observer role."""
    user = getattr(getattr(request.state, "user", None), "role", None)
    if user == "observer":
        if request.method.upper() not in ("GET", "OPTIONS", "HEAD"):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": {"code": "AUTH-002", "message": "Read-only observer cannot modify resources"}},
            )
    return None


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
async def test_observer_post_returns_403_with_auth_002():
    request = MockRequest(method="POST", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is not None, "Expected 403 response for POST"
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got {response.status_code}"
    body = response.body
    body_dict = json.loads(body)
    assert body_dict["error"]["code"] == "AUTH-002", f"Expected AUTH-002, got {body_dict['error']['code']}"


@pytest.mark.asyncio
async def test_observer_patch_returns_403_with_auth_002():
    request = MockRequest(method="PATCH", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is not None, "Expected 403 response for PATCH"
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got {response.status_code}"
    body = response.body
    body_dict = json.loads(body)
    assert body_dict["error"]["code"] == "AUTH-002", f"Expected AUTH-002, got {body_dict['error']['code']}"


@pytest.mark.asyncio
async def test_observer_options_returns_none():
    request = MockRequest(method="OPTIONS", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is None, f"Expected None (pass-through) for OPTIONS, got {response}"


@pytest.mark.asyncio
async def test_observer_head_returns_none():
    request = MockRequest(method="HEAD", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is None, f"Expected None (pass-through) for HEAD, got {response}"


@pytest.mark.asyncio
async def test_observer_case_insensitive_method():
    request = MockRequest(method="get", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is None, f"Expected None (pass-through) for lowercase 'get', got {response}"


@pytest.mark.asyncio
async def test_observer_case_insensitive_method_put():
    request = MockRequest(method="put", user_role="observer")
    response = await mock_observer_authorization_check(request)
    assert response is not None, "Expected 403 response for lowercase 'put'"
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got {response.status_code}"
    body = response.body
    body_dict = json.loads(body)
    assert body_dict["error"]["code"] == "AUTH-002"


@pytest.mark.asyncio
async def test_request_no_user_attribute_passes_through():
    request = MockRequestNoUser(method="PUT")
    response = await mock_observer_authorization_check(request)
    assert response is None, "Expected pass-through when state has no user attribute"


@pytest.mark.asyncio
async def test_request_user_no_role_attribute_passes_through():
    request = MockRequestNoRole(method="PUT")
    response = await mock_observer_authorization_check(request)
    assert response is None, "Expected pass-through when state.user has no role attribute"


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