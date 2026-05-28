import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError, ExpiredSignatureError
from app.config import get_settings

settings = get_settings()

ACCESS_TOKEN_EXPIRE_SECONDS = 86400


def hash_password(password: str) -> str:
    password_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt(rounds=12, prefix=b"2b")
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


get_password_hash = hash_password


def verify_password(plain_password: str, hash_password: str) -> bool:
    password_bytes = plain_password[:72].encode("utf-8")
    hash_bytes = hash_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


def create_access_token(user_id: str, expires_delta: timedelta = None, extra_claims: Dict[str, Any] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS))
    payload = {"sub": user_id, "exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": user_id, "exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (ExpiredSignatureError, JWTError):
        return None
