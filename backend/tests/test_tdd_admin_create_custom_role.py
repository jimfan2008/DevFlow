import time
import pytest
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import StaticPool
from typing import Optional

TestBase = declarative_base()

ROLE_PERMISSIONS_TABLE = Table(
    "custom_role_permissions",
    TestBase.metadata,
    Column("role_id", String, ForeignKey("custom_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_key", String, primary_key=True),
)

USER_CUSTOM_ROLES_TABLE = Table(
    "user_custom_roles",
    TestBase.metadata,
    Column("user_id", String, ForeignKey("test_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String, ForeignKey("custom_roles.id", ondelete="CASCADE"), primary_key=True),
)


class TestUser(TestBase):
    __tablename__ = "test_users"
    id = Column(String, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")


class CustomRole(TestBase):
    __tablename__ = "custom_roles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    role_type = Column(String(50), nullable=False, default="custom")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, ForeignKey("test_users.id"), nullable=False)


class CustomPermission(TestBase):
    __tablename__ = "custom_permissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)


ALL_PERMISSIONS = [
    {"key": "project_create", "label": "创建项目", "description": "允许创建新项目"},
    {"key": "project_delete", "label": "删除项目", "description": "允许删除已有项目"},
    {"key": "project_read", "label": "查看项目", "description": "允许查看项目详情"},
    {"key": "project_update", "label": "更新项目", "description": "允许更新项目信息"},
    {"key": "workflow_start", "label": "启动工作流", "description": "允许启动项目工作流"},
    {"key": "workflow_stop", "label": "停止工作流", "description": "允许停止运行中的工作流"},
    {"key": "workflow_view", "label": "查看工作流", "description": "允许查看工作流状态"},
    {"key": "workflow_edit", "label": "编辑工作流", "description": "允许编辑工作流配置"},
    {"key": "agent_manage", "label": "管理Agent", "description": "允许管理Agent配置"},
    {"key": "agent_assign", "label": "分配Agent", "description": "允许分配Agent到任务"},
    {"key": "agent_monitor", "label": "监控Agent", "description": "允许监控Agent运行状态"},
    {"key": "task_create", "label": "创建任务", "description": "允许创建新任务"},
    {"key": "task_delete", "label": "删除任务", "description": "允许删除已有任务"},
    {"key": "task_assign", "label": "分配任务", "description": "允许分配任务给Agent"},
    {"key": "task_review", "label": "审查任务", "description": "允许审查任务完成情况"},
    {"key": "requirement_read", "label": "查看需求", "description": "允许查看需求文档"},
    {"key": "requirement_edit", "label": "编辑需求", "description": "允许编辑需求文档"},
    {"key": "requirement_approve", "label": "审批需求", "description": "允许审批需求变更"},
    {"key": "code_review", "label": "代码审查", "description": "允许审查代码变更"},
    {"key": "qa_inspect", "label": "QA检验", "description": "允许执行QA检验"},
    {"key": "repo_manage", "label": "仓库管理", "description": "允许管理代码仓库"},
    {"key": "notification_manage", "label": "通知管理", "description": "允许管理通知设置"},
    {"key": "setting_manage", "label": "系统设置", "description": "允许管理系统设置"},
    {"key": "audit_log_view", "label": "审计日志", "description": "允许查看审计日志"},
]


class CustomRoleService:

    def __init__(self, db: Session):
        self.db = db

    def create_role(self, name: str, description: str, permission_keys: list[str], created_by: str) -> dict:
        if not name or not name.strip():
            raise ValueError("角色名称不能为空")
        existing = self.db.query(CustomRole).filter(CustomRole.name == name).first()
        if existing:
            raise ValueError(f"角色名称 '{name}' 已存在")

        valid_keys = {p["key"] for p in ALL_PERMISSIONS}
        for key in permission_keys:
            if key not in valid_keys:
                raise ValueError(f"无效权限 key: {key}")

        role = CustomRole(
            name=name.strip(),
            description=description,
            role_type="custom",
            created_by=created_by,
        )
        self.db.add(role)
        self.db.flush()

        for key in permission_keys:
            perm = self.db.query(CustomPermission).filter(CustomPermission.key == key).first()
            if not perm:
                perm_data = next(p for p in ALL_PERMISSIONS if p["key"] == key)
                perm = CustomPermission(key=key, label=perm_data["label"], description=perm_data["description"])
                self.db.add(perm)
                self.db.flush()
            stmt = ROLE_PERMISSIONS_TABLE.insert().values(role_id=role.id, permission_key=key)
            self.db.execute(stmt)

        self.db.commit()
        self.db.refresh(role)
        return self._role_to_dict(role)

    def assign_role_to_user(self, user_id: str, role_id: str) -> dict:
        user = self.db.query(TestUser).filter(TestUser.id == user_id).first()
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        role = self.db.query(CustomRole).filter(CustomRole.id == role_id).first()
        if not role:
            raise ValueError(f"角色 {role_id} 不存在")
        existing = self.db.execute(
            USER_CUSTOM_ROLES_TABLE.select().where(
                USER_CUSTOM_ROLES_TABLE.c.user_id == user_id,
                USER_CUSTOM_ROLES_TABLE.c.role_id == role_id,
            )
        ).first()
        if existing:
            raise ValueError("该角色已分配给此用户")
        stmt = USER_CUSTOM_ROLES_TABLE.insert().values(user_id=user_id, role_id=role_id)
        self.db.execute(stmt)
        self.db.commit()
        return {"status": "assigned", "user_id": user_id, "role_id": role_id}

    def get_role_by_id(self, role_id: str) -> Optional[dict]:
        role = self.db.query(CustomRole).filter(CustomRole.id == role_id).first()
        if not role:
            return None
        return self._role_to_dict(role)

    def get_role_by_name(self, name: str) -> Optional[dict]:
        role = self.db.query(CustomRole).filter(CustomRole.name == name).first()
        if not role:
            return None
        return self._role_to_dict(role)

    def _role_to_dict(self, role: CustomRole) -> dict:
        perm_keys = [
            row.permission_key
            for row in self.db.execute(
                ROLE_PERMISSIONS_TABLE.select().where(ROLE_PERMISSIONS_TABLE.c.role_id == role.id)
            ).fetchall()
        ]
        permissions = [p for p in ALL_PERMISSIONS if p["key"] in perm_keys]
        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "role_type": role.role_type,
            "is_active": role.is_active,
            "created_by": role.created_by,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "permissions": permissions,
            "permission_keys": perm_keys,
        }


auth_error_code = "AUTH-001"

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _setup_db():
    TestBase.metadata.create_all(bind=TEST_ENGINE)


def _teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(TestBase.metadata.sorted_tables):
            table.drop(conn, checkfirst=True)
        conn.commit()


def get_admin_user(db: Session) -> TestUser:
    existing = db.query(TestUser).filter(TestUser.username == "admin").first()
    if existing:
        return existing
    admin = TestUser(
        id="admin_test_001",
        username="admin",
        email="admin@devflow.test",
        password_hash="hashed_admin_123",
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_regular_user(db: Session) -> TestUser:
    existing = db.query(TestUser).filter(TestUser.username == "regular_user").first()
    if existing:
        return existing
    user = TestUser(
        id="user_test_002",
        username="regular_user",
        email="user@devflow.test",
        password_hash="hashed_user_123",
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": auth_error_code,
                    "message": str(exc.detail),
                }
            },
            headers=getattr(exc, "headers", None),
        )

    def get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def require_admin(authorization: str = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ", 1)[1]
        if token == "admin_token_valid":
            return {"user_id": "admin_test_001", "username": "admin", "role": "admin"}
        if token == "user_token_valid":
            return {"user_id": "user_test_002", "username": "regular_user", "role": "user"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def require_admin_role(current_user: dict = Depends(require_admin)):
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    @app.post("/api/admin/roles", status_code=201)
    def create_custom_role(
        body: dict,
        current_user: dict = Depends(require_admin_role),
        db: Session = Depends(get_db),
    ):
        name = body.get("name")
        description = body.get("description", "")
        permission_keys = body.get("permission_keys", [])
        if not name or not name.strip():
            raise HTTPException(status_code=422, detail="角色名称不能为空")
        service = CustomRoleService(db)
        try:
            role = service.create_role(name=name, description=description, permission_keys=permission_keys, created_by=current_user["user_id"])
            return {"code": 0, "message": "角色创建成功", "data": role}
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.post("/api/admin/roles/{role_id}/assign")
    def assign_role_to_user(
        role_id: str,
        body: dict,
        current_user: dict = Depends(require_admin_role),
        db: Session = Depends(get_db),
    ):
        user_id = body.get("user_id")
        if not user_id:
            raise HTTPException(status_code=422, detail="user_id is required")
        service = CustomRoleService(db)
        try:
            result = service.assign_role_to_user(user_id=user_id, role_id=role_id)
            return {"code": 0, "message": "角色分配成功", "data": result}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/roles/{role_id}")
    def get_role(role_id: str, db: Session = Depends(get_db)):
        service = CustomRoleService(db)
        role = service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"code": 0, "data": role}

    return app


class TestAdminCreateCustomRole:

    @pytest.fixture(autouse=True)
    def setup_method(self):
        _setup_db()
        self.db = TestSessionLocal()
        self.admin = get_admin_user(self.db)
        self.regular_user = get_regular_user(self.db)
        self.app = _build_app()
        self.client = TestClient(self.app)
        yield
        self.db.close()
        _teardown_db()

    def _admin_headers(self) -> dict:
        return {"Authorization": "Bearer admin_token_valid"}

    def _user_headers(self) -> dict:
        return {"Authorization": "Bearer user_token_valid"}

    def _create_default_role(self, overrides: dict = None) -> dict:
        payload = {
            "name": "自定义测试角色",
            "description": "用于测试的自定义角色",
            "permission_keys": ["project_read", "project_update", "task_create", "task_assign", "workflow_view"],
        }
        if overrides:
            payload.update(overrides)
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        return resp.json()["data"]

    def test_admin_creates_role_returns_201(self):
        payload = {
            "name": "项目管理角色",
            "description": "可管理项目和任务",
            "permission_keys": ["project_read", "project_update", "task_create", "task_assign"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}: {resp.text}"

    def test_response_has_code_zero(self):
        payload = {
            "name": "代码审查角色",
            "description": "可审查代码",
            "permission_keys": ["code_review", "project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "角色创建成功"

    def test_response_contains_role_data(self):
        payload = {
            "name": "QA质检角色",
            "description": "可执行QA检验",
            "permission_keys": ["qa_inspect", "task_review", "project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "QA质检角色"
        assert data["description"] == "可执行QA检验"
        assert data["role_type"] == "custom"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_response_contains_permissions(self):
        payload = {
            "name": "审计角色",
            "description": "审计专用",
            "permission_keys": ["audit_log_view", "project_read", "notification_manage"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "permissions" in data
        assert "permission_keys" in data
        keys = data["permission_keys"]
        assert "audit_log_view" in keys
        assert "project_read" in keys
        assert "notification_manage" in keys
        assert len(data["permissions"]) == 3

    def test_response_time_within_300ms(self):
        payload = {
            "name": "快速创建角色",
            "description": "测试响应时间",
            "permission_keys": ["project_read"],
        }
        self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        start = time.perf_counter()
        resp = self.client.post(
            "/api/admin/roles",
            json={"name": "响应时间测试角色", "description": "test", "permission_keys": ["project_read"]},
            headers=self._admin_headers(),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}"
        assert elapsed_ms <= 300, f"响应时间 {elapsed_ms:.2f}ms 超过 300ms"

    def test_role_persisted_in_database(self):
        payload = {
            "name": "持久化角色",
            "description": "验证数据库持久化",
            "permission_keys": ["project_read", "task_create", "code_review"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        role_id = resp.json()["data"]["id"]

        service = CustomRoleService(self.db)
        role = service.get_role_by_id(role_id)
        assert role is not None
        assert role["name"] == "持久化角色"
        assert role["description"] == "验证数据库持久化"
        assert "project_read" in role["permission_keys"]
        assert "task_create" in role["permission_keys"]
        assert "code_review" in role["permission_keys"]

    def test_role_is_assignable_to_user(self):
        role_data = self._create_default_role()
        role_id = role_data["id"]

        assign_resp = self.client.post(
            f"/api/admin/roles/{role_id}/assign",
            json={"user_id": self.regular_user.id},
            headers=self._admin_headers(),
        )
        assert assign_resp.status_code == 200, f"分配失败: {assign_resp.text}"
        assign_body = assign_resp.json()
        assert assign_body["code"] == 0
        assert assign_body["data"]["status"] == "assigned"
        assert assign_body["data"]["user_id"] == self.regular_user.id
        assert assign_body["data"]["role_id"] == role_id

        row = self.db.execute(
            USER_CUSTOM_ROLES_TABLE.select().where(
                USER_CUSTOM_ROLES_TABLE.c.user_id == self.regular_user.id,
                USER_CUSTOM_ROLES_TABLE.c.role_id == role_id,
            )
        ).first()
        assert row is not None, "数据库中应存在用户-角色关联记录"

    def test_non_admin_gets_403(self):
        payload = {
            "name": "非管理员创建",
            "description": "不应成功",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._user_headers())
        assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}"

    def test_missing_name_returns_422(self):
        payload = {
            "description": "没有名称",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 422

    def test_duplicate_role_name_returns_409(self):
        payload = {
            "name": "唯一角色名称",
            "description": "测试重复",
            "permission_keys": ["project_read"],
        }
        resp1 = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp1.status_code == 201
        resp2 = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp2.status_code == 409

    def test_invalid_permission_key_returns_409(self):
        payload = {
            "name": "无效权限角色",
            "description": "包含无效权限",
            "permission_keys": ["project_read", "nonexistent_key_xyz"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 409

    def test_assign_nonexistent_role_returns_404(self):
        fake_role_id = "nonexistent_role_id_12345"
        resp = self.client.post(
            f"/api/admin/roles/{fake_role_id}/assign",
            json={"user_id": self.regular_user.id},
            headers=self._admin_headers(),
        )
        assert resp.status_code == 404

    def test_assign_role_to_nonexistent_user_returns_404(self):
        role_data = self._create_default_role()
        resp = self.client.post(
            f"/api/admin/roles/{role_data['id']}/assign",
            json={"user_id": "nonexistent_user_id"},
            headers=self._admin_headers(),
        )
        assert resp.status_code == 404

    def test_empty_permission_keys_allowed(self):
        payload = {
            "name": "空权限角色",
            "description": "无任何权限",
            "permission_keys": [],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert len(data["permission_keys"]) == 0

    def test_role_appears_in_database_and_can_be_queried(self):
        role_data = self._create_default_role()
        get_resp = self.client.get(f"/api/roles/{role_data['id']}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["code"] == 0
        assert body["data"]["name"] == "自定义测试角色"
        assert body["data"]["id"] == role_data["id"]

    def test_multiple_roles_can_be_created(self):
        names = ["角色A", "角色B", "角色C"]
        for name in names:
            resp = self.client.post(
                "/api/admin/roles",
                json={"name": name, "description": f"{name}描述", "permission_keys": ["project_read"]},
                headers=self._admin_headers(),
            )
            assert resp.status_code == 201, f"创建 {name} 失败: {resp.text}"
        service = CustomRoleService(self.db)
        for name in names:
            role = service.get_role_by_name(name)
            assert role is not None, f"角色 {name} 应在数据库中"
            assert role["name"] == name

    def test_full_workflow_create_assign_verify(self):
        payload = {
            "name": f"全流程角色_{uuid.uuid4().hex[:6]}",
            "description": "全流程测试: 创建-分配-验证",
            "permission_keys": [
                "project_read", "project_update", "project_create",
                "task_create", "task_assign", "task_review",
                "workflow_view", "workflow_start",
                "code_review", "qa_inspect",
            ],
        }
        create_resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert create_resp.status_code == 201
        role = create_resp.json()["data"]
        assert len(role["permission_keys"]) == 10

        assign_resp = self.client.post(
            f"/api/admin/roles/{role['id']}/assign",
            json={"user_id": self.regular_user.id},
            headers=self._admin_headers(),
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["data"]["status"] == "assigned"

        row = self.db.execute(
            USER_CUSTOM_ROLES_TABLE.select().where(
                USER_CUSTOM_ROLES_TABLE.c.user_id == self.regular_user.id,
                USER_CUSTOM_ROLES_TABLE.c.role_id == role["id"],
            )
        ).first()
        assert row is not None, "用户-角色关联应持久化在数据库中"

        get_resp = self.client.get(f"/api/roles/{role['id']}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()["data"]
        assert fetched["name"] == payload["name"]
        assert fetched["description"] == payload["description"]
        assert len(fetched["permission_keys"]) == 10

    def test_whitespace_only_name_returns_422(self):
        payload = {
            "name": "   ",
            "description": "仅包含空格",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 422

    def test_null_name_returns_422(self):
        payload = {
            "name": None,
            "description": "名称为null",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 422

    def test_created_by_is_admin_id(self):
        payload = {
            "name": "验证创建者角色",
            "description": "验证 created_by 字段",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["created_by"] == self.admin.id, f"期望 created_by={self.admin.id}，实际 {data['created_by']}"

    def test_very_long_name_handled_gracefully(self):
        long_name = "A" * 500
        payload = {
            "name": long_name,
            "description": "超长名称测试",
            "permission_keys": ["project_read"],
        }
        resp = self.client.post("/api/admin/roles", json=payload, headers=self._admin_headers())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == long_name
