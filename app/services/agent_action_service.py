from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.organization.contract import OrganizationApiGateway
from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionExecutionContext,
    AgentActionExecutionResult,
    AgentActionHandler,
    AgentActionProposal,
    AgentActionProposalInput,
)
from app.agent.action_errors import (
    AgentActionAlreadyDecidedError,
    AgentActionCancelledError,
    AgentActionExecutionInProgressError,
    AgentActionExpiredError,
    AgentActionIdempotencyConflictError,
    AgentActionInvalidError,
    AgentActionProposalNotFoundError,
    AgentActionReconciliationRequiredError,
    AgentActionStaleError,
    AgentActionStateConflictError,
)
from app.agent.action_handlers import StaleActionResourceError
from app.agent.action_registry import (
    AgentActionRegistry,
    InvalidAgentActionProposalError,
    build_action_fingerprint,
)
from app.core.errors import OrganizationSuspendedError, ProductionAccessBlockedError
from app.domain.enums import Environment, OrganizationStatus, Permission
from app.domain.models import User
from app.permissions.permission_service import PermissionService
from app.repositories.agent_action_repository import (
    AgentActionRepository,
    AgentActionTransitionConflictError,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.nucleus_actor_mapping_repository import (
    NucleusActorMappingRepository,
)


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
        action_handlers: dict[str, AgentActionHandler],
        nucleus_actor_mapping_repository: NucleusActorMappingRepository,
    ) -> None:
        self._organization_gateway = organization_gateway
        self._permission_service = permission_service
        self._action_repository = action_repository
        self._audit_repository = audit_repository
        self._action_registry = action_registry
        self._action_handlers = action_handlers
        self._nucleus_actor_mapping_repository = (
            nucleus_actor_mapping_repository
        )

    async def propose(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_input: AgentActionProposalInput,
        provenance: dict[str, Any] | None = None,
    ) -> AgentActionProposal:
        try:
            action_definition = self._action_registry.validate(proposal_input)
        except InvalidAgentActionProposalError as exception:
            raise AgentActionInvalidError() from exception
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=action_definition.required_permission,
            allow_suspended_organization=(
                action_definition.allow_suspended_organization
            ),
        )
        handler = self._require_handler(action_definition.name)
        try:
            preparation = await handler.prepare(
                organization_id=organization_id,
                arguments=proposal_input.arguments,
            )
        except (KeyError, ValueError) as exception:
            raise AgentActionInvalidError(str(exception)) from exception
        expires_at = _utcnow() + timedelta(minutes=15)
        fingerprint = build_action_fingerprint(
            organization_id=organization_id,
            requested_by_user_id=user.id,
            action_name=action_definition.name,
            arguments=preparation.normalized_arguments,
            changes=preparation.changes,
            observed_resource_version=preparation.observed_resource_version,
            resource_preconditions=preparation.resource_preconditions,
            fingerprint_version=3,
            approval_policy=action_definition.approval_policy,
            resource_type=preparation.resource_type,
            resource_id=preparation.resource_id,
            expires_at=expires_at,
        )
        proposal = await self._action_repository.create_proposal(
            organization_id=organization_id,
            requested_by_user_id=user.id,
            action_name=action_definition.name,
            arguments=preparation.normalized_arguments,
            changes=preparation.changes,
            action_fingerprint=fingerprint,
            risk_level=action_definition.risk_level,
            resource_type=preparation.resource_type,
            resource_id=preparation.resource_id,
            observed_resource_version=preparation.observed_resource_version,
            resource_preconditions=preparation.resource_preconditions,
            fingerprint_version=3,
            approval_policy=action_definition.approval_policy,
            expires_at=expires_at,
        )
        details = {"risk_level": proposal.risk_level}
        if provenance:
            details.update(provenance)
        await self._append_audit(
            user=user,
            proposal=proposal,
            event_type="agent_action_proposed",
            outcome="success",
            details=details,
        )
        return proposal

    async def list_proposals(
        self,
        *,
        user: User,
        organization_id: str,
        status: str | None = None,
    ) -> tuple[AgentActionProposal, ...]:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.ORGANIZATION_PROFILE_UPDATE.value,
        )
        proposals = await self._action_repository.list_proposals(
            organization_id=organization_id,
            status=status,
        )
        refreshed: list[AgentActionProposal] = []
        for proposal in proposals:
            refreshed.append(await self._expire_if_needed(proposal))
        return tuple(refreshed)

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
            allow_suspended_organization=(
                action_definition.allow_suspended_organization
            ),
        )
        return await self._expire_if_needed(proposal)

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
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=proposal.approval_policy.required_approver_permission,
            allow_suspended_organization=True,
        )
        if (
            not proposal.approval_policy.self_approval_allowed
            and proposal.requested_by_user_id == user.id
        ):
            raise AgentActionStateConflictError("Self-approval is not allowed.")
        if proposal.status == "expired":
            raise AgentActionExpiredError()
        if proposal.status == "cancelled":
            raise AgentActionCancelledError()
        if proposal.status != "pending_approval":
            raise AgentActionAlreadyDecidedError()
        try:
            approval = await self._action_repository.decide(
                proposal_id=proposal.id,
                decided_by_user_id=user.id,
                decision=decision,
                decision_reason=reason,
            )
        except AgentActionTransitionConflictError as exception:
            raise AgentActionAlreadyDecidedError() from exception
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

    async def cancel(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        reason: str | None,
    ) -> AgentActionProposal:
        proposal = await self.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        if proposal.status not in {"pending_approval", "approved"}:
            raise AgentActionStateConflictError()
        changed = await self._action_repository.transition_status(
            proposal_id=proposal.id,
            current_statuses=(proposal.status,),
            target_status="cancelled",
        )
        if not changed:
            raise AgentActionStateConflictError()
        cancelled = await self._require_proposal(
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        await self._append_audit(
            user=user,
            proposal=cancelled,
            event_type="agent_action_cancelled",
            outcome="success",
            details={"reason": reason},
        )
        return cancelled

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
        existing_execution = await self._action_repository.get_execution(proposal.id)
        if existing_execution is not None:
            if existing_execution.idempotency_key != idempotency_key:
                raise AgentActionIdempotencyConflictError()
            if existing_execution.outcome == "executing":
                raise AgentActionExecutionInProgressError()
            if existing_execution.outcome == "reconciliation_required":
                raise AgentActionReconciliationRequiredError()
            return existing_execution
        if proposal.status == "expired":
            raise AgentActionExpiredError()
        if proposal.status == "cancelled":
            raise AgentActionCancelledError()
        if proposal.status == "stale":
            raise AgentActionStaleError()
        if proposal.status != "approved":
            raise AgentActionStateConflictError("Explicit approval is required.")
        self._validate_fingerprint(proposal)
        approval = await self._action_repository.get_approval(proposal.id)
        if approval is None or approval.decision != "approved":
            raise AgentActionStateConflictError("Explicit approval is required.")
        if approval.consumed_at is not None:
            raise AgentActionStateConflictError("Action approval has already been consumed.")
        handler = self._require_handler(proposal.action_name)
        current_preparation = await handler.prepare(
            organization_id=organization_id,
            arguments=proposal.arguments,
        )
        if (
            current_preparation.resource_preconditions
            != proposal.resource_preconditions
            or current_preparation.changes != proposal.changes
        ):
            await self._action_repository.transition_status(
                proposal_id=proposal.id,
                current_statuses=("approved",),
                target_status="stale",
            )
            raise AgentActionStaleError()
        nucleus_actor_id = None
        if getattr(handler, "requires_execution_context", False):
            nucleus_actor_id = (
                await self._nucleus_actor_mapping_repository.get_nucleus_actor_id(
                    user.id
                )
            )
            if nucleus_actor_id is None:
                raise AgentActionStateConflictError(
                    "Executor has no Nucleus actor mapping."
                )
        try:
            started_execution = await self._action_repository.start_execution(
                proposal_id=proposal.id,
                idempotency_key=idempotency_key,
                executed_by_user_id=user.id,
                nucleus_actor_id=nucleus_actor_id,
            )
        except AgentActionTransitionConflictError as exception:
            concurrent_execution = await self._action_repository.get_execution(proposal.id)
            if (
                concurrent_execution is not None
                and concurrent_execution.idempotency_key == idempotency_key
            ):
                if concurrent_execution.outcome == "executing":
                    raise AgentActionExecutionInProgressError() from exception
                return concurrent_execution
            raise AgentActionStateConflictError() from exception
        await self._append_execution_audit_safely(
            user=user,
            proposal=proposal,
            event_type="agent_action_execution_started",
            outcome="success",
            details={"idempotency_key": idempotency_key},
        )
        context = AgentActionExecutionContext(
            organization_id=organization_id,
            executed_by_user_id=started_execution.executed_by_user_id,
            nucleus_actor_id=started_execution.nucleus_actor_id,
            execution_started_at=started_execution.started_at,
        )
        try:
            if getattr(handler, "requires_execution_context", False):
                handler_result = await handler.execute(
                    proposal=proposal, context=context
                )
            else:
                handler_result = await handler.execute(proposal=proposal)
        except StaleActionResourceError as exception:
            await self._action_repository.mark_stale_execution(proposal.id)
            raise AgentActionStaleError() from exception
        except Exception as exception:
            await self._action_repository.complete_execution(
                proposal_id=proposal.id,
                outcome="reconciliation_required",
                result=None,
                error_code="action_outcome_unknown",
                reconciliation_status="required",
            )
            await self._append_execution_audit_safely(
                user=user,
                proposal=proposal,
                event_type="agent_action_reconciliation_required",
                outcome="failure",
                details={"error_code": "action_outcome_unknown"},
            )
            raise AgentActionReconciliationRequiredError() from exception
        execution_result = await self._action_repository.complete_execution(
            proposal_id=proposal.id,
            outcome="succeeded",
            result=handler_result.model_dump(mode="json"),
            error_code=None,
            provider_operation_id=handler_result.external_operation_id,
            reconciliation_status="not_required",
        )
        await self._append_execution_audit_safely(
            user=user,
            proposal=proposal,
            event_type="agent_action_succeeded",
            outcome="success",
            details=execution_result.result,
        )
        return await self._require_execution(proposal.id)

    async def reconcile(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionExecutionResult:
        proposal = await self.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        execution = await self._require_execution(proposal.id)
        if execution.outcome not in {"executing", "reconciliation_required"}:
            return execution
        await self._action_repository.increment_reconciliation_attempt(proposal.id)
        handler = self._require_handler(proposal.action_name)
        context = AgentActionExecutionContext(
            organization_id=organization_id,
            executed_by_user_id=execution.executed_by_user_id,
            nucleus_actor_id=execution.nucleus_actor_id,
            execution_started_at=execution.started_at,
        )
        if getattr(handler, "requires_execution_context", False):
            handler_result = await handler.reconcile(
                proposal=proposal,
                execution=execution,
                context=context,
            )
        else:
            handler_result = await handler.reconcile(
                proposal=proposal,
                execution=execution,
            )
        if handler_result is None:
            return await self._action_repository.keep_reconciliation_required(
                proposal_id=proposal.id,
                audit_pending=execution.audit_pending,
            )
        reconciled = await self._action_repository.complete_execution(
            proposal_id=proposal.id,
            outcome="succeeded",
            result=handler_result.model_dump(mode="json"),
            error_code=None,
            provider_operation_id=handler_result.external_operation_id,
            reconciliation_status="resolved",
            audit_pending=execution.audit_pending,
        )
        await self._append_execution_audit_safely(
            user=user,
            proposal=proposal,
            event_type="agent_action_succeeded",
            outcome="success",
            details=reconciled.result,
        )
        return await self._require_execution(proposal.id)

    async def _expire_if_needed(
        self,
        proposal: AgentActionProposal,
    ) -> AgentActionProposal:
        if (
            proposal.status in {"pending_approval", "approved"}
            and _as_aware(proposal.expires_at) <= _utcnow()
        ):
            await self._action_repository.transition_status(
                proposal_id=proposal.id,
                current_statuses=(proposal.status,),
                target_status="expired",
            )
            return await self._require_proposal(
                organization_id=proposal.organization_id,
                proposal_id=proposal.id,
            )
        return proposal

    def _validate_fingerprint(self, proposal: AgentActionProposal) -> None:
        expected_fingerprint = build_action_fingerprint(
            organization_id=proposal.organization_id,
            requested_by_user_id=proposal.requested_by_user_id,
            action_name=proposal.action_name,
            arguments=proposal.arguments,
            changes=proposal.changes,
            observed_resource_version=proposal.observed_resource_version,
            resource_preconditions=proposal.resource_preconditions,
            fingerprint_version=proposal.fingerprint_version,
            approval_policy=proposal.approval_policy,
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            expires_at=proposal.expires_at,
        )
        if expected_fingerprint != proposal.action_fingerprint:
            raise AgentActionStateConflictError("Action proposal fingerprint is invalid.")

    async def _authorize(
        self,
        *,
        user: User,
        organization_id: str,
        required_permission: str,
        allow_suspended_organization: bool = False,
    ) -> None:
        organization_profile = await self._organization_gateway.get_profile(
            organization_id
        )
        if organization_profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()
        if (
            organization_profile.status != OrganizationStatus.ACTIVE
            and not allow_suspended_organization
        ):
            raise OrganizationSuspendedError()
        await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )

    def _require_handler(self, action_name: str) -> AgentActionHandler:
        handler = self._action_handlers.get(action_name)
        if handler is None:
            raise AgentActionInvalidError("No action handler is registered.")
        return handler

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

    async def _require_execution(
        self,
        proposal_id: str,
    ) -> AgentActionExecutionResult:
        execution = await self._action_repository.get_execution(proposal_id)
        if execution is None:
            raise AgentActionStateConflictError("Action execution was not found.")
        return execution

    async def _append_execution_audit_safely(
        self,
        *,
        user: User,
        proposal: AgentActionProposal,
        event_type: str,
        outcome: str,
        details: dict | None,
    ) -> None:
        try:
            await self._append_audit(
                user=user,
                proposal=proposal,
                event_type=event_type,
                outcome=outcome,
                details=details,
            )
        except Exception:
            await self._action_repository.mark_audit_pending(proposal.id, True)

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
