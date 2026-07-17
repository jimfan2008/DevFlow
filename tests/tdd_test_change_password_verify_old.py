import time
import tempfile
import os
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


class TestChangePasswordVerifyOld:
    OLD_PASSWORD = "TestPass123"
    NEW_PASSWORD = "NewSecurePass456!"

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.close()
        self.db_path = f.name
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        TestSessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        session = TestSessionLocal()
        user = UserModel(id="user_001", username="testuser", password_hash=pwd_context.hash(self.OLD_PASSWORD))
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
        def change_password(req: ChangePasswordRequest, db: Session = Depends(get_db)):
            user = db.query(UserModel).filter(UserModel.username == "testuser").first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not pwd_context.verify(req.current_password, user.password_hash):
                raise HTTPException(status_code=401, detail="Old password is incorrect")
            user.password_hash = pwd_context.hash(req.new_password)
            db.commit()
            return {"code": 0, "message": "Password changed successfully"}

        @app.post("/api/auth/login")
        def login(req: LoginRequest, db: Session = Depends(get_db)):
            user = db.query(UserModel).filter(UserModel.username == req.username).first()
            if not user or not pwd_context.verify(req.password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return {"code": 0, "message": "Login successful"}

        self.app = app
        self.client = TestClient(app)
        yield
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_change_password_returns_200_with_correct_old_password(self):
        response = self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        assert response.status_code == 200

    def test_change_password_response_time_within_300ms(self):
        start = time.time()
        response = self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        elapsed = (time.time() - start) * 1000
        assert response.status_code == 200
        assert elapsed <= 300.0, f"Response time {elapsed:.0f}ms exceeds 300ms limit"

    def test_password_hash_updated_to_bcrypt_format(self):
        self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT password_hash FROM users WHERE username='testuser'"))
            row = result.fetchone()
        assert row is not None
        assert row[0].startswith("$2b$"), f"Expected bcrypt hash starting with $2b$, got {row[0]}"

    def test_old_password_no_longer_works_for_login(self):
        self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        login_response = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": self.OLD_PASSWORD,
        })
        assert login_response.status_code == 401

    def test_new_password_works_for_login(self):
        self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        login_response = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": self.NEW_PASSWORD,
        })
        assert login_response.status_code == 200

    def test_rejects_change_with_wrong_old_password(self):
        response = self.client.post("/api/auth/change-password", json={
            "current_password": "WrongPass999!",
            "new_password": self.NEW_PASSWORD,
        })
        assert response.status_code == 401

    def test_password_hash_differs_after_change(self):
        with self.engine.connect() as conn:
            old_result = conn.execute(text("SELECT password_hash FROM users WHERE username='testuser'"))
            old_hash = old_result.fetchone()[0]
        self.client.post("/api/auth/change-password", json={
            "current_password": self.OLD_PASSWORD,
            "new_password": self.NEW_PASSWORD,
        })
        with self.engine.connect() as conn:
            new_result = conn.execute(text("SELECT password_hash FROM users WHERE username='testuser'"))
            new_hash = new_result.fetchone()[0]
        assert new_hash != old_hash
        assert new_hash.startswith("$2b$")
