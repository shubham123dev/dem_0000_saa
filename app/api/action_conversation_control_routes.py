from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.action_control_dependencies import ActionControlServiceDep
from app.api.dependencies import SessionDep, UserDep
from app.db.action_models import AgentActionProposalORM
from app.db.agent_run_models import AgentRunORM
from app.schemas.action_control import ActionProposalControlOut
from app.agent.action_errors import AgentActionProposalNotFoundError

router = APIRouter(prefix="/workplace/organizations", tags=["workplace-action-control"])


@router.get(
    "/{organization_id}/agent/control/conversations/{conversation_id}/action",
    response_model=ActionProposalControlOut,
)
async def get_conversation_action_control(
    organization_id: str,
    conversation_id: str,
    user: UserDep,
    service: ActionControlServiceDep,
    session: SessionDep,
) -> ActionProposalControlOut:
    result = await session.execute(
        select(AgentActionProposalORM.id)
        .join(AgentRunORM, AgentRunORM.id == AgentActionProposalORM.source_agent_run_id)
        .where(
            AgentActionProposalORM.organization_id == organization_id,
            AgentRunORM.organization_id == organization_id,
            AgentRunORM.conversation_id == conversation_id,
        )
        .order_by(AgentActionProposalORM.created_at.desc(), AgentActionProposalORM.id.desc())
        .limit(1)
    )
    proposal_id = result.scalar_one_or_none()
    if proposal_id is None:
        raise AgentActionProposalNotFoundError()
    return await service.detail(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )
