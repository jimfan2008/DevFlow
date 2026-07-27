import time
import pytest
from dataclasses import dataclass
from typing import Optional
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)


@dataclass
class UserRecord:
    username: str
    password_hash: str


@dataclass
class ChangePasswordResult:
    status_code: int
    error: Optional[str]
    elapsed_ms: float


@dataclass
class LoginResult:
    success: bool
    elapsed_ms: float


class UserRepository:
    def __init__(self):
        self._users: dict[str, UserRecord] = {}

    def add(self, username: str, password_hash: str) -> None:
        self._users[username] = UserRecord(username=username, password_hash=password_hash)

    def get(self, username: str) -> Optional[UserRecord]:
        return self._users.get(username)

    def update_password_hash(self, username: str, new_hash: str) -> None:
        if username in self._users:
            self._users[username].password_hash = new_hash

    def get_password_hash(self, username: str) -> Optional[str]:
        record = self._users.get(username)
        return record.password_hash if record else None


class PasswordService:
    def __init__(self, repository: UserRepository):
        self._repository = repository

    def change_password(self, username: str, old_password: str, new_password: str) -> ChangePasswordResult:
        start = time.perf_counter()
        record = self._repository.get(username)
        if record is None:
            elapsed = (time.perf_counter() - start) * 1000
            return ChangePasswordResult(status_code=404, error="USER_NOT_FOUND", elapsed_ms=elapsed)
        if not pwd_context.verify(old_password, record.password_hash):
            elapsed = (time.perf_counter() - start) * 1000
            return ChangePasswordResult(status_code=403, error="INVALID_OLD_PASSWORD", elapsed_ms=elapsed)
        new_hash = pwd_context.hash(new_password)
        self._repository.update_password_hash(username, new_hash)
        elapsed = (time.perf_counter() - start) * 1000
        return ChangePasswordResult(status_code=200, error=None, elapsed_ms=elapsed)

    def login(self, username: str, password: str) -> LoginResult:
        start = time.perf_counter()
        record = self._repository.get(username)
        if record is None:
            elapsed = (time.perf_counter() - start) * 1000
            return LoginResult(success=False, elapsed_ms=elapsed)
        success = pwd_context.verify(password, record.password_hash)
        elapsed = (time.perf_counter() - start) * 1000
        return LoginResult(success=success, elapsed_ms=elapsed)

    def register(self, username: str, password: str) -> None:
        password_hash = pwd_context.hash(password)
        self._repository.add(username, password_hash)


class TestChangePasswordVerifyOld:
    OLD_PASSWORD = "TestPass123"
    NEW_PASSWORD = "NewPass456!"
    TEST_USER = "testuser"

    def setup_method(self):
        self.repository = UserRepository()
        self.service = PasswordService(self.repository)
        self.service.register(self.TEST_USER, self.OLD_PASSWORD)

    def test_change_password_returns_200_with_correct_old_password(self):
        result = self.service.change_password(self.TEST_USER, self.OLD_PASSWORD, self.NEW_PASSWORD)
        assert result.status_code == 200, f"Expected 200, got {result.status_code}"
        assert result.error is None

    def test_change_password_response_time_within_300ms(self):
        result = self.service.change_password(self.TEST_USER, self.OLD_PASSWORD, self.NEW_PASSWORD)
        assert result.elapsed_ms <= 300.0, f"Response time {result.elapsed_ms}ms exceeds 300ms limit"

    def test_password_hash_updated_to_bcrypt_hash_after_change(self):
        old_hash = self.repository.get_password_hash(self.TEST_USER)
        self.service.change_password(self.TEST_USER, self.OLD_PASSWORD, self.NEW_PASSWORD)
        new_hash = self.repository.get_password_hash(self.TEST_USER)
        assert new_hash is not None
        assert new_hash != old_hash, "password_hash should have changed"
        assert new_hash.startswith("$2b$"), "new password_hash should be bcrypt format"

    def test_old_password_no_longer_works_for_login(self):
        self.service.change_password(self.TEST_USER, self.OLD_PASSWORD, self.NEW_PASSWORD)
        login_result = self.service.login(self.TEST_USER, self.OLD_PASSWORD)
        assert login_result.success is False, "Old password should not work anymore"

    def test_new_password_works_for_login(self):
        self.service.change_password(self.TEST_USER, self.OLD_PASSWORD, self.NEW_PASSWORD)
        login_result = self.service.login(self.TEST_USER, self.NEW_PASSWORD)
        assert login_result.success is True, "New password should work for login"

    def test_rejects_change_with_wrong_old_password(self):
        result = self.service.change_password(self.TEST_USER, "WrongPass99!", self.NEW_PASSWORD)
        assert result.status_code == 403, f"Expected 403, got {result.status_code}"
        assert result.error == "INVALID_OLD_PASSWORD"

    def test_rejects_change_for_nonexistent_user(self):
        result = self.service.change_password("nonexistent", self.OLD_PASSWORD, self.NEW_PASSWORD)
        assert result.status_code == 404, f"Expected 404, got {result.status_code}"
        assert result.error == "USER_NOT_FOUND"

    def test_password_hash_stays_bcrypt_after_multiple_changes(self):
        passwords = [self.NEW_PASSWORD, "AnotherPwd789!", "FinalPwd000!"]
        current_old = self.OLD_PASSWORD
        for new_pwd in passwords:
            result = self.service.change_password(self.TEST_USER, current_old, new_pwd)
            assert result.status_code == 200
            current_hash = self.repository.get_password_hash(self.TEST_USER)
            assert current_hash.startswith("$2b$"), "password_hash must remain bcrypt format"
            current_old = new_pwd
