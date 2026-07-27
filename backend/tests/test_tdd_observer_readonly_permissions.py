#!/usr/bin/env python3
"""
测试用例：只读观察员权限限制
验证只读观察员仅允许查看，不允许修改任何内容

验收标准：
- GET 返回 HTTP 200
- PUT、DELETE、POST 返回 HTTP 403，error.code='AUTH-002'
- OPTIONS、HEAD 也允许通过（安全方法）
"""
import pytest
from unittest.mock import Mock

from app.middleware.authorization import (
    check_observer_permissions,
    ObserverReadOnlyError,
    _SAFE_METHODS,
)
from app.core.exceptions import DevFlowException


# ── Mock 辅助类 ──────────────────────────────────────────

class _MockUser:
    """模拟 user 对象"""

    def __init__(self, role: str):
        self.role = role


class _MockState:
    """模拟 request.state 对象"""

    def __init__(self, user=None):
        self._user = user

    @property
    def user(self):
        if self._user is None:
            raise AttributeError("user")
        return self._user


class _MockRequest:
    """模拟 Starlette Request 对象"""

    def __init__(self, method: str = "GET", user: _MockUser = None):
        self.method = method
        if user is not None:
            self.state = _MockState(user=user)
        else:
            self.state = _MockState(user=None)


def _make_request(method: str, role: str | None = None):
    """便捷构造 MockRequest"""
    user = _MockUser(role=role) if role is not None else None
    return _MockRequest(method=method, user=user)


# ── 生产代码导入验证 ─────────────────────────────────────

class TestObserverPermissionsImport:
    """验证正确导入了生产代码而非内联 mock"""

    def test_check_observer_permissions_is_from_production(self):
        func = check_observer_permissions
        assert func.__module__ == "app.middleware.authorization", (
            f"Expected import from production module 'app.middleware.authorization', "
            f"got {func.__module__!r}"
        )

    def test_observer_readonly_error_is_devflow_exception(self):
        assert issubclass(ObserverReadOnlyError, DevFlowException), (
            "ObserverReadOnlyError must be a subclass of DevFlowException"
        )

    def test_observer_readonly_error_has_correct_status(self):
        exc = ObserverReadOnlyError()
        assert exc.status_code == 403
        assert exc.error_code == "AUTH-002"


# ── 核心功能测试 ─────────────────────────────────────────

class TestObserverGetAllowed:
    """GET 请求应被允许（返回 None 即不抛出异常）"""

    def test_observer_get_returns_none(self):
        result = check_observer_permissions(_make_request("GET", "observer"))
        assert result is None

    def test_observer_get_lower_returns_none(self):
        result = check_observer_permissions(_make_request("get", "observer"))
        assert result is None

    def test_observer_get_upper_explicit_returns_none(self):
        result = check_observer_permissions(_make_request("GET", "observer"))
        assert result is None


class TestObserverOptionsAllowed:
    """OPTIONS 请求应被允许（安全方法）"""

    def test_observer_options_returns_none(self):
        result = check_observer_permissions(_make_request("OPTIONS", "observer"))
        assert result is None

    def test_observer_options_lower_returns_none(self):
        result = check_observer_permissions(_make_request("options", "observer"))
        assert result is None


class TestObserverHeadAllowed:
    """HEAD 请求应被允许（安全方法）"""

    def test_observer_head_returns_none(self):
        result = check_observer_permissions(_make_request("HEAD", "observer"))
        assert result is None

    def test_observer_head_lower_returns_none(self):
        result = check_observer_permissions(_make_request("head", "observer"))
        assert result is None


class TestObserverPutBlocked:
    """PUT 请求应被阻止"""

    def test_observer_put_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("PUT", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"

    def test_observer_put_lower_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("put", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"


class TestObserverDeleteBlocked:
    """DELETE 请求应被阻止"""

    def test_observer_delete_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("DELETE", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"

    def test_observer_delete_lower_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("delete", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"


class TestObserverPostBlocked:
    """POST 请求应被阻止（创建资源，同属写操作）"""

    def test_observer_post_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("POST", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"

    def test_observer_post_lower_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("post", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"


class TestObserverPatchBlocked:
    """PATCH 请求应被阻止（部分更新，也属写操作）"""

    def test_observer_patch_raises_403(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("PATCH", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"


# ── 非观察员角色测试 ─────────────────────────────────────

class TestNonObserverRolesPassThrough:
    """非 observer 角色不应被拦截"""

    def test_admin_get_returns_none(self):
        result = check_observer_permissions(_make_request("GET", "admin"))
        assert result is None

    def test_admin_put_returns_none(self):
        result = check_observer_permissions(_make_request("PUT", "admin"))
        assert result is None

    def test_admin_delete_returns_none(self):
        result = check_observer_permissions(_make_request("DELETE", "admin"))
        assert result is None

    def test_user_get_returns_none(self):
        result = check_observer_permissions(_make_request("GET", "user"))
        assert result is None

    def test_user_put_returns_none(self):
        result = check_observer_permissions(_make_request("PUT", "user"))
        assert result is None

    def test_manager_delete_returns_none(self):
        result = check_observer_permissions(_make_request("DELETE", "manager"))
        assert result is None

    def test_viewer_post_returns_none(self):
        result = check_observer_permissions(_make_request("POST", "viewer"))
        assert result is None


class TestBoundaryRolesPassThrough:
    """边界角色（空字符串、未知角色）不应被误拦"""

    def test_empty_role_returns_none(self):
        result = check_observer_permissions(_make_request("PUT", ""))
        assert result is None

    def test_unknown_role_guest_returns_none(self):
        result = check_observer_permissions(_make_request("PUT", "guest"))
        assert result is None

    def test_unknown_role_superadmin_returns_none(self):
        result = check_observer_permissions(_make_request("DELETE", "superadmin"))
        assert result is None

    def test_none_role_returns_none(self):
        result = check_observer_permissions(_make_request("POST", None))
        assert result is None


# ── 无认证用户测试 ────────────────────────────────────────

class TestNoUserAttribute:
    """request.state 没有 user 属性时，应放行（交由认证层处理）"""

    def test_no_user_state_returns_none(self):
        req = _MockRequest(method="PUT")
        req.state = type("State", (), {"__getattr__": lambda self, attr: (_ for _ in ()).throw(AttributeError(attr))})()
        result = check_observer_permissions(req)
        assert result is None

    def test_no_user_delete_returns_none(self):
        req = _MockRequest(method="DELETE")
        req.state = type("EmptyState", (), {})()
        result = check_observer_permissions(req)
        assert result is None

    def test_no_user_post_returns_none(self):
        req = _MockRequest(method="POST")
        req.state = type("EmptyState", (), {})()
        result = check_observer_permissions(req)
        assert result is None


class TestNoRoleAttribute:
    """user 对象没有 role 属性时，应放行（getattr 返回 None）"""

    def test_user_without_role_attribute_returns_none(self):
        user = type("User", (), {})()  # 无 role 属性
        req = _MockRequest(method="PUT", user=user)
        result = check_observer_permissions(req)
        assert result is None

    def test_user_without_role_attribute_delete_returns_none(self):
        user = type("User", (), {})()
        req = _MockRequest(method="DELETE", user=user)
        result = check_observer_permissions(req)
        assert result is None


class TestRoleCaseSensitivity:
    """角色名为大小写变体时，不应被误拦为 observer"""

    def test_observer_uppercase_returns_none(self):
        # "Observer" != "observer"，不应被拦截
        result = check_observer_permissions(_make_request("PUT", "Observer"))
        assert result is None

    def test_observer_uppercase_blocked_returns_none(self):
        # "OBSERVER" != "observer"，不应被拦截
        result = check_observer_permissions(_make_request("PUT", "OBSERVER"))
        assert result is None

    def test_observer_mixed_case_returns_none(self):
        # "ObSeRvEr" != "observer"，不应被拦截
        result = check_observer_permissions(_make_request("DELETE", "ObSeRvEr"))
        assert result is None

    def test_observer_trailing_space_returns_none(self):
        # "observer " != "observer"（尾部空格），不应被拦截
        result = check_observer_permissions(_make_request("PUT", "observer "))
        assert result is None

    def test_observer_leading_space_returns_none(self):
        # " observer" != "observer"（前导空格），不应被拦截
        result = check_observer_permissions(_make_request("PUT", " observer"))
        assert result is None


# ── 方法名大小写防御测试 ──────────────────────────────────

class TestMethodCaseInsensitivity:
    """方法名大小写不敏感"""

    def test_mixed_case_get_allowed(self):
        result = check_observer_permissions(_make_request("GeT", "observer"))
        assert result is None

    def test_mixed_case_put_blocked(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("PuT", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"

    def test_mixed_case_delete_blocked(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("DeLeTe", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"

    def test_mixed_case_post_blocked(self):
        with pytest.raises(ObserverReadOnlyError) as exc_info:
            check_observer_permissions(_make_request("PoSt", "observer"))
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "AUTH-002"


# ── 安全方法集合完整性测试 ────────────────────────────────

class TestSafeMethodsCompleteness:
    """验证安全方法集合包含 GET、OPTIONS、HEAD"""

    def test_safe_methods_contains_get(self):
        assert "GET" in _SAFE_METHODS

    def test_safe_methods_contains_options(self):
        assert "OPTIONS" in _SAFE_METHODS

    def test_safe_methods_contains_head(self):
        assert "HEAD" in _SAFE_METHODS

    def test_safe_methods_not_contains_put(self):
        assert "PUT" not in _SAFE_METHODS

    def test_safe_methods_not_contains_delete(self):
        assert "DELETE" not in _SAFE_METHODS

    def test_safe_methods_not_contains_post(self):
        assert "POST" not in _SAFE_METHODS

    def test_safe_methods_not_contains_patch(self):
        assert "PATCH" not in _SAFE_METHODS


# ── 异常类属性测试 ────────────────────────────────────────

class TestObserverReadOnlyErrorAttributes:
    """ObserverReadOnlyError 异常类属性"""

    def test_error_status_code_is_403(self):
        exc = ObserverReadOnlyError()
        assert exc.status_code == 403

    def test_error_code_is_auth_002(self):
        exc = ObserverReadOnlyError()
        assert exc.error_code == "AUTH-002"

    def test_error_detail_not_empty(self):
        exc = ObserverReadOnlyError()
        assert len(exc.detail) > 0

    def test_error_is_instance_of_devflow_exception(self):
        exc = ObserverReadOnlyError()
        assert isinstance(exc, DevFlowException)

    def test_error_is_instance_of_http_exception(self):
        from fastapi import HTTPException
        exc = ObserverReadOnlyError()
        assert isinstance(exc, HTTPException)
