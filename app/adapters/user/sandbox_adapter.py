"""In-memory user directory used only by sandbox and isolated tests.

This adapter replaces the old sandbox ``users`` database table. It keeps
tests deterministic without introducing a second production user source.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Collection, Iterable
from datetime import datetime, timezone

from app.adapters.user.contract import CreateUserCommand
from app.domain.enums import UserStatus
from app.domain.models import User


def _normalized_email(value: str) -> str:
    return value.strip().lower()


class SandboxUserDirectory:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._email_index: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @property
    def creation_enabled(self) -> bool:
        return True

    def reset(self, users: Iterable[User]) -> None:
        materialized = tuple(users)
        self._users = {item.id: item for item in materialized}
        self._email_index = {
            _normalized_email(item.email): item.id for item in materialized
        }

    def upsert(self, user: User) -> None:
        previous = self._users.get(user.id)
        if previous is not None:
            self._email_index.pop(_normalized_email(previous.email), None)
        self._users[user.id] = user
        self._email_index[_normalized_email(user.email)] = user.id

    async def ping(self) -> None:
        return None

    async def get_by_id(self, user_id: str) -> User | None:
        return self._users.get(str(user_id))

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._email_index.get(_normalized_email(email))
        return self._users.get(user_id) if user_id is not None else None

    async def get_many_by_ids(
        self, user_ids: Collection[str]
    ) -> dict[str, User]:
        return {
            str(user_id): self._users[str(user_id)]
            for user_id in user_ids
            if str(user_id) in self._users
        }

    async def create_user(self, command: CreateUserCommand) -> User:
        normalized = _normalized_email(command.email)
        async with self._lock:
            existing = await self.get_by_email(normalized)
            if existing is not None:
                return existing
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
            user_id = f"usr_invited_{digest}"
            now = datetime.now(timezone.utc)
            user = User(
                id=user_id,
                display_name=command.display_name,
                email=normalized,
                status=(
                    UserStatus.ACTIVE
                    if command.is_active
                    else UserStatus.DISABLED
                ),
                created_at=now,
                updated_at=now,
            )
            self.upsert(user)
            return user


_sandbox_user_directory = SandboxUserDirectory()


def get_sandbox_user_directory() -> SandboxUserDirectory:
    return _sandbox_user_directory
