from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.action_errors import AgentActionInvalidError
from app.agent.action_control_contracts import AgentActionExecutionEventRecord
from app.api.action_control_dependencies import (
    ActionControlRepositoryDep,
    ActionControlServiceDep,
)
from app.api.dependencies import SessionDep, UserDep
from app.core.config import get_settings
from app.core.errors import REQUEST_ID_HEADER
from app.repositories.action_control_repository import ActionControlRepository
from app.schemas.action_control import (
    ActionCapabilityCatalogueOut,
    ActionDecisionBody,
    ActionExecuteBody,
    ActionExecutionEventOut,
    ActionProposalControlListOut,
    ActionProposalControlOut,
)

router = APIRouter(
    prefix="/workplace/organizations",
    tags=["workplace-action-control"],
)


def _event_out(event: AgentActionExecutionEventRecord) -> ActionExecutionEventOut:
    return ActionExecutionEventOut(
        proposal_id=event.proposal_id,
        sequence=event.sequence,
        type=event.event_type,
        stage=event.stage,
        message=event.safe_message,
        payload=event.safe_payload,
        terminal=event.terminal,
        occurred_at=event.created_at,
    )


def _frame(event: AgentActionExecutionEventRecord) -> str:
    data = json.dumps(
        _event_out(event).model_dump(mode="json"),
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {data}\n\n"
    )


@router.get(
    "/{organization_id}/agent/capabilities",
    response_model=ActionCapabilityCatalogueOut,
)
async def get_action_capabilities(
    organization_id: str,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionCapabilityCatalogueOut:
    return await service.capabilities(user=user, organization_id=organization_id)


@router.get(
    "/{organization_id}/agent/control/actions",
    response_model=ActionProposalControlListOut,
)
async def list_action_control_proposals(
    organization_id: str,
    user: UserDep,
    service: ActionControlServiceDep,
    status: str | None = Query(default=None, max_length=80),
    action_name: str | None = Query(default=None, max_length=160),
    requested_by: str | None = Query(default=None, max_length=200),
    limit: int | None = Query(default=None, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=200),
) -> ActionProposalControlListOut:
    return await service.list_proposals(
        user=user,
        organization_id=organization_id,
        status=status,
        action_name=action_name,
        requested_by_user_id=requested_by,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/{organization_id}/agent/control/actions/{proposal_id}",
    response_model=ActionProposalControlOut,
)
async def get_action_control_proposal(
    organization_id: str,
    proposal_id: str,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    return await service.detail(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/approve",
    response_model=ActionProposalControlOut,
)
async def approve_action_control_proposal(
    organization_id: str,
    proposal_id: str,
    body: ActionDecisionBody,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    try:
        return await service.decide(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            decision="approved",
            reason=body.reason,
            confirmation=body.confirmation,
        )
    except ValueError as exception:
        raise AgentActionInvalidError(str(exception)) from exception


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/reject",
    response_model=ActionProposalControlOut,
)
async def reject_action_control_proposal(
    organization_id: str,
    proposal_id: str,
    body: ActionDecisionBody,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    try:
        return await service.decide(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            decision="rejected",
            reason=body.reason,
            confirmation=body.confirmation,
        )
    except ValueError as exception:
        raise AgentActionInvalidError(str(exception)) from exception


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/cancel",
    response_model=ActionProposalControlOut,
)
async def cancel_action_control_proposal(
    organization_id: str,
    proposal_id: str,
    body: ActionDecisionBody,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    return await service.cancel(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        reason=body.reason,
    )


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/execute",
    response_model=ActionProposalControlOut,
)
async def execute_action_control_proposal(
    organization_id: str,
    proposal_id: str,
    body: ActionExecuteBody,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    try:
        return await service.execute(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            idempotency_key=body.idempotency_key,
            confirmation=body.confirmation,
        )
    except ValueError as exception:
        raise AgentActionInvalidError(str(exception)) from exception


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/reconcile",
    response_model=ActionProposalControlOut,
)
async def reconcile_action_control_execution(
    organization_id: str,
    proposal_id: str,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    return await service.reconcile(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )


@router.post(
    "/{organization_id}/agent/control/actions/{proposal_id}/rollback-proposal",
    response_model=ActionProposalControlOut,
)
async def create_action_control_rollback(
    organization_id: str,
    proposal_id: str,
    body: ActionDecisionBody,
    user: UserDep,
    service: ActionControlServiceDep,
) -> ActionProposalControlOut:
    return await service.create_rollback(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
        reason=body.reason,
    )


@router.get(
    "/{organization_id}/agent/control/actions/{proposal_id}/execution/events"
)
async def stream_action_execution_events(
    organization_id: str,
    proposal_id: str,
    request: Request,
    user: UserDep,
    service: ActionControlServiceDep,
    repository: ActionControlRepositoryDep,
    session: SessionDep,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID"),
    ] = None,
) -> StreamingResponse:
    await service.detail(
        user=user,
        organization_id=organization_id,
        proposal_id=proposal_id,
    )
    header_cursor = 0
    if last_event_id:
        try:
            header_cursor = max(0, int(last_event_id))
        except ValueError:
            header_cursor = 0
    cursor = max(after_sequence, header_cursor)
    settings = get_settings()
    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    await session.close()

    async def event_stream():
        nonlocal cursor
        heartbeat_elapsed = 0.0
        while True:
            if await request.is_disconnected():
                return
            async with session_factory() as stream_session:
                events = await ActionControlRepository(stream_session).list_events(
                    proposal_id=proposal_id,
                    after_sequence=cursor,
                )
            if events:
                heartbeat_elapsed = 0.0
                for index, event in enumerate(events):
                    cursor = event.sequence
                    yield _frame(event)
                    if event.terminal and index == len(events) - 1:
                        return
                continue
            await asyncio.sleep(settings.agent_run_stream_poll_seconds)
            heartbeat_elapsed += settings.agent_run_stream_poll_seconds
            if heartbeat_elapsed >= settings.agent_run_heartbeat_seconds:
                heartbeat_elapsed = 0.0
                yield ": heartbeat\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            REQUEST_ID_HEADER: getattr(request.state, "request_id", ""),
        },
    )
