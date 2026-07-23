import asyncio
import traceback
import uuid

from app.db import (  # noqa: F401
    action_models,
    nucleus_admin_models,
    nucleus_models,
    orm_models,
)
from app.db.session import get_sessionmaker
from app.repositories.agent_run_repository import AgentRunRepository


async def main():
    sm = get_sessionmaker()
    async with sm() as session:
        repo = AgentRunRepository(session)
        try:
            created = await repo.create_run(
                organization_id="org_sandbox_001",
                requested_by_user_id="215",
                query="diag real create_run",
                client_request_id="diagreal_" + uuid.uuid4().hex[:8],
                conversation_id=None,
                request_id="diag-real-req",
            )
            print("CREATE_RUN OK conv=", created.conversation.id, "run=", created.run.id)
        except Exception:
            print("CREATE_RUN FAILED:")
            traceback.print_exc()


asyncio.run(main())
