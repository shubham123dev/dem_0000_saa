#!/usr/bin/env python3
"""Apply the Nucleus full administrative-control vertical slice.

Baseline repository:
    shubham123dev/dem_0000_saa
Baseline commit:
    2a2809410adae9a14973eaf77870559f402e0611

This patch is fail-closed. It validates the exact branch and commit, refuses
tracked local changes, asserts every source transformation, restores all touched
files on failure, and never stages, commits, pushes, or removes unrelated
untracked files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

BASELINE_COMMIT = "2a2809410adae9a14973eaf77870559f402e0611"


class PatchError(RuntimeError):
    pass


def clean(value: str) -> str:
    return dedent(value).strip("\n") + "\n"


def indent_text(value: str, spaces: int) -> str:
    prefix = " " * spaces
    return "".join(
        prefix + line if line.strip() else line
        for line in value.splitlines(keepends=True)
    )


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PatchError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def read_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    if not path.is_file():
        raise PatchError(f"Required file is missing: {relative_path}")
    return path.read_text(encoding="utf-8")


def write_text(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def create_exact(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    normalized = content.strip("\n") + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == normalized:
            return
        raise PatchError(f"Refusing to overwrite existing file: {relative_path}")
    write_text(root, relative_path, normalized)


def replace_exact(
    root: Path,
    relative_path: str,
    old: str,
    new: str,
    *,
    expected_count: int = 1,
) -> None:
    text = read_text(root, relative_path)
    count = text.count(old)
    if count != expected_count:
        raise PatchError(
            f"{relative_path}: expected {expected_count} occurrence(s), found {count}:\n{old}"
        )
    write_text(root, relative_path, text.replace(old, new))


def insert_before(
    root: Path,
    relative_path: str,
    marker: str,
    addition: str,
    *,
    expected_count: int = 1,
) -> None:
    text = read_text(root, relative_path)
    count = text.count(marker)
    if count != expected_count:
        raise PatchError(
            f"{relative_path}: expected {expected_count} marker(s), found {count}: {marker}"
        )
    write_text(root, relative_path, text.replace(marker, addition + marker, 1))


def validate_repository(root: Path) -> None:
    if not (root / ".git").is_dir():
        raise PatchError("Run this script against the repository root containing .git")
    branch = run_git(root, "branch", "--show-current")
    if branch != "main":
        raise PatchError(f"Expected branch main, found {branch or '<detached>'}")
    head = run_git(root, "rev-parse", "HEAD")
    if head != BASELINE_COMMIT:
        raise PatchError(
            f"Unexpected HEAD. Expected {BASELINE_COMMIT}, found {head}. "
            "Do not force-apply this patch to another source state."
        )
    if run_git(root, "diff", "--name-only"):
        raise PatchError("Tracked working-tree changes exist; commit or revert them first")
    if run_git(root, "diff", "--cached", "--name-only"):
        raise PatchError("Staged changes exist; commit or unstage them first")


def add_database_models(root: Path) -> None:
    create_exact(
        root,
        "app/db/nucleus_admin_models.py",
        clean(
            '''
            """Internal persistence supporting safe Nucleus administration.

            These tables are Workplace Agent sidecars. They do not alter the eight
            supplied Nucleus tables and are not part of the future Nucleus wire contract.
            """

            from __future__ import annotations

            from datetime import datetime, timezone

            from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
            from sqlalchemy.orm import Mapped, mapped_column

            from app.db.base import Base


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            class NucleusActorMappingORM(Base):
                __tablename__ = "nucleus_actor_mappings"
                __table_args__ = (
                    UniqueConstraint("nucleus_actor_id", name="uq_nucleus_actor_mapping_actor"),
                )

                workplace_user_id: Mapped[str] = mapped_column(
                    String,
                    ForeignKey("users.id", ondelete="CASCADE"),
                    primary_key=True,
                )
                nucleus_actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
                created_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )
                updated_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
                )


            class NucleusAccessTombstoneORM(Base):
                """Logical revocation for exact tables that have no IsActive column."""

                __tablename__ = "nucleus_access_tombstones"
                __table_args__ = (
                    UniqueConstraint(
                        "resource_type", "access_id", name="uq_nucleus_access_tombstone"
                    ),
                    Index(
                        "ix_nucleus_access_tombstone_org",
                        "organization_account_id",
                        "resource_type",
                    ),
                )

                resource_type: Mapped[str] = mapped_column(String(80), primary_key=True)
                access_id: Mapped[int] = mapped_column(Integer, primary_key=True)
                organization_account_id: Mapped[int] = mapped_column(
                    Integer,
                    ForeignKey(
                        "OrganizationAccount.OrganizationAccountId",
                        ondelete="CASCADE",
                    ),
                    nullable=False,
                )
                version: Mapped[int] = mapped_column(Integer, nullable=False)
                snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
                revoked_by: Mapped[int] = mapped_column(Integer, nullable=False)
                revoked_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )
            '''
        ),
    )


def add_domain_models(root: Path) -> None:
    create_exact(
        root,
        "app/domain/nucleus_admin_models.py",
        clean(
            '''
            """Framework-neutral state used by Nucleus administrative actions."""

            from __future__ import annotations

            from dataclasses import dataclass
            from datetime import date, datetime
            from typing import Any


            @dataclass(frozen=True)
            class NucleusAccountAdminState:
                organization_account_id: int
                login_username: str
                max_user_limit: int
                license_start_date: datetime | None
                license_end_date: datetime | None
                status: str
                approved_by: int | None
                approved_date: datetime | None
                rejected_by: int | None
                rejected_date: datetime | None
                rejection_reason: str | None
                is_active: bool
                version: int


            @dataclass(frozen=True)
            class NucleusManagedAccess:
                resource_type: str
                access_id: int
                organization_account_id: int
                values: dict[str, int | None]
                revoked: bool
                version: int


            @dataclass(frozen=True)
            class NucleusLicenseProjectionState:
                seat_pool_id: str
                total_seats: int
                starts_at: datetime | None
                expires_at: datetime | None
                seat_pool_status: str
                seat_pool_version: int
                active_assignments: int
                renewal_date: date | None
                overview_version: int


            @dataclass(frozen=True)
            class NucleusLifecycleProjectionState:
                organization_status: str
                organization_version: int
                seat_pool_id: str
                seat_pool_status: str
                seat_pool_version: int


            def managed_access_snapshot(access: NucleusManagedAccess) -> dict[str, Any]:
                return {
                    "resource_type": access.resource_type,
                    "access_id": access.access_id,
                    **access.values,
                    "revoked": access.revoked,
                    "version": access.version,
                }
            '''
        ),
    )


def add_contracts(root: Path) -> None:
    create_exact(
        root,
        "app/adapters/nucleus/admin_contract.py",
        clean(
            '''
            """Ports for privileged Nucleus administration and legacy projections."""

            from __future__ import annotations

            from datetime import datetime
            from typing import Protocol, runtime_checkable

            from app.domain.nucleus_admin_models import (
                NucleusAccountAdminState,
                NucleusLicenseProjectionState,
                NucleusLifecycleProjectionState,
                NucleusManagedAccess,
            )


            @runtime_checkable
            class NucleusAdministrationGateway(Protocol):
                async def get_admin_state(
                    self, organization_code: str
                ) -> NucleusAccountAdminState | None:
                    ...

                async def get_username_owner_id(self, username: str) -> int | None:
                    ...

                async def update_username_if_version(
                    self,
                    *,
                    organization_code: str,
                    username: str,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    ...

                async def update_license_if_version(
                    self,
                    *,
                    organization_code: str,
                    max_user_limit: int,
                    license_start_date: datetime | None,
                    license_end_date: datetime | None,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    ...

                async def transition_approval_if_version(
                    self,
                    *,
                    organization_code: str,
                    decision: str,
                    reason: str | None,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    ...

                async def set_active_if_version(
                    self,
                    *,
                    organization_code: str,
                    is_active: bool,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    ...

                async def inspect_access(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    values: dict[str, int | None],
                ) -> tuple[NucleusManagedAccess | None, int] | None:
                    ...

                async def get_access(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    access_id: int,
                ) -> NucleusManagedAccess | None:
                    ...

                async def grant_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    values: dict[str, int | None],
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusManagedAccess | None:
                    ...

                async def revoke_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    access_id: int,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusManagedAccess | None:
                    ...


            @runtime_checkable
            class NucleusAdministrationProjectionGateway(Protocol):
                async def get_license_projection(
                    self, organization_id: str
                ) -> NucleusLicenseProjectionState | None:
                    ...

                async def update_license_projection_if_versions(
                    self,
                    *,
                    organization_id: str,
                    max_user_limit: int,
                    license_start_date: datetime | None,
                    license_end_date: datetime | None,
                    expected_seat_pool_version: int,
                    expected_overview_version: int,
                ) -> NucleusLicenseProjectionState | None:
                    ...

                async def get_lifecycle_projection(
                    self, organization_id: str
                ) -> NucleusLifecycleProjectionState | None:
                    ...

                async def update_lifecycle_projection_if_versions(
                    self,
                    *,
                    organization_id: str,
                    should_be_active: bool,
                    license_end_date: datetime | None,
                    expected_organization_version: int,
                    expected_seat_pool_version: int,
                ) -> NucleusLifecycleProjectionState | None:
                    ...
            '''
        ),
    )


def add_actor_mapping_repository(root: Path) -> None:
    create_exact(
        root,
        "app/repositories/nucleus_actor_mapping_repository.py",
        clean(
            '''
            """Resolve authenticated Workplace users to Nucleus integer actor IDs."""

            from __future__ import annotations

            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.nucleus_admin_models import NucleusActorMappingORM


            class NucleusActorMappingRepository:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                async def get_nucleus_actor_id(self, workplace_user_id: str) -> int | None:
                    row = await self._session.get(
                        NucleusActorMappingORM, workplace_user_id
                    )
                    return row.nucleus_actor_id if row is not None else None
            '''
        ),
    )


def add_admin_repository(root: Path) -> None:
    create_exact(
        root,
        "app/repositories/nucleus_administration_repository.py",
        clean(
            '''
            """SQLite adapter for privileged Nucleus administration."""

            from __future__ import annotations

            from dataclasses import dataclass
            from datetime import datetime, timezone
            import hashlib
            import json

            from sqlalchemy import func, select, update
            from sqlalchemy.exc import IntegrityError
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.nucleus_admin_models import NucleusAccessTombstoneORM
            from app.db.nucleus_models import (
                NucleusOrganizationAccountORM,
                NucleusOrganizationCompanyProfileAccessORM,
                NucleusOrganizationDrugAccessORM,
                NucleusOrganizationIndicationAccessORM,
                NucleusOrganizationMarketAccessORM,
                NucleusResourceVersionORM,
            )
            from app.domain.nucleus_admin_models import (
                NucleusAccountAdminState,
                NucleusManagedAccess,
            )


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            @dataclass(frozen=True)
            class _AccessSpec:
                resource_type: str
                version_resource_type: str
                orm_type: type
                id_attribute: str
                value_attributes: tuple[str, ...]


            _ACCESS_SPECS = {
                "company_profile": _AccessSpec(
                    resource_type="OrganizationCompanyProfileAccess",
                    version_resource_type="nucleus_company_profile_access",
                    orm_type=NucleusOrganizationCompanyProfileAccessORM,
                    id_attribute="organization_company_profile_access_id",
                    value_attributes=("company_id",),
                ),
                "drug": _AccessSpec(
                    resource_type="OrganizationDrugAccess",
                    version_resource_type="nucleus_drug_access",
                    orm_type=NucleusOrganizationDrugAccessORM,
                    id_attribute="organization_drug_access_id",
                    value_attributes=("drug_id",),
                ),
                "indication": _AccessSpec(
                    resource_type="OrganizationIndicationAccess",
                    version_resource_type="nucleus_indication_access",
                    orm_type=NucleusOrganizationIndicationAccessORM,
                    id_attribute="organization_indication_access_id",
                    value_attributes=("indication_id",),
                ),
                "market": _AccessSpec(
                    resource_type="OrganizationMarketAccess",
                    version_resource_type="nucleus_market_access",
                    orm_type=NucleusOrganizationMarketAccessORM,
                    id_attribute="organization_market_access_id",
                    value_attributes=("market_id", "market_sample_id"),
                ),
            }


            class NucleusAdministrationRepository:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                @staticmethod
                def _spec(access_kind: str) -> _AccessSpec:
                    try:
                        return _ACCESS_SPECS[access_kind]
                    except KeyError as exception:
                        raise ValueError("Unsupported Nucleus access kind") from exception

                async def _account_row(
                    self, organization_code: str
                ) -> NucleusOrganizationAccountORM | None:
                    return await self._session.scalar(
                        select(NucleusOrganizationAccountORM).where(
                            NucleusOrganizationAccountORM.organization_code
                            == organization_code
                        )
                    )

                async def _version(
                    self, resource_type: str, resource_key: str, *, default: int = 1
                ) -> int:
                    row = await self._session.get(
                        NucleusResourceVersionORM,
                        {"resource_type": resource_type, "resource_key": resource_key},
                    )
                    return row.version if row is not None else default

                async def _advance_version(
                    self,
                    resource_type: str,
                    resource_key: str,
                    expected_version: int,
                ) -> int | None:
                    result = await self._session.execute(
                        update(NucleusResourceVersionORM)
                        .where(
                            NucleusResourceVersionORM.resource_type == resource_type,
                            NucleusResourceVersionORM.resource_key == resource_key,
                            NucleusResourceVersionORM.version == expected_version,
                        )
                        .values(
                            version=expected_version + 1,
                            updated_at=_utcnow(),
                        )
                    )
                    if result.rowcount != 1:
                        await self._session.rollback()
                        return None
                    return expected_version + 1

                @staticmethod
                def _admin_state(
                    row: NucleusOrganizationAccountORM, version: int
                ) -> NucleusAccountAdminState:
                    return NucleusAccountAdminState(
                        organization_account_id=row.organization_account_id,
                        login_username=row.user_name,
                        max_user_limit=row.max_user_limit,
                        license_start_date=row.license_start_date,
                        license_end_date=row.license_end_date,
                        status=row.status,
                        approved_by=row.approved_by,
                        approved_date=row.approved_date,
                        rejected_by=row.rejected_by,
                        rejected_date=row.rejected_date,
                        rejection_reason=row.rejection_reason,
                        is_active=row.is_active,
                        version=version,
                    )

                async def get_admin_state(
                    self, organization_code: str
                ) -> NucleusAccountAdminState | None:
                    row = await self._account_row(organization_code)
                    if row is None:
                        return None
                    version = await self._version(
                        "nucleus_account", str(row.organization_account_id)
                    )
                    return self._admin_state(row, version)

                async def get_username_owner_id(self, username: str) -> int | None:
                    return await self._session.scalar(
                        select(NucleusOrganizationAccountORM.organization_account_id).where(
                            func.lower(NucleusOrganizationAccountORM.user_name)
                            == username.lower()
                        )
                    )

                async def _claim_account(
                    self,
                    organization_code: str,
                    expected_version: int,
                ) -> tuple[NucleusOrganizationAccountORM, int] | None:
                    row = await self._account_row(organization_code)
                    if row is None:
                        return None
                    next_version = await self._advance_version(
                        "nucleus_account",
                        str(row.organization_account_id),
                        expected_version,
                    )
                    if next_version is None:
                        return None
                    return row, next_version

                async def update_username_if_version(
                    self,
                    *,
                    organization_code: str,
                    username: str,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    claimed = await self._claim_account(
                        organization_code, expected_version
                    )
                    if claimed is None:
                        return None
                    row, next_version = claimed
                    owner_id = await self.get_username_owner_id(username)
                    if owner_id is not None and owner_id != row.organization_account_id:
                        await self._session.rollback()
                        return None
                    row.user_name = username
                    row.updated_by = actor_id
                    row.updated_date = _utcnow()
                    await self._session.commit()
                    await self._session.refresh(row)
                    return self._admin_state(row, next_version)

                async def update_license_if_version(
                    self,
                    *,
                    organization_code: str,
                    max_user_limit: int,
                    license_start_date: datetime | None,
                    license_end_date: datetime | None,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    claimed = await self._claim_account(
                        organization_code, expected_version
                    )
                    if claimed is None:
                        return None
                    row, next_version = claimed
                    row.max_user_limit = max_user_limit
                    row.license_start_date = license_start_date
                    row.license_end_date = license_end_date
                    row.updated_by = actor_id
                    row.updated_date = _utcnow()
                    await self._session.commit()
                    await self._session.refresh(row)
                    return self._admin_state(row, next_version)

                async def transition_approval_if_version(
                    self,
                    *,
                    organization_code: str,
                    decision: str,
                    reason: str | None,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    claimed = await self._claim_account(
                        organization_code, expected_version
                    )
                    if claimed is None:
                        return None
                    row, next_version = claimed
                    now = _utcnow()
                    if decision == "approved":
                        row.status = "approved"
                        row.approved_by = actor_id
                        row.approved_date = now
                        row.rejected_by = None
                        row.rejected_date = None
                        row.rejection_reason = None
                    elif decision == "rejected":
                        row.status = "rejected"
                        row.is_active = False
                        row.rejected_by = actor_id
                        row.rejected_date = now
                        row.rejection_reason = reason
                        row.approved_by = None
                        row.approved_date = None
                    else:
                        await self._session.rollback()
                        raise ValueError("Unsupported approval decision")
                    row.updated_by = actor_id
                    row.updated_date = now
                    await self._session.commit()
                    await self._session.refresh(row)
                    return self._admin_state(row, next_version)

                async def set_active_if_version(
                    self,
                    *,
                    organization_code: str,
                    is_active: bool,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusAccountAdminState | None:
                    row = await self._account_row(organization_code)
                    if row is None:
                        return None
                    now = _utcnow()
                    if is_active and (
                        row.status != "approved"
                        or (
                            row.license_start_date is not None
                            and row.license_start_date.replace(
                                tzinfo=row.license_start_date.tzinfo or timezone.utc
                            )
                            > now
                        )
                        or (
                            row.license_end_date is not None
                            and row.license_end_date.replace(
                                tzinfo=row.license_end_date.tzinfo or timezone.utc
                            )
                            < now
                        )
                    ):
                        return None
                    claimed = await self._claim_account(
                        organization_code, expected_version
                    )
                    if claimed is None:
                        return None
                    row, next_version = claimed
                    row.is_active = is_active
                    row.updated_by = actor_id
                    row.updated_date = now
                    await self._session.commit()
                    await self._session.refresh(row)
                    return self._admin_state(row, next_version)

                async def _matching_access_row(
                    self,
                    *,
                    organization_account_id: int,
                    spec: _AccessSpec,
                    values: dict[str, int | None],
                ):
                    conditions = [
                        spec.orm_type.organization_account_id
                        == organization_account_id
                    ]
                    for attribute in spec.value_attributes:
                        conditions.append(
                            getattr(spec.orm_type, attribute) == values[attribute]
                        )
                    return await self._session.scalar(
                        select(spec.orm_type)
                        .where(*conditions)
                        .order_by(getattr(spec.orm_type, spec.id_attribute).desc())
                    )

                async def _access_domain(
                    self, spec: _AccessSpec, row
                ) -> NucleusManagedAccess:
                    access_id = int(getattr(row, spec.id_attribute))
                    tombstone = await self._session.get(
                        NucleusAccessTombstoneORM,
                        {"resource_type": spec.resource_type, "access_id": access_id},
                    )
                    version = await self._version(
                        spec.version_resource_type, str(access_id)
                    )
                    return NucleusManagedAccess(
                        resource_type=spec.resource_type,
                        access_id=access_id,
                        organization_account_id=row.organization_account_id,
                        values={
                            attribute: getattr(row, attribute)
                            for attribute in spec.value_attributes
                        },
                        revoked=tombstone is not None,
                        version=version,
                    )

                async def inspect_access(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    values: dict[str, int | None],
                ) -> tuple[NucleusManagedAccess | None, int] | None:
                    spec = self._spec(access_kind)
                    account = await self._account_row(organization_code)
                    if account is None:
                        return None
                    row = await self._matching_access_row(
                        organization_account_id=account.organization_account_id,
                        spec=spec,
                        values=values,
                    )
                    if row is None:
                        return None, 0
                    access = await self._access_domain(spec, row)
                    return access, access.version

                async def get_access(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    access_id: int,
                ) -> NucleusManagedAccess | None:
                    spec = self._spec(access_kind)
                    account = await self._account_row(organization_code)
                    if account is None:
                        return None
                    row = await self._session.get(spec.orm_type, access_id)
                    if (
                        row is None
                        or row.organization_account_id
                        != account.organization_account_id
                    ):
                        return None
                    return await self._access_domain(spec, row)

                @staticmethod
                def _grant_key(
                    spec: _AccessSpec,
                    organization_account_id: int,
                    values: dict[str, int | None],
                ) -> str:
                    payload = json.dumps(
                        {
                            "organization_account_id": organization_account_id,
                            "values": values,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

                async def grant_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    values: dict[str, int | None],
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusManagedAccess | None:
                    del actor_id  # Retained in the action audit; source rows lack actor columns.
                    spec = self._spec(access_kind)
                    account = await self._account_row(organization_code)
                    if account is None:
                        return None
                    existing = await self._matching_access_row(
                        organization_account_id=account.organization_account_id,
                        spec=spec,
                        values=values,
                    )
                    if existing is not None:
                        access = await self._access_domain(spec, existing)
                        if not access.revoked or access.version != expected_version:
                            return None
                        next_version = await self._advance_version(
                            spec.version_resource_type,
                            str(access.access_id),
                            expected_version,
                        )
                        if next_version is None:
                            return None
                        tombstone = await self._session.get(
                            NucleusAccessTombstoneORM,
                            {
                                "resource_type": spec.resource_type,
                                "access_id": access.access_id,
                            },
                        )
                        if tombstone is None:
                            await self._session.rollback()
                            return None
                        await self._session.delete(tombstone)
                        await self._session.commit()
                        return NucleusManagedAccess(
                            resource_type=spec.resource_type,
                            access_id=access.access_id,
                            organization_account_id=access.organization_account_id,
                            values=access.values,
                            revoked=False,
                            version=next_version,
                        )

                    if expected_version != 0:
                        return None
                    intent_type = f"{spec.version_resource_type}:grant"
                    intent_key = self._grant_key(
                        spec, account.organization_account_id, values
                    )
                    self._session.add(
                        NucleusResourceVersionORM(
                            resource_type=intent_type,
                            resource_key=intent_key,
                            version=1,
                            updated_at=_utcnow(),
                        )
                    )
                    row = spec.orm_type(
                        organization_account_id=account.organization_account_id,
                        **values,
                    )
                    self._session.add(row)
                    try:
                        await self._session.flush()
                    except IntegrityError:
                        await self._session.rollback()
                        return None
                    access_id = int(getattr(row, spec.id_attribute))
                    self._session.add(
                        NucleusResourceVersionORM(
                            resource_type=spec.version_resource_type,
                            resource_key=str(access_id),
                            version=1,
                            updated_at=_utcnow(),
                        )
                    )
                    try:
                        await self._session.commit()
                    except IntegrityError:
                        await self._session.rollback()
                        return None
                    return await self.get_access(
                        organization_code=organization_code,
                        access_kind=access_kind,
                        access_id=access_id,
                    )

                async def revoke_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_kind: str,
                    access_id: int,
                    actor_id: int,
                    expected_version: int,
                ) -> NucleusManagedAccess | None:
                    spec = self._spec(access_kind)
                    access = await self.get_access(
                        organization_code=organization_code,
                        access_kind=access_kind,
                        access_id=access_id,
                    )
                    if (
                        access is None
                        or access.revoked
                        or access.version != expected_version
                    ):
                        return None
                    next_version = await self._advance_version(
                        spec.version_resource_type, str(access_id), expected_version
                    )
                    if next_version is None:
                        return None
                    self._session.add(
                        NucleusAccessTombstoneORM(
                            resource_type=spec.resource_type,
                            access_id=access_id,
                            organization_account_id=access.organization_account_id,
                            version=next_version,
                            snapshot_json=access.values,
                            revoked_by=actor_id,
                            revoked_at=_utcnow(),
                        )
                    )
                    try:
                        await self._session.commit()
                    except IntegrityError:
                        await self._session.rollback()
                        return None
                    return NucleusManagedAccess(
                        resource_type=access.resource_type,
                        access_id=access.access_id,
                        organization_account_id=access.organization_account_id,
                        values=access.values,
                        revoked=True,
                        version=next_version,
                    )
            '''
        ),
    )


def add_projection_repository(root: Path) -> None:
    create_exact(
        root,
        "app/repositories/nucleus_administration_projection_repository.py",
        clean(
            '''
            """Coordinate Nucleus license/lifecycle projections in the sandbox."""

            from __future__ import annotations

            from datetime import datetime, timezone

            from sqlalchemy import func, select, update
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.orm_models import (
                OrganizationORM,
                OrganizationOverviewORM,
                OrganizationSeatPoolORM,
                SeatAssignmentORM,
            )
            from app.domain.enums import (
                OrganizationStatus,
                SeatAssignmentStatus,
                SeatPoolStatus,
                SeatType,
            )
            from app.domain.nucleus_admin_models import (
                NucleusLicenseProjectionState,
                NucleusLifecycleProjectionState,
            )


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            class NucleusAdministrationProjectionRepository:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                async def _seat_pool(self, organization_id: str):
                    return await self._session.scalar(
                        select(OrganizationSeatPoolORM).where(
                            OrganizationSeatPoolORM.organization_id == organization_id,
                            OrganizationSeatPoolORM.seat_type == SeatType.STANDARD.value,
                        )
                    )

                async def get_license_projection(
                    self, organization_id: str
                ) -> NucleusLicenseProjectionState | None:
                    pool = await self._seat_pool(organization_id)
                    overview = await self._session.get(
                        OrganizationOverviewORM, organization_id
                    )
                    if pool is None or overview is None:
                        return None
                    active_assignments = int(
                        await self._session.scalar(
                            select(func.count())
                            .select_from(SeatAssignmentORM)
                            .where(
                                SeatAssignmentORM.organization_id == organization_id,
                                SeatAssignmentORM.seat_pool_id == pool.id,
                                SeatAssignmentORM.status
                                == SeatAssignmentStatus.ACTIVE.value,
                            )
                        )
                        or 0
                    )
                    return NucleusLicenseProjectionState(
                        seat_pool_id=pool.id,
                        total_seats=pool.total_seats,
                        starts_at=pool.starts_at,
                        expires_at=pool.expires_at,
                        seat_pool_status=pool.status,
                        seat_pool_version=pool.version,
                        active_assignments=active_assignments,
                        renewal_date=overview.renewal_date,
                        overview_version=overview.version,
                    )

                async def update_license_projection_if_versions(
                    self,
                    *,
                    organization_id: str,
                    max_user_limit: int,
                    license_start_date: datetime | None,
                    license_end_date: datetime | None,
                    expected_seat_pool_version: int,
                    expected_overview_version: int,
                ) -> NucleusLicenseProjectionState | None:
                    state = await self.get_license_projection(organization_id)
                    if (
                        state is None
                        or state.seat_pool_version != expected_seat_pool_version
                        or state.overview_version != expected_overview_version
                        or state.active_assignments > max_user_limit
                    ):
                        return None
                    now = _utcnow()
                    pool_status = state.seat_pool_status
                    if license_end_date is not None:
                        end = license_end_date.replace(
                            tzinfo=license_end_date.tzinfo or timezone.utc
                        )
                        if end < now:
                            pool_status = SeatPoolStatus.EXPIRED.value
                    pool_result = await self._session.execute(
                        update(OrganizationSeatPoolORM)
                        .where(
                            OrganizationSeatPoolORM.id == state.seat_pool_id,
                            OrganizationSeatPoolORM.version
                            == expected_seat_pool_version,
                        )
                        .values(
                            total_seats=max_user_limit,
                            starts_at=license_start_date,
                            expires_at=license_end_date,
                            status=pool_status,
                            version=expected_seat_pool_version + 1,
                            updated_at=now,
                        )
                    )
                    overview_result = await self._session.execute(
                        update(OrganizationOverviewORM)
                        .where(
                            OrganizationOverviewORM.organization_id == organization_id,
                            OrganizationOverviewORM.version == expected_overview_version,
                        )
                        .values(
                            renewal_date=(
                                license_end_date.date()
                                if license_end_date is not None
                                else None
                            ),
                            version=expected_overview_version + 1,
                            updated_at=now,
                        )
                    )
                    if pool_result.rowcount != 1 or overview_result.rowcount != 1:
                        await self._session.rollback()
                        return None
                    await self._session.commit()
                    return await self.get_license_projection(organization_id)

                async def get_lifecycle_projection(
                    self, organization_id: str
                ) -> NucleusLifecycleProjectionState | None:
                    organization = await self._session.get(
                        OrganizationORM, organization_id
                    )
                    pool = await self._seat_pool(organization_id)
                    if organization is None or pool is None:
                        return None
                    return NucleusLifecycleProjectionState(
                        organization_status=organization.status,
                        organization_version=organization.version,
                        seat_pool_id=pool.id,
                        seat_pool_status=pool.status,
                        seat_pool_version=pool.version,
                    )

                async def update_lifecycle_projection_if_versions(
                    self,
                    *,
                    organization_id: str,
                    should_be_active: bool,
                    license_end_date: datetime | None,
                    expected_organization_version: int,
                    expected_seat_pool_version: int,
                ) -> NucleusLifecycleProjectionState | None:
                    state = await self.get_lifecycle_projection(organization_id)
                    if (
                        state is None
                        or state.organization_version
                        != expected_organization_version
                        or state.seat_pool_version != expected_seat_pool_version
                    ):
                        return None
                    now = _utcnow()
                    expired = False
                    if license_end_date is not None:
                        expired = license_end_date.replace(
                            tzinfo=license_end_date.tzinfo or timezone.utc
                        ) < now
                    target_org_status = (
                        OrganizationStatus.ACTIVE.value
                        if should_be_active and not expired
                        else OrganizationStatus.SUSPENDED.value
                    )
                    target_pool_status = (
                        SeatPoolStatus.EXPIRED.value
                        if expired
                        else (
                            SeatPoolStatus.ACTIVE.value
                            if should_be_active
                            else SeatPoolStatus.SUSPENDED.value
                        )
                    )
                    org_result = await self._session.execute(
                        update(OrganizationORM)
                        .where(
                            OrganizationORM.id == organization_id,
                            OrganizationORM.version == expected_organization_version,
                        )
                        .values(
                            status=target_org_status,
                            version=expected_organization_version + 1,
                            updated_at=now,
                        )
                    )
                    pool_result = await self._session.execute(
                        update(OrganizationSeatPoolORM)
                        .where(
                            OrganizationSeatPoolORM.id == state.seat_pool_id,
                            OrganizationSeatPoolORM.version
                            == expected_seat_pool_version,
                        )
                        .values(
                            status=target_pool_status,
                            version=expected_seat_pool_version + 1,
                            updated_at=now,
                        )
                    )
                    if org_result.rowcount != 1 or pool_result.rowcount != 1:
                        await self._session.rollback()
                        return None
                    await self._session.commit()
                    return await self.get_lifecycle_projection(organization_id)
            '''
        ),
    )


def add_admin_handlers(root: Path) -> None:
    create_exact(
        root,
        "app/agent/nucleus_admin_action_handlers.py",
        clean(
            '''
            """Approval-gated Nucleus administrative and entitlement actions."""

            from __future__ import annotations

            from dataclasses import dataclass
            from datetime import datetime, timezone
            import re

            from app.adapters.nucleus.admin_contract import (
                NucleusAdministrationGateway,
                NucleusAdministrationProjectionGateway,
            )
            from app.agent.action_contracts import (
                AgentActionChange,
                AgentActionExecutionContext,
                AgentActionExecutionResult,
                AgentActionHandlerResult,
                AgentActionPreparation,
                AgentActionProposal,
                AgentActionResourcePrecondition,
            )
            from app.agent.action_handlers import StaleActionResourceError
            from app.domain.nucleus_admin_models import (
                NucleusAccountAdminState,
                NucleusLicenseProjectionState,
                NucleusLifecycleProjectionState,
                managed_access_snapshot,
            )

            _USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,149}$")
            _NULL_SENTINELS = {"null", "none", "-"}


            def _required_actor(context: AgentActionExecutionContext) -> int:
                if context.nucleus_actor_id is None:
                    raise ValueError("Authenticated executor has no Nucleus actor mapping")
                return context.nucleus_actor_id


            def _precondition(
                proposal: AgentActionProposal,
                resource_type: str,
                resource_id: str | None = None,
            ) -> AgentActionResourcePrecondition:
                matches = [
                    item
                    for item in proposal.resource_preconditions
                    if item.resource_type == resource_type
                    and (resource_id is None or item.resource_id == resource_id)
                ]
                if len(matches) != 1:
                    raise ValueError("Action resource precondition is missing or ambiguous")
                return matches[0]


            def _change(proposal: AgentActionProposal, field: str) -> AgentActionChange:
                matches = [item for item in proposal.changes if item.field == field]
                if len(matches) != 1:
                    raise ValueError("Reviewed action change is missing or ambiguous")
                return matches[0]


            def _normalize_username(value: str) -> str:
                normalized = value.strip().lower()
                if not _USERNAME_PATTERN.fullmatch(normalized):
                    raise ValueError(
                        "Username must be 3-150 lowercase letters, numbers, dots, underscores, or hyphens"
                    )
                return normalized


            def _parse_datetime(value: str, *, field_name: str) -> datetime | None:
                normalized = value.strip().lower()
                if normalized in _NULL_SENTINELS:
                    return None
                raw = value.strip().replace("Z", "+00:00")
                try:
                    parsed = datetime.fromisoformat(raw)
                except ValueError as exception:
                    raise ValueError(f"{field_name} must be ISO-8601 or null") from exception
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)


            def _datetime_argument(value: datetime | None) -> str:
                if value is None:
                    return "null"
                aware = value.replace(tzinfo=value.tzinfo or timezone.utc)
                return aware.astimezone(timezone.utc).isoformat()


            def _date_argument(value) -> str:
                return "null" if value is None else value.isoformat()


            def _positive_int(value: str, *, field_name: str) -> int:
                try:
                    parsed = int(value.strip())
                except ValueError as exception:
                    raise ValueError(f"{field_name} must be an integer") from exception
                if parsed <= 0:
                    raise ValueError(f"{field_name} must be positive")
                return parsed


            def _nullable_positive_int(value: str, *, field_name: str) -> int | None:
                if value.strip().lower() in _NULL_SENTINELS:
                    return None
                return _positive_int(value, field_name=field_name)


            def _admin_before(state: NucleusAccountAdminState) -> dict:
                return {
                    "login_username": state.login_username,
                    "max_user_limit": state.max_user_limit,
                    "license_start_date": state.license_start_date,
                    "license_end_date": state.license_end_date,
                    "status": state.status,
                    "approved_by": state.approved_by,
                    "approved_date": state.approved_date,
                    "rejected_by": state.rejected_by,
                    "rejected_date": state.rejected_date,
                    "rejection_reason": state.rejection_reason,
                    "is_active": state.is_active,
                    "version": state.version,
                }


            class UpdateNucleusOrganizationUsernameHandler:
                requires_execution_context = True

                def __init__(self, gateway: NucleusAdministrationGateway) -> None:
                    self._gateway = gateway

                async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
                    username = _normalize_username(arguments["username"])
                    state = await self._gateway.get_admin_state(organization_id)
                    if state is None:
                        raise ValueError("Nucleus organization account was not found")
                    owner_id = await self._gateway.get_username_owner_id(username)
                    if owner_id is not None and owner_id != state.organization_account_id:
                        raise ValueError("Username is already assigned")
                    if state.login_username == username:
                        raise ValueError("Username already has this value")
                    return AgentActionPreparation(
                        normalized_arguments={"username": username},
                        changes=(AgentActionChange(field="UserName", before=state.login_username, after=username),),
                        observed_resource_version=state.version,
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                    )

                async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
                    actor_id = _required_actor(context)
                    precondition = _precondition(proposal, "OrganizationAccount")
                    updated = await self._gateway.update_username_if_version(
                        organization_code=proposal.organization_id,
                        username=proposal.arguments["username"],
                        actor_id=actor_id,
                        expected_version=precondition.observed_version,
                    )
                    if updated is None:
                        raise StaleActionResourceError()
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(updated.organization_account_id),
                        before={"username": _change(proposal, "UserName").before, "version": precondition.observed_version},
                        after={"username": updated.login_username, "version": updated.version, "updated_by": actor_id},
                    )

                async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
                    state = await self._gateway.get_admin_state(proposal.organization_id)
                    if state is None or state.login_username != proposal.arguments["username"]:
                        return None
                    precondition = _precondition(proposal, "OrganizationAccount")
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                        before={"username": _change(proposal, "UserName").before, "version": precondition.observed_version},
                        after={"username": state.login_username, "version": state.version, "updated_by": context.nucleus_actor_id},
                    )


            class UpdateNucleusOrganizationLicenseHandler:
                requires_execution_context = True

                def __init__(self, gateway: NucleusAdministrationGateway, projections: NucleusAdministrationProjectionGateway) -> None:
                    self._gateway = gateway
                    self._projections = projections

                async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
                    max_user_limit = _positive_int(arguments["max_user_limit"], field_name="max_user_limit")
                    start = _parse_datetime(arguments["license_start_date"], field_name="license_start_date")
                    end = _parse_datetime(arguments["license_end_date"], field_name="license_end_date")
                    if start is not None and end is not None and end < start:
                        raise ValueError("License end date must not precede start date")
                    state = await self._gateway.get_admin_state(organization_id)
                    projection = await self._projections.get_license_projection(organization_id)
                    if state is None or projection is None:
                        raise ValueError("Nucleus license projection was not found")
                    if projection.active_assignments > max_user_limit:
                        raise ValueError("Max user limit cannot be below active seat assignments")
                    target_renewal = end.date() if end is not None else None
                    if (
                        state.max_user_limit == max_user_limit
                        and _datetime_argument(state.license_start_date) == _datetime_argument(start)
                        and _datetime_argument(state.license_end_date) == _datetime_argument(end)
                        and projection.total_seats == max_user_limit
                        and _datetime_argument(projection.starts_at) == _datetime_argument(start)
                        and _datetime_argument(projection.expires_at) == _datetime_argument(end)
                        and _date_argument(projection.renewal_date) == _date_argument(target_renewal)
                    ):
                        raise ValueError("License already has these values")
                    return AgentActionPreparation(
                        normalized_arguments={
                            "max_user_limit": str(max_user_limit),
                            "license_start_date": _datetime_argument(start),
                            "license_end_date": _datetime_argument(end),
                        },
                        changes=(
                            AgentActionChange(field="MaxUserLimit", before=state.max_user_limit, after=max_user_limit),
                            AgentActionChange(field="LicenseStartDate", before=_datetime_argument(state.license_start_date), after=_datetime_argument(start)),
                            AgentActionChange(field="LicenseEndDate", before=_datetime_argument(state.license_end_date), after=_datetime_argument(end)),
                            AgentActionChange(field="organization_seat_pool.total_seats", before=projection.total_seats, after=max_user_limit),
                            AgentActionChange(field="organization_seat_pool.starts_at", before=_datetime_argument(projection.starts_at), after=_datetime_argument(start)),
                            AgentActionChange(field="organization_seat_pool.expires_at", before=_datetime_argument(projection.expires_at), after=_datetime_argument(end)),
                            AgentActionChange(field="organization_overview.renewal_date", before=_date_argument(projection.renewal_date), after=_date_argument(target_renewal)),
                        ),
                        observed_resource_version=state.version,
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                        resource_preconditions=(
                            AgentActionResourcePrecondition(resource_type="OrganizationAccount", resource_id=str(state.organization_account_id), observed_version=state.version),
                            AgentActionResourcePrecondition(resource_type="organization_seat_pool", resource_id=projection.seat_pool_id, observed_version=projection.seat_pool_version),
                            AgentActionResourcePrecondition(resource_type="organization_overview", resource_id=organization_id, observed_version=projection.overview_version),
                        ),
                    )

                @staticmethod
                def _targets(proposal: AgentActionProposal) -> tuple[int, datetime | None, datetime | None]:
                    return (
                        int(proposal.arguments["max_user_limit"]),
                        _parse_datetime(proposal.arguments["license_start_date"], field_name="license_start_date"),
                        _parse_datetime(proposal.arguments["license_end_date"], field_name="license_end_date"),
                    )

                async def _apply_projection(self, proposal: AgentActionProposal) -> NucleusLicenseProjectionState | None:
                    max_limit, start, end = self._targets(proposal)
                    current = await self._projections.get_license_projection(proposal.organization_id)
                    if current is None:
                        return None
                    target_renewal = end.date() if end is not None else None
                    if (
                        current.total_seats == max_limit
                        and _datetime_argument(current.starts_at) == _datetime_argument(start)
                        and _datetime_argument(current.expires_at) == _datetime_argument(end)
                        and _date_argument(current.renewal_date) == _date_argument(target_renewal)
                    ):
                        return current
                    pool_precondition = _precondition(proposal, "organization_seat_pool")
                    overview_precondition = _precondition(proposal, "organization_overview")
                    if (
                        current.seat_pool_version != pool_precondition.observed_version
                        or current.overview_version != overview_precondition.observed_version
                        or current.total_seats != _change(proposal, "organization_seat_pool.total_seats").before
                        or _datetime_argument(current.starts_at) != _change(proposal, "organization_seat_pool.starts_at").before
                        or _datetime_argument(current.expires_at) != _change(proposal, "organization_seat_pool.expires_at").before
                        or _date_argument(current.renewal_date) != _change(proposal, "organization_overview.renewal_date").before
                    ):
                        return None
                    return await self._projections.update_license_projection_if_versions(
                        organization_id=proposal.organization_id,
                        max_user_limit=max_limit,
                        license_start_date=start,
                        license_end_date=end,
                        expected_seat_pool_version=current.seat_pool_version,
                        expected_overview_version=current.overview_version,
                    )

                async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
                    actor_id = _required_actor(context)
                    max_limit, start, end = self._targets(proposal)
                    account_precondition = _precondition(proposal, "OrganizationAccount")
                    updated = await self._gateway.update_license_if_version(
                        organization_code=proposal.organization_id,
                        max_user_limit=max_limit,
                        license_start_date=start,
                        license_end_date=end,
                        actor_id=actor_id,
                        expected_version=account_precondition.observed_version,
                    )
                    if updated is None:
                        raise StaleActionResourceError()
                    projection = await self._apply_projection(proposal)
                    if projection is None:
                        raise RuntimeError("License projection requires reconciliation")
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(updated.organization_account_id),
                        before={
                            "max_user_limit": _change(proposal, "MaxUserLimit").before,
                            "license_start_date": _change(proposal, "LicenseStartDate").before,
                            "license_end_date": _change(proposal, "LicenseEndDate").before,
                            "version": account_precondition.observed_version,
                        },
                        after={
                            "max_user_limit": updated.max_user_limit,
                            "license_start_date": updated.license_start_date,
                            "license_end_date": updated.license_end_date,
                            "version": updated.version,
                            "seat_pool_version": projection.seat_pool_version,
                            "overview_version": projection.overview_version,
                            "updated_by": actor_id,
                        },
                    )

                async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
                    max_limit, start, end = self._targets(proposal)
                    state = await self._gateway.get_admin_state(proposal.organization_id)
                    if state is None or (
                        state.max_user_limit != max_limit
                        or _datetime_argument(state.license_start_date) != _datetime_argument(start)
                        or _datetime_argument(state.license_end_date) != _datetime_argument(end)
                    ):
                        return None
                    projection = await self._apply_projection(proposal)
                    if projection is None:
                        return None
                    account_precondition = _precondition(proposal, "OrganizationAccount")
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                        before={
                            "max_user_limit": _change(proposal, "MaxUserLimit").before,
                            "license_start_date": _change(proposal, "LicenseStartDate").before,
                            "license_end_date": _change(proposal, "LicenseEndDate").before,
                            "version": account_precondition.observed_version,
                        },
                        after={
                            "max_user_limit": state.max_user_limit,
                            "license_start_date": state.license_start_date,
                            "license_end_date": state.license_end_date,
                            "version": state.version,
                            "seat_pool_version": projection.seat_pool_version,
                            "overview_version": projection.overview_version,
                            "updated_by": context.nucleus_actor_id,
                        },
                    )


            class NucleusOrganizationLifecycleHandler:
                requires_execution_context = True

                def __init__(self, gateway: NucleusAdministrationGateway, projections: NucleusAdministrationProjectionGateway, mode: str) -> None:
                    self._gateway = gateway
                    self._projections = projections
                    self._mode = mode

                def _target(self, state: NucleusAccountAdminState, reason: str | None) -> dict:
                    target = {
                        "status": state.status,
                        "is_active": state.is_active,
                        "approved_by": state.approved_by,
                        "approved_date": state.approved_date,
                        "rejected_by": state.rejected_by,
                        "rejected_date": state.rejected_date,
                        "rejection_reason": state.rejection_reason,
                    }
                    if self._mode == "approve":
                        target.update(status="approved", approved_by="$executor", approved_date="$execution_time", rejected_by=None, rejected_date=None, rejection_reason=None)
                    elif self._mode == "reject":
                        target.update(status="rejected", is_active=False, approved_by=None, approved_date=None, rejected_by="$executor", rejected_date="$execution_time", rejection_reason=reason)
                    elif self._mode == "activate":
                        if state.status != "approved":
                            raise ValueError("Only an approved organization account can be activated")
                        now = datetime.now(timezone.utc)
                        if (
                            state.license_start_date is not None
                            and state.license_start_date.replace(
                                tzinfo=state.license_start_date.tzinfo or timezone.utc
                            )
                            > now
                        ):
                            raise ValueError("Future organization license cannot be activated")
                        if (
                            state.license_end_date is not None
                            and state.license_end_date.replace(
                                tzinfo=state.license_end_date.tzinfo or timezone.utc
                            )
                            < now
                        ):
                            raise ValueError("Expired organization license cannot be activated")
                        target["is_active"] = True
                    elif self._mode == "deactivate":
                        target["is_active"] = False
                    else:
                        raise ValueError("Unsupported lifecycle mode")
                    return target

                async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
                    reason = None
                    normalized_arguments: dict[str, str] = {}
                    if self._mode == "reject":
                        reason = arguments["reason"].strip()
                        if not reason or len(reason) > 500:
                            raise ValueError("Rejection reason must be 1-500 characters")
                        normalized_arguments["reason"] = reason
                    state = await self._gateway.get_admin_state(organization_id)
                    projection = await self._projections.get_lifecycle_projection(organization_id)
                    if state is None or projection is None:
                        raise ValueError("Nucleus lifecycle projection was not found")
                    target = self._target(state, reason)
                    now = datetime.now(timezone.utc)
                    license_started = (
                        state.license_start_date is None
                        or state.license_start_date.replace(
                            tzinfo=state.license_start_date.tzinfo or timezone.utc
                        )
                        <= now
                    )
                    license_unexpired = (
                        state.license_end_date is None
                        or state.license_end_date.replace(
                            tzinfo=state.license_end_date.tzinfo or timezone.utc
                        )
                        >= now
                    )
                    should_be_active = (
                        target["status"] == "approved"
                        and bool(target["is_active"])
                        and license_started
                        and license_unexpired
                    )
                    target_org_status = "active" if should_be_active else "suspended"
                    target_pool_status = "active" if should_be_active else "suspended"
                    if not license_unexpired:
                        target_pool_status = "expired"
                    if self._mode == "approve" and (
                        state.status == "approved"
                        and state.rejected_by is None
                        and state.rejected_date is None
                        and state.rejection_reason is None
                    ):
                        raise ValueError("Organization account is already approved")
                    if self._mode == "reject" and (
                        state.status == "rejected"
                        and state.is_active is False
                        and state.rejection_reason == reason
                    ):
                        raise ValueError("Organization account is already rejected")
                    if (
                        state.status == target["status"]
                        and state.is_active == target["is_active"]
                        and (self._mode not in {"approve", "reject"})
                        and projection.organization_status == target_org_status
                        and projection.seat_pool_status == target_pool_status
                    ):
                        raise ValueError("Organization lifecycle already has this state")
                    changes = [
                        AgentActionChange(field="Status", before=state.status, after=target["status"]),
                        AgentActionChange(field="IsActive", before=state.is_active, after=target["is_active"]),
                    ]
                    if self._mode in {"approve", "reject"}:
                        for field, attr in (
                            ("ApprovedBy", "approved_by"),
                            ("ApprovedDate", "approved_date"),
                            ("RejectedBy", "rejected_by"),
                            ("RejectedDate", "rejected_date"),
                            ("RejectionReason", "rejection_reason"),
                        ):
                            before_value = getattr(state, attr)
                            after_value = target[attr]
                            if attr in {"approved_date", "rejected_date"}:
                                before_value = _datetime_argument(before_value)
                                if isinstance(after_value, datetime):
                                    after_value = _datetime_argument(after_value)
                            changes.append(
                                AgentActionChange(
                                    field=field,
                                    before=before_value,
                                    after=after_value,
                                )
                            )
                    changes.extend(
                        (
                            AgentActionChange(field="organization.status", before=projection.organization_status, after=target_org_status),
                            AgentActionChange(field="organization_seat_pool.status", before=projection.seat_pool_status, after=target_pool_status),
                        )
                    )
                    return AgentActionPreparation(
                        normalized_arguments=normalized_arguments,
                        changes=tuple(changes),
                        observed_resource_version=state.version,
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                        resource_preconditions=(
                            AgentActionResourcePrecondition(resource_type="OrganizationAccount", resource_id=str(state.organization_account_id), observed_version=state.version),
                            AgentActionResourcePrecondition(resource_type="organization", resource_id=organization_id, observed_version=projection.organization_version),
                            AgentActionResourcePrecondition(resource_type="organization_seat_pool", resource_id=projection.seat_pool_id, observed_version=projection.seat_pool_version),
                        ),
                    )

                async def _apply_projection(self, proposal: AgentActionProposal, state: NucleusAccountAdminState) -> NucleusLifecycleProjectionState | None:
                    current = await self._projections.get_lifecycle_projection(proposal.organization_id)
                    if current is None:
                        return None
                    now = datetime.now(timezone.utc)
                    license_started = (
                        state.license_start_date is None
                        or state.license_start_date.replace(
                            tzinfo=state.license_start_date.tzinfo or timezone.utc
                        )
                        <= now
                    )
                    license_unexpired = (
                        state.license_end_date is None
                        or state.license_end_date.replace(
                            tzinfo=state.license_end_date.tzinfo or timezone.utc
                        )
                        >= now
                    )
                    should_be_active = (
                        state.status == "approved"
                        and state.is_active
                        and license_started
                        and license_unexpired
                    )
                    target_org_status = "active" if should_be_active else "suspended"
                    target_pool_status = "active" if should_be_active else "suspended"
                    if not license_unexpired:
                        target_pool_status = "expired"
                    if current.organization_status == target_org_status and current.seat_pool_status == target_pool_status:
                        return current
                    org_precondition = _precondition(proposal, "organization")
                    pool_precondition = _precondition(proposal, "organization_seat_pool")
                    if (
                        current.organization_version != org_precondition.observed_version
                        or current.seat_pool_version != pool_precondition.observed_version
                        or current.organization_status != _change(proposal, "organization.status").before
                        or current.seat_pool_status != _change(proposal, "organization_seat_pool.status").before
                    ):
                        return None
                    return await self._projections.update_lifecycle_projection_if_versions(
                        organization_id=proposal.organization_id,
                        should_be_active=should_be_active,
                        license_end_date=state.license_end_date,
                        expected_organization_version=current.organization_version,
                        expected_seat_pool_version=current.seat_pool_version,
                    )

                async def _apply_canonical(self, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> NucleusAccountAdminState | None:
                    actor_id = _required_actor(context)
                    precondition = _precondition(proposal, "OrganizationAccount")
                    if self._mode in {"approve", "reject"}:
                        return await self._gateway.transition_approval_if_version(
                            organization_code=proposal.organization_id,
                            decision="approved" if self._mode == "approve" else "rejected",
                            reason=proposal.arguments.get("reason"),
                            actor_id=actor_id,
                            expected_version=precondition.observed_version,
                        )
                    return await self._gateway.set_active_if_version(
                        organization_code=proposal.organization_id,
                        is_active=self._mode == "activate",
                        actor_id=actor_id,
                        expected_version=precondition.observed_version,
                    )

                def _canonical_matches(self, state: NucleusAccountAdminState, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> bool:
                    if self._mode == "approve":
                        return state.status == "approved" and state.approved_by == context.nucleus_actor_id and state.rejected_by is None and state.rejection_reason is None
                    if self._mode == "reject":
                        return state.status == "rejected" and not state.is_active and state.rejected_by == context.nucleus_actor_id and state.rejection_reason == proposal.arguments["reason"]
                    if self._mode == "activate":
                        return state.status == "approved" and state.is_active
                    return not state.is_active

                async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
                    actor_id = _required_actor(context)
                    updated = await self._apply_canonical(proposal, context)
                    if updated is None:
                        raise StaleActionResourceError()
                    projection = await self._apply_projection(proposal, updated)
                    if projection is None:
                        raise RuntimeError("Lifecycle projection requires reconciliation")
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(updated.organization_account_id),
                        before={
                            "status": _change(proposal, "Status").before,
                            "is_active": _change(proposal, "IsActive").before,
                            "version": _precondition(proposal, "OrganizationAccount").observed_version,
                        },
                        after={
                            **_admin_before(updated),
                            "organization_status": projection.organization_status,
                            "seat_pool_status": projection.seat_pool_status,
                            "updated_by": actor_id,
                        },
                    )

                async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
                    state = await self._gateway.get_admin_state(proposal.organization_id)
                    if state is None or not self._canonical_matches(state, proposal, context):
                        return None
                    projection = await self._apply_projection(proposal, state)
                    if projection is None:
                        return None
                    return AgentActionHandlerResult(
                        resource_type="OrganizationAccount",
                        resource_id=str(state.organization_account_id),
                        before={
                            "status": _change(proposal, "Status").before,
                            "is_active": _change(proposal, "IsActive").before,
                            "version": _precondition(proposal, "OrganizationAccount").observed_version,
                        },
                        after={
                            **_admin_before(state),
                            "organization_status": projection.organization_status,
                            "seat_pool_status": projection.seat_pool_status,
                            "updated_by": context.nucleus_actor_id,
                        },
                    )


            @dataclass(frozen=True)
            class NucleusAccessActionSpec:
                access_kind: str
                resource_type: str
                argument_fields: tuple[str, ...]
                value_fields: tuple[str, ...]
                nullable_fields: frozenset[str] = frozenset()

                def parse(self, arguments: dict[str, str]) -> dict[str, int | None]:
                    values: dict[str, int | None] = {}
                    for argument, field in zip(self.argument_fields, self.value_fields, strict=True):
                        values[field] = (
                            _nullable_positive_int(arguments[argument], field_name=argument)
                            if argument in self.nullable_fields
                            else _positive_int(arguments[argument], field_name=argument)
                        )
                    return values

                def normalize(self, values: dict[str, int | None]) -> dict[str, str]:
                    return {
                        argument: "null" if values[field] is None else str(values[field])
                        for argument, field in zip(self.argument_fields, self.value_fields, strict=True)
                    }


            COMPANY_PROFILE_ACCESS = NucleusAccessActionSpec(
                access_kind="company_profile",
                resource_type="OrganizationCompanyProfileAccess",
                argument_fields=("company_id",),
                value_fields=("company_id",),
            )
            DRUG_ACCESS = NucleusAccessActionSpec(
                access_kind="drug",
                resource_type="OrganizationDrugAccess",
                argument_fields=("drug_id",),
                value_fields=("drug_id",),
            )
            INDICATION_ACCESS = NucleusAccessActionSpec(
                access_kind="indication",
                resource_type="OrganizationIndicationAccess",
                argument_fields=("indication_id",),
                value_fields=("indication_id",),
            )
            MARKET_ACCESS = NucleusAccessActionSpec(
                access_kind="market",
                resource_type="OrganizationMarketAccess",
                argument_fields=("market_id", "market_sample_id"),
                value_fields=("market_id", "market_sample_id"),
                nullable_fields=frozenset({"market_sample_id"}),
            )


            class GrantNucleusManagedAccessHandler:
                requires_execution_context = True

                def __init__(self, gateway: NucleusAdministrationGateway, spec: NucleusAccessActionSpec) -> None:
                    self._gateway = gateway
                    self._spec = spec

                async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
                    values = self._spec.parse(arguments)
                    inspected = await self._gateway.inspect_access(
                        organization_code=organization_id,
                        access_kind=self._spec.access_kind,
                        values=values,
                    )
                    if inspected is None:
                        raise ValueError("Nucleus organization account was not found")
                    existing, version = inspected
                    if existing is not None and not existing.revoked:
                        raise ValueError("Nucleus access is already granted")
                    resource_id = (
                        str(existing.access_id)
                        if existing is not None
                        else "new:" + ":".join(str(values[field]) for field in self._spec.value_fields)
                    )
                    before = managed_access_snapshot(existing) if existing is not None else None
                    return AgentActionPreparation(
                        normalized_arguments=self._spec.normalize(values),
                        changes=(AgentActionChange(field="access", before=before, after={**values, "revoked": False}),),
                        observed_resource_version=version,
                        resource_type=self._spec.resource_type,
                        resource_id=resource_id,
                    )

                async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
                    values = self._spec.parse(proposal.arguments)
                    updated = await self._gateway.grant_access_if_version(
                        organization_code=proposal.organization_id,
                        access_kind=self._spec.access_kind,
                        values=values,
                        actor_id=_required_actor(context),
                        expected_version=proposal.observed_resource_version,
                    )
                    if updated is None:
                        raise StaleActionResourceError()
                    return AgentActionHandlerResult(
                        resource_type=self._spec.resource_type,
                        resource_id=str(updated.access_id),
                        before=_change(proposal, "access").before or {**values, "revoked": True, "version": proposal.observed_resource_version},
                        after=managed_access_snapshot(updated),
                    )

                async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
                    values = self._spec.parse(proposal.arguments)
                    inspected = await self._gateway.inspect_access(
                        organization_code=proposal.organization_id,
                        access_kind=self._spec.access_kind,
                        values=values,
                    )
                    if inspected is None or inspected[0] is None or inspected[0].revoked:
                        return None
                    access = inspected[0]
                    return AgentActionHandlerResult(
                        resource_type=self._spec.resource_type,
                        resource_id=str(access.access_id),
                        before=_change(proposal, "access").before or {**values, "revoked": True, "version": proposal.observed_resource_version},
                        after=managed_access_snapshot(access),
                    )


            class RevokeNucleusManagedAccessHandler:
                requires_execution_context = True

                def __init__(self, gateway: NucleusAdministrationGateway, spec: NucleusAccessActionSpec) -> None:
                    self._gateway = gateway
                    self._spec = spec

                async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
                    access_id = _positive_int(arguments["access_id"], field_name="access_id")
                    access = await self._gateway.get_access(
                        organization_code=organization_id,
                        access_kind=self._spec.access_kind,
                        access_id=access_id,
                    )
                    if access is None:
                        raise ValueError("Nucleus access row was not found")
                    if access.revoked:
                        raise ValueError("Nucleus access is already revoked")
                    return AgentActionPreparation(
                        normalized_arguments={"access_id": str(access_id)},
                        changes=(AgentActionChange(field="access", before=managed_access_snapshot(access), after={**access.values, "access_id": access.access_id, "revoked": True}),),
                        observed_resource_version=access.version,
                        resource_type=self._spec.resource_type,
                        resource_id=str(access.access_id),
                    )

                async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
                    access_id = int(proposal.arguments["access_id"])
                    updated = await self._gateway.revoke_access_if_version(
                        organization_code=proposal.organization_id,
                        access_kind=self._spec.access_kind,
                        access_id=access_id,
                        actor_id=_required_actor(context),
                        expected_version=proposal.observed_resource_version,
                    )
                    if updated is None:
                        raise StaleActionResourceError()
                    return AgentActionHandlerResult(
                        resource_type=self._spec.resource_type,
                        resource_id=str(updated.access_id),
                        before=_change(proposal, "access").before,
                        after=managed_access_snapshot(updated),
                    )

                async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
                    access = await self._gateway.get_access(
                        organization_code=proposal.organization_id,
                        access_kind=self._spec.access_kind,
                        access_id=int(proposal.arguments["access_id"]),
                    )
                    if access is None or not access.revoked:
                        return None
                    return AgentActionHandlerResult(
                        resource_type=self._spec.resource_type,
                        resource_id=str(access.access_id),
                        before=_change(proposal, "access").before,
                        after=managed_access_snapshot(access),
                    )
            '''
        ),
    )


def add_migration(root: Path) -> None:
    create_exact(
        root,
        "alembic/versions/0013_nucleus_admin.py",
        clean(
            '''
            """add Nucleus administrative control sidecars

            Revision ID: 0013_nucleus_admin
            Revises: 0012_resource_preconditions
            Create Date: 2026-07-18
            """

            from __future__ import annotations

            from typing import Sequence, Union

            import sqlalchemy as sa
            from alembic import op

            revision: str = "0013_nucleus_admin"
            down_revision: Union[str, None] = "0012_resource_preconditions"
            branch_labels: Union[str, Sequence[str], None] = None
            depends_on: Union[str, Sequence[str], None] = None


            def upgrade() -> None:
                op.create_table(
                    "nucleus_actor_mappings",
                    sa.Column("workplace_user_id", sa.String(), nullable=False),
                    sa.Column("nucleus_actor_id", sa.Integer(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ["workplace_user_id"], ["users.id"], ondelete="CASCADE"
                    ),
                    sa.PrimaryKeyConstraint("workplace_user_id"),
                    sa.UniqueConstraint(
                        "nucleus_actor_id", name="uq_nucleus_actor_mapping_actor"
                    ),
                )
                op.create_table(
                    "nucleus_access_tombstones",
                    sa.Column("resource_type", sa.String(length=80), nullable=False),
                    sa.Column("access_id", sa.Integer(), nullable=False),
                    sa.Column("organization_account_id", sa.Integer(), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("snapshot_json", sa.JSON(), nullable=False),
                    sa.Column("revoked_by", sa.Integer(), nullable=False),
                    sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ["organization_account_id"],
                        ["OrganizationAccount.OrganizationAccountId"],
                        ondelete="CASCADE",
                    ),
                    sa.PrimaryKeyConstraint("resource_type", "access_id"),
                    sa.UniqueConstraint(
                        "resource_type", "access_id", name="uq_nucleus_access_tombstone"
                    ),
                )
                op.create_index(
                    "ix_nucleus_access_tombstone_org",
                    "nucleus_access_tombstones",
                    ["organization_account_id", "resource_type"],
                    unique=False,
                )
                with op.batch_alter_table("agent_action_executions") as batch_op:
                    batch_op.add_column(
                        sa.Column("executed_by_user_id", sa.String(), nullable=True)
                    )
                    batch_op.add_column(
                        sa.Column("nucleus_actor_id", sa.Integer(), nullable=True)
                    )

                connection = op.get_bind()
                connection.execute(
                    sa.text(
                        "UPDATE agent_action_executions "
                        "SET executed_by_user_id = ("
                        "SELECT requested_by_user_id FROM agent_action_proposals "
                        "WHERE agent_action_proposals.id = "
                        "agent_action_executions.proposal_id) "
                        "WHERE executed_by_user_id IS NULL"
                    )
                )
                with op.batch_alter_table("agent_action_executions") as batch_op:
                    batch_op.alter_column(
                        "executed_by_user_id",
                        existing_type=sa.String(),
                        nullable=False,
                    )
                    batch_op.create_foreign_key(
                        "fk_agent_action_execution_executor",
                        "users",
                        ["executed_by_user_id"],
                        ["id"],
                    )




            def downgrade() -> None:
                with op.batch_alter_table("agent_action_executions") as batch_op:
                    batch_op.drop_constraint(
                        "fk_agent_action_execution_executor", type_="foreignkey"
                    )
                    batch_op.drop_column("nucleus_actor_id")
                    batch_op.drop_column("executed_by_user_id")
                op.drop_index(
                    "ix_nucleus_access_tombstone_org",
                    table_name="nucleus_access_tombstones",
                )
                op.drop_table("nucleus_access_tombstones")
                op.drop_table("nucleus_actor_mappings")
            '''
        ),
    )


def patch_model_imports(root: Path) -> None:
    replace_exact(
        root,
        "alembic/env.py",
        "from app.db import action_models, nucleus_models, orm_models  # noqa: F401\n",
        "from app.db import action_models, nucleus_admin_models, nucleus_models, orm_models  # noqa: F401\n",
    )
    replace_exact(
        root,
        "tests/conftest.py",
        "from app.db import action_models, nucleus_models, orm_models  # noqa: F401\n",
        "from app.db import action_models, nucleus_admin_models, nucleus_models, orm_models  # noqa: F401\n",
    )


def patch_action_contracts(root: Path) -> None:
    path = "app/agent/action_contracts.py"
    replace_exact(
        root,
        path,
        "    supports_dry_run: bool\n    approval_policy: AgentApprovalPolicy\n",
        "    supports_dry_run: bool\n"
        "    approval_policy: AgentApprovalPolicy\n"
        "    allow_suspended_organization: bool = False\n",
    )
    insert_before(
        root,
        path,
        "class AgentActionExecutionResult(BaseModel):\n",
        clean(
            '''
            class AgentActionExecutionContext(BaseModel):
                """Backend-derived identity and time for one execution attempt."""

                model_config = ConfigDict(frozen=True)

                organization_id: str
                executed_by_user_id: str
                nucleus_actor_id: int | None = None
                execution_started_at: datetime


            '''
        ),
    )
    replace_exact(
        root,
        path,
        "    proposal_id: str\n    idempotency_key: str\n",
        "    proposal_id: str\n"
        "    idempotency_key: str\n"
        "    executed_by_user_id: str\n"
        "    nucleus_actor_id: int | None = None\n",
    )


def patch_permissions(root: Path) -> None:
    path = "app/domain/enums.py"
    replace_exact(
        root,
        path,
        "    ORGANIZATION_ACCOUNT_UPDATE = \"organization.account.update\"\n"
        "    ORGANIZATION_ENTITLEMENTS_READ = \"organization.entitlements.read\"\n",
        "    ORGANIZATION_ACCOUNT_UPDATE = \"organization.account.update\"\n"
        "    ORGANIZATION_ACCOUNT_IDENTITY_UPDATE = (\n"
        "        \"organization.account.identity.update\"\n"
        "    )\n"
        "    ORGANIZATION_LICENSE_UPDATE = \"organization.license.update\"\n"
        "    ORGANIZATION_LIFECYCLE_UPDATE = \"organization.lifecycle.update\"\n"
        "    ORGANIZATION_ENTITLEMENTS_READ = \"organization.entitlements.read\"\n",
    )
    replace_exact(
        root,
        path,
        "    ORGANIZATION_ENTITLEMENTS_UPDATE = \"organization.entitlements.update\"\n",
        "    ORGANIZATION_ENTITLEMENTS_UPDATE = \"organization.entitlements.update\"\n"
        "    ORGANIZATION_ENTITLEMENTS_DELETE = \"organization.entitlements.delete\"\n",
    )
    replace_exact(
        root,
        path,
        "    Permission.ORGANIZATION_ACCOUNT_UPDATE,\n"
        "    Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,\n",
        "    Permission.ORGANIZATION_ACCOUNT_UPDATE,\n"
        "    Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE,\n"
        "    Permission.ORGANIZATION_LICENSE_UPDATE,\n"
        "    Permission.ORGANIZATION_LIFECYCLE_UPDATE,\n"
        "    Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,\n"
        "    Permission.ORGANIZATION_ENTITLEMENTS_DELETE,\n",
    )


def _registry_definitions() -> str:
    return indent_text(clean(
        '''
                self._definition(
                    name="update_nucleus_organization_username",
                    description="Propose changing the Nucleus login username after uniqueness validation.",
                    arguments=("username",),
                    permission=Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                ),
                self._definition(
                    name="update_nucleus_organization_license",
                    description="Propose atomically changing the user limit and license dates with seat-pool and renewal synchronization.",
                    arguments=("max_user_limit", "license_start_date", "license_end_date"),
                    permission=Permission.ORGANIZATION_LICENSE_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                ),
                self._definition(
                    name="approve_nucleus_organization_account",
                    description="Propose approving the Nucleus organization account with backend-derived actor and time.",
                    arguments=(),
                    permission=Permission.ORGANIZATION_LIFECYCLE_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                    allow_suspended_organization=True,
                ),
                self._definition(
                    name="reject_nucleus_organization_account",
                    description="Propose rejecting and deactivating the Nucleus organization account with a reason.",
                    arguments=("reason",),
                    permission=Permission.ORGANIZATION_LIFECYCLE_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                    allow_suspended_organization=True,
                ),
                self._definition(
                    name="activate_nucleus_organization_account",
                    description="Propose activating an approved, unexpired Nucleus organization and its legacy projections.",
                    arguments=(),
                    permission=Permission.ORGANIZATION_LIFECYCLE_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                    allow_suspended_organization=True,
                ),
                self._definition(
                    name="deactivate_nucleus_organization_account",
                    description="Propose deactivating the Nucleus organization and suspending its legacy projections without deleting data.",
                    arguments=(),
                    permission=Permission.ORGANIZATION_LIFECYCLE_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="high",
                    allow_suspended_organization=True,
                ),
                self._definition(
                    name="grant_nucleus_company_profile_access",
                    description="Propose granting or restoring one company-profile access row.",
                    arguments=("company_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationCompanyProfileAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_company_profile_access",
                    description="Propose reversibly revoking one company-profile access row.",
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
                    resource_type="OrganizationCompanyProfileAccess",
                    risk_level="high",
                ),
                self._definition(
                    name="grant_nucleus_drug_access",
                    description="Propose granting or restoring one drug access row.",
                    arguments=("drug_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationDrugAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_drug_access",
                    description="Propose reversibly revoking one drug access row.",
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
                    resource_type="OrganizationDrugAccess",
                    risk_level="high",
                ),
                self._definition(
                    name="grant_nucleus_indication_access",
                    description="Propose granting or restoring one indication access row.",
                    arguments=("indication_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationIndicationAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_indication_access",
                    description="Propose reversibly revoking one indication access row.",
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
                    resource_type="OrganizationIndicationAccess",
                    risk_level="high",
                ),
                self._definition(
                    name="grant_nucleus_market_access",
                    description="Propose granting or restoring one market access row.",
                    arguments=("market_id", "market_sample_id"),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationMarketAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_market_access",
                    description="Propose reversibly revoking one market access row.",
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
                    resource_type="OrganizationMarketAccess",
                    risk_level="high",
                ),
        '''
    ), 16)


def patch_action_registry(root: Path) -> None:
    path = "app/agent/action_registry.py"
    insert_before(
        root,
        path,
        "                self._definition(\n                    name=\"invite_organization_user\",\n",
        _registry_definitions(),
    )
    replace_exact(
        root,
        path,
        "        risk_level: str,\n    ) -> AgentActionDefinition:\n",
        "        risk_level: str,\n"
        "        allow_suspended_organization: bool = False,\n"
        "    ) -> AgentActionDefinition:\n",
    )
    replace_exact(
        root,
        path,
        "            approval_policy=AgentApprovalPolicy(\n"
        "                self_approval_allowed=not high_risk,\n"
        "                required_approver_permission=permission_value,\n"
        "                minimum_approvals=2 if high_risk else 1,\n"
        "            ),\n"
        "        )\n",
        "            approval_policy=AgentApprovalPolicy(\n"
        "                self_approval_allowed=not high_risk,\n"
        "                required_approver_permission=permission_value,\n"
        "                minimum_approvals=2 if high_risk else 1,\n"
        "            ),\n"
        "            allow_suspended_organization=allow_suspended_organization,\n"
        "        )\n",
    )
    replace_exact(
        root,
        path,
        "            \"actor_user_id\",\n            \"permission\",\n",
        "            \"actor_user_id\",\n"
        "            \"nucleus_actor_id\",\n"
        "            \"approved_by\",\n"
        "            \"approved_date\",\n"
        "            \"rejected_by\",\n"
        "            \"rejected_date\",\n"
        "            \"updated_by\",\n"
        "            \"updated_date\",\n"
        "            \"permission\",\n",
    )


def patch_execution_persistence(root: Path) -> None:
    path = "app/db/action_models.py"
    replace_exact(
        root,
        path,
        "    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)\n"
        "    outcome: Mapped[str] = mapped_column(String, nullable=False)\n",
        "    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)\n"
        "    executed_by_user_id: Mapped[str] = mapped_column(\n"
        "        String, ForeignKey(\"users.id\"), nullable=False, index=True\n"
        "    )\n"
        "    nucleus_actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)\n"
        "    outcome: Mapped[str] = mapped_column(String, nullable=False)\n",
    )

    path = "app/repositories/agent_action_repository.py"
    replace_exact(
        root,
        path,
        "        proposal_id: str,\n"
        "        idempotency_key: str,\n"
        "    ) -> AgentActionExecutionResult:\n",
        "        proposal_id: str,\n"
        "        idempotency_key: str,\n"
        "        executed_by_user_id: str,\n"
        "        nucleus_actor_id: int | None,\n"
        "    ) -> AgentActionExecutionResult:\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "            idempotency_key=idempotency_key,\n"
        "            outcome=\"executing\",\n",
        "            idempotency_key=idempotency_key,\n"
        "            executed_by_user_id=executed_by_user_id,\n"
        "            nucleus_actor_id=nucleus_actor_id,\n"
        "            outcome=\"executing\",\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "            idempotency_key=row.idempotency_key,\n"
        "            outcome=row.outcome,\n",
        "            idempotency_key=row.idempotency_key,\n"
        "            executed_by_user_id=row.executed_by_user_id,\n"
        "            nucleus_actor_id=row.nucleus_actor_id,\n"
        "            outcome=row.outcome,\n",
    )

    path = "app/repositories/multi_approval_agent_action_repository.py"
    replace_exact(
        root,
        path,
        "        proposal_id: str,\n"
        "        idempotency_key: str,\n"
        "    ) -> AgentActionExecutionResult:\n",
        "        proposal_id: str,\n"
        "        idempotency_key: str,\n"
        "        executed_by_user_id: str,\n"
        "        nucleus_actor_id: int | None,\n"
        "    ) -> AgentActionExecutionResult:\n",
    )
    replace_exact(
        root,
        path,
        "            idempotency_key=idempotency_key,\n"
        "            outcome=\"executing\",\n",
        "            idempotency_key=idempotency_key,\n"
        "            executed_by_user_id=executed_by_user_id,\n"
        "            nucleus_actor_id=nucleus_actor_id,\n"
        "            outcome=\"executing\",\n",
    )


def patch_action_service(root: Path) -> None:
    path = "app/services/agent_action_service.py"
    replace_exact(
        root,
        path,
        "    AgentActionExecutionResult,\n",
        "    AgentActionExecutionContext,\n    AgentActionExecutionResult,\n",
    )
    replace_exact(
        root,
        path,
        "from app.repositories.audit_repository import AuditRepository\n",
        "from app.repositories.audit_repository import AuditRepository\n"
        "from app.repositories.nucleus_actor_mapping_repository import (\n"
        "    NucleusActorMappingRepository,\n"
        ")\n",
    )
    replace_exact(
        root,
        path,
        "        action_registry: AgentActionRegistry,\n"
        "        action_handlers: dict[str, AgentActionHandler],\n"
        "    ) -> None:\n",
        "        action_registry: AgentActionRegistry,\n"
        "        action_handlers: dict[str, AgentActionHandler],\n"
        "        nucleus_actor_mapping_repository: NucleusActorMappingRepository,\n"
        "    ) -> None:\n",
    )
    replace_exact(
        root,
        path,
        "        self._action_registry = action_registry\n"
        "        self._action_handlers = action_handlers\n",
        "        self._action_registry = action_registry\n"
        "        self._action_handlers = action_handlers\n"
        "        self._nucleus_actor_mapping_repository = (\n"
        "            nucleus_actor_mapping_repository\n"
        "        )\n",
    )
    replace_exact(
        root,
        path,
        "            required_permission=action_definition.required_permission,\n"
        "        )\n"
        "        handler = self._require_handler(action_definition.name)\n",
        "            required_permission=action_definition.required_permission,\n"
        "            allow_suspended_organization=(\n"
        "                action_definition.allow_suspended_organization\n"
        "            ),\n"
        "        )\n"
        "        handler = self._require_handler(action_definition.name)\n",
    )
    replace_exact(
        root,
        path,
        "            required_permission=action_definition.required_permission,\n"
        "        )\n"
        "        return await self._expire_if_needed(proposal)\n",
        "            required_permission=action_definition.required_permission,\n"
        "            allow_suspended_organization=(\n"
        "                action_definition.allow_suspended_organization\n"
        "            ),\n"
        "        )\n"
        "        return await self._expire_if_needed(proposal)\n",
    )
    replace_exact(
        root,
        path,
        "        try:\n"
        "            await self._action_repository.start_execution(\n"
        "                proposal_id=proposal.id,\n"
        "                idempotency_key=idempotency_key,\n"
        "            )\n",
        "        nucleus_actor_id = None\n"
        "        if getattr(handler, \"requires_execution_context\", False):\n"
        "            nucleus_actor_id = (\n"
        "                await self._nucleus_actor_mapping_repository.get_nucleus_actor_id(\n"
        "                    user.id\n"
        "                )\n"
        "            )\n"
        "            if nucleus_actor_id is None:\n"
        "                raise AgentActionStateConflictError(\n"
        "                    \"Executor has no Nucleus actor mapping.\"\n"
        "                )\n"
        "        try:\n"
        "            started_execution = await self._action_repository.start_execution(\n"
        "                proposal_id=proposal.id,\n"
        "                idempotency_key=idempotency_key,\n"
        "                executed_by_user_id=user.id,\n"
        "                nucleus_actor_id=nucleus_actor_id,\n"
        "            )\n",
    )
    replace_exact(
        root,
        path,
        "        try:\n"
        "            handler_result = await handler.execute(proposal=proposal)\n",
        "        context = AgentActionExecutionContext(\n"
        "            organization_id=organization_id,\n"
        "            executed_by_user_id=started_execution.executed_by_user_id,\n"
        "            nucleus_actor_id=started_execution.nucleus_actor_id,\n"
        "            execution_started_at=started_execution.started_at,\n"
        "        )\n"
        "        try:\n"
        "            if getattr(handler, \"requires_execution_context\", False):\n"
        "                handler_result = await handler.execute(\n"
        "                    proposal=proposal, context=context\n"
        "                )\n"
        "            else:\n"
        "                handler_result = await handler.execute(proposal=proposal)\n",
    )
    replace_exact(
        root,
        path,
        "        handler_result = await handler.reconcile(\n"
        "            proposal=proposal,\n"
        "            execution=execution,\n"
        "        )\n",
        "        context = AgentActionExecutionContext(\n"
        "            organization_id=organization_id,\n"
        "            executed_by_user_id=execution.executed_by_user_id,\n"
        "            nucleus_actor_id=execution.nucleus_actor_id,\n"
        "            execution_started_at=execution.started_at,\n"
        "        )\n"
        "        if getattr(handler, \"requires_execution_context\", False):\n"
        "            handler_result = await handler.reconcile(\n"
        "                proposal=proposal,\n"
        "                execution=execution,\n"
        "                context=context,\n"
        "            )\n"
        "        else:\n"
        "            handler_result = await handler.reconcile(\n"
        "                proposal=proposal,\n"
        "                execution=execution,\n"
        "            )\n",
    )
    replace_exact(
        root,
        path,
        "            required_permission=proposal.approval_policy.required_approver_permission,\n"
        "        )\n",
        "            required_permission=proposal.approval_policy.required_approver_permission,\n"
        "            allow_suspended_organization=True,\n"
        "        )\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "        required_permission: str,\n"
        "    ) -> None:\n",
        "        required_permission: str,\n"
        "        allow_suspended_organization: bool = False,\n"
        "    ) -> None:\n",
    )
    replace_exact(
        root,
        path,
        "        if organization_profile.status != OrganizationStatus.ACTIVE:\n"
        "            raise OrganizationSuspendedError()\n",
        "        if (\n"
        "            organization_profile.status != OrganizationStatus.ACTIVE\n"
        "            and not allow_suspended_organization\n"
        "        ):\n"
        "            raise OrganizationSuspendedError()\n",
    )


def patch_action_dependencies(root: Path) -> None:
    path = "app/api/action_dependencies.py"
    replace_exact(
        root,
        path,
        "from app.agent.nucleus_action_handlers import (\n",
        "from app.agent.nucleus_admin_action_handlers import (\n"
        "    COMPANY_PROFILE_ACCESS,\n"
        "    DRUG_ACCESS,\n"
        "    INDICATION_ACCESS,\n"
        "    MARKET_ACCESS,\n"
        "    NucleusOrganizationLifecycleHandler,\n"
        "    GrantNucleusManagedAccessHandler,\n"
        "    RevokeNucleusManagedAccessHandler,\n"
        "    UpdateNucleusOrganizationLicenseHandler,\n"
        "    UpdateNucleusOrganizationUsernameHandler,\n"
        ")\n"
        "from app.agent.nucleus_action_handlers import (\n",
    )
    replace_exact(
        root,
        path,
        "from app.repositories.audit_repository import AuditRepository\n",
        "from app.repositories.audit_repository import AuditRepository\n"
        "from app.repositories.nucleus_actor_mapping_repository import (\n"
        "    NucleusActorMappingRepository,\n"
        ")\n"
        "from app.repositories.nucleus_administration_projection_repository import (\n"
        "    NucleusAdministrationProjectionRepository,\n"
        ")\n"
        "from app.repositories.nucleus_administration_repository import (\n"
        "    NucleusAdministrationRepository,\n"
        ")\n",
    )
    replace_exact(
        root,
        path,
        "    resources = OperationalResourceService(session)\n"
        "    return {\n",
        "    resources = OperationalResourceService(session)\n"
        "    nucleus_admin = NucleusAdministrationRepository(session)\n"
        "    nucleus_projections = NucleusAdministrationProjectionRepository(session)\n"
        "    return {\n",
    )
    insert_before(
        root,
        path,
        '        "invite_organization_user": InviteOrganizationUserHandler(resources),\n',
        indent_text(clean(
            '''
                    "update_nucleus_organization_username": (
                        UpdateNucleusOrganizationUsernameHandler(nucleus_admin)
                    ),
                    "update_nucleus_organization_license": (
                        UpdateNucleusOrganizationLicenseHandler(
                            nucleus_admin, nucleus_projections
                        )
                    ),
                    "approve_nucleus_organization_account": (
                        NucleusOrganizationLifecycleHandler(
                            nucleus_admin, nucleus_projections, mode="approve"
                        )
                    ),
                    "reject_nucleus_organization_account": (
                        NucleusOrganizationLifecycleHandler(
                            nucleus_admin, nucleus_projections, mode="reject"
                        )
                    ),
                    "activate_nucleus_organization_account": (
                        NucleusOrganizationLifecycleHandler(
                            nucleus_admin, nucleus_projections, mode="activate"
                        )
                    ),
                    "deactivate_nucleus_organization_account": (
                        NucleusOrganizationLifecycleHandler(
                            nucleus_admin, nucleus_projections, mode="deactivate"
                        )
                    ),
                    "grant_nucleus_company_profile_access": (
                        GrantNucleusManagedAccessHandler(
                            nucleus_admin, COMPANY_PROFILE_ACCESS
                        )
                    ),
                    "revoke_nucleus_company_profile_access": (
                        RevokeNucleusManagedAccessHandler(
                            nucleus_admin, COMPANY_PROFILE_ACCESS
                        )
                    ),
                    "grant_nucleus_drug_access": GrantNucleusManagedAccessHandler(
                        nucleus_admin, DRUG_ACCESS
                    ),
                    "revoke_nucleus_drug_access": RevokeNucleusManagedAccessHandler(
                        nucleus_admin, DRUG_ACCESS
                    ),
                    "grant_nucleus_indication_access": GrantNucleusManagedAccessHandler(
                        nucleus_admin, INDICATION_ACCESS
                    ),
                    "revoke_nucleus_indication_access": RevokeNucleusManagedAccessHandler(
                        nucleus_admin, INDICATION_ACCESS
                    ),
                    "grant_nucleus_market_access": GrantNucleusManagedAccessHandler(
                        nucleus_admin, MARKET_ACCESS
                    ),
                    "revoke_nucleus_market_access": RevokeNucleusManagedAccessHandler(
                        nucleus_admin, MARKET_ACCESS
                    ),
            '''
        ), 8),
    )
    replace_exact(
        root,
        path,
        "    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],\n"
        "    action_repository: Annotated[\n",
        "    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],\n"
        "    session: SessionDep,\n"
        "    action_repository: Annotated[\n",
    )
    replace_exact(
        root,
        path,
        "        action_registry=action_registry,\n"
        "        action_handlers=action_handlers,\n"
        "    )\n",
        "        action_registry=action_registry,\n"
        "        action_handlers=action_handlers,\n"
        "        nucleus_actor_mapping_repository=NucleusActorMappingRepository(session),\n"
        "    )\n",
    )


def patch_seed(root: Path) -> None:
    path = "app/db/seed.py"
    replace_exact(
        root,
        path,
        "from app.db.nucleus_models import (\n",
        "from app.db.nucleus_admin_models import NucleusActorMappingORM\n"
        "from app.db.nucleus_models import (\n",
    )
    insert_before(
        root,
        path,
        "MEMBERSHIPS = [\n",
        clean(
            '''
            NUCLEUS_ACTOR_MAPPINGS = (
                ("usr_admin_001", 1001),
                ("usr_approval_admin_001", 1002),
                ("usr_approval_admin_002", 1003),
            )


            '''
        ),
    )
    replace_exact(
        root,
        path,
        "    await session.flush()\n\n"
        "    for user_id, role, membership_status in MEMBERSHIPS:\n",
        "    await session.flush()\n\n"
        "    for workplace_user_id, nucleus_actor_id in NUCLEUS_ACTOR_MAPPINGS:\n"
        "        if (\n"
        "            await session.get(NucleusActorMappingORM, workplace_user_id)\n"
        "            is None\n"
        "        ):\n"
        "            session.add(\n"
        "                NucleusActorMappingORM(\n"
        "                    workplace_user_id=workplace_user_id,\n"
        "                    nucleus_actor_id=nucleus_actor_id,\n"
        "                    created_at=_EPOCH,\n"
        "                    updated_at=_EPOCH,\n"
        "                )\n"
        "            )\n\n"
        "    for user_id, role, membership_status in MEMBERSHIPS:\n",
    )


def patch_entitlement_filtering(root: Path) -> None:
    path = "app/repositories/nucleus_organization_repository.py"
    replace_exact(
        root,
        path,
        "from app.db.nucleus_models import (\n",
        "from app.db.nucleus_admin_models import NucleusAccessTombstoneORM\n"
        "from app.db.nucleus_models import (\n",
    )
    replace_exact(
        root,
        path,
        "        account_id = account.organization_account_id\n\n"
        "        category_rows = (\n",
        "        account_id = account.organization_account_id\n"
        "        tombstone_rows = (\n"
        "            await self._session.execute(\n"
        "                select(NucleusAccessTombstoneORM).where(\n"
        "                    NucleusAccessTombstoneORM.organization_account_id\n"
        "                    == account_id\n"
        "                )\n"
        "            )\n"
        "        ).scalars().all()\n"
        "        tombstones = {\n"
        "            (row.resource_type, row.access_id) for row in tombstone_rows\n"
        "        }\n\n"
        "        category_rows = (\n",
    )
    replace_exact(
        root,
        path,
        "            company_profile_access=tuple(\n"
        "                [await self._company_to_domain(row) for row in company_rows]\n"
        "            ),\n",
        "            company_profile_access=tuple(\n"
        "                [\n"
        "                    await self._company_to_domain(row)\n"
        "                    for row in company_rows\n"
        "                    if (\n"
        "                        \"OrganizationCompanyProfileAccess\",\n"
        "                        row.organization_company_profile_access_id,\n"
        "                    )\n"
        "                    not in tombstones\n"
        "                ]\n"
        "            ),\n",
    )
    replace_exact(
        root,
        path,
        "            drug_access=tuple(\n"
        "                [await self._drug_to_domain(row) for row in drug_rows]\n"
        "            ),\n",
        "            drug_access=tuple(\n"
        "                [\n"
        "                    await self._drug_to_domain(row)\n"
        "                    for row in drug_rows\n"
        "                    if (\n"
        "                        \"OrganizationDrugAccess\",\n"
        "                        row.organization_drug_access_id,\n"
        "                    )\n"
        "                    not in tombstones\n"
        "                ]\n"
        "            ),\n",
    )
    replace_exact(
        root,
        path,
        "            indication_access=tuple(\n"
        "                [await self._indication_to_domain(row) for row in indication_rows]\n"
        "            ),\n",
        "            indication_access=tuple(\n"
        "                [\n"
        "                    await self._indication_to_domain(row)\n"
        "                    for row in indication_rows\n"
        "                    if (\n"
        "                        \"OrganizationIndicationAccess\",\n"
        "                        row.organization_indication_access_id,\n"
        "                    )\n"
        "                    not in tombstones\n"
        "                ]\n"
        "            ),\n",
    )
    replace_exact(
        root,
        path,
        "            market_access=tuple(\n"
        "                [await self._market_to_domain(row) for row in market_rows]\n"
        "            ),\n",
        "            market_access=tuple(\n"
        "                [\n"
        "                    await self._market_to_domain(row)\n"
        "                    for row in market_rows\n"
        "                    if (\n"
        "                        \"OrganizationMarketAccess\",\n"
        "                        row.organization_market_access_id,\n"
        "                    )\n"
        "                    not in tombstones\n"
        "                ]\n"
        "            ),\n",
    )


def patch_rollback_support(root: Path) -> None:
    path = "app/services/stale_safe_agent_action_service.py"
    insert_before(
        root,
        path,
        "        if source.action_name in {\n"
        "            \"update_nucleus_organization_account_field\",\n",
        indent_text(clean(
            '''
                    if source.action_name == "update_nucleus_organization_username":
                        previous_username = before.get("username")
                        if not isinstance(previous_username, str) or not previous_username:
                            raise AgentActionRollbackUnavailableError()
                        return AgentActionProposalInput(
                            action_name="update_nucleus_organization_username",
                            arguments={"username": previous_username},
                        )

                    if source.action_name == "update_nucleus_organization_license":
                        previous_limit = before.get("max_user_limit")
                        if not isinstance(previous_limit, int) or previous_limit <= 0:
                            raise AgentActionRollbackUnavailableError()
                        return AgentActionProposalInput(
                            action_name="update_nucleus_organization_license",
                            arguments={
                                "max_user_limit": str(previous_limit),
                                "license_start_date": _argument_value(
                                    before.get("license_start_date")
                                ),
                                "license_end_date": _argument_value(
                                    before.get("license_end_date")
                                ),
                            },
                        )

                    if source.action_name == "activate_nucleus_organization_account":
                        return AgentActionProposalInput(
                            action_name="deactivate_nucleus_organization_account",
                            arguments={},
                        )

                    if source.action_name == "deactivate_nucleus_organization_account":
                        if before.get("is_active") is not True:
                            raise AgentActionRollbackUnavailableError()
                        return AgentActionProposalInput(
                            action_name="activate_nucleus_organization_account",
                            arguments={},
                        )

                    access_pairs = {
                        "grant_nucleus_company_profile_access": (
                            "revoke_nucleus_company_profile_access",
                            "company_id",
                        ),
                        "grant_nucleus_drug_access": (
                            "revoke_nucleus_drug_access",
                            "drug_id",
                        ),
                        "grant_nucleus_indication_access": (
                            "revoke_nucleus_indication_access",
                            "indication_id",
                        ),
                        "grant_nucleus_market_access": (
                            "revoke_nucleus_market_access",
                            "market_id",
                        ),
                    }
                    if source.action_name in access_pairs:
                        access_id = after.get("access_id")
                        if not isinstance(access_id, int):
                            raise AgentActionRollbackUnavailableError()
                        return AgentActionProposalInput(
                            action_name=access_pairs[source.action_name][0],
                            arguments={"access_id": str(access_id)},
                        )

                    revoke_pairs = {
                        "revoke_nucleus_company_profile_access": (
                            "grant_nucleus_company_profile_access",
                            ("company_id",),
                        ),
                        "revoke_nucleus_drug_access": (
                            "grant_nucleus_drug_access",
                            ("drug_id",),
                        ),
                        "revoke_nucleus_indication_access": (
                            "grant_nucleus_indication_access",
                            ("indication_id",),
                        ),
                        "revoke_nucleus_market_access": (
                            "grant_nucleus_market_access",
                            ("market_id", "market_sample_id"),
                        ),
                    }
                    if source.action_name in revoke_pairs:
                        action_name, fields = revoke_pairs[source.action_name]
                        arguments = {
                            field: _argument_value(before.get(field)) for field in fields
                        }
                        if any(value == "null" for field, value in arguments.items() if field != "market_sample_id"):
                            raise AgentActionRollbackUnavailableError()
                        return AgentActionProposalInput(
                            action_name=action_name,
                            arguments=arguments,
                        )

            '''
        ), 8),
    )


def patch_health(root: Path) -> None:
    path = "app/api/health_routes.py"
    replace_exact(
        root,
        path,
        'EXPECTED_MIGRATION_HEAD = "0012_resource_preconditions"\n',
        'EXPECTED_MIGRATION_HEAD = "0013_nucleus_admin"\n',
    )
    replace_exact(
        root,
        path,
        "    registry_names = {\n",
        indent_text(clean(
            '''
                try:
                    await session.execute(
                        text(
                            "SELECT workplace_user_id, nucleus_actor_id "
                            "FROM nucleus_actor_mappings LIMIT 1"
                        )
                    )
                    await session.execute(
                        text(
                            "SELECT resource_type, access_id "
                            "FROM nucleus_access_tombstones LIMIT 1"
                        )
                    )
                    await session.execute(
                        text(
                            "SELECT executed_by_user_id, nucleus_actor_id "
                            "FROM agent_action_executions LIMIT 1"
                        )
                    )
                    nucleus_admin_sidecars_supported = True
                except SQLAlchemyError:
                    await session.rollback()
                    nucleus_admin_sidecars_supported = False

                registry_names = {
            '''
        ), 4),
    )
    replace_exact(
        root,
        path,
        "    configured_management_permissions = set(permission_rows)\n\n"
        "    audit_pending = int(\n",
        "    configured_management_permissions = set(permission_rows)\n\n"
        "    nucleus_admin_permissions = {\n"
        "        Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE.value,\n"
        "        Permission.ORGANIZATION_LICENSE_UPDATE.value,\n"
        "        Permission.ORGANIZATION_LIFECYCLE_UPDATE.value,\n"
        "        Permission.ORGANIZATION_ENTITLEMENTS_DELETE.value,\n"
        "    }\n"
        "    configured_nucleus_admin_permissions = set(\n"
        "        (\n"
        "            await session.execute(\n"
        "                select(RolePermissionORM.permission).where(\n"
        "                    RolePermissionORM.role == Role.SANDBOX_ADMIN.value,\n"
        "                    RolePermissionORM.permission.in_(\n"
        "                        nucleus_admin_permissions\n"
        "                    ),\n"
        "                )\n"
        "            )\n"
        "        ).scalars().all()\n"
        "    )\n\n"
        "    audit_pending = int(\n",
    )
    replace_exact(
        root,
        path,
        '        "proposal_resource_preconditions_supported": proposal_preconditions_supported,\n'
        '        "registry_handler_parity": registry_names == handler_names,\n',
        '        "proposal_resource_preconditions_supported": proposal_preconditions_supported,\n'
        '        "nucleus_admin_sidecars_supported": nucleus_admin_sidecars_supported,\n'
        '        "nucleus_admin_permissions_seeded": (\n'
        '            configured_nucleus_admin_permissions == nucleus_admin_permissions\n'
        '        ),\n'
        '        "registry_handler_parity": registry_names == handler_names,\n',
    )


def patch_migration_tests(root: Path) -> None:
    path = "tests/test_migrations.py"
    replace_exact(
        root,
        path,
        'EXPECTED_HEAD = "0012_resource_preconditions"\n',
        'EXPECTED_HEAD = "0013_nucleus_admin"\n',
    )
    replace_exact(
        root,
        path,
        "    proposal_indexes = read_index_names(connection, \"agent_action_proposals\")\n",
        "    actor_columns = read_column_names(connection, \"nucleus_actor_mappings\")\n"
        "    assert {\"workplace_user_id\", \"nucleus_actor_id\"}.issubset(actor_columns)\n"
        "    tombstone_columns = read_column_names(connection, \"nucleus_access_tombstones\")\n"
        "    assert {\n"
        "        \"resource_type\",\n"
        "        \"access_id\",\n"
        "        \"organization_account_id\",\n"
        "        \"version\",\n"
        "        \"snapshot_json\",\n"
        "        \"revoked_by\",\n"
        "        \"revoked_at\",\n"
        "    }.issubset(tombstone_columns)\n"
        "    execution_columns = read_column_names(connection, \"agent_action_executions\")\n"
        "    assert {\"executed_by_user_id\", \"nucleus_actor_id\"}.issubset(\n"
        "        execution_columns\n"
        "    )\n\n"
        "    proposal_indexes = read_index_names(connection, \"agent_action_proposals\")\n",
    )


def patch_action_schema(root: Path) -> None:
    path = "app/schemas/agent_actions.py"
    insert_before(
        root,
        path,
        '    "invite_organization_user",\n',
        indent_text(clean(
            '''
                "update_nucleus_organization_username",
                "update_nucleus_organization_license",
                "approve_nucleus_organization_account",
                "reject_nucleus_organization_account",
                "activate_nucleus_organization_account",
                "deactivate_nucleus_organization_account",
                "grant_nucleus_company_profile_access",
                "revoke_nucleus_company_profile_access",
                "grant_nucleus_drug_access",
                "revoke_nucleus_drug_access",
                "grant_nucleus_indication_access",
                "revoke_nucleus_indication_access",
                "grant_nucleus_market_access",
                "revoke_nucleus_market_access",
            '''
        ), 4),
    )
    replace_exact(
        root,
        path,
        "AgentActionName = Literal[\n",
        "_NO_ARGUMENT_ACTIONS = {\n"
        "    \"approve_nucleus_organization_account\",\n"
        "    \"activate_nucleus_organization_account\",\n"
        "    \"deactivate_nucleus_organization_account\",\n"
        "}\n\n\n"
        "AgentActionName = Literal[\n",
    )
    replace_exact(
        root,
        path,
        "        elif not self.arguments:\n"
        "            raise ValueError(\"Action arguments are required\")\n",
        "        elif not self.arguments and self.action_name not in _NO_ARGUMENT_ACTIONS:\n"
        "            raise ValueError(\"Action arguments are required\")\n",
    )


def patch_action_policy_tests(root: Path) -> None:
    path = "tests/test_action_policy_discovery.py"
    replace_exact(root, path, "    assert len(actions) == 16\n", "    assert len(actions) == 30\n")
    replace_exact(
        root,
        path,
        '    assert actions["remove_organization_user"]["self_approval_allowed"] is False\n',
        '    assert actions["remove_organization_user"]["self_approval_allowed"] is False\n'
        '    assert actions["update_nucleus_organization_license"]["minimum_approvals"] == 2\n'
        '    assert actions["update_nucleus_organization_license"]["self_approval_allowed"] is False\n'
        '    assert actions["revoke_nucleus_market_access"]["minimum_approvals"] == 2\n',
    )


def patch_operational_tests(root: Path) -> None:
    path = "tests/test_operational_hardening.py"
    replace_exact(
        root,
        path,
        '    assert body["checks"]["proposal_resource_preconditions_supported"] is True\n'
        '    assert body["checks"]["action_management_permissions_seeded"] is True\n'
        '    assert body["migration"]["expected"] == "0012_resource_preconditions"\n'
        '    assert body["actions"] == {"registered": 16, "handlers": 16}\n',
        '    assert body["checks"]["proposal_resource_preconditions_supported"] is True\n'
        '    assert body["checks"]["nucleus_admin_sidecars_supported"] is True\n'
        '    assert body["checks"]["nucleus_admin_permissions_seeded"] is True\n'
        '    assert body["checks"]["action_management_permissions_seeded"] is True\n'
        '    assert body["migration"]["expected"] == "0013_nucleus_admin"\n'
        '    assert body["actions"] == {"registered": 30, "handlers": 30}\n',
    )


def add_admin_tests(root: Path) -> None:
    create_exact(
        root,
        "tests/test_nucleus_admin_control.py",
        clean(
            '''
            from __future__ import annotations

            from datetime import datetime, timezone

            from httpx import AsyncClient
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.nucleus_admin_models import NucleusActorMappingORM
            from app.db.nucleus_models import NucleusOrganizationAccountORM
            from app.db.orm_models import OrganizationOverviewORM, OrganizationSeatPoolORM

            ORGANIZATION_ID = "org_sandbox_001"
            BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
            APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
            APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}


            async def _propose(
                client: AsyncClient,
                headers: dict[str, str],
                action_name: str,
                arguments: dict[str, str],
            ) -> dict:
                response = await client.post(
                    f"{BASE}/propose",
                    headers=headers,
                    json={"action_name": action_name, "arguments": arguments},
                )
                assert response.status_code == 200, response.text
                return response.json()["proposal"]


            async def _approve_high_risk(
                client: AsyncClient,
                proposal_id: str,
            ) -> None:
                first = await client.post(
                    f"{BASE}/{proposal_id}/approve",
                    headers=APPROVER_ONE,
                    json={"reason": "Independent review one"},
                )
                assert first.status_code == 200, first.text
                second = await client.post(
                    f"{BASE}/{proposal_id}/approve",
                    headers=APPROVER_TWO,
                    json={"reason": "Independent review two"},
                )
                assert second.status_code == 200, second.text


            async def _execute(
                client: AsyncClient,
                headers: dict[str, str],
                proposal_id: str,
                key: str,
            ) -> dict:
                response = await client.post(
                    f"{BASE}/{proposal_id}/execute",
                    headers=headers,
                    json={"idempotency_key": key},
                )
                assert response.status_code == 200, response.text
                return response.json()["execution"]


            async def test_username_change_requires_two_approvals_and_records_executor(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_nucleus_organization_username",
                    {"username": "internal.company.admin"},
                )
                assert proposal["approval_policy"] == {
                    "self_approval_allowed": False,
                    "required_approver_permission": (
                        "organization.account.identity.update"
                    ),
                    "minimum_approvals": 2,
                }
                await _approve_high_risk(client, proposal["id"])
                execution = await _execute(
                    client,
                    admin_headers,
                    proposal["id"],
                    "username-admin-control-001",
                )
                assert execution["executed_by_user_id"] == "usr_admin_001"
                assert execution["nucleus_actor_id"] == 1001

                account = await db_session.get(NucleusOrganizationAccountORM, 1)
                assert account is not None
                await db_session.refresh(account)
                assert account.user_name == "internal.company.admin"
                assert account.updated_by == 1001
                assert account.password == "$mock$not-a-real-password"

                assert "password" not in str(execution).lower()


            async def test_sensitive_execution_fails_closed_without_actor_mapping(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_nucleus_organization_username",
                    {"username": "mapping.required"},
                )
                await _approve_high_risk(client, proposal["id"])
                mapping = await db_session.get(
                    NucleusActorMappingORM, "usr_admin_001"
                )
                assert mapping is not None
                await db_session.delete(mapping)
                await db_session.commit()

                response = await client.post(
                    f"{BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "missing-actor-mapping-001"},
                )
                assert response.status_code == 409
                assert response.json()["error"]["code"] == (
                    "agent_action_state_conflict"
                )


            async def test_license_change_synchronizes_all_reviewed_resources(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_nucleus_organization_license",
                    {
                        "max_user_limit": "8",
                        "license_start_date": "2026-01-01T00:00:00+00:00",
                        "license_end_date": "2027-01-31T00:00:00+00:00",
                    },
                )
                assert {
                    item["resource_type"]
                    for item in proposal["resource_preconditions"]
                } == {
                    "OrganizationAccount",
                    "organization_seat_pool",
                    "organization_overview",
                }
                await _approve_high_risk(client, proposal["id"])
                await _execute(
                    client,
                    admin_headers,
                    proposal["id"],
                    "license-admin-control-001",
                )

                account = await db_session.get(NucleusOrganizationAccountORM, 1)
                pool = await db_session.get(
                    OrganizationSeatPoolORM, "seatpool_sandbox_standard"
                )
                overview = await db_session.get(OrganizationOverviewORM, ORGANIZATION_ID)
                assert account is not None and pool is not None and overview is not None
                await db_session.refresh(account)
                await db_session.refresh(pool)
                await db_session.refresh(overview)
                assert account.max_user_limit == 8
                assert account.license_end_date.replace(tzinfo=timezone.utc) == datetime(
                    2027, 1, 31, tzinfo=timezone.utc
                )
                assert pool.total_seats == 8
                assert pool.expires_at.replace(tzinfo=timezone.utc) == datetime(
                    2027, 1, 31, tzinfo=timezone.utc
                )
                assert overview.renewal_date.isoformat() == "2027-01-31"


            async def test_rejection_uses_backend_actor_and_suspends_projections(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "reject_nucleus_organization_account",
                    {"reason": "Internal compliance hold"},
                )
                fields = {change["field"] for change in proposal["changes"]}
                assert {"RejectedBy", "RejectedDate", "organization.status"}.issubset(
                    fields
                )
                await _approve_high_risk(client, proposal["id"])
                await _execute(
                    client,
                    admin_headers,
                    proposal["id"],
                    "reject-admin-control-001",
                )
                account = await db_session.get(NucleusOrganizationAccountORM, 1)
                assert account is not None
                await db_session.refresh(account)
                assert account.status == "rejected"
                assert account.is_active is False
                assert account.rejected_by == 1001
                assert account.rejection_reason == "Internal compliance hold"
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_nucleus_managed_access.py",
        clean(
            '''
            from __future__ import annotations

            import pytest
            from httpx import AsyncClient
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.nucleus_admin_models import NucleusAccessTombstoneORM
            from app.db.nucleus_models import (
                NucleusOrganizationCompanyProfileAccessORM,
                NucleusOrganizationDrugAccessORM,
                NucleusOrganizationIndicationAccessORM,
                NucleusOrganizationMarketAccessORM,
            )

            ORGANIZATION_ID = "org_sandbox_001"
            BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
            APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
            APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}

            CASES = (
                (
                    "company_profile",
                    "revoke_nucleus_company_profile_access",
                    NucleusOrganizationCompanyProfileAccessORM,
                    1,
                    "OrganizationCompanyProfileAccess",
                ),
                (
                    "drug",
                    "revoke_nucleus_drug_access",
                    NucleusOrganizationDrugAccessORM,
                    1,
                    "OrganizationDrugAccess",
                ),
                (
                    "indication",
                    "revoke_nucleus_indication_access",
                    NucleusOrganizationIndicationAccessORM,
                    1,
                    "OrganizationIndicationAccess",
                ),
                (
                    "market",
                    "revoke_nucleus_market_access",
                    NucleusOrganizationMarketAccessORM,
                    1,
                    "OrganizationMarketAccess",
                ),
            )


            @pytest.mark.parametrize(
                "kind,action_name,orm_type,access_id,resource_type", CASES
            )
            async def test_revocation_is_reversible_tombstone_not_source_delete(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
                kind: str,
                action_name: str,
                orm_type: type,
                access_id: int,
                resource_type: str,
            ) -> None:
                proposed = await client.post(
                    f"{BASE}/propose",
                    headers=admin_headers,
                    json={
                        "action_name": action_name,
                        "arguments": {"access_id": str(access_id)},
                    },
                )
                assert proposed.status_code == 200, proposed.text
                proposal_id = proposed.json()["proposal"]["id"]
                for headers in (APPROVER_ONE, APPROVER_TWO):
                    approved = await client.post(
                        f"{BASE}/{proposal_id}/approve",
                        headers=headers,
                        json={"reason": f"Reviewed {kind} revocation"},
                    )
                    assert approved.status_code == 200, approved.text
                executed = await client.post(
                    f"{BASE}/{proposal_id}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": f"revoke-{kind}-admin-001"},
                )
                assert executed.status_code == 200, executed.text

                source_row = await db_session.get(orm_type, access_id)
                tombstone = await db_session.get(
                    NucleusAccessTombstoneORM,
                    {"resource_type": resource_type, "access_id": access_id},
                )
                assert source_row is not None
                assert tombstone is not None
                assert tombstone.revoked_by == 1001

                rollback_response = await client.post(
                    f"{BASE}/{proposal_id}/rollback-proposal",
                    headers=admin_headers,
                    json={"reason": "Restore exact reviewed access"},
                )
                assert rollback_response.status_code == 200, rollback_response.text
                rollback_id = rollback_response.json()["proposal"]["id"]
                rollback_approval = await client.post(
                    f"{BASE}/{rollback_id}/approve",
                    headers=admin_headers,
                    json={"reason": "Reviewed restoration"},
                )
                assert rollback_approval.status_code == 200, rollback_approval.text
                rollback_execution = await client.post(
                    f"{BASE}/{rollback_id}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": f"restore-{kind}-admin-001"},
                )
                assert rollback_execution.status_code == 200, rollback_execution.text
                db_session.expire_all()
                restored_tombstone = await db_session.get(
                    NucleusAccessTombstoneORM,
                    {"resource_type": resource_type, "access_id": access_id},
                )
                assert restored_tombstone is None
                assert await db_session.get(orm_type, access_id) is not None


            async def test_grant_and_duplicate_protection(
                client: AsyncClient,
                admin_headers: dict[str, str],
            ) -> None:
                payload = {
                    "action_name": "grant_nucleus_company_profile_access",
                    "arguments": {"company_id": "999"},
                }
                proposal = await client.post(
                    f"{BASE}/propose", headers=admin_headers, json=payload
                )
                assert proposal.status_code == 200, proposal.text
                proposal_id = proposal.json()["proposal"]["id"]
                approved = await client.post(
                    f"{BASE}/{proposal_id}/approve",
                    headers=admin_headers,
                    json={"reason": "Reviewed grant"},
                )
                assert approved.status_code == 200, approved.text
                executed = await client.post(
                    f"{BASE}/{proposal_id}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "grant-company-admin-001"},
                )
                assert executed.status_code == 200, executed.text

                duplicate = await client.post(
                    f"{BASE}/propose", headers=admin_headers, json=payload
                )
                assert duplicate.status_code == 422
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_nucleus_admin_registry.py",
        clean(
            '''
            from __future__ import annotations

            from app.agent.action_registry import AgentActionRegistry
            from app.domain.enums import Permission, ROLE_PERMISSIONS, Role


            def test_full_admin_surface_is_registered_with_scoped_policies() -> None:
                definitions = AgentActionRegistry().list_definitions()
                assert len(definitions) == 30
                by_name = {definition.name: definition for definition in definitions}
                assert by_name["update_nucleus_organization_license"].risk_level == "high"
                assert (
                    by_name["update_nucleus_organization_license"]
                    .approval_policy.minimum_approvals
                    == 2
                )
                assert not (
                    by_name["update_nucleus_organization_license"]
                    .approval_policy.self_approval_allowed
                )
                assert (
                    by_name["revoke_nucleus_market_access"].required_permission
                    == Permission.ORGANIZATION_ENTITLEMENTS_DELETE.value
                )
                assert (
                    by_name["activate_nucleus_organization_account"]
                    .allow_suspended_organization
                    is True
                )
                assert all("password" not in name for name in by_name)


            def test_sensitive_admin_permissions_are_admin_only() -> None:
                admin_permissions = set(ROLE_PERMISSIONS[Role.SANDBOX_ADMIN])
                reader_permissions = set(ROLE_PERMISSIONS[Role.SANDBOX_READER])
                expected = {
                    Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE,
                    Permission.ORGANIZATION_LICENSE_UPDATE,
                    Permission.ORGANIZATION_LIFECYCLE_UPDATE,
                    Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
                }
                assert expected.issubset(admin_permissions)
                assert expected.isdisjoint(reader_permissions)
            '''
        ),
    )


def patch_documentation(root: Path) -> None:
    path = "README.md"
    replace_exact(
        root,
        path,
        "Protected fields are not chat-editable in this slice:\n\n"
        "```text\n"
        "OrganizationAccountId\n"
        "OrganizationCode\n"
        "UserName\n"
        "Password\n"
        "MaxUserLimit\n"
        "LicenseStartDate\n"
        "LicenseEndDate\n"
        "Status\n"
        "ApprovedBy\n"
        "ApprovedDate\n"
        "RejectedBy\n"
        "RejectedDate\n"
        "RejectionReason\n"
        "IsActive\n"
        "CreatedBy\n"
        "CreatedDate\n"
        "UpdatedBy\n"
        "UpdatedDate\n"
        "```\n",
        "Administrative fields are controlled through dedicated actions rather than the generic profile-field action:\n\n"
        "```text\n"
        "UserName                  dedicated identity action, two approvals\n"
        "MaxUserLimit             dedicated license action, two approvals\n"
        "LicenseStartDate         dedicated license action, two approvals\n"
        "LicenseEndDate           dedicated license action, two approvals\n"
        "Status/IsActive          dedicated lifecycle actions, two approvals\n"
        "Approval/rejection data  backend-generated actor and UTC time\n"
        "```\n\n"
        "The following remain non-editable identifiers, credentials, and audit-owned fields:\n\n"
        "```text\n"
        "OrganizationAccountId\n"
        "OrganizationCode\n"
        "Password\n"
        "CreatedBy\n"
        "CreatedDate\n"
        "UpdatedBy\n"
        "UpdatedDate\n"
        "```\n",
    )
    replace_exact(
        root,
        path,
        "The supplied Company Profile, Drug, Indication and Market tables do not contain\n"
        "`IsActive`, timestamps, or a stated delete contract. They are intentionally\n"
        "read-only in this package rather than inventing destructive behavior.\n",
        "The supplied Company Profile, Drug, Indication and Market tables do not contain\n"
        "`IsActive`. The workplace layer therefore uses reversible internal tombstones:\n"
        "the exact source rows remain unchanged, entitlement reads exclude revoked rows,\n"
        "and approved grant actions can restore them without destructive deletion.\n",
    )
    replace_exact(
        root,
        path,
        "0012_resource_preconditions\n",
        "0013_nucleus_admin\n",
    )
    insert_before(
        root,
        path,
        "## Database and seed\n",
        clean(
            '''
            ## Administrative-control surface

            The sandbox now exposes 30 named write actions. Sensitive username,
            licensing, lifecycle and entitlement-revocation operations require two
            independent approvals and prohibit requester self-approval. Execution
            actor IDs are derived from authenticated backend mappings; the model cannot
            provide actor IDs, timestamps, organization scope, permissions, approvals or
            idempotency state. This is the same constrained-control pattern used by
            mature workplace administration agents; it is not arbitrary SQL access and
            it does not advertise production connectivity.

            '''
        ),
    )

    path = "APPLY_AND_VALIDATE.md"
    replace_exact(
        root,
        path,
        "0012_resource_preconditions (head)",
        "0013_nucleus_admin (head)",
    )
    replace_exact(root, path, "16 write actions", "30 write actions")
    replace_exact(
        root,
        path,
        "Readiness must report migration `0012_resource_preconditions` and registry/\n"
        "handler parity of 16/16.\n",
        "Readiness must report migration `0013_nucleus_admin`, Nucleus administrative\n"
        "sidecar support, and registry/handler parity of 30/30.\n",
    )
    replace_exact(
        root,
        path,
        'git commit -m "add multi-resource preconditions and projection synchronization"',
        'git commit -m "add Nucleus full administrative control"',
    )

    for path in ("docs/ARCHITECTURE.md", "docs/SECURITY_MODEL.md"):
        content = read_text(root, path)
        content += clean(
            '''

            ## Nucleus full administrative control

            Nucleus administrative writes are exposed only as named backend-owned
            actions. Profile fields remain low risk; username, license and lifecycle
            transitions require two independent approvals. Authenticated Workplace user
            IDs resolve to integer Nucleus actors through an internal mapping and the
            execution record preserves the original executor for deterministic
            reconciliation. Company-profile, drug, indication and market revocations use
            reversible tombstones because those supplied tables do not contain
            `IsActive`; exact source rows are never physically deleted by this package.
            Password is outside every action, model, response and audit contract.
            '''
        )
        write_text(root, path, content)


MODIFIED_PATHS = (
    "APPLY_AND_VALIDATE.md",
    "README.md",
    "alembic/env.py",
    "app/agent/action_contracts.py",
    "app/agent/action_registry.py",
    "app/api/action_dependencies.py",
    "app/api/health_routes.py",
    "app/db/action_models.py",
    "app/db/seed.py",
    "app/domain/enums.py",
    "app/repositories/agent_action_repository.py",
    "app/repositories/multi_approval_agent_action_repository.py",
    "app/repositories/nucleus_organization_repository.py",
    "app/schemas/agent_actions.py",
    "app/services/agent_action_service.py",
    "app/services/hardened_agent_action_service.py",
    "app/services/release_ready_agent_action_service.py",
    "app/services/stale_safe_agent_action_service.py",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY_MODEL.md",
    "tests/conftest.py",
    "tests/test_action_policy_discovery.py",
    "tests/test_migrations.py",
    "tests/test_operational_hardening.py",
)

NEW_PATHS = (
    "alembic/versions/0013_nucleus_admin.py",
    "app/adapters/nucleus/admin_contract.py",
    "app/agent/nucleus_admin_action_handlers.py",
    "app/db/nucleus_admin_models.py",
    "app/domain/nucleus_admin_models.py",
    "app/repositories/nucleus_actor_mapping_repository.py",
    "app/repositories/nucleus_administration_projection_repository.py",
    "app/repositories/nucleus_administration_repository.py",
    "tests/test_nucleus_admin_control.py",
    "tests/test_nucleus_admin_registry.py",
    "tests/test_nucleus_managed_access.py",
)


def restore_after_failure(
    root: Path,
    backups: dict[str, str],
    new_path_existed: dict[str, bool],
) -> None:
    for relative_path, content in backups.items():
        write_text(root, relative_path, content)
    for relative_path, existed_before in new_path_existed.items():
        path = root / relative_path
        if not existed_before and path.exists():
            path.unlink()


def apply_patch(root: Path) -> None:
    validate_repository(root)
    backups = {path: read_text(root, path) for path in MODIFIED_PATHS}
    new_path_existed = {path: (root / path).exists() for path in NEW_PATHS}
    try:
        add_database_models(root)
        add_domain_models(root)
        add_contracts(root)
        add_actor_mapping_repository(root)
        add_admin_repository(root)
        add_projection_repository(root)
        add_admin_handlers(root)
        add_migration(root)
        patch_model_imports(root)
        patch_action_contracts(root)
        patch_permissions(root)
        patch_action_registry(root)
        patch_execution_persistence(root)
        patch_action_service(root)
        patch_suspended_action_management(root)
        patch_action_dependencies(root)
        patch_seed(root)
        patch_entitlement_filtering(root)
        patch_rollback_support(root)
        patch_health(root)
        patch_migration_tests(root)
        patch_action_schema(root)
        patch_action_policy_tests(root)
        patch_operational_tests(root)
        add_admin_tests(root)
        patch_documentation(root)
    except Exception:
        restore_after_failure(root, backups, new_path_existed)
        raise

    print("Applied Nucleus full administrative-control vertical slice.")
    print("No files were staged, committed, pushed, or deleted.")
    print("The eight supplied Nucleus table definitions were not changed.")
    print("Untracked ZIP/download files were not touched.")
    print()
    print("Run exactly:")
    print("  python -m compileall -q app tests alembic")
    print("  git diff --check")
    print("  alembic upgrade head")
    print("  alembic current")
    print("  python -m app.db.seed")
    print("  python -m app.db.seed")
    print("  pytest -q")
    print("  git status --short")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args()
    try:
        apply_patch(args.repo.resolve())
    except PatchError as exception:
        print(f"PATCH FAILED: {exception}", file=sys.stderr)
        return 1
    except Exception as exception:
        print(
            f"PATCH FAILED: {type(exception).__name__}: {exception}",
            file=sys.stderr,
        )
        return 1
    return 0


def patch_suspended_action_management(root: Path) -> None:
    path = "app/services/release_ready_agent_action_service.py"
    replace_exact(
        root,
        path,
        "            required_permission=definition.required_permission,\n"
        "        )\n",
        "            required_permission=definition.required_permission,\n"
        "            allow_suspended_organization=(\n"
        "                definition.allow_suspended_organization\n"
        "            ),\n"
        "        )\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "            required_permission=Permission.AGENT_ACTIONS_READ.value,\n"
        "        )\n",
        "            required_permission=Permission.AGENT_ACTIONS_READ.value,\n"
        "            allow_suspended_organization=True,\n"
        "        )\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "            required_permission=action_definition.required_permission,\n"
        "        )\n",
        "            required_permission=action_definition.required_permission,\n"
        "            allow_suspended_organization=(\n"
        "                action_definition.allow_suspended_organization\n"
        "            ),\n"
        "        )\n",
        expected_count=1,
    )

    path = "app/services/hardened_agent_action_service.py"
    for permission, count in (
        ("AGENT_ACTIONS_READ", 2),
        ("AGENT_ACTIONS_APPROVE", 1),
        ("AGENT_ACTIONS_EXECUTE", 3),
        ("AGENT_ACTIONS_RECONCILE", 2),
    ):
        replace_exact(
            root,
            path,
            f"            required_permission=Permission.{permission}.value,\n"
            "        )\n",
            f"            required_permission=Permission.{permission}.value,\n"
            "            allow_suspended_organization=True,\n"
            "        )\n",
            expected_count=count,
        )

if __name__ == "__main__":
    raise SystemExit(main())

