from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_admin_models import NucleusAccessTombstoneORM
from app.db.nucleus_models import (
    NucleusOrganizationCompanyProfileAccessORM,
    NucleusOrganizationDrugAccessORM,
    NucleusOrganizationIndicationAccessORM,
    NucleusOrganizationMarketAccessORM,
)

ORGANIZATION_ID = "org_sandbox_001"
BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}

CASES = (
    (
        "company_profile",
        "revoke_nucleus_company_profile_access",
        NucleusOrganizationCompanyProfileAccessORM,
        1,
        "OrganizationCompanyProfileAccess",
    ),
    (
        "drug",
        "revoke_nucleus_drug_access",
        NucleusOrganizationDrugAccessORM,
        1,
        "OrganizationDrugAccess",
    ),
    (
        "indication",
        "revoke_nucleus_indication_access",
        NucleusOrganizationIndicationAccessORM,
        1,
        "OrganizationIndicationAccess",
    ),
    (
        "market",
        "revoke_nucleus_market_access",
        NucleusOrganizationMarketAccessORM,
        1,
        "OrganizationMarketAccess",
    ),
)


@pytest.mark.parametrize(
    "kind,action_name,orm_type,access_id,resource_type", CASES
)
async def test_revocation_is_reversible_tombstone_not_source_delete(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    kind: str,
    action_name: str,
    orm_type: type,
    access_id: int,
    resource_type: str,
) -> None:
    proposed = await client.post(
        f"{BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": action_name,
            "arguments": {"access_id": str(access_id)},
        },
    )
    assert proposed.status_code == 200, proposed.text
    proposal_id = proposed.json()["proposal"]["id"]
    for headers in (APPROVER_ONE, APPROVER_TWO):
        approved = await client.post(
            f"{BASE}/{proposal_id}/approve",
            headers=headers,
            json={"reason": f"Reviewed {kind} revocation"},
        )
        assert approved.status_code == 200, approved.text
    executed = await client.post(
        f"{BASE}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": f"revoke-{kind}-admin-001"},
    )
    assert executed.status_code == 200, executed.text

    source_row = await db_session.get(orm_type, access_id)
    tombstone = await db_session.get(
        NucleusAccessTombstoneORM,
        {"resource_type": resource_type, "access_id": access_id},
    )
    assert source_row is not None
    assert tombstone is not None
    assert tombstone.revoked_by == 1001

    rollback_response = await client.post(
        f"{BASE}/{proposal_id}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Restore exact reviewed access"},
    )
    assert rollback_response.status_code == 200, rollback_response.text
    rollback_id = rollback_response.json()["proposal"]["id"]
    rollback_approval = await client.post(
        f"{BASE}/{rollback_id}/approve",
        headers=admin_headers,
        json={"reason": "Reviewed restoration"},
    )
    assert rollback_approval.status_code == 200, rollback_approval.text
    rollback_execution = await client.post(
        f"{BASE}/{rollback_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": f"restore-{kind}-admin-001"},
    )
    assert rollback_execution.status_code == 200, rollback_execution.text
    db_session.expire_all()
    restored_tombstone = await db_session.get(
        NucleusAccessTombstoneORM,
        {"resource_type": resource_type, "access_id": access_id},
    )
    assert restored_tombstone is None
    assert await db_session.get(orm_type, access_id) is not None


async def test_grant_and_duplicate_protection(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    payload = {
        "action_name": "grant_nucleus_company_profile_access",
        "arguments": {"company_id": "999"},
    }
    proposal = await client.post(
        f"{BASE}/propose", headers=admin_headers, json=payload
    )
    assert proposal.status_code == 200, proposal.text
    proposal_id = proposal.json()["proposal"]["id"]
    approved = await client.post(
        f"{BASE}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Reviewed grant"},
    )
    assert approved.status_code == 200, approved.text
    executed = await client.post(
        f"{BASE}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "grant-company-admin-001"},
    )
    assert executed.status_code == 200, executed.text

    duplicate = await client.post(
        f"{BASE}/propose", headers=admin_headers, json=payload
    )
    assert duplicate.status_code == 422
