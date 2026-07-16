"""Idempotent seed for deterministic synthetic sandbox data.

Run as a module::

    python -m app.db.seed

Seeding is idempotent: running it twice never produces duplicate data. The
seed function accepts an existing ``AsyncSession`` so tests can reuse it against
isolated temporary databases.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.orm_models import (
    AuditEventORM,  # noqa: F401  (ensures table is registered on metadata)
    EmployeeORM,
    EmployeeOrganizationRoleORM,
    OrganizationORM,
    RolePermissionORM,
)
from app.db.session import get_engine, get_sessionmaker
from app.domain.enums import (
    ROLE_PERMISSIONS,
    EmployeeStatus,
    Environment,
    OrganizationStatus,
    Role,
)

# --- Deterministic synthetic seed data -------------------------------------

ORGANIZATION = {
    "id": "org_sandbox_001",
    "display_name": "Demo Enterprise Sandbox",
    "legal_name": "Demo Enterprise Private Limited",
    "contact_email": "operations@example.test",
    "environment": Environment.SANDBOX.value,
    "status": OrganizationStatus.ACTIVE.value,
    "version": 1,
}

EMPLOYEES = [
    {
        "id": "emp_admin_001",
        "display_name": "Admin Employee",
        "email": "admin@example.test",
        "status": EmployeeStatus.ACTIVE.value,
    },
    {
        "id": "emp_reader_001",
        "display_name": "Read Only Employee",
        "email": "reader@example.test",
        "status": EmployeeStatus.ACTIVE.value,
    },
    {
        "id": "emp_outsider_001",
        "display_name": "Outside Employee",
        "email": "outsider@example.test",
        "status": EmployeeStatus.ACTIVE.value,
    },
]

# (employee_id, organization_id, role) — the outsider intentionally has none.
EMPLOYEE_ROLES = [
    ("emp_admin_001", "org_sandbox_001", Role.SANDBOX_ADMIN.value),
    ("emp_reader_001", "org_sandbox_001", Role.SANDBOX_READER.value),
]


async def _upsert_organization(session: AsyncSession) -> None:
    existing = await session.get(OrganizationORM, ORGANIZATION["id"])
    if existing is None:
        session.add(OrganizationORM(**ORGANIZATION))


async def _upsert_employees(session: AsyncSession) -> None:
    for data in EMPLOYEES:
        existing = await session.get(EmployeeORM, data["id"])
        if existing is None:
            session.add(EmployeeORM(**data))


async def _upsert_employee_roles(session: AsyncSession) -> None:
    for employee_id, organization_id, role in EMPLOYEE_ROLES:
        stmt = select(EmployeeOrganizationRoleORM).where(
            EmployeeOrganizationRoleORM.employee_id == employee_id,
            EmployeeOrganizationRoleORM.organization_id == organization_id,
            EmployeeOrganizationRoleORM.role == role,
        )
        if (await session.execute(stmt)).scalar_one_or_none() is None:
            session.add(
                EmployeeOrganizationRoleORM(
                    employee_id=employee_id,
                    organization_id=organization_id,
                    role=role,
                )
            )


async def _upsert_role_permissions(session: AsyncSession) -> None:
    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            stmt = select(RolePermissionORM).where(
                RolePermissionORM.role == role.value,
                RolePermissionORM.permission == permission.value,
            )
            if (await session.execute(stmt)).scalar_one_or_none() is None:
                session.add(
                    RolePermissionORM(role=role.value, permission=permission.value)
                )


async def seed(session: AsyncSession) -> None:
    """Idempotently seed all synthetic data into the provided session."""

    await _upsert_organization(session)
    await _upsert_employees(session)
    await _upsert_employee_roles(session)
    await _upsert_role_permissions(session)
    await session.commit()


async def _run() -> None:
    engine = get_engine()
    # Ensure tables exist even if the seed is run before/without Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await seed(session)
    await engine.dispose()
    print("Seed complete (idempotent). Organization: org_sandbox_001")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
