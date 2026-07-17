"""FastAPI application entrypoint for the sandbox Workplace Agent."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from app import __version__
from app.api import action_routes, agent_routes, health_routes, workplace_routes
from app.core.config import get_settings
from app.core.errors import REQUEST_ID_HEADER, register_exception_handlers
from app.mock_api import routes as mock_api_routes


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
    application.include_router(workplace_routes.router)
    application.include_router(agent_routes.router)
    application.include_router(action_routes.router)

    if settings.is_sandbox and settings.enable_raw_mock_api:
        application.include_router(mock_api_routes.router)

    return application


app = create_app()
