import time
import os
import tempfile
import pytest
from passlib.context import CryptContext
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TestChangePasswordVerifyOldPassword:
    """验证用户修改密码时需正确验证原密码"""

    OLD_PASSWORD = "TestPass123"
    NEW_PASSWORD = "NewSecurePass789!"

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.close()
        self.db_path = f.name
        self.engine = create_engine(
            f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.engine)
        TestSessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )
        session = TestSessionLocal()
        user = UserModel(
            id="user_001",
            username="testuser",
            password_hash=pwd_context.hash(self.OLD_PASSWORD),
        )
        session.add(user)
        session.commit()
        session.close()

        app = FastAPI()

        def get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        @app.post("/api/auth/change-password")
        def change_password(
            req: ChangePasswordRequest, db: Session = Depends(get_db)
        ):
            user = (
                db.query(UserModel)
                .filter(UserModel.username == "testuser")
                .first()
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not pwd_context.verify(req.current_password, user.password_hash):
                raise HTTPException(
                    status_code=401, detail="Old password is incorrect"
                )
            user.password_hash = pwd_context.hash(req.new_password)
            db.commit()
            return {"code": 0, "message": "Password changed successfully"}

        @app.post("/api/auth/login")
        def login(req: LoginRequest, db: Session = Depends(get_db)):
            user = (
                db.query(UserModel)
                .filter(UserModel.username == req.username)
                .first()
            )
            if not user or not pwd_context.verify(
                req.password, user.password_hash
            ):
                raise HTTPException(
                    status_code=401, detail="Invalid credentials"
                )
            return {"code": 0, "message": "Login successful"}

        self.app = app
        self.client = TestClient(app)
        yield
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # ── 验收标准 1：HTTP200 返回，响应时间 ≤300ms ──

    def test_change_password_returns_http_200(self):
        """修改密码成功时返回 HTTP 200"""
        response = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        assert response.status_code == 200

    def test_change_password_response_time_within_300ms(self):
        """修改密码响应时间不超过 300ms"""
        start = time.time()
        response = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        elapsed_ms = (time.time() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms <= 300.0, (
            f"响应时间 {elapsed_ms:.0f}ms 超过 300ms 上限"
        )

    # ── 验收标准 2：数据库中 password_hash 已更新为 bcrypt 哈希 ──

    def test_password_hash_updated_to_bcrypt_in_database(self):
        """修改密码后，数据库中的 password_hash 为 bcrypt 格式"""
        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT password_hash FROM users WHERE username='testuser'"
                )
            )
            row = result.fetchone()
        assert row is not None
        stored_hash = row[0]
        assert stored_hash.startswith("$2b$"), (
            f"期望 bcrypt 哈希以 $2b$ 开头，实际为 {stored_hash[:10]}..."
        )

    def test_password_hash_matches_new_password(self):
        """修改密码后，数据库中的 bcrypt 哈希能验证新密码"""
        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT password_hash FROM users WHERE username='testuser'"
                )
            )
            row = result.fetchone()
        stored_hash = row[0]
        assert pwd_context.verify(self.NEW_PASSWORD, stored_hash)

    # ── 验收标准 3：原密码 TestPass123 不再可用登录 ──

    def test_old_password_no_longer_valid_for_login(self):
        """修改密码后，原密码 TestPass123 不能用于登录"""
        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": self.OLD_PASSWORD,
            },
        )
        assert login_response.status_code == 401

    def test_new_password_valid_for_login(self):
        """修改密码后，新密码可以正常登录"""
        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": self.OLD_PASSWORD,
                "new_password": self.NEW_PASSWORD,
            },
        )
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": self.NEW_PASSWORD,
            },
        )
        assert login_response.status_code == 200

    # ── 补充场景：错误的原密码拒绝修改 ──

    def test_wrong_old_password_rejected(self):
        """原密码错误时拒绝修改"""
        response = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword999",
                "new_password": self.NEW_PASSWORD,
            },
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_wrong_old_password_does_not_change_hash(self):
        """原密码错误时数据库中的哈希未被修改"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT password_hash FROM users WHERE username='testuser'"
                )
            )
            original_hash = result.fetchone()[0]

        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword999",
                "new_password": self.NEW_PASSWORD,
            },
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT password_hash FROM users WHERE username='testuser'"
                )
            )
            current_hash = result.fetchone()[0]

        assert current_hash == original_hash

    def test_original_password_still_works_after_failed_change(self):
        """修改密码失败后，原密码仍可正常登录"""
        self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword999",
                "new_password": self.NEW_PASSWORD,
            },
        )
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": self.OLD_PASSWORD,
            },
        )
        assert login_response.status_code == 200
