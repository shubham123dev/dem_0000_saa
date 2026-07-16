"""Audit-log tests: reads are audited; the log is organization-scoped."""
from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationMembershipORM, OrganizationORM

AUDIT_URL = "/workplace/organizations/org_sandbox_001/audit-log"
PROFILE_URL = "/workplace/organizations/org_sandbox_001/profile"


async def test_read_creates_audit_event(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    before = await client.get(AUDIT_URL, headers=admin_headers)
    assert before.status_code == 200
    assert before.json()["events"] == []

    read = await client.get(PROFILE_URL, headers=admin_headers)
    assert read.status_code == 200

    after = await client.get(AUDIT_URL, headers=admin_headers)
    events = after.json()["events"]
    read_events = [e for e in events if e["resource_id"] == "org_sandbox_001"]
    assert len(read_events) >= 1
    event = read_events[0]
    assert event["actor_user_id"] == "usr_admin_001"
    assert event["organization_id"] == "org_sandbox_001"
    assert event["event_type"] == "organization.profile.read"
    assert event["operation"] == "read"
    assert event["outcome"] == "success"
    assert event["resource_type"] == "organization"


async def test_each_read_tool_records_its_own_event(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.get(PROFILE_URL, headers=admin_headers)
    await client.get("/workplace/organizations/org_sandbox_001/users", headers=admin_headers)
    await client.get("/workplace/organizations/org_sandbox_001/seats", headers=admin_headers)
    await client.get("/workplace/organizations/org_sandbox_001/reports", headers=admin_headers)
    await client.get(
        "/workplace/organizations/org_sandbox_001/reports/rpt_market_001/access",
        headers=admin_headers,
    )

    events = (await client.get(AUDIT_URL, headers=admin_headers)).json()["events"]
    event_types = {e["event_type"] for e in events}
    assert event_types == {
        "organization.profile.read",
        "organization.users.read",
        "organization.seats.read",
        "organization.reports.read",
        "organization.reports.access_check",
    }


async def test_audit_events_are_scoped_to_organization(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        OrganizationORM(
            id="org_sandbox_002",
            display_name="Second Sandbox",
            legal_name=None,
            contact_email=None,
            environment="sandbox",
            status="active",
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    # With SQLite FK enforcement enabled, persist the parent before the child.
    await db_session.flush()
    db_session.add(
        OrganizationMembershipORM(
            organization_id="org_sandbox_002",
            user_id="usr_admin_001",
            role="sandbox_admin",
            membership_status="active",
            joined_at=now,
        )
    )
    await db_session.commit()

    await client.get(PROFILE_URL, headers=admin_headers)
    await client.get(PROFILE_URL, headers=admin_headers)
    await client.get(
        "/workplace/organizations/org_sandbox_002/profile", headers=admin_headers
    )

    log1 = (await client.get(AUDIT_URL, headers=admin_headers)).json()["events"]
    log2 = (
        await client.get(
            "/workplace/organizations/org_sandbox_002/audit-log", headers=admin_headers
        )
    ).json()["events"]

    assert all(e["organization_id"] == "org_sandbox_001" for e in log1)
    assert all(e["organization_id"] == "org_sandbox_002" for e in log2)
    assert len(log1) >= 2
    assert len(log2) >= 1
    assert {e["id"] for e in log1}.isdisjoint({e["id"] for e in log2})
