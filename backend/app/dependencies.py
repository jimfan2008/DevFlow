#!/usr/bin/env python3
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Callable
from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.project import ProjectMember
from app.core.exceptions import ForbiddenError


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    auth_service = AuthService(db=db)
    user_id = auth_service.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise ForbiddenError(detail="Admin access required")
    return current_user


def require_project_member(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if current_user.role == "admin":
        return current_user
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    ).first()
    if not member:
        project_creator = db.query(User).join(
            ProjectMember,
            ProjectMember.user_id == User.id,
        ).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.role == "owner",
        ).first()
        if project_creator and project_creator.id == current_user.id:
            return current_user
        raise ForbiddenError(detail="Not a member of this project")
    return current_user
