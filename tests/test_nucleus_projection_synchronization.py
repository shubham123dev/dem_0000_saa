from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.nucleus_action_handlers import (
    UpdateOrganizationContactEmailBridgeHandler,
)
from app.api.action_dependencies import get_agent_action_handlers
from app.db.nucleus_models import NucleusOrganizationAccountORM
from app.db.orm_models import OrganizationORM, OrganizationOverviewORM
from app.main import app
from app.mock_api.service import MockOrganizationApi
from app.repositories.nucleus_organization_repository import (
    NucleusOrganizationRepository,
)

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def _propose(
    client: AsyncClient,
    headers: dict[str, str],
    action_name: str,
    arguments: dict[str, str],
) -> dict:
    response = await client.post(
        f"{ACTION_BASE}/propose",
        headers=headers,
        json={"action_name": action_name, "arguments": arguments},
    )
    assert response.status_code == 200
    return response.json()["proposal"]


async def _approve(
    client: AsyncClient,
    headers: dict[str, str],
    proposal_id: str,
) -> None:
    response = await client.post(
        f"{ACTION_BASE}/{proposal_id}/approve",
        headers=headers,
        json={"reason": "Reviewed projection state"},
    )
    assert response.status_code == 200


class FailFirstContactProjectionGateway:
    def __init__(self, delegate: MockOrganizationApiAdapter) -> None:
        self._delegate = delegate
        self._fail_contact_update = True

    async def get_profile(self, organization_id: str):
        return await self._delegate.get_profile(organization_id)

    async def get_overview(self, organization_id: str):
        return await self._delegate.get_overview(organization_id)

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str | None,
        expected_version: int,
    ):
        if self._fail_contact_update:
            self._fail_contact_update = False
            return None
        return await self._delegate.update_contact_email_if_version(
            organization_id,
            contact_email,
            expected_version,
        )

    async def update_display_name_if_version(
        self,
        organization_id: str,
        display_name: str,
        expected_version: int,
    ):
        return await self._delegate.update_display_name_if_version(
            organization_id,
            display_name,
            expected_version,
        )

    async def update_organization_type_if_version(
        self,
        organization_id: str,
        organization_type: str,
        expected_version: int,
    ):
        return await self._delegate.update_organization_type_if_version(
            organization_id,
            organization_type,
            expected_version,
        )


def _install_fail_first_contact_handler(db_session: AsyncSession) -> None:
    nucleus = NucleusOrganizationRepository(db_session)
    projection = FailFirstContactProjectionGateway(
        MockOrganizationApiAdapter(MockOrganizationApi(db_session))
    )
    handler = UpdateOrganizationContactEmailBridgeHandler(
        nucleus,
        projection,
    )
    app.dependency_overrides[get_agent_action_handlers] = lambda: {
        "update_organization_contact_email": handler
    }


async def test_legacy_profile_drift_marks_contact_action_stale(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_organization_contact_email",
        {"contact_email": "approved-contact@example.test"},
    )
    await _approve(client, admin_headers, proposal["id"])

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    organization.contact_email = "concurrent@example.test"
    organization.version += 1
    await db_session.commit()

    response = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "legacy-drift-contact-001"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agent_action_stale"


async def test_nucleus_drift_marks_contact_action_stale(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_organization_contact_email",
        {"contact_email": "approved-nucleus@example.test"},
    )
    await _approve(client, admin_headers, proposal["id"])

    account = await db_session.scalar(
        select(NucleusOrganizationAccountORM).where(
            NucleusOrganizationAccountORM.organization_code == ORGANIZATION_ID
        )
    )
    assert account is not None
    account.email = "concurrent-nucleus@example.test"
    await db_session.commit()

    response = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "nucleus-drift-contact-001"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agent_action_stale"


async def test_partial_contact_update_reconciles_missing_projection_once(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    _install_fail_first_contact_handler(db_session)
    proposal = await _propose(
        client,
        admin_headers,
        "update_organization_contact_email",
        {"contact_email": "repaired-projection@example.test"},
    )
    await _approve(client, admin_headers, proposal["id"])

    execute = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "partial-contact-projection-001"},
    )
    assert execute.status_code == 409
    assert execute.json()["error"]["code"] == (
        "agent_action_reconciliation_required"
    )

    account = await db_session.scalar(
        select(NucleusOrganizationAccountORM).where(
            NucleusOrganizationAccountORM.organization_code == ORGANIZATION_ID
        )
    )
    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert account is not None
    assert organization is not None
    await db_session.refresh(account)
    await db_session.refresh(organization)
    assert account.email == "repaired-projection@example.test"
    assert organization.contact_email == "operations@example.test"

    reconciled = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/reconcile",
        headers=admin_headers,
    )
    assert reconciled.status_code == 200
    execution = reconciled.json()["execution"]
    assert execution["outcome"] == "succeeded"
    assert execution["reconciliation_status"] == "resolved"

    await db_session.refresh(organization)
    assert organization.contact_email == "repaired-projection@example.test"
    assert organization.version == 2

    repeated = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/reconcile",
        headers=admin_headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["execution"] == execution


async def test_reconciliation_does_not_overwrite_conflicting_projection(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    _install_fail_first_contact_handler(db_session)
    proposal = await _propose(
        client,
        admin_headers,
        "update_organization_contact_email",
        {"contact_email": "must-not-overwrite@example.test"},
    )
    await _approve(client, admin_headers, proposal["id"])
    execute = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "conflicting-projection-001"},
    )
    assert execute.status_code == 409

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    organization.contact_email = "newer-human-change@example.test"
    organization.version += 1
    await db_session.commit()

    reconciled = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/reconcile",
        headers=admin_headers,
    )
    assert reconciled.status_code == 200
    assert reconciled.json()["execution"]["outcome"] == (
        "reconciliation_required"
    )
    await db_session.refresh(organization)
    assert organization.contact_email == "newer-human-change@example.test"


async def test_organization_type_updates_nucleus_and_overview_projection(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_account_field",
        {"field_name": "OrganizationType", "value": "Research Network"},
    )
    assert {
        item["resource_type"]
        for item in proposal["resource_preconditions"]
    } == {"OrganizationAccount", "organization_overview"}
    await _approve(client, admin_headers, proposal["id"])
    response = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "organization-type-sync-001"},
    )
    assert response.status_code == 200

    overview = await db_session.get(OrganizationOverviewORM, ORGANIZATION_ID)
    assert overview is not None
    await db_session.refresh(overview)
    assert overview.organization_type == "Research Network"
    assert overview.version == 2
