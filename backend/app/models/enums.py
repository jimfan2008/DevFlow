import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class ProjectStatus(str, enum.Enum):
    created = "created"
    in_progress = "in_progress"
    completed = "completed"


class AgentType(str, enum.Enum):
    hermes = "hermes"
    trae = "trae"
    codearts = "codearts"
    opencode = "opencode"
    cursor = "cursor"
    claude_code = "claude_code"
    codebuddy = "codebuddy"
    lingma = "lingma"
    devika = "devika"


class AgentStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    busy = "busy"


class DiscoveredBy(str, enum.Enum):
    profile_scan = "profile_scan"
    skill_discover = "skill_discover"


class SkillType(str, enum.Enum):
    discover_agent = "discover_agent"
    connect_agent = "connect_agent"
    assign_task = "assign_task"
    receive_message = "receive_message"
    execute_task = "execute_task"
    review_result = "review_result"
    generate_report = "generate_report"
    manage_repo = "manage_repo"
    coordinate_meeting = "coordinate_meeting"


class SkillStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class ConnectionStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    reconnecting = "reconnecting"


class TaskPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    running = "running"
    in_progress = "in_progress"
    delivered = "delivered"
    accepted = "accepted"
    failed = "failed"
    rejected = "rejected"
    reassigned = "reassigned"


class AcceptanceResult(str, enum.Enum):
    accepted = "accepted"
    rejected = "rejected"


class GroupMode(str, enum.Enum):
    discussion = "discussion"
    meeting = "meeting"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MeetingType(str, enum.Enum):
    requirement_review = "requirement_review"
    tech_solution = "tech_solution"
    daily_standup = "daily_standup"
    incident_postmortem = "incident_postmortem"


class GroupTaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class PRStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    merged = "merged"
    conflict = "conflict"


class BranchType(str, enum.Enum):
    main = "main"
    develop = "develop"
    feature = "feature"
    release = "release"
    hotfix = "hotfix"
    bugfix = "bugfix"


class NotificationChannel(str, enum.Enum):
    platform = "platform"
    email = "email"
    sms = "sms"


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    QA_REVIEW = "qa_review"
    PASSED = "passed"
    REJECTED = "rejected"
    COMPLETED = "completed"


class QAStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class SwarmPurpose(str, enum.Enum):
    CODE_WRITING = "code_writing"
    TEST_EXECUTION = "test_execution"


class RoleType(str, enum.Enum):
    PROJECT_MANAGER = "project_manager"
    REQUIREMENT_ANALYST = "requirement_analyst"
    ARCHITECT = "architect"
    PROGRAMMER = "programmer"
    TESTER = "tester"
    CICD_ENGINEER = "cicd_engineer"
    DOC_MANAGER = "doc_manager"
    QA = "qa"
    SECURITY_OFFICER = "security_officer"
    SYSTEM_ADMIN = "system_admin"
    SWARM_MEMBER = "swarm_member"
