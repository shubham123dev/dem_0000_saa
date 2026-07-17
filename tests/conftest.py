"""Shared pytest fixtures.

Every test runs against an isolated temporary SQLite database. Tests explicitly
enable the raw mock API before importing the application; runtime defaults keep
that surface disabled unless configured.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
import os

os.environ.setdefault("WORKPLACE_ENABLE_RAW_MOCK_API", "true")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import action_models, orm_models  # noqa: F401
from app.db.base import Base
from app.db.seed import seed
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def engine(tmp_path):
    db_path = tmp_path / "test_sandbox.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def db_session(sessionmaker_) -> AsyncIterator[AsyncSession]:
    async with sessionmaker_() as session:
        yield session


@pytest_asyncio.fixture
async def seeded(sessionmaker_) -> async_sessionmaker[AsyncSession]:
    async with sessionmaker_() as session:
        await seed(session)
    return sessionmaker_


@pytest_asyncio.fixture
async def client(sessionmaker_, seeded) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker_() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Mock-User-Id": "usr_admin_001"}


@pytest.fixture
def reader_headers() -> dict[str, str]:
    return {"X-Mock-User-Id": "usr_member_001"}


@pytest.fixture
def unseated_headers() -> dict[str, str]:
    return {"X-Mock-User-Id": "usr_member_003"}


@pytest.fixture
def invited_headers() -> dict[str, str]:
    return {"X-Mock-User-Id": "usr_invited_001"}


@pytest.fixture
def outsider_headers() -> dict[str, str]:
    return {"X-Mock-User-Id": "usr_outsider_001"}
