"""Full-text search index for agent messages.

Revision ID: 0020_fts_search
Revises: 0019_conversation_store
Create Date: 2024-01-15

Adds SQLite FTS5 virtual table for full-text search across conversation messages.
"""

from alembic import op
import sqlalchemy as sa

revision = "0020_fts_search"
down_revision = "0019_conversation_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create FTS5 virtual table for full-text search
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS agent_messages_fts USING fts5(
            message_id UNINDEXED,
            conversation_id UNINDEXED,
            content,
            tokenize='porter unicode61'
        )
    """)

    # Populate FTS index from existing messages
    op.execute("""
        INSERT INTO agent_messages_fts (message_id, conversation_id, content)
        SELECT id, conversation_id, content
        FROM agent_messages
        WHERE content IS NOT NULL AND content != ''
    """)

    # Trigger for INSERT
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS agent_messages_ai AFTER INSERT ON agent_messages
        WHEN NEW.content IS NOT NULL AND NEW.content != ''
        BEGIN
            INSERT INTO agent_messages_fts (message_id, conversation_id, content)
            VALUES (NEW.id, NEW.conversation_id, NEW.content);
        END
    """)

    # Trigger for DELETE
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS agent_messages_ad AFTER DELETE ON agent_messages
        BEGIN
            DELETE FROM agent_messages_fts WHERE message_id = OLD.id;
        END
    """)

    # Trigger for UPDATE
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS agent_messages_au AFTER UPDATE OF content ON agent_messages
        BEGIN
            DELETE FROM agent_messages_fts WHERE message_id = OLD.id;
            INSERT INTO agent_messages_fts (message_id, conversation_id, content)
            SELECT NEW.id, NEW.conversation_id, NEW.content
            WHERE NEW.content IS NOT NULL AND NEW.content != '';
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS agent_messages_au")
    op.execute("DROP TRIGGER IF EXISTS agent_messages_ad")
    op.execute("DROP TRIGGER IF EXISTS agent_messages_ai")
    op.execute("DROP TABLE IF EXISTS agent_messages_fts")
