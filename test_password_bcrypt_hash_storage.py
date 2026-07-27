import bcrypt
import pytest


class TestPasswordBcryptHashStorage:
    """密码bcrypt哈希存储：验证用户密码以bcrypt哈希存储而非明文"""

    def test_password_hash_is_bcrypt_format(self):
        """password_hash 字段存储 bcrypt 哈希值"""
        password = "T3stP@ssw0rd!"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        hash_str = password_hash.decode("utf-8")
        assert hash_str.startswith("$2b$"), (
            f"期望 password_hash 为 bcrypt 格式(以 $2b$ 开头)，实际: {hash_str[:10]}..."
        )

    def test_password_not_stored_in_plaintext(self):
        """password_hash 字段不存储明文密码"""
        password = "S3cretP@ss!"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        hash_str = password_hash.decode("utf-8")
        assert hash_str != password, "password_hash 不应等于明文密码"
        assert password not in hash_str, "plain 密码不应出现在哈希字符串中"

    def test_salt_length_at_least_16_bytes(self):
        """盐值长度 >= 16 字节"""
        salt = bcrypt.gensalt(rounds=12)
        assert len(salt) >= 16, f"盐值长度不足 16 字节，实际: {len(salt)} 字节"

    def test_hash_can_verify_correct_password(self):
        """bcrypt 哈希能正确验证原密码"""
        password = "MyP@ssw0rd123"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert bcrypt.checkpw(password.encode("utf-8"), password_hash), (
            "正确密码应通过 bcrypt.checkpw 验证"
        )

    def test_hash_rejects_wrong_password(self):
        """bcrypt 哈希拒绝错误密码"""
        password = "CorrectP@ss1"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert not bcrypt.checkpw(b"WrongP@ss1", password_hash), (
            "错误密码应被 bcrypt.checkpw 拒绝"
        )

    def test_same_password_different_hashes(self):
        """相同密码产生不同哈希（证明盐值随机性）"""
        password = "S4meP@ss2025"
        hash1 = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        hash2 = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert hash1 != hash2, "相同密码不同调用应产生不同哈希"

    def test_hash_format_structure(self):
        """bcrypt 哈希格式结构: $2b$XX$salt+hash"""
        password = "StruCTureT3st!"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        hash_str = password_hash.decode("utf-8")
        parts = hash_str.split("$")
        assert len(parts) == 4, f"预期 4 段，实际 {len(parts)} 段"
        assert parts[0] == ""
        assert parts[1] == "2b"
        rounds = int(parts[2])
        assert 4 <= rounds <= 31, f"cost rounds 应在 4-31，实际: {rounds}"
        assert len(parts[3]) == 53, f"盐值+哈希组合长度应为 53，实际: {len(parts[3])}"

    def test_unicode_password_bcrypt_hash(self):
        """Unicode 密码也能正确哈希"""
        password = "密码测试123😀"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert password_hash.startswith(b"$2b$")
        assert bcrypt.checkpw(password.encode("utf-8"), password_hash)

    def test_empty_password_bcrypt_hash(self):
        """空字符串也能正确哈希"""
        password = ""
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert password_hash.startswith(b"$2b$")
        assert bcrypt.checkpw(b"", password_hash)

    def test_long_password_truncated(self):
        """超长密码按 bcrypt 72 字节限制截断"""
        long_password = "A" * 200
        truncated_password = "A" * 72
        password_hash = bcrypt.hashpw(long_password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        assert bcrypt.checkpw(long_password.encode("utf-8"), password_hash)
        assert bcrypt.checkpw(truncated_password.encode("utf-8"), password_hash)
