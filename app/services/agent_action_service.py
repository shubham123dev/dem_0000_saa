from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.adapters.organization.contract import OrganizationApiGateway
from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionProposal,
    AgentActionProposalInput,
)
from app.agent.action_errors import (
    AgentActionExpiredError,
    AgentActionInvalidError,
    AgentActionProposalNotFoundError,
    AgentActionStateConflictError,
)
from app.agent.action_registry import (
    AgentActionRegistry,
    InvalidAgentActionProposalError,
    build_action_fingerprint,
)
from app.core.errors import OrganizationSuspendedError, ProductionAccessBlockedError
from app.domain.enums import Environment, OrganizationStatus
from app.domain.models import User
from app.permissions.permission_service import PermissionService
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.audit_repository import AuditRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class AgentActionService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationApiGateway,
        permission_service: PermissionService,
        action_repository: AgentActionRepository,
        audit_repository: AuditRepository,
        action_registry: AgentActionRegistry,
    ) -> None:
        self._organization_gateway = organization_gateway
        self._permission_service = permission_service
        self._action_repository = action_repository
        self._audit_repository = audit_repository
        self._action_registry = action_registry

    async def propose(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_input: AgentActionProposalInput,
    ) -> AgentActionProposal:
        try:
            action_definition = self._action_registry.validate(proposal_input)
        except InvalidAgentActionProposalError as exception:
            raise AgentActionInvalidError() from exception

        organization_profile = await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=action_definition.required_permission,
        )
        contact_email = proposal_input.arguments["contact_email"].strip().lower()
        normalized_arguments = {"contact_email": contact_email}
        changes = (
            AgentActionChange(
                field="contact_email",
                before=organization_profile.contact_email,
                after=contact_email,
            ),
        )
        action_fingerprint = build_action_fingerprint(
            organization_id=organization_id,
            requested_by_user_id=user.id,
            action_name=action_definition.name,
            arguments=normalized_arguments,
            resource_type=action_definition.resource_type,
            resource_id=organization_id,
        )
        proposal = await self._action_repository.create_proposal(
            organization_id=organization_id,
            requested_by_user_id=user.id,
            action_name=action_definition.name,
            arguments=normalized_arguments,
            changes=changes,
            action_fingerprint=action_fingerprint,
            risk_level=action_definition.risk_level,
            resource_type=action_definition.resource_type,
            resource_id=organization_id,
            expires_at=_utcnow() + timedelta(minutes=15),
        )
        await self._append_audit(
            user=user,
            proposal=proposal,
            event_type="agent_action_proposed",
            outcome="success",
            details={"risk_level": proposal.risk_level},
        )
        return proposal

    async def get_proposal(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionProposal:
        proposal = await self._require_proposal(
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        action_definition = self._action_registry.get_definition(proposal.action_name)
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=action_definition.required_permission,
        )
        return proposal

    async def decide(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        decision: str,
        reason: str | None,
    ) -> AgentActionApproval:
        proposal = await self.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        if proposal.status != "pending_approval":
            raise AgentActionStateConflictError()
        if _as_aware(proposal.expires_at) <= _utcnow():
            await self._action_repository.mark_expired(proposal.id)
            raise AgentActionExpiredError()
        approval = await self._action_repository.decide(
            proposal_id=proposal.id,
            decided_by_user_id=user.id,
            decision=decision,
            decision_reason=reason,
        )
        await self._append_audit(
            user=user,
            proposal=proposal,
            event_type=(
                "agent_action_approved"
                if decision == "approved"
                else "agent_action_rejected"
            ),
            outcome="success",
            details={"reason": reason},
        )
        return approval

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        idempotency_key: str,
    ) -> AgentActionExecutionResult:
        proposal = await self.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        if _as_aware(proposal.expires_at) <= _utcnow():
            await self._action_repository.mark_expired(proposal.id)
            raise AgentActionExpiredError()
        if proposal.status != "approved":
            raise AgentActionStateConflictError()
        expected_fingerprint = build_action_fingerprint(
            organization_id=proposal.organization_id,
            requested_by_user_id=proposal.requested_by_user_id,
            action_name=proposal.action_name,
            arguments=proposal.arguments,
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
        )
        if expected_fingerprint != proposal.action_fingerprint:
            raise AgentActionStateConflictError("Action proposal fingerprint is invalid.")
        approval = await self._action_repository.get_approval(proposal.id)
        if approval is None or approval.decision != "approved":
            raise AgentActionStateConflictError("Explicit approval is required.")
        if approval.consumed_at is not None:
            raise AgentActionStateConflictError("Action approval has already been consumed.")

        try:
            await self._action_repository.start_execution(
                proposal_id=proposal.id,
                idempotency_key=idempotency_key,
            )
        except (PermissionError, RuntimeError) as exception:
            raise AgentActionStateConflictError() from exception

        await self._append_audit(
            user=user,
            proposal=proposal,
            event_type="agent_action_execution_started",
            outcome="success",
            details={"idempotency_key": idempotency_key},
        )
        try:
            updated_profile = await self._organization_gateway.update_contact_email(
                organization_id,
                proposal.arguments["contact_email"],
            )
            execution_result = await self._action_repository.complete_execution(
                proposal_id=proposal.id,
                outcome="succeeded",
                result={
                    "organization_id": updated_profile.id,
                    "contact_email": updated_profile.contact_email,
                    "version": updated_profile.version,
                },
                error_code=None,
            )
            await self._append_audit(
                user=user,
                proposal=proposal,
                event_type="agent_action_succeeded",
                outcome="success",
                details=execution_result.result,
            )
            return execution_result
        except Exception as exception:
            await self._action_repository.complete_execution(
                proposal_id=proposal.id,
                outcome="failed",
                result=None,
                error_code="action_execution_failed",
            )
            await self._append_audit(
                user=user,
                proposal=proposal,
                event_type="agent_action_failed",
                outcome="failure",
                details={"error_code": "action_execution_failed"},
            )
            raise exception

    async def _authorize(
        self,
        *,
        user: User,
        organization_id: str,
        required_permission: str,
    ):
        organization_profile = await self._organization_gateway.get_profile(
            organization_id
        )
        if organization_profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()
        if organization_profile.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()
        await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        return organization_profile

    async def _require_proposal(
        self,
        *,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionProposal:
        proposal = await self._action_repository.get_proposal(
            proposal_id=proposal_id,
            organization_id=organization_id,
        )
        if proposal is None:
            raise AgentActionProposalNotFoundError()
        return proposal

    async def _append_audit(
        self,
        *,
        user: User,
        proposal: AgentActionProposal,
        event_type: str,
        outcome: str,
        details: dict | None,
    ) -> None:
        audit_details = {
            "proposal_id": proposal.id,
            "action_name": proposal.action_name,
            "action_fingerprint": proposal.action_fingerprint,
        }
        if details:
            audit_details.update(details)
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=proposal.organization_id,
            event_type=event_type,
            operation="write",
            outcome=outcome,
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            details=audit_details,
        )
