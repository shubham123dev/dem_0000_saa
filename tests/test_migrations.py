from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "0008_add_multi_approval_and_rollbacks"
EXPECTED_DATABASE_TABLE_NAMES = {
    "agent_action_approvals",
    "agent_action_executions",
    "agent_action_proposals",
    "agent_action_rollbacks",
    "alembic_version",
    "audit_events",
    "organization_memberships",
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
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def read_index_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA index_list({table_name})").fetchall()
    }


def assert_head_and_operational_columns(connection: sqlite3.Connection) -> None:
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert revision == (EXPECTED_HEAD,)
    assert "version" in read_column_names(connection, "organization_memberships")
    assert "version" in read_column_names(connection, "organization_seat_pools")
    assert "version" in read_column_names(connection, "organization_report_access")
    assert {"version", "revoked_by_user_id"}.issubset(
        read_column_names(connection, "seat_assignments")
    )
    assert "ix_membership_lifecycle_lookup" in read_index_names(
        connection, "organization_memberships"
    )
    assert "ix_seat_lifecycle_lookup" in read_index_names(
        connection, "seat_assignments"
    )
    assert "ix_report_access_lifecycle_lookup" in read_index_names(
        connection, "organization_report_access"
    )
    assert "ix_agent_action_approval_progress" in read_index_names(
        connection, "agent_action_approvals"
    )
    assert "ix_agent_action_rollback_source" in read_index_names(
        connection, "agent_action_rollbacks"
    )
    assert {
        "source_proposal_id",
        "rollback_proposal_id",
        "created_by_user_id",
        "created_at",
    }.issubset(read_column_names(connection, "agent_action_rollbacks"))
    assert {
        "observed_resource_version",
        "approval_policy_json",
        "cancelled_at",
        "stale_at",
    }.issubset(read_column_names(connection, "agent_action_proposals"))
    assert {
        "attempt_count",
        "last_attempt_at",
        "provider_operation_id",
        "reconciliation_status",
        "audit_pending",
    }.issubset(read_column_names(connection, "agent_action_executions"))


def test_fresh_database_upgrades_to_head_and_is_repeatable(tmp_path: Path) -> None:
    database_file_path = tmp_path / "fresh.db"
    run_alembic(database_file_path, "head")
    run_alembic(database_file_path, "head")
    with sqlite3.connect(database_file_path) as connection:
        assert read_table_names(connection) == EXPECTED_DATABASE_TABLE_NAMES
        assert_head_and_operational_columns(connection)


def test_database_from_initial_revision_upgrades_to_operational_head(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "initial.db"
    run_alembic(database_file_path, "0001_initial")
    run_alembic(database_file_path, "head")
    with sqlite3.connect(database_file_path) as connection:
        assert read_table_names(connection) == EXPECTED_DATABASE_TABLE_NAMES
        assert_head_and_operational_columns(connection)


def test_0005_rows_and_approval_are_preserved_through_0008_upgrade(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "upgrade.db"
    run_alembic(database_file_path, "0005_harden_agent_action_lifecycle")

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
                3,
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        for user_id, email in (
            ("usr_upgrade_001", "upgrade@example.test"),
            ("usr_upgrade_002", "upgrade2@example.test"),
        ):
            connection.execute(
                "INSERT INTO users(id, display_name, email, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    user_id,
                    email,
                    "active",
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:00:00",
                ),
            )
        connection.execute(
            "INSERT INTO organization_memberships(organization_id, user_id, role, membership_status, joined_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "org_upgrade_001",
                "usr_upgrade_001",
                "sandbox_admin",
                "active",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO organization_seat_pools(id, organization_id, seat_type, total_seats, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "pool_upgrade_001",
                "org_upgrade_001",
                "standard",
                2,
                "active",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO seat_assignments(id, organization_id, seat_pool_id, user_id, status, assigned_at, assigned_by_user_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "seat_upgrade_001",
                "org_upgrade_001",
                "pool_upgrade_001",
                "usr_upgrade_001",
                "active",
                "2026-01-01 00:00:00",
                "usr_upgrade_001",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO reports(id, external_report_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "report_upgrade_001",
                "EXT-001",
                "Upgrade Report",
                "active",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO organization_report_access(id, organization_id, report_id, access_level, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "access_upgrade_001",
                "org_upgrade_001",
                "report_upgrade_001",
                "view",
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
                "approved",
                3,
                '{"self_approval_allowed":true,"required_approver_permission":"organization.profile.update","minimum_approvals":1}',
                "2026-12-01 00:00:00",
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO agent_action_approvals(id, proposal_id, decision, decided_by_user_id, decided_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "approval_upgrade_001",
                "proposal_upgrade_001",
                "approved",
                "usr_upgrade_001",
                "2026-01-01 00:00:00",
            ),
        )
        connection.commit()

    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert_head_and_operational_columns(connection)
        assert connection.execute(
            "SELECT role, membership_status, version FROM organization_memberships"
        ).fetchone() == ("sandbox_admin", "active", 1)
        assert connection.execute(
            "SELECT total_seats, version FROM organization_seat_pools"
        ).fetchone() == (2, 1)
        assert connection.execute(
            "SELECT status, version, revoked_by_user_id FROM seat_assignments"
        ).fetchone() == ("active", 1, None)
        assert connection.execute(
            "SELECT access_level, status, version FROM organization_report_access"
        ).fetchone() == ("view", "active", 1)
        assert connection.execute(
            "SELECT id, status FROM agent_action_proposals"
        ).fetchone() == ("proposal_upgrade_001", "approved")
        assert connection.execute(
            "SELECT id, decided_by_user_id FROM agent_action_approvals"
        ).fetchone() == ("approval_upgrade_001", "usr_upgrade_001")

        connection.execute(
            "INSERT INTO agent_action_approvals(id, proposal_id, decision, decided_by_user_id, decided_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "approval_upgrade_002",
                "proposal_upgrade_001",
                "approved",
                "usr_upgrade_002",
                "2026-01-02 00:00:00",
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO agent_action_approvals(id, proposal_id, decision, decided_by_user_id, decided_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "approval_duplicate",
                    "proposal_upgrade_001",
                    "approved",
                    "usr_upgrade_001",
                    "2026-01-03 00:00:00",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO users(id, display_name, email, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "usr_duplicate_email",
                    "Duplicate",
                    "upgrade@example.test",
                    "active",
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:00:00",
                ),
            )
