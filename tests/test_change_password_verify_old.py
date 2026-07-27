import time
import bcrypt
import pytest


class MockUser:
    def __init__(self, user_id, username, password_hash):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash


class InMemoryUserDB:
    def __init__(self):
        self._users: dict[int, MockUser] = {}

    def add_user(self, user: MockUser):
        self._users[user.user_id] = user

    def get_by_id(self, user_id: int) -> MockUser | None:
        return self._users.get(user_id)

    def update_password(self, user_id: int, new_hash: bytes) -> bool:
        if user_id not in self._users:
            return False
        self._users[user_id].password_hash = new_hash
        return True


class AuthService:
    """Simulated auth service. Uses low bcrypt rounds for speed in tests."""

    _BCRYPT_ROUNDS = 4

    def __init__(self, db: InMemoryUserDB):
        self._db = db

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> dict:
        start = time.monotonic()
        user = self._db.get_by_id(user_id)
        if user is None:
            return {"status": 404, "message": "user not found"}
        if not bcrypt.checkpw(
            old_password.encode("utf-8"), user.password_hash
        ):
            elapsed_ms = (time.monotonic() - start) * 1000
            return {
                "status": 403,
                "message": "Old password is incorrect",
                "elapsed_ms": round(elapsed_ms, 2),
            }
        if old_password == new_password:
            elapsed_ms = (time.monotonic() - start) * 1000
            return {
                "status": 400,
                "message": "New password must be different from old password",
                "elapsed_ms": round(elapsed_ms, 2),
            }
        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt(rounds=self._BCRYPT_ROUNDS)
        )
        self._db.update_password(user_id, new_hash)
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "status": 200,
            "message": "password changed successfully",
            "elapsed_ms": round(elapsed_ms, 2),
        }

    def verify_login(self, user_id: int, password: str) -> bool:
        user = self._db.get_by_id(user_id)
        if user is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), user.password_hash)


@pytest.fixture()
def user_db():
    return InMemoryUserDB()


@pytest.fixture()
def auth_service(user_db):
    return AuthService(user_db)


class TestChangePasswordVerifyOld:
    """修改密码——验证原密码"""

    def _create_user(self, auth_service, user_id: int, username: str, password: str) -> MockUser:
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=4))
        user = MockUser(user_id=user_id, username=username, password_hash=pw_hash)
        auth_service._db.add_user(user)
        return user

    # ── 核心正向用例 ──

    def test_change_password_success_within_time_limit(self, auth_service):
        """HTTP200 返回，响应时间 ≤300ms"""
        self._create_user(auth_service, 1, "test_user_1", "TestPass123")
        result = auth_service.change_password(1, "TestPass123", "NewPass456!")
        assert result["status"] == 200
        assert result["message"] == "password changed successfully"
        assert result["elapsed_ms"] <= 300, (
            f"响应时间 {result['elapsed_ms']}ms 超过 300ms"
        )

    def test_password_hash_updated_to_bcrypt(self, auth_service):
        """数据库中 password_hash 已更新为 bcrypt 哈希"""
        self._create_user(auth_service, 2, "test_user_2", "TestPass123")
        auth_service.change_password(2, "TestPass123", "NewPass456!")
        user_after = auth_service._db.get_by_id(2)
        assert user_after is not None
        assert user_after.password_hash.startswith(b"$2"), (
            "password_hash 必须以 $2 开头（bcrypt 格式）"
        )
        assert bcrypt.checkpw(b"NewPass456!", user_after.password_hash), (
            "存储的哈希应能验证新密码 NewPass456!"
        )

    def test_old_password_no_longer_valid(self, auth_service):
        """原密码 TestPass123 不再可用登录"""
        self._create_user(auth_service, 3, "test_user_3", "TestPass123")
        auth_service.change_password(3, "TestPass123", "NewPass456!")
        assert auth_service.verify_login(3, "TestPass123") is False, (
            "原密码 TestPass123 修改后应无法登录"
        )
        assert auth_service.verify_login(3, "NewPass456!") is True, (
            "新密码 NewPass456! 应可正常登录"
        )

    # ── 负向用例 ──

    def test_change_password_wrong_old_password(self, auth_service):
        """原密码错误 → 403"""
        self._create_user(auth_service, 10, "test_user_10", "TestPass123")
        result = auth_service.change_password(10, "WrongPass999", "NewPass456!")
        assert result["status"] == 403
        assert result["message"] == "Old password is incorrect"

    def test_change_password_user_not_found(self, auth_service):
        """用户不存在 → 404"""
        result = auth_service.change_password(9999, "TestPass123", "NewPass456!")
        assert result["status"] == 404
        assert result["message"] == "user not found"

    # ── 边界用例 ──

    def test_change_password_empty_old_password(self, auth_service):
        """原密码为空字符串 → 403"""
        self._create_user(auth_service, 20, "test_user_20", "TestPass123")
        result = auth_service.change_password(20, "", "NewPass456!")
        assert result["status"] == 403
        assert result["message"] == "Old password is incorrect"

    def test_change_password_empty_new_password(self, auth_service):
        """新密码为空字符串 → 200（bcrypt 允许空密码，实际 API 由校验层拦截）"""
        self._create_user(auth_service, 21, "test_user_21", "TestPass123")
        result = auth_service.change_password(21, "TestPass123", "")
        assert result["status"] == 200
        assert auth_service.verify_login(21, "") is True

    def test_change_password_same_old_and_new_password(self, auth_service):
        """新旧密码相同 → 400"""
        self._create_user(auth_service, 30, "test_user_30", "TestPass123")
        result = auth_service.change_password(30, "TestPass123", "TestPass123")
        assert result["status"] == 400
        assert "different" in result["message"].lower()

    def test_change_password_very_long_password(self, auth_service):
        """超长密码（>72 字节被 bcrypt 截断，仍能改密成功）"""
        self._create_user(auth_service, 40, "test_user_40", "TestPass123")
        long_password = "A" * 200
        result = auth_service.change_password(40, "TestPass123", long_password)
        assert result["status"] == 200
        user_after = auth_service._db.get_by_id(40)
        assert bcrypt.checkpw(long_password.encode("utf-8"), user_after.password_hash), (
            "超长密码（被 bcrypt 截断）应仍能验证通过"
        )

    def test_timing_attack_protection_wrong_vs_correct(self, auth_service):
        """时序攻击防护：错误密码与正确密码的响应时间差 ≤50ms"""
        self._create_user(auth_service, 50, "test_user_50", "TestPass123")

        # 错误密码的响应时间
        result_wrong = auth_service.change_password(50, "WrongPass999", "NewPass456!")
        elapsed_wrong = result_wrong["elapsed_ms"]

        # 正确密码的响应时间
        result_correct = auth_service.change_password(50, "TestPass123", "NewPass456!")
        elapsed_correct = result_correct["elapsed_ms"]

        # 两者时间差不应过大（<=50ms），表明不存在明显的时序泄露
        time_diff = abs(elapsed_wrong - elapsed_correct)
        assert time_diff <= 50, (
            f"错误密码与正确密码响应时间差 {time_diff}ms 过大，可能存在时序泄露"
        )
