from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.run_contracts import AgentMessageRecord, AgentRunEventRecord, AgentRunRecord
from app.api.agent_run_dependencies import AgentRunServiceDep
from app.api.dependencies import SessionDep, UserDep, verify_organization_membership
from app.core.config import get_settings
from app.core.errors import REQUEST_ID_HEADER
from app.repositories.agent_run_repository import AgentRunRepository
from app.schemas.agent_run import (
    AgentConversationResponse,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunEventOut,
    AgentRunMessageOut,
    AgentRunOut,
)

router = APIRouter(
    prefix="/workplace/organizations",
    tags=["workplace-agent-runs"],
)


def _message_out(message: AgentMessageRecord) -> AgentRunMessageOut:
    return AgentRunMessageOut(
        id=message.id,
        sequence=message.sequence,
        role=message.role,
        content=message.content,
        mode=message.mode,
        answer_source=message.answer_source,
        safe_metadata=message.safe_metadata,
        created_at=message.created_at,
    )


def _run_out(run: AgentRunRecord) -> AgentRunOut:
    return AgentRunOut(
        id=run.id,
        conversation_id=run.conversation_id,
        status=run.status,
        current_stage=run.current_stage,
        final_mode=run.final_mode,
        error_code=run.error_code,
        cancellation_requested_at=run.cancellation_requested_at,
        attempt_count=run.attempt_count,
        terminal=run.terminal,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _event_out(event: AgentRunEventRecord) -> AgentRunEventOut:
    return AgentRunEventOut(
        run_id=event.run_id,
        sequence=event.sequence,
        type=event.event_type,
        stage=event.stage,
        message=event.safe_message,
        payload=event.safe_payload,
        terminal=event.terminal,
        occurred_at=event.created_at,
    )


def _sse_frame(event: AgentRunEventRecord) -> str:
    payload = _event_out(event).model_dump(mode="json")
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return f"id: {event.sequence}\nevent: {event.event_type}\ndata: {encoded}\n\n"


@router.post(
    "/{organization_id}/agent/runs",
    response_model=AgentRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_agent_run(
    organization_id: str,
    body: AgentRunCreateRequest,
    request: Request,
    user: UserDep,
    service: AgentRunServiceDep,
) -> AgentRunCreateResponse:
    created = await service.create(
        user=user,
        organization_id=organization_id,
        query=body.query,
        client_request_id=body.client_request_id,
        conversation_id=body.conversation_id,
        request_id=getattr(request.state, "request_id", None),
    )
    coordinator = getattr(request.app.state, "agent_run_coordinator", None)
    if coordinator is not None:
        coordinator.notify()
    events_url = (
        f"/workplace/organizations/{organization_id}/agent/runs/"
        f"{created.run.id}/events"
    )
    return AgentRunCreateResponse(
        conversation_id=created.conversation.id,
        run=_run_out(created.run),
        user_message=_message_out(created.user_message),
        events_url=events_url,
        created=created.created,
    )


@router.get(
    "/{organization_id}/agent/conversations/{conversation_id}",
    response_model=AgentConversationResponse,
)
async def get_agent_conversation(
    organization_id: str,
    conversation_id: str,
    user: UserDep,
    service: AgentRunServiceDep,
) -> AgentConversationResponse:
    conversation, messages, active_run = await service.conversation(
        user=user,
        organization_id=organization_id,
        conversation_id=conversation_id,
    )
    return AgentConversationResponse(
        conversation_id=conversation.id,
        messages=tuple(_message_out(message) for message in messages),
        active_run=_run_out(active_run) if active_run is not None else None,
    )


@router.get(
    "/{organization_id}/agent/runs/{run_id}",
    response_model=AgentRunOut,
)
async def get_agent_run(
    organization_id: str,
    run_id: str,
    user: UserDep,
    service: AgentRunServiceDep,
) -> AgentRunOut:
    return _run_out(
        await service.run(
            user=user, organization_id=organization_id, run_id=run_id
        )
    )


@router.post(
    "/{organization_id}/agent/runs/{run_id}/cancel",
    response_model=AgentRunOut,
)
async def cancel_agent_run(
    organization_id: str,
    run_id: str,
    request: Request,
    user: UserDep,
    service: AgentRunServiceDep,
) -> AgentRunOut:
    run = await service.cancel(
        user=user, organization_id=organization_id, run_id=run_id
    )
    coordinator = getattr(request.app.state, "agent_run_coordinator", None)
    if coordinator is not None:
        coordinator.notify()
    return _run_out(run)


@router.get("/{organization_id}/agent/runs/{run_id}/events")
async def stream_agent_run_events(
    organization_id: str,
    run_id: str,
    request: Request,
    user: UserDep,
    service: AgentRunServiceDep,
    session: SessionDep,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[
        str | None, Header(alias="Last-Event-ID")
    ] = None,
) -> StreamingResponse:
    await service.run(user=user, organization_id=organization_id, run_id=run_id)
    header_cursor = 0
    if last_event_id:
        try:
            header_cursor = max(0, int(last_event_id))
        except ValueError:
            header_cursor = 0
    cursor = max(after_sequence, header_cursor)
    settings = get_settings()
    if session.bind is None:
        raise RuntimeError("Agent run event streaming requires a database bind")
    stream_sessions = async_sessionmaker(
        bind=session.bind, expire_on_commit=False, class_=AsyncSession
    )
    # A streaming response can remain open for minutes. Release the request-scoped
    # authorization session before following events with short-lived sessions.
    await session.close()

    async def event_stream():
        nonlocal cursor
        heartbeat_elapsed = 0.0
        while True:
            if await request.is_disconnected():
                return
            async with stream_sessions() as event_session:
                stream_repository = AgentRunRepository(event_session)
                events = await stream_repository.list_events(
                    run_id=run_id, after_sequence=cursor
                )
                current_run = await stream_repository.get_run_internal(run_id)
            if events:
                heartbeat_elapsed = 0.0
                for event in events:
                    cursor = event.sequence
                    yield _sse_frame(event)
                    if event.terminal:
                        return
                continue
            if current_run is None or current_run.terminal:
                return
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
