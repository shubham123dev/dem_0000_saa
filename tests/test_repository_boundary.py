"""Repository-boundary tests for the standalone Workplace Agent backend."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import RolePermissionORM
from app.domain.enums import Permission


def test_runtime_contains_no_chatbot_adapter_package() -> None:
    assert not (Path("app") / "adapters" / "chatbot").exists()


def test_domain_declares_no_chatbot_permissions() -> None:
    assert all(not permission.value.startswith("chatbot.") for permission in Permission)


async def test_seeded_database_contains_no_chatbot_permissions(
    db_session: AsyncSession,
) -> None:
    permissions = (
        await db_session.scalars(select(RolePermissionORM.permission))
    ).all()
    assert all(not permission.startswith("chatbot.") for permission in permissions)
