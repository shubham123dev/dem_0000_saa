from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.agent.action_contracts import AgentActionHandler
from app.agent.action_registry import AgentActionRegistry
from app.api.action_dependencies import (
    AgentActionServiceDep,
    get_agent_action_handlers,
    get_agent_action_registry,
)
from app.api.dependencies import SessionDep, get_user_repository
from app.permissions.permission_service import PermissionService
from app.repositories.action_control_repository import ActionControlRepository
from app.repositories.user_repository import UserRepository
from app.services.action_control_service import ActionControlService


def get_action_control_repository(session: SessionDep) -> ActionControlRepository:
    return ActionControlRepository(session)


def get_action_control_service(
    action_service: AgentActionServiceDep,
    action_registry: Annotated[
        AgentActionRegistry,
        Depends(get_agent_action_registry),
    ],
    action_handlers: Annotated[
        dict[str, AgentActionHandler],
        Depends(get_agent_action_handlers),
    ],
    user_repository: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
    repository: Annotated[
        ActionControlRepository,
        Depends(get_action_control_repository),
    ],
) -> ActionControlService:
    return ActionControlService(
        action_service=action_service,
        action_registry=action_registry,
        action_handlers=action_handlers,
        permission_service=PermissionService(user_repository),
        repository=repository,
    )


ActionControlRepositoryDep = Annotated[
    ActionControlRepository,
    Depends(get_action_control_repository),
]
ActionControlServiceDep = Annotated[
    ActionControlService,
    Depends(get_action_control_service),
]
