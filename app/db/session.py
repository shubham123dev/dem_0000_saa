"""Async database engine and session management.

Provides an application engine/sessionmaker plus a FastAPI dependency. SQLite
foreign-key enforcement is enabled on every connection so the mock sandbox
cannot persist invalid organization, user, seat, or report-access references.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_engine(database_url: str) -> AsyncEngine:
    """Create a configured async engine for application and test use."""

    engine = create_async_engine(database_url, future=True)
    _enable_sqlite_foreign_keys(engine)
    return engine


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""

    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url)
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
