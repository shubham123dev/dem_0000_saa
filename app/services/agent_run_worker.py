from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import socket
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.answer_contracts import AgentQueryCompletion
from app.agent.run_contracts import AgentRunCancelled
from app.api.action_dependencies import get_agent_action_repository
from app.agent.run_runtime import build_run_response_service
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.user_repository import UserRepository
from app.services.agent_run_activity import DatabaseAgentRunActivitySink

logger = logging.getLogger("app.agent_runs")


class AgentRunExecutor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        lease_seconds: int = 45,
        lease_renew_seconds: int = 15,
    ) -> None:
        self._session_factory = session_factory
        self._lease_seconds = lease_seconds
        self._lease_renew_seconds = lease_renew_seconds

    async def execute(self, run_id: str, worker_id: str) -> None:
        async with self._session_factory() as session:
            repository = AgentRunRepository(session)
            run = await repository.get_run_internal(run_id)
            if run is None or run.terminal:
                return
            activity = DatabaseAgentRunActivitySink(repository, run_id)
            lease_task = asyncio.create_task(
                self._renew_lease(run_id, worker_id),
                name=f"agent-run-lease-{run_id}",
            )
            try:
                existing_proposal = await get_agent_action_repository(
                    session
                ).get_proposal_by_source_agent_run_id(run_id)
                if existing_proposal is not None:
                    await repository.complete_run(
                        run_id=run_id,
                        completion=AgentQueryCompletion(
                            mode="action_proposal",
                            answer=(
                                "The requested change was prepared as a dry-run "
                                "proposal and requires explicit approval before execution."
                            ),
                            answer_source="deterministic",
                            action_proposal=existing_proposal,
                        ),
                    )
                    return
                await activity.checkpoint()
                user = await UserRepository(session).get_by_id(
                    run.requested_by_user_id
                )
                if user is None or not user.is_active:
                    await repository.fail_run(run_id, "agent_requester_unavailable")
                    return
                user_request = await repository.conversation_context(
                    conversation_id=run.conversation_id,
                    through_message_id=run.user_message_id,
                )
                response_service = build_run_response_service(
                    session, activity_sink=activity
                )
                completion = await response_service.execute(
                    user=user,
                    organization_id=run.organization_id,
                    user_request=user_request,
                    request_id=None,
                    agent_run_id=run_id,
                    activity_sink=activity,
                )
                if completion.mode != "action_proposal":
                    await activity.checkpoint()
                await repository.complete_run(
                    run_id=run_id, completion=completion
                )
            except AgentRunCancelled:
                await session.rollback()
                await repository.cancel_run(run_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Agent run failed", extra={"run_id": run_id})
                with suppress(Exception):
                    await session.rollback()
                    await repository.fail_run(run_id, "agent_run_failed")
            finally:
                lease_task.cancel()
                with suppress(asyncio.CancelledError):
                    await lease_task

    async def _renew_lease(self, run_id: str, worker_id: str) -> None:
        while True:
            await asyncio.sleep(self._lease_renew_seconds)
            async with self._session_factory() as session:
                renewed = await AgentRunRepository(session).renew_lease(
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=self._lease_seconds,
                )
                if not renewed:
                    return


class AgentRunCoordinator:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_seconds: float = 0.75,
        lease_seconds: int = 45,
        lease_renew_seconds: int = 15,
    ) -> None:
        if lease_renew_seconds >= lease_seconds:
            raise ValueError("Agent run lease renewal must be shorter than the lease")
        self._session_factory = session_factory
        self._executor = AgentRunExecutor(
            session_factory,
            lease_seconds=lease_seconds,
            lease_renew_seconds=lease_renew_seconds,
        )
        self._lease_seconds = lease_seconds
        self._poll_seconds = poll_seconds
        self._worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"
        self._wake = asyncio.Event()
        self._stopping = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(
                self._run(), name="agent-run-coordinator"
            )

    async def stop(self) -> None:
        self._stopping.set()
        self._wake.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def notify(self) -> None:
        self._wake.set()

    async def run_once(self) -> bool:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).claim_next(
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
            )
        if run is None:
            return False
        await self._executor.execute(run.id, self._worker_id)
        return True

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                processed = await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Agent run coordinator iteration failed")
                processed = False
            if processed:
                continue
            self._wake.clear()
            try:
                await asyncio.wait_for(
                    self._wake.wait(), timeout=self._poll_seconds
                )
            except TimeoutError:
                pass
