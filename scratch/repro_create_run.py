import asyncio
import traceback
import uuid
from datetime import datetime, timezone

from app.db import (  # noqa: F401  register all tables in metadata
    action_models,
    agent_run_models as _arm,
    nucleus_admin_models,
    nucleus_models,
    orm_models,
)
from app.db.session import get_sessionmaker
from app.db.agent_run_models import (
    AgentConversationORM,
    AgentRunORM,
    AgentMessageORM,
    AgentRunEventORM,
)
from app.repositories.agent_run_repository import AgentRunRepository


def _now():
    return datetime.now(timezone.utc)


async def main():
    sm = get_sessionmaker()
    async with sm() as session:
        repo = AgentRunRepository(session)
        now = _now()
        conv_id = uuid.uuid4().hex
        run_id = uuid.uuid4().hex
        message_id = uuid.uuid4().hex
        try:
            conversation_row = AgentConversationORM(
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
            session.add(conversation_row)
            session.add_all(repo._create_default_context_blocks(conv_id, now))
            message_row = AgentMessageORM(
                id=message_id,
                conversation_id=conv_id,
                run_id=run_id,
                parent_id=None,
                sequence=1,
                role="user",
                content="diag test",
                mode=None,
                answer_source=None,
                safe_metadata_json=None,
                created_at=now,
            )
            run_row = AgentRunORM(
                id=run_id,
                conversation_id=conv_id,
                organization_id="org_sandbox_001",
                requested_by_user_id="215",
                user_message_id=message_id,
                client_request_id="diag_" + uuid.uuid4().hex[:8],
                request_id="diag-req",
                active_slot=1,
                status="queued",
                current_stage="request_acceptance",
                attempt_count=0,
                next_event_sequence=2,
                version=1,
                created_at=now,
            )
            event_row = AgentRunEventORM(
                id=uuid.uuid4().hex,
                run_id=run_id,
                sequence=1,
                event_type="run.accepted",
                stage="request_acceptance",
                safe_message="Request accepted",
                safe_payload_json=None,
                terminal=False,
                created_at=now,
            )
            session.add(run_row)
            await session.flush()
            session.add_all((message_row, event_row))
            await session.commit()
            print("INSERT OK conv=", conv_id)
            # cleanup so we don't leave the diag row
            await session.delete(run_row)
            await session.delete(message_row)
            await session.delete(event_row)
            await session.delete(conversation_row)
            await session.commit()
            print("cleanup done")
        except Exception:
            print("REAL EXCEPTION:")
            traceback.print_exc()


asyncio.run(main())
