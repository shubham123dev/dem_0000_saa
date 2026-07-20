"""Persistence for the governed workplace-resource runtime."""

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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkplaceSettingORM(Base):
    __tablename__ = "workplace_settings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "namespace",
            "setting_key",
            name="uq_workplace_setting_org_namespace_key",
        ),
        Index(
            "ix_workplace_setting_org_active",
            "organization_id",
            "is_active",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict | list | str | int | float | bool | None] = (
        mapped_column(JSON, nullable=True)
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class WorkplaceResourceSnapshotORM(Base):
    __tablename__ = "workplace_resource_snapshots"
    __table_args__ = (
        Index(
            "ix_workplace_snapshot_resource",
            "organization_id",
            "resource_type",
            "resource_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class WorkplaceMutationPlanORM(Base):
    __tablename__ = "workplace_mutation_plans"
    __table_args__ = (
        UniqueConstraint("proposal_id", name="uq_workplace_plan_proposal"),
        Index(
            "ix_workplace_plan_org_workflow_status",
            "organization_id",
            "workflow_name",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_action_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False
    )
    operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    workflow_version: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    target_set_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    risk_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compensation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class WorkplaceMutationStepReceiptORM(Base):
    __tablename__ = "workplace_mutation_step_receipts"
    __table_args__ = (
        UniqueConstraint(
            "mutation_plan_id",
            "step_index",
            name="uq_workplace_plan_step",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mutation_plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workplace_mutation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    depends_on_step_index: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    verification_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compensation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WorkplaceResourceTombstoneORM(Base):
    __tablename__ = "workplace_resource_tombstones"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "resource_type",
            "resource_id",
            name="uq_workplace_resource_tombstone",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    deleted_by_user_id: Mapped[str] = mapped_column(String, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    restored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
