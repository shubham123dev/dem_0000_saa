"""FastAPI application entrypoint for the Step 0 sandbox Workplace Agent.

Wires the consistent error contract, per-request request ids, and the read-only
Step 0 routers. No LLM planning, write actions, or production integration are
present. The raw mock Nucleus API is mounted only when explicitly enabled in a
sandbox environment.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from app.api import health_routes, workplace_routes
from app.core.config import get_settings
from app.core.errors import REQUEST_ID_HEADER, register_exception_handlers
from app.mock_api import routes as mock_api_routes


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.0.1",
        description=(
            "DBMR Workplace Agent — Step 0 contract-first, read-only sandbox "
            "foundation. Sandbox-only; production access is out of scope."
        ),
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(workplace_routes.router)

    # The raw mock surface represents the future Nucleus system of record. It is
    # intentionally local/sandbox-only and is never mounted merely because the
    # application happens to have the mock adapter available.
    if settings.is_sandbox and settings.enable_raw_mock_api:
        app.include_router(mock_api_routes.router)

    return app


app = create_app()
