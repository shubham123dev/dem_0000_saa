"""Pydantic schemas for the conversation store API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationListItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str | None
    summary: str | None
    status: str
    message_count: int
    pinned: bool
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversations: list[ConversationListItem]
    total: int
    has_more: bool


class ConversationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    pinned: bool | None = None


class ConversationMessageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    conversation_id: str
    run_id: str | None
    parent_id: str | None
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    mode: str | None
    answer_source: str | None
    safe_metadata: dict[str, Any] | None
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    title: str | None
    messages: list[ConversationMessageOut]
    has_branches: bool


class ConversationSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: str
    conversation_id: str
    conversation_title: str | None
    role: str
    snippet: str
    created_at: datetime


class ConversationSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[ConversationSearchResult]
    total: int
