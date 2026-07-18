from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import AuditEventORM

BASE = "/workplace/organizations/org_sandbox_001/nucleus"


async def test_admin_reads_exact_schema_account_without_password(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(f"{BASE}/account", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    account = body["account"]
    assert account["organization_account_id"] == 1
    assert account["organization_name"] == "Demo Enterprise Sandbox"
    assert account["organization_code"] == "org_sandbox_001"
    assert account["organization_type"] == "Enterprise"
    assert account["login_username"] == "sandbox.organization"
    assert account["email"] == "operations@example.test"
    assert "password" not in response.text.lower()
    assert body["access"]["permission"] == "organization.account.read"


async def test_account_read_is_admin_only(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await client.get(f"{BASE}/account", headers=reader_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_license_and_approval_status_are_exact_fields(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    license_response = await client.get(f"{BASE}/license", headers=admin_headers)
    assert license_response.status_code == 200
    license_info = license_response.json()["license"]
    assert license_info["max_user_limit"] == 5
    assert license_info["license_start_date"].startswith("2026-01-01")
    assert license_info["license_end_date"].startswith("2026-11-26")

    approval_response = await client.get(
        f"{BASE}/approval-status",
        headers=admin_headers,
    )
    assert approval_response.status_code == 200
    approval = approval_response.json()["approval"]
    assert approval["status"] == "approved"
    assert approval["approved_by"] == 1001
    assert approval["rejected_by"] is None
    assert approval["rejection_reason"] is None


async def test_entitlements_expose_every_supplied_access_table(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await client.get(f"{BASE}/entitlements", headers=reader_headers)
    assert response.status_code == 200
    entitlements = response.json()["entitlements"]
    assert entitlements["organization_account_id"] == 1
    assert entitlements["category_access"][0]["category_id"] == 101
    assert entitlements["company_profile_access"][0]["company_id"] == 201
    assert entitlements["drug_access"][0]["drug_id"] == 301
    assert entitlements["indication_access"][0]["indication_id"] == 401
    assert entitlements["market_access"][0]["market_id"] == 501
    assert entitlements["report_access"][0]["reports_id"] == 1001
    assert entitlements["special_permissions"][0]["reports_custom_id"] == 605
    assert response.json()["access"]["permission"] == "organization.entitlements.read"


async def test_nucleus_reads_are_audited_without_secrets(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    assert (await client.get(f"{BASE}/account", headers=admin_headers)).status_code == 200
    event = await db_session.scalar(
        select(AuditEventORM).where(
            AuditEventORM.event_type == "nucleus.organization_account.read"
        )
    )
    assert event is not None
    assert event.resource_type == "OrganizationAccount"
    assert "password" not in str(event.details_json).lower()
