"""Internal persistence supporting safe Nucleus administration.

These tables are Workplace Agent sidecars. They do not alter the eight
supplied Nucleus tables and are not part of the future Nucleus wire contract.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NucleusActorMappingORM(Base):
    __tablename__ = "nucleus_actor_mappings"
    __table_args__ = (
        UniqueConstraint("nucleus_actor_id", name="uq_nucleus_actor_mapping_actor"),
    )

    workplace_user_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    nucleus_actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class NucleusAccessTombstoneORM(Base):
    """Logical revocation for exact tables that have no IsActive column."""

    __tablename__ = "nucleus_access_tombstones"
    __table_args__ = (
        UniqueConstraint(
            "resource_type", "access_id", name="uq_nucleus_access_tombstone"
        ),
        Index(
            "ix_nucleus_access_tombstone_org",
            "organization_account_id",
            "resource_type",
        ),
    )

    resource_type: Mapped[str] = mapped_column(String(80), primary_key=True)
    access_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "OrganizationAccount.OrganizationAccountId",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    revoked_by: Mapped[int] = mapped_column(Integer, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
