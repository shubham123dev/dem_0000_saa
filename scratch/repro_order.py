import asyncio
import traceback
import uuid
from datetime import datetime, timezone

from app.db import (  # noqa: F401  register all tables in metadata
    action_models,
    nucleus_admin_models,
    nucleus_models,
    orm_models,
)
from app.db.session import get_sessionmaker
from app.db.agent_run_models import AgentConversationORM
from app.repositories.agent_run_repository import AgentRunRepository


async def main():
    sm = get_sessionmaker()
    async with sm() as session:
        repo = AgentRunRepository(session)
        now = datetime.now(timezone.utc)
        conv_id = uuid.uuid4().hex
        try:
            conv = AgentConversationORM(
                id=conv_id,
                organization_id="org_sandbox_001",
                created_by_user_id="215",
                status="active",
                next_message_sequence=2,
                version=1,
                message_count=1,
                last_message_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(conv)
            await session.flush()  # flush parent FIRST
            session.add_all(repo._create_default_context_blocks(conv_id, now))
            await session.flush()
            print("ORDERED INSERT OK -> ordering was the problem")
            await session.rollback()
        except Exception:
            print("STILL FAILS with ordered flush:")
            traceback.print_exc()


asyncio.run(main())
