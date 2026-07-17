from __future__ import annotations

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
    VersionedOrganizationMutationGateway,
)


class StaleActionResourceError(RuntimeError):
    pass


def normalize_contact_email(value: str) -> str:
    normalized_value = value.strip().lower()
    local_part, separator, domain_part = normalized_value.partition("@")
    if (
        not separator
        or not local_part
        or "." not in domain_part
        or len(normalized_value) > 320
    ):
        raise ValueError("Contact email is invalid")
    return normalized_value


class UpdateOrganizationContactEmailHandler:
    def __init__(self, gateway: VersionedOrganizationMutationGateway) -> None:
        self._gateway = gateway

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        profile = await self._gateway.get_profile(organization_id)
        contact_email = normalize_contact_email(arguments["contact_email"])
        return AgentActionPreparation(
            normalized_arguments={"contact_email": contact_email},
            changes=(
                AgentActionChange(
                    field="contact_email",
                    before=profile.contact_email,
                    after=contact_email,
                ),
            ),
            observed_resource_version=profile.version,
            resource_type="organization",
            resource_id=organization_id,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        updated_profile = await self._gateway.update_contact_email_if_version(
            proposal.organization_id,
            proposal.arguments["contact_email"],
            proposal.observed_resource_version,
        )
        if updated_profile is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=updated_profile.id,
            before={
                "contact_email": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "contact_email": updated_profile.contact_email,
                "version": updated_profile.version,
            },
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        profile = await self._gateway.get_profile(proposal.organization_id)
        if (
            profile.contact_email == proposal.arguments["contact_email"]
            and profile.version >= proposal.observed_resource_version + 1
        ):
            return AgentActionHandlerResult(
                resource_type="organization",
                resource_id=profile.id,
                before={
                    "contact_email": proposal.changes[0].before,
                    "version": proposal.observed_resource_version,
                },
                after={
                    "contact_email": profile.contact_email,
                    "version": profile.version,
                },
            )
        return None
