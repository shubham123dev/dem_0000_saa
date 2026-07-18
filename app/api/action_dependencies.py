from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.agent.action_contracts import AgentActionHandler
from app.agent.action_handlers import (
    ActivateOrganizationMembershipHandler,
    AssignOrganizationSeatHandler,
    GrantOrganizationReportAccessHandler,
    InviteOrganizationUserHandler,
    RemoveOrganizationUserHandler,
    RevokeOrganizationReportAccessHandler,
    RevokeOrganizationSeatHandler,
    UpdateOrganizationMemberRoleHandler,
)
from app.agent.action_registry import AgentActionRegistry
from app.agent.nucleus_action_handlers import (
    ClearNucleusOrganizationAccountFieldHandler,
    GrantNucleusCategoryAccessHandler,
    GrantNucleusReportAccessHandler,
    RevokeNucleusCategoryAccessHandler,
    RevokeNucleusReportAccessHandler,
    UpdateNucleusOrganizationAccountFieldHandler,
    UpdateNucleusOrganizationPermissionsHandler,
    UpdateOrganizationContactEmailBridgeHandler,
)
from app.api.dependencies import (
    NucleusOrganizationGatewayDep,
    OrganizationGatewayDep,
    SessionDep,
    VersionedOrganizationMutationGatewayDep,
    get_audit_repository,
    get_user_repository,
)
from app.permissions.permission_service import PermissionService
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.hardened_agent_action_repository import (
    HardenedAgentActionRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.agent_action_reconciliation_service import AgentActionReconciliationService
from app.services.operational_resource_service import OperationalResourceService
from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService


def get_agent_action_repository(session: SessionDep) -> AgentActionRepository:
    return HardenedAgentActionRepository(session)


def get_agent_action_registry() -> AgentActionRegistry:
    return AgentActionRegistry()


def get_agent_action_handlers(
    session: SessionDep,
    nucleus: NucleusOrganizationGatewayDep,
    organization_mutations: VersionedOrganizationMutationGatewayDep,
) -> dict[str, AgentActionHandler]:
    resources = OperationalResourceService(session)
    return {
        "update_organization_contact_email": (
            UpdateOrganizationContactEmailBridgeHandler(
                nucleus,
                organization_mutations,
            )
        ),
        "update_nucleus_organization_account_field": (
            UpdateNucleusOrganizationAccountFieldHandler(
                nucleus,
                organization_mutations,
            )
        ),
        "clear_nucleus_organization_account_field": (
            ClearNucleusOrganizationAccountFieldHandler(
                nucleus,
                organization_mutations,
            )
        ),
        "grant_nucleus_category_access": GrantNucleusCategoryAccessHandler(nucleus),
        "revoke_nucleus_category_access": RevokeNucleusCategoryAccessHandler(nucleus),
        "grant_nucleus_report_access": GrantNucleusReportAccessHandler(nucleus),
        "revoke_nucleus_report_access": RevokeNucleusReportAccessHandler(nucleus),
        "update_nucleus_organization_permissions": (
            UpdateNucleusOrganizationPermissionsHandler(nucleus)
        ),
        "invite_organization_user": InviteOrganizationUserHandler(resources),
        "activate_organization_membership": ActivateOrganizationMembershipHandler(
            resources
        ),
        "update_organization_member_role": UpdateOrganizationMemberRoleHandler(
            resources
        ),
        "remove_organization_user": RemoveOrganizationUserHandler(resources),
        "assign_organization_seat": AssignOrganizationSeatHandler(resources),
        "revoke_organization_seat": RevokeOrganizationSeatHandler(resources),
        "grant_organization_report_access": GrantOrganizationReportAccessHandler(
            resources
        ),
        "revoke_organization_report_access": RevokeOrganizationReportAccessHandler(
            resources
        ),
    }


def get_agent_action_service(
    organization_gateway: OrganizationGatewayDep,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],
    action_repository: Annotated[
        AgentActionRepository,
        Depends(get_agent_action_repository),
    ],
    action_registry: Annotated[
        AgentActionRegistry,
        Depends(get_agent_action_registry),
    ],
    action_handlers: Annotated[
        dict[str, AgentActionHandler],
        Depends(get_agent_action_handlers),
    ],
) -> ReleaseReadyAgentActionService:
    return ReleaseReadyAgentActionService(
        organization_gateway=organization_gateway,
        permission_service=PermissionService(user_repository),
        action_repository=action_repository,
        audit_repository=audit_repository,
        action_registry=action_registry,
        action_handlers=action_handlers,
    )


def get_agent_action_reconciliation_service(
    action_service: Annotated[
        ReleaseReadyAgentActionService,
        Depends(get_agent_action_service),
    ],
) -> AgentActionReconciliationService:
    return AgentActionReconciliationService(action_service)


AgentActionServiceDep = Annotated[
    ReleaseReadyAgentActionService,
    Depends(get_agent_action_service),
]
AgentActionReconciliationServiceDep = Annotated[
    AgentActionReconciliationService,
    Depends(get_agent_action_reconciliation_service),
]
