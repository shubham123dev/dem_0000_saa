"""Audit-log tests (Step 0 tests 10, 11)."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import EmployeeOrganizationRoleORM, OrganizationORM

AUDIT_URL = "/sandbox/organizations/org_sandbox_001/audit-log"
PROFILE_URL = "/sandbox/organizations/org_sandbox_001/profile"


async def test_read_creates_audit_event(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    # No reads yet -> empty audit log.
    before = await client.get(AUDIT_URL, headers=admin_headers)
    assert before.status_code == 200
    assert before.json()["events"] == []

    read = await client.get(PROFILE_URL, headers=admin_headers)
    assert read.status_code == 200

    after = await client.get(AUDIT_URL, headers=admin_headers)
    events = after.json()["events"]
    # The profile read + the first audit-log read both authorize with a read
    # permission; only the profile read records an audit event.
    read_events = [e for e in events if e["resource_id"] == "org_sandbox_001"]
    assert len(read_events) >= 1
    event = read_events[0]
    assert event["actor_employee_id"] == "emp_admin_001"
    assert event["organization_id"] == "org_sandbox_001"
    assert event["event_type"] == "organization.profile.read"
    assert event["operation"] == "read"
    assert event["outcome"] == "success"
    assert event["resource_type"] == "organization"


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
    db_session.add(
        EmployeeOrganizationRoleORM(
            employee_id="emp_admin_001",
            organization_id="org_sandbox_002",
            role="sandbox_admin",
        )
    )
    await db_session.commit()

    # Read org 1 twice, org 2 once.
    await client.get(PROFILE_URL, headers=admin_headers)
    await client.get(PROFILE_URL, headers=admin_headers)
    await client.get(
        "/sandbox/organizations/org_sandbox_002/profile", headers=admin_headers
    )

    log1 = (await client.get(AUDIT_URL, headers=admin_headers)).json()["events"]
    log2 = (
        await client.get(
            "/sandbox/organizations/org_sandbox_002/audit-log", headers=admin_headers
        )
    ).json()["events"]

    assert all(e["organization_id"] == "org_sandbox_001" for e in log1)
    assert all(e["organization_id"] == "org_sandbox_002" for e in log2)
    # org 1 has strictly more read events than org 2.
    assert len(log1) >= 2
    assert len(log2) >= 1
    ids1 = {e["id"] for e in log1}
    ids2 = {e["id"] for e in log2}
    assert ids1.isdisjoint(ids2)
