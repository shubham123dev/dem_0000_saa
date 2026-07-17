"""Health, readiness, and capability routes."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.agent.action_registry import AgentActionRegistry
from app.api.dependencies import SessionDep
from app.core.config import get_settings
from app.schemas.organization import CapabilityActionOut, CapabilitiesResponse

router = APIRouter(tags=["health"])


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
