"""Authentication & permission tests.

Covers the backend-owned access pipeline: active user + active membership +
required permission. Reads never require a seat.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import UserORM

PROFILE_URL = "/workplace/organizations/org_sandbox_001/profile"


async def test_outsider_receives_403(
    client: AsyncClient, outsider_headers: dict[str, str]
) -> None:
    """A user with no membership is denied at the organization boundary."""

    resp = await client.get(PROFILE_URL, headers=outsider_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "organization_access_denied"


async def test_invited_member_receives_403(
    client: AsyncClient, invited_headers: dict[str, str]
) -> None:
    """An invited (not-yet-active) membership confers no roles -> denied."""

    resp = await client.get(PROFILE_URL, headers=invited_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "organization_access_denied"


async def test_unseated_active_member_can_read(
    client: AsyncClient, unseated_headers: dict[str, str]
) -> None:
    """Reads do NOT require a seat: an active, unseated member is allowed."""

    resp = await client.get(PROFILE_URL, headers=unseated_headers)
    assert resp.status_code == 200
    assert resp.json()["access"]["user_id"] == "usr_member_003"


async def test_missing_user_header_receives_401(client: AsyncClient) -> None:
    resp = await client.get(PROFILE_URL)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_unknown_user_receives_401(client: AsyncClient) -> None:
    resp = await client.get(PROFILE_URL, headers={"X-Mock-User-Id": "usr_ghost_999"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_disabled_user_receives_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await db_session.get(UserORM, "usr_admin_001")
    assert user is not None
    user.status = "disabled"
    await db_session.commit()

    resp = await client.get(PROFILE_URL, headers={"X-Mock-User-Id": "usr_admin_001"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "user_disabled"


async def test_error_response_shape_includes_request_id(client: AsyncClient) -> None:
    resp = await client.get(PROFILE_URL)
    error = resp.json()["error"]
    assert set(error.keys()) == {"code", "message", "request_id"}
    assert error["request_id"]
