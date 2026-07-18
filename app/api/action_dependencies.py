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
from app.agent.workplace_resource_handlers import WorkplaceResourceActionHandler
from app.agent.workflow_action_handlers import (
    ApplyOrganizationAccessPackageWorkflowHandler,
    OffboardOrganizationUserWorkflowHandler,
    OnboardOrganizationUserWorkflowHandler,
    QuerySelectedBulkUpdateWorkflowHandler,
    RestoreWorkplaceResourceSnapshotsHandler,
)
from app.agent.nucleus_admin_action_handlers import (
    COMPANY_PROFILE_ACCESS,
    DRUG_ACCESS,
    INDICATION_ACCESS,
    MARKET_ACCESS,
    NucleusOrganizationLifecycleHandler,
    GrantNucleusManagedAccessHandler,
    RevokeNucleusManagedAccessHandler,
    UpdateNucleusOrganizationLicenseHandler,
    UpdateNucleusOrganizationUsernameHandler,
)
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
from app.repositories.nucleus_actor_mapping_repository import (
    NucleusActorMappingRepository,
)
from app.repositories.nucleus_administration_projection_repository import (
    NucleusAdministrationProjectionRepository,
)
from app.repositories.nucleus_administration_repository import (
    NucleusAdministrationRepository,
)
from app.repositories.hardened_agent_action_repository import (
    HardenedAgentActionRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.agent_action_reconciliation_service import AgentActionReconciliationService
from app.services.operational_resource_service import OperationalResourceService
from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService
from app.workplace_resources.registry import WorkplaceResourceRegistry
from app.workplace_resources.service import WorkplaceResourceService
from app.workplace_resources.workflows import WorkplaceWorkflowService


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
    nucleus_admin = NucleusAdministrationRepository(session)
    nucleus_projections = NucleusAdministrationProjectionRepository(session)
    workplace_resources = WorkplaceResourceService(
        session, WorkplaceResourceRegistry()
    )
    workplace_workflows = WorkplaceWorkflowService(
        session, WorkplaceResourceRegistry()
    )
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
        "update_nucleus_organization_username": (
            UpdateNucleusOrganizationUsernameHandler(nucleus_admin)
        ),
        "update_nucleus_organization_license": (
            UpdateNucleusOrganizationLicenseHandler(
                nucleus_admin, nucleus_projections
            )
        ),
        "approve_nucleus_organization_account": (
            NucleusOrganizationLifecycleHandler(
                nucleus_admin, nucleus_projections, mode="approve"
            )
        ),
        "reject_nucleus_organization_account": (
            NucleusOrganizationLifecycleHandler(
                nucleus_admin, nucleus_projections, mode="reject"
            )
        ),
        "activate_nucleus_organization_account": (
            NucleusOrganizationLifecycleHandler(
                nucleus_admin, nucleus_projections, mode="activate"
            )
        ),
        "deactivate_nucleus_organization_account": (
            NucleusOrganizationLifecycleHandler(
                nucleus_admin, nucleus_projections, mode="deactivate"
            )
        ),
        "grant_nucleus_company_profile_access": (
            GrantNucleusManagedAccessHandler(
                nucleus_admin, COMPANY_PROFILE_ACCESS
            )
        ),
        "revoke_nucleus_company_profile_access": (
            RevokeNucleusManagedAccessHandler(
                nucleus_admin, COMPANY_PROFILE_ACCESS
            )
        ),
        "grant_nucleus_drug_access": GrantNucleusManagedAccessHandler(
            nucleus_admin, DRUG_ACCESS
        ),
        "revoke_nucleus_drug_access": RevokeNucleusManagedAccessHandler(
            nucleus_admin, DRUG_ACCESS
        ),
        "grant_nucleus_indication_access": GrantNucleusManagedAccessHandler(
            nucleus_admin, INDICATION_ACCESS
        ),
        "revoke_nucleus_indication_access": RevokeNucleusManagedAccessHandler(
            nucleus_admin, INDICATION_ACCESS
        ),
        "grant_nucleus_market_access": GrantNucleusManagedAccessHandler(
            nucleus_admin, MARKET_ACCESS
        ),
        "revoke_nucleus_market_access": RevokeNucleusManagedAccessHandler(
            nucleus_admin, MARKET_ACCESS
        ),
        "create_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "create"),
        "update_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "update"),
        "clear_workplace_resource_fields": WorkplaceResourceActionHandler(workplace_resources, "clear"),
        "activate_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "activate"),
        "deactivate_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "deactivate"),
        "delete_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "delete"),
        "restore_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "restore"),
        "bulk_update_workplace_resources": WorkplaceResourceActionHandler(workplace_resources, "bulk_update"),
        "bulk_update_workplace_resources_by_query": (
            QuerySelectedBulkUpdateWorkflowHandler(workplace_workflows)
        ),
        "onboard_organization_user": (
            OnboardOrganizationUserWorkflowHandler(workplace_workflows)
        ),
        "offboard_organization_user": (
            OffboardOrganizationUserWorkflowHandler(workplace_workflows)
        ),
        "apply_organization_access_package": (
            ApplyOrganizationAccessPackageWorkflowHandler(workplace_workflows)
        ),
        "restore_workplace_resource_snapshots": (
            RestoreWorkplaceResourceSnapshotsHandler(workplace_workflows)
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
    session: SessionDep,
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
        nucleus_actor_mapping_repository=NucleusActorMappingRepository(session),
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
