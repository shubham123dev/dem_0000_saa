"""Health, readiness, and capability routes (no authentication required)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import SessionDep
from app.core.config import get_settings
from app.schemas.organization import CapabilitiesResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "healthy"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    """Readiness probe: verifies database connectivity."""

    await session.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "database": "connected",
        "environment": get_settings().environment,
    }


@router.get("/workplace/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    """Advertise Step 0 capabilities: one read tool, zero write tools."""

    return CapabilitiesResponse()
