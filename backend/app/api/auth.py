#!/usr/bin/env python3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.dependencies import require_admin
from app.schemas.auth import (
    LoginRequest, RegisterRequest, PasswordChangeRequest,
    TokenResponse, UserResponse, UserListResponse, UserUpdateRequest,
)
from app.core.exceptions import InvalidCredentials, UserAlreadyExists, AuthUserNotFoundError, AuthPasswordError
from app.models.user import User
import logging

logger = logging.getLogger("devflow.auth")
router = APIRouter(redirect_slashes=False)


@router.post("/register", tags=["auth"])
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
