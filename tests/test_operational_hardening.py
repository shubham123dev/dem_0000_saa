from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.action_models import AgentActionExecutionORM
from app.db.orm_models import AuditEventORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def propose_contact(
    client: AsyncClient,
    headers: dict[str, str],
    email: str,
):
    return await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=headers,
        json={
            "action_name": "update_organization_contact_email",
            "arguments": {"contact_email": email},
        },
    )


async def test_action_visibility_requires_management_permission(
    client: AsyncClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
) -> None:
    proposal = await propose_contact(
        client,
        admin_headers,
        "visibility@example.test",
    )
    assert proposal.status_code == 200

    denied = await client.get(ACTION_BASE_URL, headers=reader_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"

    allowed = await client.get(ACTION_BASE_URL, headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["proposals"]


async def test_action_list_supports_bounded_cursor_pagination_and_filters(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    for index in range(3):
        response = await propose_contact(
            client,
            admin_headers,
            f"pagination-{index}@example.test",
        )
        assert response.status_code == 200

    first = await client.get(
        ACTION_BASE_URL,
        headers=admin_headers,
        params={
            "limit": 2,
            "action_name": "update_organization_contact_email",
            "requested_by": "usr_admin_001",
        },
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["proposals"]) == 2
    assert first_body["next_cursor"] is not None

    second = await client.get(
        ACTION_BASE_URL,
        headers=admin_headers,
        params={
            "limit": 2,
            "action_name": "update_organization_contact_email",
            "requested_by": "usr_admin_001",
            "cursor": first_body["next_cursor"],
        },
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["proposals"]) == 1
    assert second_body["next_cursor"] is None

    first_ids = {item["id"] for item in first_body["proposals"]}
    second_ids = {item["id"] for item in second_body["proposals"]}
    assert first_ids.isdisjoint(second_ids)

    oversized = await client.get(
        ACTION_BASE_URL,
        headers=admin_headers,
        params={"limit": 101},
    )
    assert oversized.status_code == 429
    assert oversized.json()["error"]["code"] == "agent_action_limit_exceeded"


async def test_proposal_rate_limit_is_backend_owned(
    client: AsyncClient,
    admin_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "WORKPLACE_ACTION_MAXIMUM_PROPOSALS_PER_USER_PER_MINUTE",
        "2",
    )
    get_settings.cache_clear()
    try:
        assert (
            await propose_contact(client, admin_headers, "rate-1@example.test")
        ).status_code == 200
        assert (
            await propose_contact(client, admin_headers, "rate-2@example.test")
        ).status_code == 200
        limited = await propose_contact(
            client,
            admin_headers,
            "rate-3@example.test",
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "agent_action_limit_exceeded"
    finally:
        get_settings.cache_clear()


async def test_audit_replay_clears_pending_without_repeating_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposed = await propose_contact(
        client,
        admin_headers,
        "audit-replay@example.test",
    )
    proposal_id = proposed.json()["proposal"]["id"]
    assert (
        await client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/approve",
            headers=admin_headers,
            json={"reason": "Reviewed"},
        )
    ).status_code == 200
    executed = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "audit-replay-source-execution"},
    )
    assert executed.status_code == 200

    execution_row = await db_session.scalar(
        select(AgentActionExecutionORM).where(
            AgentActionExecutionORM.proposal_id == proposal_id
        )
    )
    assert execution_row is not None
    execution_row.audit_pending = True
    await db_session.commit()

    replayed = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/audit-replay",
        headers=admin_headers,
    )
    assert replayed.status_code == 200
    assert replayed.json()["execution"]["audit_pending"] is False

    await db_session.refresh(execution_row)
    assert execution_row.audit_pending is False
    assert execution_row.audit_replay_attempts == 1
    assert execution_row.audit_last_error is None
    assert execution_row.audit_last_attempt_at is not None

    replay_event = await db_session.scalar(
        select(AuditEventORM).where(
            AuditEventORM.organization_id == ORGANIZATION_ID,
            AuditEventORM.event_type == "agent_action_audit_replayed",
        )
    )
    assert replay_event is not None
    assert replay_event.details_json["proposal_id"] == proposal_id


async def test_detailed_readiness_reports_latest_schema_without_secrets(
    client: AsyncClient,
) -> None:
    response = await client.get("/ready/details")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert body["checks"]["database_connected"] is True
    assert body["checks"]["registry_handler_parity"] is True
    assert body["checks"]["proposal_resource_preconditions_supported"] is True
    assert body["checks"]["nucleus_admin_sidecars_supported"] is True
    assert body["checks"]["nucleus_admin_permissions_seeded"] is True
    assert body["checks"]["workplace_resource_runtime_supported"] is True
    assert body["checks"]["workplace_resource_permissions_seeded"] is True
    assert body["checks"]["workflow_schema_supported"] is True
    assert body["checks"]["workplace_workflow_permission_seeded"] is True
    assert body["checks"]["internal_rollback_hidden_from_model"] is True
    assert body["checks"]["agent_resource_tools_registered"] is True
    assert body["checks"]["workplace_operation_routes_valid"] is True
    assert body["checks"]["action_management_permissions_seeded"] is True
    assert body["migration"]["expected"] == "0018_replace_local_users"
    assert body["actions"] == {"registered": 43, "handlers": 43}
    assert body["read_tools"] == {"registered": 20}
    assert body["limits"]["maximum_page_size"] >= 1
    response_text = response.text.lower()
    assert "api_key" not in response_text
    assert "database_url" not in response_text
    assert "sqlite" not in response_text
