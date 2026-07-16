"""Shared pytest fixtures.

Every test runs against an **isolated temporary SQLite database** created under
pytest's ``tmp_path``. Tests never touch a developer's local SQLite file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import orm_models  # noqa: F401  (register tables on Base.metadata)
from app.db.base import Base
from app.db.seed import seed
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def engine(tmp_path):
    """An isolated async engine bound to a temp-file SQLite database."""

    db_path = tmp_path / "test_sandbox.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def db_session(sessionmaker_) -> AsyncIterator[AsyncSession]:
    """A session for direct database setup/inspection inside tests."""

    async with sessionmaker_() as session:
        yield session


@pytest_asyncio.fixture
async def seeded(sessionmaker_) -> async_sessionmaker[AsyncSession]:
    """Seed the isolated database with deterministic synthetic data."""

    async with sessionmaker_() as session:
        await seed(session)
    return sessionmaker_


@pytest_asyncio.fixture
async def client(sessionmaker_, seeded) -> AsyncIterator[AsyncClient]:
    """An HTTP client wired to the app using the isolated test database."""

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
    return {"X-Mock-Employee-Id": "emp_admin_001"}


@pytest.fixture
def reader_headers() -> dict[str, str]:
    return {"X-Mock-Employee-Id": "emp_reader_001"}


@pytest.fixture
def outsider_headers() -> dict[str, str]:
    return {"X-Mock-Employee-Id": "emp_outsider_001"}
