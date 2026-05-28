import pytest
from fastapi.testclient import TestClient
from app.core.exceptions import (
    DevFlowException,
    AuthUserNotFoundError, AuthPasswordError,
    ProjectNotFoundError, ProjectAlreadyExistsError,
    RequirementNotFoundError, RequirementLockedError,
    TaskNotFoundError, TaskAlreadyAssignedError, TaskStatusTransitionError, TaskDependencyError,
    AgentNotFoundError, AgentOfflineError, AgentBusyError, AgentRegistrationError,
    GroupNotFoundError, GroupMeetingError,
    RepoNotFoundError, RepoAlreadyExistsError, RepoCommitValidationError, RepoBranchError,
    GatewayConnectionError, GatewayTimeoutError,
    MeetingAlreadyInProgressError, MeetingHostOfflineError,
    SkillNoAgentError, SkillConnectError, SkillOverloadedError, SkillExecutionError,
)


class TestErrorCodeCoverage:
    def test_auth_001(self):
        exc = AuthUserNotFoundError()
        assert exc.error_code == "AUTH_001"
        assert exc.status_code == 401

    def test_auth_002(self):
        exc = AuthPasswordError()
        assert exc.error_code == "AUTH_002"
        assert exc.status_code == 401

    def test_proj_001(self):
        exc = ProjectNotFoundError("p1")
        assert exc.error_code == "PROJ_001"
        assert exc.status_code == 404

    def test_proj_002(self):
        exc = ProjectAlreadyExistsError("TestProj")
        assert exc.error_code == "PROJ_002"
        assert exc.status_code == 400

    def test_req_001(self):
        exc = RequirementNotFoundError()
        assert exc.error_code == "REQ_001"
        assert exc.status_code == 404

    def test_req_002(self):
        exc = RequirementLockedError()
        assert exc.error_code == "REQ_002"
        assert exc.status_code == 409

    def test_task_001(self):
        exc = TaskNotFoundError("t1")
        assert exc.error_code == "TASK_001"
        assert exc.status_code == 404

    def test_task_002(self):
        exc = TaskAlreadyAssignedError()
        assert exc.error_code == "TASK_002"
        assert exc.status_code == 409

    def test_task_003(self):
        exc = TaskStatusTransitionError("done", "todo")
        assert exc.error_code == "TASK_003"
        assert exc.status_code == 409

    def test_task_004(self):
        exc = TaskDependencyError()
        assert exc.error_code == "TASK_004"
        assert exc.status_code == 409

    def test_agent_001(self):
        exc = AgentNotFoundError("a1")
        assert exc.error_code == "AGENT_001"
        assert exc.status_code == 404

    def test_agent_002(self):
        exc = AgentOfflineError("Agent1")
        assert exc.error_code == "AGENT_002"
        assert exc.status_code == 503

    def test_agent_003(self):
        exc = AgentBusyError()
        assert exc.error_code == "AGENT_003"
        assert exc.status_code == 503

    def test_agent_004(self):
        exc = AgentRegistrationError()
        assert exc.error_code == "AGENT_004"
        assert exc.status_code == 400

    def test_group_001(self):
        exc = GroupNotFoundError()
        assert exc.error_code == "GROUP_001"
        assert exc.status_code == 404

    def test_group_002(self):
        exc = GroupMeetingError()
        assert exc.error_code == "GROUP_002"
        assert exc.status_code == 409

    def test_repo_001(self):
        exc = RepoNotFoundError()
        assert exc.error_code == "REPO_001"
        assert exc.status_code == 404

    def test_repo_002(self):
        exc = RepoAlreadyExistsError()
        assert exc.error_code == "REPO_002"
        assert exc.status_code == 409

    def test_repo_003(self):
        exc = RepoCommitValidationError()
        assert exc.error_code == "REPO_003"
        assert exc.status_code == 400

    def test_repo_004(self):
        exc = RepoBranchError()
        assert exc.error_code == "REPO_004"
        assert exc.status_code == 400

    def test_gateway_001(self):
        exc = GatewayConnectionError()
        assert exc.error_code == "GATEWAY_001"
        assert exc.status_code == 503

    def test_gateway_002(self):
        exc = GatewayTimeoutError()
        assert exc.error_code == "GATEWAY_002"
        assert exc.status_code == 504

    def test_meeting_001(self):
        exc = MeetingAlreadyInProgressError()
        assert exc.error_code == "MEETING_001"
        assert exc.status_code == 409

    def test_meeting_002(self):
        exc = MeetingHostOfflineError()
        assert exc.error_code == "MEETING_002"
        assert exc.status_code == 503

    def test_skill_001(self):
        exc = SkillNoAgentError()
        assert exc.error_code == "SKILL_001"
        assert exc.status_code == 503

    def test_skill_002(self):
        exc = SkillConnectError()
        assert exc.error_code == "SKILL_002"
        assert exc.status_code == 503

    def test_skill_003(self):
        exc = SkillOverloadedError()
        assert exc.error_code == "SKILL_003"
        assert exc.status_code == 503

    def test_skill_004(self):
        exc = SkillExecutionError()
        assert exc.error_code == "SKILL_004"
        assert exc.status_code == 500


class TestErrorFormat:
    def test_error_response_format(self):
        exc = ProjectNotFoundError("proj-123")
        assert exc.error_code == "PROJ_001"
        assert "proj-123" in exc.detail
        assert exc.status_code == 404

    def test_all_errors_inherit_devflow_exception(self):
        error_classes = [
            AuthUserNotFoundError, AuthPasswordError,
            ProjectNotFoundError, ProjectAlreadyExistsError,
            RequirementNotFoundError, RequirementLockedError,
            TaskNotFoundError, TaskAlreadyAssignedError, TaskStatusTransitionError, TaskDependencyError,
            AgentNotFoundError, AgentOfflineError, AgentBusyError, AgentRegistrationError,
            GroupNotFoundError, GroupMeetingError,
            RepoNotFoundError, RepoAlreadyExistsError, RepoCommitValidationError, RepoBranchError,
            GatewayConnectionError, GatewayTimeoutError,
            MeetingAlreadyInProgressError, MeetingHostOfflineError,
            SkillNoAgentError, SkillConnectError, SkillOverloadedError, SkillExecutionError,
        ]
        for cls in error_classes:
            try:
                instance = cls()
            except TypeError:
                instance = cls("test")
            assert isinstance(instance, DevFlowException)
            assert hasattr(instance, 'error_code')
            assert hasattr(instance, 'status_code')
            assert hasattr(instance, 'detail')
