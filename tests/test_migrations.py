from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "0013_nucleus_admin"
EXPECTED_DATABASE_TABLE_NAMES = {
    "OrganizationAccount",
    "OrganizationCategoryAccess",
    "OrganizationCompanyProfileAccess",
    "OrganizationDrugAccess",
    "OrganizationIndicationAccess",
    "OrganizationMarketAccess",
    "OrganizationPermission",
    "OrganizationReportAccess",
    "agent_action_approvals",
    "agent_action_executions",
    "agent_action_proposals",
    "agent_action_rollbacks",
    "alembic_version",
    "audit_events",
    "nucleus_access_tombstones",
    "nucleus_actor_mappings",
    "nucleus_resource_versions",
    "organization_memberships",
    "organization_overviews",
    "organization_report_access",
    "organization_seat_pools",
    "organizations",
    "reports",
    "role_permissions",
    "seat_assignments",
    "users",
}


def build_alembic_environment(database_file_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["WORKPLACE_DATABASE_URL"] = (
        f"sqlite+aiosqlite:///{database_file_path.as_posix()}"
    )
    return environment


def run_alembic(database_file_path: Path, revision: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=REPOSITORY_ROOT,
        env=build_alembic_environment(database_file_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def read_table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        if not row[0].startswith("sqlite_")
    }


def read_column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


def read_index_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(
            f"PRAGMA index_list({table_name})"
        ).fetchall()
    }


def assert_head_and_hardening_schema(connection: sqlite3.Connection) -> None:
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert revision == (EXPECTED_HEAD,)

    account_columns = read_column_names(connection, "OrganizationAccount")
    assert {
        "OrganizationAccountId",
        "OrganizationName",
        "OrganizationCode",
        "OrganizationType",
        "Industry",
        "Website",
        "UserName",
        "Password",
        "Email",
        "ContactPersonName",
        "ContactPersonDesignation",
        "ContactPhone",
        "AddressLine1",
        "AddressLine2",
        "City",
        "State",
        "Country",
        "PostalCode",
        "MaxUserLimit",
        "LicenseStartDate",
        "LicenseEndDate",
        "Status",
        "ApprovedBy",
        "ApprovedDate",
        "RejectedBy",
        "RejectedDate",
        "RejectionReason",
        "IsActive",
        "CreatedBy",
        "CreatedDate",
        "UpdatedBy",
        "UpdatedDate",
    } == account_columns

    assert read_column_names(connection, "OrganizationCategoryAccess") == {
        "OrganizationCategoryAccessId",
        "OrganizationAccountId",
        "CategoryID",
        "CategorySampleID",
        "CreatedDate",
        "IsActive",
    }
    assert read_column_names(connection, "OrganizationCompanyProfileAccess") == {
        "OrganizationCompanyProfileAccessId",
        "OrganizationAccountId",
        "CompanyID",
    }
    assert read_column_names(connection, "OrganizationDrugAccess") == {
        "OrganizationDrugAccessId",
        "OrganizationAccountId",
        "DrugID",
    }
    assert read_column_names(connection, "OrganizationIndicationAccess") == {
        "OrganizationIndicationAccessId",
        "OrganizationAccountId",
        "IndicationID",
    }
    assert read_column_names(connection, "OrganizationMarketAccess") == {
        "OrganizationMarketAccessId",
        "OrganizationAccountId",
        "MarketID",
        "MarketSampleId",
    }
    assert read_column_names(connection, "OrganizationPermission") == {
        "OrganizationPermissionId",
        "OrganizationAccountId",
        "cp_CompanyMaster_PharmaID",
        "HC_TheropeticCategory_PharmaID",
        "HC_TheropeticCategory_EpidemID",
        "HC_Disease_Code_EpidemID",
        "ReportsCustomID",
        "importexportReportID",
        "CreatedDate",
        "IsActive",
    }
    assert read_column_names(connection, "OrganizationReportAccess") == {
        "OrganizationReportAccessId",
        "OrganizationAccountId",
        "ReportsID",
        "SampleID",
        "SampleTocID",
        "SpecialityID",
        "IsExecutiveAccess",
        "CreatedDate",
        "IsActive",
    }

    overview_columns = read_column_names(connection, "organization_overviews")
    assert {
        "organization_id",
        "organization_type",
        "renewal_date",
        "workspace_status",
        "workspace_health_percent",
        "licensed_modules",
        "available_areas",
        "organization_logins",
        "version",
        "created_at",
        "updated_at",
    } == overview_columns

    execution_columns = read_column_names(connection, "agent_action_executions")
    assert {
        "audit_pending",
        "audit_replay_attempts",
        "audit_last_attempt_at",
        "audit_last_error",
        "attempt_count",
        "reconciliation_status",
    }.issubset(execution_columns)

    proposal_columns = read_column_names(connection, "agent_action_proposals")
    assert {
        "resource_preconditions_json",
        "fingerprint_version",
    }.issubset(proposal_columns)

    actor_columns = read_column_names(connection, "nucleus_actor_mappings")
    assert {"workplace_user_id", "nucleus_actor_id"}.issubset(actor_columns)
    tombstone_columns = read_column_names(connection, "nucleus_access_tombstones")
    assert {
        "resource_type",
        "access_id",
        "organization_account_id",
        "version",
        "snapshot_json",
        "revoked_by",
        "revoked_at",
    }.issubset(tombstone_columns)
    execution_columns = read_column_names(connection, "agent_action_executions")
    assert {"executed_by_user_id", "nucleus_actor_id"}.issubset(
        execution_columns
    )

    proposal_indexes = read_index_names(connection, "agent_action_proposals")
    assert {
        "ix_agent_action_proposal_org_created",
        "ix_agent_action_proposal_requester_created",
        "ix_agent_action_proposal_status_created",
    }.issubset(proposal_indexes)
    assert "ix_agent_action_execution_audit_replay" in read_index_names(
        connection,
        "agent_action_executions",
    )
    assert "ix_agent_action_approval_progress" in read_index_names(
        connection,
        "agent_action_approvals",
    )
    assert "ix_agent_action_rollback_source" in read_index_names(
        connection,
        "agent_action_rollbacks",
    )


def test_fresh_database_upgrades_to_head_and_is_repeatable(tmp_path: Path) -> None:
    database_file_path = tmp_path / "fresh.db"
    run_alembic(database_file_path, "head")
    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        assert read_table_names(connection) == EXPECTED_DATABASE_TABLE_NAMES
        assert_head_and_hardening_schema(connection)


def test_database_from_initial_revision_upgrades_to_head(tmp_path: Path) -> None:
    database_file_path = tmp_path / "initial.db"
    run_alembic(database_file_path, "0001_initial")
    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        assert read_table_names(connection) == EXPECTED_DATABASE_TABLE_NAMES
        assert_head_and_hardening_schema(connection)


def test_0009_upgrade_adds_overview_without_touching_existing_rows(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "overview-upgrade.db"
    run_alembic(database_file_path, "0009_operational_hardening")

    with sqlite3.connect(database_file_path) as connection:
        connection.execute(
            "INSERT INTO organizations(id, display_name, environment, status, version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "org_upgrade_overview",
                "Upgrade Overview Organization",
                "sandbox",
                "active",
                4,
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.commit()

    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        assert_head_and_hardening_schema(connection)
        organization = connection.execute(
            "SELECT id, display_name, version FROM organizations "
            "WHERE id = 'org_upgrade_overview'"
        ).fetchone()
        assert organization == (
            "org_upgrade_overview",
            "Upgrade Overview Organization",
            4,
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM organization_overviews"
        ).fetchone() == (0,)


def test_0008_execution_is_preserved_by_upgrade_to_latest_head(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "upgrade.db"
    run_alembic(database_file_path, "0008_add_multi_approval_and_rollbacks")

    with sqlite3.connect(database_file_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO organizations(id, display_name, environment, status, version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "org_upgrade_001",
                "Upgrade Organization",
                "sandbox",
                "active",
                1,
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO users(id, display_name, email, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "usr_upgrade_001",
                "Upgrade User",
                "upgrade@example.test",
                "active",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO agent_action_proposals(id, organization_id, requested_by_user_id, action_name, arguments_json, changes_json, action_fingerprint, risk_level, resource_type, resource_id, status, observed_resource_version, approval_policy_json, expires_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "proposal_upgrade_001",
                "org_upgrade_001",
                "usr_upgrade_001",
                "update_organization_contact_email",
                '{"contact_email":"new@example.test"}',
                '[{"field":"contact_email","before":null,"after":"new@example.test"}]',
                "fingerprint",
                "low",
                "organization",
                "org_upgrade_001",
                "succeeded",
                1,
                '{"self_approval_allowed":true,"required_approver_permission":"organization.profile.update","minimum_approvals":1}',
                "2026-12-01 00:00:00",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO agent_action_executions(id, proposal_id, idempotency_key, outcome, attempt_count, audit_pending, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "execution_upgrade_001",
                "proposal_upgrade_001",
                "upgrade-idempotency-key",
                "succeeded",
                1,
                1,
                "2026-01-01 00:00:00",
                "2026-01-01 00:01:00",
            ),
        )
        connection.commit()

    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        assert_head_and_hardening_schema(connection)
        proposal = connection.execute(
            "SELECT resource_preconditions_json, fingerprint_version "
            "FROM agent_action_proposals WHERE id = 'proposal_upgrade_001'"
        ).fetchone()
        assert proposal is not None
        assert json.loads(proposal[0]) == [
            {
                "resource_type": "organization",
                "resource_id": "org_upgrade_001",
                "observed_version": 1,
            }
        ]
        assert proposal[1] == 2

        execution = connection.execute(
            "SELECT id, outcome, audit_pending, audit_replay_attempts, "
            "audit_last_attempt_at, audit_last_error FROM agent_action_executions"
        ).fetchone()
        assert execution == (
            "execution_upgrade_001",
            "succeeded",
            1,
            0,
            None,
            None,
        )
