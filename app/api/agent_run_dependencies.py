from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.agent_dependencies import (
    get_agent_authorization_preflight_service,
)
from app.api.dependencies import SessionDep
from app.repositories.agent_run_repository import AgentRunRepository
from app.services.agent_preflight_service import AgentAuthorizationPreflightService
from app.services.agent_run_service import AgentRunService


def get_agent_run_repository(session: SessionDep) -> AgentRunRepository:
    return AgentRunRepository(session)


def get_agent_run_service(
    repository: Annotated[
        AgentRunRepository, Depends(get_agent_run_repository)
    ],
    preflight_service: Annotated[
        AgentAuthorizationPreflightService,
        Depends(get_agent_authorization_preflight_service),
    ],
) -> AgentRunService:
    return AgentRunService(repository, preflight_service)


AgentRunRepositoryDep = Annotated[
    AgentRunRepository, Depends(get_agent_run_repository)
]
AgentRunServiceDep = Annotated[AgentRunService, Depends(get_agent_run_service)]
