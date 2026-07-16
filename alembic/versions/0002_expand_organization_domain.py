"""compatibly expand the original Step 0 sandbox schema

Revision ID: 0002_expand_organization_domain
Revises: 0001_initial
Create Date: 2026-07-16

The repository briefly shipped an earlier ``0001_initial`` containing employees
and employee_organization_roles. The current 0001 creates the expanded schema
for fresh databases. This compatibility migration upgrades a database already
stamped with the earlier revision and is a no-op for a fresh expanded database.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_expand_organization_domain"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()

    if "employees" in tables and "users" not in tables:
        op.rename_table("employees", "users")
        tables.remove("employees")
        tables.add("users")

    if "employee_organization_roles" in tables and "organization_memberships" not in tables:
        op.rename_table("employee_organization_roles", "organization_memberships")
        tables.remove("employee_organization_roles")
        tables.add("organization_memberships")

    if "organization_memberships" in tables:
        cols = _columns("organization_memberships")
        with op.batch_alter_table("organization_memberships") as batch:
            if "employee_id" in cols and "user_id" not in cols:
                batch.alter_column("employee_id", new_column_name="user_id")
            if "membership_status" not in cols:
                batch.add_column(sa.Column("membership_status", sa.String(), nullable=False, server_default="active"))
            if "joined_at" not in cols:
                batch.add_column(sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True))
            if "created_at" not in cols:
                batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
            if "updated_at" not in cols:
                batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

        indexes = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("organization_memberships")}
        if "ix_organization_memberships_organization_id" not in indexes:
            op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
        if "ix_organization_memberships_user_id" not in indexes:
            op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
        if "uq_org_membership_user" not in indexes:
            op.create_index("uq_org_membership_user", "organization_memberships", ["organization_id", "user_id"], unique=True)

    if "audit_events" in tables:
        cols = _columns("audit_events")
        if "actor_employee_id" in cols and "actor_user_id" not in cols:
            with op.batch_alter_table("audit_events") as batch:
                batch.alter_column("actor_employee_id", new_column_name="actor_user_id")
        indexes = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("audit_events")}
        if "ix_audit_events_actor_user_id" not in indexes:
            op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])

    tables = _tables()
    if "organization_seat_pools" not in tables:
        op.create_table(
            "organization_seat_pools",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("seat_type", sa.String(), nullable=False),
            sa.Column("total_seats", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.UniqueConstraint("organization_id", "seat_type", name="uq_seat_pool_org_type"),
        )
        op.create_index("ix_organization_seat_pools_organization_id", "organization_seat_pools", ["organization_id"])

    tables = _tables()
    if "seat_assignments" not in tables:
        op.create_table(
            "seat_assignments",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("seat_pool_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("assigned_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["seat_pool_id"], ["organization_seat_pools.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_seat_assignments_organization_id", "seat_assignments", ["organization_id"])
        op.create_index("ix_seat_assignments_seat_pool_id", "seat_assignments", ["seat_pool_id"])
        op.create_index("ix_seat_assignments_user_id", "seat_assignments", ["user_id"])
        op.create_index(
            "uq_active_seat_per_user_pool",
            "seat_assignments",
            ["organization_id", "seat_pool_id", "user_id"],
            unique=True,
            sqlite_where=sa.text("status = 'active'"),
        )

    tables = _tables()
    if "reports" not in tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("external_report_id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("market_name", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_reports_external_report_id", "reports", ["external_report_id"])

    tables = _tables()
    if "organization_report_access" not in tables:
        op.create_table(
            "organization_report_access",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("report_id", sa.String(), nullable=False),
            sa.Column("access_level", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("granted_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
            sa.UniqueConstraint("organization_id", "report_id", name="uq_org_report_access"),
        )
        op.create_index("ix_organization_report_access_organization_id", "organization_report_access", ["organization_id"])
        op.create_index("ix_organization_report_access_report_id", "organization_report_access", ["report_id"])


def downgrade() -> None:
    # This repository is an isolated synthetic sandbox. Downgrade removes only the
    # four expansion tables; renamed identity tables remain on the modern names to
    # avoid destructive loss of seeded memberships and audit history.
    tables = _tables()
    for table in ("organization_report_access", "reports", "seat_assignments", "organization_seat_pools"):
        if table in tables:
            op.drop_table(table)
