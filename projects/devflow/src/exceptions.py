#!/usr/bin/env python3
"""
DevFlow 自定义异常定义
"""

from typing import Optional, Any


class DevFlowError(Exception):
    """DevFlow 基础异常"""

    def __init__(self, message: str = "", code: int = 1, detail: Optional[Any] = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(DevFlowError):
    """资源不存在"""

    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(message=message, code=404, detail=detail)


class ValidationError(DevFlowError):
    """参数校验失败"""

    def __init__(self, message: str = "参数校验失败", detail: Optional[Any] = None):
        super().__init__(message=message, code=422, detail=detail)


class AuthError(DevFlowError):
    """认证/授权失败"""

    def __init__(self, message: str = "认证失败", detail: Optional[Any] = None):
        super().__init__(message=message, code=401, detail=detail)


class ForbiddenError(DevFlowError):
    """权限不足"""

    def __init__(self, message: str = "权限不足", detail: Optional[Any] = None):
        super().__init__(message=message, code=403, detail=detail)


class ConflictError(DevFlowError):
    """资源冲突"""

    def __init__(self, message: str = "资源冲突", detail: Optional[Any] = None):
        super().__init__(message=message, code=409, detail=detail)


class AgentNotAvailableError(DevFlowError):
    """Agent 不可用"""

    def __init__(self, message: str = "Agent 不可用", detail: Optional[Any] = None):
        super().__init__(message=message, code=503, detail=detail)


class SwarmExecutionError(DevFlowError):
    """蜂群执行失败"""

    def __init__(self, message: str = "蜂群执行失败", detail: Optional[Any] = None):
        super().__init__(message=message, code=500, detail=detail)
