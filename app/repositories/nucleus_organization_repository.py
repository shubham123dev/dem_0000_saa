"""Persistence adapter for the exact-schema Nucleus SQLite mock."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_models import (
    NucleusOrganizationAccountORM,
    NucleusOrganizationCategoryAccessORM,
    NucleusOrganizationCompanyProfileAccessORM,
    NucleusOrganizationDrugAccessORM,
    NucleusOrganizationIndicationAccessORM,
    NucleusOrganizationMarketAccessORM,
    NucleusOrganizationPermissionORM,
    NucleusOrganizationReportAccessORM,
    NucleusResourceVersionORM,
)
from app.db.orm_models import OrganizationORM, OrganizationOverviewORM
from app.domain.nucleus_models import (
    NucleusCategoryAccess,
    NucleusCompanyProfileAccess,
    NucleusDrugAccess,
    NucleusIndicationAccess,
    NucleusMarketAccess,
    NucleusOrganizationAccount,
    NucleusOrganizationApprovalStatus,
    NucleusOrganizationEntitlements,
    NucleusOrganizationLicense,
    NucleusReportAccess,
    NucleusSpecialPermissions,
)


ACCOUNT_FIELD_ATTRIBUTES: dict[str, str] = {
    "OrganizationName": "organization_name",
    "OrganizationType": "organization_type",
    "Industry": "industry",
    "Website": "website",
    "Email": "email",
    "ContactPersonName": "contact_person_name",
    "ContactPersonDesignation": "contact_person_designation",
    "ContactPhone": "contact_phone",
    "AddressLine1": "address_line1",
    "AddressLine2": "address_line2",
    "City": "city",
    "State": "state",
    "Country": "country",
    "PostalCode": "postal_code",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NucleusOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _account_row_by_code(
        self,
        organization_code: str,
    ) -> NucleusOrganizationAccountORM | None:
        statement = select(NucleusOrganizationAccountORM).where(
            NucleusOrganizationAccountORM.organization_code == organization_code
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def _version_row(
        self,
        resource_type: str,
        resource_key: str,
    ) -> NucleusResourceVersionORM | None:
        return await self._session.get(
            NucleusResourceVersionORM,
            {"resource_type": resource_type, "resource_key": resource_key},
        )

    async def _version(
        self,
        resource_type: str,
        resource_key: str,
        *,
        default: int = 1,
    ) -> int:
        row = await self._version_row(resource_type, resource_key)
        return row.version if row is not None else default

    async def _advance_existing_version(
        self,
        resource_type: str,
        resource_key: str,
        expected_version: int,
    ) -> int | None:
        """Atomically claim the next sidecar version for an existing resource."""

        statement = (
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
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        return expected_version + 1

    async def get_account(
        self,
        organization_code: str,
    ) -> NucleusOrganizationAccount | None:
        row = await self._account_row_by_code(organization_code)
        if row is None:
            return None
        version = await self._version(
            "nucleus_account",
            str(row.organization_account_id),
        )
        return self._account_to_domain(row, version)

    async def get_license(
        self,
        organization_code: str,
    ) -> NucleusOrganizationLicense | None:
        row = await self._account_row_by_code(organization_code)
        if row is None:
            return None
        version = await self._version(
            "nucleus_account",
            str(row.organization_account_id),
        )
        return NucleusOrganizationLicense(
            organization_account_id=row.organization_account_id,
            max_user_limit=row.max_user_limit,
            license_start_date=row.license_start_date,
            license_end_date=row.license_end_date,
            is_active=row.is_active,
            status=row.status,
            version=version,
        )

    async def get_approval_status(
        self,
        organization_code: str,
    ) -> NucleusOrganizationApprovalStatus | None:
        row = await self._account_row_by_code(organization_code)
        if row is None:
            return None
        version = await self._version(
            "nucleus_account",
            str(row.organization_account_id),
        )
        return NucleusOrganizationApprovalStatus(
            organization_account_id=row.organization_account_id,
            status=row.status,
            approved_by=row.approved_by,
            approved_date=row.approved_date,
            rejected_by=row.rejected_by,
            rejected_date=row.rejected_date,
            rejection_reason=row.rejection_reason,
            is_active=row.is_active,
            version=version,
        )

    async def get_account_field_state(
        self,
        organization_code: str,
        field_name: str,
    ) -> tuple[NucleusOrganizationAccount, Any] | None:
        attribute_name = ACCOUNT_FIELD_ATTRIBUTES.get(field_name)
        if attribute_name is None:
            raise ValueError("Organization account field is not editable")
        row = await self._account_row_by_code(organization_code)
        if row is None:
            return None
        version = await self._version(
            "nucleus_account",
            str(row.organization_account_id),
        )
        return self._account_to_domain(row, version), getattr(row, attribute_name)

    async def get_contact_email_bridge_state(
        self,
        organization_code: str,
    ) -> tuple[NucleusOrganizationAccount, int] | None:
        """Return the Nucleus account with the legacy profile version.

        The legacy contact-email action keeps its established organization-version
        concurrency contract while synchronizing the Nucleus account.
        """

        row = await self._account_row_by_code(organization_code)
        organization = await self._session.get(OrganizationORM, organization_code)
        if row is None or organization is None:
            return None
        version = await self._version(
            "nucleus_account",
            str(row.organization_account_id),
        )
        return self._account_to_domain(row, version), organization.version

    async def update_contact_email_bridge_if_version(
        self,
        *,
        organization_code: str,
        value: str,
        expected_legacy_version: int,
        expected_nucleus_email: str | None,
    ) -> NucleusOrganizationAccount | None:
        """Atomically update both contact-email representations."""

        row = await self._account_row_by_code(organization_code)
        if row is None or row.email != expected_nucleus_email:
            await self._session.rollback()
            return None

        legacy_update = (
            update(OrganizationORM)
            .where(
                OrganizationORM.id == organization_code,
                OrganizationORM.version == expected_legacy_version,
            )
            .values(
                contact_email=value,
                version=expected_legacy_version + 1,
                updated_at=_utcnow(),
            )
        )
        legacy_result = await self._session.execute(legacy_update)
        if legacy_result.rowcount != 1:
            await self._session.rollback()
            return None

        resource_key = str(row.organization_account_id)
        current_nucleus_version = await self._version(
            "nucleus_account",
            resource_key,
        )
        next_nucleus_version = await self._advance_existing_version(
            "nucleus_account",
            resource_key,
            current_nucleus_version,
        )
        if next_nucleus_version is None:
            return None

        row.email = value
        row.updated_date = _utcnow()
        await self._session.commit()
        await self._session.refresh(row)
        return self._account_to_domain(row, next_nucleus_version)

    async def update_account_field_if_version(
        self,
        *,
        organization_code: str,
        field_name: str,
        value: str | None,
        expected_version: int,
    ) -> NucleusOrganizationAccount | None:
        attribute_name = ACCOUNT_FIELD_ATTRIBUTES.get(field_name)
        if attribute_name is None:
            raise ValueError("Organization account field is not editable")
        row = await self._account_row_by_code(organization_code)
        if row is None:
            return None
        resource_key = str(row.organization_account_id)
        next_version = await self._advance_existing_version(
            "nucleus_account",
            resource_key,
            expected_version,
        )
        if next_version is None:
            return None

        setattr(row, attribute_name, value)
        row.updated_date = _utcnow()
        await self._synchronize_legacy_overview(
            organization_code=organization_code,
            field_name=field_name,
            value=value,
        )
        await self._session.commit()
        await self._session.refresh(row)
        return self._account_to_domain(row, next_version)

    async def _synchronize_legacy_overview(
        self,
        *,
        organization_code: str,
        field_name: str,
        value: str | None,
    ) -> None:
        organization = await self._session.get(OrganizationORM, organization_code)
        if organization is None:
            return
        if field_name == "OrganizationName" and value is not None:
            organization.display_name = value
            organization.version += 1
        elif field_name == "Email":
            organization.contact_email = value
            organization.version += 1
        elif field_name == "OrganizationType":
            overview = await self._session.get(
                OrganizationOverviewORM,
                organization_code,
            )
            if overview is not None:
                overview.organization_type = value or "organization"
                overview.version += 1

    async def get_entitlements(
        self,
        organization_code: str,
    ) -> NucleusOrganizationEntitlements | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        account_id = account.organization_account_id

        category_rows = (
            await self._session.execute(
                select(NucleusOrganizationCategoryAccessORM)
                .where(
                    NucleusOrganizationCategoryAccessORM.organization_account_id
                    == account_id
                )
                .order_by(
                    NucleusOrganizationCategoryAccessORM.organization_category_access_id
                )
            )
        ).scalars().all()
        company_rows = (
            await self._session.execute(
                select(NucleusOrganizationCompanyProfileAccessORM)
                .where(
                    NucleusOrganizationCompanyProfileAccessORM.organization_account_id
                    == account_id
                )
                .order_by(
                    NucleusOrganizationCompanyProfileAccessORM.organization_company_profile_access_id
                )
            )
        ).scalars().all()
        drug_rows = (
            await self._session.execute(
                select(NucleusOrganizationDrugAccessORM)
                .where(
                    NucleusOrganizationDrugAccessORM.organization_account_id
                    == account_id
                )
                .order_by(NucleusOrganizationDrugAccessORM.organization_drug_access_id)
            )
        ).scalars().all()
        indication_rows = (
            await self._session.execute(
                select(NucleusOrganizationIndicationAccessORM)
                .where(
                    NucleusOrganizationIndicationAccessORM.organization_account_id
                    == account_id
                )
                .order_by(
                    NucleusOrganizationIndicationAccessORM.organization_indication_access_id
                )
            )
        ).scalars().all()
        market_rows = (
            await self._session.execute(
                select(NucleusOrganizationMarketAccessORM)
                .where(
                    NucleusOrganizationMarketAccessORM.organization_account_id
                    == account_id
                )
                .order_by(NucleusOrganizationMarketAccessORM.organization_market_access_id)
            )
        ).scalars().all()
        report_rows = (
            await self._session.execute(
                select(NucleusOrganizationReportAccessORM)
                .where(
                    NucleusOrganizationReportAccessORM.organization_account_id
                    == account_id
                )
                .order_by(NucleusOrganizationReportAccessORM.organization_report_access_id)
            )
        ).scalars().all()
        permission_rows = (
            await self._session.execute(
                select(NucleusOrganizationPermissionORM)
                .where(
                    NucleusOrganizationPermissionORM.organization_account_id
                    == account_id
                )
                .order_by(NucleusOrganizationPermissionORM.organization_permission_id)
            )
        ).scalars().all()

        return NucleusOrganizationEntitlements(
            organization_account_id=account_id,
            category_access=tuple(
                [await self._category_to_domain(row) for row in category_rows]
            ),
            company_profile_access=tuple(
                [await self._company_to_domain(row) for row in company_rows]
            ),
            drug_access=tuple(
                [await self._drug_to_domain(row) for row in drug_rows]
            ),
            indication_access=tuple(
                [await self._indication_to_domain(row) for row in indication_rows]
            ),
            market_access=tuple(
                [await self._market_to_domain(row) for row in market_rows]
            ),
            report_access=tuple(
                [await self._report_to_domain(row) for row in report_rows]
            ),
            special_permissions=tuple(
                [await self._permission_to_domain(row) for row in permission_rows]
            ),
        )

    async def inspect_category_grant(
        self,
        *,
        organization_code: str,
        category_id: int,
        category_sample_id: int | None,
    ) -> tuple[NucleusCategoryAccess | None, int] | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        statement = (
            select(NucleusOrganizationCategoryAccessORM)
            .where(
                NucleusOrganizationCategoryAccessORM.organization_account_id
                == account.organization_account_id,
                NucleusOrganizationCategoryAccessORM.category_id == category_id,
                NucleusOrganizationCategoryAccessORM.category_sample_id
                == category_sample_id,
            )
            .order_by(
                NucleusOrganizationCategoryAccessORM.organization_category_access_id.desc()
            )
        )
        row = (await self._session.execute(statement)).scalars().first()
        if row is None:
            return None, 0
        domain = await self._category_to_domain(row)
        return domain, domain.version

    async def get_category_access(
        self,
        *,
        organization_code: str,
        access_id: int,
    ) -> NucleusCategoryAccess | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        row = await self._session.get(NucleusOrganizationCategoryAccessORM, access_id)
        if row is None or row.organization_account_id != account.organization_account_id:
            return None
        return await self._category_to_domain(row)

    async def grant_category_access_if_version(
        self,
        *,
        organization_code: str,
        category_id: int,
        category_sample_id: int | None,
        expected_version: int,
    ) -> NucleusCategoryAccess | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        inspected = await self.inspect_category_grant(
            organization_code=organization_code,
            category_id=category_id,
            category_sample_id=category_sample_id,
        )
        if inspected is None:
            return None
        existing, current_version = inspected
        if current_version != expected_version:
            await self._session.rollback()
            return None
        if existing is not None and existing.is_active:
            await self._session.rollback()
            return None

        if existing is None:
            row = NucleusOrganizationCategoryAccessORM(
                organization_account_id=account.organization_account_id,
                category_id=category_id,
                category_sample_id=category_sample_id,
                created_date=_utcnow(),
                is_active=True,
            )
            self._session.add(row)
            await self._session.flush()
            next_version = 1
            self._session.add(
                NucleusResourceVersionORM(
                    resource_type="nucleus_category_access",
                    resource_key=str(row.organization_category_access_id),
                    version=next_version,
                    updated_at=_utcnow(),
                )
            )
        else:
            row = await self._session.get(
                NucleusOrganizationCategoryAccessORM,
                existing.access_id,
            )
            if row is None:
                await self._session.rollback()
                return None
            row.is_active = True
            next_version = await self._advance_existing_version(
                "nucleus_category_access",
                str(row.organization_category_access_id),
                current_version,
            )
            if next_version is None:
                return None
        await self._session.commit()
        await self._session.refresh(row)
        return await self._category_to_domain(row, version_override=next_version)

    async def revoke_category_access_if_version(
        self,
        *,
        organization_code: str,
        access_id: int,
        expected_version: int,
    ) -> NucleusCategoryAccess | None:
        current = await self.get_category_access(
            organization_code=organization_code,
            access_id=access_id,
        )
        if current is None or not current.is_active or current.version != expected_version:
            await self._session.rollback()
            return None
        row = await self._session.get(NucleusOrganizationCategoryAccessORM, access_id)
        if row is None:
            return None
        row.is_active = False
        next_version = await self._advance_existing_version(
            "nucleus_category_access",
            str(access_id),
            current.version,
        )
        if next_version is None:
            return None
        await self._session.commit()
        await self._session.refresh(row)
        return await self._category_to_domain(row, version_override=next_version)

    async def inspect_report_grant(
        self,
        *,
        organization_code: str,
        reports_id: int | None,
        sample_id: int | None,
        sample_toc_id: int | None,
        speciality_id: int | None,
        is_executive_access: bool | None,
    ) -> tuple[NucleusReportAccess | None, int] | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        statement = (
            select(NucleusOrganizationReportAccessORM)
            .where(
                NucleusOrganizationReportAccessORM.organization_account_id
                == account.organization_account_id,
                NucleusOrganizationReportAccessORM.reports_id == reports_id,
                NucleusOrganizationReportAccessORM.sample_id == sample_id,
                NucleusOrganizationReportAccessORM.sample_toc_id == sample_toc_id,
                NucleusOrganizationReportAccessORM.speciality_id == speciality_id,
                NucleusOrganizationReportAccessORM.is_executive_access
                == is_executive_access,
            )
            .order_by(
                NucleusOrganizationReportAccessORM.organization_report_access_id.desc()
            )
        )
        row = (await self._session.execute(statement)).scalars().first()
        if row is None:
            return None, 0
        domain = await self._report_to_domain(row)
        return domain, domain.version

    async def get_report_access(
        self,
        *,
        organization_code: str,
        access_id: int,
    ) -> NucleusReportAccess | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        row = await self._session.get(NucleusOrganizationReportAccessORM, access_id)
        if row is None or row.organization_account_id != account.organization_account_id:
            return None
        return await self._report_to_domain(row)

    async def grant_report_access_if_version(
        self,
        *,
        organization_code: str,
        reports_id: int | None,
        sample_id: int | None,
        sample_toc_id: int | None,
        speciality_id: int | None,
        is_executive_access: bool | None,
        expected_version: int,
    ) -> NucleusReportAccess | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        inspected = await self.inspect_report_grant(
            organization_code=organization_code,
            reports_id=reports_id,
            sample_id=sample_id,
            sample_toc_id=sample_toc_id,
            speciality_id=speciality_id,
            is_executive_access=is_executive_access,
        )
        if inspected is None:
            return None
        existing, current_version = inspected
        if current_version != expected_version:
            await self._session.rollback()
            return None
        if existing is not None and existing.is_active:
            await self._session.rollback()
            return None

        if existing is None:
            row = NucleusOrganizationReportAccessORM(
                organization_account_id=account.organization_account_id,
                reports_id=reports_id,
                sample_id=sample_id,
                sample_toc_id=sample_toc_id,
                speciality_id=speciality_id,
                is_executive_access=is_executive_access,
                created_date=_utcnow(),
                is_active=True,
            )
            self._session.add(row)
            await self._session.flush()
            next_version = 1
            self._session.add(
                NucleusResourceVersionORM(
                    resource_type="nucleus_report_access",
                    resource_key=str(row.organization_report_access_id),
                    version=next_version,
                    updated_at=_utcnow(),
                )
            )
        else:
            row = await self._session.get(
                NucleusOrganizationReportAccessORM,
                existing.access_id,
            )
            if row is None:
                await self._session.rollback()
                return None
            row.is_active = True
            next_version = await self._advance_existing_version(
                "nucleus_report_access",
                str(row.organization_report_access_id),
                current_version,
            )
            if next_version is None:
                return None
        await self._session.commit()
        await self._session.refresh(row)
        return await self._report_to_domain(row, version_override=next_version)

    async def revoke_report_access_if_version(
        self,
        *,
        organization_code: str,
        access_id: int,
        expected_version: int,
    ) -> NucleusReportAccess | None:
        current = await self.get_report_access(
            organization_code=organization_code,
            access_id=access_id,
        )
        if current is None or not current.is_active or current.version != expected_version:
            await self._session.rollback()
            return None
        row = await self._session.get(NucleusOrganizationReportAccessORM, access_id)
        if row is None:
            return None
        row.is_active = False
        next_version = await self._advance_existing_version(
            "nucleus_report_access",
            str(access_id),
            current.version,
        )
        if next_version is None:
            return None
        await self._session.commit()
        await self._session.refresh(row)
        return await self._report_to_domain(row, version_override=next_version)

    async def get_permission(
        self,
        *,
        organization_code: str,
        permission_id: int,
    ) -> NucleusSpecialPermissions | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None
        row = await self._session.get(NucleusOrganizationPermissionORM, permission_id)
        if row is None or row.organization_account_id != account.organization_account_id:
            return None
        return await self._permission_to_domain(row)

    async def set_permission_if_version(
        self,
        *,
        organization_code: str,
        permission_id: int | None,
        values: dict[str, int | bool | None],
        expected_version: int,
    ) -> NucleusSpecialPermissions | None:
        account = await self._account_row_by_code(organization_code)
        if account is None:
            return None

        if permission_id is None:
            if expected_version != 0:
                await self._session.rollback()
                return None
            row = NucleusOrganizationPermissionORM(
                organization_account_id=account.organization_account_id,
                created_date=_utcnow(),
                **values,
            )
            self._session.add(row)
            await self._session.flush()
            next_version = 1
            self._session.add(
                NucleusResourceVersionORM(
                    resource_type="nucleus_special_permissions",
                    resource_key=str(row.organization_permission_id),
                    version=next_version,
                    updated_at=_utcnow(),
                )
            )
        else:
            current = await self.get_permission(
                organization_code=organization_code,
                permission_id=permission_id,
            )
            if current is None or current.version != expected_version:
                await self._session.rollback()
                return None
            row = await self._session.get(
                NucleusOrganizationPermissionORM,
                permission_id,
            )
            if row is None:
                await self._session.rollback()
                return None
            next_version = await self._advance_existing_version(
                "nucleus_special_permissions",
                str(permission_id),
                expected_version,
            )
            if next_version is None:
                return None
            for name, value in values.items():
                setattr(row, name, value)

        await self._session.commit()
        await self._session.refresh(row)
        return await self._permission_to_domain(row, version_override=next_version)

    @staticmethod
    def _account_to_domain(
        row: NucleusOrganizationAccountORM,
        version: int,
    ) -> NucleusOrganizationAccount:
        return NucleusOrganizationAccount(
            organization_account_id=row.organization_account_id,
            organization_name=row.organization_name,
            organization_code=row.organization_code,
            organization_type=row.organization_type,
            industry=row.industry,
            website=row.website,
            login_username=row.user_name,
            email=row.email,
            contact_person_name=row.contact_person_name,
            contact_person_designation=row.contact_person_designation,
            contact_phone=row.contact_phone,
            address_line1=row.address_line1,
            address_line2=row.address_line2,
            city=row.city,
            state=row.state,
            country=row.country,
            postal_code=row.postal_code,
            status=row.status,
            is_active=row.is_active,
            created_by=row.created_by,
            created_date=row.created_date,
            updated_by=row.updated_by,
            updated_date=row.updated_date,
            version=version,
        )

    async def _category_to_domain(
        self,
        row: NucleusOrganizationCategoryAccessORM,
        *,
        version_override: int | None = None,
    ) -> NucleusCategoryAccess:
        version = version_override or await self._version(
            "nucleus_category_access",
            str(row.organization_category_access_id),
        )
        return NucleusCategoryAccess(
            access_id=row.organization_category_access_id,
            organization_account_id=row.organization_account_id,
            category_id=row.category_id,
            category_sample_id=row.category_sample_id,
            created_date=row.created_date,
            is_active=row.is_active,
            version=version,
        )

    async def _company_to_domain(
        self,
        row: NucleusOrganizationCompanyProfileAccessORM,
    ) -> NucleusCompanyProfileAccess:
        version = await self._version(
            "nucleus_company_profile_access",
            str(row.organization_company_profile_access_id),
        )
        return NucleusCompanyProfileAccess(
            access_id=row.organization_company_profile_access_id,
            organization_account_id=row.organization_account_id,
            company_id=row.company_id,
            version=version,
        )

    async def _drug_to_domain(
        self,
        row: NucleusOrganizationDrugAccessORM,
    ) -> NucleusDrugAccess:
        version = await self._version(
            "nucleus_drug_access",
            str(row.organization_drug_access_id),
        )
        return NucleusDrugAccess(
            access_id=row.organization_drug_access_id,
            organization_account_id=row.organization_account_id,
            drug_id=row.drug_id,
            version=version,
        )

    async def _indication_to_domain(
        self,
        row: NucleusOrganizationIndicationAccessORM,
    ) -> NucleusIndicationAccess:
        version = await self._version(
            "nucleus_indication_access",
            str(row.organization_indication_access_id),
        )
        return NucleusIndicationAccess(
            access_id=row.organization_indication_access_id,
            organization_account_id=row.organization_account_id,
            indication_id=row.indication_id,
            version=version,
        )

    async def _market_to_domain(
        self,
        row: NucleusOrganizationMarketAccessORM,
    ) -> NucleusMarketAccess:
        version = await self._version(
            "nucleus_market_access",
            str(row.organization_market_access_id),
        )
        return NucleusMarketAccess(
            access_id=row.organization_market_access_id,
            organization_account_id=row.organization_account_id,
            market_id=row.market_id,
            market_sample_id=row.market_sample_id,
            version=version,
        )

    async def _report_to_domain(
        self,
        row: NucleusOrganizationReportAccessORM,
        *,
        version_override: int | None = None,
    ) -> NucleusReportAccess:
        version = version_override or await self._version(
            "nucleus_report_access",
            str(row.organization_report_access_id),
        )
        return NucleusReportAccess(
            access_id=row.organization_report_access_id,
            organization_account_id=row.organization_account_id,
            reports_id=row.reports_id,
            sample_id=row.sample_id,
            sample_toc_id=row.sample_toc_id,
            speciality_id=row.speciality_id,
            is_executive_access=row.is_executive_access,
            created_date=row.created_date,
            is_active=row.is_active,
            version=version,
        )

    async def _permission_to_domain(
        self,
        row: NucleusOrganizationPermissionORM,
        *,
        version_override: int | None = None,
    ) -> NucleusSpecialPermissions:
        version = version_override or await self._version(
            "nucleus_special_permissions",
            str(row.organization_permission_id),
        )
        return NucleusSpecialPermissions(
            permission_id=row.organization_permission_id,
            organization_account_id=row.organization_account_id,
            cp_company_master_pharma_id=row.cp_company_master_pharma_id,
            hc_theropetic_category_pharma_id=(
                row.hc_theropetic_category_pharma_id
            ),
            hc_theropetic_category_epidem_id=(
                row.hc_theropetic_category_epidem_id
            ),
            hc_disease_code_epidem_id=row.hc_disease_code_epidem_id,
            reports_custom_id=row.reports_custom_id,
            importexport_report_id=row.importexport_report_id,
            created_date=row.created_date,
            is_active=row.is_active,
            version=version,
        )
