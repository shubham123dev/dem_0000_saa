"""FastAPI application entrypoint for the sandbox Workplace Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request

from app import __version__
from app.adapters.user.provider import dispose_user_directory
from app.api import (
    action_conversation_control_routes,
    action_control_routes,
    action_routes,
    agent_routes,
    agent_run_routes,
    auth_routes,
    conversation_routes,
    health_routes,
    nucleus_routes,
    workplace_resource_routes,
    workplace_routes,
)
from app.core.config import get_settings
from app.core.errors import REQUEST_ID_HEADER, register_exception_handlers
from app.db.session import get_sessionmaker
from app.mock_api import routes as mock_api_routes
from app.services.agent_run_worker import AgentRunCoordinator


@asynccontextmanager
async def _lifespan(application: FastAPI):
    settings = get_settings()

    # Ensure all ORM tables (e.g. user_sessions) exist in local sandbox database
    import app.db.orm_models  # noqa: F401
    from app.db.base import Base
    from app.db.session import get_engine
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import logging
    logger = logging.getLogger("uvicorn")
    if settings.nucleus_user_database_url:
        logger.info("Nucleus SQL Server User Directory configured for dbmr_Database_Nucleus.dbo.Test_user1")

    coordinator = AgentRunCoordinator(
        get_sessionmaker(),
        poll_seconds=settings.agent_run_poll_seconds,
        lease_seconds=settings.agent_run_lease_seconds,
        lease_renew_seconds=settings.agent_run_lease_renew_seconds,
    )
    application.state.agent_run_coordinator = coordinator
    await coordinator.start()
    try:
        yield
    finally:
        await coordinator.stop()
        await dispose_user_directory()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "DBMR Workplace Agent sandbox with stable organization reads, "
            "grounded chat planning and explicit approval-gated actions. "
            "Production organization access is blocked."
        ),
        lifespan=_lifespan,
    )

    @application.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    register_exception_handlers(application)
    application.include_router(health_routes.router)
    application.include_router(auth_routes.router)
    application.include_router(workplace_routes.router)
    application.include_router(nucleus_routes.router)
    application.include_router(workplace_resource_routes.router)
    application.include_router(agent_routes.router)
    application.include_router(conversation_routes.router)
    application.include_router(agent_run_routes.router)
    application.include_router(action_control_routes.router)
    application.include_router(action_conversation_control_routes.router)
    application.include_router(action_routes.router)

    if settings.is_sandbox and settings.enable_raw_mock_api:
        application.include_router(mock_api_routes.router)
    return application


app = create_app()
