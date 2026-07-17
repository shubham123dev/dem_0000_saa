from __future__ import annotations

from fastapi import APIRouter

from app.agent.action_contracts import AgentActionProposalInput
from app.api.action_dependencies import AgentActionServiceDep
from app.api.dependencies import UserDep
from app.schemas.agent_actions import (
    AgentActionApprovalResponse,
    AgentActionDecisionRequest,
    AgentActionExecutionRequest,
    AgentActionExecutionResponse,
    AgentActionProposalRequest,
    AgentActionProposalResponse,
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
            arguments={"contact_email": request_body.contact_email},
        ),
    )
    return AgentActionProposalResponse(proposal=proposal)


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
