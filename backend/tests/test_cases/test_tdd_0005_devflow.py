import time
import uuid
import json
from unittest.mock import patch, Mock

import pytest
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, String, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import jwt as pyjwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)
Base = declarative_base()

SECRET_KEY = "test-secret-key-for-github-oauth-tdd-0005"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 86400
REFRESH_TOKEN_EXPIRE_SECONDS = 86400 * 7
MOCK_GITHUB_CLIENT_ID = "test-github-client-id-0005"
MOCK_GITHUB_CLIENT_SECRET = "test-github-client-secret-0005"
MOCK_GITHUB_ACCESS_TOKEN = "gho_test_access_token_0005_abcdef"
MOCK_GITHUB_USER_ID = 9988776655
MOCK_GITHUB_LOGIN = "tdd-github-user-0005"
MOCK_GITHUB_EMAIL = "tdd-github-user-0005@example.com"
MOCK_GITHUB_AVATAR = "https://avatars.githubusercontent.com/u/9988776655"


class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="viewer")
    status = Column(String, default="active")
    avatar_url = Column(String, nullable=True)


class AuthServiceStandalone:
    def __init__(self, db: Session):
        self.db = db

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, user_id: str, extra_claims: dict = None) -> str:
        now = time.time()
        payload = {
            "sub": user_id,
            "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
            "iat": now,
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)
        return pyjwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        now = time.time()
        payload = {
            "sub": user_id,
            "exp": now + REFRESH_TOKEN_EXPIRE_SECONDS,
            "iat": now,
            "type": "refresh",
        }
        return pyjwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

    def create_tokens(self, user_id: str, extra_claims: dict = None) -> dict:
        return {
            "access_token": self.create_access_token(user_id, extra_claims),
            "refresh_token": self.create_refresh_token(user_id),
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        }

    def github_oauth_login(self, auth_code: str, client_id: str) -> dict:
        if not auth_code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        if client_id != MOCK_GITHUB_CLIENT_ID:
            raise HTTPException(status_code=400, detail="Invalid client_id")
        github_user = {
            "id": MOCK_GITHUB_USER_ID,
            "login": MOCK_GITHUB_LOGIN,
            "email": MOCK_GITHUB_EMAIL,
            "name": "TDD GitHub User 0005",
            "avatar_url": MOCK_GITHUB_AVATAR,
        }
        email = github_user.get("email") or f"gh_{github_user['id']}@github.com"
        user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if user is None:
            username = github_user.get("login", f"gh_{github_user['id']}")
            existing = self.db.query(UserModel).filter(UserModel.username == username).first()
            if existing:
                username = f"{username}_{github_user['id']}"
            user = UserModel(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash="",
                role="viewer",
                status="active",
                avatar_url=github_user.get("avatar_url"),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        tokens = self.create_tokens(user.id, extra_claims={"role": user.role})
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "avatar_url": user.avatar_url,
            },
            "tokens": tokens,
        }


@pytest.fixture
def app():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    app = FastAPI()

    def get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.get("/api/auth/oauth/github")
    def github_oauth_initiate(
        client_id: str = Query(...),
        redirect_uri: str = Query(None),
    ):
        state = str(uuid.uuid4())
        callback_uri = redirect_uri or "http://localhost:8000/api/auth/oauth/github/callback"
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={callback_uri}"
            f"&scope=read:user+user:email"
            f"&state={state}"
        )
        return RedirectResponse(url=auth_url, status_code=307)

    @app.get("/api/auth/oauth/github/callback")
    def github_oauth_callback(
        code: str = Query(...),
        client_id: str = Query(...),
        db: Session = Depends(get_db),
    ):
        auth_service = AuthServiceStandalone(db=db)
        result = auth_service.github_oauth_login(auth_code=code, client_id=client_id)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "user": result["user"],
                "tokens": result["tokens"],
            },
        }

    @app.post("/api/auth/login")
    def login(username: str, password: str, db: Session = Depends(get_db)):
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user or not auth_service.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"code": 0, "message": "Login successful"}

    app.state.test_engine = engine
    app.state.TestSessionLocal = TestSessionLocal
    return app


@pytest.fixture
def client(app):
    return TestClient(app, follow_redirects=False)


class TestGitHubOAuthInitiateRedirect:
    def test_oauth_initiate_returns_307_redirect(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert response.status_code == 307

    def test_redirect_url_contains_github_authorize_endpoint(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        loc = response.headers.get("location", "")
        assert "github.com/login/oauth/authorize" in loc

    def test_redirect_url_contains_client_id(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        loc = response.headers.get("location", "")
        assert f"client_id={MOCK_GITHUB_CLIENT_ID}" in loc

    def test_redirect_url_contains_scope(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        loc = response.headers.get("location", "")
        assert "scope=" in loc
        assert "read:user" in loc
        assert "user:email" in loc

    def test_redirect_url_contains_state_for_csrf(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        loc = response.headers.get("location", "")
        assert "state=" in loc

    def test_redirect_url_with_custom_redirect_uri(self, client):
        custom_uri = "https://myapp.example.com/callback"
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID, "redirect_uri": custom_uri},
        )
        loc = response.headers.get("location", "")
        assert custom_uri in loc

    def test_redirect_response_time_under_1_second(self, client):
        start = time.monotonic()
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        elapsed = (time.monotonic() - start) * 1000
        assert response.status_code == 307
        assert elapsed <= 1000.0


class TestGitHubOAuthCallbackReturnsJWT:
    def test_callback_returns_200(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert response.status_code == 200

    def test_callback_response_has_code_zero(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        data = response.json()
        assert data["code"] == 0

    def test_callback_response_has_tokens(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        tokens = response.json()["data"]["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "Bearer"

    def test_access_token_is_valid_three_part_jwt(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        access_token = response.json()["data"]["tokens"]["access_token"]
        parts = access_token.split(".")
        assert len(parts) == 3

    def test_refresh_token_is_valid_three_part_jwt(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        refresh_token = response.json()["data"]["tokens"]["refresh_token"]
        parts = refresh_token.split(".")
        assert len(parts) == 3

    def test_access_token_decodes_with_sub_and_exp(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        access_token = response.json()["data"]["tokens"]["access_token"]
        decoded = pyjwt.decode(access_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert "sub" in decoded
        assert "exp" in decoded
        assert decoded["type"] == "access"

    def test_token_sub_matches_created_user_id(self, client, app):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        access_token = response.json()["data"]["tokens"]["access_token"]
        decoded = pyjwt.decode(access_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = decoded["sub"]
        session = app.state.TestSessionLocal()
        try:
            result = session.execute(
                text("SELECT id FROM users WHERE id = :uid"),
                {"uid": user_id},
            ).fetchone()
            assert result is not None
        finally:
            session.close()

    def test_callback_response_time_under_1_second(self, client):
        start = time.monotonic()
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        elapsed = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert elapsed <= 1000.0

    def test_callback_response_contains_user_info(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "role" in user
        assert "status" in user

    def test_callback_response_user_matches_github_data(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["email"] == MOCK_GITHUB_EMAIL
        assert user["username"] == MOCK_GITHUB_LOGIN
        assert user["avatar_url"] == MOCK_GITHUB_AVATAR


class TestFirstLoginCreatesViewer:
    def test_first_login_creates_new_user(self, client, app):
        session = app.state.TestSessionLocal()
        try:
            before = session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        finally:
            session.close()
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert response.status_code == 200
        session = app.state.TestSessionLocal()
        try:
            after = session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        finally:
            session.close()
        assert after == before + 1

    def test_new_user_has_viewer_role_in_db(self, client, app):
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        session = app.state.TestSessionLocal()
        try:
            role = session.execute(
                text("SELECT role FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).scalar()
        finally:
            session.close()
        assert role == "viewer"

    def test_new_user_has_viewer_role_in_response(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["role"] == "viewer"

    def test_new_user_has_active_status(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["status"] == "active"

    def test_new_user_has_username_in_response(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["username"] == MOCK_GITHUB_LOGIN

    def test_new_user_has_email_in_response(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["email"] == MOCK_GITHUB_EMAIL

    def test_new_user_has_avatar_url(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user = response.json()["data"]["user"]
        assert user["avatar_url"] == MOCK_GITHUB_AVATAR

    def test_new_user_id_is_uuid_in_db(self, client, app):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        user_id = response.json()["data"]["user"]["id"]
        session = app.state.TestSessionLocal()
        try:
            row = session.execute(
                text("SELECT id FROM users WHERE id = :uid"),
                {"uid": user_id},
            ).fetchone()
        finally:
            session.close()
        assert row is not None

    def test_token_expires_in_86400_seconds(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_auth_code_xyz", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        tokens = response.json()["data"]["tokens"]
        assert tokens["expires_in"] == ACCESS_TOKEN_EXPIRE_SECONDS


class TestDuplicateLoginNoDuplicateUser:
    def test_second_login_does_not_create_new_user(self, client, app):
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_first", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        session = app.state.TestSessionLocal()
        try:
            before = session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).scalar()
        finally:
            session.close()
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_second", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        session = app.state.TestSessionLocal()
        try:
            after = session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).scalar()
        finally:
            session.close()
        assert after == before
        assert after == 1

    def test_second_login_returns_same_user_id(self, client):
        r1 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_a", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        uid1 = r1.json()["data"]["user"]["id"]
        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_b", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        uid2 = r2.json()["data"]["user"]["id"]
        assert uid1 == uid2

    def test_second_login_returns_valid_jwt(self, client):
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_x", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_y", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert r2.status_code == 200
        token = r2.json()["data"]["tokens"]["access_token"]
        parts = token.split(".")
        assert len(parts) == 3

    def test_second_login_role_unchanged(self, client, app):
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_m", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        session = app.state.TestSessionLocal()
        try:
            session.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            )
            session.commit()
        finally:
            session.close()
        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_n", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        role = r2.json()["data"]["user"]["role"]
        assert role == "admin"

    def test_multiple_logins_only_one_user_record(self, client, app):
        for i in range(5):
            client.get(
                "/api/auth/oauth/github/callback",
                params={"code": f"code_{i}", "client_id": MOCK_GITHUB_CLIENT_ID},
            )
        session = app.state.TestSessionLocal()
        try:
            count = session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).scalar()
        finally:
            session.close()
        assert count == 1

    def test_created_at_not_changed_on_relogin(self, client, app):
        r1 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_t1", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert r1.status_code == 200
        session = app.state.TestSessionLocal()
        try:
            row_before = session.execute(
                text("SELECT created_at FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).fetchone()
        finally:
            session.close()
        assert row_before is not None
        client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "code_t2", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        session = app.state.TestSessionLocal()
        try:
            row_after = session.execute(
                text("SELECT created_at FROM users WHERE email = :email"),
                {"email": MOCK_GITHUB_EMAIL},
            ).fetchone()
        finally:
            session.close()
        assert str(row_after[0]) == str(row_before[0])


class TestCallbackMissingParams:
    def test_missing_code_returns_422(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert response.status_code == 422

    def test_missing_client_id_returns_422(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "some_code"},
        )
        assert response.status_code == 422

    def test_both_missing_returns_422(self, client):
        response = client.get("/api/auth/oauth/github/callback")
        assert response.status_code == 422

    def test_empty_code_returns_400(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "", "client_id": MOCK_GITHUB_CLIENT_ID},
        )
        assert response.status_code in (400, 422)

    def test_wrong_client_id_returns_400(self, client):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_code", "client_id": "wrong-client-id"},
        )
        assert response.status_code in (400, 422)


class TestOAuthInitiateMissingParams:
    def test_missing_client_id_returns_422(self, client):
        response = client.get("/api/auth/oauth/github")
        assert response.status_code == 422

    def test_empty_client_id_returns_422(self, client):
        response = client.get(
            "/api/auth/oauth/github",
            params={"client_id": ""},
        )
        assert response.status_code == 422
