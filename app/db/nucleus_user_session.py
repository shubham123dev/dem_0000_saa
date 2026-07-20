"""Isolated async SQL Server engine for the production Test_user1 table."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_nucleus_user_engine() -> AsyncEngine:
    global _engine
    settings = get_settings()
    if not settings.nucleus_user_database_url:
        raise RuntimeError("WORKPLACE_NUCLEUS_USER_DATABASE_URL is required")
    if _engine is None:
        _engine = create_async_engine(
            settings.nucleus_user_database_url,
            future=True,
            pool_pre_ping=True,
            pool_recycle=settings.nucleus_user_pool_recycle_seconds,
        )
    return _engine


def get_nucleus_user_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_nucleus_user_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


async def dispose_nucleus_user_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
