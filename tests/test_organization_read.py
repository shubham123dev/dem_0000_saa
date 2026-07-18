"""Organization profile read-flow and cross-cutting guarantees."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import action_routes, agent_routes, workplace_routes
from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationORM,
    OrganizationOverviewORM,
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
OVERVIEW_URL = "/workplace/organizations/org_sandbox_001/overview"
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
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(PROFILE_URL, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["organization"] == EXPECTED_ORG
    assert body["access"] == {
        "user_id": "usr_admin_001",
        "permission": "organization.profile.read",
    }


async def test_reader_can_read_organization(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await client.get(PROFILE_URL, headers=reader_headers)
    assert response.status_code == 200
    assert response.json()["organization"] == EXPECTED_ORG
    assert response.json()["access"]["user_id"] == "usr_member_001"


async def test_unknown_organization_returns_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/workplace/organizations/org_does_not_exist/profile",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"


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

    for endpoint in ("profile", "overview"):
        response = await client.get(
            f"/workplace/organizations/org_prod_001/{endpoint}",
            headers=admin_headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "production_access_blocked"


async def test_only_explicit_workplace_post_routes_exist() -> None:
    allowed_post_paths = {
        "/workplace/organizations/{organization_id}/agent/query",
        "/workplace/organizations/{organization_id}/agent/actions/propose",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/approve",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reject",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/cancel",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/rollback-proposal",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/execute",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reconcile",
        "/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/audit-replay",
    }
    workplace_post_paths: set[str] = set()

    explicit_workplace_routes = (
        workplace_routes.router.routes
        + agent_routes.router.routes
        + action_routes.router.routes
    )
    for route in explicit_workplace_routes:
        route_path = getattr(route, "path", "")
        route_methods = getattr(route, "methods", set()) or set()
        if route_path.startswith("/workplace"):
            assert not (route_methods & {"PUT", "PATCH", "DELETE"})
            if "POST" in route_methods:
                workplace_post_paths.add(route_path)

    assert workplace_post_paths == allowed_post_paths


async def test_seed_is_idempotent(
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> None:
    async def counts(session: AsyncSession) -> dict[str, int]:
        async def count(model) -> int:
            return int(
                await session.scalar(select(func.count()).select_from(model)) or 0
            )

        return {
            "orgs": await count(OrganizationORM),
            "overviews": await count(OrganizationOverviewORM),
            "users": await count(UserORM),
            "memberships": await count(OrganizationMembershipORM),
            "pools": await count(OrganizationSeatPoolORM),
            "assignments": await count(SeatAssignmentORM),
            "reports": await count(ReportORM),
            "access": await count(OrganizationReportAccessORM),
            "role_permissions": await count(RolePermissionORM),
        }

    async with sessionmaker_() as session:
        await seed(session)
        first = await counts(session)

    async with sessionmaker_() as session:
        await seed(session)
        second = await counts(session)

    assert first == second
    assert first == {
        "orgs": 1,
        "overviews": 1,
        "users": 8,
        "memberships": 7,
        "pools": 1,
        "assignments": 3,
        "reports": 5,
        "access": 3,
        "role_permissions": 31,
    }


async def test_responses_do_not_leak_sql_or_db_paths(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    leak_markers = ["sqlite", "aiosqlite", "SELECT ", "Traceback", "test_sandbox.db"]
    responses = [
        await client.get(PROFILE_URL, headers=admin_headers),
        await client.get(OVERVIEW_URL, headers=admin_headers),
        await client.get(
            "/workplace/organizations/org_missing/profile",
            headers=admin_headers,
        ),
        await client.get(
            "/workplace/organizations/org_missing/overview",
            headers=admin_headers,
        ),
    ]
    for response in responses:
        for marker in leak_markers:
            assert marker not in response.text
