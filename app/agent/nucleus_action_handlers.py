"""Approval-gated handlers for safe Nucleus account and access mutations."""

from __future__ import annotations

from typing import Any

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
)
from app.agent.action_handlers import StaleActionResourceError, normalize_email
from app.adapters.nucleus.contract import NucleusOrganizationGateway
from app.domain.nucleus_policy import (
    CLEARABLE_NUCLEUS_ACCOUNT_FIELDS,
    EDITABLE_NUCLEUS_ACCOUNT_FIELDS,
    NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS,
)

_NULL_SENTINELS = {"null", "none", "-"}
_FIELD_MAX_LENGTHS = NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS
_CLEARABLE_FIELDS = CLEARABLE_NUCLEUS_ACCOUNT_FIELDS


def _normalize_field_name(value: str) -> str:
    normalized = value.strip()
    for allowed in EDITABLE_NUCLEUS_ACCOUNT_FIELDS:
        if allowed.lower() == normalized.lower():
            return allowed
    raise ValueError("Organization account field is not editable")


def _normalize_account_value(field_name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Organization account value is required")
    if len(normalized) > _FIELD_MAX_LENGTHS[field_name]:
        raise ValueError("Organization account value is too long")
    if field_name == "Email":
        lowered = normalized.lower()
        local, separator, domain = lowered.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("Email is invalid")
        return lowered
    return normalized


def _nullable_int(value: str, *, field_name: str) -> int | None:
    normalized = value.strip().lower()
    if normalized in _NULL_SENTINELS:
        return None
    try:
        parsed = int(normalized)
    except ValueError as exception:
        raise ValueError(f"{field_name} must be an integer or null") from exception
    if parsed <= 0:
        raise ValueError(f"{field_name} must be positive")
    return parsed


def _required_int(value: str, *, field_name: str) -> int:
    parsed = _nullable_int(value, field_name=field_name)
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def _nullable_bool(value: str, *, field_name: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in _NULL_SENTINELS:
        return None
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field_name} must be true, false, or null")


def _required_bool(value: str, *, field_name: str) -> bool:
    parsed = _nullable_bool(value, field_name=field_name)
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def _sentinel(value: int | bool | None) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)




class UpdateOrganizationContactEmailBridgeHandler:
    """Keep the legacy Overview profile and exact OrganizationAccount in sync."""

    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        contact_email = normalize_email(arguments["contact_email"])
        state = await self._gateway.get_contact_email_bridge_state(organization_id)
        if state is None:
            raise ValueError("Nucleus organization account was not found")
        account, legacy_version = state
        before = account.email
        if before == contact_email:
            raise ValueError("Organization contact email already has this value")
        return AgentActionPreparation(
            normalized_arguments={"contact_email": contact_email},
            changes=(
                AgentActionChange(
                    field="contact_email",
                    before=before,
                    after=contact_email,
                ),
            ),
            observed_resource_version=legacy_version,
            resource_type="organization",
            resource_id=organization_id,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        updated = await self._gateway.update_contact_email_bridge_if_version(
            organization_code=proposal.organization_id,
            value=proposal.arguments["contact_email"],
            expected_legacy_version=proposal.observed_resource_version,
            expected_nucleus_email=proposal.changes[0].before,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=proposal.organization_id,
            before={
                "contact_email": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "contact_email": updated.email,
                "version": updated.version,
            },
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._gateway.get_contact_email_bridge_state(
            proposal.organization_id
        )
        if state is None:
            return None
        account, legacy_version = state
        value = account.email
        if value != proposal.arguments["contact_email"]:
            return None
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=proposal.organization_id,
            before={
                "contact_email": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "contact_email": value,
                "version": legacy_version,
            },
        )


class UpdateNucleusOrganizationAccountFieldHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        field_name = _normalize_field_name(arguments["field_name"])
        value = _normalize_account_value(field_name, arguments["value"])
        state = await self._gateway.get_account_field_state(
            organization_id,
            field_name,
        )
        if state is None:
            raise ValueError("Nucleus organization account was not found")
        account, before = state
        if before == value:
            raise ValueError("Organization account field already has this value")
        return AgentActionPreparation(
            normalized_arguments={"field_name": field_name, "value": value},
            changes=(AgentActionChange(field=field_name, before=before, after=value),),
            observed_resource_version=account.version,
            resource_type="OrganizationAccount",
            resource_id=str(account.organization_account_id),
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        updated = await self._gateway.update_account_field_if_version(
            organization_code=proposal.organization_id,
            field_name=proposal.arguments["field_name"],
            value=proposal.arguments["value"],
            expected_version=proposal.observed_resource_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(updated.organization_account_id),
            before={
                "field_name": proposal.arguments["field_name"],
                "value": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "field_name": proposal.arguments["field_name"],
                "value": proposal.changes[0].after,
                "version": updated.version,
            },
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._gateway.get_account_field_state(
            proposal.organization_id,
            proposal.arguments["field_name"],
        )
        if state is None:
            return None
        account, value = state
        if value != proposal.arguments["value"]:
            return None
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(account.organization_account_id),
            before={
                "field_name": proposal.arguments["field_name"],
                "value": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "field_name": proposal.arguments["field_name"],
                "value": value,
                "version": account.version,
            },
        )


class ClearNucleusOrganizationAccountFieldHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        field_name = _normalize_field_name(arguments["field_name"])
        if field_name not in _CLEARABLE_FIELDS:
            raise ValueError("This organization account field cannot be cleared")
        state = await self._gateway.get_account_field_state(
            organization_id,
            field_name,
        )
        if state is None:
            raise ValueError("Nucleus organization account was not found")
        account, before = state
        if before is None:
            raise ValueError("Organization account field is already empty")
        return AgentActionPreparation(
            normalized_arguments={"field_name": field_name},
            changes=(AgentActionChange(field=field_name, before=before, after=None),),
            observed_resource_version=account.version,
            resource_type="OrganizationAccount",
            resource_id=str(account.organization_account_id),
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        updated = await self._gateway.update_account_field_if_version(
            organization_code=proposal.organization_id,
            field_name=proposal.arguments["field_name"],
            value=None,
            expected_version=proposal.observed_resource_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(updated.organization_account_id),
            before={
                "field_name": proposal.arguments["field_name"],
                "value": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "field_name": proposal.arguments["field_name"],
                "value": None,
                "version": updated.version,
            },
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._gateway.get_account_field_state(
            proposal.organization_id,
            proposal.arguments["field_name"],
        )
        if state is None:
            return None
        account, value = state
        if value is not None:
            return None
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(account.organization_account_id),
            before={
                "field_name": proposal.arguments["field_name"],
                "value": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "field_name": proposal.arguments["field_name"],
                "value": None,
                "version": account.version,
            },
        )


class GrantNucleusCategoryAccessHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        category_id = _required_int(arguments["category_id"], field_name="category_id")
        category_sample_id = _nullable_int(
            arguments["category_sample_id"],
            field_name="category_sample_id",
        )
        inspected = await self._gateway.inspect_category_grant(
            organization_code=organization_id,
            category_id=category_id,
            category_sample_id=category_sample_id,
        )
        if inspected is None:
            raise ValueError("Nucleus organization account was not found")
        existing, version = inspected
        if existing is not None and existing.is_active:
            raise ValueError("Category access is already active")
        before = None if existing is None else {
            "access_id": existing.access_id,
            "category_id": existing.category_id,
            "category_sample_id": existing.category_sample_id,
            "is_active": existing.is_active,
            "version": existing.version,
        }
        after = {
            "category_id": category_id,
            "category_sample_id": category_sample_id,
            "is_active": True,
        }
        return AgentActionPreparation(
            normalized_arguments={
                "category_id": str(category_id),
                "category_sample_id": _sentinel(category_sample_id),
            },
            changes=(AgentActionChange(field="category_access", before=before, after=after),),
            observed_resource_version=version,
            resource_type="OrganizationCategoryAccess",
            resource_id=str(existing.access_id) if existing is not None else f"category:{category_id}:{_sentinel(category_sample_id)}",
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._gateway.grant_category_access_if_version(
            organization_code=proposal.organization_id,
            category_id=_required_int(proposal.arguments["category_id"], field_name="category_id"),
            category_sample_id=_nullable_int(proposal.arguments["category_sample_id"], field_name="category_sample_id"),
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationCategoryAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before or {"is_active": None, "version": 0},
            after={
                "access_id": result.access_id,
                "category_id": result.category_id,
                "category_sample_id": result.category_sample_id,
                "is_active": result.is_active,
                "version": result.version,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        inspected = await self._gateway.inspect_category_grant(
            organization_code=proposal.organization_id,
            category_id=_required_int(proposal.arguments["category_id"], field_name="category_id"),
            category_sample_id=_nullable_int(proposal.arguments["category_sample_id"], field_name="category_sample_id"),
        )
        if inspected is None or inspected[0] is None or not inspected[0].is_active:
            return None
        result = inspected[0]
        return AgentActionHandlerResult(
            resource_type="OrganizationCategoryAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before or {"is_active": None, "version": 0},
            after={
                "access_id": result.access_id,
                "category_id": result.category_id,
                "category_sample_id": result.category_sample_id,
                "is_active": result.is_active,
                "version": result.version,
            },
        )


class RevokeNucleusCategoryAccessHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        access_id = _required_int(arguments["access_id"], field_name="access_id")
        current = await self._gateway.get_category_access(
            organization_code=organization_id,
            access_id=access_id,
        )
        if current is None:
            raise ValueError("Category access was not found")
        if not current.is_active:
            raise ValueError("Category access is already inactive")
        before = {
            "access_id": current.access_id,
            "category_id": current.category_id,
            "category_sample_id": current.category_sample_id,
            "is_active": True,
            "version": current.version,
        }
        after = {**before, "is_active": False}
        return AgentActionPreparation(
            normalized_arguments={"access_id": str(access_id)},
            changes=(AgentActionChange(field="category_access", before=before, after=after),),
            observed_resource_version=current.version,
            resource_type="OrganizationCategoryAccess",
            resource_id=str(access_id),
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._gateway.revoke_category_access_if_version(
            organization_code=proposal.organization_id,
            access_id=_required_int(proposal.arguments["access_id"], field_name="access_id"),
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationCategoryAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before,
            after={
                "access_id": result.access_id,
                "category_id": result.category_id,
                "category_sample_id": result.category_sample_id,
                "is_active": result.is_active,
                "version": result.version,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        result = await self._gateway.get_category_access(
            organization_code=proposal.organization_id,
            access_id=_required_int(proposal.arguments["access_id"], field_name="access_id"),
        )
        if result is None or result.is_active:
            return None
        return AgentActionHandlerResult(
            resource_type="OrganizationCategoryAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before,
            after={
                "access_id": result.access_id,
                "category_id": result.category_id,
                "category_sample_id": result.category_sample_id,
                "is_active": result.is_active,
                "version": result.version,
            },
        )


class GrantNucleusReportAccessHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    @staticmethod
    def _values(arguments: dict[str, str]) -> dict[str, int | bool | None]:
        values: dict[str, int | bool | None] = {
            "reports_id": _nullable_int(arguments["reports_id"], field_name="reports_id"),
            "sample_id": _nullable_int(arguments["sample_id"], field_name="sample_id"),
            "sample_toc_id": _nullable_int(arguments["sample_toc_id"], field_name="sample_toc_id"),
            "speciality_id": _nullable_int(arguments["speciality_id"], field_name="speciality_id"),
            "is_executive_access": _nullable_bool(arguments["executive_access"], field_name="executive_access"),
        }
        if all(values[name] is None for name in ("reports_id", "sample_id", "sample_toc_id", "speciality_id")):
            raise ValueError("At least one report access identifier is required")
        return values

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        values = self._values(arguments)
        inspected = await self._gateway.inspect_report_grant(
            organization_code=organization_id,
            **values,
        )
        if inspected is None:
            raise ValueError("Nucleus organization account was not found")
        existing, version = inspected
        if existing is not None and existing.is_active:
            raise ValueError("Report access is already active")
        before = None if existing is None else {
            "access_id": existing.access_id,
            "reports_id": existing.reports_id,
            "sample_id": existing.sample_id,
            "sample_toc_id": existing.sample_toc_id,
            "speciality_id": existing.speciality_id,
            "is_executive_access": existing.is_executive_access,
            "is_active": existing.is_active,
            "version": existing.version,
        }
        normalized_arguments = {
            "reports_id": _sentinel(values["reports_id"]),
            "sample_id": _sentinel(values["sample_id"]),
            "sample_toc_id": _sentinel(values["sample_toc_id"]),
            "speciality_id": _sentinel(values["speciality_id"]),
            "executive_access": _sentinel(values["is_executive_access"]),
        }
        return AgentActionPreparation(
            normalized_arguments=normalized_arguments,
            changes=(AgentActionChange(field="report_access", before=before, after={**values, "is_active": True}),),
            observed_resource_version=version,
            resource_type="OrganizationReportAccess",
            resource_id=str(existing.access_id) if existing is not None else "new-report-access",
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        values = self._values(proposal.arguments)
        result = await self._gateway.grant_report_access_if_version(
            organization_code=proposal.organization_id,
            expected_version=proposal.observed_resource_version,
            **values,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationReportAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before or {"is_active": None, "version": 0},
            after={
                "access_id": result.access_id,
                "reports_id": result.reports_id,
                "sample_id": result.sample_id,
                "sample_toc_id": result.sample_toc_id,
                "speciality_id": result.speciality_id,
                "is_executive_access": result.is_executive_access,
                "is_active": result.is_active,
                "version": result.version,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        values = self._values(proposal.arguments)
        inspected = await self._gateway.inspect_report_grant(
            organization_code=proposal.organization_id,
            **values,
        )
        if inspected is None or inspected[0] is None or not inspected[0].is_active:
            return None
        result = inspected[0]
        return AgentActionHandlerResult(
            resource_type="OrganizationReportAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before or {"is_active": None, "version": 0},
            after={
                "access_id": result.access_id,
                "reports_id": result.reports_id,
                "sample_id": result.sample_id,
                "sample_toc_id": result.sample_toc_id,
                "speciality_id": result.speciality_id,
                "is_executive_access": result.is_executive_access,
                "is_active": result.is_active,
                "version": result.version,
            },
        )


class RevokeNucleusReportAccessHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        access_id = _required_int(arguments["access_id"], field_name="access_id")
        current = await self._gateway.get_report_access(
            organization_code=organization_id,
            access_id=access_id,
        )
        if current is None:
            raise ValueError("Report access was not found")
        if not current.is_active:
            raise ValueError("Report access is already inactive")
        before = {
            "access_id": current.access_id,
            "reports_id": current.reports_id,
            "sample_id": current.sample_id,
            "sample_toc_id": current.sample_toc_id,
            "speciality_id": current.speciality_id,
            "is_executive_access": current.is_executive_access,
            "is_active": True,
            "version": current.version,
        }
        return AgentActionPreparation(
            normalized_arguments={"access_id": str(access_id)},
            changes=(AgentActionChange(field="report_access", before=before, after={**before, "is_active": False}),),
            observed_resource_version=current.version,
            resource_type="OrganizationReportAccess",
            resource_id=str(access_id),
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._gateway.revoke_report_access_if_version(
            organization_code=proposal.organization_id,
            access_id=_required_int(proposal.arguments["access_id"], field_name="access_id"),
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationReportAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before,
            after={
                "access_id": result.access_id,
                "reports_id": result.reports_id,
                "sample_id": result.sample_id,
                "sample_toc_id": result.sample_toc_id,
                "speciality_id": result.speciality_id,
                "is_executive_access": result.is_executive_access,
                "is_active": result.is_active,
                "version": result.version,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        result = await self._gateway.get_report_access(
            organization_code=proposal.organization_id,
            access_id=_required_int(proposal.arguments["access_id"], field_name="access_id"),
        )
        if result is None or result.is_active:
            return None
        return AgentActionHandlerResult(
            resource_type="OrganizationReportAccess",
            resource_id=str(result.access_id),
            before=proposal.changes[0].before,
            after={
                "access_id": result.access_id,
                "reports_id": result.reports_id,
                "sample_id": result.sample_id,
                "sample_toc_id": result.sample_toc_id,
                "speciality_id": result.speciality_id,
                "is_executive_access": result.is_executive_access,
                "is_active": result.is_active,
                "version": result.version,
            },
        )


_PERMISSION_ARGUMENT_TO_ATTRIBUTE = {
    "cp_company_master_pharma_id": "cp_company_master_pharma_id",
    "hc_theropetic_category_pharma_id": "hc_theropetic_category_pharma_id",
    "hc_theropetic_category_epidem_id": "hc_theropetic_category_epidem_id",
    "hc_disease_code_epidem_id": "hc_disease_code_epidem_id",
    "reports_custom_id": "reports_custom_id",
    "importexport_report_id": "importexport_report_id",
}


class UpdateNucleusOrganizationPermissionsHandler:
    def __init__(self, gateway: NucleusOrganizationGateway) -> None:
        self._gateway = gateway

    @staticmethod
    def _values(arguments: dict[str, str]) -> dict[str, int | bool | None]:
        values: dict[str, int | bool | None] = {
            argument_name: _nullable_int(
                arguments[argument_name],
                field_name=argument_name,
            )
            for argument_name in _PERMISSION_ARGUMENT_TO_ATTRIBUTE
        }
        values["is_active"] = _required_bool(
            arguments["is_active"],
            field_name="is_active",
        )
        return values

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        permission_id = _nullable_int(
            arguments["permission_id"],
            field_name="permission_id",
        )
        values = self._values(arguments)
        if permission_id is None:
            before: dict[str, Any] | None = None
            version = 0
            resource_id = "new"
        else:
            current = await self._gateway.get_permission(
                organization_code=organization_id,
                permission_id=permission_id,
            )
            if current is None:
                raise ValueError("OrganizationPermission row was not found")
            before = {
                name: getattr(current, attribute)
                for name, attribute in _PERMISSION_ARGUMENT_TO_ATTRIBUTE.items()
            }
            before.update(
                {
                    "is_active": current.is_active,
                    "permission_id": current.permission_id,
                    "version": current.version,
                }
            )
            version = current.version
            resource_id = str(current.permission_id)
            comparable_before = {name: before[name] for name in values}
            if comparable_before == values:
                raise ValueError("OrganizationPermission already matches this state")

        normalized = {
            "permission_id": _sentinel(permission_id),
            **{name: _sentinel(value) for name, value in values.items()},
        }
        return AgentActionPreparation(
            normalized_arguments=normalized,
            changes=(
                AgentActionChange(
                    field="organization_permission",
                    before=before,
                    after={"permission_id": permission_id, **values},
                ),
            ),
            observed_resource_version=version,
            resource_type="OrganizationPermission",
            resource_id=resource_id,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        permission_id = _nullable_int(
            proposal.arguments["permission_id"],
            field_name="permission_id",
        )
        values = self._values(proposal.arguments)
        result = await self._gateway.set_permission_if_version(
            organization_code=proposal.organization_id,
            permission_id=permission_id,
            values=values,
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        after = {
            name: getattr(result, attribute)
            for name, attribute in _PERMISSION_ARGUMENT_TO_ATTRIBUTE.items()
        }
        after.update(
            {
                "is_active": result.is_active,
                "permission_id": result.permission_id,
                "version": result.version,
            }
        )
        return AgentActionHandlerResult(
            resource_type="OrganizationPermission",
            resource_id=str(result.permission_id),
            before=proposal.changes[0].before or {"version": 0},
            after=after,
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        permission_id = _nullable_int(
            proposal.arguments["permission_id"],
            field_name="permission_id",
        )
        if permission_id is None:
            result_payload = dict((execution.result or {}).get("after") or {})
            created_id = result_payload.get("permission_id")
            if not isinstance(created_id, int):
                return None
            permission_id = created_id
        result = await self._gateway.get_permission(
            organization_code=proposal.organization_id,
            permission_id=permission_id,
        )
        if result is None:
            return None
        expected = self._values(proposal.arguments)
        current = {
            name: getattr(result, attribute)
            for name, attribute in _PERMISSION_ARGUMENT_TO_ATTRIBUTE.items()
        }
        current["is_active"] = result.is_active
        if current != expected:
            return None
        current.update(
            {
                "permission_id": result.permission_id,
                "version": result.version,
            }
        )
        return AgentActionHandlerResult(
            resource_type="OrganizationPermission",
            resource_id=str(result.permission_id),
            before=proposal.changes[0].before or {"version": 0},
            after=current,
        )
