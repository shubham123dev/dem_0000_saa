from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionResourcePrecondition,
    AgentApprovalPolicy,
)
from app.agent.action_registry import build_action_fingerprint
from app.db.action_models import AgentActionProposalORM
from app.db.orm_models import OrganizationORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


def build_fingerprint(**overrides) -> str:
    values = {
        "organization_id": "org_001",
        "requested_by_user_id": "usr_001",
        "action_name": "update_organization_contact_email",
        "arguments": {"contact_email": "one@example.test"},
        "changes": (
            AgentActionChange(
                field="contact_email",
                before="old@example.test",
                after="one@example.test",
            ),
        ),
        "observed_resource_version": 1,
        "approval_policy": AgentApprovalPolicy(
            self_approval_allowed=True,
            required_approver_permission="organization.profile.update",
            minimum_approvals=1,
        ),
        "resource_type": "organization",
        "resource_id": "org_001",
        "resource_preconditions": (
            AgentActionResourcePrecondition(
                resource_type="organization",
                resource_id="org_001",
                observed_version=1,
            ),
        ),
        "fingerprint_version": 3,
        "expires_at": datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_action_fingerprint(**values)


def test_action_fingerprint_changes_with_reviewed_scope_and_state() -> None:
    baseline = build_fingerprint()
    variants = {
        build_fingerprint(organization_id="org_002"),
        build_fingerprint(requested_by_user_id="usr_002"),
        build_fingerprint(arguments={"contact_email": "two@example.test"}),
        build_fingerprint(
            changes=(
                AgentActionChange(
                    field="contact_email",
                    before="different@example.test",
                    after="one@example.test",
                ),
            )
        ),
        build_fingerprint(observed_resource_version=2),
        build_fingerprint(
            approval_policy=AgentApprovalPolicy(
                self_approval_allowed=False,
                required_approver_permission="organization.profile.update",
                minimum_approvals=1,
            )
        ),
        build_fingerprint(resource_id="org_002"),
        build_fingerprint(
            resource_preconditions=(
                AgentActionResourcePrecondition(
                    resource_type="organization",
                    resource_id="org_001",
                    observed_version=2,
                ),
            )
        ),
        build_fingerprint(
            expires_at=datetime(2026, 7, 17, 12, 1, tzinfo=timezone.utc)
        ),
    }
    assert baseline not in variants
    assert len(variants) == 9


def test_action_fingerprint_treats_naive_sqlite_datetime_as_utc() -> None:
    aware = datetime(2026, 7, 17, 12, 0, 0, 123456, tzinfo=timezone.utc)
    naive = aware.replace(tzinfo=None)

    assert build_fingerprint(expires_at=aware) == build_fingerprint(expires_at=naive)


def test_version_two_fingerprint_remains_backward_compatible() -> None:
    assert build_fingerprint(fingerprint_version=2) == (
        "2f612e8430834954193e3046d794074bccf5f483ce59887399cb9b0ceb7c0a86"
    )


async def test_modified_approved_proposal_cannot_execute(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "approved@example.test",
        },
    )
    proposal_id = proposal_response.json()["proposal"]["id"]
    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved original value"},
    )
    assert approval_response.status_code == 200

    proposal_row = await db_session.get(AgentActionProposalORM, proposal_id)
    assert proposal_row is not None
    proposal_row.arguments_json = {"contact_email": "tampered@example.test"}
    await db_session.commit()

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "tampered-execution-001"},
    )
    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == "agent_action_state_conflict"
    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "operations@example.test"
    assert organization.version == 1
