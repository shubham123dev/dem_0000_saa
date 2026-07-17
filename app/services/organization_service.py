"""Organization service: orchestrates the Step 0 read-only tools."""

from __future__ import annotations

from app.adapters.organization.contract import OrganizationApiGateway
from app.core.errors import OrganizationSuspendedError, ProductionAccessBlockedError
from app.domain.enums import Environment, OrganizationStatus, Permission
from app.domain.models import (
    AuditEvent,
    OrganizationMember,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
    User,
)
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.schemas.permission import AccessContext


class OrganizationService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationApiGateway,
        permission_service: Permission