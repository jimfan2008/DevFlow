#!/usr/bin/env python3
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.dependencies import require_admin
from app.schemas.auth import (
    LoginRequest, RegisterRequest, PasswordChangeRequest,
    TokenResponse, UserResponse, UserListResponse, UserUpdateRequest,
)
from app.core.exceptions import (
    InvalidCredentials, UserAlreadyExists, AuthUserNotFoundError,
    AuthPasswordError, GitHubOAuthError,
)
from app.models.user import User
from app.config import get_settings
import uuid
import logging

logger = logging.getLogger("devflow.auth")
router = APIRouter(redirect_slashes=False)


# ── GitHub OAuth ─────────────────────────────────────────


@router.get("/oauth/github", tags=["auth", "oauth"])
def github_oauth_initiate(
    client_id: str = Query(..., description="GitHub OAuth App Client ID"),
    redirect_uri: str = Query(None, description="自定义回调地址（可选）"),
):
    """发起 GitHub OAuth 登录，307 重定向到 GitHub 授权页"""
    settings = get_settings()
    state = str(uuid.uuid4())
    callback_uri = redirect_uri or settings.GITHUB_OAUTH_REDIRECT_URI
    auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={callback_uri}&scope=read:user+user:email&state={state}"
    return RedirectResponse(url=auth_url, status_code=307)


@router.get("/oauth/github/callback", tags=["auth", "oauth"])
def github_oauth_callback(
    code: str = Query(..., description="GitHub 授权码"),
    client_id: str = Query(..., description="GitHub OAuth App Client ID"),
    db: Session = Depends(get_db),
):
    """GitHub OAuth 回调：用授权码换取 access_token → 登录/注册 → 返回 JWT"""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    auth_service = AuthService(db=db)
    try:
        result = auth_service.github_oauth_login(auth_code=code, client_id=client_id)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "user": result["user"],
                "tokens": result["tokens"],
            },
        }
    except GitHubOAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.post("/register", tags=["auth"], status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        data.check_passwords_match()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    auth_service = AuthService(db=db)
    try:
        result = auth_service.register(
            username=data.username,
            email=data.email,
            password=data.password,
        )
        return {
            "code": 0,
            "message": "success",
            "data": {
                "user": result["user"],
                "tokens": result["tokens"],
            },
        }
    except UserAlreadyExists:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", tags=["auth"])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username or data.email
    if not username:
        raise HTTPException(status_code=422, detail="username or email is required")
    auth_service = AuthService(db=db)
    try:
        result = auth_service.login(
            username_or_email=username,
            password=data.password,
        )
        return {
            "code": 0,
            "message": "success",
            "data": {
                "user": result["user"],
                "tokens": result["tokens"],
            },
        }
    except (AuthUserNotFoundError, AuthPasswordError, InvalidCredentials):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", tags=["auth"])
def get_me(current_user=Depends(get_current_user)):
    return {
        "code": 0,
        "message": "success",
        "data": {"user": current_user.to_dict()},
    }


@router.put("/me", tags=["auth"])
def update_me(
    data: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    db.commit()
    db.refresh(user)
    return {
        "code": 0,
        "message": "success",
        "data": {"user": user.to_dict()},
    }


@router.patch("/me", tags=["auth"])
def update_me_patch(
    data: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    db.commit()
    db.refresh(user)
    return {
        "code": 0,
        "message": "success",
        "data": {"user": user.to_dict()},
    }


@router.post("/change-password", tags=["auth"])
def change_password(
    data: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    auth_service = AuthService(db=db)

    if not auth_service.verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_002", "message": "Incorrect password"})

    user.password_hash = auth_service.hash_password(data.new_password)
    db.commit()
    return {
        "code": 0,
        "message": "Password changed successfully",
        "data": None,
    }


@router.post("/logout", tags=["auth"])
def logout(current_user=Depends(get_current_user)):
    return {
        "code": 0,
        "message": "Logout successful",
        "data": None,
    }


@router.get("/refresh", tags=["auth"])
def refresh_token(
    token: str,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db=db)
    try:
        tokens = auth_service.refresh_token(token)
        return {
            "code": 0,
            "message": "Token refreshed",
            "data": tokens,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/users", tags=["auth"])
def list_users(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {
        "code": 0,
        "message": "success",
        "data": {"users": [u.to_dict() for u in users], "total": len(users)},
    }
