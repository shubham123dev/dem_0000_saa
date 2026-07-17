from __future__ import annotations

import hashlib
import json

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.domain.enums import Permission


class InvalidAgentActionProposalError(ValueError):
    pass


class AgentActionRegistry:
    def __init__(self) -> None:
        self._definitions = {
            "update_organization_contact_email": AgentActionDefinition(
                name="update_organization_contact_email",
                description="Propose changing the organization contact email.",
                required_argument_names=("contact_email",),
                required_permission=Permission.ORGANIZATION_PROFILE_UPDATE.value,
                resource_type="organization",
                risk_level="low",
                requires_approval=True,
                supports_dry_run=True,
            )
        }

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
            "user_id",
            "actor_user_id",
            "permission",
            "role",
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
    resource_type: str,
    resource_id: str,
) -> str:
    fingerprint_payload = {
        "organization_id": organization_id,
        "requested_by_user_id": requested_by_user_id,
        "action_name": action_name,
        "arguments": dict(sorted(arguments.items())),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "version": 1,
    }
    canonical_payload = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
