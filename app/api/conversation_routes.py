"""Conversation store API: listing, history, search, rename, archive."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import SessionDep, UserDep
from app.core.errors import AgentConversationNotFoundError
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_search_repository import ConversationSearchRepository
from app.schemas.conversation import (
    ConversationHistoryResponse,
    ConversationListItem,
    ConversationListResponse,
    ConversationMessageOut,
    ConversationSearchResponse,
    ConversationSearchResult,
    ConversationUpdateRequest,
)

router = APIRouter(
    prefix="/workplace/organizations",
    tags=["workplace-conversations"],
)


def get_conversation_repository(session: SessionDep) -> ConversationRepository:
    return ConversationRepository(session)


def get_search_repository(session: SessionDep) -> ConversationSearchRepository:
    return ConversationSearchRepository(session)


ConversationRepoDep = Annotated[
    ConversationRepository, Depends(get_conversation_repository)
]

SearchRepoDep = Annotated[
    ConversationSearchRepository, Depends(get_search_repository)
]


@router.get(
    "/{organization_id}/agent/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations(
    organization_id: str,
    user: UserDep,
    repo: ConversationRepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> ConversationListResponse:
    conversations, total = await repo.list_conversations(
        organization_id=organization_id,
        user_id=user.id,
        limit=limit,
        offset=offset,
        search=search,
    )
    items = [
        ConversationListItem(
            id=c.id,
            title=c.title,
            summary=c.summary,
            status=c.status,
            message_count=c.message_count,
            pinned=c.pinned,
            last_message_at=c.last_message_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]
    return ConversationListResponse(
        conversations=items,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{organization_id}/agent/conversations/search",
    response_model=ConversationSearchResponse,
)
async def search_conversations(
    organization_id: str,
    user: UserDep,
    search_repo: SearchRepoDep,
    q: Annotated[str, Query(min_length=1, max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ConversationSearchResponse:
    """Full-text search across conversation messages using FTS5."""
    hits = await search_repo.search(
        organization_id=organization_id,
        user_id=user.id,
        query=q,
        limit=limit,
    )
    results = [
        ConversationSearchResult(
            message_id=h.message_id,
            conversation_id=h.conversation_id,
            conversation_title=h.conversation_title,
            role=h.role,
            snippet=h.snippet,
            created_at=h.created_at,
        )
        for h in hits
    ]
    return ConversationSearchResponse(results=results, total=len(results))


@router.get(
    "/{organization_id}/agent/conversations/{conversation_id}/messages",
    response_model=ConversationHistoryResponse,
)
async def get_conversation_history(
    organization_id: str,
    conversation_id: str,
    user: UserDep,
    repo: ConversationRepoDep,
    leaf_id: Annotated[str | None, Query(max_length=64)] = None,
) -> ConversationHistoryResponse:
    conversation = await repo.get_conversation(
        conversation_id=conversation_id,
        organization_id=organization_id,
        user_id=user.id,
    )
    if conversation is None:
        raise AgentConversationNotFoundError()

    messages, has_branches = await repo.get_history(
        conversation_id=conversation_id,
        leaf_id=leaf_id,
    )
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        title=conversation.title,
        messages=[
            ConversationMessageOut(
                id=m.id,
                conversation_id=m.conversation_id,
                run_id=m.run_id,
                parent_id=m.parent_id,
                sequence=m.sequence,
                role=m.role,  # type: ignore[arg-type]
                content=m.content,
                mode=m.mode,
                answer_source=m.answer_source,
                safe_metadata=m.safe_metadata,
                created_at=m.created_at,
            )
            for m in messages
        ],
        has_branches=has_branches,
    )


@router.patch(
    "/{organization_id}/agent/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
)
async def update_conversation(
    organization_id: str,
    conversation_id: str,
    body: ConversationUpdateRequest,
    user: UserDep,
    repo: ConversationRepoDep,
) -> dict:
    conversation = await repo.get_conversation(
        conversation_id=conversation_id,
        organization_id=organization_id,
        user_id=user.id,
    )
    if conversation is None:
        raise AgentConversationNotFoundError()

    if body.title is not None:
        await repo.rename_conversation(
            conversation_id=conversation_id, title=body.title
        )
    if body.pinned is not None:
        await repo.pin_conversation(
            conversation_id=conversation_id, pinned=body.pinned
        )
    return {"ok": True}


@router.delete(
    "/{organization_id}/agent/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    organization_id: str,
    conversation_id: str,
    user: UserDep,
    repo: ConversationRepoDep,
) -> None:
    conversation = await repo.get_conversation(
        conversation_id=conversation_id,
        organization_id=organization_id,
        user_id=user.id,
    )
    if conversation is None:
        raise AgentConversationNotFoundError()
    await repo.archive_conversation(conversation_id=conversation_id)
