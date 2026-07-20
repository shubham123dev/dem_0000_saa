"""replace the local users table with the Test_user1 directory

Revision ID: 0018_replace_local_users
Revises: 0017_action_control_plane
Create Date: 2026-07-20

The external dbmr_Database_Nucleus.dbo.Test_user1 table is deliberately
outside Alembic metadata. This migration only removes local foreign keys
and the obsolete local users table.
"""

from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_replace_local_users"
down_revision: Union[str, None] = "0017_action_control_plane"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_USER_FOREIGN_KEYS = (
    ("organization_memberships", "user_id"),
    ("seat_assignments", "user_id"),
    ("agent_action_proposals", "requested_by_user_id"),
    ("agent_action_approvals", "decided_by_user_id"),
    ("agent_action_executions", "executed_by_user_id"),
    ("agent_action_rollbacks", "created_by_user_id"),
    ("agent_conversations", "created_by_user_id"),
    ("agent_runs", "requested_by_user_id"),
    ("workplace_resource_tombstones", "deleted_by_user_id"),
    ("nucleus_actor_mappings", "workplace_user_id"),
)
_SQLITE_NAMING = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
}


def _foreign_key(table_name: str, column_name: str) -> dict | None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if (
            foreign_key.get("referred_table") == "users"
            and column_name in foreign_key.get("constrained_columns", ())
        ):
            return foreign_key
    return None


def _drop_user_foreign_key(table_name: str, column_name: str) -> None:
    foreign_key = _foreign_key(table_name, column_name)
    if foreign_key is None:
        return
    bind = op.get_bind()
    name = foreign_key.get("name")
    if bind.dialect.name == "sqlite":
        constraint_name = name or f"fk_{table_name}_{column_name}_users"
        with op.batch_alter_table(
            table_name,
            recreate="always",
            naming_convention=_SQLITE_NAMING,
        ) as batch:
            batch.drop_constraint(constraint_name, type_="foreignkey")
        return
    if not name:
        raise RuntimeError(
            f"Cannot safely drop unnamed user foreign key on {table_name}.{column_name}"
        )
    op.drop_constraint(name, table_name, type_="foreignkey")


def _require_canonical_production_ids() -> None:
    # The one-time mapper must run before this migration on a populated
    # production database. Sandbox databases intentionally use synthetic
    # IDs and are replaced by the in-memory sandbox adapter after upgrade.
    if not os.getenv("WORKPLACE_NUCLEUS_USER_DATABASE_URL"):
        return
    bind = op.get_bind()
    invalid = [
        str(row[0])
        for row in bind.execute(sa.text("SELECT id FROM users")).fetchall()
        if not str(row[0]).isdigit()
    ]
    if invalid:
        sample = ", ".join(invalid[:5])
        raise RuntimeError(
            "Legacy users remain unmapped to Test_user1.UserID values. "
            "Run `python -m scripts.map_legacy_users_to_test_user1 --apply` "
            f"before upgrading. Example IDs: {sample}"
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return
    _require_canonical_production_ids()
    for table_name, column_name in _USER_FOREIGN_KEYS:
        if table_name in sa.inspect(op.get_bind()).get_table_names():
            _drop_user_foreign_key(table_name, column_name)
    op.drop_table("users")


def downgrade() -> None:
    raise RuntimeError(
        "0018 is intentionally irreversible: user profiles now live only in Test_user1"
    )
