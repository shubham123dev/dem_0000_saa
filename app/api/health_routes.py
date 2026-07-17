"""Health, readiness, and capability routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.agent.action_registry import AgentActionRegistry
from app.api.action_dependencies import AgentActionServiceDep
from app.api.dependencies import SessionDep
from app.core.config import get_settings
from app.db.action_models import AgentActionExecutionORM
from app.db.orm_models import RolePermissionORM
from app.domain.enums import Permission, Role
from app.schemas.organization import CapabilityActionOut, CapabilitiesResponse

router = APIRouter(tags=["health"])
EXPECTED_MIGRATION_HEAD = "0010_add_organization_overview"


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

    registry_names = {
        definition.name for definition in AgentActionRegistry().list_definitions()
    }
    handler_names = set(action_service._action_handlers)

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
        "registry_handler_parity": registry_names == handler_names,
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
