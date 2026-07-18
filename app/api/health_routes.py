"""Health, readiness, and capability routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.agent.action_registry import AgentActionRegistry
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.api.action_dependencies import AgentActionServiceDep
from app.api.dependencies import SessionDep
from app.core.config import get_settings
from app.db.action_models import AgentActionExecutionORM
from app.db.orm_models import RolePermissionORM
from app.domain.enums import Permission, Role
from app.schemas.organization import CapabilityActionOut, CapabilitiesResponse

router = APIRouter(tags=["health"])
EXPECTED_MIGRATION_HEAD = "0014_workplace_resources"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "database": "connected",
        "environment": get_settings().environment,
    }


@router.get("/ready/details")
async def readiness_details(
    session: SessionDep,
    action_service: AgentActionServiceDep,
) -> dict:
    await session.execute(text("SELECT 1"))
    settings = get_settings()
    try:
        migration_head = await session.scalar(
            text("SELECT version_num FROM alembic_version")
        )
    except SQLAlchemyError:
        await session.rollback()
        migration_head = None

    try:
        await session.execute(
            text(
                "SELECT resource_preconditions_json, fingerprint_version "
                "FROM agent_action_proposals LIMIT 1"
            )
        )
        proposal_preconditions_supported = True
    except SQLAlchemyError:
        await session.rollback()
        proposal_preconditions_supported = False

    try:
        await session.execute(
            text(
                "SELECT workplace_user_id, nucleus_actor_id "
                "FROM nucleus_actor_mappings LIMIT 1"
            )
        )
        await session.execute(
            text(
                "SELECT resource_type, access_id "
                "FROM nucleus_access_tombstones LIMIT 1"
            )
        )
        await session.execute(
            text(
                "SELECT executed_by_user_id, nucleus_actor_id "
                "FROM agent_action_executions LIMIT 1"
            )
        )
        nucleus_admin_sidecars_supported = True
    except SQLAlchemyError:
        await session.rollback()
        nucleus_admin_sidecars_supported = False

    try:
        await session.execute(
            text(
                "SELECT id, organization_id, namespace, setting_key, "
                "version FROM workplace_settings LIMIT 1"
            )
        )
        await session.execute(
            text(
                "SELECT proposal_id, plan_json, status "
                "FROM workplace_mutation_plans LIMIT 1"
            )
        )
        await session.execute(
            text(
                "SELECT resource_type, resource_id, snapshot_hash "
                "FROM workplace_resource_snapshots LIMIT 1"
            )
        )
        workplace_resource_runtime_supported = True
    except SQLAlchemyError:
        await session.rollback()
        workplace_resource_runtime_supported = False
    registry_names = {
        definition.name for definition in AgentActionRegistry().list_definitions()
    }
    handler_names = set(action_service._action_handlers)
    read_tool_names = {
        definition.name
        for definition in ReadOnlyAgentToolRegistry().list_tool_definitions()
    }
    try:
        operation_router = WorkplaceOperationRouter()
        routed_actions = {
            route.target_name
            for route in operation_router.list_routes()
            if route.route_kind == "action"
        }
        routed_tools = {
            route.target_name
            for route in operation_router.list_routes()
            if route.route_kind == "tool"
        }
        workplace_operation_routes_valid = (
            routed_actions.issubset(registry_names)
            and routed_tools.issubset(read_tool_names)
        )
    except RuntimeError:
        workplace_operation_routes_valid = False

    management_permissions = {
        Permission.AGENT_ACTIONS_READ.value,
        Permission.AGENT_ACTIONS_APPROVE.value,
        Permission.AGENT_ACTIONS_EXECUTE.value,
        Permission.AGENT_ACTIONS_RECONCILE.value,
    }
    permission_rows = (
        await session.execute(
            select(RolePermissionORM.permission).where(
                RolePermissionORM.role == Role.SANDBOX_ADMIN.value,
                RolePermissionORM.permission.in_(management_permissions),
            )
        )
    ).scalars().all()
    configured_management_permissions = set(permission_rows)

    nucleus_admin_permissions = {
        Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE.value,
        Permission.ORGANIZATION_LICENSE_UPDATE.value,
        Permission.ORGANIZATION_LIFECYCLE_UPDATE.value,
        Permission.ORGANIZATION_ENTITLEMENTS_DELETE.value,
    }
    configured_nucleus_admin_permissions = set(
        (
            await session.execute(
                select(RolePermissionORM.permission).where(
                    RolePermissionORM.role == Role.SANDBOX_ADMIN.value,
                    RolePermissionORM.permission.in_(
                        nucleus_admin_permissions
                    ),
                )
            )
        ).scalars().all()
    )

    workplace_resource_permissions = {
        Permission.WORKPLACE_RESOURCES_CREATE.value,
        Permission.WORKPLACE_RESOURCES_UPDATE.value,
        Permission.WORKPLACE_RESOURCES_DELETE.value,
        Permission.WORKPLACE_RESOURCES_RESTORE.value,
        Permission.WORKPLACE_RESOURCES_BULK_MANAGE.value,
    }
    configured_workplace_resource_permissions = set(
        (
            await session.execute(
                select(RolePermissionORM.permission).where(
                    RolePermissionORM.role == Role.SANDBOX_ADMIN.value,
                    RolePermissionORM.permission.in_(
                        workplace_resource_permissions
                    ),
                )
            )
        ).scalars().all()
    )
    audit_pending = int(
        await session.scalar(
            select(func.count())
            .select_from(AgentActionExecutionORM)
            .where(AgentActionExecutionORM.audit_pending.is_(True))
        )
        or 0
    )

    checks = {
        "database_connected": True,
        "sandbox_environment": settings.is_sandbox,
        "migration_at_expected_head": migration_head == EXPECTED_MIGRATION_HEAD,
        "proposal_resource_preconditions_supported": proposal_preconditions_supported,
        "nucleus_admin_sidecars_supported": nucleus_admin_sidecars_supported,
        "workplace_resource_runtime_supported": (
            workplace_resource_runtime_supported
        ),
        "workplace_resource_permissions_seeded": (
            configured_workplace_resource_permissions
            == workplace_resource_permissions
        ),
        "nucleus_admin_permissions_seeded": (
            configured_nucleus_admin_permissions == nucleus_admin_permissions
        ),
        "registry_handler_parity": registry_names == handler_names,
        "agent_resource_tools_registered": len(read_tool_names) == 16,
        "workplace_operation_routes_valid": workplace_operation_routes_valid,
        "action_management_permissions_seeded": (
            configured_management_permissions == management_permissions
        ),
    }
    return {
        "status": "ready" if all(checks.values()) else "not_ready",
        "checks": checks,
        "migration": {
            "current": migration_head,
            "expected": EXPECTED_MIGRATION_HEAD,
        },
        "actions": {
            "registered": len(registry_names),
            "handlers": len(handler_names),
        },
        "read_tools": {
            "registered": len(read_tool_names),
        },
        "audit": {
            "pending_replay": audit_pending,
            "maximum_replay_attempts": settings.action_maximum_audit_replay_attempts,
        },
        "limits": {
            "pending_per_organization": settings.action_maximum_pending_per_organization,
            "pending_per_user": settings.action_maximum_pending_per_user,
            "proposals_per_user_per_minute": settings.action_maximum_proposals_per_user_per_minute,
            "maximum_page_size": settings.action_maximum_page_size,
            "maximum_reconciliation_attempts": settings.action_maximum_reconciliation_attempts,
        },
        "model": {
            "provider_configured": bool(settings.agent_model_provider),
            "credential_configured": bool(settings.agent_model_api_key),
            "model_name": settings.agent_model_name,
        },
        "raw_mock_api_enabled": settings.enable_raw_mock_api,
    }


@router.get("/workplace/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    definitions = AgentActionRegistry().list_definitions()
    return CapabilitiesResponse(
        write_tools=tuple(definition.name for definition in definitions),
        write_actions=tuple(
            CapabilityActionOut(
                name=definition.name,
                required_arguments=definition.required_argument_names,
                risk_level=definition.risk_level,
                requires_approval=definition.requires_approval,
                supports_dry_run=definition.supports_dry_run,
                minimum_approvals=definition.approval_policy.minimum_approvals,
                self_approval_allowed=definition.approval_policy.self_approval_allowed,
            )
            for definition in definitions
        ),
    )
