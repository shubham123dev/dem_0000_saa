from __future__ import annotations

from app.agent.run_contracts import CreatedAgentRun
from app.core.errors import (
    AgentConversationBusyError,
    AgentConversationNotFoundError,
    AgentRunNotFoundError,
)
from app.domain.models import User
from app.repositories.agent_run_repository import (
    AgentConversationBusyRepositoryError,
    AgentRunRepository,
)
from app.services.agent_preflight_service import AgentAuthorizationPreflightService


class AgentRunService:
    def __init__(
        self,
        repository: AgentRunRepository,
        preflight_service: AgentAuthorizationPreflightService,
    ) -> None:
        self._repository = repository
        self._preflight_service = preflight_service

    async def _authorize(self, *, user: User, organization_id: str) -> None:
        await self._preflight_service.authorize(
            user=user,
            organization_id=organization_id,
        )

    async def create(
        self,
        *,
        user: User,
        organization_id: str,
        query: str,
        client_request_id: str,
        conversation_id: str | None,
        request_id: str | None,
    ) -> CreatedAgentRun:
        await self._authorize(user=user, organization_id=organization_id)
        try:
            return await self._repository.create_run(
                organization_id=organization_id,
                requested_by_user_id=user.id,
                query=query,
                client_request_id=client_request_id,
                conversation_id=conversation_id,
                request_id=request_id,
            )
        except AgentConversationBusyRepositoryError as exception:
            raise AgentConversationBusyError() from exception
        except LookupError as exception:
            raise AgentConversationNotFoundError() from exception

    async def conversation(
        self, *, user: User, organization_id: str, conversation_id: str
    ):
        await self._authorize(user=user, organization_id=organization_id)
        try:
            conversation = await self._repository.require_conversation(
                conversation_id=conversation_id,
                organization_id=organization_id,
                user_id=user.id,
            )
        except LookupError as exception:
            raise AgentConversationNotFoundError() from exception
        messages = await self._repository.list_messages(
            conversation_id=conversation.id
        )
        active_run = await self._repository.find_active_run(
            conversation_id=conversation.id
        )
        return conversation, messages, active_run

    async def run(self, *, user: User, organization_id: str, run_id: str):
        await self._authorize(user=user, organization_id=organization_id)
        try:
            return await self._repository.require_run(
                run_id=run_id,
                organization_id=organization_id,
                user_id=user.id,
            )
        except LookupError as exception:
            raise AgentRunNotFoundError() from exception

    async def cancel(self, *, user: User, organization_id: str, run_id: str):
        await self.run(user=user, organization_id=organization_id, run_id=run_id)
        try:
            return await self._repository.request_cancellation(run_id)
        except LookupError as exception:
            raise AgentRunNotFoundError() from exception
