from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentActionProposalORM(Base):
    __tablename__ = "agent_action_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    action_name: Mapped[str] = mapped_column(String, nullable=False)
    arguments_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    changes_json: Mapped[list] = mapped_column(JSON, nullable=False)
    action_fingerprint: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    observed_resource_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_policy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class AgentActionApprovalORM(Base):
    __tablename__ = "agent_action_approvals"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "decided_by_user_id",
            name="uq_agent_action_approval_proposal_approver",
        ),
        Index(
            "ix_agent_action_approval_progress",
            "proposal_id",
            "decision",
            "consumed_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String, ForeignKey("agent_action_proposals.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    decided_by_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    decision_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentActionExecutionORM(Base):
    __tablename__ = "agent_action_executions"
    __table_args__ = (
        UniqueConstraint("proposal_id", name="uq_agent_action_execution_proposal"),
        UniqueConstraint("idempotency_key", name="uq_agent_action_execution_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String, ForeignKey("agent_action_proposals.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_operation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reconciliation_status: Mapped[str | None] = mapped_column(String, nullable=True)
    audit_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentActionRollbackORM(Base):
    __tablename__ = "agent_action_rollbacks"
    __table_args__ = (
        UniqueConstraint(
            "rollback_proposal_id",
            name="uq_agent_action_rollback_proposal",
        ),
        Index(
            "ix_agent_action_rollback_source",
            "source_proposal_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_proposal_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_action_proposals.id"),
        nullable=False,
    )
    rollback_proposal_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_action_proposals.id"),
        nullable=False,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
