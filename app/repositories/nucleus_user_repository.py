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
    "UserTypeID",
    "OrganizationId",
    "Name",
    "EmailID",
    "CreatedDate",
    "ModifiedDate",
    "CreatedBy",
    "ModifiedBy",
    "IsActive",
    "PareentUserID",
    "menuAccess",
    "regionsAssigned",
    "macAddress",
    "isClient",
    "company",
    "contactNumber",
    "designation",
    "licenceEndDate",
    "licenceStartDate",
    "licenceType",
    "reportAccess",
    "isFrontAccess",
    "countryAccess",
    "epidemAccess",
    "iExportAccess",
    "indicatorAccess",
    "pharmaAccess",
    "reportAccessMew",
    "epidomReegions",
    "pharmaReegions",
    "reportReegions",
    "userSource",
    "isSampleDatabaseAccess",
    "isApprovedTC",
    "SpocUserID",
    "RpocUserID",
    "isCpAccess",
    "clientType",
    "IndicationsAccess",
    "pharma_CompanyView",
    "pharma_DrugView",
    "pharma_TherpyView",
    "firstLoginDate",
    "viewOnly",
    "expiryDate",
    "NoOFDays",
    "isSampleTocDatabaseAccess",
    "epicDatabaseAccess",
    "isBlurAll",
    "ciDataBaseAccess",
    "isSpecialityAccess",
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

    async def get_by_email_and_password(
        self, email: str, password: str
    ) -> User | None:
        normalized = email.strip().lower()
        statement = text(
            f"SELECT TOP (2) {self._projection()} "
            f"FROM {self._qualified_table} "
            "WHERE LOWER(LTRIM(RTRIM([EmailID]))) = :email "
            "  AND [Password] = :password "
            "ORDER BY [UserID] ASC"
        )
        async with self._sessionmaker() as session:
            rows = tuple(
                (
                    await session.execute(
                        statement, {"email": normalized, "password": password}
                    )
                )
                .mappings()
                .all()
            )
        if len(rows) > 1:
            raise AmbiguousUserEmailError(
                "Test_user1 contains more than one row for this EmailID and Password"
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
        known_keys = {"UserID", "Name", "EmailID", "IsActive", "CreatedDate", "ModifiedDate"}
        extra = {}
        for k, v in row.items():
            if k not in known_keys:
                if hasattr(v, "isoformat") and callable(v.isoformat):
                    extra[k] = v.isoformat()
                else:
                    extra[k] = v
        return User(
            id=str(row["UserID"]),
            display_name=str(row.get("Name") or "").strip(),
            email=str(row.get("EmailID") or "").strip(),
            status=(
                UserStatus.ACTIVE if active is True or active == 1 else UserStatus.DISABLED
            ),
            created_at=row.get("CreatedDate"),
            updated_at=row.get("ModifiedDate"),
            extra_fields=extra,
        )
