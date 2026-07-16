"""Framework-agnostic domain models.

These dataclasses represent domain state passed between the persistence,
adapter, service, and API layers. Keeping them independent of both the ORM and
the Pydantic API schemas lets the adapter contract stay stable when the mock
database is later replaced by the real Nucleus organization API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import Environment, EmployeeStatus, OrganizationStatus


@dataclass(frozen=True)
class OrganizationProfile:
    """The exact organization state returned by an OrganizationAdapter."""

    id: str
    display_name: str
    legal_name: str | None
    contact_email: str | None
    environment: Environment
    status: OrganizationStatus
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class Employee:
    """An authenticated mock employee resolved from the sandbox database."""

    id: str
    display_name: str
    email: str
    status: EmployeeStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == EmployeeStatus.ACTIVE


@dataclass(frozen=True)
class AuditEvent:
    """An append-only record of a read (or, in later steps, write) action."""

    id: str
    actor_employee_id: str
    organization_id: str
    event_type: str
    operation: str
    outcome: str
    resource_type: str
    resource_id: str
    details_json: dict | None
    created_at: datetime | None = None
