from __future__ import annotations

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
    OrganizationORM,
    OrganizationOverviewORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    SeatAssignmentORM,
)
from app.db.workplace_resource_models import WorkplaceSettingORM
from app.workplace_resources.definitions import (
    WorkplaceFieldPolicy,
    WorkplaceResourceDefinition,
)


def _field(
    name: str,
    attribute: str,
    kind: str,
    **kwargs,
) -> WorkplaceFieldPolicy:
    return WorkplaceFieldPolicy(
        name=name,
        attribute=attribute,
        kind=kind,
        **kwargs,
    )


class WorkplaceResourceRegistry:
    def __init__(self) -> None:
        definitions = (
            WorkplaceResourceDefinition(
                resource_type="organization",
                display_name="Organization",
                orm_type=OrganizationORM,
                id_attribute="id",
                organization_attribute="id",
                version_attribute="version",
                operations=frozenset({"read", "search", "update", "clear"}),
                fields=(
                    _field("id", "id", "string", searchable=True, sortable=True),
                    _field("display_name", "display_name", "string", editable=True, searchable=True, sortable=True, maximum_length=250),
                    _field("legal_name", "legal_name", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=250),
                    _field("contact_email", "contact_email", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=320),
                    _field("environment", "environment", "string", sortable=True),
                    _field("status", "status", "string", sortable=True),
                    _field("version", "version", "integer", sortable=True),
                    _field("created_at", "created_at", "datetime", sortable=True),
                    _field("updated_at", "updated_at", "datetime", sortable=True),
                ),
            ),
            WorkplaceResourceDefinition(
                resource_type="workplace_setting",
                display_name="Workplace setting",
                orm_type=WorkplaceSettingORM,
                id_attribute="id",
                organization_attribute="organization_id",
                version_attribute="version",
                soft_delete_attribute="is_active",
                operations=frozenset({"read", "search", "create", "update", "clear", "activate", "deactivate", "delete", "restore", "bulk_update"}),
                fields=(
                    _field("id", "id", "string", searchable=True, sortable=True),
                    _field("namespace", "namespace", "string", editable=False, searchable=True, sortable=True, maximum_length=80),
                    _field("key", "setting_key", "string", editable=False, searchable=True, sortable=True, maximum_length=120),
                    _field("value", "value_json", "json", nullable=True, editable=True, clearable=True),
                    _field("description", "description", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=500),
                    _field("is_active", "is_active", "boolean", sortable=True),
                    _field("version", "version", "integer", sortable=True),
                    _field("created_at", "created_at", "datetime", sortable=True),
                    _field("updated_at", "updated_at", "datetime", sortable=True),
                ),
            ),
            WorkplaceResourceDefinition(
                resource_type="organization_overview",
                display_name="Organization overview",
                orm_type=OrganizationOverviewORM,
                id_attribute="organization_id",
                organization_attribute="organization_id",
                version_attribute="version",
                operations=frozenset({"read", "search"}),
                fields=(
                    _field("organization_id", "organization_id", "string", searchable=True),
                    _field("organization_type", "organization_type", "string", searchable=True),
                    _field("renewal_date", "renewal_date", "date", nullable=True, sortable=True),
                    _field("workspace_status", "workspace_status", "string", searchable=True),
                    _field("workspace_health_percent", "workspace_health_percent", "integer", sortable=True),
                    _field("version", "version", "integer"),
                ),
            ),
            WorkplaceResourceDefinition(
                resource_type="organization_membership",
                display_name="Organization membership",
                orm_type=OrganizationMembershipORM,
                id_attribute="id",
                organization_attribute="organization_id",
                version_attribute="version",
                operations=frozenset({"read", "search"}),
                fields=(
                    _field("id", "id", "integer", searchable=True),
                    _field("user_id", "user_id", "string", searchable=True),
                    _field("role", "role", "string", searchable=True),
                    _field("status", "membership_status", "string", searchable=True),
                    _field("version", "version", "integer"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="organization_seat_pool",
                display_name="Organization seat pool",
                orm_type=OrganizationSeatPoolORM,
                id_attribute="id",
                organization_attribute="organization_id",
                version_attribute="version",
                operations=frozenset({"read", "search"}),
                fields=(
                    _field("id", "id", "string", searchable=True),
                    _field("seat_type", "seat_type", "string", searchable=True),
                    _field("total_seats", "total_seats", "integer", sortable=True),
                    _field("status", "status", "string", searchable=True),
                    _field("version", "version", "integer"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="seat_assignment",
                display_name="Seat assignment",
                orm_type=SeatAssignmentORM,
                id_attribute="id",
                organization_attribute="organization_id",
                version_attribute="version",
                operations=frozenset({"read", "search"}),
                fields=(
                    _field("id", "id", "string", searchable=True),
                    _field("seat_pool_id", "seat_pool_id", "string", searchable=True),
                    _field("user_id", "user_id", "string", searchable=True),
                    _field("status", "status", "string", searchable=True),
                    _field("version", "version", "integer"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="organization_report_access",
                display_name="Organization report access",
                orm_type=OrganizationReportAccessORM,
                id_attribute="id",
                organization_attribute="organization_id",
                version_attribute="version",
                operations=frozenset({"read", "search"}),
                fields=(
                    _field("id", "id", "string", searchable=True),
                    _field("report_id", "report_id", "string", searchable=True),
                    _field("access_level", "access_level", "string", searchable=True),
                    _field("status", "status", "string", searchable=True),
                    _field("version", "version", "integer"),
                ),
                dedicated_management=True,
            ),
        ) + self._nucleus_definitions()
        self._definitions = {item.resource_type: item for item in definitions}
        if len(self._definitions) != len(definitions):
            raise RuntimeError("Duplicate workplace resource type")
        self._validate()

    @staticmethod
    def _nucleus_definitions() -> tuple[WorkplaceResourceDefinition, ...]:
        specs = (
            ("nucleus_organization_account", "Nucleus organization account", NucleusOrganizationAccountORM, "organization_account_id"),
            ("nucleus_category_access", "Nucleus category access", NucleusOrganizationCategoryAccessORM, "organization_category_access_id"),
            ("nucleus_company_profile_access", "Nucleus company profile access", NucleusOrganizationCompanyProfileAccessORM, "organization_company_profile_access_id"),
            ("nucleus_drug_access", "Nucleus drug access", NucleusOrganizationDrugAccessORM, "organization_drug_access_id"),
            ("nucleus_indication_access", "Nucleus indication access", NucleusOrganizationIndicationAccessORM, "organization_indication_access_id"),
            ("nucleus_market_access", "Nucleus market access", NucleusOrganizationMarketAccessORM, "organization_market_access_id"),
            ("nucleus_permission", "Nucleus permission", NucleusOrganizationPermissionORM, "organization_permission_id"),
            ("nucleus_report_access", "Nucleus report access", NucleusOrganizationReportAccessORM, "organization_report_access_id"),
        )
        return tuple(
            WorkplaceResourceDefinition(
                resource_type=resource_type,
                display_name=display_name,
                orm_type=orm_type,
                id_attribute=id_attribute,
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", id_attribute, "integer"),
                ),
                dedicated_management=True,
            )
            for resource_type, display_name, orm_type, id_attribute in specs
        )

    def _validate(self) -> None:
        for definition in self._definitions.values():
            names = [field.name for field in definition.fields]
            if len(names) != len(set(names)):
                raise RuntimeError(f"Duplicate field in {definition.resource_type}")
            if definition.orm_type is not None:
                for field in definition.fields:
                    if not hasattr(definition.orm_type, field.attribute):
                        raise RuntimeError(
                            f"Unknown ORM attribute {definition.resource_type}.{field.attribute}"
                        )
            for field in definition.fields:
                if field.sensitive and field.readable:
                    raise RuntimeError("Sensitive fields cannot be readable")
                if field.clearable and not field.nullable:
                    raise RuntimeError("Only nullable fields can be clearable")

    def list_definitions(self) -> tuple[WorkplaceResourceDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, resource_type: str) -> WorkplaceResourceDefinition:
        try:
            return self._definitions[resource_type]
        except KeyError as exception:
            raise ValueError("Unknown workplace resource type") from exception
