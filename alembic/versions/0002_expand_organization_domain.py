"""compatibly expand the original Step 0 sandbox schema

Revision ID: 0002_expand_organization_domain
Revises: 0001_initial
Create Date: 2026-07-16
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_expand_organization_domain"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def get_column_names(table_name: str) -> set[str]:
    return {
        column_definition["name"]
        for column_definition in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def get_index_names(table_name: str) -> set[str]:
    return {
        index_definition["name"]
        for index_definition in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def get_unique_constraint_names(table_name: str) -> set[str]:
    return {
        constraint_definition["name"]
        for constraint_definition in sa.inspect(op.get_bind()).get_unique_constraints(table_name)
        if constraint_definition["name"] is not None
    }


def collapse_duplicate_legacy_memberships() -> None:
    connection = op.get_bind()
    duplicate_membership_groups = connection.execute(
        sa.text(
            "SELECT organization_id, user_id, MIN(id) AS retained_id "
            "FROM organization_memberships "
            "GROUP BY organization_id, user_id "
            "HAVING COUNT(*) > 1"
        )
    ).mappings().all()

    for duplicate_membership_group in duplicate_membership_groups:
        connection.execute(
            sa.text(
                "DELETE FROM organization_memberships "
                "WHERE organization_id = :organization_id "
                "AND user_id = :user_id "
                "AND id != :retained_id"
            ),
            duplicate_membership_group,
        )


def upgrade() -> None:
    existing_table_names = get_table_names()

    if "employees" in existing_table_names and "users" not in existing_table_names:
        op.rename_table("employees", "users")
        existing_table_names.remove("employees")
        existing_table_names.add("users")

    if (
        "employee_organization_roles" in existing_table_names
        and "organization_memberships" not in existing_table_names
    ):
        op.rename_table("employee_organization_roles", "organization_memberships")
        existing_table_names.remove("employee_organization_roles")
        existing_table_names.add("organization_memberships")

    if "organization_memberships" in existing_table_names:
        existing_membership_column_names = get_column_names("organization_memberships")
        with op.batch_alter_table("organization_memberships") as membership_batch:
            if (
                "employee_id" in existing_membership_column_names
                and "user_id" not in existing_membership_column_names
            ):
                membership_batch.alter_column("employee_id", new_column_name="user_id")
            if "membership_status" not in existing_membership_column_names:
                membership_batch.add_column(
                    sa.Column(
                        "membership_status",
                        sa.String(),
                        nullable=False,
                        server_default="active",
                    )
                )
            if "joined_at" not in existing_membership_column_names:
                membership_batch.add_column(
                    sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True)
                )
            if "created_at" not in existing_membership_column_names:
                membership_batch.add_column(
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
                )
            if "updated_at" not in existing_membership_column_names:
                membership_batch.add_column(
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
                )

        current_timestamp = datetime.now(timezone.utc)
        op.execute(
            sa.text(
                "UPDATE organization_memberships "
                "SET joined_at = COALESCE(joined_at, :current_timestamp), "
                "created_at = COALESCE(created_at, :current_timestamp), "
                "updated_at = COALESCE(updated_at, :current_timestamp)"
            ).bindparams(current_timestamp=current_timestamp)
        )
        collapse_duplicate_legacy_memberships()

        existing_membership_index_names = get_index_names("organization_memberships")
        existing_membership_constraint_names = get_unique_constraint_names(
            "organization_memberships"
        )
        if "ix_organization_memberships_organization_id" not in existing_membership_index_names:
            op.create_index(
                "ix_organization_memberships_organization_id",
                "organization_memberships",
                ["organization_id"],
            )
        if "ix_organization_memberships_user_id" not in existing_membership_index_names:
            op.create_index(
                "ix_organization_memberships_user_id",
                "organization_memberships",
                ["user_id"],
            )
        if (
            "uq_org_membership_user" not in existing_membership_index_names
            and "uq_org_membership_user" not in existing_membership_constraint_names
        ):
            op.create_index(
                "uq_org_membership_user",
                "organization_memberships",
                ["organization_id", "user_id"],
                unique=True,
            )

    if "audit_events" in existing_table_names:
        existing_audit_column_names = get_column_names("audit_events")
        if (
            "actor_employee_id" in existing_audit_column_names
            and "actor_user_id" not in existing_audit_column_names
        ):
            with op.batch_alter_table("audit_events") as audit_event_batch:
                audit_event_batch.alter_column(
                    "actor_employee_id", new_column_name="actor_user_id"
                )
        existing_audit_index_names = get_index_names("audit_events")
        if "ix_audit_events_actor_user_id" not in existing_audit_index_names:
            op.create_index(
                "ix_audit_events_actor_user_id",
                "audit_events",
                ["actor_user_id"],
            )

    existing_table_names = get_table_names()
    if "organization_seat_pools" not in existing_table_names:
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

    existing_table_names = get_table_names()
    if "seat_assignments" not in existing_table_names:
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
            "ix_seat_assignments_organization_id",
            "seat_assignments",
            ["organization_id"],
        )
        op.create_index(
            "ix_seat_assignments_seat_pool_id",
            "seat_assignments",
            ["seat_pool_id"],
        )
        op.create_index(
            "ix_seat_assignments_user_id", "seat_assignments", ["user_id"]
        )
        op.create_index(
            "uq_active_seat_per_user_pool",
            "seat_assignments",
            ["organization_id", "seat_pool_id", "user_id"],
            unique=True,
            sqlite_where=sa.text("status = 'active'"),
        )

    existing_table_names = get_table_names()
    if "reports" not in existing_table_names:
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
        op.create_index(
            "ix_reports_external_report_id", "reports", ["external_report_id"]
        )

    existing_table_names = get_table_names()
    if "organization_report_access" not in existing_table_names:
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


def downgrade() -> None:
    existing_table_names = get_table_names()
    for removable_table_name in (
        "organization_report_access",
        "reports",
        "seat_assignments",
        "organization_seat_pools",
    ):
        if removable_table_name in existing_table_names:
            op.drop_table(removable_table_name)
