"""Pydantic schemas for the auth scaffold (register/login)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class UserCreate(BaseModel):
    """Input schema for POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Input schema for POST /auth/login."""

    email: EmailStr
    password: str


class UserRead(ORMBase):
    """Output schema for a User (never includes the password hash)."""

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    """Output schema for a successful login/register, carrying the JWT."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload shape."""

    sub: str
    exp: int
