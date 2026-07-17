from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATABASE_TABLE_NAMES = {
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
    alembic_environment = os.environ.copy()
    alembic_environment["WORKPLACE_DATABASE_URL"] = (
        f"sqlite+aiosqlite:///{database_file_path.as_posix()}"
    )
    return alembic_environment


def run_alembic_upgrade(database_file_path: Path) -> None:
    completed_upgrade_process = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPOSITORY_ROOT,
        env=build_alembic_environment(database_file_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed_upgrade_process.returncode == 0, (
        completed_upgrade_process.stdout + completed_upgrade_process.stderr
    )


def read_table_names(database_connection: sqlite3.Connection) -> set[str]:
    table_rows = database_connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {table_row[0] for table_row in table_rows if not table_row[0].startswith("sqlite_")}


def create_legacy_database_schema(database_file_path: Path) -> None:
    with sqlite3.connect(database_file_path) as database_connection:
        database_connection.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE organizations (
                id TEXT PRIMARY KEY NOT NULL,
                display_name TEXT NOT NULL,
                legal_name TEXT,
                contact_email TEXT,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );

            CREATE TABLE employees (
                id TEXT PRIMARY KEY NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );

            CREATE TABLE employee_organization_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                role TEXT NOT NULL,
                CONSTRAINT fk_legacy_role_employee
                    FOREIGN KEY(employee_id) REFERENCES employees(id),
                CONSTRAINT fk_legacy_role_organization
                    FOREIGN KEY(organization_id) REFERENCES organizations(id),
                CONSTRAINT uq_employee_org_role
                    UNIQUE(employee_id, organization_id, role)
            );

            CREATE TABLE role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                permission TEXT NOT NULL,
                CONSTRAINT uq_role_permission UNIQUE(role, permission)
            );

            CREATE TABLE audit_events (
                id TEXT PRIMARY KEY NOT NULL,
                actor_employee_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                outcome TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                details_json JSON,
                created_at DATETIME NOT NULL
            );

            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL
            );

            INSERT INTO alembic_version(version_num)
            VALUES ('0001_initial');

            INSERT INTO organizations(
                id,
                display_name,
                legal_name,
                contact_email,
                environment,
                status,
                version,
                created_at,
                updated_at
            ) VALUES (
                'org_legacy_001',
                'Legacy Organization',
                'Legacy Organization Private Limited',
                'legacy@example.test',
                'sandbox',
                'active',
                1,
                '2026-01-01 00:00:00',
                '2026-01-01 00:00:00'
            );

            INSERT INTO employees(
                id,
                display_name,
                email,
                status,
                created_at,
                updated_at
            ) VALUES (
                'emp_legacy_001',
                'Legacy Employee',
                'legacy.employee@example.test',
                'active',
                '2026-01-01 00:00:00',
                '2026-01-01 00:00:00'
            );

            INSERT INTO employee_organization_roles(
                employee_id,
                organization_id,
                role
            ) VALUES
                ('emp_legacy_001', 'org_legacy_001', 'sandbox_reader'),
                ('emp_legacy_001', 'org_legacy_001', 'sandbox_admin');

            INSERT INTO role_permissions(role, permission)
            VALUES
                ('sandbox_reader', 'organization.profile.read'),
                ('sandbox_reader', 'chatbot.report.query'),
                ('sandbox_admin', 'chatbot.report.summarize');

            INSERT INTO audit_events(
                id,
                actor_employee_id,
                organization_id,
                event_type,
                operation,
                outcome,
                resource_type,
                resource_id,
                details_json,
                created_at
            ) VALUES (
                'audit_legacy_001',
                'emp_legacy_001',
                'org_legacy_001',
                'organization.profile.read',
                'read',
                'success',
                'organization',
                'org_legacy_001',
                '{}',
                '2026-01-01 00:00:00'
            );
            """
        )


def test_fresh_database_upgrades_to_head_and_is_repeatable(tmp_path: Path) -> None:
    database_file_path = tmp_path / "fresh_migration.db"

    run_alembic_upgrade(database_file_path)
    run_alembic_upgrade(database_file_path)

    with sqlite3.connect(database_file_path) as database_connection:
        assert read_table_names(database_connection) == EXPECTED_DATABASE_TABLE_NAMES
        current_revision = database_connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert current_revision == ("0003_remove_chatbot_permissions",)


def test_legacy_database_upgrade_preserves_identity_membership_and_audit_data(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "legacy_migration.db"
    create_legacy_database_schema(database_file_path)

    run_alembic_upgrade(database_file_path)
    run_alembic_upgrade(database_file_path)

    with sqlite3.connect(database_file_path) as database_connection:
        assert read_table_names(database_connection) == EXPECTED_DATABASE_TABLE_NAMES

        migrated_user = database_connection.execute(
            "SELECT id, display_name, email, status FROM users WHERE id = ?",
            ("emp_legacy_001",),
        ).fetchone()
        assert migrated_user == (
            "emp_legacy_001",
            "Legacy Employee",
            "legacy.employee@example.test",
            "active",
        )

        migrated_memberships = database_connection.execute(
            "SELECT organization_id, user_id, role, membership_status, "
            "joined_at, created_at, updated_at "
            "FROM organization_memberships "
            "WHERE organization_id = ? AND user_id = ?",
            ("org_legacy_001", "emp_legacy_001"),
        ).fetchall()
        assert len(migrated_memberships) == 1
        assert migrated_memberships[0][0:4] == (
            "org_legacy_001",
            "emp_legacy_001",
            "sandbox_reader",
            "active",
        )
        assert all(timestamp_value is not None for timestamp_value in migrated_memberships[0][4:7])

        migrated_audit_actor = database_connection.execute(
            "SELECT actor_user_id FROM audit_events WHERE id = ?",
            ("audit_legacy_001",),
        ).fetchone()
        assert migrated_audit_actor == ("emp_legacy_001",)

        remaining_permissions = {
            permission_row[0]
            for permission_row in database_connection.execute(
                "SELECT permission FROM role_permissions"
            ).fetchall()
        }
        assert remaining_permissions == {"organization.profile.read"}

        current_revision = database_connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert current_revision == ("0003_remove_chatbot_permissions",)


def test_legacy_upgrade_enforces_one_membership_per_user_and_organization(
    tmp_path: Path,
) -> None:
    database_file_path = tmp_path / "legacy_membership_constraint.db"
    create_legacy_database_schema(database_file_path)
    run_alembic_upgrade(database_file_path)

    with sqlite3.connect(database_file_path) as database_connection:
        with pytest.raises(sqlite3.IntegrityError):
            database_connection.execute(
                "INSERT INTO organization_memberships(" 
                "organization_id, user_id, role, membership_status, "
                "joined_at, created_at, updated_at" 
                ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "org_legacy_001",
                    "emp_legacy_001",
                    "sandbox_admin",
                    "active",
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:00:00",
                ),
            )
