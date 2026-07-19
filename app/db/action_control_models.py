"""Persistence for safe governed-action execution activity."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentActionExecutionEventORM(Base):
    __tablename__ = "agent_action_execution_events"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "sequence",
            name="uq_action_execution_event_sequence",
        ),
        UniqueConstraint(
            "proposal_id",
            "dedupe_key",
            name="uq_action_execution_event_dedupe",
        ),
        Index(
            "ix_action_execution_event_replay",
            "proposal_id",
            "sequence",
        ),
        Index(
            "ix_action_execution_event_terminal",
            "proposal_id",
            "terminal",
            "sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_action_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    safe_message: Mapped[str] = mapped_column(String(240), nullable=False)
    safe_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
