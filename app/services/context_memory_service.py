"""Context memory service for Cloudflare-inspired conversation memory blocks.

Manages context blocks (soul, memory, knowledge, skill) that provide
persistent memory and context for agent conversations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.agent_run_models import AgentContextBlockORM


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _estimate_tokens(text: str) -> int:
    """Simple token estimation: ~1.3 tokens per word."""
    words = len(text.split())
    return int(words * 1.3)


@dataclass(frozen=True)
class ContextBlock:
    """A context memory block."""

    id: str
    conversation_id: str
    block_type: str
    key: str
    content: str
    description: str | None
    max_tokens: int | None
    current_tokens: int | None
    provider_type: str
    loaded: bool
    created_at: datetime
    updated_at: datetime


# Default soul content for workplace agent
DEFAULT_SOUL_CONTENT = """You are SARA, the workplace assistant for this organization.

Your role:
- Answer workplace questions using available tools and data
- Help users understand organization resources, users, and settings
- Create governed action proposals for changes that require approval
- Maintain a helpful, professional, and concise communication style

Guidelines:
- Always verify information before responding
- Use available tools to fetch real data rather than guessing
- For actions that modify data, create proposals for approval
- Be transparent about limitations and uncertainties
"""

# Default memory block description
DEFAULT_MEMORY_DESCRIPTION = "Important facts learned during this conversation"

# Default todos block description
DEFAULT_TODOS_DESCRIPTION = "Task tracking for this conversation"


class ContextMemoryService:
    """Service for managing conversation context memory blocks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def initialize_conversation_blocks(
        self, conversation_id: str
    ) -> list[ContextBlock]:
        """
        Initialize default context blocks for a new conversation.

        Creates:
        - soul (readonly): Agent identity and instructions
        - memory (writable): Important facts learned
        - todos (writable): Task tracking
        """
        now = _utcnow()
        blocks = [
            AgentContextBlockORM(
                id=uuid.uuid4().hex,
                conversation_id=conversation_id,
                block_type="soul",
                key="soul",
                content=DEFAULT_SOUL_CONTENT,
                description="Agent identity and instructions",
                max_tokens=None,
                current_tokens=_estimate_tokens(DEFAULT_SOUL_CONTENT),
                provider_type="readonly",
                loaded=True,
                created_at=now,
                updated_at=now,
            ),
            AgentContextBlockORM(
                id=uuid.uuid4().hex,
                conversation_id=conversation_id,
                block_type="memory",
                key="memory",
                content="",
                description=DEFAULT_MEMORY_DESCRIPTION,
                max_tokens=1100,
                current_tokens=0,
                provider_type="writable",
                loaded=True,
                created_at=now,
                updated_at=now,
            ),
            AgentContextBlockORM(
                id=uuid.uuid4().hex,
                conversation_id=conversation_id,
                block_type="memory",
                key="todos",
                content="",
                description=DEFAULT_TODOS_DESCRIPTION,
                max_tokens=2000,
                current_tokens=0,
                provider_type="writable",
                loaded=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        self._session.add_all(blocks)
        await self._session.commit()
        return [self._to_block(b) for b in blocks]

    async def get_blocks(
        self, conversation_id: str, block_type: str | None = None
    ) -> list[ContextBlock]:
        """Get all context blocks for a conversation, optionally filtered by type."""
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id
        )
        if block_type:
            stmt = stmt.where(AgentContextBlockORM.block_type == block_type)
        stmt = stmt.order_by(AgentContextBlockORM.created_at.asc())

        result = await self._session.execute(stmt)
        return [self._to_block(row) for row in result.scalars().all()]

    async def get_block(
        self, conversation_id: str, key: str
    ) -> ContextBlock | None:
        """Get a specific context block by key."""
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id,
            AgentContextBlockORM.key == key,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_block(row) if row else None

    async def set_context(
        self, conversation_id: str, key: str, content: str
    ) -> ContextBlock | None:
        """
        Write content to a writable context block.

        Returns None if the block doesn't exist or is not writable.
        """
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id,
            AgentContextBlockORM.key == key,
        )
        result = await self._session.execute(stmt)
        block = result.scalar_one_or_none()

        if block is None:
            return None
        if block.provider_type != "writable":
            return None

        # Check token limit
        new_tokens = _estimate_tokens(content)
        if block.max_tokens and new_tokens > block.max_tokens:
            # Truncate to fit within limit (approximate)
            max_words = int(block.max_tokens / 1.3)
            words = content.split()[:max_words]
            content = " ".join(words)
            new_tokens = _estimate_tokens(content)

        block.content = content
        block.current_tokens = new_tokens
        block.updated_at = _utcnow()
        await self._session.commit()
        return self._to_block(block)

    async def append_context(
        self, conversation_id: str, key: str, content: str
    ) -> ContextBlock | None:
        """
        Append content to a writable context block.

        Returns None if the block doesn't exist or is not writable.
        """
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id,
            AgentContextBlockORM.key == key,
        )
        result = await self._session.execute(stmt)
        block = result.scalar_one_or_none()

        if block is None:
            return None
        if block.provider_type != "writable":
            return None

        new_content = f"{block.content}\n{content}".strip()
        new_tokens = _estimate_tokens(new_content)

        # Check token limit and truncate if needed
        if block.max_tokens and new_tokens > block.max_tokens:
            # Keep the most recent content
            max_words = int(block.max_tokens / 1.3)
            words = new_content.split()[-max_words:]
            new_content = " ".join(words)
            new_tokens = _estimate_tokens(new_content)

        block.content = new_content
        block.current_tokens = new_tokens
        block.updated_at = _utcnow()
        await self._session.commit()
        return self._to_block(block)

    async def load_skill(self, conversation_id: str, key: str) -> ContextBlock | None:
        """Load a skill block (set loaded=True)."""
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id,
            AgentContextBlockORM.key == key,
            AgentContextBlockORM.block_type == "skill",
        )
        result = await self._session.execute(stmt)
        block = result.scalar_one_or_none()

        if block is None:
            return None

        block.loaded = True
        block.updated_at = _utcnow()
        await self._session.commit()
        return self._to_block(block)

    async def unload_skill(self, conversation_id: str, key: str) -> ContextBlock | None:
        """Unload a skill block (set loaded=False) to free context space."""
        stmt = select(AgentContextBlockORM).where(
            AgentContextBlockORM.conversation_id == conversation_id,
            AgentContextBlockORM.key == key,
            AgentContextBlockORM.block_type == "skill",
        )
        result = await self._session.execute(stmt)
        block = result.scalar_one_or_none()

        if block is None:
            return None

        block.loaded = False
        block.updated_at = _utcnow()
        await self._session.commit()
        return self._to_block(block)

    async def assemble_system_prompt(self, conversation_id: str) -> str:
        """
        Assemble all loaded context blocks into a structured system prompt.

        Order: soul -> memory -> knowledge summary -> loaded skills
        """
        blocks = await self.get_blocks(conversation_id)
        if not blocks:
            return DEFAULT_SOUL_CONTENT

        sections: list[str] = []

        # Soul block first
        soul_blocks = [b for b in blocks if b.block_type == "soul" and b.loaded]
        for block in soul_blocks:
            sections.append(block.content)

        # Memory blocks
        memory_blocks = [b for b in blocks if b.block_type == "memory" and b.loaded and b.content]
        if memory_blocks:
            sections.append("## Conversation Memory")
            for block in memory_blocks:
                if block.description:
                    sections.append(f"### {block.description}")
                sections.append(block.content)

        # Knowledge blocks (summary only)
        knowledge_blocks = [b for b in blocks if b.block_type == "knowledge" and b.loaded]
        if knowledge_blocks:
            sections.append("## Available Knowledge")
            for block in knowledge_blocks:
                desc = block.description or block.key
                token_info = f" ({block.current_tokens or 0} tokens)" if block.current_tokens else ""
                sections.append(f"- {desc}{token_info}")

        # Loaded skills
        skill_blocks = [b for b in blocks if b.block_type == "skill" and b.loaded]
        if skill_blocks:
            sections.append("## Loaded Skills")
            for block in skill_blocks:
                sections.append(f"### {block.key}")
                sections.append(block.content)

        return "\n\n".join(sections)

    async def search_context(
        self, conversation_id: str, key: str, query: str
    ) -> str | None:
        """
        Search within a searchable context block.

        Returns matching content or None if not found.
        """
        block = await self.get_block(conversation_id, key)
        if block is None:
            return None
        if block.provider_type not in ("searchable", "writable", "readonly"):
            return None

        # Simple keyword search within content
        lower_content = block.content.lower()
        lower_query = query.lower()

        if lower_query in lower_content:
            # Return context around the match
            idx = lower_content.find(lower_query)
            start = max(0, idx - 200)
            end = min(len(block.content), idx + len(query) + 200)
            return block.content[start:end]

        return None

    @staticmethod
    def _to_block(row: AgentContextBlockORM) -> ContextBlock:
        return ContextBlock(
            id=row.id,
            conversation_id=row.conversation_id,
            block_type=row.block_type,
            key=row.key,
            content=row.content,
            description=row.description,
            max_tokens=row.max_tokens,
            current_tokens=row.current_tokens,
            provider_type=row.provider_type,
            loaded=row.loaded,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
