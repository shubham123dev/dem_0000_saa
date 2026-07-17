from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionHandlerResult,
    AgentActionPreparation,
)
from app.api.action_dependencies import get_agent_action_handlers
from app.db.orm_models import OrganizationORM
from app.main import app

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


class MutateThenLoseResponseHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.execution_count = 0

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]):
        organization = await self._session.get(OrganizationORM, organization_id)
        assert organization is not None
        return AgentActionPreparation(
            normalized_arguments={"contact_email": arguments["contact_email"]},
            changes=(
                AgentActionChange(
                    field="contact_email",
                    before=organization.contact_email,
                    after=arguments["contact_email"],
                ),
            ),
            observed_resource_version=organization.version,
            resource_type="organization",
            resource_id=organization_id,
        )

    async def execute(self, *, proposal):
        self.execution_count += 1
        organization = await self._session.get(
            OrganizationORM,
            proposal.organization_id,
        )
        assert organization is not None
        organization.contact_email = proposal.arguments["contact_email"]
        organization.version += 1
        await self._session.commit()
        raise RuntimeError("provider response was lost after mutation")

    async def reconcile(self, *, proposal, execution):
        organization = await self._session.get(
            OrganizationORM,
            proposal.organization_id,
        )
        assert organization is not None
        await self._session.refresh(organization)
        if organization.contact_email != proposal.arguments["contact_email"]:
            return None
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=organization.id,
            before={
                "contact_email": proposal.changes[0].before,
                "version": proposal.observed_resource_version,
            },
            after={
                "contact_email": organization.contact_email,
                "version": organization.version,
            },
        )


async def test_unknown_execution_outcome_reconciles_without_second_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    handler = MutateThenLoseResponseHandler(db_session)
    app.dependency_overrides[get_agent_action_handlers] = lambda: {
        "update_organization_contact_email": handler
    }
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "reconciled@example.test",
        },
    )
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
        json={"idempotency_key": "reconciliation-key"},
    )
    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == (
        "agent_action_reconciliation_required"
    )
    assert handler.execution_count == 1

    reconciliation_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/reconcile",
        headers=admin_headers,
    )
    assert reconciliation_response.status_code == 200
    execution = reconciliation_response.json()["execution"]
    assert execution["outcome"] == "succeeded"
    assert execution["reconciliation_status"] == "resolved"
    assert execution["attempt_count"] == 2
    assert handler.execution_count == 1

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "reconciled@example.test"
    assert organization.version == 2
