"""Context memory blocks for agent conversations.

Revision ID: 0021_context_memory
Revises: 0020_fts_search
Create Date: 2024-01-15

Adds agent_context_blocks table for Cloudflare-inspired context memory:
- soul (readonly): Agent identity and instructions
- memory (writable): Important facts learned during conversation
- knowledge (searchable): Searchable knowledge base
- skill (loadable): Loadable skill definitions
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_context_memory"
down_revision = "0020_fts_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_context_blocks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(64),
            sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("block_type", sa.String(32), nullable=False),  # soul, memory, knowledge, skill
        sa.Column("key", sa.String(128), nullable=False),  # block name
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),  # for writable blocks
        sa.Column("current_tokens", sa.Integer, nullable=True),  # tracked usage
        sa.Column(
            "provider_type", sa.String(32), nullable=False, server_default="readonly"
        ),  # readonly, writable, searchable, loadable
        sa.Column("loaded", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("conversation_id", "key", name="uq_context_block_key"),
    )

    # Index for efficient block lookup
    op.create_index(
        "ix_agent_context_blocks_conversation_type",
        "agent_context_blocks",
        ["conversation_id", "block_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_context_blocks_conversation_type", table_name="agent_context_blocks")
    op.drop_table("agent_context_blocks")
