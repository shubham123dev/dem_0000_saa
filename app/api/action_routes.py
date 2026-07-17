from __future__ import annotations

from fastapi import APIRouter, Query

from app.agent.action_contracts import AgentActionProposalInput
from app.api.action_dependencies import (
    AgentActionReconciliationServiceDep,
    AgentActionServiceDep,
)
from app.api.dependencies import UserDep
from app.schemas.agent_actions import (
    AgentActionApprovalResponse,
    AgentActionDecisionRequest,
    AgentActionExecutionRequest,
    AgentActionExecutionResponse,
    AgentActionProposalListResponse,
    AgentActionProposalRequest,
    AgentActionProposalResponse,
    AgentActionStatusFilter,
)

router = APIRouter(
    prefix="/workplace/organizations",
    tags=["workplace-agent-actions"],
)


@router.post(
    "/{organization_id}/agent/actions/propose",
    response_model=AgentActionProposalResponse,
)
async def propose_agent_action(
    organization_id: str,
    request_body: AgentActionProposalRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionProposalResponse:
    proposal = await action_service.propose(
        user=user,
        organization_id=organization_id,
        proposal_input=AgentActionProposalInput(
            action_name=request_body.action_name,
            arguments=request_body.resolved_arguments(),
        ),
    )
    return AgentActionProposalResponse(proposal=proposal)


@router.get(
    "/{organization_id}/agent/actions",
    response_model=AgentActionProposalListResponse,
)
async def list_agent_action_proposals(
    organization_id: str,
    user: UserDep,
    action_service: AgentActionServiceDep,
    status: AgentActionStatusFilter | None = Query(default=None),
) -> AgentActionProposalListResponse:
    proposals = await action_service.list_proposals(
        user=user,
        organization_id=organization_id,
        status=status,
    )
    return AgentActionProposalListResponse(proposals=proposals)


@router.get(
    "/{organization_id}/agent/actions/{proposal_id}",
    response_model=AgentActionProposalResponse,
)
async def get_agent_action_proposal(
    organization_id: str,
    proposal_id: str,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionProposalResponse:
    proposal = await action_service.get_proposal(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )
    return AgentActionProposalResponse(proposal=proposal)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/approve",
    response_model=AgentActionApprovalResponse,
)
async def approve_agent_action(
    organization_id: str,
    proposal_id: str,
    request_body: AgentActionDecisionRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionApprovalResponse:
    approval = await action_service.decide(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        decision="approved",
        reason=request_body.reason,
    )
    return AgentActionApprovalResponse(approval=approval)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/reject",
    response_model=AgentActionApprovalResponse,
)
async def reject_agent_action(
    organization_id: str,
    proposal_id: str,
    request_body: AgentActionDecisionRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionApprovalResponse:
    approval = await action_service.decide(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        decision="rejected",
        reason=request_body.reason,
    )
    return AgentActionApprovalResponse(approval=approval)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/cancel",
    response_model=AgentActionProposalResponse,
)
async def cancel_agent_action(
    organization_id: str,
    proposal_id: str,
    request_body: AgentActionDecisionRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionProposalResponse:
    proposal = await action_service.cancel(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        reason=request_body.reason,
    )
    return AgentActionProposalResponse(proposal=proposal)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/rollback-proposal",
    response_model=AgentActionProposalResponse,
)
async def create_agent_action_rollback_proposal(
    organization_id: str,
    proposal_id: str,
    request_body: AgentActionDecisionRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionProposalResponse:
    proposal = await action_service.create_rollback_proposal(
        user=user,
        organization_id=organization_id,
        source_proposal_id=proposal_id,
        reason=request_body.reason,
    )
    return AgentActionProposalResponse(proposal=proposal)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/execute",
    response_model=AgentActionExecutionResponse,
)
async def execute_agent_action(
    organization_id: str,
    proposal_id: str,
    request_body: AgentActionExecutionRequest,
    user: UserDep,
    action_service: AgentActionServiceDep,
) -> AgentActionExecutionResponse:
    execution = await action_service.execute(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        idempotency_key=request_body.idempotency_key,
    )
    return AgentActionExecutionResponse(execution=execution)


@router.post(
    "/{organization_id}/agent/actions/{proposal_id}/reconcile",
    response_model=AgentActionExecutionResponse,
)
async def reconcile_agent_action(
    organization_id: str,
    proposal_id: str,
    user: UserDep,
    reconciliation_service: AgentActionReconciliationServiceDep,
) -> AgentActionExecutionResponse:
    execution = await reconciliation_service.reconcile(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )
    return AgentActionExecutionResponse(execution=execution)
