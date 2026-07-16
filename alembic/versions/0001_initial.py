"""initial sandbox schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-16

Creates the five mock sandbox tables:
organizations, employees, employee_organization_roles,
role_permissions, audit_events.
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
        "employees",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "employee_organization_roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint(
            "employee_id", "organization_id", "role", name="uq_employee_org_role"
        ),
    )
    op.create_index(
        "ix_employee_organization_roles_employee_id",
        "employee_organization_roles",
        ["employee_id"],
    )
    op.create_index(
        "ix_employee_organization_roles_organization_id",
        "employee_organization_roles",
        ["organization_id"],
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
        sa.Column("actor_employee_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_audit_events_actor_employee_id", "audit_events", ["actor_employee_id"]
    )
    op.create_index(
        "ix_audit_events_organization_id", "audit_events", ["organization_id"]
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_employee_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index(
        "ix_employee_organization_roles_organization_id",
        table_name="employee_organization_roles",
    )
    op.drop_index(
        "ix_employee_organization_roles_employee_id",
        table_name="employee_organization_roles",
    )
    op.drop_table("employee_organization_roles")

    op.drop_table("employees")
    op.drop_table("organizations")
