"""User ORM model - minimal auth scaffold for the MVP (email + password).

Structured so OAuth providers can be added later as additional columns
(e.g. `oauth_provider`, `oauth_subject`) without breaking this table.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAtMixin


class User(Base, CreatedAtMixin):
    """An application user who can authenticate via email + password."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
