"""Audit repository: append-only writes and organization-scoped reads."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import AuditEventORM
from app.domain.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        actor_employee_id: str,
        organization_id: str,
        event_type: str,
        operation: str,
        outcome: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append a new audit event. Audit rows are never updated or deleted."""

        row = AuditEventORM(
            id=uuid.uuid4().hex,
            actor_employee_id=actor_employee_id,
            organization_id=organization_id,
            event_type=event_type,
            operation=operation,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=details,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def list_for_organization(self, organization_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEventORM)
            .where(AuditEventORM.organization_id == organization_id)
            .order_by(AuditEventORM.created_at.asc(), AuditEventORM.id.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: AuditEventORM) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            actor_employee_id=row.actor_employee_id,
            organization_id=row.organization_id,
            event_type=row.event_type,
            operation=row.operation,
            outcome=row.outcome,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            details_json=row.details_json,
            created_at=row.created_at,
        )
