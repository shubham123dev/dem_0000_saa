from __future__ import annotations

from httpx import AsyncClient

from app.core.config import get_settings
from app.repositories.hardened_agent_action_repository import HardenedAgentActionRepository

ORGANIZATION_ID = "org_sandbox_001"
PROPOSE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions/propose"


async def propose(client: AsyncClient, headers: dict[str, str], email: str):
    return await client.post(
        PROPOSE_URL,
        headers=headers,
        json={
            "action_name": "update_organization_contact_email",
            "arguments": {"contact_email": email},
        },
    )


async def fail_count(*args, **kwargs):
    raise AssertionError("limit evaluation must not run before authorization")


async def zero_count(*args, **kwargs):
    return 0


async def test_unauthorized_user_does_not_observe_organization_limit(
    client: AsyncClient,
    reader_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(HardenedAgentActionRepository, "count_pending", fail_count)
    response = await propose(client, reader_headers, "hidden-org-limit@example.test")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_unauthorized_user_does_not_observe_rate_limit(
    client: AsyncClient,
    reader_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(HardenedAgentActionRepository, "count_pending", zero_count)
    monkeypatch.setattr(
        HardenedAgentActionRepository,
        "count_recent_proposals",
        fail_count,
    )
    response = await propose(client, reader_headers, "hidden-rate-limit@example.test")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_authorized_user_receives_organization_limit_error(
    client: AsyncClient,
    admin_headers: dict[str, str],
    monkeypatch,
) -> None:
    settings = get_settings()

    async def organization_limit(*args, **kwargs):
        return settings.action_maximum_pending_per_organization

    monkeypatch.setattr(
        HardenedAgentActionRepository,
        "count_pending",
        organization_limit,
    )
    response = await propose(client, admin_headers, "visible-org-limit@example.test")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "agent_action_limit_exceeded"


async def test_authorized_user_below_limits_creates_proposal(
    client: AsyncClient,
    admin_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(HardenedAgentActionRepository, "count_pending", zero_count)
    monkeypatch.setattr(
        HardenedAgentActionRepository,
        "count_recent_proposals",
        zero_count,
    )
    response = await propose(client, admin_headers, "below-limits@example.test")
    assert response.status_code == 200
    assert response.json()["proposal"]["status"] == "pending_approval"
