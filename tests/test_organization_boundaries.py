from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    AuditEventORM,
    OrganizationMembershipORM,
    OrganizationORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    SeatAssignmentORM,
    UserORM,
)

PRIMARY_ORGANIZATION_ID = "org_sandbox_001"
SECONDARY_ORGANIZATION_ID = "org_sandbox_002"
SECONDARY_USER_ID = "usr_secondary_001"
SECONDARY_REPORT_ID = "rpt_secondary_001"
SECONDARY_SEAT_POOL_ID = "seat_pool_secondary_001"
SECONDARY_AUDIT_EVENT_ID = "audit_secondary_001"


def build_organization_url(organization_id: str, resource_path: str) -> str:
    return f"/workplace/organizations/{organization_id}/{resource_path}"


async def create_secondary_organization_data(database_session: AsyncSession) -> None:
    current_time_utc = datetime.now(timezone.utc)

    database_session.add(
        OrganizationORM(
            id=SECONDARY_ORGANIZATION_ID,
            display_name="Secondary Sandbox Organization",
            legal_name=None,
            contact_email="secondary@example.test",
            environment="sandbox",
            status="active",
            version=1,
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        UserORM(
            id=SECONDARY_USER_ID,
            display_name="Secondary Organization User",
            email="secondary.user@example.test",
            status="active",
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        ReportORM(
            id=SECONDARY_REPORT_ID,
            external_report_id="external_secondary_001",
            title="Secondary Organization Report",
            market_name="Secondary Market",
            status="active",
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    await database_session.flush()

    database_session.add(
        OrganizationMembershipORM(
            organization_id=SECONDARY_ORGANIZATION_ID,
            user_id="usr_admin_001",
            role="sandbox_admin",
            membership_status="active",
            joined_at=current_time_utc,
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        OrganizationMembershipORM(
            organization_id=SECONDARY_ORGANIZATION_ID,
            user_id=SECONDARY_USER_ID,
            role="sandbox_reader",
            membership_status="active",
            joined_at=current_time_utc,
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        OrganizationSeatPoolORM(
            id=SECONDARY_SEAT_POOL_ID,
            organization_id=SECONDARY_ORGANIZATION_ID,
            seat_type="standard",
            total_seats=1,
            status="active",
            starts_at=current_time_utc,
            expires_at=None,
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        OrganizationReportAccessORM(
            id="report_access_secondary_001",
            organization_id=SECONDARY_ORGANIZATION_ID,
            report_id=SECONDARY_REPORT_ID,
            access_level="view",
            status="active",
            granted_at=current_time_utc,
            expires_at=None,
            granted_by_user_id="usr_admin_001",
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    await database_session.flush()

    database_session.add(
        SeatAssignmentORM(
            id="seat_assignment_secondary_001",
            organization_id=SECONDARY_ORGANIZATION_ID,
            seat_pool_id=SECONDARY_SEAT_POOL_ID,
            user_id=SECONDARY_USER_ID,
            status="active",
            assigned_at=current_time_utc,
            revoked_at=None,
            assigned_by_user_id="usr_admin_001",
            created_at=current_time_utc,
            updated_at=current_time_utc,
        )
    )
    database_session.add(
        AuditEventORM(
            id=SECONDARY_AUDIT_EVENT_ID,
            actor_user_id="usr_admin_001",
            organization_id=SECONDARY_ORGANIZATION_ID,
            event_type="secondary.boundary.test",
            operation="read",
            outcome="success",
            resource_type="organization",
            resource_id=SECONDARY_ORGANIZATION_ID,
            details_json=None,
            created_at=current_time_utc,
        )
    )
    await database_session.commit()


async def test_suspended_organization_blocks_every_read_surface(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    suspended_organization_record = await db_session.get(
        OrganizationORM,
        PRIMARY_ORGANIZATION_ID,
    )
    suspended_organization_record.status = "suspended"
    await db_session.commit()

    protected_resource_paths = (
        "profile",
        "users",
        "seats",
        "reports",
        "reports/rpt_market_001/access",
        "audit-log",
    )

    for protected_resource_path in protected_resource_paths:
        protected_resource_response = await client.get(
            build_organization_url(
                PRIMARY_ORGANIZATION_ID,
                protected_resource_path,
            ),
            headers=admin_headers,
        )
        assert protected_resource_response.status_code == 403
        assert (
            protected_resource_response.json()["error"]["code"]
            == "organization_suspended"
        )


async def test_secondary_organization_users_do_not_appear_in_primary_user_list(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    await create_secondary_organization_data(db_session)

    primary_user_response = await client.get(
        build_organization_url(PRIMARY_ORGANIZATION_ID, "users"),
        headers=admin_headers,
    )
    secondary_user_response = await client.get(
        build_organization_url(SECONDARY_ORGANIZATION_ID, "users"),
        headers=admin_headers,
    )

    primary_user_ids = {
        member_record["user_id"]
        for member_record in primary_user_response.json()["members"]
    }
    secondary_user_ids = {
        member_record["user_id"]
        for member_record in secondary_user_response.json()["members"]
    }

    assert SECONDARY_USER_ID not in primary_user_ids
    assert SECONDARY_USER_ID in secondary_user_ids


async def test_secondary_organization_seats_do_not_affect_primary_seat_summary(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    await create_secondary_organization_data(db_session)

    primary_seat_response = await client.get(
        build_organization_url(PRIMARY_ORGANIZATION_ID, "seats"),
        headers=admin_headers,
    )
    secondary_seat_response = await client.get(
        build_organization_url(SECONDARY_ORGANIZATION_ID, "seats"),
        headers=admin_headers,
    )

    primary_seat_summary = primary_seat_response.json()["seats"]
    secondary_seat_summary = secondary_seat_response.json()["seats"]

    assert SECONDARY_USER_ID not in primary_seat_summary["seated_user_ids"]
    assert secondary_seat_summary["seated_user_ids"] == [SECONDARY_USER_ID]
    assert secondary_seat_summary["active_assignments"] == 1


async def test_report_access_is_resolved_independently_for_each_organization(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    await create_secondary_organization_data(db_session)

    primary_access_response = await client.get(
        build_organization_url(
            PRIMARY_ORGANIZATION_ID,
            f"reports/{SECONDARY_REPORT_ID}/access",
        ),
        headers=admin_headers,
    )
    secondary_access_response = await client.get(
        build_organization_url(
            SECONDARY_ORGANIZATION_ID,
            f"reports/{SECONDARY_REPORT_ID}/access",
        ),
        headers=admin_headers,
    )

    assert primary_access_response.status_code == 200
    assert primary_access_response.json()["has_access"] is False
    assert secondary_access_response.status_code == 200
    assert secondary_access_response.json()["has_access"] is True


async def test_audit_log_returns_only_requested_organization_events(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    await create_secondary_organization_data(db_session)

    primary_audit_response = await client.get(
        build_organization_url(PRIMARY_ORGANIZATION_ID, "audit-log"),
        headers=admin_headers,
    )
    secondary_audit_response = await client.get(
        build_organization_url(SECONDARY_ORGANIZATION_ID, "audit-log"),
        headers=admin_headers,
    )

    primary_audit_event_ids = {
        audit_event_record["id"]
        for audit_event_record in primary_audit_response.json()["events"]
    }
    secondary_audit_event_ids = {
        audit_event_record["id"]
        for audit_event_record in secondary_audit_response.json()["events"]
    }

    assert SECONDARY_AUDIT_EVENT_ID not in primary_audit_event_ids
    assert SECONDARY_AUDIT_EVENT_ID in secondary_audit_event_ids
    assert primary_audit_event_ids.isdisjoint(secondary_audit_event_ids)
