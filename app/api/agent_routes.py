from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder

from app.agent.errors import AgentToolCallInvalidError
from app.agent.tool_registry import InvalidAgentToolCallError
from app.api.agent_dependencies import ReadOnlyAgentResponseServiceDep
from app.api.dependencies import UserDep
from app.schemas.agent import (
    AgentActionProposalSummary,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentToolResultOut,
)

router = APIRouter(prefix="/workplace/organizations", tags=["workplace-agent"])


@router.post(
    "/{organization_id}/agent/query",
    response_model=AgentQueryResponse,
)
async def query_read_only_agent(
    organization_id: str,
    request_body: AgentQueryRequest,
    request: Request,
    user: UserDep,
    response_service: ReadOnlyAgentResponseServiceDep,
) -> AgentQueryResponse:
    try:
        completion = await response_service.execute(
            user=user,
            organization_id=organization_id,
            user_request=request_body.query,
            request_id=getattr(request.state, "request_id", None),
        )
    except InvalidAgentToolCallError as exception:
        raise AgentToolCallInvalidError() from exception

    proposal_summary = None
    if completion.action_proposal is not None:
        proposal_summary = AgentActionProposalSummary(
            id=completion.action_proposal.id,
            action_name=completion.action_proposal.action_name,
            risk_level=completion.action_proposal.risk_level,
            status=completion.action_proposal.status,
            changes=completion.action_proposal.changes,
            expires_at=completion.action_proposal.expires_at,
        )

    return AgentQueryResponse(
        mode=completion.mode,
        organization_id=organization_id,
        answer=completion.answer,
        evidence_ids=completion.evidence_ids,
        answer_source=completion.answer_source,
        action_proposal=proposal_summary,
        missing_fields=completion.missing_fields,
        results=tuple(
            AgentToolResultOut(
                tool_name=tool_result.tool_name,
                data=jsonable_encoder(tool_result.data),
            )
            for tool_result in completion.results
        ),
    )
