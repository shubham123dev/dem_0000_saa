from __future__ import annotations

import json

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.workplace_resource_models import (
    WorkplaceMutationPlanORM,
    WorkplaceResourceTombstoneORM,
    WorkplaceSettingORM,
)

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
            json={"reason": f"Resource review {index + 1}"},
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


async def test_setting_full_lifecycle_and_receipts(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    create = await _propose(
        client,
        admin_headers,
        "create_workplace_resource",
        {
            "resource_type": "workplace_setting",
            "values_json": json.dumps(
                {
                    "namespace": "notifications",
                    "key": "daily_digest",
                    "value": {"enabled": True, "hour": 8},
                    "description": "Daily digest policy",
                }
            ),
        },
    )
    await _approve(client, create, admin_headers)
    created_execution = await _execute(
        client,
        create,
        admin_headers,
        "create-workplace-setting-001",
    )
    setting_id = created_execution["result"]["resource_id"]

    setting = await db_session.get(WorkplaceSettingORM, setting_id)
    assert setting is not None
    assert setting.value_json == {"enabled": True, "hour": 8}

    update = await _propose(
        client,
        admin_headers,
        "update_workplace_resource",
        {
            "resource_type": "workplace_setting",
            "resource_id": setting_id,
            "changes_json": json.dumps(
                {"value": {"enabled": True, "hour": 9}}
            ),
        },
    )
    await _approve(client, update, admin_headers)
    await _execute(client, update, admin_headers, "update-workplace-setting-001")

    delete = await _propose(
        client,
        admin_headers,
        "delete_workplace_resource",
        {
            "resource_type": "workplace_setting",
            "resource_id": setting_id,
        },
    )
    await _approve(client, delete, admin_headers)
    await _execute(client, delete, admin_headers, "delete-workplace-setting-001")
    await db_session.refresh(setting)
    assert setting.is_active is False
    tombstone = await db_session.scalar(
        select(WorkplaceResourceTombstoneORM).where(
            WorkplaceResourceTombstoneORM.resource_id == setting_id
        )
    )
    assert tombstone is not None
    assert tombstone.deleted_by_user_id == "usr_admin_001"

    restore = await _propose(
        client,
        admin_headers,
        "restore_workplace_resource",
        {
            "resource_type": "workplace_setting",
            "resource_id": setting_id,
        },
    )
    await _approve(client, restore, admin_headers)
    await _execute(client, restore, admin_headers, "restore-workplace-setting-001")
    await db_session.refresh(setting)
    assert setting.is_active is True
    await db_session.refresh(tombstone)
    assert tombstone.restored_at is not None

    plans = (
        await db_session.execute(select(WorkplaceMutationPlanORM))
    ).scalars().all()
    assert len(plans) == 4
    assert all(plan.status == "succeeded" for plan in plans)


async def test_protected_fields_and_cross_scope_are_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    protected = await client.post(
        f"{ACTION_BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_workplace_resource",
            "arguments": {
                "resource_type": "organization",
                "resource_id": ORGANIZATION_ID,
                "changes_json": json.dumps({"version": 99}),
            },
        },
    )
    assert protected.status_code == 422

    other_scope = await client.get(
        f"/workplace/organizations/other-org/resources/organization/{ORGANIZATION_ID}",
        headers=admin_headers,
    )
    assert other_scope.status_code in {403, 404, 422}
async def test_generic_profile_routes_cannot_bypass_projection_handlers(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    for changes in (
        {"contact_email": "bypass@example.test"},
        {"display_name": "Bypass Name"},
    ):
        response = await client.post(
            f"{ACTION_BASE}/propose",
            headers=admin_headers,
            json={
                "action_name": "update_workplace_resource",
                "arguments": {
                    "resource_type": "organization",
                    "resource_id": ORGANIZATION_ID,
                    "changes_json": json.dumps(changes),
                },
            },
        )
        assert response.status_code == 422


async def test_restore_reapplies_exact_snapshot_and_redelete_records_executor(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    create = await _propose(
        client,
        admin_headers,
        "create_workplace_resource",
        {
            "resource_type": "workplace_setting",
            "values_json": json.dumps(
                {
                    "namespace": "integrity",
                    "key": "restore_snapshot",
                    "value": {"enabled": True},
                    "description": "Reviewed original description",
                }
            ),
        },
    )
    await _approve(client, create, admin_headers)
    created = await _execute(
        client,
        create,
        admin_headers,
        "create-restore-integrity-001",
    )
    setting_id = created["result"]["resource_id"]

    delete = await _propose(
        client,
        admin_headers,
        "delete_workplace_resource",
        {"resource_type": "workplace_setting", "resource_id": setting_id},
    )
    await _approve(client, delete, admin_headers)
    await _execute(client, delete, admin_headers, "delete-restore-integrity-001")

    setting = await db_session.get(WorkplaceSettingORM, setting_id)
    assert setting is not None
    setting.description = "Unreviewed same-version tamper"
    await db_session.commit()

    restore = await _propose(
        client,
        admin_headers,
        "restore_workplace_resource",
        {"resource_type": "workplace_setting", "resource_id": setting_id},
    )
    restored_changes = {
        item["field"]: item for item in restore["changes"]
    }
    assert restored_changes["description"]["after"] == (
        "Reviewed original description"
    )
    await _approve(client, restore, admin_headers)
    await _execute(client, restore, admin_headers, "restore-integrity-001")
    await db_session.refresh(setting)
    assert setting.is_active is True
    assert setting.description == "Reviewed original description"

    second_delete = await _propose(
        client,
        admin_headers,
        "delete_workplace_resource",
        {"resource_type": "workplace_setting", "resource_id": setting_id},
    )
    await _approve(client, second_delete, admin_headers)
    await _execute(
        client,
        second_delete,
        APPROVER_ONE,
        "delete-restore-integrity-002",
    )
    tombstone = await db_session.scalar(
        select(WorkplaceResourceTombstoneORM).where(
            WorkplaceResourceTombstoneORM.resource_id == setting_id
        )
    )
    assert tombstone is not None
    await db_session.refresh(tombstone)
    assert tombstone.deleted_by_user_id == "usr_approval_admin_001"
