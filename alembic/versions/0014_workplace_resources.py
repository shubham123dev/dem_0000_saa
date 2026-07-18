"""add governed workplace resource runtime

Revision ID: 0014_workplace_resources
Revises: 0013_nucleus_admin
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_workplace_resources"
down_revision: Union[str, None] = "0013_nucleus_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workplace_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("setting_key", sa.String(length=120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "namespace",
            "setting_key",
            name="uq_workplace_setting_org_namespace_key",
        ),
    )
    op.create_index(
        "ix_workplace_setting_org_active",
        "workplace_settings",
        ["organization_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_workplace_settings_organization_id",
        "workplace_settings",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "workplace_resource_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=250), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workplace_snapshot_resource",
        "workplace_resource_snapshots",
        ["organization_id", "resource_type", "resource_id"],
        unique=False,
    )
    op.create_table(
        "workplace_mutation_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("operation_type", sa.String(length=80), nullable=False),
        sa.Column("resource_count", sa.Integer(), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["agent_action_proposals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_workplace_plan_proposal"),
    )
    op.create_table(
        "workplace_mutation_step_receipts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mutation_plan_id", sa.String(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=250), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mutation_plan_id"],
            ["workplace_mutation_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mutation_plan_id",
            "step_index",
            name="uq_workplace_plan_step",
        ),
    )
    op.create_table(
        "workplace_resource_tombstones",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=250), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("deleted_by_user_id", sa.String(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["deleted_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "resource_type",
            "resource_id",
            name="uq_workplace_resource_tombstone",
        ),
    )


def downgrade() -> None:
    op.drop_table("workplace_resource_tombstones")
    op.drop_table("workplace_mutation_step_receipts")
    op.drop_table("workplace_mutation_plans")
    op.drop_index(
        "ix_workplace_snapshot_resource",
        table_name="workplace_resource_snapshots",
    )
    op.drop_table("workplace_resource_snapshots")
    op.drop_index(
        "ix_workplace_settings_organization_id",
        table_name="workplace_settings",
    )
    op.drop_index(
        "ix_workplace_setting_org_active",
        table_name="workplace_settings",
    )
    op.drop_table("workplace_settings")
