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
        sa.Column("id