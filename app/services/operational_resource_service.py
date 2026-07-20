from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import CreateUserCommand, UserDirectory
from app.adapters.user.provider import get_user_directory
from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    SeatAssignmentORM,
)
from app.domain.enums import (
    MembershipStatus,
    ReportAccessStatus,
    ReportStatus,
    Role,
    SeatAssignmentStatus,
    SeatPoolStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OperationalResourceConflictError(RuntimeError):
    pass


class OperationalResourceNotFoundError(LookupError):
    pass


class OperationalResourceService:
    def __init__(
        self,
        session: AsyncSession,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._users = user_directory or get_user_directory()

    async def inspect_invitation(self, organization_id: str, email: str) -> dict:
        user = await self._users.get_by_email(email)
        membership = None
        if user is not None:
            membership = await self._membership(organization_id, user.id)
        return {
            "user_id": user.id if user else None,
            "membership_status": membership.membership_status if membership else None,
            "role": membership.role if membership else None,
            "version": membership.version if membership else 0,
            "creation_enabled": self._users.creation_enabled,
        }

    async def invite_user(
        self,
        *,
        organization_id: str,
        email: str,
        display_name: str,
        role: str,
        requested_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_invitation(organization_id, email)
        if state["version"] != expected_version or state["membership_status"] is not None:
            return None
        user = await self._users.get_by_email(email)
        if user is None:
            user = await self._users.create_user(
                CreateUserCommand(
                    display_name=display_name,
                    email=email,
                    actor_user_id=requested_by_user_id,
                )
            )
        self._session.add(
            OrganizationMembershipORM(
                organization_id=organization_id,
                user_id=user.id,
                role=role,
                membership_status=MembershipStatus.INVITED.value,
                version=1,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return None
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": role,
            "membership_status": MembershipStatus.INVITED.value,
            "version": 1,
        }

    async def inspect_membership(self, organization_id: str, user_id: str) -> dict:
        membership = await self._membership(organization_id, user_id)
        if membership is None:
            raise OperationalResourceNotFoundError("Organization membership was not found")
        active_admin_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(OrganizationMembershipORM)
                .where(
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.membership_status == MembershipStatus.ACTIVE.value,
                    OrganizationMembershipORM.role == Role.SANDBOX_ADMIN.value,
                )
            )
            or 0
        )
        active_seat = await self._session.scalar(
            select(SeatAssignmentORM).where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.user_id == user_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
            )
        )
        return {
            "user_id": user_id,
            "role": membership.role,
            "membership_status": membership.membership_status,
            "version": membership.version,
            "active_admin_count": active_admin_count,
            "has_active_seat": active_seat is not None,
        }

    async def activate_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
        expected_version: int,
    ) -> dict | None:
        now = _utcnow()
        result = await self._session.execute(
            update(OrganizationMembershipORM)
            .where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
                OrganizationMembershipORM.membership_status == MembershipStatus.INVITED.value,
                OrganizationMembershipORM.version == expected_version,
            )
            .values(
                membership_status=MembershipStatus.ACTIVE.value,
                joined_at=now,
                version=expected_version + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return await self.inspect_membership(organization_id, user_id)

    async def update_member_role(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_membership(organization_id, user_id)
        if (
            state["version"] != expected_version
            or state["membership_status"] != MembershipStatus.ACTIVE.value
            or (
                state["role"] == Role.SANDBOX_ADMIN.value
                and role != Role.SANDBOX_ADMIN.value
                and state["active_admin_count"] <= 1
            )
        ):
            return None
        now = _utcnow()
        result = await self._session.execute(
            update(OrganizationMembershipORM)
            .where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
                OrganizationMembershipORM.membership_status == MembershipStatus.ACTIVE.value,
                OrganizationMembershipORM.role == state["role"],
                OrganizationMembershipORM.version == expected_version,
            )
            .values(role=role, version=expected_version + 1, updated_at=now)
        )
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return await self.inspect_membership(organization_id, user_id)

    async def remove_member(
        self,
        *,
        organization_id: str,
        user_id: str,
        requested_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_membership(organization_id, user_id)
        if (
            user_id == requested_by_user_id
            or state["version"] != expected_version
            or state["membership_status"] not in {
                MembershipStatus.ACTIVE.value,
                MembershipStatus.INVITED.value,
                MembershipStatus.SUSPENDED.value,
            }
            or state["has_active_seat"]
            or (
                state["membership_status"] == MembershipStatus.ACTIVE.value
                and state["role"] == Role.SANDBOX_ADMIN.value
                and state["active_admin_count"] <= 1
            )
        ):
            return None
        now = _utcnow()
        result = await self._session.execute(
            update(OrganizationMembershipORM)
            .where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
                OrganizationMembershipORM.version == expected_version,
            )
            .values(
                membership_status=MembershipStatus.REMOVED.value,
                version=expected_version + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return await self.inspect_membership(organization_id, user_id)

    async def inspect_seat_assignment(
        self,
        organization_id: str,
        user_id: str,
        seat_type: str,
    ) -> dict:
        membership = await self._membership(organization_id, user_id)
        if membership is None or membership.membership_status != MembershipStatus.ACTIVE.value:
            raise OperationalResourceNotFoundError("Active organization member was not found")
        pool = await self._session.scalar(
            select(OrganizationSeatPoolORM).where(
                OrganizationSeatPoolORM.organization_id == organization_id,
                OrganizationSeatPoolORM.seat_type == seat_type,
                OrganizationSeatPoolORM.status == SeatPoolStatus.ACTIVE.value,
            )
        )
        if pool is None:
            raise OperationalResourceNotFoundError("Active seat pool was not found")
        active_count = int(
            await self._session.scalar(
                select(func.count()).select_from(SeatAssignmentORM).where(
                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                    SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                )
            )
            or 0
        )
        assignment = await self._session.scalar(
            select(SeatAssignmentORM).where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.seat_pool_id == pool.id,
                SeatAssignmentORM.user_id == user_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
            )
        )
        return {
            "seat_pool_id": pool.id,
            "seat_type": pool.seat_type,
            "pool_version": pool.version,
            "total_seats": max(pool.total_seats, 0),
            "active_assignments": active_count,
            "has_active_seat": assignment is not None,
            "assignment_id": assignment.id if assignment else None,
            "assignment_version": assignment.version if assignment else 0,
        }

    async def assign_seat(
        self,
        *,
        organization_id: str,
        user_id: str,
        seat_type: str,
        assigned_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_seat_assignment(organization_id, user_id, seat_type)
        if (
            state["pool_version"] != expected_version
            or state["has_active_seat"]
            or state["active_assignments"] >= state["total_seats"]
        ):
            return None
        pool_result = await self._session.execute(
            update(OrganizationSeatPoolORM)
            .where(
                OrganizationSeatPoolORM.id == state["seat_pool_id"],
                OrganizationSeatPoolORM.version == expected_version,
            )
            .values(version=expected_version + 1, updated_at=_utcnow())
        )
        if pool_result.rowcount != 1:
            await self._session.rollback()
            return None
        assignment = SeatAssignmentORM(
            id=uuid.uuid4().hex,
            organization_id=organization_id,
            seat_pool_id=state["seat_pool_id"],
            user_id=user_id,
            status=SeatAssignmentStatus.ACTIVE.value,
            version=1,
            assigned_at=_utcnow(),
            assigned_by_user_id=assigned_by_user_id,
        )
        self._session.add(assignment)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return None
        return {
            "assignment_id": assignment.id,
            "user_id": user_id,
            "seat_pool_id": state["seat_pool_id"],
            "seat_type": seat_type,
            "pool_version": expected_version + 1,
            "assignment_version": 1,
        }

    async def revoke_seat(
        self,
        *,
        organization_id: str,
        user_id: str,
        seat_type: str,
        revoked_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_seat_assignment(organization_id, user_id, seat_type)
        if not state["has_active_seat"] or state["assignment_version"] != expected_version:
            return None
        now = _utcnow()
        assignment_result = await self._session.execute(
            update(SeatAssignmentORM)
            .where(
                SeatAssignmentORM.id == state["assignment_id"],
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                SeatAssignmentORM.version == expected_version,
            )
            .values(
                status=SeatAssignmentStatus.REVOKED.value,
                version=expected_version + 1,
                revoked_at=now,
                revoked_by_user_id=revoked_by_user_id,
                updated_at=now,
            )
        )
        if assignment_result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.execute(
            update(OrganizationSeatPoolORM)
            .where(OrganizationSeatPoolORM.id == state["seat_pool_id"])
            .values(
                version=OrganizationSeatPoolORM.version + 1,
                updated_at=now,
            )
        )
        await self._session.commit()
        return {
            "assignment_id": state["assignment_id"],
            "user_id": user_id,
            "seat_type": seat_type,
            "status": SeatAssignmentStatus.REVOKED.value,
            "assignment_version": expected_version + 1,
        }

    async def inspect_report_grant(self, organization_id: str, report_id: str) -> dict:
        report = await self._session.get(ReportORM, report_id)
        if report is None or report.status != ReportStatus.ACTIVE.value:
            raise OperationalResourceNotFoundError("Active report was not found")
        access = await self._session.scalar(
            select(OrganizationReportAccessORM).where(
                OrganizationReportAccessORM.organization_id == organization_id,
                OrganizationReportAccessORM.report_id == report_id,
            )
        )
        return {
            "report_id": report_id,
            "title": report.title,
            "access_level": access.access_level if access else None,
            "status": access.status if access else None,
            "version": access.version if access else 0,
        }

    async def grant_report_access(
        self,
        *,
        organization_id: str,
        report_id: str,
        access_level: str,
        granted_by_user_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_report_grant(organization_id, report_id)
        now = _utcnow()
        if state["version"] != expected_version:
            return None
        if expected_version == 0:
            access = OrganizationReportAccessORM(
                id=uuid.uuid4().hex,
                organization_id=organization_id,
                report_id=report_id,
                access_level=access_level,
                status=ReportAccessStatus.ACTIVE.value,
                version=1,
                granted_at=now,
                granted_by_user_id=granted_by_user_id,
            )
            self._session.add(access)
            try:
                await self._session.commit()
            except IntegrityError:
                await self._session.rollback()
                return None
            return {
                "report_id": report_id,
                "access_level": access_level,
                "status": ReportAccessStatus.ACTIVE.value,
                "version": 1,
            }
        result = await self._session.execute(
            update(OrganizationReportAccessORM)
            .where(
                OrganizationReportAccessORM.organization_id == organization_id,
                OrganizationReportAccessORM.report_id == report_id,
                OrganizationReportAccessORM.version == expected_version,
            )
            .values(
                access_level=access_level,
                status=ReportAccessStatus.ACTIVE.value,
                version=expected_version + 1,
                granted_at=now,
                granted_by_user_id=granted_by_user_id,
                expires_at=None,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return {
            "report_id": report_id,
            "access_level": access_level,
            "status": ReportAccessStatus.ACTIVE.value,
            "version": expected_version + 1,
        }

    async def revoke_report_access(
        self,
        *,
        organization_id: str,
        report_id: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_report_grant(organization_id, report_id)
        if state["status"] != ReportAccessStatus.ACTIVE.value or state["version"] != expected_version:
            return None
        now = _utcnow()
        result = await self._session.execute(
            update(OrganizationReportAccessORM)
            .where(
                OrganizationReportAccessORM.organization_id == organization_id,
                OrganizationReportAccessORM.report_id == report_id,
                OrganizationReportAccessORM.status == ReportAccessStatus.ACTIVE.value,
                OrganizationReportAccessORM.version == expected_version,
            )
            .values(
                status=ReportAccessStatus.REVOKED.value,
                version=expected_version + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return {
            "report_id": report_id,
            "access_level": state["access_level"],
            "status": ReportAccessStatus.REVOKED.value,
            "version": expected_version + 1,
        }

    async def _membership(
        self,
        organization_id: str,
        user_id: str,
    ) -> OrganizationMembershipORM | None:
        return await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
            )
        )
