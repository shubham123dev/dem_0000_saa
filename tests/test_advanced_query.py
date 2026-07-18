from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationORM
from app.db.workplace_resource_models import WorkplaceSettingORM
from app.workplace_resources.advanced_query import WorkplaceAdvancedQueryService


async def test_advanced_query_supports_registered_operators(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        OrganizationORM(
            id="org_sandbox_001",
            legal_name="Sandbox Org",
            display_name="Sandbox Org",
            contact_email="org@example.test",
            version=1,
        )
    )
    await db_session.flush()
    db_session.add_all(
        [
            WorkplaceSettingORM(
                id="advanced_query_alpha",
                organization_id="org_sandbox_001",
                namespace="analytics",
                setting_key="daily_alpha",
                value_json={"enabled": True},
                description="Alpha daily summary",
                is_active=True,
                version=1,
                created_at=now,
                updated_at=now,
            ),
            WorkplaceSettingORM(
                id="advanced_query_beta",
                organization_id="org_sandbox_001",
                namespace="analytics",
                setting_key="weekly_beta",
                value_json={"enabled": False},
                description=None,
                is_active=False,
                version=2,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.commit()
    service = WorkplaceAdvancedQueryService(db_session)
    items, total, normalized = await service.search(
        organization_id="org_sandbox_001",
        resource_type="workplace_setting",
        query={
            "all": [
                {
                    "field": "namespace",
                    "operator": "equals",
                    "value": "analytics",
                },
                {
                    "field": "key",
                    "operator": "starts_with",
                    "value": "daily",
                },
                {
                    "field": "description",
                    "operator": "contains",
                    "value": "summary",
                },
            ]
        },
    )
    assert total == 1
    assert items[0]["id"] == "advanced_query_alpha"
    assert normalized["all"][0]["operator"] == "equals"

    summary = await service.summarize(
        organization_id="org_sandbox_001",
        resource_type="workplace_setting",
        query={
            "all": [
                {
                    "field": "namespace",
                    "operator": "in",
                    "value": ["analytics"],
                }
            ],
            "any": [
                {
                    "field": "description",
                    "operator": "is_null",
                },
                {
                    "field": "is_active",
                    "operator": "equals",
                    "value": True,
                },
            ],
        },
    )
    assert summary["count"] == 2
    assert summary["active_count"] == 1
    assert summary["inactive_count"] == 1


async def test_advanced_query_rejects_ordering_on_strings(
    db_session: AsyncSession,
) -> None:
    service = WorkplaceAdvancedQueryService(db_session)
    try:
        service.normalize_query(
            resource_type="workplace_setting",
            query={
                "all": [
                    {
                        "field": "namespace",
                        "operator": "greater_than",
                        "value": "a",
                    }
                ]
            },
        )
    except ValueError as exception:
        assert "integer or date" in str(exception)
    else:
        raise AssertionError("String ordering must be rejected")
