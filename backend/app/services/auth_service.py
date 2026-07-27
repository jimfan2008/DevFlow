#!/usr/bin/env python3
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_SECONDS = 86400
REFRESH_TOKEN_EXPIRE_SECONDS = 86400 * 7


class AuthService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, extra_claims: Dict[str, Any] = None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS),
            "iat": now,
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "exp": now + timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS),
            "iat": now,
            "type": "refresh",
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_tokens(self, user_id: str, extra_claims: Dict[str, Any] = None) -> dict:
        access_token = self.create_access_token(user_id, extra_claims)
        refresh_token = self.create_refresh_token(user_id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        }

    def verify_token(self, token: str, token_type: str = "access") -> Optional[str]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload.get("sub")
        except ExpiredSignatureError:
            return None
        except JWTError:
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except (ExpiredSignatureError, JWTError):
            return None

    def register(self, username: str, email: str, password: str) -> dict:
        from app.core.exceptions import UserAlreadyExists
        User = self._get_user_model()
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if user:
            raise UserAlreadyExists()
        hashed = self.hash_password(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed,
            role="user",
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        tokens = self.create_tokens(new_user.id, extra_claims={"role": new_user.role})
        return {"user": new_user.to_dict(), "tokens": tokens}

    def login(self, username_or_email: str = None, email: str = None, password: str = "") -> dict:
        from app.core.exceptions import InvalidCredentials
        User = self._get_user_model()
        user = None
        if username_or_email:
            user = self.db.query(User).filter(
                (User.username == username_or_email) | (User.email == username_or_email)
            ).first()
            if not user:
                raise InvalidCredentials()
        elif email:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise InvalidCredentials()
        if not self.verify_password(password, user.password_hash):
            from app.core.exceptions import AuthPasswordError
            raise AuthPasswordError()
        tokens = self.create_tokens(user.id, extra_claims={"role": user.role})
        return {"user": user.to_dict(), "tokens": tokens}

    def refresh_token(self, refresh_token: str) -> dict:
        user_id = self.verify_token(refresh_token, token_type="refresh")
        if not user_id:
            raise ValueError("Invalid refresh token")
        User = self._get_user_model()
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        tokens = self.create_tokens(user_id, extra_claims={"role": user.role})
        return tokens

    def _get_user_model(self):
        from app.models.user import User
        return User
