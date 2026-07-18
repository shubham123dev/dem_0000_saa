from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionDefinition,
    AgentActionProposalInput,
    AgentActionResourcePrecondition,
    AgentApprovalPolicy,
)
from app.domain.enums import Permission


class InvalidAgentActionProposalError(ValueError):
    pass


class AgentActionRegistry:
    def __init__(self) -> None:
        self._definitions = {
            definition.name: definition
            for definition in (
                self._definition(
                    name="update_organization_contact_email",
                    description="Propose changing the canonical contact email and synchronizing the Overview profile.",
                    arguments=("contact_email",),
                    permission=Permission.ORGANIZATION_PROFILE_UPDATE,
                    resource_type="organization",
                    risk_level="low",
                ),
                self._definition(
                    name="update_nucleus_organization_account_field",
                    description=(
                        "Propose updating one allowlisted Nucleus OrganizationAccount "
                        "profile/contact field. Arguments are field_name and value."
                    ),
                    arguments=("field_name", "value"),
                    permission=Permission.ORGANIZATION_ACCOUNT_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="low",
                ),
                self._definition(
                    name="clear_nucleus_organization_account_field",
                    description=(
                        "Propose clearing one nullable allowlisted Nucleus "
                        "OrganizationAccount profile/contact field."
                    ),
                    arguments=("field_name",),
                    permission=Permission.ORGANIZATION_ACCOUNT_UPDATE,
                    resource_type="OrganizationAccount",
                    risk_level="low",
                ),
                self._definition(
                    name="grant_nucleus_category_access",
                    description=(
                        "Propose granting or reactivating OrganizationCategoryAccess. "
                        "Use category_sample_id='null' when no sample is intended."
                    ),
                    arguments=("category_id", "category_sample_id"),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationCategoryAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_category_access",
                    description=(
                        "Propose setting one OrganizationCategoryAccess row inactive "
                        "by its access_id."
                    ),
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationCategoryAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="grant_nucleus_report_access",
                    description=(
                        "Propose granting or reactivating OrganizationReportAccess. "
                        "Use 'null' for nullable identifiers or executive_access."
                    ),
                    arguments=(
                        "reports_id",
                        "sample_id",
                        "sample_toc_id",
                        "speciality_id",
                        "executive_access",
                    ),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationReportAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_nucleus_report_access",
                    description=(
                        "Propose setting one OrganizationReportAccess row inactive "
                        "by its access_id."
                    ),
                    arguments=("access_id",),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationReportAccess",
                    risk_level="medium",
                ),
                self._definition(
                    name="update_nucleus_organization_permissions",
                    description=(
                        "Propose creating or replacing one exact OrganizationPermission "
                        "row. Use permission_id='null' to create and 'null' for an unset resource ID."
                    ),
                    arguments=(
                        "permission_id",
                        "cp_company_master_pharma_id",
                        "hc_theropetic_category_pharma_id",
                        "hc_theropetic_category_epidem_id",
                        "hc_disease_code_epidem_id",
                        "reports_custom_id",
                        "importexport_report_id",
                        "is_active",
                    ),
                    permission=Permission.ORGANIZATION_ENTITLEMENTS_UPDATE,
                    resource_type="OrganizationPermission",
                    risk_level="high",
                ),
                self._definition(
                    name="invite_organization_user",
                    description="Propose inviting a user with a backend-supported role.",
                    arguments=("email", "display_name", "role"),
                    permission=Permission.ORGANIZATION_USERS_INVITE,
                    resource_type="organization_membership",
                    risk_level="medium",
                ),
                self._definition(
                    name="activate_organization_membership",
                    description="Propose activating an invited organization membership.",
                    arguments=("user_id",),
                    permission=Permission.ORGANIZATION_USERS_UPDATE,
                    resource_type="organization_membership",
                    risk_level="medium",
                ),
                self._definition(
                    name="update_organization_member_role",
                    description="Propose changing an active organization member role.",
                    arguments=("user_id", "role"),
                    permission=Permission.ORGANIZATION_USERS_UPDATE,
                    resource_type="organization_membership",
                    risk_level="high",
                ),
                self._definition(
                    name="remove_organization_user",
                    description="Propose removing a user membership after seat and last-admin checks.",
                    arguments=("user_id",),
                    permission=Permission.ORGANIZATION_USERS_REMOVE,
                    resource_type="organization_membership",
                    risk_level="high",
                ),
                self._definition(
                    name="assign_organization_seat",
                    description="Propose assigning an available standard seat to an active member.",
                    arguments=("user_id", "seat_type"),
                    permission=Permission.ORGANIZATION_SEATS_ASSIGN,
                    resource_type="seat_assignment",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_organization_seat",
                    description="Propose revoking an active standard seat assignment.",
                    arguments=("user_id", "seat_type"),
                    permission=Permission.ORGANIZATION_SEATS_REVOKE,
                    resource_type="seat_assignment",
                    risk_level="medium",
                ),
                self._definition(
                    name="grant_organization_report_access",
                    description="Propose granting or upgrading legacy organization report access.",
                    arguments=("report_id", "access_level"),
                    permission=Permission.ORGANIZATION_REPORTS_GRANT,
                    resource_type="organization_report_access",
                    risk_level="medium",
                ),
                self._definition(
                    name="revoke_organization_report_access",
                    description="Propose revoking active legacy organization report access.",
                    arguments=("report_id",),
                    permission=Permission.ORGANIZATION_REPORTS_REVOKE,
                    resource_type="organization_report_access",
                    risk_level="medium",
                ),
            )
        }

    @staticmethod
    def _definition(
        *,
        name: str,
        description: str,
        arguments: tuple[str, ...],
        permission: Permission,
        resource_type: str,
        risk_level: str,
    ) -> AgentActionDefinition:
        permission_value = permission.value
        high_risk = risk_level == "high"
        return AgentActionDefinition(
            name=name,
            description=description,
            required_argument_names=arguments,
            required_permission=permission_value,
            resource_type=resource_type,
            risk_level=risk_level,
            requires_approval=True,
            supports_dry_run=True,
            approval_policy=AgentApprovalPolicy(
                self_approval_allowed=not high_risk,
                required_approver_permission=permission_value,
                minimum_approvals=2 if high_risk else 1,
            ),
        )

    def list_definitions(self) -> tuple[AgentActionDefinition, ...]:
        return tuple(self._definitions.values())

    def get_definition(self, action_name: str) -> AgentActionDefinition:
        definition = self._definitions.get(action_name)
        if definition is None:
            raise InvalidAgentActionProposalError("Unknown agent action")
        return definition

    def validate(self, proposal_input: AgentActionProposalInput) -> AgentActionDefinition:
        forbidden = {
            "organization_id",
            "actor_user_id",
            "permission",
            "approved",
            "approval",
            "approval_decision",
            "proposal_id",
            "idempotency_key",
            "execute",
        }
        if set(proposal_input.arguments) & forbidden:
            raise InvalidAgentActionProposalError(
                "Identity, authorization, approval, and execution arguments are forbidden"
            )
        definition = self.get_definition(proposal_input.action_name)
        if set(proposal_input.arguments) != set(definition.required_argument_names):
            raise InvalidAgentActionProposalError("Agent action arguments are invalid")
        return definition


def _canonical_utc_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="microseconds")


def build_action_fingerprint(
    *,
    organization_id: str,
    requested_by_user_id: str,
    action_name: str,
    arguments: dict[str, str],
    changes: tuple[AgentActionChange, ...],
    observed_resource_version: int,
    approval_policy: AgentApprovalPolicy,
    resource_type: str,
    resource_id: str,
    expires_at: datetime,
    resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = (),
    fingerprint_version: int = 3,
) -> str:
    payload = {
        "organization_id": organization_id,
        "requested_by_user_id": requested_by_user_id,
        "action_name": action_name,
        "arguments": dict(sorted(arguments.items())),
        "changes": [change.model_dump(mode="json") for change in changes],
        "observed_resource_version": observed_resource_version,
        "approval_policy": approval_policy.model_dump(mode="json"),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "expires_at": _canonical_utc_datetime(expires_at),
    }
    if fingerprint_version == 2:
        payload["version"] = 2
    elif fingerprint_version == 3:
        if not resource_preconditions:
            resource_preconditions = (
                AgentActionResourcePrecondition(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    observed_version=observed_resource_version,
                ),
            )
        payload["resource_preconditions"] = [
            item.model_dump(mode="json")
            for item in sorted(
                resource_preconditions,
                key=lambda item: (item.resource_type, item.resource_id),
            )
        ]
        payload["version"] = 3
    else:
        raise ValueError("Unsupported action fingerprint version")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
