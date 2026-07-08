"""Shared FastAPI dependencies for the API layer (e.g. current-user auth)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve the authenticated `User` from a Bearer JWT.

    Inputs: token (from the Authorization header), db session.
    Outputs: the matching `User` ORM instance.
    Raises: HTTPException(401) if the token is invalid/expired or the user
        no longer exists - usable as a dependency on future protected routes.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None:
            raise credentials_error
    except JWTError:
        raise credentials_error from None

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_error
    return user
