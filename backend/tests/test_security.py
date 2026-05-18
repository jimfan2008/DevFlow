#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 安全工具单元测试
测试 JWT 创建/解码、密码哈希/验证
"""

import pytest
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import get_settings


class TestHashPassword:
    """测试 hash_password 函数"""

    def test_hash_password_returns_string(self):
        """哈希密码应返回字符串"""
        hashed = hash_password("testpassword123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self):
        """同一密码的哈希值应不同（盐值随机）"""
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2

    def test_hash_password_empty(self):
        """空密码哈希"""
        hashed = hash_password("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_unicode(self):
        """Unicode 密码哈希"""
        hashed = hash_password("密码123测试")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_long(self):
        """超长密码哈希"""
        long_password = "a" * 10000
        hashed = hash_password(long_password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_special_chars(self):
        """特殊字符密码哈希"""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(special)
        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestVerifyPassword:
    """测试 verify_password 函数"""

    def test_verify_correct_password(self):
        """验证正确密码"""
        hashed = hash_password("testpass123")
        assert verify_password("testpass123", hashed) is True

    def test_verify_wrong_password(self):
        """验证错误密码"""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password(self):
        """验证空密码"""
        hashed = hash_password("nonempty")
        assert verify_password("", hashed) is False

    def test_verify_no_cross_match(self):
        """不同密码不应交叉验证"""
        hash1 = hash_password("password_one")
        hash2 = hash_password("password_two")
        assert verify_password("password_one", hash1) is True
        assert verify_password("password_two", hash1) is False
        assert verify_password("password_one", hash2) is False
        assert verify_password("password_two", hash2) is True

    def test_verify_hash_from_passlib(self):
        """验证 passlib 格式哈希"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        known_hash = pwd_context.hash("knownpassword")
        assert verify_password("knownpassword", known_hash) is True
        assert verify_password("wrong", known_hash) is False


class TestCreateAccessToken:
    """测试 create_access_token 函数"""

    def test_access_token_returns_string(self):
        """访问令牌应返回字符串"""
        token = create_access_token("user_001")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_user_id(self):
        """访问令牌应包含用户ID"""
        token = create_access_token("user_test_123")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user_test_123"
        assert decoded["type"] == "access"

    def test_access_token_has_expiry(self):
        """访问令牌应有过期时间"""
        token = create_access_token("user_001")
        decoded = decode_token(token)
        assert decoded is not None
        assert "exp" in decoded
        assert "iat" in decoded

    def test_access_token_custom_expiry(self):
        """自定义过期时间的访问令牌"""
        expire_delta = timedelta(minutes=5)
        token = create_access_token("user_001", expires_delta=expire_delta)
        decoded = decode_token(token)
        assert decoded is not None
        # 过期时间应在 5 分钟左右
        exp_diff = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc) - datetime.now(timezone.utc)
        assert abs(exp_diff.total_seconds() - 300) < 10  # 允许10秒误差

    def test_access_token_different_users(self):
        """不同用户的令牌解码结果应不同"""
        token1 = create_access_token("user_a")
        token2 = create_access_token("user_b")
        decoded1 = decode_token(token1)
        decoded2 = decode_token(token2)
        assert decoded1["sub"] == "user_a"
        assert decoded2["sub"] == "user_b"

    def test_access_token_is_jwt(self):
        """访问令牌应为 JWT 格式（包含三个点）"""
        token = create_access_token("user_001")
        parts = token.split(".")
        assert len(parts) == 3

    def test_access_token_empty_user_id(self):
        """空用户ID的令牌"""
        token = create_access_token("")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == ""


class TestCreateRefreshToken:
    """测试 create_refresh_token 函数"""

    def test_refresh_token_returns_string(self):
        """刷新令牌应返回字符串"""
        token = create_refresh_token("user_001")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token_contains_user_id(self):
        """刷新令牌应包含用户ID"""
        token = create_refresh_token("user_test_456")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user_test_456"
        assert decoded["type"] == "refresh"

    def test_refresh_token_longer_expiry(self):
        """刷新令牌的过期时间应长于访问令牌"""
        access_token = create_access_token("user_001")
        refresh_token = create_refresh_token("user_001")
        access_decoded = decode_token(access_token)
        refresh_decoded = decode_token(refresh_token)
        # 刷新令牌过期时间应远大于访问令牌（访问令牌默认30分钟，刷新令牌7天）
        assert refresh_decoded["exp"] > access_decoded["exp"]

    def test_refresh_token_different_from_access(self):
        """刷新令牌与访问令牌不应相同"""
        access_token = create_access_token("user_001")
        refresh_token = create_refresh_token("user_001")
        assert access_token != refresh_token

    def test_refresh_token_multiple_users(self):
        """不同用户的刷新令牌"""
        token1 = create_refresh_token("user_x")
        token2 = create_refresh_token("user_y")
        decoded1 = decode_token(token1)
        decoded2 = decode_token(token2)
        assert decoded1["sub"] == "user_x"
        assert decoded2["sub"] == "user_y"


class TestDecodeToken:
    """测试 decode_token 函数"""

    def test_decode_valid_access_token(self):
        """解码有效访问令牌"""
        token = create_access_token("user_001")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user_001"
        assert decoded["type"] == "access"

    def test_decode_valid_refresh_token(self):
        """解码有效刷新令牌"""
        token = create_refresh_token("user_002")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user_002"
        assert decoded["type"] == "refresh"

    def test_decode_expired_token(self):
        """解码过期令牌应返回 None"""
        import jwt
        from app.config import get_settings
        settings = get_settings()
        expired_payload = {
            "sub": "user_001",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        assert decode_token(expired_token) is None

    def test_decode_invalid_token_format(self):
        """解码无效格式令牌应返回 None"""
        assert decode_token("not.a.valid.jwt.token.extra") is None
        assert decode_token("totallyfake") is None
        assert decode_token("") is None

    def test_decode_token_with_wrong_secret(self):
        """使用错误密钥编码的令牌应无法解码"""
        import jwt
        fake_token = jwt.encode(
            {"sub": "user_001", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "iat": datetime.now(timezone.utc), "type": "access"},
            "wrong_secret_key_12345",
            algorithm="HS256"
        )
        assert decode_token(fake_token) is None

    def test_decode_none_input(self):
        """解码 None 应返回 None"""
        assert decode_token(None) is None

    def test_decode_manually_encoded_token(self):
        """手动编码的令牌应正确解码"""
        import jwt
        from app.config import get_settings
        settings = get_settings()
        manual_token = jwt.encode(
            {"sub": "manual_user", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "iat": datetime.now(timezone.utc)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        decoded = decode_token(manual_token)
        assert decoded is not None
        assert decoded["sub"] == "manual_user"


class TestPasswordSecurity:
    """密码安全综合测试"""

    def test_password_never_exposed(self):
        """哈希后的密码不应包含原始密码"""
        hashed = hash_password("my_secret_password")
        assert "my_secret_password" not in hashed

    def test_verification_requires_original(self):
        """只有原始密码才能通过验证"""
        hashed = hash_password("correct_secret")
        assert verify_password("correct_secret", hashed)
        assert not verify_password("correct_secre", hashed)
        assert not verify_password("correct_secrett", hashed)
        assert not verify_password("correct SECRET", hashed)

    def test_bcrypt_scheme_used(self):
        """哈希应使用 bcrypt 算法"""
        hashed = hash_password("test")
        assert "$2b$" in hashed or "$2a$" in hashed or "$2y$" in hashed


class TestSecurityIntegration:
    """安全工具集成测试"""

    def test_full_auth_flow(self):
        """完整的认证流程：哈希 -> 存储 -> 验证"""
        # 注册时哈希
        original_password = "secure_password_123"
        stored_hash = hash_password(original_password)

        # 登录时验证
        assert verify_password(original_password, stored_hash)
        assert not verify_password("wrong_password", stored_hash)

    def test_token_lifecycle(self):
        """令牌生命周期测试"""
        user_id = "integration_user"

        # 创建令牌
        access = create_access_token(user_id)
        refresh = create_refresh_token(user_id)

        # 解码验证
        access_data = decode_token(access)
        refresh_data = decode_token(refresh)

        assert access_data["sub"] == user_id
        assert refresh_data["sub"] == user_id
        assert access_data["type"] == "access"
        assert refresh_data["type"] == "refresh"

    def test_tampered_token_rejected(self):
        """篡改的令牌应被拒绝"""
        import jwt
        from app.config import get_settings
        settings = get_settings()

        # 创建有效令牌
        payload = {
            "sub": "user_001",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        # 篡改令牌载荷（修改用户ID）
        parts = token.split(".")
        # 解码中间部分并修改
        import base64
        payload_part = parts[1]
        # 填充缺失的 base64 填充
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        decoded_payload = base64.urlsafe_b64decode(payload_part)
        modified_payload = decoded_payload.replace(b"user_001", b"hacker")
        # 重新编码
        encoded_payload = base64.urlsafe_b64encode(modified_payload).rstrip(b"=").decode()
        tampered_token = parts[0] + "." + encoded_payload + "." + parts[2]

        assert decode_token(tampered_token) is None
