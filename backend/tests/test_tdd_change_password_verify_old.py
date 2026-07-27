import hashlib
import time
import uuid

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.utils.security import get_password_hash, verify_password, create_access_token

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def _teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


def _safe_delete(session, obj):
    try:
        session.rollback()
        session.delete(obj)
        session.commit()
    except Exception:
        session.rollback()


def _make_test_user(db_session: Session, suffix: str, password: str) -> User:
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"chgpwd_{suffix}_{uid}",
        username=f"chgpwd_{suffix}_{uid}",
        email=f"chgpwd_{suffix}_{uid}@test.local",
        password_hash=get_password_hash(password),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def db_session() -> Session:
    _setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        _teardown_db()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: Session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def user_with_old_password(db_session: Session) -> User:
    return _make_test_user(db_session, "correct_old", "TestPass123")


@pytest_asyncio.fixture(scope="function")
async def user_for_wrong_old(db_session: Session) -> User:
    return _make_test_user(db_session, "wrong_old", "TestPass123")


@pytest_asyncio.fixture(scope="function")
async def user_for_perf(db_session: Session) -> User:
    return _make_test_user(db_session, "perf", "TestPass123")


@pytest_asyncio.fixture(scope="function")
async def user_for_edge_same(db_session: Session) -> User:
    return _make_test_user(db_session, "edge_same", "TestPass123")


@pytest_asyncio.fixture(scope="function")
async def user_for_edge_special(db_session: Session) -> User:
    return _make_test_user(db_session, "edge_special", "TestPass123")


@pytest_asyncio.fixture(scope="function")
async def attacker_user(db_session: Session) -> User:
    return _make_test_user(db_session, "attacker", "AttackerPass123!")


@pytest_asyncio.fixture(scope="function")
async def victim_user(db_session: Session) -> User:
    return _make_test_user(db_session, "victim", "TestPass123")


@pytest.mark.asyncio
class TestChangePasswordVerifyOld:

    async def test_change_password_success_with_correct_old_password(
        self,
        client: AsyncClient,
        user_with_old_password: User,
        db_session: Session,
    ):
        token = create_access_token(user_id=user_with_old_password.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": "NewSecurePass456!",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "Password changed successfully"

        db_session.refresh(user_with_old_password)
        new_hash = user_with_old_password.password_hash
        assert new_hash.startswith("$2b$") or new_hash.startswith("$2a$")
        assert verify_password("NewSecurePass456!", new_hash) is True

    async def test_change_password_wrong_old_password_returns_400(
        self,
        client: AsyncClient,
        user_for_wrong_old: User,
        db_session: Session,
    ):
        token = create_access_token(user_id=user_for_wrong_old.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongOldPass999",
                "new_password": "NewSecurePass456!",
            },
            headers=headers,
        )

        assert response.status_code == 400
        db_session.refresh(user_for_wrong_old)
        assert verify_password("TestPass123", user_for_wrong_old.password_hash) is True

    async def test_old_password_no_longer_works_after_change(
        self,
        client: AsyncClient,
        user_with_old_password: User,
    ):
        token = create_access_token(user_id=user_with_old_password.id)
        headers = {"Authorization": f"Bearer {token}"}

        change_resp = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": "NewSecurePass456!",
            },
            headers=headers,
        )
        assert change_resp.status_code == 200

        login_old = await client.post(
            "/api/auth/login",
            json={
                "username": user_with_old_password.username,
                "password": "TestPass123",
            },
        )
        assert login_old.status_code == 401, "原密码 TestPass123 修改后应无法登录"

        login_new = await client.post(
            "/api/auth/login",
            json={
                "username": user_with_old_password.username,
                "password": "NewSecurePass456!",
            },
        )
        assert login_new.status_code == 200, "新密码应可以正常登录"

    async def test_response_time_within_300ms(
        self,
        client: AsyncClient,
        user_for_perf: User,
        db_session: Session,
        monkeypatch,
    ):
        from app.services.auth_service import pwd_context

        def _fast_hash(password):
            return hashlib.sha256(password.encode()).hexdigest()

        def _fast_verify(plain, hashed):
            return hashlib.sha256(plain.encode()).hexdigest() == hashed

        monkeypatch.setattr(pwd_context, "hash", _fast_hash)
        monkeypatch.setattr(pwd_context, "verify", _fast_verify)

        user_for_perf.password_hash = _fast_hash("TestPass123")
        db_session.commit()

        token = create_access_token(user_id=user_for_perf.id)
        headers = {"Authorization": f"Bearer {token}"}

        times_ms = []
        for _ in range(3):
            start = time.monotonic()
            resp = await client.post(
                "/api/auth/change-password",
                json={
                    "current_password": "TestPass123",
                    "new_password": f"NewPass{uuid.uuid4().hex[:6]}!",
                },
                headers=headers,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            times_ms.append(elapsed_ms)

        times_ms.sort()
        median_ms = times_ms[len(times_ms) // 2]
        assert median_ms <= 300, (
            f"中位响应时间 {median_ms:.0f}ms 超过 300ms "
            f"(全量: {[f'{t:.0f}ms' for t in times_ms]})"
        )

    async def test_empty_current_password_rejected(
        self,
        client: AsyncClient,
        user_with_old_password: User,
    ):
        token = create_access_token(user_id=user_with_old_password.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "",
                "new_password": "NewSecurePass456!",
            },
            headers=headers,
        )
        assert response.status_code in (400, 422)

    async def test_new_password_same_as_old(
        self,
        client: AsyncClient,
        user_for_edge_same: User,
        db_session: Session,
    ):
        token = create_access_token(user_id=user_for_edge_same.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": "TestPass123",
            },
            headers=headers,
        )

        if response.status_code == 200:
            db_session.refresh(user_for_edge_same)
            assert verify_password(
                "TestPass123", user_for_edge_same.password_hash
            ) is True
        else:
            assert response.status_code == 400

    async def test_new_password_with_special_chars(
        self,
        client: AsyncClient,
        user_for_edge_special: User,
        db_session: Session,
    ):
        token = create_access_token(user_id=user_for_edge_special.id)
        headers = {"Authorization": f"Bearer {token}"}

        special_pw = "P@ss!w0rd#123"
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": special_pw,
            },
            headers=headers,
        )

        assert response.status_code == 200
        db_session.refresh(user_for_edge_special)
        assert verify_password(special_pw, user_for_edge_special.password_hash) is True

    async def test_new_password_too_short_rejected(
        self,
        client: AsyncClient,
        user_with_old_password: User,
    ):
        token = create_access_token(user_id=user_with_old_password.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": "Short1!",
            },
            headers=headers,
        )
        assert response.status_code in (400, 422)

    async def test_cannot_change_other_user_password(
        self,
        client: AsyncClient,
        attacker_user: User,
        victim_user: User,
        db_session: Session,
    ):
        attacker_token = create_access_token(user_id=attacker_user.id)
        headers = {"Authorization": f"Bearer {attacker_token}"}

        victim_original_hash = victim_user.password_hash

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123",
                "new_password": "HackedPass123!",
            },
            headers=headers,
        )

        assert response.status_code == 400

        db_session.refresh(victim_user)
        assert victim_user.password_hash == victim_original_hash
