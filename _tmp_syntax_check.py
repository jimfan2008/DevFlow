#!/usr/bin/env python3
class DevFlowException(Exception):
    """Base exception for all DevFlow custom exceptions."""
    def __init__(self, message: str, code: str | None = None, status_code: int = 500) -> None:
        self.message = message
        self.code = code or "INTERNAL-001"
        self.status_code = status_code
        super().__init__(self.message)
    def to_dict(self) -> dict[str, str]:
        return {"error": {"code": self.code, "message": self.message}}
class AuthenticationError(DevFlowException):
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH-001") -> None:
        super().__init__(message=message, code=code, status_code=401)
class InvalidCredentialsError(AuthenticationError):
    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message=message, code="AUTH-004")
class TokenExpiredError(AuthenticationError):
    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message=message, code="AUTH-005")
class TokenInvalidError(AuthenticationError):
    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message=message, code="AUTH-006")
class SessionExpiredError(AuthenticationError):
    def __init__(self, message: str = "Session has expired due to inactivity") -> None:
        super().__init__(message=message, code="AUTH-007")
class AuthorizationError(DevFlowException):
    def __init__(self, message: str = "Insufficient permissions", code: str = "AUTH-002") -> None:
        super().__init__(message=message, code=code, status_code=403)
class ResourceNotFoundError(DevFlowException):
    def __init__(self, resource: str = "Resource", identifier: str = "", code: str = "NOTFOUND-001") -> None:
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} '{identifier}' not found"
        super().__init__(message=msg, code=code, status_code=404)
class UserNotFoundError(ResourceNotFoundError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(resource="User", identifier=identifier, code="NOTFOUND-002")
class ProjectNotFoundError(ResourceNotFoundError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(resource="Project", identifier=identifier, code="NOTFOUND-003")
class AgentNotFoundError(ResourceNotFoundError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(resource="Agent", identifier=identifier, code="NOTFOUND-004")
class RoleNotFoundError(ResourceNotFoundError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(resource="Role", identifier=identifier, code="NOTFOUND-005")
class GroupNotFoundError(ResourceNotFoundError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(resource="Group", identifier=identifier, code="NOTFOUND-006")
class ValidationError(DevFlowException):
    def __init__(self, message: str = "Validation failed", code: str = "VALID-001", field: str | None = None) -> None:
        self.field = field
        super().__init__(message=message, code=code, status_code=400)
class PasswordPolicyError(ValidationError):
    def __init__(self, message: str = "Password must be at least 8 characters with uppercase, lowercase, and digits") -> None:
        super().__init__(message=message, code="VALID-002")
class EmailFormatError(ValidationError):
    def __init__(self, message: str = "Invalid email format") -> None:
        super().__init__(message=message, code="VALID-003")
class ResourceConflictError(DevFlowException):
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT-001") -> None:
        super().__init__(message=message, code=code, status_code=409)
class EmailAlreadyRegisteredError(ResourceConflictError):
    def __init__(self, message: str = "Email already registered") -> None:
        super().__init__(message=message, code="CONFLICT-002")
class DuplicateUsernameError(ResourceConflictError):
    def __init__(self, message: str = "Username already taken") -> None:
        super().__init__(message=message, code="CONFLICT-003")
class WorkflowStateError(DevFlowException):
    def __init__(self, message: str = "Invalid workflow state transition", code: str = "WORKFLOW-001") -> None:
        super().__init__(message=message, code=code, status_code=409)
class QAGateRejection(DevFlowException):
    def __init__(self, message: str = "QA gate check failed", code: str = "QA-001", details: list[str] | None = None) -> None:
        self.details = details or []
        super().__init__(message=message, code=code, status_code=422)
class RateLimitError(DevFlowException):
    def __init__(self, message: str = "Rate limit exceeded, please try again later", code: str = "RATE-001") -> None:
        super().__init__(message=message, code=code, status_code=429)
class ServiceUnavailableError(DevFlowException):
    def __init__(self, message: str = "Service temporarily unavailable", code: str = "SERVICE-001") -> None:
        super().__init__(message=message, code=code, status_code=503)
class InferenceTimeoutError(DevFlowException):
    def __init__(self, message: str = "AI inference service is busy, please retry later", code: str = "INFER-001") -> None:
        super().__init__(message=message, code=code, status_code=503)
class CeleryTaskError(DevFlowException):
    def __init__(self, message: str = "Task execution failed", code: str = "TASK-001", task_id: str | None = None) -> None:
        self.task_id = task_id
        super().__init__(message=message, code=code, status_code=500)
class BackupError(DevFlowException):
    def __init__(self, message: str = "Backup operation failed", code: str = "BACKUP-001") -> None:
        super().__init__(message=message, code=code, status_code=500)
class GiteaIntegrationError(DevFlowException):
    def __init__(self, message: str = "Repository operation failed", code: str = "GITEA-001") -> None:
        super().__init__(message=message, code=code, status_code=502)
