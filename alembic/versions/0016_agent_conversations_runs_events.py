"""add durable agent conversations, runs, and events

Revision ID: 0016_agent_runs_events
Revises: 0015_workplace_workflows
Create Date: 2026-07-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_agent_runs_events"
down_revision: Union[str, None] = "0015_workplace_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("next_message_sequence", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_conversation_owner_updated",
        "agent_conversations",
        ["organization_id", "created_by_user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(), nullable=False),
        sa.Column("user_message_id", sa.String(), nullable=False),
        sa.Column("client_request_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("active_slot", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("final_mode", sa.String(length=40), nullable=True),
        sa.Column("final_message_id", sa.String(), nullable=True),
        sa.Column("proposal_id", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=160), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_event_sequence", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "requested_by_user_id",
            "client_request_id",
            name="uq_agent_run_request_idempotency",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "active_slot",
            name="uq_agent_run_active_conversation",
        ),
    )
    op.create_index(
        "ix_agent_run_claim",
        "agent_runs",
        ["status", "lease_expires_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_conversation_created",
        "agent_runs",
        ["conversation_id", "created_at"],
        unique=False,
    )

    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.add_column(
            sa.Column("source_agent_run_id", sa.String(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_agent_action_proposal_source_run",
            "agent_runs",
            ["source_agent_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ux_agent_action_proposal_source_run",
            ["source_agent_run_id"],
            unique=True,
        )

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=True),
        sa.Column("answer_source", sa.String(length=40), nullable=True),
        sa.Column("safe_metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence",
            name="uq_agent_message_conversation_sequence",
        ),
    )
    op.create_index(
        "ix_agent_message_conversation_sequence",
        "agent_messages",
        ["conversation_id", "sequence"],
        unique=False,
    )

    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("safe_message", sa.String(length=240), nullable=False),
        sa.Column("safe_payload_json", sa.JSON(), nullable=True),
        sa.Column("terminal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_agent_run_event_sequence"),
    )
    op.create_index(
        "ix_agent_run_event_replay",
        "agent_run_events",
        ["run_id", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_run_event_replay", table_name="agent_run_events")
    op.drop_table("agent_run_events")
    op.drop_index(
        "ix_agent_message_conversation_sequence", table_name="agent_messages"
    )
    op.drop_table("agent_messages")
    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.drop_index("ux_agent_action_proposal_source_run")
        batch_op.drop_constraint(
            "fk_agent_action_proposal_source_run", type_="foreignkey"
        )
        batch_op.drop_column("source_agent_run_id")
    op.drop_index("ix_agent_run_conversation_created", table_name="agent_runs")
    op.drop_index("ix_agent_run_claim", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(
        "ix_agent_conversation_owner_updated", table_name="agent_conversations"
    )
    op.drop_table("agent_conversations")
