#!/usr/bin/env python3
"""Apply the Test_user1 replacement vertical slice.

Pinned to shubham123dev/dem_0000_saa main commit:
2e8f9c5afb677d84044d01e39cb4e57acb86cdc6

Usage:
    python apply_test_user1_replacement.py --repo /path/to/dem_0000_saa
    python apply_test_user1_replacement.py --repo . --run-tests
    python apply_test_user1_replacement.py --repo . --run-tests --commit

The script is intentionally fail-fast and idempotent. It never pushes.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

TARGET_SHA = "2e8f9c5afb677d84044d01e39cb4e57acb86cdc6"
BRANCH_NAME = "agent/replace-users-with-test-user1"
COMMIT_MESSAGE = "replace local users with Test_user1 directory"


class PatchError(RuntimeError):
    pass


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(args), cwd=repo, text=True, capture_output=True, check=False
    )
    if check and completed.returncode != 0:
        raise PatchError(
            f"Command failed ({' '.join(args)}):\n{completed.stdout}{completed.stderr}"
        )
    return completed


def read(repo: Path, relative: str) -> str:
    path = repo / relative
    if not path.exists():
        raise PatchError(f"Missing expected file: {relative}")
    return path.read_text(encoding="utf-8")


def write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = dedent(content).lstrip("\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return
    path.write_text(normalized, encoding="utf-8")


def replace_once(repo: Path, relative: str, old: str, new: str) -> None:
    text = read(repo, relative)
    if new in text and old not in text:
        return
    count = text.count(old)
    if count != 1:
        raise PatchError(
            f"Expected exactly one match in {relative}, found {count}:\n{old[:300]}"
        )
    (repo / relative).write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(repo: Path, relative: str, old: str, new: str, *, minimum: int = 1) -> None:
    text = read(repo, relative)
    count = text.count(old)
    if count == 0 and new in text:
        return
    if count < minimum:
        raise PatchError(f"Expected at least {minimum} matches in {relative}, found {count}")
    (repo / relative).write_text(text.replace(old, new), encoding="utf-8")


def remove_once(repo: Path, relative: str, old: str) -> None:
    replace_once(repo, relative, old, "")


def assert_clean_base(repo: Path, allow_newer: bool) -> None:
    if not (repo / ".git").exists():
        raise PatchError(f"Not a git checkout: {repo}")
    head = run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    if head == TARGET_SHA:
        return
    if allow_newer:
        ancestor = run(
            repo, "git", "merge-base", "--is-ancestor", TARGET_SHA, head, check=False
        )
        if ancestor.returncode == 0:
            return
    raise PatchError(
        f"Patch is pinned to {TARGET_SHA}, but checkout is {head}. "
        "Update the patch or pass --allow-newer only when the target commit is an ancestor."
    )


def ensure_branch(repo: Path) -> None:
    branch = run(repo, "git", "branch", "--show-current").stdout.strip()
    if branch in {"main", "master"}:
        existing = run(repo, "git", "branch", "--list", BRANCH_NAME).stdout.strip()
        if existing:
            run(repo, "git", "switch", BRANCH_NAME)
        else:
            run(repo, "git", "switch", "-c", BRANCH_NAME)


def add_new_files(repo: Path) -> None:
    write(
        repo,
        "app/adapters/user/__init__.py",
        '''
        """User-directory boundary backed by Test_user1 in production."""

        from app.adapters.user.contract import CreateUserCommand, UserDirectory

        __all__ = ["CreateUserCommand", "UserDirectory"]
        ''',
    )
    write(
        repo,
        "app/adapters/user/contract.py",
        '''
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
        ''',
    )
    write(
        repo,
        "app/adapters/user/sandbox_adapter.py",
        '''
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
        ''',
    )
    write(
        repo,
        "app/db/nucleus_user_session.py",
        '''
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
        ''',
    )
    write(
        repo,
        "app/repositories/nucleus_user_repository.py",
        '''
        """Production user directory for dbmr_Database_Nucleus.dbo.Test_user1.

        Reads use an explicit safe projection and never select ``Password``.
        Creation is feature-gated and validates the live SQL Server column
        metadata before issuing an INSERT, so unknown NOT NULL requirements fail
        closed instead of being guessed.
        """

        from __future__ import annotations

        import re
        from collections.abc import Collection, Mapping
        from dataclasses import dataclass
        from datetime import datetime, timezone
        from typing import Any

        from sqlalchemy import bindparam, text
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.adapters.user.contract import (
            AmbiguousUserEmailError,
            CreateUserCommand,
            UserCreationContractError,
            UserDirectoryWriteDisabledError,
        )
        from app.core.config import Settings
        from app.domain.enums import UserStatus
        from app.domain.models import User

        _IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        _SAFE_COLUMNS = (
            "UserID",
            "Name",
            "EmailID",
            "IsActive",
            "CreatedDate",
            "ModifiedDate",
        )
        _PROTECTED_CREATE_COLUMNS = {"UserID", "Password"}


        @dataclass(frozen=True)
        class _ColumnMetadata:
            name: str
            type_name: str
            nullable: bool
            identity: bool
            computed: bool
            has_default: bool

            @property
            def database_generated(self) -> bool:
                return self.identity or self.computed or self.type_name in {
                    "timestamp",
                    "rowversion",
                }


        def _quote_identifier(value: str) -> str:
            if not _IDENTIFIER.fullmatch(value):
                raise ValueError(f"Unsafe SQL identifier: {value!r}")
            return f"[{value}]"


        class NucleusUserRepository:
            def __init__(
                self,
                sessionmaker: async_sessionmaker[AsyncSession],
                settings: Settings,
            ) -> None:
                self._sessionmaker = sessionmaker
                self._settings = settings
                self._database = _quote_identifier(settings.nucleus_user_database_name)
                self._schema = _quote_identifier(settings.nucleus_user_schema_name)
                self._table = _quote_identifier(settings.nucleus_user_table_name)
                self._qualified_table = f"{self._database}.{self._schema}.{self._table}"
                self._object_name = (
                    f"{settings.nucleus_user_database_name}."
                    f"{settings.nucleus_user_schema_name}."
                    f"{settings.nucleus_user_table_name}"
                )
                self._metadata_cache: dict[str, _ColumnMetadata] | None = None

            @property
            def creation_enabled(self) -> bool:
                return self._settings.nucleus_user_writes_enabled

            async def ping(self) -> None:
                statement = text(
                    f"SELECT TOP (1) [UserID] FROM {self._qualified_table}"
                )
                async with self._sessionmaker() as session:
                    await session.execute(statement)

            async def get_by_id(self, user_id: str) -> User | None:
                try:
                    numeric_id = int(str(user_id).strip())
                except (TypeError, ValueError):
                    return None
                statement = text(
                    f"SELECT {self._projection()} "
                    f"FROM {self._qualified_table} WHERE [UserID] = :user_id"
                )
                async with self._sessionmaker() as session:
                    row = (await session.execute(statement, {"user_id": numeric_id})).mappings().one_or_none()
                return self._to_user(row) if row is not None else None

            async def get_by_email(self, email: str) -> User | None:
                normalized = email.strip().lower()
                statement = text(
                    f"SELECT TOP (2) {self._projection()} "
                    f"FROM {self._qualified_table} "
                    "WHERE LOWER(LTRIM(RTRIM([EmailID]))) = :email "
                    "ORDER BY [UserID] ASC"
                )
                async with self._sessionmaker() as session:
                    rows = tuple(
                        (await session.execute(statement, {"email": normalized}))
                        .mappings()
                        .all()
                    )
                if len(rows) > 1:
                    raise AmbiguousUserEmailError(
                        "Test_user1 contains more than one row for this EmailID"
                    )
                return self._to_user(rows[0]) if rows else None

            async def get_many_by_ids(
                self, user_ids: Collection[str]
            ) -> dict[str, User]:
                numeric_ids: list[int] = []
                for user_id in dict.fromkeys(str(item) for item in user_ids):
                    try:
                        numeric_ids.append(int(user_id))
                    except ValueError:
                        continue
                result: dict[str, User] = {}
                for start in range(0, len(numeric_ids), 500):
                    chunk = numeric_ids[start : start + 500]
                    statement = text(
                        f"SELECT {self._projection()} FROM {self._qualified_table} "
                        "WHERE [UserID] IN :user_ids"
                    ).bindparams(bindparam("user_ids", expanding=True))
                    async with self._sessionmaker() as session:
                        rows = (
                            await session.execute(statement, {"user_ids": chunk})
                        ).mappings().all()
                    for row in rows:
                        user = self._to_user(row)
                        result[user.id] = user
                return result

            async def create_user(self, command: CreateUserCommand) -> User:
                if not self.creation_enabled:
                    raise UserDirectoryWriteDisabledError(
                        "Test_user1 writes are disabled; set "
                        "WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=true only after "
                        "validating the production creation contract"
                    )
                existing = await self.get_by_email(command.email)
                if existing is not None:
                    return existing
                actor_user_id = self._numeric_actor(command.actor_user_id)
                metadata = await self._column_metadata()
                now = datetime.now(timezone.utc)
                values: dict[str, Any] = dict(self._settings.nucleus_user_create_defaults)
                values.update(dict(command.trusted_defaults))
                if "Password" in values:
                    raise UserCreationContractError(
                        "Password cannot be written through the workplace user adapter"
                    )
                values.update(
                    {
                        "Name": command.display_name,
                        "EmailID": command.email.strip().lower(),
                        "IsActive": command.is_active,
                        "CreatedDate": now,
                        "ModifiedDate": now,
                        "CreatedBy": actor_user_id,
                        "ModifiedBy": actor_user_id,
                    }
                )
                user_type_id = (
                    command.user_type_id
                    if command.user_type_id is not None
                    else self._settings.nucleus_user_default_type_id
                )
                if user_type_id is not None:
                    values["UserTypeID"] = user_type_id
                source = command.source or self._settings.nucleus_user_default_source
                if source is not None:
                    values["userSource"] = source

                unknown = sorted(set(values) - set(metadata))
                if unknown:
                    raise UserCreationContractError(
                        "Configured Test_user1 creation fields do not exist: "
                        + ", ".join(unknown)
                    )
                protected = sorted(set(values) & _PROTECTED_CREATE_COLUMNS)
                if protected:
                    raise UserCreationContractError(
                        "Protected Test_user1 creation fields were supplied: "
                        + ", ".join(protected)
                    )
                insertable = {
                    name: value
                    for name, value in values.items()
                    if not metadata[name].database_generated
                }
                required_missing = sorted(
                    column.name
                    for column in metadata.values()
                    if not column.nullable
                    and not column.database_generated
                    and not column.has_default
                    and (
                        column.name not in insertable
                        or insertable[column.name] is None
                    )
                )
                if "Password" in required_missing:
                    raise UserCreationContractError(
                        "Password is required without a database default. Use the "
                        "official Nucleus user-creation/authentication procedure; "
                        "direct plaintext password insertion is prohibited."
                    )
                if required_missing:
                    raise UserCreationContractError(
                        "Test_user1 requires trusted creation defaults for: "
                        + ", ".join(required_missing)
                    )
                if not insertable:
                    raise UserCreationContractError("No insertable Test_user1 fields")

                columns = list(insertable)
                parameters = {f"p{index}": insertable[name] for index, name in enumerate(columns)}
                column_sql = ", ".join(_quote_identifier(name) for name in columns)
                values_sql = ", ".join(f":p{index}" for index in range(len(columns)))
                statement = text(
                    f"INSERT INTO {self._qualified_table} ({column_sql}) "
                    f"OUTPUT INSERTED.[UserID] VALUES ({values_sql})"
                )
                async with self._sessionmaker() as session:
                    user_id = (await session.execute(statement, parameters)).scalar_one()
                    await session.commit()
                created = await self.get_by_id(str(user_id))
                if created is None:
                    raise UserCreationContractError(
                        "Test_user1 INSERT succeeded but the created user could not be reread"
                    )
                return created

            async def _column_metadata(self) -> dict[str, _ColumnMetadata]:
                if self._metadata_cache is not None:
                    return self._metadata_cache
                database_sys = f"{self._database}.[sys]"
                statement = text(
                    "SELECT c.[name] AS column_name, ty.[name] AS type_name, "
                    "c.[is_nullable], c.[is_identity], c.[is_computed], "
                    "CASE WHEN dc.[object_id] IS NULL THEN 0 ELSE 1 END AS has_default "
                    f"FROM {database_sys}.[columns] AS c "
                    f"JOIN {database_sys}.[types] AS ty "
                    "ON ty.[user_type_id] = c.[user_type_id] "
                    f"LEFT JOIN {database_sys}.[default_constraints] AS dc "
                    "ON dc.[parent_object_id] = c.[object_id] "
                    "AND dc.[parent_column_id] = c.[column_id] "
                    "WHERE c.[object_id] = OBJECT_ID(:object_name)"
                )
                async with self._sessionmaker() as session:
                    rows = (
                        await session.execute(statement, {"object_name": self._object_name})
                    ).mappings().all()
                if not rows:
                    raise UserCreationContractError(
                        f"Could not inspect Test_user1 metadata for {self._object_name}"
                    )
                self._metadata_cache = {
                    str(row["column_name"]): _ColumnMetadata(
                        name=str(row["column_name"]),
                        type_name=str(row["type_name"]).lower(),
                        nullable=bool(row["is_nullable"]),
                        identity=bool(row["is_identity"]),
                        computed=bool(row["is_computed"]),
                        has_default=bool(row["has_default"]),
                    )
                    for row in rows
                }
                return self._metadata_cache

            @staticmethod
            def _numeric_actor(actor_user_id: str) -> int:
                try:
                    return int(str(actor_user_id).strip())
                except (TypeError, ValueError) as exception:
                    raise UserCreationContractError(
                        "Production user creation requires a numeric Test_user1 actor UserID"
                    ) from exception

            @staticmethod
            def _projection() -> str:
                return ", ".join(_quote_identifier(name) for name in _SAFE_COLUMNS)

            @staticmethod
            def _to_user(row: Mapping[str, Any]) -> User:
                active = row.get("IsActive")
                return User(
                    id=str(row["UserID"]),
                    display_name=str(row.get("Name") or "").strip(),
                    email=str(row.get("EmailID") or "").strip(),
                    status=(
                        UserStatus.ACTIVE if active is True or active == 1 else UserStatus.DISABLED
                    ),
                    created_at=row.get("CreatedDate"),
                    updated_at=row.get("ModifiedDate"),
                )
        ''',
    )
    write(
        repo,
        "app/adapters/user/provider.py",
        '''
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
        ''',
    )

def patch_configuration(repo: Path) -> None:
    replace_once(
        repo,
        "pyproject.toml",
        '    "aiosqlite>=0.19",\n',
        '    "aiosqlite>=0.19",\n    "aioodbc>=0.5",\n    "pyodbc>=5.1",\n',
    )
    replace_once(
        repo,
        "app/core/config.py",
        '''    environment: str = "sandbox"
    enable_raw_mock_api: bool = False

    agent_model_provider: str | None = None
''',
        '''    environment: str = "sandbox"
    enable_raw_mock_api: bool = False

    # Test_user1 is the only production user source. Keep its connection
    # separate from the Workplace database so Alembic never manages it.
    nucleus_user_database_url: str | None = None
    nucleus_user_database_name: str = "dbmr_Database_Nucleus"
    nucleus_user_schema_name: str = "dbo"
    nucleus_user_table_name: str = "Test_user1"
    nucleus_user_writes_enabled: bool = False
    nucleus_user_default_type_id: int | None = None
    nucleus_user_default_source: str | None = "workplace_agent"
    nucleus_user_create_defaults: dict[str, str | int | bool | None] = Field(
        default_factory=dict
    )
    nucleus_user_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)

    agent_model_provider: str | None = None
''',
    )


def patch_local_models(repo: Path) -> None:
    remove_once(
        repo,
        "app/db/orm_models.py",
        '''class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    memberships: Mapped[list["OrganizationMembershipORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


''',
    )
    replace_once(
        repo,
        "app/db/orm_models.py",
        "from sqlalchemy.orm import Mapped, mapped_column, relationship\n",
        "from sqlalchemy.orm import Mapped, mapped_column\n",
    )
    replace_all(
        repo,
        "app/db/orm_models.py",
        '''    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
''',
        '''    # String form of the canonical Test_user1.UserID. Cross-database
    # referential validity is enforced by the user-directory boundary.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
''',
        minimum=2,
    )
    remove_once(
        repo,
        "app/db/orm_models.py",
        '    user: Mapped["UserORM"] = relationship(back_populates="memberships")\n\n',
    )

    for relative, old, new in (
        (
            "app/db/action_models.py",
            '''    requested_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
''',
            '''    requested_by_user_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
''',
        ),
        (
            "app/db/action_models.py",
            '    decided_by_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)\n',
            '    decided_by_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)\n',
        ),
        (
            "app/db/action_models.py",
            '''    executed_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
''',
            '''    executed_by_user_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
''',
        ),
        (
            "app/db/action_models.py",
            '''    created_by_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
    )
''',
            '''    created_by_user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
''',
        ),
        (
            "app/db/agent_run_models.py",
            '''    created_by_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
''',
            '''    created_by_user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
''',
        ),
        (
            "app/db/agent_run_models.py",
            '''    requested_by_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
''',
            '''    requested_by_user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
''',
        ),
        (
            "app/db/workplace_resource_models.py",
            '''    deleted_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
''',
            '''    deleted_by_user_id: Mapped[str] = mapped_column(String, nullable=False)
''',
        ),
        (
            "app/db/nucleus_admin_models.py",
            '''    workplace_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
''',
            '''    workplace_user_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
''',
        ),
    ):
        replace_once(repo, relative, old, new)


def replace_user_repository(repo: Path) -> None:
    write(
        repo,
        "app/repositories/user_repository.py",
        '''
        """User facade combining Test_user1 identity with local access sidecars."""

        from __future__ import annotations

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.adapters.user.contract import UserDirectory
        from app.adapters.user.provider import get_user_directory
        from app.db.orm_models import OrganizationMembershipORM, RolePermissionORM
        from app.domain.enums import MembershipStatus
        from app.domain.models import User


        class UserRepository:
            def __init__(
                self,
                session: AsyncSession,
                user_directory: UserDirectory | None = None,
            ) -> None:
                self._session = session
                self._users = user_directory or get_user_directory()

            async def get_by_id(self, user_id: str) -> User | None:
                return await self._users.get_by_id(user_id)

            async def get_by_email(self, email: str) -> User | None:
                return await self._users.get_by_email(email)

            async def get_active_roles(self, user_id: str, organization_id: str) -> list[str]:
                """Return roles from the user's active local organization membership."""

                stmt = select(OrganizationMembershipORM.role).where(
                    OrganizationMembershipORM.user_id == str(user_id),
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.membership_status
                    == MembershipStatus.ACTIVE.value,
                )
                result = await self._session.execute(stmt)
                return list(result.scalars().all())

            async def get_permissions_for_roles(self, roles: list[str]) -> set[str]:
                if not roles:
                    return set()
                stmt = select(RolePermissionORM.permission).where(
                    RolePermissionORM.role.in_(roles)
                )
                result = await self._session.execute(stmt)
                return set(result.scalars().all())

            async def list_memberships(
                self, organization_id: str
            ) -> list[tuple[User, OrganizationMembershipORM]]:
                """Hydrate organization memberships from the sole user directory."""

                statement = (
                    select(OrganizationMembershipORM)
                    .where(OrganizationMembershipORM.organization_id == organization_id)
                    .order_by(OrganizationMembershipORM.id.asc())
                )
                memberships = tuple(
                    (await self._session.execute(statement)).scalars().all()
                )
                users = await self._users.get_many_by_ids(
                    tuple(item.user_id for item in memberships)
                )
                # This mirrors the old inner join: stale references are not exposed.
                return [
                    (users[item.user_id], item)
                    for item in memberships
                    if item.user_id in users
                ]
        ''',
    )


def patch_dependencies(repo: Path) -> None:
    replace_once(
        repo,
        "app/api/dependencies.py",
        "from app.adapters.nucleus.contract import NucleusOrganizationGateway\n",
        '''from app.adapters.nucleus.contract import NucleusOrganizationGateway
from app.adapters.user.contract import UserDirectory
from app.adapters.user.provider import get_user_directory as provide_user_directory
''',
    )
    replace_once(
        repo,
        "app/api/dependencies.py",
        '''SessionDep = Annotated[AsyncSession, Depends(get_session)]
MOCK_USER_HEADER = "X-Mock-User-Id"


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)
''',
        '''SessionDep = Annotated[AsyncSession, Depends(get_session)]
MOCK_USER_HEADER = "X-Mock-User-Id"


def get_user_directory() -> UserDirectory:
    return provide_user_directory()


UserDirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]


def get_user_repository(
    session: SessionDep,
    user_directory: UserDirectoryDep,
) -> UserRepository:
    return UserRepository(session, user_directory)
''',
    )
    replace_once(
        repo,
        "app/api/action_dependencies.py",
        '''    SessionDep,
    VersionedOrganizationMutationGatewayDep,
    get_audit_repository,
    get_user_repository,
)
''',
        '''    SessionDep,
    UserDirectoryDep,
    VersionedOrganizationMutationGatewayDep,
    get_audit_repository,
    get_user_repository,
)
''',
    )
    replace_once(
        repo,
        "app/api/action_dependencies.py",
        '''def get_agent_action_handlers(
    session: SessionDep,
    nucleus: NucleusOrganizationGatewayDep,
    organization_mutations: VersionedOrganizationMutationGatewayDep,
) -> dict[str, AgentActionHandler]:
    resources = OperationalResourceService(session)
''',
        '''def get_agent_action_handlers(
    session: SessionDep,
    nucleus: NucleusOrganizationGatewayDep,
    organization_mutations: VersionedOrganizationMutationGatewayDep,
    user_directory: UserDirectoryDep,
) -> dict[str, AgentActionHandler]:
    resources = OperationalResourceService(session, user_directory)
''',
    )
    replace_once(
        repo,
        "app/api/action_dependencies.py",
        '''    workplace_workflows = WorkplaceWorkflowService(
        session, WorkplaceResourceRegistry()
    )
''',
        '''    workplace_workflows = WorkplaceWorkflowService(
        session, WorkplaceResourceRegistry(), user_directory
    )
''',
    )

def patch_operational_user_actions(repo: Path) -> None:
    replace_once(
        repo,
        "app/services/operational_resource_service.py",
        "from datetime import datetime, timezone\nimport hashlib\nimport uuid\n",
        "from datetime import datetime, timezone\nimport uuid\n",
    )
    replace_once(
        repo,
        "app/services/operational_resource_service.py",
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
        '''from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import CreateUserCommand, UserDirectory
from app.adapters.user.provider import get_user_directory
''',
    )
    replace_once(
        repo,
        "app/services/operational_resource_service.py",
        '''    ReportORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    ReportORM,
    SeatAssignmentORM,
)
''',
    )
    replace_once(
        repo,
        "app/services/operational_resource_service.py",
        '''    SeatAssignmentStatus,
    SeatPoolStatus,
    UserStatus,
)
''',
        '''    SeatAssignmentStatus,
    SeatPoolStatus,
)
''',
    )
    replace_once(
        repo,
        "app/services/operational_resource_service.py",
        '''class OperationalResourceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect_invitation(self, organization_id: str, email: str) -> dict:
        user = await self._session.scalar(select(UserORM).where(UserORM.email == email))
        membership = None
        if user is not None:
            membership = await self._membership(organization_id, user.id)
        return {
            "user_id": user.id if user else None,
            "membership_status": membership.membership_status if membership else None,
            "role": membership.role if membership else None,
            "version": membership.version if membership else 0,
        }

    async def invite_user(
        self,
        *,
        organization_id: str,
        email: str,
        display_name: str,
        role: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_invitation(organization_id, email)
        if state["version"] != expected_version or state["membership_status"] is not None:
            return None
        user_id = state["user_id"] or self._user_id_for_email(email)
        if state["user_id"] is None:
            self._session.add(
                UserORM(
                    id=user_id,
                    display_name=display_name,
                    email=email,
                    status=UserStatus.ACTIVE.value,
                )
            )
        self._session.add(
            OrganizationMembershipORM(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                membership_status=MembershipStatus.INVITED.value,
                version=1,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return None
        return {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "role": role,
            "membership_status": MembershipStatus.INVITED.value,
            "version": 1,
        }
''',
        '''class OperationalResourceService:
    def __init__(
        self,
        session: AsyncSession,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._users = user_directory or get_user_directory()

    async def inspect_invitation(self, organization_id: str, email: str) -> dict:
        user = await self._users.get_by_email(email)
        membership = None
        if user is not None:
            membership = await self._membership(organization_id, user.id)
        return {
            "user_id": user.id if user else None,
            "membership_status": membership.membership_status if membership else None,
            "role": membership.role if membership else None,
            "version": membership.version if membership else 0,
            "creation_enabled": self._users.creation_enabled,
        }

    async def invite_user(
        self,
        *,
        organization_id: str,
        email: str,
        display_name: str,
        role: str,
        requested_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_invitation(organization_id, email)
        if state["version"] != expected_version or state["membership_status"] is not None:
            return None
        user = await self._users.get_by_email(email)
        if user is None:
            user = await self._users.create_user(
                CreateUserCommand(
                    display_name=display_name,
                    email=email,
                    actor_user_id=requested_by_user_id,
                )
            )
        self._session.add(
            OrganizationMembershipORM(
                organization_id=organization_id,
                user_id=user.id,
                role=role,
                membership_status=MembershipStatus.INVITED.value,
                version=1,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return None
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": role,
            "membership_status": MembershipStatus.INVITED.value,
            "version": 1,
        }
''',
    )
    remove_once(
        repo,
        "app/services/operational_resource_service.py",
        '''
    @staticmethod
    def _user_id_for_email(email: str) -> str:
        digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:20]
        return f"usr_invited_{digest}"
''',
    )
    replace_once(
        repo,
        "app/agent/action_handlers.py",
        '''        if state["membership_status"] is not None:
            raise ValueError("User already has an organization membership")
''',
        '''        if state["membership_status"] is not None:
            raise ValueError("User already has an organization membership")
        if state["user_id"] is None and not state["creation_enabled"]:
            raise ValueError("Production user creation is not configured")
''',
    )
    replace_once(
        repo,
        "app/agent/action_handlers.py",
        '''            display_name=proposal.arguments["display_name"],
            role=proposal.arguments["role"],
            expected_version=proposal.observed_resource_version,
''',
        '''            display_name=proposal.arguments["display_name"],
            role=proposal.arguments["role"],
            requested_by_user_id=proposal.requested_by_user_id,
            expected_version=proposal.observed_resource_version,
''',
    )


def patch_workflows(repo: Path) -> None:
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
        '''from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import CreateUserCommand, UserDirectory
from app.adapters.user.provider import get_user_directory
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''    ReportORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    ReportORM,
    SeatAssignmentORM,
)
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''    SeatAssignmentStatus,
    SeatPoolStatus,
    UserStatus,
)
''',
        '''    SeatAssignmentStatus,
    SeatPoolStatus,
)
''',
    )
    remove_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''
def _user_id_for_email(email: str) -> str:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:20]
    return f"usr_invited_{digest}"

''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''    def __init__(
        self,
        session: AsyncSession,
        registry: WorkplaceResourceRegistry | None = None,
    ) -> None:
        self._session = session
        self._registry = registry or WorkplaceResourceRegistry()
''',
        '''    def __init__(
        self,
        session: AsyncSession,
        registry: WorkplaceResourceRegistry | None = None,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._registry = registry or WorkplaceResourceRegistry()
        self._users = user_directory or get_user_directory()
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        user = await self._session.scalar(select(UserORM).where(UserORM.email == email))
        membership = None
        if user is not None:
''',
        '''        user = await self._users.get_by_email(email)
        if user is not None and not user.is_active:
            raise ValueError("Production user is disabled")
        if user is None and not self._users.creation_enabled:
            raise ValueError("Production user creation is not configured")
        membership = None
        if user is not None:
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        user_id = user.id if user is not None else _user_id_for_email(email)
        before = {
            "user_id": user_id if user is not None else None,
            "user_status": user.status if user is not None else None,
''',
        '''        # Keep preparation stable if a prior execution created Test_user1 but
        # failed before the local membership transaction committed.
        user_id = membership.user_id if membership is not None else email
        seat_lookup_user_id = user.id if user is not None else user_id
        before = {
            "user_id": membership.user_id if membership is not None else None,
            "user_status": (
                user.status.value if membership is not None and user is not None else None
            ),
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                    SeatAssignmentORM.user_id == user_id,
                    SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
''',
        '''                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                    SeatAssignmentORM.user_id == seat_lookup_user_id,
                    SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        after = {
            "user_id": user_id,
            "user_status": UserStatus.ACTIVE.value,
''',
        '''        after = {
            "user_id": membership.user_id if membership is not None else None,
            "user_status": "active",
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        now = _utcnow()
        email = proposal.arguments["email"]
        user = await self._session.scalar(select(UserORM).where(UserORM.email == email))
        if user is None:
            user = UserORM(
                id=_user_id_for_email(email),
                display_name=proposal.arguments["display_name"],
                email=email,
                status=UserStatus.ACTIVE.value,
                created_at=now,
                updated_at=now,
            )
            self._session.add(user)
            await self._session.flush()
        else:
            user.display_name = proposal.arguments["display_name"]
            user.status = UserStatus.ACTIVE.value
            user.updated_at = now

''',
        '''        now = _utcnow()
        email = proposal.arguments["email"]
        user = await self._users.get_by_email(email)
        if user is None:
            user = await self._users.create_user(
                CreateUserCommand(
                    display_name=proposal.arguments["display_name"],
                    email=email,
                    actor_user_id=executor_user_id,
                )
            )
        if not user.is_active:
            raise ValueError("Production user is disabled")

''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        user = await self._session.scalar(
            select(UserORM).where(UserORM.email == proposal.arguments["email"])
        )
''',
        '''        user = await self._users.get_by_email(proposal.arguments["email"])
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/workflows.py",
        '''        user = await self._session.get(UserORM, user_id)
        if user is None:
            raise ValueError("Organization user was not found")
''',
        '''        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ValueError("Organization user was not found")
''',
    )


def patch_run_runtime(repo: Path) -> None:
    replace_once(
        repo,
        "app/agent/run_runtime.py",
        "from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter\n",
        '''from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.adapters.user.provider import get_user_directory
''',
    )
    replace_once(
        repo,
        "app/agent/run_runtime.py",
        '''    user_repository = get_user_repository(session)
    audit_repository = get_audit_repository(session)
''',
        '''    user_directory = get_user_directory()
    user_repository = get_user_repository(session, user_directory)
    audit_repository = get_audit_repository(session)
''',
    )
    replace_once(
        repo,
        "app/agent/run_runtime.py",
        '''        nucleus_gateway,
        organization_gateway,
    )
''',
        '''        nucleus_gateway,
        organization_gateway,
        user_directory,
    )
''',
    )
    replace_once(
        repo,
        "app/agent/run_runtime.py",
        '''        relationship_service=WorkplaceRelationshipService(
            session,
            resource_registry,
            operation_router,
        ),
''',
        '''        relationship_service=WorkplaceRelationshipService(
            session,
            resource_registry,
            operation_router,
            user_directory=user_directory,
        ),
''',
    )

def patch_user_read_surfaces(repo: Path) -> None:
    replace_once(
        repo,
        "app/workplace_resources/registry.py",
        '''    RolePermissionORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    RolePermissionORM,
    SeatAssignmentORM,
)
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/registry.py",
        '''                orm_type=UserORM,
                id_attribute="id",
''',
        '''                # Test_user1 is exposed through the dedicated user adapter,
                # never through the local Workplace SQLAlchemy metadata.
                orm_type=None,
                id_attribute="id",
''',
    )

    replace_once(
        repo,
        "app/workplace_resources/relationships.py",
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
        '''from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import UserDirectory
from app.adapters.user.provider import get_user_directory
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/relationships.py",
        '''    ReportORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    ReportORM,
    SeatAssignmentORM,
)
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/relationships.py",
        '''        operation_router: WorkplaceOperationRouter | None = None,
        relation_registry: WorkplaceRelationRegistry | None = None,
    ) -> None:
        self._session = session
''',
        '''        operation_router: WorkplaceOperationRouter | None = None,
        relation_registry: WorkplaceRelationRegistry | None = None,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._users = user_directory or get_user_directory()
''',
    )
    replace_once(
        repo,
        "app/workplace_resources/relationships.py",
        '''            if relationship == "user":
                user = await self._session.get(UserORM, membership.user_id)
                return (user,) if user is not None else ()
''',
        '''            if relationship == "user":
                user = await self._users.get_by_id(membership.user_id)
                return (user,) if user is not None else ()
''',
    )

    replace_once(
        repo,
        "app/repositories/action_control_repository.py",
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
        '''from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import UserDirectory
from app.adapters.user.provider import get_user_directory
''',
    )
    remove_once(
        repo,
        "app/repositories/action_control_repository.py",
        "from app.db.orm_models import UserORM\n",
    )
    replace_once(
        repo,
        "app/repositories/action_control_repository.py",
        '''class ActionControlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
''',
        '''class ActionControlRepository:
    def __init__(
        self,
        session: AsyncSession,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._users = user_directory or get_user_directory()
''',
    )
    replace_once(
        repo,
        "app/repositories/action_control_repository.py",
        '''    async def user_label(self, user_id: str) -> str:
        result = await self._session.execute(
            select(UserORM.display_name).where(UserORM.id == user_id)
        )
        value = result.scalar_one_or_none()
        return value or "Workspace user"
''',
        '''    async def user_label(self, user_id: str) -> str:
        user = await self._users.get_by_id(user_id)
        return user.display_name if user is not None else "Workspace user"
''',
    )


def patch_seed(repo: Path) -> None:
    replace_once(
        repo,
        "app/db/seed.py",
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
        '''from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
''',
    )
    replace_once(
        repo,
        "app/db/seed.py",
        '''    RolePermissionORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    RolePermissionORM,
    SeatAssignmentORM,
)
''',
    )
    replace_once(
        repo,
        "app/db/seed.py",
        "from app.domain.enums import (\n",
        "from app.domain.enums import (\n",
    )
    replace_once(
        repo,
        "app/db/seed.py",
        ''')

_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
''',
        ''')
from app.domain.models import User

_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
''',
    )
    replace_once(
        repo,
        "app/db/seed.py",
        '''    for user_id, display_name, email in USERS:
        if await session.get(UserORM, user_id) is None:
            session.add(
                UserORM(
                    id=user_id,
                    display_name=display_name,
                    email=email,
                    status=UserStatus.ACTIVE.value,
                )
            )

    await session.flush()
''',
        '''    # Sandbox users are no longer persisted in the Workplace database.
    # Production resolves the same contract from Test_user1.
    get_sandbox_user_directory().reset(
        User(
            id=user_id,
            display_name=display_name,
            email=email,
            status=UserStatus.ACTIVE,
            created_at=_EPOCH,
            updated_at=_EPOCH,
        )
        for user_id, display_name, email in USERS
    )

    await session.flush()
''',
    )


def patch_lifecycle_and_health(repo: Path) -> None:
    replace_once(
        repo,
        "app/main.py",
        "from app import __version__\n",
        '''from app import __version__
from app.adapters.user.provider import dispose_user_directory
''',
    )
    replace_once(
        repo,
        "app/main.py",
        '''    finally:
        await coordinator.stop()
''',
        '''    finally:
        await coordinator.stop()
        await dispose_user_directory()
''',
    )
    replace_once(
        repo,
        "app/api/health_routes.py",
        "from app.api.dependencies import SessionDep\n",
        "from app.api.dependencies import SessionDep, UserDirectoryDep\n",
    )
    replace_once(
        repo,
        "app/api/health_routes.py",
        'EXPECTED_MIGRATION_HEAD = "0016_agent_runs_events"\n',
        'EXPECTED_MIGRATION_HEAD = "0018_replace_local_users"\n',
    )
    replace_once(
        repo,
        "app/api/health_routes.py",
        '''@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "database": "connected",
        "environment": get_settings().environment,
    }
''',
        '''@router.get("/ready")
async def ready(
    session: SessionDep,
    user_directory: UserDirectoryDep,
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    await user_directory.ping()
    return {
        "status": "ready",
        "database": "connected",
        "user_directory": "connected",
        "environment": get_settings().environment,
    }
''',
    )
    replace_once(
        repo,
        "app/api/health_routes.py",
        '''async def readiness_details(
    session: SessionDep,
    action_service: AgentActionServiceDep,
) -> dict:
    await session.execute(text("SELECT 1"))
    settings = get_settings()
''',
        '''async def readiness_details(
    session: SessionDep,
    action_service: AgentActionServiceDep,
    user_directory: UserDirectoryDep,
) -> dict:
    await session.execute(text("SELECT 1"))
    settings = get_settings()
    try:
        await user_directory.ping()
        user_directory_connected = True
    except Exception:
        user_directory_connected = False
''',
    )
    replace_once(
        repo,
        "app/api/health_routes.py",
        '''    checks = {
        "database_connected": True,
        "sandbox_environment": settings.is_sandbox,
''',
        '''    checks = {
        "database_connected": True,
        "user_directory_connected": user_directory_connected,
        "user_directory_is_test_user1_or_sandbox": bool(
            settings.nucleus_user_database_url or settings.is_sandbox
        ),
        "sandbox_environment": settings.is_sandbox,
''',
    )

def add_migration_and_cutover_tool(repo: Path) -> None:
    write(
        repo,
        "alembic/versions/0018_replace_local_users.py",
        '''
        """replace the local users table with the Test_user1 directory

        Revision ID: 0018_replace_local_users
        Revises: 0017_action_control_plane
        Create Date: 2026-07-20

        The external dbmr_Database_Nucleus.dbo.Test_user1 table is deliberately
        outside Alembic metadata. This migration only removes local foreign keys
        and the obsolete local users table.
        """

        from __future__ import annotations

        import os
        from typing import Sequence, Union

        import sqlalchemy as sa
        from alembic import op

        revision: str = "0018_replace_local_users"
        down_revision: Union[str, None] = "0017_action_control_plane"
        branch_labels: Union[str, Sequence[str], None] = None
        depends_on: Union[str, Sequence[str], None] = None

        _USER_FOREIGN_KEYS = (
            ("organization_memberships", "user_id"),
            ("seat_assignments", "user_id"),
            ("agent_action_proposals", "requested_by_user_id"),
            ("agent_action_approvals", "decided_by_user_id"),
            ("agent_action_executions", "executed_by_user_id"),
            ("agent_action_rollbacks", "created_by_user_id"),
            ("agent_conversations", "created_by_user_id"),
            ("agent_runs", "requested_by_user_id"),
            ("workplace_resource_tombstones", "deleted_by_user_id"),
            ("nucleus_actor_mappings", "workplace_user_id"),
        )
        _SQLITE_NAMING = {
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        }


        def _foreign_key(table_name: str, column_name: str) -> dict | None:
            inspector = sa.inspect(op.get_bind())
            for foreign_key in inspector.get_foreign_keys(table_name):
                if (
                    foreign_key.get("referred_table") == "users"
                    and column_name in foreign_key.get("constrained_columns", ())
                ):
                    return foreign_key
            return None


        def _drop_user_foreign_key(table_name: str, column_name: str) -> None:
            foreign_key = _foreign_key(table_name, column_name)
            if foreign_key is None:
                return
            bind = op.get_bind()
            name = foreign_key.get("name")
            if bind.dialect.name == "sqlite":
                constraint_name = name or f"fk_{table_name}_{column_name}_users"
                with op.batch_alter_table(
                    table_name,
                    recreate="always",
                    naming_convention=_SQLITE_NAMING,
                ) as batch:
                    batch.drop_constraint(constraint_name, type_="foreignkey")
                return
            if not name:
                raise RuntimeError(
                    f"Cannot safely drop unnamed user foreign key on {table_name}.{column_name}"
                )
            op.drop_constraint(name, table_name, type_="foreignkey")


        def _require_canonical_production_ids() -> None:
            # The one-time mapper must run before this migration on a populated
            # production database. Sandbox databases intentionally use synthetic
            # IDs and are replaced by the in-memory sandbox adapter after upgrade.
            if not os.getenv("WORKPLACE_NUCLEUS_USER_DATABASE_URL"):
                return
            bind = op.get_bind()
            invalid = [
                str(row[0])
                for row in bind.execute(sa.text("SELECT id FROM users")).fetchall()
                if not str(row[0]).isdigit()
            ]
            if invalid:
                sample = ", ".join(invalid[:5])
                raise RuntimeError(
                    "Legacy users remain unmapped to Test_user1.UserID values. "
                    "Run `python -m scripts.map_legacy_users_to_test_user1 --apply` "
                    f"before upgrading. Example IDs: {sample}"
                )


        def upgrade() -> None:
            inspector = sa.inspect(op.get_bind())
            if "users" not in inspector.get_table_names():
                return
            _require_canonical_production_ids()
            for table_name, column_name in _USER_FOREIGN_KEYS:
                if table_name in sa.inspect(op.get_bind()).get_table_names():
                    _drop_user_foreign_key(table_name, column_name)
            op.drop_table("users")


        def downgrade() -> None:
            raise RuntimeError(
                "0018 is intentionally irreversible: user profiles now live only in Test_user1"
            )
        ''',
    )
    write(repo, "scripts/__init__.py", '"""Operational migration helpers."""\n')
    write(
        repo,
        "scripts/map_legacy_users_to_test_user1.py",
        '''
        """Map populated legacy local users to Test_user1.UserID before Alembic 0018.

        Dry-run by default. The apply mode performs all local reference rewrites in
        one transaction while the legacy users table and its foreign keys still
        exist. Every EmailID must resolve to exactly one Test_user1 row.
        """

        from __future__ import annotations

        import argparse
        import asyncio
        import hashlib
        from dataclasses import dataclass

        from sqlalchemy import text

        from app.adapters.user.provider import get_user_directory
        from app.db.session import get_sessionmaker

        _REFERENCES = (
            ("organization_memberships", "user_id"),
            ("seat_assignments", "user_id"),
            ("seat_assignments", "assigned_by_user_id"),
            ("seat_assignments", "revoked_by_user_id"),
            ("organization_report_access", "granted_by_user_id"),
            ("audit_events", "actor_user_id"),
            ("agent_action_proposals", "requested_by_user_id"),
            ("agent_action_approvals", "decided_by_user_id"),
            ("agent_action_executions", "executed_by_user_id"),
            ("agent_action_rollbacks", "created_by_user_id"),
            ("agent_conversations", "created_by_user_id"),
            ("agent_runs", "requested_by_user_id"),
            ("workplace_resource_tombstones", "deleted_by_user_id"),
            ("nucleus_actor_mappings", "workplace_user_id"),
        )


        @dataclass(frozen=True)
        class Mapping:
            old_id: str
            new_id: str
            email: str
            display_name: str


        async def build_mappings() -> tuple[Mapping, ...]:
            directory = get_user_directory()
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                rows = (
                    await session.execute(
                        text(
                            "SELECT id, display_name, email FROM users "
                            "ORDER BY id ASC"
                        )
                    )
                ).mappings().all()
            mappings: list[Mapping] = []
            errors: list[str] = []
            for row in rows:
                external = await directory.get_by_email(str(row["email"]))
                if external is None:
                    errors.append(
                        f"{row['id']}: no Test_user1 match for {row['email']}"
                    )
                    continue
                mappings.append(
                    Mapping(
                        old_id=str(row["id"]),
                        new_id=external.id,
                        email=str(row["email"]),
                        display_name=str(row["display_name"]),
                    )
                )
            if errors:
                raise RuntimeError("Legacy mapping failed:\\n" + "\\n".join(errors))
            new_ids = [item.new_id for item in mappings]
            if len(new_ids) != len(set(new_ids)):
                raise RuntimeError(
                    "Two legacy users resolve to the same Test_user1.UserID; resolve duplicates manually"
                )
            return tuple(mappings)


        async def apply_mappings(mappings: tuple[Mapping, ...]) -> None:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                async with session.begin():
                    for item in mappings:
                        if item.old_id == item.new_id:
                            continue
                        target_exists = await session.scalar(
                            text("SELECT COUNT(*) FROM users WHERE id = :new_id"),
                            {"new_id": item.new_id},
                        )
                        if int(target_exists or 0):
                            raise RuntimeError(
                                f"Target local ID already exists: {item.new_id}"
                            )
                        digest = hashlib.sha256(item.old_id.encode("utf-8")).hexdigest()[:16]
                        legacy_email = f"legacy-{digest}@invalid.local"
                        await session.execute(
                            text("UPDATE users SET email = :legacy_email WHERE id = :old_id"),
                            {"legacy_email": legacy_email, "old_id": item.old_id},
                        )
                        await session.execute(
                            text(
                                "INSERT INTO users "
                                "(id, display_name, email, status, created_at, updated_at) "
                                "SELECT :new_id, display_name, :email, status, created_at, updated_at "
                                "FROM users WHERE id = :old_id"
                            ),
                            {
                                "new_id": item.new_id,
                                "email": item.email,
                                "old_id": item.old_id,
                            },
                        )
                        for table_name, column_name in _REFERENCES:
                            await session.execute(
                                text(
                                    f"UPDATE {table_name} SET {column_name} = :new_id "
                                    f"WHERE {column_name} = :old_id"
                                ),
                                {"new_id": item.new_id, "old_id": item.old_id},
                            )
                        await session.execute(
                            text("DELETE FROM users WHERE id = :old_id"),
                            {"old_id": item.old_id},
                        )


        async def main(apply: bool) -> None:
            mappings = await build_mappings()
            for item in mappings:
                marker = "=" if item.old_id == item.new_id else "->"
                print(f"{item.old_id} {marker} {item.new_id}  {item.email}")
            if not apply:
                print("Dry run only. Re-run with --apply after reviewing every mapping.")
                return
            await apply_mappings(mappings)
            print(f"Applied {len(mappings)} canonical user mappings.")


        if __name__ == "__main__":
            parser = argparse.ArgumentParser()
            parser.add_argument("--apply", action="store_true")
            arguments = parser.parse_args()
            asyncio.run(main(arguments.apply))
        ''',
    )
    write(
        repo,
        "docs/TEST_USER1_CUTOVER.md",
        '''
        # Test_user1 cutover

        `dbmr_Database_Nucleus.dbo.Test_user1` is the only production user
        identity/profile table. The Workplace database retains organization
        memberships, roles, seats, actions, runs, and audits, whose user ID fields
        contain the string representation of `Test_user1.UserID`.

        ## Required environment

        ```bash
        export WORKPLACE_NUCLEUS_USER_DATABASE_URL='mssql+aioodbc://...'
        export WORKPLACE_NUCLEUS_USER_DATABASE_NAME='dbmr_Database_Nucleus'
        export WORKPLACE_NUCLEUS_USER_SCHEMA_NAME='dbo'
        export WORKPLACE_NUCLEUS_USER_TABLE_NAME='Test_user1'
        ```

        The ODBC connection string must use an installed Microsoft SQL Server ODBC
        driver. Production startup fails closed when this URL is absent.

        ## Existing populated deployment

        Before Alembic 0018, map every legacy local user by email:

        ```bash
        python -m scripts.map_legacy_users_to_test_user1
        python -m scripts.map_legacy_users_to_test_user1 --apply
        alembic upgrade head
        ```

        The first command is a mandatory dry run. Duplicate or missing EmailID
        matches stop the migration. After 0018, the local `users` table no longer
        exists and Alembic never manages `Test_user1`.

        ## User creation

        Reads are available as soon as the Nucleus connection is configured.
        Writes remain disabled by default:

        ```bash
        export WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=false
        ```

        The repository introspects the live Test_user1 metadata before INSERT. Set
        trusted defaults using JSON only for columns verified by DB metadata:

        ```bash
        export WORKPLACE_NUCLEUS_USER_DEFAULT_TYPE_ID='...'
        export WORKPLACE_NUCLEUS_USER_CREATE_DEFAULTS='{"company":"..."}'
        export WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=true
        ```

        `Password` is always rejected. If it is a required column without a DB
        default, user creation must be routed through the official authentication
        stored procedure/API rather than direct SQL.
        ''',
    )

def patch_tests(repo: Path) -> None:
    replace_once(
        repo,
        "tests/test_migrations.py",
        'EXPECTED_HEAD = "0017_action_control_plane"\n',
        'EXPECTED_HEAD = "0018_replace_local_users"\n',
    )
    remove_once(repo, "tests/test_migrations.py", '    "users",\n')

    # Contextual seat flow: add the synthetic user to the sandbox directory.
    replace_once(
        repo,
        "tests/test_contextual_seat_actions.py",
        "from sqlalchemy import select\n\n",
        '''from sqlalchemy import select

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
''',
    )
    replace_once(
        repo,
        "tests/test_contextual_seat_actions.py",
        "from app.db.orm_models import OrganizationMembershipORM, SeatAssignmentORM, UserORM\n",
        "from app.db.orm_models import OrganizationMembershipORM, SeatAssignmentORM\n",
    )
    replace_once(
        repo,
        "tests/test_contextual_seat_actions.py",
        "from app.domain.models import OrganizationMember\n",
        "from app.domain.models import OrganizationMember, User\n",
    )
    replace_once(
        repo,
        "tests/test_contextual_seat_actions.py",
        '''    async with sessionmaker_() as session:
        session.add(
            UserORM(
                id=user_id,
                display_name="Demo Analyst",
                email="demo.analyst@example.test",
                status=UserStatus.ACTIVE.value,
            )
        )
        session.add(
''',
        '''    async with sessionmaker_() as session:
        get_sandbox_user_directory().upsert(
            User(
                id=user_id,
                display_name="Demo Analyst",
                email="demo.analyst@example.test",
                status=UserStatus.ACTIVE,
            )
        )
        session.add(
''',
    )

    # Organization-boundary fixture.
    replace_once(
        repo,
        "tests/test_organization_boundaries.py",
        "from httpx import AsyncClient\n",
        '''from httpx import AsyncClient

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
''',
    )
    replace_once(
        repo,
        "tests/test_organization_boundaries.py",
        '''    SeatAssignmentORM,
    UserORM,
)
''',
        '''    SeatAssignmentORM,
)
from app.domain.enums import UserStatus
from app.domain.models import User
''',
    )
    replace_once(
        repo,
        "tests/test_organization_boundaries.py",
        '''    database_session.add(
        UserORM(
            id=SECONDARY_USER_ID,
            display_name="Secondary Organization User",
            email="secondary.user@example.test",
            status="active",
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
''',
        '''    get_sandbox_user_directory().upsert(
        User(
            id=SECONDARY_USER_ID,
            display_name="Secondary Organization User",
            email="secondary.user@example.test",
            status=UserStatus.ACTIVE,
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
''',
    )

    # Multi-approval peer administrators.
    replace_once(
        repo,
        "tests/test_multi_approval_and_rollback.py",
        "from httpx import AsyncClient\n",
        '''from httpx import AsyncClient

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
''',
    )
    replace_once(
        repo,
        "tests/test_multi_approval_and_rollback.py",
        "from app.db.orm_models import OrganizationMembershipORM, OrganizationORM, UserORM\n",
        '''from app.db.orm_models import OrganizationMembershipORM, OrganizationORM
from app.domain.enums import UserStatus
from app.domain.models import User
''',
    )
    replace_once(
        repo,
        "tests/test_multi_approval_and_rollback.py",
        '''        db_session.add(
            UserORM(
                id=user_id,
                display_name=f"Approver {suffix.upper()}",
                email=f"approver.{suffix}@example.test",
                status="active",
            )
        )
''',
        '''        get_sandbox_user_directory().upsert(
            User(
                id=user_id,
                display_name=f"Approver {suffix.upper()}",
                email=f"approver.{suffix}@example.test",
                status=UserStatus.ACTIVE,
            )
        )
''',
    )

    # Inverse lifecycle peer administrators.
    replace_once(
        repo,
        "tests/test_inverse_operational_actions.py",
        "from httpx import AsyncClient\n",
        '''from httpx import AsyncClient

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
''',
    )
    replace_once(
        repo,
        "tests/test_inverse_operational_actions.py",
        '''    OrganizationReportAccessORM,
    SeatAssignmentORM,
    UserORM,
)
''',
        '''    OrganizationReportAccessORM,
    SeatAssignmentORM,
)
from app.domain.enums import UserStatus
from app.domain.models import User
''',
    )
    replace_once(
        repo,
        "tests/test_inverse_operational_actions.py",
        '''        db_session.add(
            UserORM(
                id=user_id,
                display_name=suffix,
                email=f"{suffix}@example.test",
                status="active",
            )
        )
''',
        '''        get_sandbox_user_directory().upsert(
            User(
                id=user_id,
                display_name=suffix,
                email=f"{suffix}@example.test",
                status=UserStatus.ACTIVE,
            )
        )
''',
    )

    write(
        repo,
        "tests/test_user_directory_boundary.py",
        '''
        from __future__ import annotations

        from app.adapters.user.contract import CreateUserCommand
        from app.adapters.user.sandbox_adapter import SandboxUserDirectory
        from app.domain.enums import UserStatus
        from app.domain.models import User


        async def test_sandbox_directory_replaces_local_user_persistence() -> None:
            directory = SandboxUserDirectory()
            directory.reset(
                (
                    User(
                        id="1001",
                        display_name="Existing User",
                        email="existing@example.test",
                        status=UserStatus.ACTIVE,
                    ),
                )
            )

            assert (await directory.get_by_id("1001")).email == "existing@example.test"
            assert (await directory.get_by_email("EXISTING@example.test")).id == "1001"
            assert set(await directory.get_many_by_ids(("1001", "missing"))) == {"1001"}


        async def test_sandbox_creation_is_idempotent_by_normalized_email() -> None:
            directory = SandboxUserDirectory()
            command = CreateUserCommand(
                display_name="Created User",
                email="Created@Example.Test",
                actor_user_id="1001",
            )
            first = await directory.create_user(command)
            second = await directory.create_user(command)

            assert first.id == second.id
            assert first.email == "created@example.test"
            assert first.status == UserStatus.ACTIVE
        ''',
    )


def patch_domain_documentation(repo: Path) -> None:
    replace_once(
        repo,
        "app/domain/models.py",
        '    """An authenticated mock user (internal employee) from the sandbox DB."""\n',
        '    """Authenticated user projected from the configured user directory."""\n',
    )
    replace_once(
        repo,
        "app/domain/models.py",
        '    ``users`` and ``seats`` are distinct: an active member may or may not\n',
        '    User identity and seats are distinct: an active member may or may not\n',
    )

def validate(repo: Path, run_tests: bool) -> None:
    forbidden = {
        "app": ("UserORM", 'ForeignKey("users.id")', "__tablename__ = \"users\""),
        "tests": ("UserORM",),
    }
    for relative, needles in forbidden.items():
        root = repo / relative
        for path in root.rglob("*.py"):
            text_value = path.read_text(encoding="utf-8")
            for needle in needles:
                if needle in text_value:
                    raise PatchError(f"Forbidden legacy user reference remains: {path}: {needle}")

    run(repo, sys.executable, "-m", "compileall", "-q", "app", "tests", "scripts", "alembic/versions")
    run(repo, "git", "diff", "--check")
    if run_tests:
        run(repo, sys.executable, "-m", "pytest", "-q")


def apply_patch(repo: Path) -> None:
    add_new_files(repo)
    patch_configuration(repo)
    patch_local_models(repo)
    replace_user_repository(repo)
    patch_dependencies(repo)
    patch_operational_user_actions(repo)
    patch_workflows(repo)
    patch_run_runtime(repo)
    patch_user_read_surfaces(repo)
    patch_seed(repo)
    patch_lifecycle_and_health(repo)
    patch_domain_documentation(repo)
    add_migration_and_cutover_tool(repo)
    patch_tests(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--allow-newer", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    assert_clean_base(repo, args.allow_newer)
    dirty_before = run(repo, "git", "status", "--porcelain").stdout.strip()
    if dirty_before and not args.allow_dirty:
        raise PatchError(
            "Working tree is not clean. Commit/stash unrelated changes or pass --allow-dirty."
        )
    if args.commit and dirty_before:
        raise PatchError("--commit is refused for a pre-existing dirty worktree")

    if args.commit:
        ensure_branch(repo)
    apply_patch(repo)
    validate(repo, args.run_tests)

    changed = run(repo, "git", "status", "--short").stdout
    if not changed.strip():
        print("Patch already applied; no changes detected.")
        return 0
    print(changed, end="")

    if args.commit:
        run(repo, "git", "add", "-A")
        run(repo, "git", "commit", "-m", COMMIT_MESSAGE)
        print(run(repo, "git", "show", "--stat", "--oneline", "HEAD").stdout)
    else:
        print("\nValidation passed. Review the diff, then commit with:")
        print(f"  git switch -c {BRANCH_NAME}")
        print("  git add -A")
        print(f"  git commit -m \"{COMMIT_MESSAGE}\"")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchError as exception:
        print(f"ERROR: {exception}", file=sys.stderr)
        raise SystemExit(2)
