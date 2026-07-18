from __future__ import annotations

from httpx import AsyncClient


async def test_capabilities_publish_backend_owned_approval_policies(
    client: AsyncClient,
) -> None:
    response = await client.get("/workplace/capabilities")
    assert response.status_code == 200
    actions = {item["name"]: item for item in response.json()["write_actions"]}

    assert len(actions) == 16
    assert actions["update_organization_contact_email"]["minimum_approvals"] == 1
    assert actions["update_organization_contact_email"]["self_approval_allowed"] is True
    assert actions["update_nucleus_organization_account_field"]["minimum_approvals"] == 1
    assert actions["grant_nucleus_category_access"]["risk_level"] == "medium"
    assert actions["update_nucleus_organization_permissions"]["minimum_approvals"] == 2
    assert actions["update_nucleus_organization_permissions"]["self_approval_allowed"] is False
    assert actions["update_organization_member_role"]["minimum_approvals"] == 2
    assert actions["update_organization_member_role"]["self_approval_allowed"] is False
    assert actions["remove_organization_user"]["minimum_approvals"] == 2
    assert actions["remove_organization_user"]["self_approval_allowed"] is False


async def test_rollback_requires_successful_reversible_source(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await client.post(
        "/workplace/organizations/org_sandbox_001/agent/actions/propose",
        headers=admin_headers,
        json={
            "action_name": "activate_organization_membership",
            "arguments": {"user_id": "usr_invited_001"},
        },
    )
    proposal_id = proposed.json()["proposal"]["id"]

    before_execution = await client.post(
        f"/workplace/organizations/org_sandbox_001/agent/actions/{proposal_id}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Not executed"},
    )
    assert before_execution.status_code == 409
    assert before_execution.json()["error"]["code"] == "agent_action_rollback_unavailable"

    assert (
        await client.post(
            f"/workplace/organizations/org_sandbox_001/agent/actions/{proposal_id}/approve",
            headers=admin_headers,
            json={"reason": "Activate"},
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/workplace/organizations/org_sandbox_001/agent/actions/{proposal_id}/execute",
            headers=admin_headers,
            json={"idempotency_key": "activate-before-unsupported-rollback"},
        )
    ).status_code == 200

    unsupported = await client.post(
        f"/workplace/organizations/org_sandbox_001/agent/actions/{proposal_id}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "No safe inverse exists"},
    )
    assert unsupported.status_code == 409
    assert unsupported.json()["error"]["code"] == "agent_action_rollback_unavailable"
