#!/usr/bin/env python3
"""自定义异常类"""
from fastapi import HTTPException


class DevFlowException(HTTPException):
    """DevFlow 自定义业务异常"""
    def __init__(self, status_code: int = 400, error_code: str = "UNKNOWN_ERROR", detail: str = "An error occurred"):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class TaskNotFound(DevFlowException):
    def __init__(self, task_id: str):
        super().__init__(status_code=404, error_code="TASK_NOT_FOUND", detail=f"Task {task_id} not found")


class BoardNotFound(DevFlowException):
    def __init__(self, board_id: str):
        super().__init__(status_code=404, error_code="BOARD_NOT_FOUND", detail=f"Board {board_id} not found")


class DependencyCycleDetected(DevFlowException):
    def __init__(self):
        super().__init__(status_code=409, error_code="DEPENDENCY_CYCLE_DETECTED", detail="Circular dependency detected")


class InvalidCredentials(DevFlowException):
    def __init__(self):
        super().__init__(status_code=401, error_code="AUTH_INVALID_CREDENTIALS", detail="Invalid username or password")


class UserAlreadyExists(DevFlowException):
    def __init__(self):
        super().__init__(status_code=400, error_code="AUTH_USER_EXISTS", detail="Username or email already exists")


class AuthUserNotFoundError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=401, error_code="AUTH_001", detail="User not found")


class AuthPasswordError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=401, error_code="AUTH_002", detail="Incorrect password")


class ForbiddenError(DevFlowException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, error_code="FORBIDDEN", detail=detail)


class SkillNoAgentError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=503, error_code="SKILL_001", detail="No available coding agent found")


class SkillConnectError(DevFlowException):
    def __init__(self, detail: str = "Failed to connect coding agent"):
        super().__init__(status_code=503, error_code="SKILL_002", detail=detail)


class SkillOverloadedError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=503, error_code="SKILL_003", detail="All matching agents are overloaded")
