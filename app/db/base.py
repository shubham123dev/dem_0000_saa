"""SQLAlchemy declarative base and shared metadata.

``Base.metadata`` is the single source of truth for the schema and is imported
by Alembic's migration environment.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
