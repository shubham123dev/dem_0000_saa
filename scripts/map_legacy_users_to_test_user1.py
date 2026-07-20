"""Map populated legacy local users to Test_user1.UserID before Alembic 0018.

Dry-run by default. The apply mode performs all local reference rewrites in
one transaction while the legacy users table and its foreign keys still
exist. Every EmailID must resolve to exactly one Test_user1 row.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from dataclasses import dataclass

from sqlalchemy import text

from app.adapters.user.provider import get_user_directory
from app.db.session import get_sessionmaker

_REFERENCES = (
    ("organization_memberships", "user_id"),
    ("seat_assignments", "user_id"),
    ("seat_assignments", "assigned_by_user_id"),
    ("seat_assignments", "revoked_by_user_id"),
    ("organization_report_access", "granted_by_user_id"),
    ("audit_events", "actor_user_id"),
    ("agent_action_proposals", "requested_by_user_id"),
    ("agent_action_approvals", "decided_by_user_id"),
    ("agent_action_executions", "executed_by_user_id"),
    ("agent_action_rollbacks", "created_by_user_id"),
    ("agent_conversations", "created_by_user_id"),
    ("agent_runs", "requested_by_user_id"),
    ("workplace_resource_tombstones", "deleted_by_user_id"),
    ("nucleus_actor_mappings", "workplace_user_id"),
)


@dataclass(frozen=True)
class Mapping:
    old_id: str
    new_id: str
    email: str
    display_name: str


async def build_mappings() -> tuple[Mapping, ...]:
    directory = get_user_directory()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id, display_name, email FROM users "
                    "ORDER BY id ASC"
                )
            )
        ).mappings().all()
    mappings: list[Mapping] = []
    errors: list[str] = []
    for row in rows:
        external = await directory.get_by_email(str(row["email"]))
        if external is None:
            errors.append(
                f"{row['id']}: no Test_user1 match for {row['email']}"
            )
            continue
        mappings.append(
            Mapping(
                old_id=str(row["id"]),
                new_id=external.id,
                email=str(row["email"]),
                display_name=str(row["display_name"]),
            )
        )
    if errors:
        raise RuntimeError("Legacy mapping failed:\n" + "\n".join(errors))
    new_ids = [item.new_id for item in mappings]
    if len(new_ids) != len(set(new_ids)):
        raise RuntimeError(
            "Two legacy users resolve to the same Test_user1.UserID; resolve duplicates manually"
        )
    return tuple(mappings)


async def apply_mappings(mappings: tuple[Mapping, ...]) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        async with session.begin():
            for item in mappings:
                if item.old_id == item.new_id:
                    continue
                target_exists = await session.scalar(
                    text("SELECT COUNT(*) FROM users WHERE id = :new_id"),
                    {"new_id": item.new_id},
                )
                if int(target_exists or 0):
                    raise RuntimeError(
                        f"Target local ID already exists: {item.new_id}"
                    )
                digest = hashlib.sha256(item.old_id.encode("utf-8")).hexdigest()[:16]
                legacy_email = f"legacy-{digest}@invalid.local"
                await session.execute(
                    text("UPDATE users SET email = :legacy_email WHERE id = :old_id"),
                    {"legacy_email": legacy_email, "old_id": item.old_id},
                )
                await session.execute(
                    text(
                        "INSERT INTO users "
                        "(id, display_name, email, status, created_at, updated_at) "
                        "SELECT :new_id, display_name, :email, status, created_at, updated_at "
                        "FROM users WHERE id = :old_id"
                    ),
                    {
                        "new_id": item.new_id,
                        "email": item.email,
                        "old_id": item.old_id,
                    },
                )
                for table_name, column_name in _REFERENCES:
                    await session.execute(
                        text(
                            f"UPDATE {table_name} SET {column_name} = :new_id "
                            f"WHERE {column_name} = :old_id"
                        ),
                        {"new_id": item.new_id, "old_id": item.old_id},
                    )
                await session.execute(
                    text("DELETE FROM users WHERE id = :old_id"),
                    {"old_id": item.old_id},
                )


async def main(apply: bool) -> None:
    mappings = await build_mappings()
    for item in mappings:
        marker = "=" if item.old_id == item.new_id else "->"
        print(f"{item.old_id} {marker} {item.new_id}  {item.email}")
    if not apply:
        print("Dry run only. Re-run with --apply after reviewing every mapping.")
        return
    await apply_mappings(mappings)
    print(f"Applied {len(mappings)} canonical user mappings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.apply))
