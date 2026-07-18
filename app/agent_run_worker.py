from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.services.agent_run_worker import AgentRunCoordinator


async def _main() -> None:
    settings = get_settings()
    coordinator = AgentRunCoordinator(
        get_sessionmaker(),
        poll_seconds=settings.agent_run_poll_seconds,
        lease_seconds=settings.agent_run_lease_seconds,
        lease_renew_seconds=settings.agent_run_lease_renew_seconds,
    )
    await coordinator.start()
    try:
        await asyncio.Event().wait()
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(_main())
