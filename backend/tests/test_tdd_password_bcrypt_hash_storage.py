import re
import base64
import bcrypt
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.security import hash_password, verify_password

_BCRYPT_ALPHABET = './ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
_STD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def _bcrypt_b64decode(s: str) -> bytes:
    trans = str.maketrans(_BCRYPT_ALPHABET, _STD_ALPHABET)
    std = s.translate(trans)
    std += '=' * ((4 - len(std) % 4) % 4)
    return base64.b64decode(std)


class TestPasswordBcryptHashStorage:

    @pytest.mark.parametrize("raw_password", [
        "Admin@123",
        "Short!1",
        "A" * 72,
        "A" * 73,
        "密码123!@#中文",
    ])
    def test_hash_starts_with_2b(self, raw_password):
        hashed = hash_password(raw_password)
        assert hashed.startswith("$2b$"), f"哈希值必须以 $2b$ 开头，实际: {hashed[:10]}..."

    @pytest.mark.parametrize("raw_password", [
        "Admin@123",
        "P@ssw0rd!",
        "Complex$tring#2026",
    ])
    def test_hash_format_is_valid_bcrypt(self, raw_password):
        hashed = hash_password(raw_password)
        pattern = r"^\$2b\$[0-9]{2}\$[A-Za-z0-9./]{53}$"
        assert re.match(pattern, hashed), f"哈希值不符合 bcrypt 标准格式: {hashed}"

    @pytest.mark.parametrize("raw_password", [
        "TestP@ss1",
        "AnotherS3cret!",
        "YetAnother#99",
    ])
    def test_salt_length_at_least_16_bytes(self, raw_password):
        hashed = hash_password(raw_password)
        parts = hashed.split("$")
        salt_and_hash = parts[3]
        salt_b64 = salt_and_hash[:22]
        salt_bytes = _bcrypt_b64decode(salt_b64)
        assert len(salt_bytes) >= 16, f"盐值长度不足 16 字节，实际: {len(salt_bytes)}"

    def test_different_passwords_produce_different_hashes(self):
        pw1 = "Password1"
        pw2 = "Password2"
        hash1 = hash_password(pw1)
        hash2 = hash_password(pw2)
        assert hash1 != hash2, "不同密码必须产生不同哈希值"

    def test_same_password_produces_different_hashes_each_time(self):
        pw = "SamePassword"
        hash1 = hash_password(pw)
        hash2 = hash_password(pw)
        assert hash1 != hash2, "相同密码每次哈希必须不同（盐值随机）"

    def test_original_password_not_in_hash(self):
        raw_password = "MySecretP@ssw0rd"
        hashed = hash_password(raw_password)
        assert raw_password not in hashed, "原始密码不得出现在哈希值中"

    def test_hash_is_not_reversible(self):
        raw_password = "Unbreakable#2026"
        hashed = hash_password(raw_password)
        assert hashed != raw_password, "哈希值不得等于原始密码"
        assert len(hashed) > len(raw_password), "哈希值长度应大于原始密码"

    def test_verify_correct_password_returns_true(self):
        raw_password = "CorrectP@ss1"
        hashed = hash_password(raw_password)
        assert verify_password(raw_password, hashed) is True

    def test_verify_wrong_password_returns_false(self):
        raw_password = "RightP@ss1"
        wrong_password = "WrongP@ss2"
        hashed = hash_password(raw_password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password_against_hash_returns_false(self):
        raw_password = "NonEmptyP@ss"
        hashed = hash_password(raw_password)
        assert verify_password("", hashed) is False

    def test_cost_factor_is_set(self):
        raw_password = "CostTest123"
        hashed = hash_password(raw_password)
        parts = hashed.split("$")
        cost = int(parts[2])
        assert 10 <= cost <= 14, f"bcrypt cost 因子不在合理范围内: {cost}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
