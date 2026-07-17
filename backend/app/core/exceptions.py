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
        super().__init__(
            status_code=409,
            error_code="AUTH_USER_EXISTS",
            detail="Username or email already exists. Please log in or use another email.",
        )


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


class SkillExecutionError(DevFlowException):
    def __init__(self, detail: str = "Skill execution failed"):
        super().__init__(status_code=500, error_code="SKILL_004", detail=detail)


class ProjectNotFoundError(DevFlowException):
    def __init__(self, project_id: str = ""):
        msg = f"Project {project_id} not found" if project_id else "Project not found"
        super().__init__(status_code=404, error_code="PROJ_001", detail=msg)


class ProjectAlreadyExistsError(DevFlowException):
    def __init__(self, name: str = ""):
        msg = f"Project '{name}' already exists" if name else "Project already exists"
        super().__init__(status_code=400, error_code="PROJ_002", detail=msg)


class RequirementNotFoundError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=404, error_code="REQ_001", detail="Requirement not found")


class RequirementLockedError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=409, error_code="REQ_002", detail="Requirement is locked, modification denied")


class TaskNotFoundError(DevFlowException):
    def __init__(self, task_id: str = ""):
        msg = f"Task {task_id} not found" if task_id else "Task not found"
        super().__init__(status_code=404, error_code="TASK_001", detail=msg)


class TaskAlreadyAssignedError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=409, error_code="TASK_002", detail="Task already assigned")


class TaskStatusTransitionError(DevFlowException):
    def __init__(self, from_status: str = "", to_status: str = ""):
        super().__init__(status_code=409, error_code="TASK_003", detail=f"Cannot transition task from {from_status} to {to_status}")


class TaskDependencyError(DevFlowException):
    def __init__(self, detail: str = "Task dependency error"):
        super().__init__(status_code=409, error_code="TASK_004", detail=detail)


class AgentNotFoundError(DevFlowException):
    def __init__(self, agent_id: str = ""):
        msg = f"Agent {agent_id} not found" if agent_id else "Agent not found"
        super().__init__(status_code=404, error_code="AGENT_001", detail=msg)


class AgentOfflineError(DevFlowException):
    def __init__(self, name: str = ""):
        msg = f"Agent {name} is offline" if name else "Agent is offline"
        super().__init__(status_code=503, error_code="AGENT_002", detail=msg)


class AgentBusyError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=503, error_code="AGENT_003", detail="Agent is busy")


class AgentRegistrationError(DevFlowException):
    def __init__(self, detail: str = "Agent registration failed"):
        super().__init__(status_code=400, error_code="AGENT_004", detail=detail)


class GroupNotFoundError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=404, error_code="GROUP_001", detail="Group not found")


class GroupMeetingError(DevFlowException):
    def __init__(self, detail: str = "Meeting operation error"):
        super().__init__(status_code=409, error_code="GROUP_002", detail=detail)


class RepoNotFoundError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=404, error_code="REPO_001", detail="Repository not found")


class RepoAlreadyExistsError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=409, error_code="REPO_002", detail="Repository already exists")


class RepoCommitValidationError(DevFlowException):
    def __init__(self, detail: str = "Commit validation failed"):
        super().__init__(status_code=400, error_code="REPO_003", detail=detail)


class RepoBranchError(DevFlowException):
    def __init__(self, detail: str = "Branch operation failed"):
        super().__init__(status_code=400, error_code="REPO_004", detail=detail)


class GatewayConnectionError(DevFlowException):
    def __init__(self, detail: str = "Gateway connection failed"):
        super().__init__(status_code=503, error_code="GATEWAY_001", detail=detail)


class GatewayTimeoutError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=504, error_code="GATEWAY_002", detail="Gateway request timed out")


class MeetingAlreadyInProgressError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=409, error_code="MEETING_001", detail="Meeting already in progress for this group")


class MeetingHostOfflineError(DevFlowException):
    def __init__(self):
        super().__init__(status_code=503, error_code="MEETING_002", detail="Host agent is not online")


class GitHubOAuthError(DevFlowException):
    def __init__(self, detail: str = "GitHub OAuth failed"):
        super().__init__(status_code=400, error_code="AUTH_005", detail=detail)
