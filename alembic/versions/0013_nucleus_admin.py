"""add Nucleus administrative control sidecars

Revision ID: 0013_nucleus_admin
Revises: 0012_resource_preconditions
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_nucleus_admin"
down_revision: Union[str, None] = "0012_resource_preconditions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nucleus_actor_mappings",
        sa.Column("workplace_user_id", sa.String(), nullable=False),
        sa.Column("nucleus_actor_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workplace_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("workplace_user_id"),
        sa.UniqueConstraint(
            "nucleus_actor_id", name="uq_nucleus_actor_mapping_actor"
        ),
    )
    op.create_table(
        "nucleus_access_tombstones",
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("access_id", sa.Integer(), nullable=False),
        sa.Column("organization_account_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("revoked_by", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_account_id"],
            ["OrganizationAccount.OrganizationAccountId"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("resource_type", "access_id"),
        sa.UniqueConstraint(
            "resource_type", "access_id", name="uq_nucleus_access_tombstone"
        ),
    )
    op.create_index(
        "ix_nucleus_access_tombstone_org",
        "nucleus_access_tombstones",
        ["organization_account_id", "resource_type"],
        unique=False,
    )
    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.add_column(
            sa.Column("executed_by_user_id", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("nucleus_actor_id", sa.Integer(), nullable=True)
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE agent_action_executions "
            "SET executed_by_user_id = ("
            "SELECT requested_by_user_id FROM agent_action_proposals "
            "WHERE agent_action_proposals.id = "
            "agent_action_executions.proposal_id) "
            "WHERE executed_by_user_id IS NULL"
        )
    )
    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.alter_column(
            "executed_by_user_id",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_agent_action_execution_executor",
            "users",
            ["executed_by_user_id"],
            ["id"],
        )




def downgrade() -> None:
    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.drop_constraint(
            "fk_agent_action_execution_executor", type_="foreignkey"
        )
        batch_op.drop_column("nucleus_actor_id")
        batch_op.drop_column("executed_by_user_id")
    op.drop_index(
        "ix_nucleus_access_tombstone_org",
        table_name="nucleus_access_tombstones",
    )
    op.drop_table("nucleus_access_tombstones")
    op.drop_table("nucleus_actor_mappings")
