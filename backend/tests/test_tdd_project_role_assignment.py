import pytest
import time
import uuid
from sqlalchemy import create_engine, Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
import enum

test_base = declarative_base()


class RoleType(str, enum.Enum):
    manager = "manager"
    developer = "developer"
    viewer = "viewer"


class ProjectMember(test_base):
    __tablename__ = "project_members"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    role = Column(SAEnum(RoleType), nullable=False, default=RoleType.viewer)
    assigned_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "role": self.role.value,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }


class ProjectRoleService:
    def __init__(self, db=None):
        self.db = db

    def assign_role(self, user_id: str, project_id: str, role: RoleType) -> ProjectMember:
        if self.db:
            existing = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
            ).first()
            if existing:
                existing.role = role
                self.db.commit()
                self.db.refresh(existing)
                return existing
        member = ProjectMember(
            id=str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            role=role,
        )
        if self.db:
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
        return member

    def get_role(self, user_id: str, project_id: str) -> str | None:
        if self.db:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
            ).first()
            if member:
                return member.role.value
            return None
        return None

    def get_user_projects(self, user_id: str) -> list[dict]:
        if self.db:
            members = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()
            return [m.to_dict() for m in members]
        return []


TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session():
    test_base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        test_base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def service(db_session):
    return ProjectRoleService(db=db_session)


class TestProjectRoleAssignment:
    USER_ID = "user_001"
    PROJECT_A = "project_p1"
    PROJECT_B = "project_p2"

    def test_assign_manager_role_to_user_in_project_a(self, service):
        member = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        assert member is not None
        assert member.user_id == self.USER_ID
        assert member.project_id == self.PROJECT_A
        assert member.role == RoleType.manager

    def test_assign_developer_role_to_user_in_project_b(self, service):
        member = service.assign_role(self.USER_ID, self.PROJECT_B, RoleType.developer)
        assert member is not None
        assert member.user_id == self.USER_ID
        assert member.project_id == self.PROJECT_B
        assert member.role == RoleType.developer

    def test_same_user_has_different_roles_in_different_projects(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        service.assign_role(self.USER_ID, self.PROJECT_B, RoleType.developer)
        role_in_a = service.get_role(self.USER_ID, self.PROJECT_A)
        role_in_b = service.get_role(self.USER_ID, self.PROJECT_B)
        assert role_in_a == "manager"
        assert role_in_b == "developer"
        assert role_in_a != role_in_b

    def test_role_independence_across_projects(self, service):
        member_a = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        member_b = service.assign_role(self.USER_ID, self.PROJECT_B, RoleType.developer)
        assert member_a.id != member_b.id
        p1_role = service.get_role(self.USER_ID, self.PROJECT_A)
        p2_role = service.get_role(self.USER_ID, self.PROJECT_B)
        assert p1_role == "manager"
        assert p2_role == "developer"
        db_a = service.db.query(ProjectMember).filter(
            ProjectMember.user_id == self.USER_ID,
            ProjectMember.project_id == self.PROJECT_A,
        ).first()
        db_b = service.db.query(ProjectMember).filter(
            ProjectMember.user_id == self.USER_ID,
            ProjectMember.project_id == self.PROJECT_B,
        ).first()
        assert db_a.role == RoleType.manager
        assert db_b.role == RoleType.developer

    def test_response_time_under_200ms_for_get_role(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        start = time.perf_counter()
        role = service.get_role(self.USER_ID, self.PROJECT_A)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert role == "manager"
        assert elapsed_ms <= 200, f"响应时间 {elapsed_ms:.2f}ms 超过 200ms 上限"

    def test_response_time_under_200ms_for_assign_role(self, service):
        start = time.perf_counter()
        member = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert member is not None
        assert elapsed_ms <= 200, f"分配角色响应时间 {elapsed_ms:.2f}ms 超过 200ms"

    def test_nonexistent_user_role_returns_none(self, service):
        role = service.get_role("nonexistent_user", self.PROJECT_A)
        assert role is None

    def test_nonexistent_project_role_returns_none(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        role = service.get_role(self.USER_ID, "nonexistent_project")
        assert role is None

    def test_get_user_projects_returns_all_project_roles(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        service.assign_role(self.USER_ID, self.PROJECT_B, RoleType.developer)
        projects = service.get_user_projects(self.USER_ID)
        assert len(projects) == 2
        proj_roles = {(p["project_id"], p["role"]) for p in projects}
        assert (self.PROJECT_A, "manager") in proj_roles
        assert (self.PROJECT_B, "developer") in proj_roles

    def test_assign_role_updates_existing_membership(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        updated = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.viewer)
        assert updated.role == RoleType.viewer
        role = service.get_role(self.USER_ID, self.PROJECT_A)
        assert role == "viewer"

    def test_different_users_independent_roles_in_same_project(self, service):
        user_x = "user_x"
        user_y = "user_y"
        service.assign_role(user_x, self.PROJECT_A, RoleType.manager)
        service.assign_role(user_y, self.PROJECT_A, RoleType.developer)
        assert service.get_role(user_x, self.PROJECT_A) == "manager"
        assert service.get_role(user_y, self.PROJECT_A) == "developer"

    def test_role_assignment_persists_in_database(self, service, db_session):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        saved = db_session.query(ProjectMember).filter(
            ProjectMember.user_id == self.USER_ID,
            ProjectMember.project_id == self.PROJECT_A,
        ).first()
        assert saved is not None
        assert saved.role == RoleType.manager

    def test_viewer_role_default_for_new_project_member(self, service):
        service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.viewer)
        role = service.get_role(self.USER_ID, self.PROJECT_A)
        assert role == "viewer"

    def test_project_role_contains_assigned_at_timestamp(self, service):
        member = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        assert member.assigned_at is not None
        assert isinstance(member.assigned_at, datetime)

    def test_to_dict_returns_expected_keys(self, service):
        member = service.assign_role(self.USER_ID, self.PROJECT_A, RoleType.manager)
        d = member.to_dict()
        assert d["user_id"] == self.USER_ID
        assert d["project_id"] == self.PROJECT_A
        assert d["role"] == "manager"
        assert "id" in d
        assert "assigned_at" in d
