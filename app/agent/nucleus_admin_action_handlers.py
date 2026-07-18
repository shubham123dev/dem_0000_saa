"""Approval-gated Nucleus administrative and entitlement actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from app.adapters.nucleus.admin_contract import (
    NucleusAdministrationGateway,
    NucleusAdministrationProjectionGateway,
)
from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionExecutionContext,
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
    AgentActionResourcePrecondition,
)
from app.agent.action_handlers import StaleActionResourceError
from app.domain.nucleus_admin_models import (
    NucleusAccountAdminState,
    NucleusLicenseProjectionState,
    NucleusLifecycleProjectionState,
    managed_access_snapshot,
)

_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,149}$")
_NULL_SENTINELS = {"null", "none", "-"}


def _required_actor(context: AgentActionExecutionContext) -> int:
    if context.nucleus_actor_id is None:
        raise ValueError("Authenticated executor has no Nucleus actor mapping")
    return context.nucleus_actor_id


def _precondition(
    proposal: AgentActionProposal,
    resource_type: str,
    resource_id: str | None = None,
) -> AgentActionResourcePrecondition:
    matches = [
        item
        for item in proposal.resource_preconditions
        if item.resource_type == resource_type
        and (resource_id is None or item.resource_id == resource_id)
    ]
    if len(matches) != 1:
        raise ValueError("Action resource precondition is missing or ambiguous")
    return matches[0]


def _change(proposal: AgentActionProposal, field: str) -> AgentActionChange:
    matches = [item for item in proposal.changes if item.field == field]
    if len(matches) != 1:
        raise ValueError("Reviewed action change is missing or ambiguous")
    return matches[0]


def _normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3-150 lowercase letters, numbers, dots, underscores, or hyphens"
        )
    return normalized


def _parse_datetime(value: str, *, field_name: str) -> datetime | None:
    normalized = value.strip().lower()
    if normalized in _NULL_SENTINELS:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exception:
        raise ValueError(f"{field_name} must be ISO-8601 or null") from exception
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _datetime_argument(value: datetime | None) -> str:
    if value is None:
        return "null"
    aware = value.replace(tzinfo=value.tzinfo or timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


def _date_argument(value) -> str:
    return "null" if value is None else value.isoformat()


def _positive_int(value: str, *, field_name: str) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as exception:
        raise ValueError(f"{field_name} must be an integer") from exception
    if parsed <= 0:
        raise ValueError(f"{field_name} must be positive")
    return parsed


def _nullable_positive_int(value: str, *, field_name: str) -> int | None:
    if value.strip().lower() in _NULL_SENTINELS:
        return None
    return _positive_int(value, field_name=field_name)


def _admin_before(state: NucleusAccountAdminState) -> dict:
    return {
        "login_username": state.login_username,
        "max_user_limit": state.max_user_limit,
        "license_start_date": state.license_start_date,
        "license_end_date": state.license_end_date,
        "status": state.status,
        "approved_by": state.approved_by,
        "approved_date": state.approved_date,
        "rejected_by": state.rejected_by,
        "rejected_date": state.rejected_date,
        "rejection_reason": state.rejection_reason,
        "is_active": state.is_active,
        "version": state.version,
    }


class UpdateNucleusOrganizationUsernameHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, gateway: NucleusAdministrationGateway) -> None:
        self._gateway = gateway

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        username = _normalize_username(arguments["username"])
        state = await self._gateway.get_admin_state(organization_id)
        if state is None:
            raise ValueError("Nucleus organization account was not found")
        owner_id = await self._gateway.get_username_owner_id(username)
        if owner_id is not None and owner_id != state.organization_account_id:
            raise ValueError("Username is already assigned")
        if state.login_username == username:
            raise ValueError("Username already has this value")
        return AgentActionPreparation(
            normalized_arguments={"username": username},
            changes=(AgentActionChange(field="UserName", before=state.login_username, after=username),),
            observed_resource_version=state.version,
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
        )

    async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
        actor_id = _required_actor(context)
        precondition = _precondition(proposal, "OrganizationAccount")
        updated = await self._gateway.update_username_if_version(
            organization_code=proposal.organization_id,
            username=proposal.arguments["username"],
            actor_id=actor_id,
            expected_version=precondition.observed_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(updated.organization_account_id),
            before={"username": _change(proposal, "UserName").before, "version": precondition.observed_version},
            after={"username": updated.login_username, "version": updated.version, "updated_by": actor_id},
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
        state = await self._gateway.get_admin_state(proposal.organization_id)
        if state is None or state.login_username != proposal.arguments["username"]:
            return None
        precondition = _precondition(proposal, "OrganizationAccount")
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
            before={"username": _change(proposal, "UserName").before, "version": precondition.observed_version},
            after={"username": state.login_username, "version": state.version, "updated_by": context.nucleus_actor_id},
        )


class UpdateNucleusOrganizationLicenseHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, gateway: NucleusAdministrationGateway, projections: NucleusAdministrationProjectionGateway) -> None:
        self._gateway = gateway
        self._projections = projections

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        max_user_limit = _positive_int(arguments["max_user_limit"], field_name="max_user_limit")
        start = _parse_datetime(arguments["license_start_date"], field_name="license_start_date")
        end = _parse_datetime(arguments["license_end_date"], field_name="license_end_date")
        if start is not None and end is not None and end < start:
            raise ValueError("License end date must not precede start date")
        state = await self._gateway.get_admin_state(organization_id)
        projection = await self._projections.get_license_projection(organization_id)
        if state is None or projection is None:
            raise ValueError("Nucleus license projection was not found")
        if projection.active_assignments > max_user_limit:
            raise ValueError("Max user limit cannot be below active seat assignments")
        target_renewal = end.date() if end is not None else None
        if (
            state.max_user_limit == max_user_limit
            and _datetime_argument(state.license_start_date) == _datetime_argument(start)
            and _datetime_argument(state.license_end_date) == _datetime_argument(end)
            and projection.total_seats == max_user_limit
            and _datetime_argument(projection.starts_at) == _datetime_argument(start)
            and _datetime_argument(projection.expires_at) == _datetime_argument(end)
            and _date_argument(projection.renewal_date) == _date_argument(target_renewal)
        ):
            raise ValueError("License already has these values")
        return AgentActionPreparation(
            normalized_arguments={
                "max_user_limit": str(max_user_limit),
                "license_start_date": _datetime_argument(start),
                "license_end_date": _datetime_argument(end),
            },
            changes=(
                AgentActionChange(field="MaxUserLimit", before=state.max_user_limit, after=max_user_limit),
                AgentActionChange(field="LicenseStartDate", before=_datetime_argument(state.license_start_date), after=_datetime_argument(start)),
                AgentActionChange(field="LicenseEndDate", before=_datetime_argument(state.license_end_date), after=_datetime_argument(end)),
                AgentActionChange(field="organization_seat_pool.total_seats", before=projection.total_seats, after=max_user_limit),
                AgentActionChange(field="organization_seat_pool.starts_at", before=_datetime_argument(projection.starts_at), after=_datetime_argument(start)),
                AgentActionChange(field="organization_seat_pool.expires_at", before=_datetime_argument(projection.expires_at), after=_datetime_argument(end)),
                AgentActionChange(field="organization_overview.renewal_date", before=_date_argument(projection.renewal_date), after=_date_argument(target_renewal)),
            ),
            observed_resource_version=state.version,
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
            resource_preconditions=(
                AgentActionResourcePrecondition(resource_type="OrganizationAccount", resource_id=str(state.organization_account_id), observed_version=state.version),
                AgentActionResourcePrecondition(resource_type="organization_seat_pool", resource_id=projection.seat_pool_id, observed_version=projection.seat_pool_version),
                AgentActionResourcePrecondition(resource_type="organization_overview", resource_id=organization_id, observed_version=projection.overview_version),
            ),
        )

    @staticmethod
    def _targets(proposal: AgentActionProposal) -> tuple[int, datetime | None, datetime | None]:
        return (
            int(proposal.arguments["max_user_limit"]),
            _parse_datetime(proposal.arguments["license_start_date"], field_name="license_start_date"),
            _parse_datetime(proposal.arguments["license_end_date"], field_name="license_end_date"),
        )

    async def _apply_projection(self, proposal: AgentActionProposal) -> NucleusLicenseProjectionState | None:
        max_limit, start, end = self._targets(proposal)
        current = await self._projections.get_license_projection(proposal.organization_id)
        if current is None:
            return None
        target_renewal = end.date() if end is not None else None
        if (
            current.total_seats == max_limit
            and _datetime_argument(current.starts_at) == _datetime_argument(start)
            and _datetime_argument(current.expires_at) == _datetime_argument(end)
            and _date_argument(current.renewal_date) == _date_argument(target_renewal)
        ):
            return current
        pool_precondition = _precondition(proposal, "organization_seat_pool")
        overview_precondition = _precondition(proposal, "organization_overview")
        if (
            current.seat_pool_version != pool_precondition.observed_version
            or current.overview_version != overview_precondition.observed_version
            or current.total_seats != _change(proposal, "organization_seat_pool.total_seats").before
            or _datetime_argument(current.starts_at) != _change(proposal, "organization_seat_pool.starts_at").before
            or _datetime_argument(current.expires_at) != _change(proposal, "organization_seat_pool.expires_at").before
            or _date_argument(current.renewal_date) != _change(proposal, "organization_overview.renewal_date").before
        ):
            return None
        return await self._projections.update_license_projection_if_versions(
            organization_id=proposal.organization_id,
            max_user_limit=max_limit,
            license_start_date=start,
            license_end_date=end,
            expected_seat_pool_version=current.seat_pool_version,
            expected_overview_version=current.overview_version,
        )

    async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
        actor_id = _required_actor(context)
        max_limit, start, end = self._targets(proposal)
        account_precondition = _precondition(proposal, "OrganizationAccount")
        updated = await self._gateway.update_license_if_version(
            organization_code=proposal.organization_id,
            max_user_limit=max_limit,
            license_start_date=start,
            license_end_date=end,
            actor_id=actor_id,
            expected_version=account_precondition.observed_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        projection = await self._apply_projection(proposal)
        if projection is None:
            raise RuntimeError("License projection requires reconciliation")
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(updated.organization_account_id),
            before={
                "max_user_limit": _change(proposal, "MaxUserLimit").before,
                "license_start_date": _change(proposal, "LicenseStartDate").before,
                "license_end_date": _change(proposal, "LicenseEndDate").before,
                "version": account_precondition.observed_version,
            },
            after={
                "max_user_limit": updated.max_user_limit,
                "license_start_date": updated.license_start_date,
                "license_end_date": updated.license_end_date,
                "version": updated.version,
                "seat_pool_version": projection.seat_pool_version,
                "overview_version": projection.overview_version,
                "updated_by": actor_id,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
        max_limit, start, end = self._targets(proposal)
        state = await self._gateway.get_admin_state(proposal.organization_id)
        if state is None or (
            state.max_user_limit != max_limit
            or _datetime_argument(state.license_start_date) != _datetime_argument(start)
            or _datetime_argument(state.license_end_date) != _datetime_argument(end)
        ):
            return None
        projection = await self._apply_projection(proposal)
        if projection is None:
            return None
        account_precondition = _precondition(proposal, "OrganizationAccount")
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
            before={
                "max_user_limit": _change(proposal, "MaxUserLimit").before,
                "license_start_date": _change(proposal, "LicenseStartDate").before,
                "license_end_date": _change(proposal, "LicenseEndDate").before,
                "version": account_precondition.observed_version,
            },
            after={
                "max_user_limit": state.max_user_limit,
                "license_start_date": state.license_start_date,
                "license_end_date": state.license_end_date,
                "version": state.version,
                "seat_pool_version": projection.seat_pool_version,
                "overview_version": projection.overview_version,
                "updated_by": context.nucleus_actor_id,
            },
        )


class NucleusOrganizationLifecycleHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, gateway: NucleusAdministrationGateway, projections: NucleusAdministrationProjectionGateway, mode: str) -> None:
        self._gateway = gateway
        self._projections = projections
        self._mode = mode

    def _target(self, state: NucleusAccountAdminState, reason: str | None) -> dict:
        target = {
            "status": state.status,
            "is_active": state.is_active,
            "approved_by": state.approved_by,
            "approved_date": state.approved_date,
            "rejected_by": state.rejected_by,
            "rejected_date": state.rejected_date,
            "rejection_reason": state.rejection_reason,
        }
        if self._mode == "approve":
            target.update(status="approved", approved_by="$executor", approved_date="$execution_time", rejected_by=None, rejected_date=None, rejection_reason=None)
        elif self._mode == "reject":
            target.update(status="rejected", is_active=False, approved_by=None, approved_date=None, rejected_by="$executor", rejected_date="$execution_time", rejection_reason=reason)
        elif self._mode == "activate":
            if state.status != "approved":
                raise ValueError("Only an approved organization account can be activated")
            now = datetime.now(timezone.utc)
            if (
                state.license_start_date is not None
                and state.license_start_date.replace(
                    tzinfo=state.license_start_date.tzinfo or timezone.utc
                )
                > now
            ):
                raise ValueError("Future organization license cannot be activated")
            if (
                state.license_end_date is not None
                and state.license_end_date.replace(
                    tzinfo=state.license_end_date.tzinfo or timezone.utc
                )
                < now
            ):
                raise ValueError("Expired organization license cannot be activated")
            target["is_active"] = True
        elif self._mode == "deactivate":
            target["is_active"] = False
        else:
            raise ValueError("Unsupported lifecycle mode")
        return target

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        reason = None
        normalized_arguments: dict[str, str] = {}
        if self._mode == "reject":
            reason = arguments["reason"].strip()
            if not reason or len(reason) > 500:
                raise ValueError("Rejection reason must be 1-500 characters")
            normalized_arguments["reason"] = reason
        state = await self._gateway.get_admin_state(organization_id)
        projection = await self._projections.get_lifecycle_projection(organization_id)
        if state is None or projection is None:
            raise ValueError("Nucleus lifecycle projection was not found")
        target = self._target(state, reason)
        now = datetime.now(timezone.utc)
        license_started = (
            state.license_start_date is None
            or state.license_start_date.replace(
                tzinfo=state.license_start_date.tzinfo or timezone.utc
            )
            <= now
        )
        license_unexpired = (
            state.license_end_date is None
            or state.license_end_date.replace(
                tzinfo=state.license_end_date.tzinfo or timezone.utc
            )
            >= now
        )
        should_be_active = (
            target["status"] == "approved"
            and bool(target["is_active"])
            and license_started
            and license_unexpired
        )
        target_org_status = "active" if should_be_active else "suspended"
        target_pool_status = "active" if should_be_active else "suspended"
        if not license_unexpired:
            target_pool_status = "expired"
        if self._mode == "approve" and (
            state.status == "approved"
            and state.rejected_by is None
            and state.rejected_date is None
            and state.rejection_reason is None
        ):
            raise ValueError("Organization account is already approved")
        if self._mode == "reject" and (
            state.status == "rejected"
            and state.is_active is False
            and state.rejection_reason == reason
        ):
            raise ValueError("Organization account is already rejected")
        if (
            state.status == target["status"]
            and state.is_active == target["is_active"]
            and (self._mode not in {"approve", "reject"})
            and projection.organization_status == target_org_status
            and projection.seat_pool_status == target_pool_status
        ):
            raise ValueError("Organization lifecycle already has this state")
        changes = [
            AgentActionChange(field="Status", before=state.status, after=target["status"]),
            AgentActionChange(field="IsActive", before=state.is_active, after=target["is_active"]),
        ]
        if self._mode in {"approve", "reject"}:
            for field, attr in (
                ("ApprovedBy", "approved_by"),
                ("ApprovedDate", "approved_date"),
                ("RejectedBy", "rejected_by"),
                ("RejectedDate", "rejected_date"),
                ("RejectionReason", "rejection_reason"),
            ):
                before_value = getattr(state, attr)
                after_value = target[attr]
                if attr in {"approved_date", "rejected_date"}:
                    before_value = _datetime_argument(before_value)
                    if isinstance(after_value, datetime):
                        after_value = _datetime_argument(after_value)
                changes.append(
                    AgentActionChange(
                        field=field,
                        before=before_value,
                        after=after_value,
                    )
                )
        changes.extend(
            (
                AgentActionChange(field="organization.status", before=projection.organization_status, after=target_org_status),
                AgentActionChange(field="organization_seat_pool.status", before=projection.seat_pool_status, after=target_pool_status),
            )
        )
        return AgentActionPreparation(
            normalized_arguments=normalized_arguments,
            changes=tuple(changes),
            observed_resource_version=state.version,
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
            resource_preconditions=(
                AgentActionResourcePrecondition(resource_type="OrganizationAccount", resource_id=str(state.organization_account_id), observed_version=state.version),
                AgentActionResourcePrecondition(resource_type="organization", resource_id=organization_id, observed_version=projection.organization_version),
                AgentActionResourcePrecondition(resource_type="organization_seat_pool", resource_id=projection.seat_pool_id, observed_version=projection.seat_pool_version),
            ),
        )

    async def _apply_projection(self, proposal: AgentActionProposal, state: NucleusAccountAdminState) -> NucleusLifecycleProjectionState | None:
        current = await self._projections.get_lifecycle_projection(proposal.organization_id)
        if current is None:
            return None
        now = datetime.now(timezone.utc)
        license_started = (
            state.license_start_date is None
            or state.license_start_date.replace(
                tzinfo=state.license_start_date.tzinfo or timezone.utc
            )
            <= now
        )
        license_unexpired = (
            state.license_end_date is None
            or state.license_end_date.replace(
                tzinfo=state.license_end_date.tzinfo or timezone.utc
            )
            >= now
        )
        should_be_active = (
            state.status == "approved"
            and state.is_active
            and license_started
            and license_unexpired
        )
        target_org_status = "active" if should_be_active else "suspended"
        target_pool_status = "active" if should_be_active else "suspended"
        if not license_unexpired:
            target_pool_status = "expired"
        if current.organization_status == target_org_status and current.seat_pool_status == target_pool_status:
            return current
        org_precondition = _precondition(proposal, "organization")
        pool_precondition = _precondition(proposal, "organization_seat_pool")
        if (
            current.organization_version != org_precondition.observed_version
            or current.seat_pool_version != pool_precondition.observed_version
            or current.organization_status != _change(proposal, "organization.status").before
            or current.seat_pool_status != _change(proposal, "organization_seat_pool.status").before
        ):
            return None
        return await self._projections.update_lifecycle_projection_if_versions(
            organization_id=proposal.organization_id,
            should_be_active=should_be_active,
            license_end_date=state.license_end_date,
            expected_organization_version=current.organization_version,
            expected_seat_pool_version=current.seat_pool_version,
        )

    async def _apply_canonical(self, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> NucleusAccountAdminState | None:
        actor_id = _required_actor(context)
        precondition = _precondition(proposal, "OrganizationAccount")
        if self._mode in {"approve", "reject"}:
            return await self._gateway.transition_approval_if_version(
                organization_code=proposal.organization_id,
                decision="approved" if self._mode == "approve" else "rejected",
                reason=proposal.arguments.get("reason"),
                actor_id=actor_id,
                expected_version=precondition.observed_version,
            )
        return await self._gateway.set_active_if_version(
            organization_code=proposal.organization_id,
            is_active=self._mode == "activate",
            actor_id=actor_id,
            expected_version=precondition.observed_version,
        )

    def _canonical_matches(self, state: NucleusAccountAdminState, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> bool:
        if self._mode == "approve":
            return state.status == "approved" and state.approved_by == context.nucleus_actor_id and state.rejected_by is None and state.rejection_reason is None
        if self._mode == "reject":
            return state.status == "rejected" and not state.is_active and state.rejected_by == context.nucleus_actor_id and state.rejection_reason == proposal.arguments["reason"]
        if self._mode == "activate":
            return state.status == "approved" and state.is_active
        return not state.is_active

    async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
        actor_id = _required_actor(context)
        updated = await self._apply_canonical(proposal, context)
        if updated is None:
            raise StaleActionResourceError()
        projection = await self._apply_projection(proposal, updated)
        if projection is None:
            raise RuntimeError("Lifecycle projection requires reconciliation")
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(updated.organization_account_id),
            before={
                "status": _change(proposal, "Status").before,
                "is_active": _change(proposal, "IsActive").before,
                "version": _precondition(proposal, "OrganizationAccount").observed_version,
            },
            after={
                **_admin_before(updated),
                "organization_status": projection.organization_status,
                "seat_pool_status": projection.seat_pool_status,
                "updated_by": actor_id,
            },
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
        state = await self._gateway.get_admin_state(proposal.organization_id)
        if state is None or not self._canonical_matches(state, proposal, context):
            return None
        projection = await self._apply_projection(proposal, state)
        if projection is None:
            return None
        return AgentActionHandlerResult(
            resource_type="OrganizationAccount",
            resource_id=str(state.organization_account_id),
            before={
                "status": _change(proposal, "Status").before,
                "is_active": _change(proposal, "IsActive").before,
                "version": _precondition(proposal, "OrganizationAccount").observed_version,
            },
            after={
                **_admin_before(state),
                "organization_status": projection.organization_status,
                "seat_pool_status": projection.seat_pool_status,
                "updated_by": context.nucleus_actor_id,
            },
        )


@dataclass(frozen=True)
class NucleusAccessActionSpec:
    access_kind: str
    resource_type: str
    argument_fields: tuple[str, ...]
    value_fields: tuple[str, ...]
    nullable_fields: frozenset[str] = frozenset()

    def parse(self, arguments: dict[str, str]) -> dict[str, int | None]:
        values: dict[str, int | None] = {}
        for argument, field in zip(self.argument_fields, self.value_fields, strict=True):
            values[field] = (
                _nullable_positive_int(arguments[argument], field_name=argument)
                if argument in self.nullable_fields
                else _positive_int(arguments[argument], field_name=argument)
            )
        return values

    def normalize(self, values: dict[str, int | None]) -> dict[str, str]:
        return {
            argument: "null" if values[field] is None else str(values[field])
            for argument, field in zip(self.argument_fields, self.value_fields, strict=True)
        }


COMPANY_PROFILE_ACCESS = NucleusAccessActionSpec(
    access_kind="company_profile",
    resource_type="OrganizationCompanyProfileAccess",
    argument_fields=("company_id",),
    value_fields=("company_id",),
)
DRUG_ACCESS = NucleusAccessActionSpec(
    access_kind="drug",
    resource_type="OrganizationDrugAccess",
    argument_fields=("drug_id",),
    value_fields=("drug_id",),
)
INDICATION_ACCESS = NucleusAccessActionSpec(
    access_kind="indication",
    resource_type="OrganizationIndicationAccess",
    argument_fields=("indication_id",),
    value_fields=("indication_id",),
)
MARKET_ACCESS = NucleusAccessActionSpec(
    access_kind="market",
    resource_type="OrganizationMarketAccess",
    argument_fields=("market_id", "market_sample_id"),
    value_fields=("market_id", "market_sample_id"),
    nullable_fields=frozenset({"market_sample_id"}),
)


class GrantNucleusManagedAccessHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, gateway: NucleusAdministrationGateway, spec: NucleusAccessActionSpec) -> None:
        self._gateway = gateway
        self._spec = spec

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        values = self._spec.parse(arguments)
        inspected = await self._gateway.inspect_access(
            organization_code=organization_id,
            access_kind=self._spec.access_kind,
            values=values,
        )
        if inspected is None:
            raise ValueError("Nucleus organization account was not found")
        existing, version = inspected
        if existing is not None and not existing.revoked:
            raise ValueError("Nucleus access is already granted")
        resource_id = (
            str(existing.access_id)
            if existing is not None
            else "new:" + ":".join(str(values[field]) for field in self._spec.value_fields)
        )
        before = managed_access_snapshot(existing) if existing is not None else None
        return AgentActionPreparation(
            normalized_arguments=self._spec.normalize(values),
            changes=(AgentActionChange(field="access", before=before, after={**values, "revoked": False}),),
            observed_resource_version=version,
            resource_type=self._spec.resource_type,
            resource_id=resource_id,
        )

    async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
        values = self._spec.parse(proposal.arguments)
        updated = await self._gateway.grant_access_if_version(
            organization_code=proposal.organization_id,
            access_kind=self._spec.access_kind,
            values=values,
            actor_id=_required_actor(context),
            expected_version=proposal.observed_resource_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type=self._spec.resource_type,
            resource_id=str(updated.access_id),
            before=_change(proposal, "access").before or {**values, "revoked": True, "version": proposal.observed_resource_version},
            after=managed_access_snapshot(updated),
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
        values = self._spec.parse(proposal.arguments)
        inspected = await self._gateway.inspect_access(
            organization_code=proposal.organization_id,
            access_kind=self._spec.access_kind,
            values=values,
        )
        if inspected is None or inspected[0] is None or inspected[0].revoked:
            return None
        access = inspected[0]
        return AgentActionHandlerResult(
            resource_type=self._spec.resource_type,
            resource_id=str(access.access_id),
            before=_change(proposal, "access").before or {**values, "revoked": True, "version": proposal.observed_resource_version},
            after=managed_access_snapshot(access),
        )


class RevokeNucleusManagedAccessHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, gateway: NucleusAdministrationGateway, spec: NucleusAccessActionSpec) -> None:
        self._gateway = gateway
        self._spec = spec

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        access_id = _positive_int(arguments["access_id"], field_name="access_id")
        access = await self._gateway.get_access(
            organization_code=organization_id,
            access_kind=self._spec.access_kind,
            access_id=access_id,
        )
        if access is None:
            raise ValueError("Nucleus access row was not found")
        if access.revoked:
            raise ValueError("Nucleus access is already revoked")
        return AgentActionPreparation(
            normalized_arguments={"access_id": str(access_id)},
            changes=(AgentActionChange(field="access", before=managed_access_snapshot(access), after={**access.values, "access_id": access.access_id, "revoked": True}),),
            observed_resource_version=access.version,
            resource_type=self._spec.resource_type,
            resource_id=str(access.access_id),
        )

    async def execute(self, *, proposal: AgentActionProposal, context: AgentActionExecutionContext) -> AgentActionHandlerResult:
        access_id = int(proposal.arguments["access_id"])
        updated = await self._gateway.revoke_access_if_version(
            organization_code=proposal.organization_id,
            access_kind=self._spec.access_kind,
            access_id=access_id,
            actor_id=_required_actor(context),
            expected_version=proposal.observed_resource_version,
        )
        if updated is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type=self._spec.resource_type,
            resource_id=str(updated.access_id),
            before=_change(proposal, "access").before,
            after=managed_access_snapshot(updated),
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult, context: AgentActionExecutionContext) -> AgentActionHandlerResult | None:
        access = await self._gateway.get_access(
            organization_code=proposal.organization_id,
            access_kind=self._spec.access_kind,
            access_id=int(proposal.arguments["access_id"]),
        )
        if access is None or not access.revoked:
            return None
        return AgentActionHandlerResult(
            resource_type=self._spec.resource_type,
            resource_id=str(access.access_id),
            before=_change(proposal, "access").before,
            after=managed_access_snapshot(access),
        )
