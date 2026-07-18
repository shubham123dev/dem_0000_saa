from __future__ import annotations

from app.agent.run_contracts import (
    AgentRunActivitySink,
    AgentRunCancelled,
    AgentRunStage,
)
from app.repositories.agent_run_repository import AgentRunRepository


class DatabaseAgentRunActivitySink(AgentRunActivitySink):
    def __init__(self, repository: AgentRunRepository, run_id: str) -> None:
        self._repository = repository
        self._run_id = run_id
        self._last: tuple[str, str] | None = None

    async def emit(self, *, stage: AgentRunStage, message: str) -> None:
        current = (stage, message)
        if current == self._last:
            return
        self._last = current
        await self._repository.append_event(
            run_id=self._run_id,
            event_type="activity.updated",
            stage=stage,
            message=message,
            payload=None,
            terminal=False,
        )

    async def checkpoint(self) -> None:
        if await self._repository.is_cancellation_requested(self._run_id):
            raise AgentRunCancelled()
