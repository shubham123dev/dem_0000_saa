from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_harden_agent_action_lifecycle"
down_revision: Union[str, None] = "0004_add_agent_action_approvals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.add_column(
            sa.Column("observed_resource_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("approval_policy_json", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("provider_operation_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("reconciliation_status", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("audit_pending", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.drop_column("audit_pending")
        batch_op.drop_column("reconciliation_status")
        batch_op.drop_column("provider_operation_id")
        batch_op.drop_column("last_attempt_at")
        batch_op.drop_column("attempt_count")

    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.drop_column("stale_at")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("approval_policy_json")
        batch_op.drop_column("observed_resource_version")
