"""SQLAlchemy ORM models for the mock sandbox database."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    environment: Mapped[str] = mapped_column(
        String, nullable=False, default="sandbox"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class OrganizationOverviewORM(Base):
    __tablename__ = "organization_overviews"
    __table_args__ = (
        CheckConstraint(
            "workspace_status IN ('healthy', 'degraded', 'unavailable', 'unknown')",
            name="ck_org_overview_workspace_status",
        ),
        CheckConstraint(
            "workspace_health_percent >= 0 AND workspace_health_percent <= 100",
            name="ck_org_overview_health_percent",
        ),
        CheckConstraint(
            "licensed_modules >= 0",
            name="ck_org_overview_licensed_modules_nonnegative",
        ),
        CheckConstraint(
            "available_areas >= 0",
            name="ck_org_overview_available_areas_nonnegative",
        ),
        CheckConstraint(
            "organization_logins >= 0",
            name="ck_org_overview_logins_nonnegative",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_org_overview_version_positive",
        ),
    )

    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    organization_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="organization"
    )
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    workspace_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown"
    )
    workspace_health_percent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    licensed_modules: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    available_areas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    organization_logins: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    memberships: Mapped[list["OrganizationMembershipORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OrganizationMembershipORM(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_membership_user"),
        Index(
            "ix_membership_lifecycle_lookup",
            "organization_id",
            "user_id",
            "membership_status",
            "version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    membership_status: Mapped[str] = mapped_column(
        String, nullable=False, default="active"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    user: Mapped["UserORM"] = relationship(back_populates="memberships")


class OrganizationSeatPoolORM(Base):
    __tablename__ = "organization_seat_pools"
    __table_args__ = (
        UniqueConstraint("organization_id", "seat_type", name="uq_seat_pool_org_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    seat_type: Mapped[str] = mapped_column(
        String, nullable=False, default="standard"
    )
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class SeatAssignmentORM(Base):
    __tablename__ = "seat_assignments"
    __table_args__ = (
        Index(
            "uq_active_seat_per_user_pool",
            "organization_id",
            "seat_pool_id",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "ix_seat_lifecycle_lookup",
            "organization_id",
            "user_id",
            "status",
            "version",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    seat_pool_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organization_seat_pools.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class ReportORM(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    external_report_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    market_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class OrganizationReportAccessORM(Base):
    __tablename__ = "organization_report_access"
    __table_args__ = (
        UniqueConstraint("organization_id", "report_id", name="uq_org_report_access"),
        Index(
            "ix_report_access_lifecycle_lookup",
            "organization_id",
            "report_id",
            "status",
            "version",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    report_id: Mapped[str] = mapped_column(
        String, ForeignKey("reports.id"), nullable=False, index=True
    )
    access_level: Mapped[str] = mapped_column(
        String, nullable=False, default="view"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    granted_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class RolePermissionORM(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role", "permission", name="uq_role_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String, nullable=False)


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
