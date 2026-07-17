#!/usr/bin/env python3
"""
观察者（只读）权限检查中间件
验证只读观察员仅允许查看，不允许修改任何内容
"""
from starlette.requests import Request
from app.core.exceptions import DevFlowException

# 只读安全方法集合
_SAFE_METHODS = frozenset({"GET", "OPTIONS", "HEAD"})


class ObserverReadOnlyError(DevFlowException):
    """只读观察员尝试执行写操作"""

    def __init__(self):
        super().__init__(
            status_code=403,
            error_code="AUTH-002",
            detail="Read-only observers are not permitted to modify resources",
        )


def check_observer_permissions(request: Request) -> None:
    """
    检查请求是否违反只读观察员权限约束。

    - 如果 request.state 没有 user 属性 → 返回 None（交由认证层处理）
    - 如果 user.role 不是 "observer" → 返回 None（非观察员，不拦截）
    - 如果方法是 GET/OPTIONS/HEAD → 返回 None（安全方法，允许通过）
    - 否则 → 抛出 ObserverReadOnlyError (403, AUTH-002)
    """
    # 未认证请求，交由上层认证中间件处理
    if not hasattr(request.state, "user"):
        return None

    user = request.state.user
    role = getattr(user, "role", None)

    # 非 observer 角色，不拦截
    if role != "observer":
        return None

    method = request.method
    if method and isinstance(method, str):
        method = method.upper()

    # 安全方法放行
    if method in _SAFE_METHODS:
        return None

    raise ObserverReadOnlyError()
