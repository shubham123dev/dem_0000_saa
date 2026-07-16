"""initial sandbox schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-16

Creates the nine mock sandbox tables:
organizations, users, organization_memberships, organization_seat_pools,
seat_assignments, reports, organization_report_access, role_permissions,
audit_events.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("environment", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("membership_status", sa.String(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_org_membership_user"
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_memberships_user_id",
        "organization_memberships",
        ["user_id"],
    )

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
        sa.UniqueConstraint(
            "organization_id", "seat_type", name="uq_seat_pool_org_type"
        ),
    )
    op.create_index(
        "ix_organization_seat_pools_organization_id",
        "organization_seat_pools",
        ["organization_id"],
    )

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
    op.create_index(
        "ix_seat_assignments_organization_id", "seat_assignments", ["organization_id"]
    )
    op.create_index(
        "ix_seat_assignments_seat_pool_id", "seat_assignments", ["seat_pool_id"]
    )
    op.create_index("ix_seat_assignments_user_id", "seat_assignments", ["user_id"])
    # A user may hold at most one *active* assignment per seat pool.
    op.create_index(
        "uq_active_seat_per_user_pool",
        "seat_assignments",
        ["organization_id", "seat_pool_id", "user_id"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
    )

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
        sa.UniqueConstraint(
            "organization_id", "report_id", name="uq_org_report_access"
        ),
    )
    op.create_index(
        "ix_organization_report_access_organization_id",
        "organization_report_access",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_report_access_report_id",
        "organization_report_access",
        ["report_id"],
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("permission", sa.String(), nullable=False),
        sa.UniqueConstraint("role", "permission", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role", "role_permissions", ["role"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index(
        "ix_audit_events_organization_id", "audit_events", ["organization_id"]
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index(
        "ix_organization_report_access_report_id",
        table_name="organization_report_access",
    )
    op.drop_index(
        "ix_organization_report_access_organization_id",
        table_name="organization_report_access",
    )
    op.drop_table("organization_report_access")

    op.drop_index("ix_reports_external_report_id", table_name="reports")
    op.drop_table("reports")

    op.drop_index("uq_active_seat_per_user_pool", table_name="seat_assignments")
    op.drop_index("ix_seat_assignments_user_id", table_name="seat_assignments")
    op.drop_index("ix_seat_assignments_seat_pool_id", table_name="seat_assignments")
    op.drop_index("ix_seat_assignments_organization_id", table_name="seat_assignments")
    op.drop_table("seat_assignments")

    op.drop_index(
        "ix_organization_seat_pools_organization_id",
        table_name="organization_seat_pools",
    )
    op.drop_table("organization_seat_pools")

    op.drop_index(
        "ix_organization_memberships_user_id", table_name="organization_memberships"
    )
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")

    op.drop_table("users")
    op.drop_table("organizations")
