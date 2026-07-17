from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_add_multi_approval_and_rollbacks"
down_revision: Union[str, None] = "0007_complete_inverse_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_action_approvals") as batch_op:
        batch_op.drop_constraint(
            "uq_agent_action_approval_proposal",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_agent_action_approval_proposal_approver",
            ["proposal_id", "decided_by_user_id"],
        )
        batch_op.create_index(
            "ix_agent_action_approval_progress",
            ["proposal_id", "decision", "consumed_at"],
            unique=False,
        )

    op.create_table(
        "agent_action_rollbacks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_proposal_id", sa.String(), nullable=False),
        sa.Column("rollback_proposal_id", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_proposal_id"],
            ["agent_action_proposals.id"],
        ),
        sa.ForeignKeyConstraint(
            ["rollback_proposal_id"],
            ["agent_action_proposals.id"],
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rollback_proposal_id",
            name="uq_agent_action_rollback_proposal",
        ),
    )
    op.create_index(
        "ix_agent_action_rollback_source",
        "agent_action_rollbacks",
        ["source_proposal_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_action_rollback_source",
        table_name="agent_action_rollbacks",
    )
    op.drop_table("agent_action_rollbacks")

    with op.batch_alter_table("agent_action_approvals") as batch_op:
        batch_op.drop_index("ix_agent_action_approval_progress")
        batch_op.drop_constraint(
            "uq_agent_action_approval_proposal_approver",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_agent_action_approval_proposal",
            ["proposal_id"],
        )
