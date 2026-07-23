"""Repository for conversation listing, search, and management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.agent_run_models import AgentConversationORM, AgentMessageORM


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ConversationListRecord:
    id: str
    title: str | None
    summary: str | None
    status: str
    message_count: int
    pinned: bool
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationMessageFullRecord:
    id: str
    conversation_id: str
    run_id: str | None
    parent_id: str | None
    sequence: int
    role: str
    content: str
    mode: str | None
    answer_source: str | None
    safe_metadata: dict | None
    created_at: datetime


@dataclass(frozen=True)
class ConversationSearchHit:
    message_id: str
    conversation_id: str
    conversation_title: str | None
    role: str
    snippet: str
    created_at: datetime


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_conversations(
        self,
        *,
        organization_id: str,
        user_id: str,
        limit: int = 30,
        offset: int = 0,
        search: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[ConversationListRecord], int]:
        """Return paginated conversations sorted by pinned DESC, last_message_at DESC."""
        base_filter = [
            AgentConversationORM.organization_id == organization_id,
            AgentConversationORM.created_by_user_id == user_id,
        ]
        if not include_archived:
            base_filter.append(AgentConversationORM.status == "active")

        if search:
            pattern = f"%{search}%"
            base_filter.append(
                or_(
                    AgentConversationORM.title.ilike(pattern),
                    AgentConversationORM.summary.ilike(pattern),
                )
            )

        where_clause = base_filter

        # Total count
        count_stmt = select(func.count(AgentConversationORM.id)).where(*where_clause)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated listing
        stmt = (
            select(AgentConversationORM)
            .where(*where_clause)
            .order_by(
                AgentConversationORM.pinned.desc(),
                AgentConversationORM.last_message_at.desc().nulls_last(),
                AgentConversationORM.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        records = [
            ConversationListRecord(
                id=row.id,
                title=row.title,
                summary=row.summary,
                status=row.status,
                message_count=row.message_count,
                pinned=row.pinned,
                last_message_at=row.last_message_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        return records, total

    async def get_conversation(
        self, *, conversation_id: str, organization_id: str, user_id: str
    ) -> AgentConversationORM | None:
        stmt = select(AgentConversationORM).where(
            AgentConversationORM.id == conversation_id,
            AgentConversationORM.organization_id == organization_id,
            AgentConversationORM.created_by_user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def rename_conversation(
        self, *, conversation_id: str, title: str | None
    ) -> bool:
        result = await self._session.execute(
            update(AgentConversationORM)
            .where(AgentConversationORM.id == conversation_id)
            .values(title=title, updated_at=_utcnow())
        )
        await self._session.commit()
        return result.rowcount == 1

    async def pin_conversation(
        self, *, conversation_id: str, pinned: bool
    ) -> bool:
        result = await self._session.execute(
            update(AgentConversationORM)
            .where(AgentConversationORM.id == conversation_id)
            .values(pinned=pinned, updated_at=_utcnow())
        )
        await self._session.commit()
        return result.rowcount == 1

    async def archive_conversation(self, *, conversation_id: str) -> bool:
        now = _utcnow()
        result = await self._session.execute(
            update(AgentConversationORM)
            .where(AgentConversationORM.id == conversation_id)
            .values(status="archived", archived_at=now, updated_at=now)
        )
        await self._session.commit()
        return result.rowcount == 1

    async def get_history(
        self,
        *,
        conversation_id: str,
        leaf_id: str | None = None,
    ) -> tuple[list[ConversationMessageFullRecord], bool]:
        """Retrieve message history. If leaf_id is given, walk the tree from leaf to root."""
        if leaf_id is not None:
            return await self._walk_branch(conversation_id, leaf_id)

        stmt = (
            select(AgentMessageORM)
            .where(AgentMessageORM.conversation_id == conversation_id)
            .order_by(AgentMessageORM.sequence.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        has_branches = any(row.parent_id is not None for row in rows)
        records = [self._to_full_record(row) for row in rows]
        return records, has_branches

    async def _walk_branch(
        self, conversation_id: str, leaf_id: str
    ) -> tuple[list[ConversationMessageFullRecord], bool]:
        """Walk from leaf to root via parent_id, then reverse."""
        messages: list[AgentMessageORM] = []
        current_id: str | None = leaf_id
        visited: set[str] = set()

        while current_id is not None:
            if current_id in visited:
                break  # cycle protection
            visited.add(current_id)
            row = await self._session.get(AgentMessageORM, current_id)
            if row is None or row.conversation_id != conversation_id:
                break
            messages.append(row)
            current_id = row.parent_id

        messages.reverse()
        records = [self._to_full_record(row) for row in messages]
        return records, True

    async def search_messages(
        self,
        *,
        organization_id: str,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> list[ConversationSearchHit]:
        """Full-text search across message content using LIKE (SQLite-compatible)."""
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

        hits: list[ConversationSearchHit] = []
        for row in rows:
            message = row[0]
            conv_title = row[1]
            # Create a snippet around the match
            snippet = self._make_snippet(message.content, query)
            hits.append(
                ConversationSearchHit(
                    message_id=message.id,
                    conversation_id=message.conversation_id,
                    conversation_title=conv_title,
                    role=message.role,
                    snippet=snippet,
                    created_at=message.created_at,
                )
            )
        return hits

    async def update_conversation_metadata(
        self, *, conversation_id: str, message_count_delta: int = 0
    ) -> None:
        """Update last_message_at and message_count after a new message is added."""
        now = _utcnow()
        conversation = await self._session.get(AgentConversationORM, conversation_id)
        if conversation is None:
            return
        await self._session.execute(
            update(AgentConversationORM)
            .where(AgentConversationORM.id == conversation_id)
            .values(
                last_message_at=now,
                message_count=conversation.message_count + message_count_delta,
                updated_at=now,
            )
        )
        await self._session.commit()

    async def set_title_if_empty(
        self, *, conversation_id: str, title: str
    ) -> bool:
        """Set title only if the conversation currently has no title."""
        result = await self._session.execute(
            update(AgentConversationORM)
            .where(
                AgentConversationORM.id == conversation_id,
                AgentConversationORM.title.is_(None),
            )
            .values(title=title[:200], updated_at=_utcnow())
        )
        await self._session.commit()
        return result.rowcount == 1

    @staticmethod
    def _make_snippet(content: str, query: str, context_chars: int = 80) -> str:
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

    @staticmethod
    def _to_full_record(row: AgentMessageORM) -> ConversationMessageFullRecord:
        return ConversationMessageFullRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            run_id=row.run_id,
            parent_id=row.parent_id,
            sequence=row.sequence,
            role=row.role,
            content=row.content,
            mode=row.mode,
            answer_source=row.answer_source,
            safe_metadata=row.safe_metadata_json,
            created_at=row.created_at,
        )
