"""Framework-neutral user directory contract.

The real implementation reads and creates users in
``dbmr_Database_Nucleus.dbo.Test_user1``. Password is deliberately absent
from every contract so it cannot enter API, audit, tool, or LLM payloads.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.domain.models import User


class UserDirectoryError(RuntimeError):
    """Base failure raised by a user-directory adapter."""


class UserDirectoryWriteDisabledError(UserDirectoryError):
    """Raised when a caller attempts a production user write while gated."""


class AmbiguousUserEmailError(UserDirectoryError):
    """Raised when EmailID does not identify exactly one production user."""


class UserCreationContractError(UserDirectoryError):
    """Raised when Test_user1 metadata requires fields not configured safely."""


@dataclass(frozen=True)
class CreateUserCommand:
    display_name: str
    email: str
    actor_user_id: str
    user_type_id: int | None = None
    is_active: bool = True
    source: str | None = None
    trusted_defaults: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class UserDirectory(Protocol):
    @property
    def creation_enabled(self) -> bool:
        ...

    async def ping(self) -> None:
        ...

    async def get_by_id(self, user_id: str) -> User | None:
        ...

    async def get_by_email(self, email: str) -> User | None:
        ...

    async def get_many_by_ids(
        self, user_ids: Collection[str]
    ) -> dict[str, User]:
        ...

    async def create_user(self, command: CreateUserCommand) -> User:
        ...
