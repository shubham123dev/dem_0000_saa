from __future__ import annotations

from enum import Enum


class AgentActionStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    STALE = "stale"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECONCILIATION_REQUIRED = "reconciliation_required"


_ALLOWED_TRANSITIONS: dict[AgentActionStatus, frozenset[AgentActionStatus]] = {
    AgentActionStatus.PENDING_APPROVAL: frozenset(
        {
            AgentActionStatus.APPROVED,
            AgentActionStatus.REJECTED,
            AgentActionStatus.EXPIRED,
            AgentActionStatus.CANCELLED,
        }
    ),
    AgentActionStatus.APPROVED: frozenset(
        {
            AgentActionStatus.EXECUTING,
            AgentActionStatus.EXPIRED,
            AgentActionStatus.CANCELLED,
            AgentActionStatus.STALE,
        }
    ),
    AgentActionStatus.EXECUTING: frozenset(
        {
            AgentActionStatus.SUCCEEDED,
            AgentActionStatus.FAILED,
            AgentActionStatus.STALE,
            AgentActionStatus.RECONCILIATION_REQUIRED,
        }
    ),
    AgentActionStatus.RECONCILIATION_REQUIRED: frozenset(
        {
            AgentActionStatus.SUCCEEDED,
            AgentActionStatus.FAILED,
        }
    ),
    AgentActionStatus.REJECTED: frozenset(),
    AgentActionStatus.EXPIRED: frozenset(),
    AgentActionStatus.CANCELLED: frozenset(),
    AgentActionStatus.STALE: frozenset(),
    AgentActionStatus.SUCCEEDED: frozenset(),
    AgentActionStatus.FAILED: frozenset(),
}


def can_transition(current: str, target: str) -> bool:
    current_status = AgentActionStatus(current)
    target_status = AgentActionStatus(target)
    return target_status in _ALLOWED_TRANSITIONS[current_status]


def require_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Invalid action transition: {current} -> {target}")
