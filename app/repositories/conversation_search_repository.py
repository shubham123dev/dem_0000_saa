"""Full-text search repository using SQLite FTS5.

Provides ranked full-text search across conversation messages with
conversation context (title, status) for result display.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class FtsSearchHit:
    """A single full-text search result."""

    message_id: str
    conversation_id: str
    conversation_title: str | None
    role: str
    snippet: str
    rank: float
    created_at: datetime


class ConversationSearchRepository:
    """Repository for FTS5-based full-text search across messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        organization_id: str,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> list[FtsSearchHit]:
        """
        Full-text search across message content using FTS5.

        Falls back to LIKE-based search if FTS5 query fails.
        """
        if not query or not query.strip():
            return []

        try:
            return await self._fts5_search(
                organization_id=organization_id,
                user_id=user_id,
                query=query.strip(),
                limit=limit,
            )
        except Exception:
            return await self._like_search(
                organization_id=organization_id,
                user_id=user_id,
                query=query.strip(),
                limit=limit,
            )

    async def _fts5_search(
        self,
        *,
        organization_id: str,
        user_id: str,
        query: str,
        limit: int,
    ) -> list[FtsSearchHit]:
        """Search using FTS5 virtual table with BM25 ranking."""
        # Escape FTS5 special characters and create search query
        fts_query = self._prepare_fts_query(query)

        sql = text("""
            SELECT
                fts.message_id,
                fts.conversation_id,
                c.title AS conversation_title,
                m.role,
                snippet(agent_messages_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet,
                rank,
                m.created_at
            FROM agent_messages_fts fts
            JOIN agent_messages m ON m.id = fts.message_id
            JOIN agent_conversations c ON c.id = fts.conversation_id
            WHERE agent_messages_fts MATCH :query
              AND c.organization_id = :org_id
              AND c.created_by_user_id = :user_id
              AND c.status = 'active'
            ORDER BY rank
            LIMIT :limit
        """)

        result = await self._session.execute(
            sql,
            {
                "query": fts_query,
                "org_id": organization_id,
                "user_id": user_id,
                "limit": limit,
            },
        )

        hits: list[FtsSearchHit] = []
        for row in result.all():
            hits.append(
                FtsSearchHit(
                    message_id=row.message_id,
                    conversation_id=row.conversation_id,
                    conversation_title=row.conversation_title,
                    role=row.role,
                    snippet=self._clean_snippet(row.snippet),
                    rank=row.rank,
                    created_at=row.created_at,
                )
            )
        return hits

    async def _like_search(
        self,
        *,
        organization_id: str,
        user_id: str,
        query: str,
        limit: int,
    ) -> list[FtsSearchHit]:
        """Fallback LIKE-based search when FTS5 query fails."""
        from app.db.agent_run_models import AgentConversationORM, AgentMessageORM
        from sqlalchemy import select

        pattern = f"%{query}%"
        stmt = (
            select(AgentMessageORM, AgentConversationORM.title)
            .join(
                AgentConversationORM,
                AgentMessageORM.conversation_id == AgentConversationORM.id,
            )
            .where(
                AgentConversationORM.organization_id == organization_id,
                AgentConversationORM.created_by_user_id == user_id,
                AgentConversationORM.status == "active",
                AgentMessageORM.content.ilike(pattern),
            )
            .order_by(AgentMessageORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        hits: list[FtsSearchHit] = []
        for idx, row in enumerate(rows):
            message = row[0]
            conv_title = row[1]
            snippet = self._make_snippet(message.content, query)
            hits.append(
                FtsSearchHit(
                    message_id=message.id,
                    conversation_id=message.conversation_id,
                    conversation_title=conv_title,
                    role=message.role,
                    snippet=snippet,
                    rank=float(idx),  # No ranking in LIKE search
                    created_at=message.created_at,
                )
            )
        return hits

    @staticmethod
    def _prepare_fts_query(query: str) -> str:
        """
        Prepare a query string for FTS5 matching.

        Escapes special characters and creates a prefix search query.
        """
        # FTS5 special characters: " * ^ ( ) : -
        # We'll use a simple approach: quote the entire query for phrase search
        # and add prefix matching for the last term
        escaped = query.replace('"', '""')

        # Split into words for prefix matching on last word
        words = escaped.split()
        if not words:
            return f'"{escaped}"'

        if len(words) == 1:
            # Single word: use prefix search
            return f"{words[0]}*"

        # Multiple words: phrase search with prefix on last word
        phrase = " ".join(words[:-1])
        return f'"{phrase}" {words[-1]}*'

    @staticmethod
    def _clean_snippet(snippet: str) -> str:
        """Clean up FTS5 snippet output."""
        # Remove HTML-like mark tags if present
        return snippet.replace("<mark>", "").replace("</mark>", "")

    @staticmethod
    def _make_snippet(content: str, query: str, context_chars: int = 80) -> str:
        """Create a snippet around the search query match."""
        lower_content = content.lower()
        lower_query = query.lower()
        idx = lower_content.find(lower_query)
        if idx == -1:
            return content[:160]
        start = max(0, idx - context_chars)
        end = min(len(content), idx + len(query) + context_chars)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet
