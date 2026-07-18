from __future__ import annotations

from datetime import datetime, timezone
import json

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_models import NucleusOrganizationCategoryAccessORM
from app.db.orm_models import OrganizationMembershipORM, SeatAssignmentORM, UserORM
from app.db.workplace_resource_models import (
    WorkplaceMutationPlanORM,
    WorkplaceMutationStepReceiptORM,
    WorkplaceSettingORM,
)
from app.workplace_resources.workflows import WorkplaceWorkflowService

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}


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
    assert response.status_code == 200, response.text
    return response.json()["proposal"]


async def _approve(
    client: AsyncClient,
    proposal: dict,
    admin_headers: dict[str, str],
) -> None:
    if proposal["approval_policy"]["minimum_approvals"] == 1:
        headers_list = (admin_headers,)
    else:
        headers_list = (APPROVER_ONE, APPROVER_TWO)
    for index, headers in enumerate(headers_list):
        response = await client.post(
            f"{ACTION_BASE}/{proposal['id']}/approve",
            headers=headers,
            json={"reason": f"Workflow review {index + 1}"},
        )
        assert response.status_code == 200, response.text


async def _execute(
    client: AsyncClient,
    proposal: dict,
    admin_headers: dict[str, str],
    key: str,
) -> dict:
    response = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["execution"]


async def test_atomic_onboard_and_offboard_workflows(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    onboard = await _propose(
        client,
        admin_headers,
        "onboard_organization_user",
        {
            "email": "workflow.reader@example.test",
            "display_name": "Workflow Reader",
            "role": "sandbox_reader",
            "seat_type": "standard",
        },
    )
    assert onboard["risk_level"] == "medium"
    assert onboard["approval_policy"]["minimum_approvals"] == 1
    await _approve(client, onboard, admin_headers)
    onboard_execution = await _execute(
        client,
        onboard,
        admin_headers,
        "workflow-onboard-001",
    )
    user_id = onboard_execution["result"]["resource_id"]

    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == user_id,
        )
    )
    assert membership is not None
    assert membership.membership_status == "active"
    assert membership.role == "sandbox_reader"
    seat = await db_session.scalar(
        select(SeatAssignmentORM).where(
            SeatAssignmentORM.organization_id == ORGANIZATION_ID,
            SeatAssignmentORM.user_id == user_id,
            SeatAssignmentORM.status == "active",
        )
    )
    assert seat is not None

    offboard = await _propose(
        client,
        admin_headers,
        "offboard_organization_user",
        {"user_id": user_id},
    )
    assert offboard["risk_level"] == "high"
    assert offboard["approval_policy"] == {
        "self_approval_allowed": False,
        "required_approver_permission": "workplace.workflows.manage",
        "minimum_approvals": 2,
    }
    await _approve(client, offboard, admin_headers)
    await _execute(client, offboard, admin_headers, "workflow-offboard-001")
    await db_session.refresh(membership)
    await db_session.refresh(seat)
    assert membership.membership_status == "removed"
    assert seat.status == "revoked"

    plans = tuple(
        (
            await db_session.execute(
                select(WorkplaceMutationPlanORM).where(
                    WorkplaceMutationPlanORM.workflow_name.in_(
                        [
                            "onboard_organization_user",
                            "offboard_organization_user",
                        ]
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(plans) == 2
    receipts = tuple(
        (
            await db_session.execute(select(WorkplaceMutationStepReceiptORM))
        )
        .scalars()
        .all()
    )
    assert any((item.verification_json or {}).get("verified") is True for item in receipts)


async def test_query_selected_bulk_freezes_targets_and_updates_atomically(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    settings = [
        WorkplaceSettingORM(
            id=f"query_bulk_{index}",
            organization_id=ORGANIZATION_ID,
            namespace="workflow_bulk",
            setting_key=f"key_{index}",
            value_json={"enabled": False},
            description="before",
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
        )
        for index in range(2)
    ]
    db_session.add_all(settings)
    await db_session.commit()

    proposal = await _propose(
        client,
        admin_headers,
        "bulk_update_workplace_resources_by_query",
        {
            "resource_type": "workplace_setting",
            "query_json": json.dumps(
                {
                    "all": [
                        {
                            "field": "namespace",
                            "operator": "equals",
                            "value": "workflow_bulk",
                        }
                    ]
                }
            ),
            "changes_json": json.dumps(
                {"description": "after", "value": {"enabled": True}}
            ),
        },
    )
    assert proposal["risk_level"] == "medium"
    assert len(proposal["resource_preconditions"]) >= 2
    await _approve(client, proposal, admin_headers)
    await _execute(client, proposal, admin_headers, "workflow-query-bulk-001")

    for setting in settings:
        await db_session.refresh(setting)
        assert setting.description == "after"
        assert setting.value_json == {"enabled": True}
        assert setting.version == 2

    rollback_response = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Restore the reviewed setting snapshots"},
    )
    assert rollback_response.status_code == 200, rollback_response.text
    rollback = rollback_response.json()["proposal"]
    assert rollback["action_name"] == "restore_workplace_resource_snapshots"
    assert rollback["approval_policy"]["minimum_approvals"] == 2
    await _approve(client, rollback, admin_headers)
    await _execute(
        client, rollback, admin_headers, "workflow-query-bulk-rollback-001"
    )
    for setting in settings:
        await db_session.refresh(setting)
        assert setting.description == "before"
        assert setting.value_json == {"enabled": False}
        assert setting.version == 3


async def test_access_package_uses_nucleus_schema_and_actor_mapping(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "apply_organization_access_package",
        {
            "package_json": json.dumps(
                {
                    "categories": [
                        {
                            "category_id": 991001,
                            "category_sample_id": None,
                            "active": True,
                        }
                    ]
                }
            )
        },
    )
    await _approve(client, proposal, admin_headers)
    await _execute(client, proposal, admin_headers, "workflow-access-package-001")

    row = await db_session.scalar(
        select(NucleusOrganizationCategoryAccessORM).where(
            NucleusOrganizationCategoryAccessORM.category_id == 991001
        )
    )
    assert row is not None
    assert row.is_active is True


async def test_self_offboarding_is_rejected_before_proposal_creation(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{ACTION_BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": "offboard_organization_user",
            "arguments": {"user_id": "usr_admin_001"},
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_action_invalid"


async def test_query_bulk_target_drift_marks_proposal_stale_without_partial_write(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    settings = [
        WorkplaceSettingORM(
            id=f"query_drift_{index}",
            organization_id=ORGANIZATION_ID,
            namespace="workflow_drift",
            setting_key=f"key_{index}",
            value_json={"enabled": False},
            description="unchanged",
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
        )
        for index in range(2)
    ]
    db_session.add_all(settings)
    await db_session.commit()
    proposal = await _propose(
        client,
        admin_headers,
        "bulk_update_workplace_resources_by_query",
        {
            "resource_type": "workplace_setting",
            "query_json": json.dumps(
                {
                    "all": [
                        {
                            "field": "namespace",
                            "operator": "equals",
                            "value": "workflow_drift",
                        }
                    ]
                }
            ),
            "changes_json": json.dumps({"description": "should-not-apply"}),
        },
    )
    settings[0].description = "concurrent-change"
    settings[0].version = 2
    await db_session.commit()
    await _approve(client, proposal, admin_headers)
    executed = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "workflow-query-drift-001"},
    )
    assert executed.status_code == 409
    assert executed.json()["error"]["code"] == "agent_action_stale"
    for setting in settings:
        await db_session.refresh(setting)
    assert settings[0].description == "concurrent-change"
    assert settings[1].description == "unchanged"
    assert settings[1].version == 1


async def test_dynamic_risk_escalates_large_query_batch(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            WorkplaceSettingORM(
                id=f"query_risk_{index}",
                organization_id=ORGANIZATION_ID,
                namespace="workflow_risk",
                setting_key=f"key_{index}",
                value_json={"index": index},
                description="risk-before",
                is_active=True,
                version=1,
                created_at=now,
                updated_at=now,
            )
            for index in range(6)
        ]
    )
    await db_session.commit()
    proposal = await _propose(
        client,
        admin_headers,
        "bulk_update_workplace_resources_by_query",
        {
            "resource_type": "workplace_setting",
            "query_json": json.dumps(
                {
                    "all": [
                        {
                            "field": "namespace",
                            "operator": "equals",
                            "value": "workflow_risk",
                        }
                    ]
                }
            ),
            "changes_json": json.dumps({"description": "risk-after"}),
        },
    )
    assert proposal["risk_level"] == "high"
    assert proposal["approval_policy"]["minimum_approvals"] == 2
    assert proposal["approval_policy"]["self_approval_allowed"] is False
    self_approval = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/approve",
        headers=admin_headers,
        json={"reason": "Requester must not approve a large batch"},
    )
    assert self_approval.status_code == 409


async def test_workflow_failure_rolls_back_every_database_change(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    monkeypatch,
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "onboard_organization_user",
        {
            "email": "atomic.failure@example.test",
            "display_name": "Atomic Failure",
            "role": "sandbox_reader",
            "seat_type": "none",
        },
    )
    await _approve(client, proposal, admin_headers)

    async def _fail_before_commit(self, **kwargs):
        raise RuntimeError("forced workflow persistence failure")

    monkeypatch.setattr(
        WorkplaceWorkflowService,
        "_persist_plan_and_steps",
        _fail_before_commit,
    )
    executed = await client.post(
        f"{ACTION_BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "workflow-atomic-failure-001"},
    )
    assert executed.status_code == 409
    assert executed.json()["error"]["code"] == (
        "agent_action_reconciliation_required"
    )
    user = await db_session.scalar(
        select(UserORM).where(UserORM.email == "atomic.failure@example.test")
    )
    assert user is None
