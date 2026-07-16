"""Organization profile read-flow and cross-cutting guarantees."""
from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    RolePermissionORM,
    SeatAssignmentORM,
    UserORM,
)
from app.db.seed import seed
from app.main import app

PROFILE_URL = "/workplace/organizations/org_sandbox_001/profile"
EXPECTED_ORG = {
    "id": "org_sandbox_001",
    "display_name": "Demo Enterprise Sandbox",
    "legal_name": "Demo Enterprise Private Limited",
    "contact_email": "operations@example.test",
    "environment": "sandbox",
    "status": "active",
    "version": 1,
}


async def test_admin_can_read_organization(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(PROFILE_URL, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["organization"] == EXPECTED_ORG
    assert body["access"] == {
        "user_id": "usr_admin_001",
        "permission": "organization.profile.read",
    }


async def test_reader_can_read_organization(
    client: AsyncClient, reader_headers: dict[str, str]
) -> None:
    resp = await client.get(PROFILE_URL, headers=reader_headers)
    assert resp.status_code == 200
    assert resp.json()["organization"] == EXPECTED_ORG
    assert resp.json()["access"]["user_id"] == "usr_member_001"


async def test_unknown_organization_returns_404(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/workplace/organizations/org_does_not_exist/profile", headers=admin_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "organization_not_found"


async def test_production_organization_access_is_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        OrganizationORM(
            id="org_prod_001",
            display_name="Prod Org",
            legal_name=None,
            contact_email=None,
            environment="production",
            status="active",
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    # Persist the parent first because SQLite foreign keys are deliberately on.
    await db_session.flush()
    db_session.add(
        OrganizationMembershipORM(
            organization_id="org_prod_001",
            user_id="usr_admin_001",
            role="sandbox_admin",
            membership_status="active",
            joined_at=now,
        )
    )
    await db_session.commit()

    resp = await client.get(
        "/workplace/organizations/org_prod_001/profile", headers=admin_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "production_access_blocked"


async def test_no_write_routes_exist() -> None:
    forbidden = {"POST", "PUT", "PATCH", "DELETE"}
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        assert not (methods & forbidden), (
            f"Unexpected write route {getattr(route, 'path', route)}: {methods}"
        )


async def test_seed_is_idempotent(
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> None:
    async def _counts(session: AsyncSession) -> dict[str, int]:
        async def n(model) -> int:
            return int(
                await session.scalar(select(func.count()).select_from(model)) or 0
            )

        return {
            "orgs": await n(OrganizationORM),
            "users": await n(UserORM),
            "memberships": await n(OrganizationMembershipORM),
            "pools": await n(OrganizationSeatPoolORM),
            "assignments": await n(SeatAssignmentORM),
            "reports": await n(ReportORM),
            "access": await n(OrganizationReportAccessORM),
            "role_permissions": await n(RolePermissionORM),
        }

    async with sessionmaker_() as session:
        await seed(session)
        first = await _counts(session)

    async with sessionmaker_() as session:
        await seed(session)
        second = await _counts(session)

    assert first == second
    assert first == {
        "orgs": 1,
        "users": 6,
        "memberships": 5,
        "pools": 1,
        "assignments": 3,
        "reports": 5,
        "access": 3,
        "role_permissions": 21,
    }


async def test_responses_do_not_leak_sql_or_db_paths(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    leak_markers = ["sqlite", "aiosqlite", "SELECT ", "Traceback", "test_sandbox.db"]
    responses = [
        await client.get(PROFILE_URL, headers=admin_headers),
        await client.get(
            "/workplace/organizations/org_missing/profile", headers=admin_headers
        ),
    ]
    for resp in responses:
        for marker in leak_markers:
            assert marker not in resp.text
