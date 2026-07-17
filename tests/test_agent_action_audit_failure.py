from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_repository
from app.db.orm_models import OrganizationORM
from app.main import app

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


class FailSuccessAuditRepository:
    async def append(self, **values):
        if values["event_type"] == "agent_action_succeeded":
            raise RuntimeError("audit backend unavailable")
        return None


async def test_audit_failure_marks_pending_without_reversing_success(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_audit_repository] = (
        lambda: FailSuccessAuditRepository()
    )
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "audit.pending@example.test",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["proposal"]["id"]
    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved"},
    )
    assert approval_response.status_code == 200

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "audit-pending-key"},
    )
    assert execution_response.status_code == 200
    execution = execution_response.json()["execution"]
    assert execution["outcome"] == "succeeded"
    assert execution["audit_pending"] is True

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "audit.pending@example.test"
    assert organization.version == 2
