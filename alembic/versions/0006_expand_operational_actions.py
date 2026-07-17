from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_expand_operational_actions"
down_revision: Union[str, None] = "0005_harden_agent_action_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_unique_constraint("uq_users_email", ["email"])

    with op.batch_alter_table("organization_memberships") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )

    with op.batch_alter_table("organization_seat_pools") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )

    with op.batch_alter_table("organization_report_access") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("organization_report_access") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("organization_seat_pools") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("organization_memberships") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
