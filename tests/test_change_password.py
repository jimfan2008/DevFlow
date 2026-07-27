import pytest
import time
import tempfile
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Session

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@pytest.fixture(scope="module")
def db_path():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    yield f.name
    os.unlink(f.name)


@pytest.fixture(scope="module")
def engine(db_path):
    e = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture(scope="module")
def TestingSessionLocal(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def db_session(TestingSessionLocal, engine):
    User.__table__.drop(engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(username="testuser", password_hash=pwd_context.hash("TestPass123"))
    db.add(user)
    db.commit()
    db.close()
    yield


@pytest.fixture
def app(TestingSessionLocal):
    app = FastAPI()

    def get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.post("/change-password/{username}")
    def change_password(username: str, req: ChangePasswordRequest, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not pwd_context.verify(req.old_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Old password is incorrect")
        user.password_hash = pwd_context.hash(req.new_password)
        db.commit()
        return {"message": "Password changed successfully"}

    @app.post("/login")
    def login(req: LoginRequest, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not pwd_context.verify(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"message": "Login successful"}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_change_password_verifies_old_password(client, TestingSessionLocal):
    start = time.time()
    response = client.post("/change-password/testuser", json={
        "old_password": "TestPass123",
        "new_password": "NewPass456"
    })
    elapsed = (time.time() - start) * 1000
    assert response.status_code == 200
    assert elapsed <= 300
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    assert pwd_context.verify("NewPass456", user.password_hash)
    db.close()
    login_response = client.post("/login", json={
        "username": "testuser",
        "password": "TestPass123"
    })
    assert login_response.status_code == 401
    login_response_new = client.post("/login", json={
        "username": "testuser",
        "password": "NewPass456"
    })
    assert login_response_new.status_code == 200
