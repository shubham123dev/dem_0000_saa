from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_operational_hardening"
down_revision: Union[str, None] = "0008_add_multi_approval_and_rollbacks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "audit_replay_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("audit_last_attempt_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("audit_last_error", sa.String(length=200), nullable=True)
        )
        batch_op.create_index(
            "ix_agent_action_execution_audit_replay",
            ["audit_pending", "audit_replay_attempts", "last_attempt_at"],
            unique=False,
        )

    op.create_index(
        "ix_agent_action_proposal_org_created",
        "agent_action_proposals",
        ["organization_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_action_proposal_requester_created",
        "agent_action_proposals",
        ["organization_id", "requested_by_user_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_action_proposal_status_created",
        "agent_action_proposals",
        ["organization_id", "status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_action_proposal_status_created",
        table_name="agent_action_proposals",
    )
    op.drop_index(
        "ix_agent_action_proposal_requester_created",
        table_name="agent_action_proposals",
    )
    op.drop_index(
        "ix_agent_action_proposal_org_created",
        table_name="agent_action_proposals",
    )

    with op.batch_alter_table("agent_action_executions") as batch_op:
        batch_op.drop_index("ix_agent_action_execution_audit_replay")
        batch_op.drop_column("audit_last_error")
        batch_op.drop_column("audit_last_attempt_at")
        batch_op.drop_column("audit_replay_attempts")
