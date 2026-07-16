"""remove chatbot-specific permissions from the workplace schema

Revision ID: 0003_remove_chatbot_permissions
Revises: 0002_expand_organization_domain
Create Date: 2026-07-16

SARA/chatbot integration is outside this repository. This migration removes
permission rows that were briefly seeded for a future chatbot gateway so both
fresh and already-upgraded databases reflect the same repository boundary.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_remove_chatbot_permissions"
down_revision: Union[str, None] = "0002_expand_organization_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHATBOT_PERMISSIONS = (
    "chatbot.report.query",
    "chatbot.report.summarize",
)


def upgrade() -> None:
    role_permissions = sa.table(
        "role_permissions",
        sa.column("permission", sa.String()),
    )
    op.execute(
        role_permissions.delete().where(
            role_permissions.c.permission.in_(_CHATBOT_PERMISSIONS)
        )
    )


def downgrade() -> None:
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String()),
        sa.column("permission", sa.String()),
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role": "sandbox_admin", "permission": "chatbot.report.query"},
            {"role": "sandbox_admin", "permission": "chatbot.report.summarize"},
            {"role": "sandbox_reader", "permission": "chatbot.report.query"},
        ],
    )
