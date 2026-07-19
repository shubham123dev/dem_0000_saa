from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from app.agent.action_errors import (
    AgentActionExecutionInProgressError,
    AgentActionIdempotencyConflictError,
    AgentActionReconciliationRequiredError,
    AgentActionStaleError,
)
from app.domain.models import User
from app.services.hardened_agent_action_service import HardenedAgentActionService
from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService


async def _service_after_parent_stale(
    monkeypatch: pytest.MonkeyPatch,
    *,
    execution: SimpleNamespace | None,
) -> ReleaseReadyAgentActionService:
    parent_execute = AsyncMock(side_effect=AgentActionStaleError())
    monkeypatch.setattr(HardenedAgentActionService, "execute", parent_execute)

    service = object.__new__(ReleaseReadyAgentActionService)
    service._action_repository = SimpleNamespace(
        get_execution=AsyncMock(return_value=execution)
    )
    return service


async def test_returns_completed_idempotent_execution_after_preflight_stale_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution = SimpleNamespace(
        idempotency_key="same-key",
        outcome="succeeded",
    )
    service = await _service_after_parent_stale(
        monkeypatch,
        execution=execution,
    )

    result = await service.execute(
        user=cast(User, object()),
        organization_id="org_sandbox_001",
        proposal_id="proposal_001",
        idempotency_key="same-key",
    )

    assert result is execution


async def test_maps_active_idempotent_execution_to_in_progress_after_stale_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = await _service_after_parent_stale(
        monkeypatch,
        execution=SimpleNamespace(
            idempotency_key="same-key",
            outcome="executing",
        ),
    )

    with pytest.raises(AgentActionExecutionInProgressError):
        await service.execute(
            user=cast(User, object()),
            organization_id="org_sandbox_001",
            proposal_id="proposal_001",
            idempotency_key="same-key",
        )


async def test_maps_uncertain_idempotent_execution_to_reconciliation_after_stale_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = await _service_after_parent_stale(
        monkeypatch,
        execution=SimpleNamespace(
            idempotency_key="same-key",
            outcome="reconciliation_required",
        ),
    )

    with pytest.raises(AgentActionReconciliationRequiredError):
        await service.execute(
            user=cast(User, object()),
            organization_id="org_sandbox_001",
            proposal_id="proposal_001",
            idempotency_key="same-key",
        )


async def test_maps_different_execution_key_to_idempotency_conflict_after_stale_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = await _service_after_parent_stale(
        monkeypatch,
        execution=SimpleNamespace(
            idempotency_key="other-key",
            outcome="succeeded",
        ),
    )

    with pytest.raises(AgentActionIdempotencyConflictError):
        await service.execute(
            user=cast(User, object()),
            organization_id="org_sandbox_001",
            proposal_id="proposal_001",
            idempotency_key="same-key",
        )


@pytest.mark.parametrize(
    "execution",
    [
        None,
        SimpleNamespace(idempotency_key="same-key", outcome="failed"),
    ],
)
async def test_preserves_real_stale_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    execution: SimpleNamespace | None,
) -> None:
    service = await _service_after_parent_stale(
        monkeypatch,
        execution=execution,
    )

    with pytest.raises(AgentActionStaleError):
        await service.execute(
            user=cast(User, object()),
            organization_id="org_sandbox_001",
            proposal_id="proposal_001",
            idempotency_key="same-key",
        )
