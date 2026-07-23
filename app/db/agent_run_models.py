"""Durable conversation, run, and event persistence for the workplace agent."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentConversationORM(Base):
    __tablename__ = "agent_conversations"
    __table_args__ = (
        Index(
            "ix_agent_conversation_owner_updated",
            "organization_id",
            "created_by_user_id",
            "updated_at",
        ),
        Index(
            "ix_agent_conversation_listing",
            "organization_id",
            "created_by_user_id",
            "status",
            "last_message_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_message_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentRunORM(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "requested_by_user_id",
            "client_request_id",
            name="uq_agent_run_request_idempotency",
        ),
        Index(
            "ix_agent_run_claim",
            "status",
            "lease_expires_at",
            "created_at",
        ),
        Index(
            "ix_agent_run_conversation_created",
            "conversation_id",
            "created_at",
        ),
        UniqueConstraint(
            "conversation_id",
            "active_slot",
            name="uq_agent_run_active_conversation",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    user_message_id: Mapped[str] = mapped_column(String, nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active_slot: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=1
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    current_stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default="request_acceptance"
    )
    final_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    final_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_event_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentMessageORM(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence",
            name="uq_agent_message_conversation_sequence",
        ),
        Index(
            "ix_agent_message_conversation_sequence",
            "conversation_id",
            "sequence",
        ),
        Index(
            "ix_agent_message_parent",
            "conversation_id",
            "parent_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    answer_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    safe_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AgentRunEventORM(Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "sequence",
            name="uq_agent_run_event_sequence",
        ),
        Index("ix_agent_run_event_replay", "run_id", "sequence"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_message: Mapped[str] = mapped_column(String(240), nullable=False)
    safe_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AgentContextBlockORM(Base):
    """Context memory blocks for Cloudflare-inspired conversation memory.

    Block types:
    - soul: Agent identity and instructions (readonly)
    - memory: Important facts learned during conversation (writable)
    - knowledge: Searchable knowledge base (searchable)
    - skill: Loadable skill definitions (loadable)
    """

    __tablename__ = "agent_context_blocks"
    __table_args__ = (
        UniqueConstraint("conversation_id", "key", name="uq_context_block_key"),
        Index(
            "ix_agent_context_blocks_conversation_type",
            "conversation_id",
            "block_type",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="readonly"
    )
    loaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class AgentCompactionOverlayORM(Base):
    """Compaction overlays for long conversation history.

    Stores summarized versions of older message ranges, preserving originals.
    Applied transparently at read time to reduce context window usage.
    """

    __tablename__ = "agent_compaction_overlays"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "start_sequence",
            "end_sequence",
            name="uq_compaction_overlay_range",
        ),
        Index(
            "ix_agent_compaction_overlays_conversation_seq",
            "conversation_id",
            "start_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    end_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
