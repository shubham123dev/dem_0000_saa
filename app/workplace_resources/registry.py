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
    ReportORM,
    RolePermissionORM,
    SeatAssignmentORM,
    UserORM,
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
                    _field(
                        "display_name",
                        "display_name",
                        "string",
                        searchable=True,
                        sortable=True,
                        maximum_length=250,
                    ),
                    _field(
                        "legal_name",
                        "legal_name",
                        "string",
                        nullable=True,
                        editable=True,
                        clearable=True,
                        searchable=True,
                        maximum_length=250,
                    ),
                    _field(
                        "contact_email",
                        "contact_email",
                        "string",
                        nullable=True,
                        searchable=True,
                        maximum_length=320,
                    ),
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
                operations=frozenset(
                    {
                        "read",
                        "search",
                        "create",
                        "update",
                        "clear",
                        "activate",
                        "deactivate",
                        "delete",
                        "restore",
                        "bulk_update",
                    }
                ),
                fields=(
                    _field("id", "id", "string", searchable=True, sortable=True),
                    _field(
                        "namespace",
                        "namespace",
                        "string",
                        searchable=True,
                        sortable=True,
                        maximum_length=80,
                    ),
                    _field(
                        "key",
                        "setting_key",
                        "string",
                        searchable=True,
                        sortable=True,
                        maximum_length=120,
                    ),
                    _field(
                        "value",
                        "value_json",
                        "json",
                        nullable=True,
                        editable=True,
                        clearable=True,
                    ),
                    _field(
                        "description",
                        "description",
                        "string",
                        nullable=True,
                        editable=True,
                        clearable=True,
                        searchable=True,
                        maximum_length=500,
                    ),
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
                    _field(
                        "organization_id",
                        "organization_id",
                        "string",
                        searchable=True,
                    ),
                    _field(
                        "organization_type",
                        "organization_type",
                        "string",
                        searchable=True,
                    ),
                    _field(
                        "renewal_date",
                        "renewal_date",
                        "date",
                        nullable=True,
                        sortable=True,
                    ),
                    _field(
                        "workspace_status",
                        "workspace_status",
                        "string",
                        searchable=True,
                    ),
                    _field(
                        "workspace_health_percent",
                        "workspace_health_percent",
                        "integer",
                        sortable=True,
                    ),
                    _field("licensed_modules", "licensed_modules", "integer"),
                    _field("available_areas", "available_areas", "integer"),
                    _field(
                        "organization_logins",
                        "organization_logins",
                        "integer",
                    ),
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
                    _field(
                        "status",
                        "membership_status",
                        "string",
                        searchable=True,
                    ),
                    _field("joined_at", "joined_at", "datetime", nullable=True),
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
                    _field("starts_at", "starts_at", "datetime", nullable=True),
                    _field("expires_at", "expires_at", "datetime", nullable=True),
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
                    _field(
                        "seat_pool_id",
                        "seat_pool_id",
                        "string",
                        searchable=True,
                    ),
                    _field("user_id", "user_id", "string", searchable=True),
                    _field("status", "status", "string", searchable=True),
                    _field(
                        "assigned_at",
                        "assigned_at",
                        "datetime",
                        nullable=True,
                    ),
                    _field(
                        "revoked_at",
                        "revoked_at",
                        "datetime",
                        nullable=True,
                    ),
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
                    _field(
                        "access_level",
                        "access_level",
                        "string",
                        searchable=True,
                    ),
                    _field("status", "status", "string", searchable=True),
                    _field("granted_at", "granted_at", "datetime", nullable=True),
                    _field("expires_at", "expires_at", "datetime", nullable=True),
                    _field("version", "version", "integer"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="user",
                display_name="User",
                orm_type=UserORM,
                id_attribute="id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "id", "string"),
                    _field("display_name", "display_name", "string"),
                    _field("email", "email", "string"),
                    _field("status", "status", "string"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="report",
                display_name="Report",
                orm_type=ReportORM,
                id_attribute="id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "id", "string"),
                    _field(
                        "external_report_id",
                        "external_report_id",
                        "string",
                    ),
                    _field("title", "title", "string"),
                    _field(
                        "market_name",
                        "market_name",
                        "string",
                        nullable=True,
                    ),
                    _field("status", "status", "string"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="role_permission",
                display_name="Role permission",
                orm_type=RolePermissionORM,
                id_attribute="id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset(),
                fields=(
                    _field("id", "id", "integer"),
                    _field("role", "role", "string"),
                    _field("permission", "permission", "string"),
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
        return (
            WorkplaceResourceDefinition(
                resource_type="nucleus_organization_account",
                display_name="Nucleus organization account",
                orm_type=NucleusOrganizationAccountORM,
                id_attribute="organization_account_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_account_id", "integer"),
                    _field("organization_name", "organization_name", "string"),
                    _field(
                        "organization_code",
                        "organization_code",
                        "string",
                        nullable=True,
                    ),
                    _field(
                        "organization_type",
                        "organization_type",
                        "string",
                        nullable=True,
                    ),
                    _field("industry", "industry", "string", nullable=True),
                    _field("website", "website", "string", nullable=True),
                    _field("user_name", "user_name", "string"),
                    _field("email", "email", "string", nullable=True),
                    _field(
                        "contact_person_name",
                        "contact_person_name",
                        "string",
                        nullable=True,
                    ),
                    _field(
                        "contact_person_designation",
                        "contact_person_designation",
                        "string",
                        nullable=True,
                    ),
                    _field(
                        "contact_phone",
                        "contact_phone",
                        "string",
                        nullable=True,
                    ),
                    _field("city", "city", "string", nullable=True),
                    _field("state", "state", "string", nullable=True),
                    _field("country", "country", "string", nullable=True),
                    _field("postal_code", "postal_code", "string", nullable=True),
                    _field("max_user_limit", "max_user_limit", "integer"),
                    _field(
                        "license_start_date",
                        "license_start_date",
                        "datetime",
                        nullable=True,
                    ),
                    _field(
                        "license_end_date",
                        "license_end_date",
                        "datetime",
                        nullable=True,
                    ),
                    _field("status", "status", "string"),
                    _field("is_active", "is_active", "boolean"),
                    _field(
                        "rejection_reason",
                        "rejection_reason",
                        "string",
                        nullable=True,
                    ),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_category_access",
                display_name="Nucleus category access",
                orm_type=NucleusOrganizationCategoryAccessORM,
                id_attribute="organization_category_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_category_access_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field("category_id", "category_id", "integer", nullable=True),
                    _field(
                        "category_sample_id",
                        "category_sample_id",
                        "integer",
                        nullable=True,
                    ),
                    _field("is_active", "is_active", "boolean"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_company_profile_access",
                display_name="Nucleus company profile access",
                orm_type=NucleusOrganizationCompanyProfileAccessORM,
                id_attribute="organization_company_profile_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field(
                        "id",
                        "organization_company_profile_access_id",
                        "integer",
                    ),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field("company_id", "company_id", "integer", nullable=True),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_drug_access",
                display_name="Nucleus drug access",
                orm_type=NucleusOrganizationDrugAccessORM,
                id_attribute="organization_drug_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_drug_access_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field("drug_id", "drug_id", "integer", nullable=True),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_indication_access",
                display_name="Nucleus indication access",
                orm_type=NucleusOrganizationIndicationAccessORM,
                id_attribute="organization_indication_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_indication_access_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field(
                        "indication_id",
                        "indication_id",
                        "integer",
                        nullable=True,
                    ),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_market_access",
                display_name="Nucleus market access",
                orm_type=NucleusOrganizationMarketAccessORM,
                id_attribute="organization_market_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_market_access_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field("market_id", "market_id", "integer", nullable=True),
                    _field(
                        "market_sample_id",
                        "market_sample_id",
                        "integer",
                        nullable=True,
                    ),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_permission",
                display_name="Nucleus permission",
                orm_type=NucleusOrganizationPermissionORM,
                id_attribute="organization_permission_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_permission_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field(
                        "company_profile_id",
                        "cp_company_master_pharma_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "therapeutic_category_pharma_id",
                        "hc_theropetic_category_pharma_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "therapeutic_category_epidem_id",
                        "hc_theropetic_category_epidem_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "disease_code_epidem_id",
                        "hc_disease_code_epidem_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "reports_custom_id",
                        "reports_custom_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "import_export_report_id",
                        "importexport_report_id",
                        "integer",
                        nullable=True,
                    ),
                    _field("is_active", "is_active", "boolean"),
                ),
                dedicated_management=True,
            ),
            WorkplaceResourceDefinition(
                resource_type="nucleus_report_access",
                display_name="Nucleus report access",
                orm_type=NucleusOrganizationReportAccessORM,
                id_attribute="organization_report_access_id",
                organization_attribute=None,
                version_attribute=None,
                operations=frozenset({"read"}),
                fields=(
                    _field("id", "organization_report_access_id", "integer"),
                    _field(
                        "organization_account_id",
                        "organization_account_id",
                        "integer",
                    ),
                    _field("reports_id", "reports_id", "integer", nullable=True),
                    _field("sample_id", "sample_id", "integer", nullable=True),
                    _field(
                        "sample_toc_id",
                        "sample_toc_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "speciality_id",
                        "speciality_id",
                        "integer",
                        nullable=True,
                    ),
                    _field(
                        "is_executive_access",
                        "is_executive_access",
                        "boolean",
                        nullable=True,
                    ),
                    _field("is_active", "is_active", "boolean"),
                ),
                dedicated_management=True,
            ),
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
                            f"Unknown ORM attribute "
                            f"{definition.resource_type}.{field.attribute}"
                        )
            for field in definition.fields:
                if field.sensitive and field.readable:
                    raise RuntimeError("Sensitive fields cannot be readable")
                if field.clearable and not field.nullable:
                    raise RuntimeError("Only nullable fields can be clearable")
                if "password" in field.name.lower():
                    raise RuntimeError("Credential fields cannot enter the registry")

    def list_definitions(self) -> tuple[WorkplaceResourceDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, resource_type: str) -> WorkplaceResourceDefinition:
        try:
            return self._definitions[resource_type]
        except KeyError as exception:
            raise ValueError("Unknown workplace resource type") from exception
