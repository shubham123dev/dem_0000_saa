"""End-to-end organization overview vertical-slice tests."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    AuditEventORM,
    OrganizationMembershipORM,
    OrganizationORM,
)

ORGANIZATION_ID = "org_sandbox_001"
OVERVIEW_URL = f"/workplace/organizations/{ORGANIZATION_ID}/overview"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


def assert_expected_overview(body: dict) -> None:
    assert body["organization"] == {
        "id": ORGANIZATION_ID,
        "display_name": "Demo Enterprise Sandbox",
        "legal_name": "Demo Enterprise Private Limited",
        "contact_email": "operations@example.test",
        "environment": "sandbox",
        "status": "active",
        "version": 1,
        "organization_type": "organization",
        "renewal_date": "2026-11-26",
        "workspace_status": "healthy",
    }
    assert body["metrics"] == {
        "licensed_modules": 2,
        "available_areas": 9,
        "organization_logins": 1,
        "workspace_health_percent": 98,
    }
    assert body["overview_version"] == 1
    assert body["overview_updated_at"] is not None
    assert body["generated_at"] is not None


async def propose_contact_email(
    client: AsyncClient,
    headers: dict[str, str],
    contact_email: str,
):
    return await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": contact_email,
        },
    )


async def test_admin_can_read_complete_overview(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(OVERVIEW_URL, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert_expected_overview(body)
    assert body["access"] == {
        "user_id": "usr_admin_001",
        "permission": "organization.profile.read",
    }


async def test_reader_can_read_overview_without_a_seat_requirement(
    client: AsyncClient,
    unseated_headers: dict[str, str],
) -> None:
    response = await client.get(OVERVIEW_URL, headers=unseated_headers)
    assert response.status_code == 200
    assert response.json()["access"]["user_id"] == "usr_member_003"


async def test_overview_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(OVERVIEW_URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_outsider_cannot_read_overview(
    client: AsyncClient,
    outsider_headers: dict[str, str],
) -> None:
    response = await client.get(OVERVIEW_URL, headers=outsider_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "organization_access_denied"


async def test_unknown_organization_overview_returns_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/workplace/organizations/org_missing/overview",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"


async def test_production_overview_is_blocked_before_details_are_returned(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        OrganizationORM(
            id="org_prod_overview",
            display_name="Production Organization",
            legal_name=None,
            contact_email=None,
            environment="production",
            status="active",
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        OrganizationMembershipORM(
            organization_id="org_prod_overview",
            user_id="usr_admin_001",
            role="sandbox_admin",
            membership_status="active",
            joined_at=now,
        )
    )
    await db_session.commit()

    response = await client.get(
        "/workplace/organizations/org_prod_overview/overview",
        headers=admin_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "production_access_blocked"


async def test_overview_read_is_audited(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(OVERVIEW_URL, headers=admin_headers)
    assert response.status_code == 200

    event = await db_session.scalar(
        select(AuditEventORM)
        .where(
            AuditEventORM.organization_id == ORGANIZATION_ID,
            AuditEventORM.event_type == "organization.overview.read",
        )
        .order_by(AuditEventORM.created_at.desc())
    )
    assert event is not None
    assert event.actor_user_id == "usr_admin_001"
    assert event.resource_type == "organization_overview"
    assert event.details_json == {
        "permission": "organization.profile.read",
        "tool": "get_organization_overview",
        "licensed_modules": 2,
        "available_areas": 9,
        "organization_logins": 1,
        "workspace_health_percent": 98,
    }


async def test_approved_contact_change_is_visible_in_overview(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await propose_contact_email(
        client,
        admin_headers,
        "overview.admin@example.test",
    )
    assert proposed.status_code == 200
    proposal_id = proposed.json()["proposal"]["id"]

    approved = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved for overview verification"},
    )
    assert approved.status_code == 200

    executed = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "overview-contact-change-001"},
    )
    assert executed.status_code == 200
    assert executed.json()["execution"]["outcome"] == "succeeded"

    overview = await client.get(OVERVIEW_URL, headers=admin_headers)
    assert overview.status_code == 200
    assert (
        overview.json()["organization"]["contact_email"]
        == "overview.admin@example.test"
    )
    assert overview.json()["organization"]["version"] == 2


async def test_rejected_contact_change_never_changes_overview(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposed = await propose_contact_email(
        client,
        admin_headers,
        "rejected.overview@example.test",
    )
    proposal_id = proposed.json()["proposal"]["id"]

    rejected = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/reject",
        headers=admin_headers,
        json={"reason": "Do not apply"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["approval"]["decision"] == "rejected"

    overview = await client.get(OVERVIEW_URL, headers=admin_headers)
    assert overview.status_code == 200
    assert (
        overview.json()["organization"]["contact_email"]
        == "operations@example.test"
    )
    assert overview.json()["organization"]["version"] == 1
