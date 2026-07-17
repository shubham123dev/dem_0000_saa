from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_agent_action_approvals"
down_revision: Union[str, None] = "0003_remove_chatbot_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_action_proposals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(), nullable=False),
        sa.Column("action_name", sa.String(), nullable=False),
        sa.Column("arguments_json", sa.JSON(), nullable=False),
        sa.Column("changes_json", sa.JSON(), nullable=False),
        sa.Column("action_fingerprint", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_action_proposals_organization_id",
        "agent_action_proposals",
        ["organization_id"],
    )
    op.create_index(
        "ix_agent_action_proposals_requested_by_user_id",
        "agent_action_proposals",
        ["requested_by_user_id"],
    )
    op.create_index(
        "ix_agent_action_proposals_action_fingerprint",
        "agent_action_proposals",
        ["action_fingerprint"],
    )
    op.create_index(
        "ix_agent_action_proposals_status",
        "agent_action_proposals",
        ["status"],
    )

    op.create_table(
        "agent_action_approvals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("decided_by_user_id", sa.String(), nullable=False),
        sa.Column("decision_reason", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["agent_action_proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_agent_action_approval_proposal"),
    )
    op.create_index(
        "ix_agent_action_approvals_proposal_id",
        "agent_action_approvals",
        ["proposal_id"],
    )
    op.create_index(
        "ix_agent_action_approvals_decided_by_user_id",
        "agent_action_approvals",
        ["decided_by_user_id"],
    )

    op.create_table(
        "agent_action_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["agent_action_proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_agent_action_execution_proposal"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_action_execution_key"),
    )
    op.create_index(
        "ix_agent_action_executions_proposal_id",
        "agent_action_executions",
        ["proposal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_action_executions_proposal_id",
        table_name="agent_action_executions",
    )
    op.drop_table("agent_action_executions")
    op.drop_index(
        "ix_agent_action_approvals_decided_by_user_id",
        table_name="agent_action_approvals",
    )
    op.drop_index(
        "ix_agent_action_approvals_proposal_id",
        table_name="agent_action_approvals",
    )
    op.drop_table("agent_action_approvals")
    op.drop_index(
        "ix_agent_action_proposals_status",
        table_name="agent_action_proposals",
    )
    op.drop_index(
        "ix_agent_action_proposals_action_fingerprint",
        table_name="agent_action_proposals",
    )
    op.drop_index(
        "ix_agent_action_proposals_requested_by_user_id",
        table_name="agent_action_proposals",
    )
    op.drop_index(
        "ix_agent_action_proposals_organization_id",
        table_name="agent_action_proposals",
    )
    op.drop_table("agent_action_proposals")
