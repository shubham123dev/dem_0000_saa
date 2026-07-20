"""Select the one configured application user directory."""

from __future__ import annotations

from functools import lru_cache

from app.adapters.user.contract import UserDirectory
from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
from app.core.config import get_settings
from app.db.nucleus_user_session import (
    dispose_nucleus_user_engine,
    get_nucleus_user_sessionmaker,
)
from app.repositories.nucleus_user_repository import NucleusUserRepository


@lru_cache
def get_user_directory() -> UserDirectory:
    settings = get_settings()
    if settings.nucleus_user_database_url:
        return NucleusUserRepository(
            get_nucleus_user_sessionmaker(),
            settings,
        )
    if settings.is_sandbox:
        return get_sandbox_user_directory()
    raise RuntimeError(
        "Production requires WORKPLACE_NUCLEUS_USER_DATABASE_URL; "
        "the legacy local users table is no longer supported"
    )


async def dispose_user_directory() -> None:
    if get_settings().nucleus_user_database_url:
        await dispose_nucleus_user_engine()
    get_user_directory.cache_clear()
