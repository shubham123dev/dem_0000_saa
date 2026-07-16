"""Async database engine and session management.

Provides an application engine/sessionmaker plus a FastAPI dependency
(``get_session``). Test suites create their own isolated engines and override
the dependency, so nothing here binds tests to a developer's local database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, future=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async sessionmaker."""

    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an ``AsyncSession`` per request."""

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
