from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "0006_expand_operational_actions"
EXPECTED_DATABASE_TABLE_NAMES = {
    "agent_action_approvals",
    "agent_action_executions",
    "agent_action_proposals",
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


def assert_head_and_operational_columns(connection: sqlite3.Connection) -> None:
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert revision == (EXPECTED_HEAD,)
    assert "version" in read_column_names(connection, "organization_memberships")
    assert "version" in read_column_names(connection, "organization_seat_pools")
    assert "version" in read_column_names(connection, "organization_report_access")
    proposal_columns = read_column_names(connection, "agent_action_proposals")
    assert {
        "observed_resource_version",
        "approval_policy_json",
        "cancelled_at",
        "stale_at",
    }.issubset(proposal_columns)
    execution_columns = read_column_names(connection, "agent_action_executions")
    assert {
        "attempt_count",
        "last_attempt_at",
        "provider_operation_id",
        "reconciliation_status",
        "audit_pending",
    }.issubset(execution_columns)


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


def test_0005_rows_are_preserved_by_0006_upgrade(tmp_path: Path) -> None:
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
        connection.commit()

    run_alembic(database_file_path, "head")

    with sqlite3.connect(database_file_path) as connection:
        assert_head_and_operational_columns(connection)
        membership = connection.execute(
            "SELECT role, membership_status, version FROM organization_memberships"
        ).fetchone()
        assert membership == ("sandbox_admin", "active", 1)
        seat_pool = connection.execute(
            "SELECT total_seats, version FROM organization_seat_pools"
        ).fetchone()
        assert seat_pool == (2, 1)
        report_access = connection.execute(
            "SELECT access_level, status, version FROM organization_report_access"
        ).fetchone()
        assert report_access == ("view", "active", 1)
        proposal = connection.execute(
            "SELECT id, status FROM agent_action_proposals"
        ).fetchone()
        assert proposal == ("proposal_upgrade_001", "approved")

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
