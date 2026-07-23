"""Compaction service for long conversation history.

Implements macro-compaction (summarize older messages) and micro-compaction
(read-time truncation) to manage context window usage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.agent_run_models import (
    AgentCompactionOverlayORM,
    AgentMessageORM,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _estimate_tokens(text: str) -> int:
    """Simple token estimation: ~1.3 tokens per word."""
    return int(len(text.split()) * 1.3)


# Compaction configuration
COMPACTION_THRESHOLD = 50  # Trigger compaction when message count exceeds this
PROTECT_HEAD = 3  # Always keep first N messages uncompacted
PROTECT_TAIL = 4  # Always keep last N messages uncompacted
TAIL_TOKEN_BUDGET = 20000  # Target token budget for tail messages
MICRO_TRUNCATE_LIMIT = 500  # Truncate tool outputs longer than this


@dataclass(frozen=True)
class CompactionOverlay:
    """A compaction overlay record."""

    id: str
    conversation_id: str
    start_sequence: int
    end_sequence: int
    summary_text: str
    token_estimate: int
    original_message_count: int
    created_at: datetime


@dataclass(frozen=True)
class CompactedMessage:
    """A message with optional compaction applied."""

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
    is_compacted: bool = False
    original_content: str | None = None


class CompactionService:
    """Service for managing conversation compaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def should_compact(self, conversation_id: str) -> bool:
        """Check if a conversation needs compaction."""
        stmt = select(AgentMessageORM.sequence).where(
            AgentMessageORM.conversation_id == conversation_id
        )
        result = await self._session.execute(stmt)
        sequences = [row[0] for row in result.all()]
        return len(sequences) > COMPACTION_THRESHOLD

    async def get_overlays(
        self, conversation_id: str
    ) -> list[CompactionOverlay]:
        """Get all compaction overlays for a conversation."""
        stmt = (
            select(AgentCompactionOverlayORM)
            .where(AgentCompactionOverlayORM.conversation_id == conversation_id)
            .order_by(AgentCompactionOverlayORM.start_sequence.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_overlay(row) for row in result.scalars().all()]

    async def compact(
        self, conversation_id: str, *, force: bool = False
    ) -> CompactionOverlay | None:
        """
        Compact older messages in a conversation.

        Creates a summary overlay for messages between PROTECT_HEAD and
        the tail token budget boundary. Original messages are preserved.

        Returns the created overlay, or None if no compaction was needed.
        """
        # Get all messages ordered by sequence
        stmt = (
            select(AgentMessageORM)
            .where(AgentMessageORM.conversation_id == conversation_id)
            .order_by(AgentMessageORM.sequence.asc())
        )
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())

        if len(messages) <= COMPACTION_THRESHOLD and not force:
            return None

        # Determine compaction range
        # Protect head messages and tail messages
        if len(messages) <= PROTECT_HEAD + PROTECT_TAIL:
            return None

        # Find the tail boundary based on token budget
        tail_start_idx = len(messages) - PROTECT_TAIL
        tail_tokens = 0
        for i in range(len(messages) - 1, PROTECT_HEAD - 1, -1):
            msg_tokens = _estimate_tokens(messages[i].content)
            if tail_tokens + msg_tokens > TAIL_TOKEN_BUDGET:
                tail_start_idx = i + 1
                break
            tail_tokens += msg_tokens
            tail_start_idx = i

        # Ensure we protect at least PROTECT_TAIL messages
        tail_start_idx = min(tail_start_idx, len(messages) - PROTECT_TAIL)

        # Compaction range: from after head to before tail
        compact_start_idx = PROTECT_HEAD
        compact_end_idx = tail_start_idx - 1

        if compact_start_idx > compact_end_idx:
            return None

        # Check if this range is already compacted
        existing_overlays = await self.get_overlays(conversation_id)
        for overlay in existing_overlays:
            if (
                overlay.start_sequence <= messages[compact_start_idx].sequence
                and overlay.end_sequence >= messages[compact_end_idx].sequence
            ):
                return None  # Already compacted

        # Create summary of compacted messages
        compacted_messages = messages[compact_start_idx : compact_end_idx + 1]
        summary = self._create_summary(compacted_messages)

        # Create overlay
        now = _utcnow()
        overlay = AgentCompactionOverlayORM(
            id=uuid.uuid4().hex,
            conversation_id=conversation_id,
            start_sequence=compacted_messages[0].sequence,
            end_sequence=compacted_messages[-1].sequence,
            summary_text=summary,
            token_estimate=_estimate_tokens(summary),
            original_message_count=len(compacted_messages),
            created_at=now,
        )
        self._session.add(overlay)
        await self._session.commit()
        return self._to_overlay(overlay)

    async def get_compacted_history(
        self, conversation_id: str, *, apply_micro: bool = True
    ) -> list[CompactedMessage]:
        """
        Get conversation history with compaction overlays applied.

        Macro-compaction: Replaces compacted message ranges with summaries.
        Micro-compaction: Truncates long tool outputs in older messages.
        """
        # Get all messages
        stmt = (
            select(AgentMessageORM)
            .where(AgentMessageORM.conversation_id == conversation_id)
            .order_by(AgentMessageORM.sequence.asc())
        )
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())

        if not messages:
            return []

        # Get overlays
        overlays = await self.get_overlays(conversation_id)

        # Build result with compaction applied
        result_messages: list[CompactedMessage] = []
        overlay_idx = 0
        message_idx = 0

        while message_idx < len(messages):
            msg = messages[message_idx]

            # Check if this message is covered by an overlay
            if overlay_idx < len(overlays):
                overlay = overlays[overlay_idx]
                if msg.sequence == overlay.start_sequence:
                    # Insert summary message
                    result_messages.append(
                        CompactedMessage(
                            id=f"compacted-{overlay.id}",
                            conversation_id=conversation_id,
                            run_id=None,
                            parent_id=None,
                            sequence=overlay.start_sequence,
                            role="system",
                            content=f"[Conversation history summary: {overlay.summary_text}]",
                            mode=None,
                            answer_source=None,
                            safe_metadata={
                                "compacted": True,
                                "original_count": overlay.original_message_count,
                            },
                            created_at=overlay.created_at,
                            is_compacted=True,
                        )
                    )
                    # Skip all messages in the overlay range
                    while (
                        message_idx < len(messages)
                        and messages[message_idx].sequence <= overlay.end_sequence
                    ):
                        message_idx += 1
                    overlay_idx += 1
                    continue

            # Apply micro-compaction to older messages
            is_tail = message_idx >= len(messages) - PROTECT_TAIL
            content = msg.content
            original_content = None

            if apply_micro and not is_tail:
                content, original_content = self._micro_compact(msg)

            result_messages.append(
                CompactedMessage(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    run_id=msg.run_id,
                    parent_id=msg.parent_id,
                    sequence=msg.sequence,
                    role=msg.role,
                    content=content,
                    mode=msg.mode,
                    answer_source=msg.answer_source,
                    safe_metadata=msg.safe_metadata_json,
                    created_at=msg.created_at,
                    is_compacted=False,
                    original_content=original_content,
                )
            )
            message_idx += 1

        return result_messages

    def _create_summary(self, messages: list[AgentMessageORM]) -> str:
        """Create a deterministic summary of messages (no LLM required)."""
        if not messages:
            return ""

        # Count messages by role
        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        # Extract key topics from user messages
        user_messages = [m for m in messages if m.role == "user"]
        topics = []
        for msg in user_messages[:5]:  # Sample first 5 user messages
            # Take first sentence or first 100 chars
            content = msg.content.strip()
            first_sentence = content.split(".")[0] if "." in content else content
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:97] + "..."
            topics.append(first_sentence)

        summary_parts = [
            f"This section contains {len(messages)} messages ({user_count} user, {assistant_count} assistant).",
        ]

        if topics:
            summary_parts.append("Topics discussed:")
            for topic in topics:
                summary_parts.append(f"- {topic}")

        # Include last assistant response summary if available
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if assistant_messages:
            last_response = assistant_messages[-1].content
            if len(last_response) > 200:
                last_response = last_response[:197] + "..."
            summary_parts.append(f"Last response preview: {last_response}")

        return "\n".join(summary_parts)

    def _micro_compact(
        self, msg: AgentMessageORM
    ) -> tuple[str, str | None]:
        """
        Apply micro-compaction to a message.

        Truncates long content in older messages, preserving a preview.
        Returns (compacted_content, original_content_or_None).
        """
        if len(msg.content) <= MICRO_TRUNCATE_LIMIT:
            return msg.content, None

        # Truncate with preview
        preview = msg.content[:MICRO_TRUNCATE_LIMIT]
        truncated = f"{preview}... [truncated, {len(msg.content) - MICRO_TRUNCATE_LIMIT} chars omitted]"
        return truncated, msg.content

    @staticmethod
    def _to_overlay(row: AgentCompactionOverlayORM) -> CompactionOverlay:
        return CompactionOverlay(
            id=row.id,
            conversation_id=row.conversation_id,
            start_sequence=row.start_sequence,
            end_sequence=row.end_sequence,
            summary_text=row.summary_text,
            token_estimate=row.token_estimate,
            original_message_count=row.original_message_count,
            created_at=row.created_at,
        )
