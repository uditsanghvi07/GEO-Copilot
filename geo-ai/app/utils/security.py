"""Password hashing and JWT helpers used by the auth scaffold."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Inputs: plain_password (str).
    Outputs: bcrypt hash (str) safe to persist.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Inputs: plain_password (str), hashed_password (str).
    Outputs: True if they match, else False.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token.

    Inputs: subject (typically the user's email/id), expires_minutes
        (defaults to Settings.JWT_EXPIRY_MINUTES).
    Outputs: encoded JWT string.
    """
    expire_delta = timedelta(minutes=expires_minutes or settings.JWT_EXPIRY_MINUTES)
    expire_at = datetime.now(timezone.utc) + expire_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Inputs: token (str).
    Outputs: decoded payload (dict).
    Raises: jose.JWTError if the token is invalid or expired.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise
