"""add multi-resource action preconditions

Revision ID: 0012_resource_preconditions
Revises: 0011_nucleus_organization_schema
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_resource_preconditions"
down_revision: Union[str, None] = "0011_nucleus_organization_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.add_column(
            sa.Column(
                "resource_preconditions_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "fingerprint_version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("2"),
            )
        )

    proposals = sa.table(
        "agent_action_proposals",
        sa.column("id", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column("resource_id", sa.String()),
        sa.column("observed_resource_version", sa.Integer()),
        sa.column("resource_preconditions_json", sa.JSON()),
        sa.column("fingerprint_version", sa.Integer()),
    )
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.select(
                proposals.c.id,
                proposals.c.resource_type,
                proposals.c.resource_id,
                proposals.c.observed_resource_version,
            )
        ).mappings()
    )
    for row in rows:
        connection.execute(
            proposals.update()
            .where(proposals.c.id == row["id"])
            .values(
                resource_preconditions_json=[
                    {
                        "resource_type": row["resource_type"],
                        "resource_id": row["resource_id"],
                        "observed_version": row["observed_resource_version"],
                    }
                ],
                fingerprint_version=2,
            )
        )

    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.alter_column(
            "fingerprint_version",
            existing_type=sa.Integer(),
            server_default=sa.text("3"),
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_action_proposals") as batch_op:
        batch_op.drop_column("fingerprint_version")
        batch_op.drop_column("resource_preconditions_json")
