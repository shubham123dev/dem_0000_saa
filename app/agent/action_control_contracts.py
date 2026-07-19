from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class AgentActionExecutionActivitySink(Protocol):
    async def emit(
        self,
        *,
        event_type: str,
        stage: str,
        message: str,
        payload: dict[str, Any] | None = None,
        terminal: bool = False,
        dedupe_key: str | None = None,
    ) -> None: ...


class NullAgentActionExecutionActivitySink:
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
        del event_type, stage, message, payload, terminal, dedupe_key


@dataclass(frozen=True)
class AgentActionExecutionEventRecord:
    id: str
    proposal_id: str
    sequence: int
    event_type: str
    stage: str
    safe_message: str
    safe_payload: dict[str, Any] | None
    terminal: bool
    created_at: datetime


@dataclass(frozen=True)
class AgentActionAllowedOperations:
    approve: bool
    reject: bool
    cancel: bool
    execute: bool
    reconcile: bool
    create_rollback: bool


def humanize_identifier(value: str) -> str:
    normalized = " ".join(
        part for part in value.replace(".", "_").replace("-", "_").split("_") if part
    )
    return normalized[:1].upper() + normalized[1:] if normalized else "Action"


def safe_value_summary(value: Any, *, limit: int = 180) -> str:
    if value is None or value == "":
        return "Not set"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        compact = " ".join(value.split())
        return compact if len(compact) <= limit else compact[: limit - 1] + "…"
    if isinstance(value, (list, tuple, set)):
        return f"{len(value)} item{'s' if len(value) != 1 else ''}"
    return "Structured value"
