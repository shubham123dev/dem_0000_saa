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
