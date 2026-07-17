from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    SeatAssignmentORM,
    UserORM,
)
from app.domain.enums import (
    MembershipStatus,
    ReportAccessStatus,
    ReportStatus,
    SeatAssignmentStatus,
    SeatPoolStatus,
    UserStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OperationalResourceConflictError(RuntimeError):
    pass


class OperationalResourceNotFoundError(LookupError):
    pass


class OperationalResourceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect_invitation(self, organization_id: str, email: str) -> dict:
        user_result = await self._session.execute(select(UserORM).where(UserORM.email == email))
        user = user_result.scalar_one_or_none()
        membership = None
        if user is not None:
            membership_result = await self._session.execute(
                select(OrganizationMembershipORM).where(
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.user_id == user.id,
                )
            )
            membership = membership_result.scalar_one_or_none()
        return {
            "user_id": user.id if user is not None else None,
            "membership_status": membership.membership_status if membership is not None else None,
            "role": membership.role if membership is not None else None,
            "version": membership.version if membership is not None else 0,
        }

    async def invite_user(
        self,
        *,
        organization_id: str,
        email: str,
        display_name: str,
        role: str,
        expected_version: int,
    ) -> dict | None:
        state = await self.inspect_invitation(organization_id, email)
        if state["version"] != expected_version or state["membership_status"] is not None:
            return None
        user_id = state["user_id"] or self._user_id_for_email(email)
        if state["user_id"] is None:
            self._session.add(
                UserORM(
                    id=user_id,
                    display_name=display_name,
                    email=email,
                    status=UserStatus.ACTIVE.value,
                )
            )
        membership = OrganizationMembershipORM(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            membership_status=MembershipStatus.INVITED.value,
            version=1,
        )
        self._session.add(membership)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            return None
        return {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "role": role,
            "membership_status": MembershipStatus.INVITED.value,
            "version": 1,
        }

    async def inspect_seat_assignment(
        self,
        organization_id: str,
        user_id: str,
        seat_type: str,
    ) -> dict:
        membership_result = await self._session.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
                OrganizationMembershipORM.membership_status == MembershipStatus.ACTIVE.value,
            )
        )
        membership = membership_result.scalar_one_or_none()
        if membership is None:
            raise OperationalResourceNotFoundError("Active organization member was not found")
        pool_result = await self._session.execute(
            select(OrganizationSeatPoolORM).where(
                OrganizationSeatPoolORM.organization_id == organization_id,
                OrganizationSeatPoolORM.seat_type == seat_type,
                OrganizationSeatPoolORM.status == SeatPoolStatus.ACTIVE.value,
            )
        )
        pool = pool_result.scalar_one_or_none()
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
        assignment_result = await self._session.execute(
            select(SeatAssignmentORM).where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.seat_pool_id == pool.id,
                SeatAssignmentORM.user_id == user_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        return {
            "seat_pool_id": pool.id,
            "seat_type": pool.seat_type,
            "pool_version": pool.version,
            "total_seats": max(pool.total_seats, 0),
            "active_assignments": active_count,
            "has_active_seat": assignment is not None,
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
        pool_update = await self._session.execute(
            update(OrganizationSeatPoolORM)
            .where(
                OrganizationSeatPoolORM.id == state["seat_pool_id"],
                OrganizationSeatPoolORM.version == expected_version,
            )
            .values(version=expected_version + 1, updated_at=_utcnow())
        )
        if pool_update.rowcount != 1:
            await self._session.rollback()
            return None
        assignment = SeatAssignmentORM(
            id=uuid.uuid4().hex,
            organization_id=organization_id,
            seat_pool_id=state["seat_pool_id"],
            user_id=user_id,
            status=SeatAssignmentStatus.ACTIVE.value,
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
        }

    async def inspect_report_grant(
        self,
        organization_id: str,
        report_id: str,
    ) -> dict:
        report = await self._session.get(ReportORM, report_id)
        if report is None or report.status != ReportStatus.ACTIVE.value:
            raise OperationalResourceNotFoundError("Active report was not found")
        access_result = await self._session.execute(
            select(OrganizationReportAccessORM).where(
                OrganizationReportAccessORM.organization_id == organization_id,
                OrganizationReportAccessORM.report_id == report_id,
            )
        )
        access = access_result.scalar_one_or_none()
        return {
            "report_id": report_id,
            "title": report.title,
            "access_level": access.access_level if access is not None else None,
            "status": access.status if access is not None else None,
            "version": access.version if access is not None else 0,
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
        access_update = await self._session.execute(
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
        if access_update.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return {
            "report_id": report_id,
            "access_level": access_level,
            "status": ReportAccessStatus.ACTIVE.value,
            "version": expected_version + 1,
        }

    @staticmethod
    def _user_id_for_email(email: str) -> str:
        digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:20]
        return f"usr_invited_{digest}"
