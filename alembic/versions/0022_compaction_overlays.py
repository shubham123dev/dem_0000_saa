"""Compaction overlays for long conversation history.

Revision ID: 0022_compaction_overlays
Revises: 0021_context_memory
Create Date: 2024-01-15

Adds agent_compaction_overlays table for macro-compaction of long conversations.
Overlays store summarized versions of older message ranges, preserving originals.
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_compaction_overlays"
down_revision = "0021_context_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_compaction_overlays",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(64),
            sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("start_sequence", sa.Integer, nullable=False),
        sa.Column("end_sequence", sa.Integer, nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("token_estimate", sa.Integer, nullable=False, server_default="0"),
        sa.Column("original_message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        # Ensure no overlapping ranges per conversation
        sa.UniqueConstraint(
            "conversation_id",
            "start_sequence",
            "end_sequence",
            name="uq_compaction_overlay_range",
        ),
    )

    # Index for efficient overlay lookup
    op.create_index(
        "ix_agent_compaction_overlays_conversation_seq",
        "agent_compaction_overlays",
        ["conversation_id", "start_sequence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_compaction_overlays_conversation_seq",
        table_name="agent_compaction_overlays",
    )
    op.drop_table("agent_compaction_overlays")
