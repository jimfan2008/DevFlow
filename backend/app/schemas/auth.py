#!/usr/bin/env python3
"""认证相关 Pydantic 模式"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re


class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def check_login_field(cls, v):
        if v is None:
            pass  # username will be used
        return v


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("password too short, must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("password must contain uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("password must contain lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("password must contain digit")
        return v

    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password mismatch")


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
