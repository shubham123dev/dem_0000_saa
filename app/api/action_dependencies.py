from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.action_contracts import AgentActionHandler
from app.agent.action_handlers import (
    ActivateOrganizationMembershipHandler,
    AssignOrganizationSeatHandler,
    GrantOrganizationReportAccessHandler,
    InviteOrganizationUserHandler,
    RemoveOrganizationUserHandler,
    RevokeOrganizationReportAccessHandler,
    RevokeOrganizationSeatHandler,
    UpdateOrganizationContactEmailHandler,
    UpdateOrganizationMemberRoleHandler,
)
from app.agent.action_registry import AgentActionRegistry
from app.api.dependencies import (
    MockOrganizationApiDep,
    SessionDep,
    get_audit_repository,
    get_user_repository,
)
from app.permissions.permission_service import PermissionService
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services.agent_action_reconciliation_service import AgentActionReconciliationService
from app.services.agent_action_service import AgentActionService
from app.services.operational_resource_service import OperationalResourceService
from app.services.stale_safe_agent_action_service import StaleSafeAgentActionService


def get_agent_action_repository(session: SessionDep) -> AgentActionRepository:
    return AgentActionRepository(session)


def get_agent_action_registry() -> AgentActionRegistry:
    return AgentActionRegistry()


def get_agent_action_handlers(
    api: MockOrganizationApiDep,
    session: SessionDep,
) -> dict[str, AgentActionHandler]:
    organization_gateway = MockOrganizationApiAdapter(api)
    resources = OperationalResourceService(session)
    return {
        "update_organization_contact_email": UpdateOrganizationContactEmailHandler(organization_gateway),
        "invite_organization_user": InviteOrganizationUserHandler(resources),
        "activate_organization_membership": ActivateOrganizationMembershipHandler(resources),
        "update_organization_member_role": UpdateOrganizationMemberRoleHandler(resources),
        "remove_organization_user": RemoveOrganizationUserHandler(resources),
        "assign_organization_seat": AssignOrganizationSeatHandler(resources),
        "revoke_organization_seat": RevokeOrganizationSeatHandler(resources),
        "grant_organization_report_access": GrantOrganizationReportAccessHandler(resources),
        "revoke_organization_report_access": RevokeOrganizationReportAccessHandler(resources),
    }


def get_agent_action_service(
    api: MockOrganizationApiDep,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],
    action_repository: Annotated[AgentActionRepository, Depends(get_agent_action_repository)],
    action_registry: Annotated[AgentActionRegistry, Depends(get_agent_action_registry)],
    action_handlers: Annotated[dict[str, AgentActionHandler], Depends(get_agent_action_handlers)],
) -> AgentActionService:
    return StaleSafeAgentActionService(
        organization_gateway=MockOrganizationApiAdapter(api),
        permission_service=PermissionService(user_repository),
        action_repository=action_repository,
        audit_repository=audit_repository,
        action_registry=action_registry,
        action_handlers=action_handlers,
    )


def get_agent_action_reconciliation_service(
    action_service: Annotated[AgentActionService, Depends(get_agent_action_service)],
) -> AgentActionReconciliationService:
    return AgentActionReconciliationService(action_service)


AgentActionServiceDep = Annotated[AgentActionService, Depends(get_agent_action_service)]
AgentActionReconciliationServiceDep = Annotated[
    AgentActionReconciliationService,
    Depends(get_agent_action_reconciliation_service),
]
