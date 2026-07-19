"""add governed action execution event journal

Revision ID: 0017_action_control_plane
Revises: 0016_agent_runs_events
Create Date: 2026-07-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_action_control_plane"
down_revision: Union[str, None] = "0016_agent_runs_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_action_execution_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("safe_message", sa.String(length=240), nullable=False),
        sa.Column("safe_payload_json", sa.JSON(), nullable=True),
        sa.Column("terminal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["agent_action_proposals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposal_id",
            "sequence",
            name="uq_action_execution_event_sequence",
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "dedupe_key",
            name="uq_action_execution_event_dedupe",
        ),
    )
    op.create_index(
        "ix_action_execution_event_replay",
        "agent_action_execution_events",
        ["proposal_id", "sequence"],
        unique=False,
    )
    op.create_index(
        "ix_action_execution_event_terminal",
        "agent_action_execution_events",
        ["proposal_id", "terminal", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_execution_event_terminal",
        table_name="agent_action_execution_events",
    )
    op.drop_index(
        "ix_action_execution_event_replay",
        table_name="agent_action_execution_events",
    )
    op.drop_table("agent_action_execution_events")
