"""conversation store: titles, listing metadata, message branching

Revision ID: 0019_conversation_store
Revises: 0018_replace_local_users
Create Date: 2026-07-23

Adds conversation listing metadata (title, summary, message_count, pinned,
last_message_at) and tree-structured message branching (parent_id).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_conversation_store"
down_revision: Union[str, None] = "0018_replace_local_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- agent_conversations: listing metadata ---
    with op.batch_alter_table("agent_conversations") as batch:
        batch.add_column(sa.Column("title", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("message_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch.add_column(
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_index(
        "ix_agent_conversation_listing",
        "agent_conversations",
        ["organization_id", "created_by_user_id", "status", "last_message_at"],
        unique=False,
    )

    # --- agent_messages: tree branching ---
    with op.batch_alter_table("agent_messages") as batch:
        batch.add_column(sa.Column("parent_id", sa.String(), nullable=True))
        batch.create_foreign_key(
            "fk_agent_messages_parent_id_agent_messages",
            "agent_messages",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_agent_message_parent",
        "agent_messages",
        ["conversation_id", "parent_id"],
        unique=False,
    )

    # Backfill last_message_at from most recent message per conversation
    op.execute(
        sa.text(
            """
            UPDATE agent_conversations
            SET last_message_at = (
                SELECT MAX(m.created_at)
                FROM agent_messages m
                WHERE m.conversation_id = agent_conversations.id
            ),
            message_count = (
                SELECT COUNT(*)
                FROM agent_messages m
                WHERE m.conversation_id = agent_conversations.id
            )
            WHERE EXISTS (
                SELECT 1 FROM agent_messages m
                WHERE m.conversation_id = agent_conversations.id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_agent_message_parent", table_name="agent_messages")
    with op.batch_alter_table("agent_messages") as batch:
        batch.drop_constraint(
            "fk_agent_messages_parent_id_agent_messages", type_="foreignkey"
        )
        batch.drop_column("parent_id")

    op.drop_index("ix_agent_conversation_listing", table_name="agent_conversations")
    with op.batch_alter_table("agent_conversations") as batch:
        batch.drop_column("last_message_at")
        batch.drop_column("pinned")
        batch.drop_column("message_count")
        batch.drop_column("summary")
        batch.drop_column("title")
