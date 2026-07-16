"""Authentication & permission tests (Step 0 tests 6, 7, 8 + disabled)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import EmployeeORM

PROFILE_URL = "/sandbox/organizations/org_sandbox_001/profile"


async def test_outsider_receives_403(
    client: AsyncClient, outsider_headers: dict[str, str]
) -> None:
    resp = await client.get(PROFILE_URL, headers=outsider_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "organization_access_denied"


async def test_missing_employee_header_receives_401(client: AsyncClient) -> None:
    resp = await client.get(PROFILE_URL)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_unknown_employee_receives_401(client: AsyncClient) -> None:
    resp = await client.get(
        PROFILE_URL, headers={"X-Mock-Employee-Id": "emp_ghost_999"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_disabled_employee_receives_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await db_session.get(EmployeeORM, "emp_admin_001")
    assert employee is not None
    employee.status = "disabled"
    await db_session.commit()

    resp = await client.get(
        PROFILE_URL, headers={"X-Mock-Employee-Id": "emp_admin_001"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "employee_disabled"


async def test_error_response_shape_includes_request_id(client: AsyncClient) -> None:
    resp = await client.get(PROFILE_URL)
    error = resp.json()["error"]
    assert set(error.keys()) == {"code", "message", "request_id"}
    assert error["request_id"]
