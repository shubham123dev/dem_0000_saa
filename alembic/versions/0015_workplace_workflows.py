"""add governed workplace workflows

Revision ID: 0015_workplace_workflows
Revises: 0014_workplace_resources
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_workplace_workflows"
down_revision: Union[str, None] = "0014_workplace_resources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workplace_mutation_plans",
        sa.Column("workflow_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "workplace_mutation_plans",
        sa.Column("workflow_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "workplace_mutation_plans",
        sa.Column("target_set_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "workplace_mutation_plans",
        sa.Column("risk_snapshot_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "workplace_mutation_plans",
        sa.Column("compensation_json", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_workplace_plan_org_workflow_status",
        "workplace_mutation_plans",
        ["organization_id", "workflow_name", "status"],
        unique=False,
    )
    op.add_column(
        "workplace_mutation_step_receipts",
        sa.Column("depends_on_step_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "workplace_mutation_step_receipts",
        sa.Column("verification_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "workplace_mutation_step_receipts",
        sa.Column("compensation_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workplace_mutation_step_receipts", "compensation_json")
    op.drop_column("workplace_mutation_step_receipts", "verification_json")
    op.drop_column("workplace_mutation_step_receipts", "depends_on_step_index")
    op.drop_index(
        "ix_workplace_plan_org_workflow_status",
        table_name="workplace_mutation_plans",
    )
    op.drop_column("workplace_mutation_plans", "compensation_json")
    op.drop_column("workplace_mutation_plans", "risk_snapshot_json")
    op.drop_column("workplace_mutation_plans", "target_set_hash")
    op.drop_column("workplace_mutation_plans", "workflow_version")
    op.drop_column("workplace_mutation_plans", "workflow_name")
