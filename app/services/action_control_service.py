from __future__ import annotations

from typing import Any

from app.agent.action_contracts import AgentActionProposal
from app.agent.action_errors import AgentActionStateConflictError
from app.agent.action_control_contracts import humanize_identifier, safe_value_summary
from app.agent.action_registry import AgentActionRegistry
from app.core.errors import AppError
from app.domain.enums import Permission
from app.domain.models import User
from app.permissions.permission_service import PermissionService
from app.repositories.action_control_repository import ActionControlRepository
from app.schemas.action_control import (
    ActionAllowedOperationsOut,
    ActionApprovalProgressOut,
    ActionCapabilityCatalogueOut,
    ActionCapabilityOut,
    ActionControlChangeOut,
    ActionExecutionReceiptOut,
    ActionProposalControlListOut,
    ActionProposalControlOut,
)
from app.services.action_execution_activity import DatabaseActionExecutionActivitySink
from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService


class ActionControlService:
    def __init__(
        self,
        *,
        action_service: ReleaseReadyAgentActionService,
        action_registry: AgentActionRegistry,
        action_handlers: dict[str, object],
        permission_service: PermissionService,
        repository: ActionControlRepository,
    ) -> None:
        self._action_service = action_service
        self._action_registry = action_registry
        self._action_handlers = action_handlers
        self._permission_service = permission_service
        self._repository = repository

    async def capabilities(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> ActionCapabilityCatalogueOut:
        capabilities: list[ActionCapabilityOut] = []
        for name in sorted(self._action_handlers):
            definition = self._action_registry.get_definition(name)
            if not definition.model_selectable:
                continue
            available = await self._can(
                user=user,
                organization_id=organization_id,
                permission=definition.required_permission,
            )
            capabilities.append(
                ActionCapabilityOut(
                    name=definition.name,
                    label=humanize_identifier(definition.name),
                    description=definition.description,
                    resource_label=humanize_identifier(definition.resource_type),
                    risk_level=definition.risk_level,
                    requires_approval=definition.requires_approval,
                    supports_dry_run=definition.supports_dry_run,
                    available=available,
                )
            )
        return ActionCapabilityCatalogueOut(
            action_capabilities=tuple(capabilities)
        )

    async def list_proposals(
        self,
        *,
        user: User,
        organization_id: str,
        status: str | None,
        action_name: str | None,
        requested_by_user_id: str | None,
        limit: int | None,
        cursor: str | None,
    ) -> ActionProposalControlListOut:
        proposals, next_cursor = await self._action_service.list_proposals_page(
            user=user,
            organization_id=organization_id,
            status=status,
            action_name=action_name,
            requested_by_user_id=requested_by_user_id,
            limit=limit,
            cursor=cursor,
        )
        projected = []
        for proposal in proposals:
            try:
                authorized = await self._action_service.get_proposal(
                    user=user,
                    organization_id=organization_id,
                    proposal_id=proposal.id,
                )
            except AppError:
                continue
            projected.append(
                await self.project(
                    user=user,
                    organization_id=organization_id,
                    proposal=authorized,
                )
            )
        return ActionProposalControlListOut(
            proposals=tuple(projected),
            next_cursor=next_cursor,
        )

    async def detail(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> ActionProposalControlOut:
        proposal = await self._action_service.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        return await self.project(
            user=user,
            organization_id=organization_id,
            proposal=proposal,
        )

    async def decide(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        decision: str,
        reason: str | None,
        confirmation: str | None,
    ) -> ActionProposalControlOut:
        proposal = await self._action_service.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        if (
            decision == "approved"
            and proposal.risk_level == "high"
            and confirmation != "APPROVE"
        ):
            raise ValueError("High-risk approval requires typed confirmation.")
        if decision == "rejected" and proposal.risk_level in {"medium", "high"} and not reason:
            raise ValueError("A rejection reason is required for this risk level.")
        await self._action_service.decide(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            decision=decision,
            reason=reason,
        )
        return await self.detail(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )

    async def cancel(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        reason: str | None,
    ) -> ActionProposalControlOut:
        await self._action_service.cancel(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            reason=reason,
        )
        return await self.detail(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        idempotency_key: str,
        confirmation: str | None,
    ) -> ActionProposalControlOut:
        proposal = await self._action_service.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        if proposal.risk_level == "high" and confirmation != "EXECUTE":
            raise ValueError("High-risk execution requires typed confirmation.")
        await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_EXECUTE.value,
        )
        if proposal.status != "approved":
            raise AgentActionStateConflictError("Explicit approval is required.")
        sink = DatabaseActionExecutionActivitySink(self._repository, proposal_id)
        existing_execution = await self._repository.execution_row(proposal_id)
        if (
            existing_execution is not None
            and existing_execution.idempotency_key != idempotency_key
        ):
            await self._action_service.execute(
                user=user,
                organization_id=organization_id,
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
            )
        prefix = f"execute-{idempotency_key}"
        await sink.emit(
            event_type="execution.accepted",
            stage="acceptance",
            message="Execution request accepted",
            dedupe_key=f"{prefix}-accepted",
        )
        await sink.emit(
            event_type="approval.verified",
            stage="governance",
            message="Approval and executor permissions verified",
            dedupe_key=f"{prefix}-approval-verified",
        )
        await sink.emit(
            event_type="resource.revalidating",
            stage="validation",
            message="Revalidating the current resource state",
            dedupe_key=f"{prefix}-revalidating",
        )
        await sink.emit(
            event_type="execution.started",
            stage="execution",
            message="Applying the approved change",
            dedupe_key=f"{prefix}-started",
        )
        try:
            execution = await self._action_service.execute(
                user=user,
                organization_id=organization_id,
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
            )
        except Exception as exception:
            name = type(exception).__name__
            if "Stale" in name:
                await sink.emit(
                    event_type="execution.stale",
                    stage="completion",
                    message="Execution stopped because the reviewed resource changed",
                    payload={"outcome": "stale"},
                    terminal=True,
                    dedupe_key=f"{prefix}-stale",
                )
            elif "Reconciliation" in name:
                await sink.emit(
                    event_type="execution.reconciliation_required",
                    stage="completion",
                    message="The execution outcome requires reconciliation",
                    payload={"outcome": "reconciliation_required"},
                    terminal=True,
                    dedupe_key=f"{prefix}-reconciliation-required",
                )
            else:
                await sink.emit(
                    event_type="execution.failed",
                    stage="completion",
                    message="The approved change could not be completed",
                    payload={"outcome": "failed"},
                    terminal=True,
                    dedupe_key=f"{prefix}-failed",
                )
            raise
        await sink.emit(
            event_type="resource.verifying",
            stage="verification",
            message="Verifying the resulting workspace state",
            dedupe_key=f"{prefix}-verifying",
        )
        terminal_type = (
            "execution.succeeded"
            if execution.outcome == "succeeded"
            else "execution.reconciliation_required"
            if execution.outcome == "reconciliation_required"
            else "execution.failed"
        )
        terminal_message = {
            "succeeded": "Execution completed and verified",
            "reconciliation_required": "The execution outcome requires reconciliation",
            "failed": "The approved change could not be completed",
        }.get(execution.outcome, "Execution state updated")
        await sink.emit(
            event_type=terminal_type,
            stage="completion",
            message=terminal_message,
            payload={"outcome": execution.outcome},
            terminal=execution.outcome != "executing",
            dedupe_key=f"{prefix}-{execution.outcome}",
        )
        return await self.detail(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )

    async def reconcile(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> ActionProposalControlOut:
        await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_RECONCILE.value,
        )
        sink = DatabaseActionExecutionActivitySink(self._repository, proposal_id)
        current = await self._repository.execution_row(proposal_id)
        attempt = (current.attempt_count if current is not None else 0) + 1
        await sink.emit(
            event_type="execution.reconciliation_requested",
            stage="reconciliation",
            message="Reconciliation requested",
            dedupe_key=f"reconciliation-{attempt}-requested",
        )
        await sink.emit(
            event_type="resource.verifying",
            stage="verification",
            message="Checking the current workspace state",
            dedupe_key=f"reconciliation-{attempt}-verifying",
        )
        try:
            execution = await self._action_service.reconcile(
                user=user,
                organization_id=organization_id,
                proposal_id=proposal_id,
            )
        except Exception:
            await sink.emit(
                event_type="execution.reconciliation_required",
                stage="completion",
                message="Reconciliation could not resolve the execution outcome",
                payload={"outcome": "reconciliation_required"},
                terminal=True,
                dedupe_key=f"reconciliation-{attempt}-error",
            )
            raise
        if execution.outcome == "succeeded":
            await sink.emit(
                event_type="execution.succeeded",
                stage="completion",
                message="Reconciliation confirmed the completed change",
                payload={"outcome": "succeeded"},
                terminal=True,
                dedupe_key=f"reconciliation-{attempt}-succeeded",
            )
        else:
            await sink.emit(
                event_type="execution.reconciliation_required",
                stage="completion",
                message="The execution outcome is still unresolved",
                payload={"outcome": "reconciliation_required"},
                terminal=True,
                dedupe_key=f"reconciliation-{attempt}-unresolved",
            )
        return await self.detail(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )

    async def create_rollback(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        reason: str | None,
    ) -> ActionProposalControlOut:
        rollback = await self._action_service.create_rollback_proposal(
            user=user,
            organization_id=organization_id,
            source_proposal_id=proposal_id,
            reason=reason,
        )
        return await self.project(
            user=user,
            organization_id=organization_id,
            proposal=rollback,
        )

    async def project(
        self,
        *,
        user: User,
        organization_id: str,
        proposal: AgentActionProposal,
    ) -> ActionProposalControlOut:
        approval_count = await self._repository.count_approvals(proposal.id)
        source_run_id, conversation_id = await self._repository.proposal_source(
            proposal.id
        )
        del source_run_id
        requester = await self._repository.user_label(proposal.requested_by_user_id)
        can_approve = await self._can(
            user=user,
            organization_id=organization_id,
            permission=Permission.AGENT_ACTIONS_APPROVE.value,
        )
        can_execute = await self._can(
            user=user,
            organization_id=organization_id,
            permission=Permission.AGENT_ACTIONS_EXECUTE.value,
        )
        can_reconcile = await self._can(
            user=user,
            organization_id=organization_id,
            permission=Permission.AGENT_ACTIONS_RECONCILE.value,
        )
        self_approval_blocked = (
            not proposal.approval_policy.self_approval_allowed
            and proposal.requested_by_user_id == user.id
        )
        execution_row = await self._repository.execution_row(proposal.id)
        execution = None
        if execution_row is not None:
            result = execution_row.result_json or {}
            execution = ActionExecutionReceiptOut(
                outcome=execution_row.outcome,
                resource_label=humanize_identifier(proposal.resource_type),
                before=self._safe_mapping(result.get("before")),
                after=self._safe_mapping(result.get("after")),
                error_code=execution_row.error_code,
                started_at=execution_row.started_at,
                completed_at=execution_row.completed_at,
                executed_by=await self._repository.user_label(
                    execution_row.executed_by_user_id
                ),
                rollback_available=(
                    execution_row.outcome == "succeeded" and can_execute
                ),
            )
        required = proposal.approval_policy.minimum_approvals
        return ActionProposalControlOut(
            id=proposal.id,
            action_name=proposal.action_name,
            action_label=humanize_identifier(proposal.action_name),
            resource_label=humanize_identifier(proposal.resource_type),
            status=proposal.status,
            risk_level=proposal.risk_level,
            requested_by=requester,
            created_at=proposal.created_at,
            expires_at=proposal.expires_at,
            approval_progress=ActionApprovalProgressOut(
                approved=approval_count,
                required=required,
                complete=approval_count >= required,
            ),
            self_approval_allowed=proposal.approval_policy.self_approval_allowed,
            required_approver_permission=(
                proposal.approval_policy.required_approver_permission
            ),
            changes=tuple(
                ActionControlChangeOut(
                    field=humanize_identifier(change.field),
                    before=safe_value_summary(change.before),
                    after=safe_value_summary(change.after),
                )
                for change in proposal.changes[:20]
            ),
            allowed_operations=ActionAllowedOperationsOut(
                approve=(
                    proposal.status == "pending_approval"
                    and can_approve
                    and not self_approval_blocked
                ),
                reject=(proposal.status == "pending_approval" and can_approve),
                cancel=(
                    proposal.status in {"pending_approval", "approved"}
                    and can_execute
                ),
                execute=(proposal.status == "approved" and can_execute),
                reconcile=(
                    proposal.status == "reconciliation_required"
                    and can_reconcile
                ),
                create_rollback=(
                    proposal.status == "succeeded"
                    and execution is not None
                    and execution.rollback_available
                ),
            ),
            source_conversation_id=conversation_id,
            execution=execution,
        )

    async def _can(
        self,
        *,
        user: User,
        organization_id: str,
        permission: str,
    ) -> bool:
        try:
            await self._permission_service.authorize(
                user=user,
                organization_id=organization_id,
                required_permission=permission,
            )
            return True
        except AppError:
            return False

    @staticmethod
    def _safe_mapping(value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        result: dict[str, Any] = {}
        for key, item in list(value.items())[:20]:
            label = humanize_identifier(str(key))
            if isinstance(item, (str, int, float, bool)) or item is None:
                result[label] = item
            elif isinstance(item, (list, tuple)):
                result[label] = f"{len(item)} items"
            else:
                result[label] = "Structured value"
        return result
