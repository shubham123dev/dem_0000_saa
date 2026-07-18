from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
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
)
from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    SeatAssignmentORM,
    UserORM,
)
from app.db.workplace_resource_models import WorkplaceSettingORM
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.registry import WorkplaceResourceRegistry


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class WorkplaceRelationDefinition:
    name: str
    source_resource_type: str
    target_resource_type: str
    cardinality: str
    description: str

    def public_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source_resource_type": self.source_resource_type,
            "target_resource_type": self.target_resource_type,
            "cardinality": self.cardinality,
            "description": self.description,
        }


class WorkplaceRelationRegistry:
    def __init__(self) -> None:
        self._definitions = (
            WorkplaceRelationDefinition(
                "memberships",
                "organization",
                "organization_membership",
                "one_to_many",
                "Organization memberships in the current workplace.",
            ),
            WorkplaceRelationDefinition(
                "seat_pools",
                "organization",
                "organization_seat_pool",
                "one_to_many",
                "Seat pools owned by the organization.",
            ),
            WorkplaceRelationDefinition(
                "seat_assignments",
                "organization",
                "seat_assignment",
                "one_to_many",
                "Seat assignments in the organization.",
            ),
            WorkplaceRelationDefinition(
                "report_access",
                "organization",
                "organization_report_access",
                "one_to_many",
                "Legacy report-access grants owned by the organization.",
            ),
            WorkplaceRelationDefinition(
                "settings",
                "organization",
                "workplace_setting",
                "one_to_many",
                "Governed workplace settings owned by the organization.",
            ),
            WorkplaceRelationDefinition(
                "nucleus_account",
                "organization",
                "nucleus_organization_account",
                "one_to_one",
                "Exact-schema Nucleus account mapped by organization code.",
            ),
            WorkplaceRelationDefinition(
                "user",
                "organization_membership",
                "user",
                "many_to_one",
                "User represented by the membership.",
            ),
            WorkplaceRelationDefinition(
                "seat_assignments",
                "organization_membership",
                "seat_assignment",
                "one_to_many",
                "Seat assignments held by the member.",
            ),
            WorkplaceRelationDefinition(
                "assignments",
                "organization_seat_pool",
                "seat_assignment",
                "one_to_many",
                "Assignments drawn from the seat pool.",
            ),
            WorkplaceRelationDefinition(
                "report",
                "organization_report_access",
                "report",
                "many_to_one",
                "Report referenced by the access grant.",
            ),
            WorkplaceRelationDefinition(
                "categories",
                "nucleus_organization_account",
                "nucleus_category_access",
                "one_to_many",
                "Nucleus category-access rows.",
            ),
            WorkplaceRelationDefinition(
                "company_profiles",
                "nucleus_organization_account",
                "nucleus_company_profile_access",
                "one_to_many",
                "Nucleus company-profile access rows.",
            ),
            WorkplaceRelationDefinition(
                "drugs",
                "nucleus_organization_account",
                "nucleus_drug_access",
                "one_to_many",
                "Nucleus drug-access rows.",
            ),
            WorkplaceRelationDefinition(
                "indications",
                "nucleus_organization_account",
                "nucleus_indication_access",
                "one_to_many",
                "Nucleus indication-access rows.",
            ),
            WorkplaceRelationDefinition(
                "markets",
                "nucleus_organization_account",
                "nucleus_market_access",
                "one_to_many",
                "Nucleus market-access rows.",
            ),
            WorkplaceRelationDefinition(
                "permissions",
                "nucleus_organization_account",
                "nucleus_permission",
                "one_to_many",
                "Nucleus special-permission rows.",
            ),
            WorkplaceRelationDefinition(
                "reports",
                "nucleus_organization_account",
                "nucleus_report_access",
                "one_to_many",
                "Nucleus report-access rows.",
            ),
        )
        keys = {(item.source_resource_type, item.name) for item in self._definitions}
        if len(keys) != len(self._definitions):
            raise RuntimeError("Duplicate workplace relationship")

    def list_definitions(self) -> tuple[WorkplaceRelationDefinition, ...]:
        return self._definitions

    def for_source(
        self,
        source_resource_type: str,
    ) -> tuple[WorkplaceRelationDefinition, ...]:
        return tuple(
            item
            for item in self._definitions
            if item.source_resource_type == source_resource_type
        )

    def get(
        self,
        source_resource_type: str,
        relationship: str,
    ) -> WorkplaceRelationDefinition:
        matches = [
            item
            for item in self._definitions
            if item.source_resource_type == source_resource_type
            and item.name == relationship
        ]
        if len(matches) != 1:
            raise ValueError("Unknown workplace relationship")
        return matches[0]


class WorkplaceRelationshipService:
    def __init__(
        self,
        session: AsyncSession,
        resource_registry: WorkplaceResourceRegistry | None = None,
        operation_router: WorkplaceOperationRouter | None = None,
        relation_registry: WorkplaceRelationRegistry | None = None,
    ) -> None:
        self._session = session
        self._resource_registry = resource_registry or WorkplaceResourceRegistry()
        self._operation_router = operation_router or WorkplaceOperationRouter(
            self._resource_registry
        )
        self._relation_registry = relation_registry or WorkplaceRelationRegistry()

    def explain_capabilities(self, resource_type: str) -> dict[str, Any]:
        resource = self._operation_router.describe(resource_type)
        return {
            "resource": resource,
            "relationships": tuple(
                item.public_dict()
                for item in self._relation_registry.for_source(resource_type)
            ),
            "query_operators": (
                "equals",
                "not_equals",
                "contains",
                "starts_with",
                "in",
                "greater_than",
                "less_than",
                "between",
                "is_null",
                "is_not_null",
            ),
        }

    async def list_related(
        self,
        *,
        organization_id: str,
        source_resource_type: str,
        source_resource_id: str,
        relationship: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 100:
            raise ValueError("Relationship limit must be between one and one hundred")
        definition = self._relation_registry.get(
            source_resource_type,
            relationship,
        )
        rows = await self._load_rows(
            organization_id=organization_id,
            source_resource_type=source_resource_type,
            source_resource_id=source_resource_id,
            relationship=relationship,
            limit=limit,
        )
        target_definition = self._resource_registry.get(
            definition.target_resource_type
        )
        items = tuple(
            self._serialize(target_definition, row)
            for row in rows
        )
        return {
            "relationship": definition.public_dict(),
            "source_resource_id": source_resource_id,
            "items": items,
            "count": len(items),
            "limit": limit,
        }

    async def _load_rows(
        self,
        *,
        organization_id: str,
        source_resource_type: str,
        source_resource_id: str,
        relationship: str,
        limit: int,
    ) -> tuple[Any, ...]:
        if source_resource_type == "organization":
            if source_resource_id != organization_id:
                raise ValueError("Organization relationship scope is invalid")
            mapping = {
                "memberships": (
                    OrganizationMembershipORM,
                    OrganizationMembershipORM.organization_id == organization_id,
                ),
                "seat_pools": (
                    OrganizationSeatPoolORM,
                    OrganizationSeatPoolORM.organization_id == organization_id,
                ),
                "seat_assignments": (
                    SeatAssignmentORM,
                    SeatAssignmentORM.organization_id == organization_id,
                ),
                "report_access": (
                    OrganizationReportAccessORM,
                    OrganizationReportAccessORM.organization_id == organization_id,
                ),
                "settings": (
                    WorkplaceSettingORM,
                    WorkplaceSettingORM.organization_id == organization_id,
                ),
            }
            if relationship == "nucleus_account":
                row = await self._session.scalar(
                    select(NucleusOrganizationAccountORM).where(
                        NucleusOrganizationAccountORM.organization_code
                        == organization_id
                    )
                )
                return (row,) if row is not None else ()
            orm_type, condition = mapping[relationship]
            id_attribute = self._resource_registry.get(
                self._relation_registry.get(
                    source_resource_type,
                    relationship,
                ).target_resource_type
            ).id_attribute
            statement = (
                select(orm_type)
                .where(condition)
                .order_by(getattr(orm_type, id_attribute).asc())
                .limit(limit)
            )
            return tuple((await self._session.execute(statement)).scalars().all())

        if source_resource_type == "organization_membership":
            try:
                membership_id = int(source_resource_id)
            except ValueError as exception:
                raise ValueError("Membership ID must be an integer") from exception
            membership = await self._session.scalar(
                select(OrganizationMembershipORM).where(
                    OrganizationMembershipORM.id == membership_id,
                    OrganizationMembershipORM.organization_id == organization_id,
                )
            )
            if membership is None:
                raise ValueError("Organization membership was not found")
            if relationship == "user":
                user = await self._session.get(UserORM, membership.user_id)
                return (user,) if user is not None else ()
            statement = (
                select(SeatAssignmentORM)
                .where(
                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.user_id == membership.user_id,
                )
                .order_by(SeatAssignmentORM.id.asc())
                .limit(limit)
            )
            return tuple((await self._session.execute(statement)).scalars().all())

        if source_resource_type == "organization_seat_pool":
            pool = await self._session.scalar(
                select(OrganizationSeatPoolORM).where(
                    OrganizationSeatPoolORM.id == source_resource_id,
                    OrganizationSeatPoolORM.organization_id == organization_id,
                )
            )
            if pool is None:
                raise ValueError("Organization seat pool was not found")
            statement = (
                select(SeatAssignmentORM)
                .where(
                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                )
                .order_by(SeatAssignmentORM.id.asc())
                .limit(limit)
            )
            return tuple((await self._session.execute(statement)).scalars().all())

        if source_resource_type == "organization_report_access":
            access = await self._session.scalar(
                select(OrganizationReportAccessORM).where(
                    OrganizationReportAccessORM.id == source_resource_id,
                    OrganizationReportAccessORM.organization_id == organization_id,
                )
            )
            if access is None:
                raise ValueError("Organization report access was not found")
            report = await self._session.get(ReportORM, access.report_id)
            return (report,) if report is not None else ()

        if source_resource_type == "nucleus_organization_account":
            try:
                account_id = int(source_resource_id)
            except ValueError as exception:
                raise ValueError("Nucleus account ID must be an integer") from exception
            account = await self._session.scalar(
                select(NucleusOrganizationAccountORM).where(
                    NucleusOrganizationAccountORM.organization_account_id == account_id,
                    NucleusOrganizationAccountORM.organization_code == organization_id,
                )
            )
            if account is None:
                raise ValueError("Nucleus organization account was not found")
            mapping = {
                "categories": NucleusOrganizationCategoryAccessORM,
                "company_profiles": NucleusOrganizationCompanyProfileAccessORM,
                "drugs": NucleusOrganizationDrugAccessORM,
                "indications": NucleusOrganizationIndicationAccessORM,
                "markets": NucleusOrganizationMarketAccessORM,
                "permissions": NucleusOrganizationPermissionORM,
                "reports": NucleusOrganizationReportAccessORM,
            }
            orm_type = mapping[relationship]
            target_type = self._relation_registry.get(
                source_resource_type,
                relationship,
            ).target_resource_type
            id_attribute = self._resource_registry.get(target_type).id_attribute
            statement = (
                select(orm_type)
                .where(orm_type.organization_account_id == account_id)
                .order_by(getattr(orm_type, id_attribute).asc())
                .limit(limit)
            )
            return tuple((await self._session.execute(statement)).scalars().all())

        raise ValueError("Relationship source is not supported")

    @staticmethod
    def _serialize(definition, row: Any) -> dict[str, Any]:
        return {
            field.name: _canonical(getattr(row, field.attribute))
            for field in definition.fields
            if field.readable and not field.sensitive
        }
