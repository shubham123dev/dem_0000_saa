from __future__ import annotations

from httpx import AsyncClient

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
NUCLEUS_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/nucleus"


async def _propose(
    client: AsyncClient,
    headers: dict[str, str],
    action_name: str,
    arguments: dict[str, str],
):
    return await client.post(
        f"{ACTION_BASE}/propose",
        headers=headers,
        json={"action_name": action_name, "arguments": arguments},
    )


async def _approve_execute(
    client: AsyncClient,
    headers: dict[str, str],
    proposal_id: str,
    key: str,
):
    approved = await client.post(
        f"{ACTION_BASE}/{proposal_id}/approve",
        headers=headers,
        json={"reason": "Approved for sandbox test"},
    )
    assert approved.status_code == 200
    executed = await client.post(
        f"{ACTION_BASE}/{proposal_id}/execute",
        headers=headers,
        json={"idempotency_key": key},
    )
    assert executed.status_code == 200
    return executed.json()["execution"]


async def test_update_account_field_is_proposed_executed_and_reflected_in_legacy_overview(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_account_field",
        {"field_name": "OrganizationName", "value": "Updated Nucleus Sandbox"},
    )
    assert proposed.status_code == 200
    proposal = proposed.json()["proposal"]
    assert proposal["changes"] == [
        {
            "field": "OrganizationName",
            "before": "Demo Enterprise Sandbox",
            "after": "Updated Nucleus Sandbox",
        }
    ]
    execution = await _approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "nucleus-account-name-001",
    )
    assert execution["outcome"] == "succeeded"

    account = (
        await client.get(f"{NUCLEUS_BASE}/account", headers=admin_headers)
    ).json()["account"]
    assert account["organization_name"] == "Updated Nucleus Sandbox"
    assert account["version"] == 2

    overview = (
        await client.get(
            f"/workplace/organizations/{ORGANIZATION_ID}/overview",
            headers=admin_headers,
        )
    ).json()
    assert overview["organization"]["display_name"] == "Updated Nucleus Sandbox"


async def test_password_and_nonallowlisted_fields_cannot_be_changed(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    for field_name in ("Password", "UserName", "OrganizationCode", "Status"):
        response = await _propose(
            client,
            admin_headers,
            "update_nucleus_organization_account_field",
            {"field_name": field_name, "value": "forbidden"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "agent_action_invalid"


async def test_nullable_account_field_can_be_cleared_and_rolled_back(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await _propose(
        client,
        admin_headers,
        "clear_nucleus_organization_account_field",
        {"field_name": "Website"},
    )
    proposal_id = proposed.json()["proposal"]["id"]
    await _approve_execute(
        client,
        admin_headers,
        proposal_id,
        "nucleus-clear-website-001",
    )
    account = (
        await client.get(f"{NUCLEUS_BASE}/account", headers=admin_headers)
    ).json()["account"]
    assert account["website"] is None

    rollback = await client.post(
        f"{ACTION_BASE}/{proposal_id}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Restore website"},
    )
    assert rollback.status_code == 200
    rollback_id = rollback.json()["proposal"]["id"]
    await _approve_execute(
        client,
        admin_headers,
        rollback_id,
        "nucleus-restore-website-001",
    )
    account = (
        await client.get(f"{NUCLEUS_BASE}/account", headers=admin_headers)
    ).json()["account"]
    assert account["website"] == "https://example.test"


async def test_category_access_grant_revoke_and_rollback(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await _propose(
        client,
        admin_headers,
        "grant_nucleus_category_access",
        {"category_id": "102", "category_sample_id": "null"},
    )
    proposal_id = proposed.json()["proposal"]["id"]
    execution = await _approve_execute(
        client,
        admin_headers,
        proposal_id,
        "nucleus-category-grant-001",
    )
    access_id = execution["result"]["after"]["access_id"]

    revoke = await _propose(
        client,
        admin_headers,
        "revoke_nucleus_category_access",
        {"access_id": str(access_id)},
    )
    revoke_id = revoke.json()["proposal"]["id"]
    await _approve_execute(
        client,
        admin_headers,
        revoke_id,
        "nucleus-category-revoke-001",
    )

    entitlements = (
        await client.get(f"{NUCLEUS_BASE}/entitlements", headers=admin_headers)
    ).json()["entitlements"]
    row = next(item for item in entitlements["category_access"] if item["access_id"] == access_id)
    assert row["is_active"] is False

    rollback = await client.post(
        f"{ACTION_BASE}/{revoke_id}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Restore category access"},
    )
    rollback_id = rollback.json()["proposal"]["id"]
    await _approve_execute(
        client,
        admin_headers,
        rollback_id,
        "nucleus-category-restore-001",
    )
    entitlements = (
        await client.get(f"{NUCLEUS_BASE}/entitlements", headers=admin_headers)
    ).json()["entitlements"]
    row = next(item for item in entitlements["category_access"] if item["access_id"] == access_id)
    assert row["is_active"] is True


async def test_report_access_supports_nullable_exact_schema_ids(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await _propose(
        client,
        admin_headers,
        "grant_nucleus_report_access",
        {
            "reports_id": "1002",
            "sample_id": "null",
            "sample_toc_id": "null",
            "speciality_id": "null",
            "executive_access": "false",
        },
    )
    assert proposed.status_code == 200
    proposal_id = proposed.json()["proposal"]["id"]
    execution = await _approve_execute(
        client,
        admin_headers,
        proposal_id,
        "nucleus-report-grant-001",
    )
    after = execution["result"]["after"]
    assert after["reports_id"] == 1002
    assert after["sample_id"] is None
    assert after["is_executive_access"] is False


async def test_special_permission_update_requires_two_non_requester_approvals(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_permissions",
        {
            "permission_id": "1",
            "cp_company_master_pharma_id": "701",
            "hc_theropetic_category_pharma_id": "702",
            "hc_theropetic_category_epidem_id": "703",
            "hc_disease_code_epidem_id": "704",
            "reports_custom_id": "705",
            "importexport_report_id": "706",
            "is_active": "true",
        },
    )
    assert proposed.status_code == 200
    proposal = proposed.json()["proposal"]
    assert proposal["risk_level"] == "high"
    assert proposal["approval_policy"]["minimum_approvals"] == 2
    assert proposal["approval_policy"]["self_approval_allowed"] is False

    self_approval = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/approve",
        headers=admin_headers,
        json={"reason": "Requester cannot self approve"},
    )
    assert self_approval.status_code == 409

    for user_id in ("usr_approval_admin_001", "usr_approval_admin_002"):
        response = await client.post(
            f"{ACTION_BASE}/{proposal['id']}/approve",
            headers={"X-Mock-User-Id": user_id},
            json={"reason": "Independent approval"},
        )
        assert response.status_code == 200

    executed = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "nucleus-permissions-update-001"},
    )
    assert executed.status_code == 200
    assert executed.json()["execution"]["outcome"] == "succeeded"
