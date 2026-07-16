"""Audit event API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.models import AuditEvent


class AuditEventOut(BaseModel):
    """Public representation of an append-only audit event."""

    id: str
    actor_user_id: str
    organization_id: str
    event_type: str
    operation: str
    outcome: str
    resource_type: str
    resource_id: str
    details: dict[str, Any] | None = None
    created_at: datetime | None = None

    @classmethod
    def from_domain(cls, event: AuditEvent) -> "AuditEventOut":
        return cls(
            id=event.id,
            actor_user_id=event.actor_user_id,
            organization_id=event.organization_id,
            event_type=event.event_type,
            operation=event.operation,
            outcome=event.outcome,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            details=event.details_json,
            created_at=event.created_at,
        )


class AuditLogResponse(BaseModel):
    """Response body for the audit-log endpoint."""

    organization_id: str
    events: list[AuditEventOut]
