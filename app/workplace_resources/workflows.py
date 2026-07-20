from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import CreateUserCommand, UserDirectory
from app.adapters.user.provider import get_user_directory
from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
    AgentActionResourcePrecondition,
)
from app.agent.action_handlers import (
    StaleActionResourceError,
    normalize_email,
    normalize_nonempty,
    normalize_role,
)
from app.db.nucleus_admin_models import NucleusAccessTombstoneORM
from app.db.nucleus_models import (
    NucleusOrganizationAccountORM,
    NucleusOrganizationCategoryAccessORM,
    NucleusOrganizationCompanyProfileAccessORM,
    NucleusOrganizationDrugAccessORM,
    NucleusOrganizationIndicationAccessORM,
    NucleusOrganizationMarketAccessORM,
    NucleusOrganizationReportAccessORM,
    NucleusResourceVersionORM,
)
from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    SeatAssignmentORM,
)
from app.db.workplace_resource_models import (
    WorkplaceMutationPlanORM,
    WorkplaceMutationStepReceiptORM,
    WorkplaceResourceSnapshotORM,
)
from app.domain.enums import (
    MembershipStatus,
    ReportAccessStatus,
    ReportStatus,
    Role,
    SeatAssignmentStatus,
    SeatPoolStatus,
)
from app.workplace_resources.advanced_query import WorkplaceAdvancedQueryService
from app.workplace_resources.registry import WorkplaceResourceRegistry
from app.workplace_resources.risk import WorkplaceRiskDecision, WorkplaceRiskEvaluator
from app.workplace_resources.service import WorkplaceResourceService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_object(raw: str, *, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exception:
        raise ValueError(f"{field_name} must be valid JSON") from exception
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _parse_list(raw: str, *, field_name: str) -> list[Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exception:
        raise ValueError(f"{field_name} must be valid JSON") from exception
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON array")
    return value


@dataclass(frozen=True)
class _AccessSpec:
    package_key: str
    resource_type: str
    version_resource_type: str
    orm_type: type
    id_attribute: str
    value_attributes: tuple[str, ...]
    active_attribute: str | None


_ACCESS_SPECS = (
    _AccessSpec(
        "categories",
        "OrganizationCategoryAccess",
        "nucleus_category_access",
        NucleusOrganizationCategoryAccessORM,
        "organization_category_access_id",
        ("category_id", "category_sample_id"),
        "is_active",
    ),
    _AccessSpec(
        "company_profiles",
        "OrganizationCompanyProfileAccess",
        "nucleus_company_profile_access",
        NucleusOrganizationCompanyProfileAccessORM,
        "organization_company_profile_access_id",
        ("company_id",),
        None,
    ),
    _AccessSpec(
        "drugs",
        "OrganizationDrugAccess",
        "nucleus_drug_access",
        NucleusOrganizationDrugAccessORM,
        "organization_drug_access_id",
        ("drug_id",),
        None,
    ),
    _AccessSpec(
        "indications",
        "OrganizationIndicationAccess",
        "nucleus_indication_access",
        NucleusOrganizationIndicationAccessORM,
        "organization_indication_access_id",
        ("indication_id",),
        None,
    ),
    _AccessSpec(
        "markets",
        "OrganizationMarketAccess",
        "nucleus_market_access",
        NucleusOrganizationMarketAccessORM,
        "organization_market_access_id",
        ("market_id", "market_sample_id"),
        None,
    ),
    _AccessSpec(
        "reports",
        "OrganizationReportAccess",
        "nucleus_report_access",
        NucleusOrganizationReportAccessORM,
        "organization_report_access_id",
        (
            "reports_id",
            "sample_id",
            "sample_toc_id",
            "speciality_id",
            "is_executive_access",
        ),
        "is_active",
    ),
)
_ACCESS_BY_KEY = {item.package_key: item for item in _ACCESS_SPECS}


class WorkplaceWorkflowService:
    """Backend-defined atomic workflows built on the existing action lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        registry: WorkplaceResourceRegistry | None = None,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._registry = registry or WorkplaceResourceRegistry()
        self._users = user_directory or get_user_directory()
        self._advanced_query = WorkplaceAdvancedQueryService(
            session,
            self._registry,
        )
        self._resources = WorkplaceResourceService(session, self._registry)

    async def rollback(self) -> None:
        await self._session.rollback()

    async def prepare_onboard(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        email = normalize_email(arguments["email"])
        display_name = normalize_nonempty(
            arguments["display_name"],
            field_name="display_name",
            maximum_length=200,
        )
        role = normalize_role(arguments["role"])
        seat_type = arguments["seat_type"].strip().lower()
        if seat_type not in {"none", "standard"}:
            raise ValueError("seat_type must be none or standard")

        user = await self._users.get_by_email(email)
        if user is not None and not user.is_active:
            raise ValueError("Production user is disabled")
        if user is None and not self._users.creation_enabled:
            raise ValueError("Production user creation is not configured")
        membership = None
        if user is not None:
            membership = await self._session.scalar(
                select(OrganizationMembershipORM).where(
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.user_id == user.id,
                )
            )
        if membership is not None and membership.membership_status == MembershipStatus.ACTIVE.value:
            raise ValueError("User already has an active organization membership")

        pool = None
        active_seat_count = 0
        if seat_type == "standard":
            pool = await self._session.scalar(
                select(OrganizationSeatPoolORM).where(
                    OrganizationSeatPoolORM.organization_id == organization_id,
                    OrganizationSeatPoolORM.seat_type == seat_type,
                    OrganizationSeatPoolORM.status == SeatPoolStatus.ACTIVE.value,
                )
            )
            if pool is None:
                raise ValueError("Active standard seat pool was not found")
            active_seat_count = int(
                await self._session.scalar(
                    select(func.count())
                    .select_from(SeatAssignmentORM)
                    .where(
                        SeatAssignmentORM.organization_id == organization_id,
                        SeatAssignmentORM.seat_pool_id == pool.id,
                        SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                    )
                )
                or 0
            )
            if active_seat_count >= pool.total_seats:
                raise ValueError("No standard seats are available")

        # Keep preparation stable if a prior execution created Test_user1 but
        # failed before the local membership transaction committed.
        user_id = membership.user_id if membership is not None else email
        seat_lookup_user_id = user.id if user is not None else user_id
        before = {
            "user_id": membership.user_id if membership is not None else None,
            "user_status": (
                user.status.value if membership is not None and user is not None else None
            ),
            "membership_status": (
                membership.membership_status if membership is not None else None
            ),
            "role": membership.role if membership is not None else None,
            "membership_version": membership.version if membership is not None else 0,
            "active_seat": False,
        }
        if pool is not None:
            active_assignment = await self._session.scalar(
                select(SeatAssignmentORM).where(
                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                    SeatAssignmentORM.user_id == seat_lookup_user_id,
                    SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                )
            )
            if active_assignment is not None:
                raise ValueError("User already has an active standard seat")
        after = {
            "user_id": membership.user_id if membership is not None else None,
            "user_status": "active",
            "membership_status": MembershipStatus.ACTIVE.value,
            "role": role,
            "active_seat": seat_type == "standard",
            "seat_type": seat_type,
        }
        preconditions = [
            AgentActionResourcePrecondition(
                resource_type="organization_membership",
                resource_id=user_id if membership is not None else email,
                observed_version=membership.version if membership is not None else 0,
            )
        ]
        if pool is not None:
            preconditions.append(
                AgentActionResourcePrecondition(
                    resource_type="organization_seat_pool",
                    resource_id=pool.id,
                    observed_version=pool.version,
                )
            )
        risk = WorkplaceRiskEvaluator.evaluate(
            action_name="onboard_organization_user",
            required_permission=WorkplaceRiskEvaluator.workflow_permission(),
            affected_count=2 if pool is not None else 1,
            privileged=role == Role.SANDBOX_ADMIN.value,
        )
        normalized = {
            "email": email,
            "display_name": display_name,
            "role": role,
            "seat_type": seat_type,
        }
        return AgentActionPreparation(
            normalized_arguments=normalized,
            changes=(
                AgentActionChange(
                    field="onboarding_workflow",
                    before=before,
                    after=after,
                ),
            ),
            observed_resource_version=membership.version if membership is not None else 0,
            resource_type="organization_user_onboarding",
            resource_id=user_id,
            resource_preconditions=tuple(preconditions),
            risk_level=risk.risk_level,
            approval_policy=risk.approval_policy,
            risk_snapshot=risk.public_dict(),
        )

    async def execute_onboard(
        self,
        *,
        proposal: AgentActionProposal,
        executor_user_id: str,
    ) -> AgentActionHandlerResult:
        fresh = await self.prepare_onboard(
            organization_id=proposal.organization_id,
            arguments=proposal.arguments,
        )
        self._require_same_preparation(proposal, fresh)
        now = _utcnow()
        email = proposal.arguments["email"]
        user = await self._users.get_by_email(email)
        if user is None:
            user = await self._users.create_user(
                CreateUserCommand(
                    display_name=proposal.arguments["display_name"],
                    email=email,
                    actor_user_id=executor_user_id,
                )
            )
        if not user.is_active:
            raise ValueError("Production user is disabled")

        membership = await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == proposal.organization_id,
                OrganizationMembershipORM.user_id == user.id,
            )
        )
        before = proposal.changes[0].before
        if membership is None:
            membership = OrganizationMembershipORM(
                organization_id=proposal.organization_id,
                user_id=user.id,
                role=proposal.arguments["role"],
                membership_status=MembershipStatus.ACTIVE.value,
                version=1,
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
            self._session.add(membership)
        else:
            membership.role = proposal.arguments["role"]
            membership.membership_status = MembershipStatus.ACTIVE.value
            membership.joined_at = membership.joined_at or now
            membership.version += 1
            membership.updated_at = now
        await self._session.flush()

        steps = [
            {
                "resource_type": "organization_membership",
                "resource_id": user.id,
                "operation": "activate_or_create",
                "before": before,
                "after": {
                    "user_id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": membership.role,
                    "membership_status": membership.membership_status,
                    "membership_version": membership.version,
                },
            }
        ]
        seat_type = proposal.arguments["seat_type"]
        if seat_type == "standard":
            pool = await self._session.scalar(
                select(OrganizationSeatPoolORM).where(
                    OrganizationSeatPoolORM.organization_id == proposal.organization_id,
                    OrganizationSeatPoolORM.seat_type == seat_type,
                    OrganizationSeatPoolORM.status == SeatPoolStatus.ACTIVE.value,
                )
            )
            if pool is None:
                raise StaleActionResourceError()
            pool.version += 1
            pool.updated_at = now
            assignment = SeatAssignmentORM(
                id=uuid.uuid4().hex,
                organization_id=proposal.organization_id,
                seat_pool_id=pool.id,
                user_id=user.id,
                status=SeatAssignmentStatus.ACTIVE.value,
                version=1,
                assigned_at=now,
                assigned_by_user_id=executor_user_id,
                created_at=now,
                updated_at=now,
            )
            self._session.add(assignment)
            steps.append(
                {
                    "resource_type": "seat_assignment",
                    "resource_id": assignment.id,
                    "operation": "assign",
                    "before": {"active": False},
                    "after": {
                        "active": True,
                        "seat_type": seat_type,
                        "seat_pool_id": pool.id,
                        "user_id": user.id,
                        "assignment_version": 1,
                    },
                }
            )
        await self._persist_plan_and_steps(
            proposal=proposal,
            workflow_name="onboard_organization_user",
            steps=steps,
            target_set_hash=_hash(
                [(item["resource_type"], item["resource_id"]) for item in steps]
            ),
            risk_snapshot=self._risk_snapshot(proposal, fresh),
            compensation={
                "action_name": "offboard_organization_user",
                "arguments": {"user_id": user.id},
            },
        )
        await self._session.commit()
        return AgentActionHandlerResult(
            resource_type="organization_user_onboarding",
            resource_id=user.id,
            before=dict(before),
            after={
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": membership.role,
                "membership_status": membership.membership_status,
                "seat_type": seat_type,
                "active_seat": seat_type == "standard",
                "steps": steps,
            },
        )

    async def reconcile_onboard(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult | None:
        user = await self._users.get_by_email(proposal.arguments["email"])
        if user is None:
            return None
        membership = await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == proposal.organization_id,
                OrganizationMembershipORM.user_id == user.id,
            )
        )
        if (
            membership is None
            or membership.membership_status != MembershipStatus.ACTIVE.value
            or membership.role != proposal.arguments["role"]
        ):
            return None
        expected_seat = proposal.arguments["seat_type"] == "standard"
        seat_statement = select(SeatAssignmentORM).where(
            SeatAssignmentORM.organization_id == proposal.organization_id,
            SeatAssignmentORM.user_id == user.id,
            SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
        )
        if expected_seat:
            seat_statement = seat_statement.join(
                OrganizationSeatPoolORM,
                OrganizationSeatPoolORM.id == SeatAssignmentORM.seat_pool_id,
            ).where(OrganizationSeatPoolORM.seat_type == "standard")
        active_seat = await self._session.scalar(seat_statement)
        if (active_seat is not None) != expected_seat:
            return None
        expected_membership_version = (
            int(proposal.changes[0].before.get("membership_version") or 0) + 1
        )
        if membership.version != expected_membership_version:
            return None
        return AgentActionHandlerResult(
            resource_type="organization_user_onboarding",
            resource_id=user.id,
            before=dict(proposal.changes[0].before),
            after={
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": membership.role,
                "membership_status": membership.membership_status,
                "active_seat": active_seat is not None,
            },
        )

    async def prepare_offboard(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        membership = await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == organization_id,
                OrganizationMembershipORM.user_id == user_id,
            )
        )
        if membership is None or membership.membership_status == MembershipStatus.REMOVED.value:
            raise ValueError("Active or invited organization membership was not found")
        active_admin_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(OrganizationMembershipORM)
                .where(
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.membership_status
                    == MembershipStatus.ACTIVE.value,
                    OrganizationMembershipORM.role == Role.SANDBOX_ADMIN.value,
                )
            )
            or 0
        )
        if (
            membership.membership_status == MembershipStatus.ACTIVE.value
            and membership.role == Role.SANDBOX_ADMIN.value
            and active_admin_count <= 1
        ):
            raise ValueError("The last active administrator cannot be offboarded")
        assignments = tuple(
            (
                await self._session.execute(
                    select(SeatAssignmentORM).where(
                        SeatAssignmentORM.organization_id == organization_id,
                        SeatAssignmentORM.user_id == user_id,
                        SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                    )
                )
            )
            .scalars()
            .all()
        )
        pools: dict[str, OrganizationSeatPoolORM] = {}
        for assignment in assignments:
            pool = await self._session.get(
                OrganizationSeatPoolORM,
                assignment.seat_pool_id,
            )
            if pool is not None:
                pools[pool.id] = pool
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ValueError("Organization user was not found")
        before = {
            "user_id": user_id,
            "email": user.email,
            "display_name": user.display_name,
            "membership_status": membership.membership_status,
            "role": membership.role,
            "membership_version": membership.version,
            "active_seats": [
                {
                    "assignment_id": item.id,
                    "seat_pool_id": item.seat_pool_id,
                    "version": item.version,
                }
                for item in assignments
            ],
        }
        after = {
            "user_id": user_id,
            "membership_status": MembershipStatus.REMOVED.value,
            "role": membership.role,
            "active_seats": [],
        }
        preconditions = [
            AgentActionResourcePrecondition(
                resource_type="organization_membership",
                resource_id=user_id,
                observed_version=membership.version,
            )
        ]
        preconditions.extend(
            AgentActionResourcePrecondition(
                resource_type="seat_assignment",
                resource_id=item.id,
                observed_version=item.version,
            )
            for item in assignments
        )
        preconditions.extend(
            AgentActionResourcePrecondition(
                resource_type="organization_seat_pool",
                resource_id=pool.id,
                observed_version=pool.version,
            )
            for pool in sorted(pools.values(), key=lambda item: item.id)
        )
        risk = WorkplaceRiskEvaluator.evaluate(
            action_name="offboard_organization_user",
            required_permission=WorkplaceRiskEvaluator.workflow_permission(),
            affected_count=1 + len(assignments) + len(pools),
            destructive=True,
            privileged=membership.role == Role.SANDBOX_ADMIN.value,
        )
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id},
            changes=(
                AgentActionChange(
                    field="offboarding_workflow",
                    before=before,
                    after=after,
                ),
            ),
            observed_resource_version=membership.version,
            resource_type="organization_user_offboarding",
            resource_id=user_id,
            resource_preconditions=tuple(preconditions),
            risk_level=risk.risk_level,
            approval_policy=risk.approval_policy,
            risk_snapshot=risk.public_dict(),
        )

    async def execute_offboard(
        self,
        *,
        proposal: AgentActionProposal,
        executor_user_id: str,
    ) -> AgentActionHandlerResult:
        if proposal.arguments["user_id"] == proposal.requested_by_user_id:
            raise ValueError("A requester cannot offboard their own membership")
        fresh = await self.prepare_offboard(
            organization_id=proposal.organization_id,
            arguments=proposal.arguments,
        )
        self._require_same_preparation(proposal, fresh)
        now = _utcnow()
        user_id = proposal.arguments["user_id"]
        membership = await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == proposal.organization_id,
                OrganizationMembershipORM.user_id == user_id,
            )
        )
        if membership is None:
            raise StaleActionResourceError()
        assignments = tuple(
            (
                await self._session.execute(
                    select(SeatAssignmentORM).where(
                        SeatAssignmentORM.organization_id == proposal.organization_id,
                        SeatAssignmentORM.user_id == user_id,
                        SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                    )
                )
            )
            .scalars()
            .all()
        )
        steps = []
        touched_pool_ids: set[str] = set()
        for assignment in assignments:
            assignment.status = SeatAssignmentStatus.REVOKED.value
            assignment.version += 1
            assignment.revoked_at = now
            assignment.revoked_by_user_id = executor_user_id
            assignment.updated_at = now
            touched_pool_ids.add(assignment.seat_pool_id)
            steps.append(
                {
                    "resource_type": "seat_assignment",
                    "resource_id": assignment.id,
                    "operation": "revoke",
                    "before": {"status": SeatAssignmentStatus.ACTIVE.value},
                    "after": {
                        "status": SeatAssignmentStatus.REVOKED.value,
                        "version": assignment.version,
                    },
                }
            )
        for pool_id in sorted(touched_pool_ids):
            pool = await self._session.get(OrganizationSeatPoolORM, pool_id)
            if pool is None:
                raise StaleActionResourceError()
            pool.version += 1
            pool.updated_at = now
        membership.membership_status = MembershipStatus.REMOVED.value
        membership.version += 1
        membership.updated_at = now
        steps.append(
            {
                "resource_type": "organization_membership",
                "resource_id": user_id,
                "operation": "remove",
                "before": dict(proposal.changes[0].before),
                "after": {
                    "membership_status": membership.membership_status,
                    "role": membership.role,
                    "version": membership.version,
                },
            }
        )
        before = dict(proposal.changes[0].before)
        compensation = {
            "action_name": "onboard_organization_user",
            "arguments": {
                "email": before["email"],
                "display_name": before["display_name"],
                "role": before["role"],
                "seat_type": "standard" if before["active_seats"] else "none",
            },
        }
        await self._persist_plan_and_steps(
            proposal=proposal,
            workflow_name="offboard_organization_user",
            steps=steps,
            target_set_hash=_hash(
                [(item["resource_type"], item["resource_id"]) for item in steps]
            ),
            risk_snapshot=self._risk_snapshot(proposal, fresh),
            compensation=compensation,
        )
        await self._session.commit()
        return AgentActionHandlerResult(
            resource_type="organization_user_offboarding",
            resource_id=user_id,
            before=before,
            after={
                "user_id": user_id,
                "membership_status": membership.membership_status,
                "role": membership.role,
                "active_seats": [],
                "steps": steps,
            },
        )

    async def reconcile_offboard(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult | None:
        user_id = proposal.arguments["user_id"]
        membership = await self._session.scalar(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == proposal.organization_id,
                OrganizationMembershipORM.user_id == user_id,
            )
        )
        membership_precondition = next(
            (
                item
                for item in proposal.resource_preconditions
                if item.resource_type == "organization_membership"
                and item.resource_id == user_id
            ),
            None,
        )
        if (
            membership is None
            or membership_precondition is None
            or membership.membership_status != MembershipStatus.REMOVED.value
            or membership.version != membership_precondition.observed_version + 1
        ):
            return None
        for precondition in proposal.resource_preconditions:
            if precondition.resource_type == "seat_assignment":
                assignment = await self._session.get(
                    SeatAssignmentORM, precondition.resource_id
                )
                if (
                    assignment is None
                    or assignment.organization_id != proposal.organization_id
                    or assignment.user_id != user_id
                    or assignment.status != SeatAssignmentStatus.REVOKED.value
                    or assignment.version != precondition.observed_version + 1
                ):
                    return None
            elif precondition.resource_type == "organization_seat_pool":
                pool = await self._session.get(
                    OrganizationSeatPoolORM, precondition.resource_id
                )
                if (
                    pool is None
                    or pool.organization_id != proposal.organization_id
                    or pool.version != precondition.observed_version + 1
                ):
                    return None
        return AgentActionHandlerResult(
            resource_type="organization_user_offboarding",
            resource_id=user_id,
            before=dict(proposal.changes[0].before),
            after={
                "user_id": user_id,
                "membership_status": membership.membership_status,
                "role": membership.role,
                "active_seats": [],
            },
        )

    async def prepare_query_bulk_update(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        resource_type = arguments["resource_type"].strip()
        query = self._advanced_query.parse_query_json(arguments["query_json"])
        target_set = await self._advanced_query.freeze_for_mutation(
            organization_id=organization_id,
            resource_type=resource_type,
            query=query,
        )
        definition = self._registry.get(resource_type)
        changes = self._resources._validate_changes(
            definition,
            _parse_object(arguments["changes_json"], field_name="changes_json"),
        )
        before = list(target_set.snapshots)
        after = [
            {**snapshot, **changes}
            for snapshot in before
        ]
        preconditions = tuple(
            AgentActionResourcePrecondition(
                resource_type=resource_type,
                resource_id=resource_id,
                observed_version=version,
            )
            for resource_id, version in zip(
                target_set.resource_ids,
                target_set.versions,
                strict=True,
            )
        )
        risk = WorkplaceRiskEvaluator.evaluate(
            action_name="bulk_update_workplace_resources_by_query",
            required_permission=WorkplaceRiskEvaluator.workflow_permission(),
            affected_count=target_set.resource_count,
        )
        return AgentActionPreparation(
            normalized_arguments={
                "resource_type": resource_type,
                "query_json": _canonical_json(target_set.query),
                "changes_json": _canonical_json(changes),
                "target_set_hash": target_set.target_set_hash,
            },
            changes=(
                AgentActionChange(
                    field="resources",
                    before=before,
                    after=after,
                ),
            ),
            observed_resource_version=0,
            resource_type=f"{resource_type}_query_batch",
            resource_id=target_set.target_set_hash,
            resource_preconditions=preconditions,
            risk_level=risk.risk_level,
            approval_policy=risk.approval_policy,
            risk_snapshot=risk.public_dict(),
        )

    async def execute_query_bulk_update(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        fresh = await self.prepare_query_bulk_update(
            organization_id=proposal.organization_id,
            arguments=proposal.arguments,
        )
        self._require_same_preparation(proposal, fresh)
        if fresh.normalized_arguments["target_set_hash"] != proposal.arguments.get(
            "target_set_hash"
        ):
            raise StaleActionResourceError()
        resource_type = proposal.arguments["resource_type"]
        definition = self._registry.get(resource_type)
        changes = _parse_object(
            proposal.arguments["changes_json"],
            field_name="changes_json",
        )
        now = _utcnow()
        steps = []
        snapshots = proposal.changes[0].before
        for index, precondition in enumerate(proposal.resource_preconditions):
            if precondition.resource_type != resource_type:
                continue
            row = await self._resources._row(
                definition,
                proposal.organization_id,
                precondition.resource_id,
            )
            if row is None or self._resources._version(definition, row) != precondition.observed_version:
                raise StaleActionResourceError()
            before = self._resources._serialize(definition, row)
            for name, value in changes.items():
                setattr(row, definition.field_map[name].attribute, value)
            if definition.version_attribute:
                setattr(
                    row,
                    definition.version_attribute,
                    precondition.observed_version + 1,
                )
            if hasattr(row, "updated_at"):
                row.updated_at = now
            after = self._resources._serialize(definition, row)
            await self._record_snapshot(
                organization_id=proposal.organization_id,
                resource_type=resource_type,
                resource_id=precondition.resource_id,
                version=precondition.observed_version,
                snapshot=before,
            )
            steps.append(
                {
                    "resource_type": resource_type,
                    "resource_id": precondition.resource_id,
                    "operation": "query_bulk_update",
                    "before": before,
                    "after": after,
                }
            )
        compensation = {
            "action_name": "restore_workplace_resource_snapshots",
            "arguments": {
                "resource_type": resource_type,
                "snapshots_json": _canonical_json(
                    [
                        {
                            "resource_id": precondition.resource_id,
                            "expected_current_version": precondition.observed_version + 1,
                            "values": snapshot,
                        }
                        for precondition, snapshot in zip(
                            [
                                item
                                for item in proposal.resource_preconditions
                                if item.resource_type == resource_type
                            ],
                            snapshots,
                            strict=True,
                        )
                    ]
                ),
            },
        }
        await self._persist_plan_and_steps(
            proposal=proposal,
            workflow_name="bulk_update_workplace_resources_by_query",
            steps=steps,
            target_set_hash=proposal.arguments["target_set_hash"],
            risk_snapshot=self._risk_snapshot(proposal, fresh),
            compensation=compensation,
        )
        await self._session.commit()
        return AgentActionHandlerResult(
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            before={"resources": snapshots},
            after={"resources": [item["after"] for item in steps]},
        )

    async def reconcile_query_bulk_update(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult | None:
        resource_type = proposal.arguments["resource_type"]
        definition = self._registry.get(resource_type)
        expected_changes = _parse_object(
            proposal.arguments["changes_json"],
            field_name="changes_json",
        )
        rows = []
        for precondition in proposal.resource_preconditions:
            if precondition.resource_type != resource_type:
                continue
            row = await self._resources._row(
                definition,
                proposal.organization_id,
                precondition.resource_id,
            )
            if row is None:
                return None
            current = self._resources._serialize(definition, row)
            if (
                self._resources._version(definition, row)
                != precondition.observed_version + 1
                or any(
                    current.get(name) != value
                    for name, value in expected_changes.items()
                )
            ):
                return None
            rows.append(current)
        return AgentActionHandlerResult(
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            before={"resources": proposal.changes[0].before},
            after={"resources": rows},
        )

    async def prepare_snapshot_restore(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        resource_type = arguments["resource_type"].strip()
        definition = self._registry.get(resource_type)
        if definition.orm_type is None or definition.organization_attribute is None:
            raise ValueError("Snapshot restore supports generic scoped resources only")
        raw_snapshots = _parse_list(
            arguments["snapshots_json"],
            field_name="snapshots_json",
        )
        if not raw_snapshots or len(raw_snapshots) > 50:
            raise ValueError("Snapshot restore requires one to fifty resources")
        normalized_snapshots = []
        preconditions = []
        before_rows = []
        after_rows = []
        for raw in raw_snapshots:
            if not isinstance(raw, dict) or set(raw) != {
                "resource_id",
                "expected_current_version",
                "values",
            }:
                raise ValueError("Snapshot restore entry is invalid")
            resource_id = str(raw["resource_id"])
            try:
                expected_version = int(raw["expected_current_version"])
            except (TypeError, ValueError) as exception:
                raise ValueError("Snapshot restore version is invalid") from exception
            values = raw["values"]
            if not isinstance(values, dict):
                raise ValueError("Snapshot restore values must be an object")
            row = await self._resources._row(
                definition,
                organization_id,
                resource_id,
            )
            if row is None or self._resources._version(definition, row) != expected_version:
                raise ValueError("Snapshot restore resource is stale")
            current = self._resources._serialize(definition, row)
            restorable: dict[str, Any] = {}
            for name, value in values.items():
                policy = definition.field_map.get(name)
                if policy is None or policy.sensitive:
                    continue
                if name in {
                    next(
                        item.name
                        for item in definition.fields
                        if item.attribute == definition.id_attribute
                    ),
                    "version",
                    "created_at",
                    "updated_at",
                }:
                    continue
                if not policy.editable and name != "is_active":
                    continue
                restorable[name] = value
            if not restorable:
                raise ValueError("Snapshot contains no restorable fields")
            target = {**current, **restorable}
            normalized_snapshots.append(
                {
                    "resource_id": resource_id,
                    "expected_current_version": expected_version,
                    "values": restorable,
                }
            )
            preconditions.append(
                AgentActionResourcePrecondition(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    observed_version=expected_version,
                )
            )
            before_rows.append(current)
            after_rows.append(target)
        risk = WorkplaceRiskEvaluator.evaluate(
            action_name="restore_workplace_resource_snapshots",
            required_permission=WorkplaceRiskEvaluator.workflow_permission(),
            affected_count=len(normalized_snapshots),
            destructive=True,
        )
        batch_hash = _hash(
            {
                "organization_id": organization_id,
                "resource_type": resource_type,
                "snapshots": normalized_snapshots,
            }
        )
        return AgentActionPreparation(
            normalized_arguments={
                "resource_type": resource_type,
                "snapshots_json": _canonical_json(normalized_snapshots),
            },
            changes=(
                AgentActionChange(
                    field="resources",
                    before=before_rows,
                    after=after_rows,
                ),
            ),
            observed_resource_version=0,
            resource_type=f"{resource_type}_snapshot_restore",
            resource_id=batch_hash,
            resource_preconditions=tuple(preconditions),
            risk_level=risk.risk_level,
            approval_policy=risk.approval_policy,
            risk_snapshot=risk.public_dict(),
        )

    async def execute_snapshot_restore(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        fresh = await self.prepare_snapshot_restore(
            organization_id=proposal.organization_id,
            arguments=proposal.arguments,
        )
        self._require_same_preparation(proposal, fresh)
        resource_type = proposal.arguments["resource_type"]
        definition = self._registry.get(resource_type)
        snapshots = _parse_list(
            proposal.arguments["snapshots_json"],
            field_name="snapshots_json",
        )
        now = _utcnow()
        steps = []
        for item in snapshots:
            row = await self._resources._row(
                definition,
                proposal.organization_id,
                item["resource_id"],
            )
            if row is None or self._resources._version(definition, row) != item["expected_current_version"]:
                raise StaleActionResourceError()
            before = self._resources._serialize(definition, row)
            for name, value in item["values"].items():
                policy = definition.field_map[name]
                setattr(row, policy.attribute, value)
            if definition.version_attribute:
                setattr(
                    row,
                    definition.version_attribute,
                    item["expected_current_version"] + 1,
                )
            if hasattr(row, "updated_at"):
                row.updated_at = now
            after = self._resources._serialize(definition, row)
            steps.append(
                {
                    "resource_type": resource_type,
                    "resource_id": item["resource_id"],
                    "operation": "restore_snapshot",
                    "before": before,
                    "after": after,
                }
            )
        await self._persist_plan_and_steps(
            proposal=proposal,
            workflow_name="restore_workplace_resource_snapshots",
            steps=steps,
            target_set_hash=proposal.resource_id,
            risk_snapshot=self._risk_snapshot(proposal, fresh),
            compensation={},
        )
        await self._session.commit()
        return AgentActionHandlerResult(
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            before={"resources": [item["before"] for item in steps]},
            after={"resources": [item["after"] for item in steps]},
        )

    async def reconcile_snapshot_restore(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult | None:
        resource_type = proposal.arguments["resource_type"]
        definition = self._registry.get(resource_type)
        snapshots = _parse_list(
            proposal.arguments["snapshots_json"],
            field_name="snapshots_json",
        )
        rows = []
        for item in snapshots:
            row = await self._resources._row(
                definition,
                proposal.organization_id,
                item["resource_id"],
            )
            if row is None:
                return None
            current = self._resources._serialize(definition, row)
            if (
                self._resources._version(definition, row)
                != item["expected_current_version"] + 1
                or any(
                    current.get(name) != value
                    for name, value in item["values"].items()
                )
            ):
                return None
            rows.append(current)
        return AgentActionHandlerResult(
            resource_type=proposal.resource_type,
            resource_id=proposal.resource_id,
            before={"resources": proposal.changes[0].before},
            after={"resources": rows},
        )

    async def prepare_access_package(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        package = self._normalize_access_package(
            _parse_object(arguments["package_json"], field_name="package_json")
        )
        account = await self._nucleus_account(organization_id)
        if account is None:
            raise ValueError("Nucleus organization account was not found")
        changes = []
        preconditions = []
        normalized_changed: dict[str, list[dict[str, Any]]] = {}
        before_package: dict[str, list[dict[str, Any]]] = {}
        destructive = False
        for package_key, desired_items in package.items():
            spec = _ACCESS_BY_KEY[package_key]
            for desired in desired_items:
                values = {
                    name: desired[name]
                    for name in spec.value_attributes
                }
                row = await self._matching_access_row(
                    account.organization_account_id,
                    spec,
                    values,
                )
                current = await self._access_state(spec, row)
                if current["active"] == desired["active"]:
                    continue
                destructive = destructive or not desired["active"]
                resource_id = (
                    str(current["access_id"])
                    if current["access_id"] is not None
                    else f"new:{package_key}:{_hash(values)[:24]}"
                )
                before = {
                    **values,
                    "active": current["active"],
                    "access_id": current["access_id"],
                    "version": current["version"],
                }
                after = {
                    **values,
                    "active": desired["active"],
                    "access_id": current["access_id"],
                    "version": current["version"] + 1,
                }
                normalized_changed.setdefault(package_key, []).append(desired)
                before_package.setdefault(package_key, []).append(
                    {**values, "active": current["active"]}
                )
                changes.append(
                    AgentActionChange(
                        field=f"{package_key}:{resource_id}",
                        before=before,
                        after=after,
                    )
                )
                preconditions.append(
                    AgentActionResourcePrecondition(
                        resource_type=spec.version_resource_type,
                        resource_id=resource_id,
                        observed_version=current["version"],
                    )
                )
        if not changes:
            raise ValueError("Access package would not change any resource")
        risk = WorkplaceRiskEvaluator.evaluate(
            action_name="apply_organization_access_package",
            required_permission=WorkplaceRiskEvaluator.workflow_permission(),
            affected_count=len(changes),
            destructive=destructive,
            access_change_count=len(changes),
        )
        normalized_payload = {
            key: value
            for key, value in normalized_changed.items()
            if value
        }
        package_hash = _hash(
            {
                "organization_id": organization_id,
                "account_id": account.organization_account_id,
                "package": normalized_payload,
            }
        )
        return AgentActionPreparation(
            normalized_arguments={
                "package_json": _canonical_json(normalized_payload),
                "before_package_json": _canonical_json(before_package),
            },
            changes=tuple(changes),
            observed_resource_version=0,
            resource_type="organization_access_package",
            resource_id=package_hash,
            resource_preconditions=tuple(preconditions),
            risk_level=risk.risk_level,
            approval_policy=risk.approval_policy,
            risk_snapshot=risk.public_dict(),
        )

    async def execute_access_package(
        self,
        *,
        proposal: AgentActionProposal,
        nucleus_actor_id: int | None,
    ) -> AgentActionHandlerResult:
        if nucleus_actor_id is None:
            raise ValueError("Executor has no Nucleus actor mapping")
        fresh = await self.prepare_access_package(
            organization_id=proposal.organization_id,
            arguments=proposal.arguments,
        )
        self._require_same_preparation(proposal, fresh)
        account = await self._nucleus_account(proposal.organization_id)
        if account is None:
            raise StaleActionResourceError()
        package = self._normalize_access_package(
            _parse_object(proposal.arguments["package_json"], field_name="package_json")
        )
        now = _utcnow()
        steps = []
        after_package: dict[str, list[dict[str, Any]]] = {}
        for package_key, desired_items in package.items():
            spec = _ACCESS_BY_KEY[package_key]
            for desired in desired_items:
                values = {
                    name: desired[name]
                    for name in spec.value_attributes
                }
                row = await self._matching_access_row(
                    account.organization_account_id,
                    spec,
                    values,
                )
                state = await self._access_state(spec, row)
                resource_id = (
                    str(state["access_id"])
                    if state["access_id"] is not None
                    else f"new:{package_key}:{_hash(values)[:24]}"
                )
                precondition = next(
                    (
                        item
                        for item in proposal.resource_preconditions
                        if item.resource_type == spec.version_resource_type
                        and item.resource_id == resource_id
                    ),
                    None,
                )
                if precondition is None or state["version"] != precondition.observed_version:
                    raise StaleActionResourceError()
                before = {
                    **values,
                    "active": state["active"],
                    "access_id": state["access_id"],
                    "version": state["version"],
                }
                if row is None:
                    if not desired["active"]:
                        raise StaleActionResourceError()
                    row_kwargs = {
                        "organization_account_id": account.organization_account_id,
                        **values,
                    }
                    if spec.active_attribute:
                        row_kwargs[spec.active_attribute] = True
                    if hasattr(spec.orm_type, "created_date"):
                        row_kwargs["created_date"] = now
                    row = spec.orm_type(**row_kwargs)
                    self._session.add(row)
                    await self._session.flush()
                    access_id = int(getattr(row, spec.id_attribute))
                    self._session.add(
                        NucleusResourceVersionORM(
                            resource_type=spec.version_resource_type,
                            resource_key=str(access_id),
                            version=1,
                            updated_at=now,
                        )
                    )
                    version = 1
                else:
                    access_id = int(getattr(row, spec.id_attribute))
                    version_row = await self._session.get(
                        NucleusResourceVersionORM,
                        {
                            "resource_type": spec.version_resource_type,
                            "resource_key": str(access_id),
                        },
                    )
                    if version_row is None:
                        if state["version"] != 1:
                            raise StaleActionResourceError()
                        version_row = NucleusResourceVersionORM(
                            resource_type=spec.version_resource_type,
                            resource_key=str(access_id),
                            version=2,
                            updated_at=now,
                        )
                        self._session.add(version_row)
                        version = 2
                    else:
                        if version_row.version != precondition.observed_version:
                            raise StaleActionResourceError()
                        version_row.version += 1
                        version_row.updated_at = now
                        version = version_row.version
                    if spec.active_attribute:
                        setattr(row, spec.active_attribute, desired["active"])
                    else:
                        tombstone = await self._session.get(
                            NucleusAccessTombstoneORM,
                            {
                                "resource_type": spec.resource_type,
                                "access_id": access_id,
                            },
                        )
                        if desired["active"]:
                            if tombstone is not None:
                                await self._session.delete(tombstone)
                        else:
                            snapshot = {
                                name: getattr(row, name)
                                for name in spec.value_attributes
                            }
                            if tombstone is None:
                                tombstone = NucleusAccessTombstoneORM(
                                    resource_type=spec.resource_type,
                                    access_id=access_id,
                                    organization_account_id=account.organization_account_id,
                                    version=version,
                                    snapshot_json=snapshot,
                                    revoked_by=nucleus_actor_id,
                                    revoked_at=now,
                                )
                                self._session.add(tombstone)
                            else:
                                tombstone.version = version
                                tombstone.snapshot_json = snapshot
                                tombstone.revoked_by = nucleus_actor_id
                                tombstone.revoked_at = now
                after = {
                    **values,
                    "active": desired["active"],
                    "access_id": access_id,
                    "version": version,
                }
                after_package.setdefault(package_key, []).append(
                    {**values, "active": desired["active"]}
                )
                steps.append(
                    {
                        "resource_type": spec.version_resource_type,
                        "resource_id": str(access_id),
                        "operation": "grant" if desired["active"] else "revoke",
                        "before": before,
                        "after": after,
                    }
                )
        before_package = _parse_object(
            proposal.arguments["before_package_json"],
            field_name="before_package_json",
        )
        await self._persist_plan_and_steps(
            proposal=proposal,
            workflow_name="apply_organization_access_package",
            steps=steps,
            target_set_hash=proposal.resource_id,
            risk_snapshot=self._risk_snapshot(proposal, fresh),
            compensation={
                "action_name": "apply_organization_access_package",
                "arguments": {
                    "package_json": _canonical_json(before_package),
                },
            },
        )
        await self._session.commit()
        return AgentActionHandlerResult(
            resource_type="organization_access_package",
            resource_id=proposal.resource_id,
            before={"package": before_package},
            after={"package": after_package, "steps": steps},
        )

    async def reconcile_access_package(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult | None:
        account = await self._nucleus_account(proposal.organization_id)
        if account is None:
            return None
        package = self._normalize_access_package(
            _parse_object(proposal.arguments["package_json"], field_name="package_json")
        )
        after_package: dict[str, list[dict[str, Any]]] = {}
        for package_key, desired_items in package.items():
            spec = _ACCESS_BY_KEY[package_key]
            for desired in desired_items:
                values = {
                    name: desired[name]
                    for name in spec.value_attributes
                }
                row = await self._matching_access_row(
                    account.organization_account_id,
                    spec,
                    values,
                )
                state = await self._access_state(spec, row)
                reviewed = [
                    change
                    for change in proposal.changes
                    if change.field.startswith(f"{package_key}:")
                    and all(
                        change.after.get(name) == value
                        for name, value in values.items()
                    )
                ]
                if (
                    len(reviewed) != 1
                    or state["active"] != desired["active"]
                    or state["version"] != reviewed[0].after.get("version")
                ):
                    return None
                after_package.setdefault(package_key, []).append(desired)
        return AgentActionHandlerResult(
            resource_type="organization_access_package",
            resource_id=proposal.resource_id,
            before={
                "package": _parse_object(
                    proposal.arguments["before_package_json"],
                    field_name="before_package_json",
                )
            },
            after={"package": after_package},
        )

    def _normalize_access_package(
        self,
        package: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        if not package or set(package) - set(_ACCESS_BY_KEY):
            raise ValueError("Access package contains unsupported resource groups")
        normalized: dict[str, list[dict[str, Any]]] = {}
        total = 0
        for package_key, raw_items in package.items():
            spec = _ACCESS_BY_KEY[package_key]
            if not isinstance(raw_items, list):
                raise ValueError("Each access package group must be an array")
            group = []
            seen = set()
            for raw in raw_items:
                if not isinstance(raw, dict):
                    raise ValueError("Access package entries must be objects")
                allowed = set(spec.value_attributes) | {"active"}
                if set(raw) - allowed or "active" not in raw:
                    raise ValueError("Access package entry fields are invalid")
                if not isinstance(raw["active"], bool):
                    raise ValueError("Access package active state must be boolean")
                item: dict[str, Any] = {"active": raw["active"]}
                for index, name in enumerate(spec.value_attributes):
                    value = raw.get(name)
                    if name == "is_executive_access":
                        if value is not None and not isinstance(value, bool):
                            raise ValueError(
                                "is_executive_access must be boolean or null"
                            )
                        item[name] = value
                        continue
                    if value is None:
                        if index == 0:
                            raise ValueError(f"{name} is required")
                        item[name] = None
                        continue
                    try:
                        parsed = int(value)
                    except (TypeError, ValueError) as exception:
                        raise ValueError(f"{name} must be an integer or null") from exception
                    if parsed <= 0:
                        raise ValueError(f"{name} must be positive")
                    item[name] = parsed
                key = tuple(item[name] for name in spec.value_attributes)
                if key in seen:
                    raise ValueError("Access package contains duplicate entries")
                seen.add(key)
                group.append(item)
                total += 1
            if group:
                normalized[package_key] = group
        if total < 1 or total > 30:
            raise ValueError("Access package requires one to thirty entries")
        return normalized

    async def _nucleus_account(
        self,
        organization_id: str,
    ) -> NucleusOrganizationAccountORM | None:
        return await self._session.scalar(
            select(NucleusOrganizationAccountORM).where(
                NucleusOrganizationAccountORM.organization_code == organization_id
            )
        )

    async def _matching_access_row(
        self,
        organization_account_id: int,
        spec: _AccessSpec,
        values: dict[str, Any],
    ) -> Any | None:
        conditions = [
            spec.orm_type.organization_account_id == organization_account_id
        ]
        for name, value in values.items():
            column = getattr(spec.orm_type, name)
            conditions.append(column.is_(None) if value is None else column == value)
        return await self._session.scalar(
            select(spec.orm_type)
            .where(*conditions)
            .order_by(getattr(spec.orm_type, spec.id_attribute).desc())
        )

    async def _access_state(
        self,
        spec: _AccessSpec,
        row: Any | None,
    ) -> dict[str, Any]:
        if row is None:
            return {"access_id": None, "active": False, "version": 0}
        access_id = int(getattr(row, spec.id_attribute))
        version_row = await self._session.get(
            NucleusResourceVersionORM,
            {
                "resource_type": spec.version_resource_type,
                "resource_key": str(access_id),
            },
        )
        version = version_row.version if version_row is not None else 1
        if spec.active_attribute:
            active = bool(getattr(row, spec.active_attribute))
        else:
            tombstone = await self._session.get(
                NucleusAccessTombstoneORM,
                {"resource_type": spec.resource_type, "access_id": access_id},
            )
            active = tombstone is None
        return {"access_id": access_id, "active": active, "version": version}

    @staticmethod
    def _require_same_preparation(
        proposal: AgentActionProposal,
        preparation: AgentActionPreparation,
    ) -> None:
        if (
            preparation.resource_preconditions != proposal.resource_preconditions
            or preparation.changes != proposal.changes
            or (
                preparation.risk_level is not None
                and preparation.risk_level != proposal.risk_level
            )
            or (
                preparation.approval_policy is not None
                and preparation.approval_policy != proposal.approval_policy
            )
        ):
            raise StaleActionResourceError()

    @staticmethod
    def _risk_snapshot(
        proposal: AgentActionProposal,
        preparation: AgentActionPreparation,
    ) -> dict[str, Any]:
        return {
            **preparation.risk_snapshot,
            "risk_level": proposal.risk_level,
            "approval_policy": proposal.approval_policy.model_dump(mode="json"),
        }

    async def _record_snapshot(
        self,
        *,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        version: int,
        snapshot: dict[str, Any],
    ) -> None:
        self._session.add(
            WorkplaceResourceSnapshotORM(
                id=uuid.uuid4().hex,
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                version=version,
                snapshot_hash=_hash(snapshot),
                snapshot_json=snapshot,
                captured_at=_utcnow(),
            )
        )

    async def _persist_plan_and_steps(
        self,
        *,
        proposal: AgentActionProposal,
        workflow_name: str,
        steps: list[dict[str, Any]],
        target_set_hash: str,
        risk_snapshot: dict[str, Any],
        compensation: dict[str, Any],
    ) -> None:
        existing = await self._session.scalar(
            select(WorkplaceMutationPlanORM).where(
                WorkplaceMutationPlanORM.proposal_id == proposal.id
            )
        )
        if existing is not None:
            return
        now = _utcnow()
        plan = WorkplaceMutationPlanORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal.id,
            organization_id=proposal.organization_id,
            operation_type=workflow_name,
            resource_count=len(steps),
            plan_json={"steps": steps},
            status="succeeded",
            workflow_name=workflow_name,
            workflow_version=1,
            target_set_hash=target_set_hash,
            risk_snapshot_json=risk_snapshot,
            compensation_json=compensation,
            created_at=now,
            updated_at=now,
        )
        self._session.add(plan)
        await self._session.flush()
        for index, step in enumerate(steps):
            self._session.add(
                WorkplaceMutationStepReceiptORM(
                    id=uuid.uuid4().hex,
                    mutation_plan_id=plan.id,
                    step_index=index,
                    resource_type=step["resource_type"],
                    resource_id=str(step["resource_id"]),
                    operation=step["operation"],
                    before_json=step.get("before"),
                    after_json=step.get("after"),
                    outcome="succeeded",
                    error_code=None,
                    attempt_count=1,
                    depends_on_step_index=index - 1 if index > 0 else None,
                    verification_json={"verified": True, "strategy": "transaction_flush"},
                    compensation_json=compensation if index == len(steps) - 1 else None,
                    completed_at=now,
                )
            )
