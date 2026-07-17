from __future__ import annotations

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.agent.errors import AgentToolCallInvalidError
from app.agent.tool_registry import InvalidAgentToolCallError
from app.api.agent_dependencies import ReadOnlyAgentOrchestratorDep
from app.api.dependencies import UserDep
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse, AgentToolResultOut

router = APIRouter(prefix="/workplace/organizations", tags=["workplace-agent"])


@router.post(
    "/{organization_id}/agent/query",
    response_model=AgentQueryResponse,
)
async def query_read_only_agent(
    organization_id: str,
    request_body: AgentQueryRequest,
    user: UserDep,
    orchestrator: ReadOnlyAgentOrchestratorDep,
) -> AgentQueryResponse:
    try:
        execution_result = await orchestrator.execute(
            user=user,
            organization_id=organization_id,
            user_request=request_body.query,
        )
    except InvalidAgentToolCallError as exception:
        raise AgentToolCallInvalidError() from exception

    return AgentQueryResponse(
        organization_id=organization_id,
        results=tuple(
            AgentToolResultOut(
                tool_name=tool_result.tool_name,
                data=jsonable_encoder(tool_result.data),
            )
            for tool_result in execution_result.results
        ),
    )
