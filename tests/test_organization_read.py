"""Organization read-flow tests (Step 0 tests 4, 5, 9, 12, 13, 14, 15)."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.orm_models import (
    EmployeeORM,
    EmployeeOrganizationRoleORM,
    OrganizationORM,
)
from app.db.seed import seed
from app.main import app

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
    resp = await client.get(
        "/sandbox/organizations/org_sandbox_001/profile", headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["organization"] == EXPECTED_ORG
    assert body["access"] == {
        "employee_id": "emp_admin_001",
        "permission": "organization.profile.read",
    }


async def test_reader_can_read_organization(
    client: AsyncClient, reader_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/sandbox/organizations/org_sandbox_001/profile", headers=reader_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["organization"] == EXPECTED_ORG
    assert body["access"]["employee_id"] == "emp_reader_001"


async def test_unknown_organization_returns_404(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/sandbox/organizations/org_does_not_exist/profile", headers=admin_headers
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
    # Even a fully-privileged role in the org must not bypass sandbox-only rules.
    db_session.add(
        EmployeeOrganizationRoleORM(
            employee_id="emp_admin_001",
            organization_id="org_prod_001",
            role="sandbox_admin",
        )
    )
    await db_session.commit()

    resp = await client.get(
        "/sandbox/organizations/org_prod_001/profile", headers=admin_headers
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
    async def _counts(session: AsyncSession) -> tuple[int, int, int]:
        orgs = await session.scalar(select(func.count()).select_from(OrganizationORM))
        emps = await session.scalar(select(func.count()).select_from(EmployeeORM))
        roles = await session.scalar(
            select(func.count()).select_from(EmployeeOrganizationRoleORM)
        )
        return orgs, emps, roles

    async with sessionmaker_() as session:
        await seed(session)
        first = await _counts(session)

    async with sessionmaker_() as session:
        await seed(session)
        second = await _counts(session)

    assert first == second
    assert first == (1, 3, 2)


async def test_responses_do_not_leak_sql_or_db_paths(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    leak_markers = ["sqlite", "aiosqlite", "SELECT ", "Traceback", "test_sandbox.db"]

    ok = await client.get(
        "/sandbox/organizations/org_sandbox_001/profile", headers=admin_headers
    )
    not_found = await client.get(
        "/sandbox/organizations/org_missing/profile", headers=admin_headers
    )
    for resp in (ok, not_found):
        text = resp.text
        for marker in leak_markers:
            assert marker not in text
