from __future__ import annotations

from datetime import datetime
import hashlib
import json

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionDefinition,
    AgentActionProposalInput,
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
                    description="Propose changing the organization contact email.",
                    arguments=("contact_email",),
                    permission=Permission.ORGANIZATION_PROFILE_UPDATE,
                    resource_type="organization",
                    risk_level="low",
                ),
                self._definition(
                    name="invite_organization_user",
                    description="Propose inviting a user to the organization with a backend-supported role.",
                    arguments=("email", "display_name", "role"),
                    permission=Permission.ORGANIZATION_USERS_INVITE,
                    resource_type="organization_membership",
                    risk_level="medium",
                ),
                self._definition(
                    name="assign_organization_seat",
                    description="Propose assigning an available standard seat to an active organization member.",
                    arguments=("user_id", "seat_type"),
                    permission=Permission.ORGANIZATION_SEATS_ASSIGN,
                    resource_type="seat_assignment",
                    risk_level="medium",
                ),
                self._definition(
                    name="grant_organization_report_access",
                    description="Propose granting or upgrading organization access to an active report.",
                    arguments=("report_id", "access_level"),
                    permission=Permission.ORGANIZATION_REPORTS_GRANT,
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
                self_approval_allowed=True,
                required_approver_permission=permission_value,
                minimum_approvals=1,
            ),
        )

    def list_definitions(self) -> tuple[AgentActionDefinition, ...]:
        return tuple(self._definitions.values())

    def get_definition(self, action_name: str) -> AgentActionDefinition:
        action_definition = self._definitions.get(action_name)
        if action_definition is None:
            raise InvalidAgentActionProposalError("Unknown agent action")
        return action_definition

    def validate(self, proposal_input: AgentActionProposalInput) -> AgentActionDefinition:
        forbidden_argument_names = {
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
        if set(proposal_input.arguments) & forbidden_argument_names:
            raise InvalidAgentActionProposalError(
                "Identity, authorization, approval, and execution arguments are forbidden"
            )
        action_definition = self.get_definition(proposal_input.action_name)
        if set(proposal_input.arguments) != set(action_definition.required_argument_names):
            raise InvalidAgentActionProposalError("Agent action arguments are invalid")
        return action_definition


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
) -> str:
    fingerprint_payload = {
        "organization_id": organization_id,
        "requested_by_user_id": requested_by_user_id,
        "action_name": action_name,
        "arguments": dict(sorted(arguments.items())),
        "changes": [change.model_dump(mode="json") for change in changes],
        "observed_resource_version": observed_resource_version,
        "approval_policy": approval_policy.model_dump(mode="json"),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "expires_at": expires_at.isoformat(),
        "version": 2,
    }
    canonical_payload = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
