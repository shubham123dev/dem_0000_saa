from __future__ import annotations

from typing import Any

from app.agent.action_control_contracts import AgentActionExecutionActivitySink
from app.repositories.action_control_repository import ActionControlRepository


class DatabaseActionExecutionActivitySink(AgentActionExecutionActivitySink):
    def __init__(self, repository: ActionControlRepository, proposal_id: str) -> None:
        self._repository = repository
        self._proposal_id = proposal_id

    async def emit(
        self,
        *,
        event_type: str,
        stage: str,
        message: str,
        payload: dict[str, Any] | None = None,
        terminal: bool = False,
        dedupe_key: str | None = None,
    ) -> None:
        await self._repository.append_event(
            proposal_id=self._proposal_id,
            event_type=event_type,
            stage=stage,
            message=message,
            payload=payload,
            terminal=terminal,
            dedupe_key=dedupe_key or event_type,
        )
