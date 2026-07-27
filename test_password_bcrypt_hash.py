import pytest
import bcrypt


def test_password_hash_starts_with_2b():
    """验证 password_hash 以 $2b$ 开头（bcrypt 格式）"""
    raw_password = "MyS3cretP@ssw0rd!"
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")
    assert hash_str.startswith("$2b$"), f"期望以 $2b$ 开头，实际: {hash_str[:10]}..."


def test_salt_length_at_least_16_bytes():
    """验证盐值长度 >= 16 字节"""
    salt = bcrypt.gensalt(rounds=12)
    assert len(salt) >= 16, f"盐值长度不足16字节，实际: {len(salt)}"


def test_original_password_cannot_be_derived_from_hash():
    """验证原始密码不可从哈希反推"""
    raw_password = "MyS3cretP@ssw0rd!"
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")
    assert raw_password not in hash_str, "原始密码不应出现在哈希字符串中"
    assert hash_str != raw_password, "哈希值不应等于原始密码"


def test_hash_is_deterministic_for_same_password_and_salt():
    """验证相同密码和盐值得出相同哈希"""
    raw_password = "MyS3cretP@ssw0rd!"
    salt = bcrypt.gensalt(rounds=12)
    hash1 = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash2 = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    assert hash1 == hash2, "相同密码和盐值应得出相同哈希"


def test_hash_differs_for_different_salt():
    """验证不同盐值得出不同哈希"""
    raw_password = "MyS3cretP@ssw0rd!"
    salt1 = bcrypt.gensalt(rounds=12)
    salt2 = bcrypt.gensalt(rounds=12)
    hash1 = bcrypt.hashpw(raw_password.encode("utf-8"), salt1)
    hash2 = bcrypt.hashpw(raw_password.encode("utf-8"), salt2)
    assert hash1 != hash2, "不同盐值应得出不同哈希"


def test_verify_password_against_hash():
    """验证可使用 bcrypt.checkpw 校验密码"""
    raw_password = "MyS3cretP@ssw0rd!"
    wrong_password = "WrongPassword123"
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    assert bcrypt.checkpw(raw_password.encode("utf-8"), password_hash), "正确密码应验证通过"
    assert not bcrypt.checkpw(wrong_password.encode("utf-8"), password_hash), "错误密码应验证失败"


def test_different_passwords_produce_different_hashes():
    """验证不同密码产生不同哈希"""
    salt = bcrypt.gensalt(rounds=12)
    hash1 = bcrypt.hashpw("Password1".encode("utf-8"), salt)
    hash2 = bcrypt.hashpw("Password2".encode("utf-8"), salt)
    assert hash1 != hash2, "不同密码应产生不同哈希"


def test_unicode_password_handling():
    """验证 Unicode 密码正确处理"""
    raw_password = "密码测试🔒123"
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")
    assert hash_str.startswith("$2b$"), "Unicode 密码哈希也应以 $2b$ 开头"
    assert bcrypt.checkpw(raw_password.encode("utf-8"), password_hash), "Unicode 密码应能正确验证"


def test_empty_password_handling():
    """验证空密码也能哈希"""
    raw_password = ""
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")
    assert hash_str.startswith("$2b$"), "空密码哈希也应以 $2b$ 开头"
    assert bcrypt.checkpw(raw_password.encode("utf-8"), password_hash), "空密码应能正确验证"


def test_hash_format_structure():
    """验证 bcrypt 哈希格式结构：$2b$XX$salt+hash"""
    raw_password = "TestP@ss123"
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")
    parts = hash_str.split("$")
    assert len(parts) == 4, f"bcrypt 哈希应有4段（以$分隔），实际有{len(parts)}段"
    assert parts[0] == "", "第一段应为空"
    assert parts[1] == "2b", f"算法标识应为 2b，实际: {parts[1]}"
    rounds = int(parts[2])
    assert 4 <= rounds <= 31, f"轮次应在 4-31 范围内，实际: {rounds}"
    combined = parts[3]
    assert len(combined) == 53, f"盐值+哈希组合长度应为53，实际: {len(combined)}"
