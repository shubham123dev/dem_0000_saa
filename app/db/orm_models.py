"""SQLAlchemy ORM models for the mock sandbox database.

Five persistent tables:

1. organizations
2. employees
3. employee_organization_roles
4. role_permissions
5. audit_events

``audit_events`` is append-only from application behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
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
    # Stored as the enum value string; only "sandbox" is used in Step 0.
    environment: Mapped[str] = mapped_column(String, nullable=False, default="sandbox")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class EmployeeORM(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    # Synthetic test email only.
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    roles: Mapped[list["EmployeeOrganizationRoleORM"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class EmployeeOrganizationRoleORM(Base):
    __tablename__ = "employee_organization_roles"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "organization_id",
            "role",
            name="uq_employee_org_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        String, ForeignKey("employees.id"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)

    employee: Mapped["EmployeeORM"] = relationship(back_populates="roles")


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
    actor_employee_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
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
