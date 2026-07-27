import bcrypt
import pytest


def hash_password(password: str, rounds: int = 12) -> bytes:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt)


def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def extract_prefix_and_salt(password_hash: bytes) -> bytes:
    return password_hash[:29]


class TestPasswordBcryptHashStorage:
    def test_password_hash_starts_with_bcrypt_prefix(self):
        password_hash = hash_password("MySecureP@ss123")
        assert password_hash.startswith(b"$2b$"), (
            f"Expected hash to start with $2b$, got {password_hash[:4].decode()}"
        )

    def test_salt_length_at_least_16_bytes(self):
        password_hash = hash_password("AnotherP@ss456")
        salt = extract_prefix_and_salt(password_hash)
        assert len(salt) >= 16, f"Expected salt length >= 16, got {len(salt)}"

    def test_original_password_cannot_be_reversed_from_hash(self):
        password = "SuperSecret!789"
        password_hash = hash_password(password)
        assert password_hash != password.encode("utf-8")
        wrong_guesses = [
            b"SuperSecret!789",
            b"supersecret!789",
            b"SuperSecret!788",
            b"SUPERSECRET!789",
            b"SuperSecret!79",
        ]
        for guess in wrong_guesses:
            assert guess != password_hash, "Hash should not equal any plaintext guess"
        assert bcrypt.checkpw(password.encode("utf-8"), password_hash)

    def test_same_password_produces_different_hashes(self):
        password = "ConsistentP@ss"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2, (
            "bcrypt should produce different hashes for the same password due to random salt"
        )

    def test_wrong_password_rejected(self):
        password = "CorrectP@ss!1"
        password_hash = hash_password(password)
        assert verify_password(password, password_hash)
        assert not verify_password("WrongP@ss!1", password_hash)

    def test_empty_password_still_hashed(self):
        password_hash = hash_password("")
        assert password_hash.startswith(b"$2b$")
        assert verify_password("", password_hash)

    def test_hash_format_structure(self):
        password_hash = hash_password("FormatT3st!", rounds=10)
        parts = password_hash.decode("utf-8").split("$")
        assert parts[0] == ""
        assert parts[1] == "2b"
        cost = int(parts[2])
        assert cost == 10
        assert 4 <= cost <= 31
