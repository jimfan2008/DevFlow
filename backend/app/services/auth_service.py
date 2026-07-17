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
            role="viewer",
            status="active",
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

    def github_oauth_login(self, auth_code: str, client_id: str) -> dict:
        """通过 GitHub OAuth 授权码登录 / 注册。

        - 用授权码换取 GitHub access_token
        - 用 access_token 获取 GitHub 用户信息
        - 按邮箱查找本地用户，不存在则自动创建（role='viewer'）
        - 返回 JWT tokens + 用户信息
        """
        import httpx
        from app.config import get_settings as _get_settings
        from app.core.exceptions import GitHubOAuthError

        settings = _get_settings()
        client_secret = settings.GITHUB_CLIENT_SECRET

        # 1. 用授权码换取 GitHub access_token
        token_url = "https://github.com/login/oauth/access_token"
        with httpx.Client() as http:
            resp = http.post(
                token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": auth_code,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200 or "error" in resp.text:
                raise GitHubOAuthError(detail="Failed to exchange authorization code")
            token_data = resp.json()
            github_access_token = token_data.get("access_token", "")
            if not github_access_token:
                raise GitHubOAuthError(detail="No access token returned from GitHub")

            # 2. 获取 GitHub 用户信息
            user_resp = http.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {github_access_token}",
                    "Accept": "application/json",
                },
            )
            if user_resp.status_code != 200:
                raise GitHubOAuthError(detail="Failed to fetch GitHub user info")
            github_user = user_resp.json()

        # 3. 按邮箱查找或创建用户
        User = self._get_user_model()
        github_email = github_user.get("email") or f"gh_{github_user.get('id')}@github.com"
        user = self.db.query(User).filter(User.email == github_email).first()

        if user is None:
            # 首次登录，自动创建账户
            username = github_user.get("login", f"gh_{github_user.get('id')}")
            # 确保用户名唯一：若已存在，附加数字
            existing = self.db.query(User).filter(User.username == username).first()
            if existing:
                username = f"{username}_{github_user.get('id', 'user')}"
            user = User(
                username=username,
                email=github_email,
                password_hash="",  # OAuth 用户无需密码哈希
                role="viewer",
                avatar_url=github_user.get("avatar_url"),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        # 4. 生成 tokens
        tokens = self.create_tokens(user.id, extra_claims={"role": user.role})
        return {"user": user.to_dict(), "tokens": tokens}

    def get_github_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        """生成 GitHub OAuth 授权 URL"""
        from urllib.parse import urlencode
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
