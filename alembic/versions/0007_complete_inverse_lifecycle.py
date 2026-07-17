from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_complete_inverse_lifecycle"
down_revision: Union[str, None] = "0006_expand_operational_actions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("seat_assignments") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("revoked_by_user_id", sa.String(), nullable=True)
        )

    op.create_index(
        "ix_membership_lifecycle_lookup",
        "organization_memberships",
        ["organization_id", "user_id", "membership_status", "version"],
        unique=False,
    )
    op.create_index(
        "ix_seat_lifecycle_lookup",
        "seat_assignments",
        ["organization_id", "user_id", "status", "version"],
        unique=False,
    )
    op.create_index(
        "ix_report_access_lifecycle_lookup",
        "organization_report_access",
        ["organization_id", "report_id", "status", "version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_access_lifecycle_lookup",
        table_name="organization_report_access",
    )
    op.drop_index("ix_seat_lifecycle_lookup", table_name="seat_assignments")
    op.drop_index(
        "ix_membership_lifecycle_lookup",
        table_name="organization_memberships",
    )

    with op.batch_alter_table("seat_assignments") as batch_op:
        batch_op.drop_column("revoked_by_user_id")
        batch_op.drop_column("version")
