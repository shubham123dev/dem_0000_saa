from __future__ import annotations

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
    VersionedOrganizationMutationGateway,
)
from app.domain.enums import MembershipStatus, ReportAccessLevel, ReportAccessStatus, Role, SeatType
from app.services.operational_resource_service import (
    OperationalResourceNotFoundError,
    OperationalResourceService,
)


class StaleActionResourceError(RuntimeError):
    pass


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or "." not in domain or len(normalized) > 320:
        raise ValueError("Email is invalid")
    return normalized


def normalize_nonempty(value: str, *, field_name: str, maximum_length: int = 200) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum_length:
        raise ValueError(f"{field_name} is invalid")
    return normalized


def normalize_role(value: str) -> str:
    role = value.strip()
    if role not in {Role.SANDBOX_ADMIN.value, Role.SANDBOX_READER.value}:
        raise ValueError("role is invalid")
    return role


def normalize_seat_type(value: str) -> str:
    seat_type = value.strip()
    if seat_type != SeatType.STANDARD.value:
        raise ValueError("seat_type is invalid")
    return seat_type


class UpdateOrganizationContactEmailHandler:
    def __init__(self, gateway: VersionedOrganizationMutationGateway) -> None:
        self._gateway = gateway

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        profile = await self._gateway.get_profile(organization_id)
        contact_email = normalize_email(arguments["contact_email"])
        return AgentActionPreparation(
            normalized_arguments={"contact_email": contact_email},
            changes=(AgentActionChange(field="contact_email", before=profile.contact_email, after=contact_email),),
            observed_resource_version=profile.version,
            resource_type="organization",
            resource_id=organization_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        profile = await self._gateway.update_contact_email_if_version(
            proposal.organization_id,
            proposal.arguments["contact_email"],
            proposal.observed_resource_version,
        )
        if profile is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=profile.id,
            before={"contact_email": proposal.changes[0].before, "version": proposal.observed_resource_version},
            after={"contact_email": profile.contact_email, "version": profile.version},
        )

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        profile = await self._gateway.get_profile(proposal.organization_id)
        if profile.contact_email != proposal.arguments["contact_email"]:
            return None
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=profile.id,
            before={"contact_email": proposal.changes[0].before, "version": proposal.observed_resource_version},
            after={"contact_email": profile.contact_email, "version": profile.version},
        )


class InviteOrganizationUserHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        email = normalize_email(arguments["email"])
        display_name = normalize_nonempty(arguments["display_name"], field_name="display_name")
        role = normalize_role(arguments["role"])
        state = await self._resources.inspect_invitation(organization_id, email)
        if state["membership_status"] is not None:
            raise ValueError("User already has an organization membership")
        if state["user_id"] is None and not state["creation_enabled"]:
            raise ValueError("Production user creation is not configured")
        return AgentActionPreparation(
            normalized_arguments={"email": email, "display_name": display_name, "role": role},
            changes=(AgentActionChange(field="organization_membership", before=None, after={"email": email, "display_name": display_name, "role": role, "status": "invited"}),),
            observed_resource_version=state["version"],
            resource_type="organization_membership",
            resource_id=email,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.invite_user(
            organization_id=proposal.organization_id,
            email=proposal.arguments["email"],
            display_name=proposal.arguments["display_name"],
            role=proposal.arguments["role"],
            requested_by_user_id=proposal.requested_by_user_id,
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=result["user_id"], before={"membership": None, "version": 0}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_invitation(proposal.organization_id, proposal.arguments["email"])
        if state["membership_status"] != MembershipStatus.INVITED.value or state["role"] != proposal.arguments["role"]:
            return None
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=state["user_id"], before={"membership": None, "version": 0}, after=state)


class ActivateOrganizationMembershipHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        state = await self._resources.inspect_membership(organization_id, user_id)
        if state["membership_status"] != MembershipStatus.INVITED.value:
            raise ValueError("Only invited memberships can be activated")
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id},
            changes=(AgentActionChange(field="membership_status", before=state["membership_status"], after=MembershipStatus.ACTIVE.value),),
            observed_resource_version=state["version"],
            resource_type="organization_membership",
            resource_id=user_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.activate_membership(organization_id=proposal.organization_id, user_id=proposal.arguments["user_id"], expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=result["user_id"], before={"membership_status": "invited", "version": proposal.observed_resource_version}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_membership(proposal.organization_id, proposal.arguments["user_id"])
        if state["membership_status"] != MembershipStatus.ACTIVE.value:
            return None
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=state["user_id"], before={"membership_status": "invited", "version": proposal.observed_resource_version}, after=state)


class UpdateOrganizationMemberRoleHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        role = normalize_role(arguments["role"])
        state = await self._resources.inspect_membership(organization_id, user_id)
        if state["membership_status"] != MembershipStatus.ACTIVE.value:
            raise ValueError("Only active memberships can change role")
        if state["role"] == role:
            raise ValueError("Membership already has this role")
        if state["role"] == Role.SANDBOX_ADMIN.value and role != Role.SANDBOX_ADMIN.value and state["active_admin_count"] <= 1:
            raise ValueError("The last active administrator cannot be demoted")
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id, "role": role},
            changes=(AgentActionChange(field="role", before=state["role"], after=role),),
            observed_resource_version=state["version"],
            resource_type="organization_membership",
            resource_id=user_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.update_member_role(organization_id=proposal.organization_id, user_id=proposal.arguments["user_id"], role=proposal.arguments["role"], expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=result["user_id"], before={"role": proposal.changes[0].before, "version": proposal.observed_resource_version}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_membership(proposal.organization_id, proposal.arguments["user_id"])
        if state["role"] != proposal.arguments["role"]:
            return None
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=state["user_id"], before={"role": proposal.changes[0].before, "version": proposal.observed_resource_version}, after=state)


class RemoveOrganizationUserHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        state = await self._resources.inspect_membership(organization_id, user_id)
        if state["membership_status"] == MembershipStatus.REMOVED.value:
            raise ValueError("Membership is already removed")
        if state["has_active_seat"]:
            raise ValueError("Revoke the active seat before removing this member")
        if state["membership_status"] == MembershipStatus.ACTIVE.value and state["role"] == Role.SANDBOX_ADMIN.value and state["active_admin_count"] <= 1:
            raise ValueError("The last active administrator cannot be removed")
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id},
            changes=(AgentActionChange(field="membership_status", before=state["membership_status"], after=MembershipStatus.REMOVED.value),),
            observed_resource_version=state["version"],
            resource_type="organization_membership",
            resource_id=user_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.remove_member(organization_id=proposal.organization_id, user_id=proposal.arguments["user_id"], requested_by_user_id=proposal.requested_by_user_id, expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=result["user_id"], before={"membership_status": proposal.changes[0].before, "version": proposal.observed_resource_version}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_membership(proposal.organization_id, proposal.arguments["user_id"])
        if state["membership_status"] != MembershipStatus.REMOVED.value:
            return None
        return AgentActionHandlerResult(resource_type="organization_membership", resource_id=state["user_id"], before={"membership_status": proposal.changes[0].before, "version": proposal.observed_resource_version}, after=state)


class AssignOrganizationSeatHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        seat_type = normalize_seat_type(arguments["seat_type"])
        try:
            state = await self._resources.inspect_seat_assignment(organization_id, user_id, seat_type)
        except OperationalResourceNotFoundError as exception:
            raise ValueError(str(exception)) from exception
        if state["has_active_seat"]:
            raise ValueError("User already has an active seat")
        if state["active_assignments"] >= state["total_seats"]:
            raise ValueError("No seats are available")
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id, "seat_type": seat_type},
            changes=(AgentActionChange(field="active_seat", before=False, after=True),),
            observed_resource_version=state["pool_version"],
            resource_type="seat_assignment",
            resource_id=user_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.assign_seat(organization_id=proposal.organization_id, user_id=proposal.arguments["user_id"], seat_type=proposal.arguments["seat_type"], assigned_by_user_id=proposal.requested_by_user_id, expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="seat_assignment", resource_id=result["assignment_id"], before={"active": False, "pool_version": proposal.observed_resource_version}, after={**result, "active": True})

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_seat_assignment(proposal.organization_id, proposal.arguments["user_id"], proposal.arguments["seat_type"])
        if not state["has_active_seat"]:
            return None
        return AgentActionHandlerResult(resource_type="seat_assignment", resource_id=state["assignment_id"], before={"active": False, "pool_version": proposal.observed_resource_version}, after={**state, "active": True})


class RevokeOrganizationSeatHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id")
        seat_type = normalize_seat_type(arguments["seat_type"])
        state = await self._resources.inspect_seat_assignment(organization_id, user_id, seat_type)
        if not state["has_active_seat"]:
            raise ValueError("User does not have an active seat")
        return AgentActionPreparation(
            normalized_arguments={"user_id": user_id, "seat_type": seat_type},
            changes=(AgentActionChange(field="active_seat", before=True, after=False),),
            observed_resource_version=state["assignment_version"],
            resource_type="seat_assignment",
            resource_id=state["assignment_id"],
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.revoke_seat(organization_id=proposal.organization_id, user_id=proposal.arguments["user_id"], seat_type=proposal.arguments["seat_type"], revoked_by_user_id=proposal.requested_by_user_id, expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="seat_assignment", resource_id=result["assignment_id"], before={"active": True, "version": proposal.observed_resource_version}, after={**result, "active": False})

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_seat_assignment(proposal.organization_id, proposal.arguments["user_id"], proposal.arguments["seat_type"])
        if state["has_active_seat"]:
            return None
        return AgentActionHandlerResult(resource_type="seat_assignment", resource_id=proposal.resource_id, before={"active": True, "version": proposal.observed_resource_version}, after={**state, "active": False})


class GrantOrganizationReportAccessHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        report_id = normalize_nonempty(arguments["report_id"], field_name="report_id")
        access_level = arguments["access_level"].strip()
        if access_level not in {item.value for item in ReportAccessLevel}:
            raise ValueError("access_level is invalid")
        state = await self._resources.inspect_report_grant(organization_id, report_id)
        if state["status"] == ReportAccessStatus.ACTIVE.value and state["access_level"] == access_level:
            raise ValueError("Organization already has this report access")
        return AgentActionPreparation(
            normalized_arguments={"report_id": report_id, "access_level": access_level},
            changes=(AgentActionChange(field="report_access", before={"access_level": state["access_level"], "status": state["status"]}, after={"access_level": access_level, "status": "active"}),),
            observed_resource_version=state["version"],
            resource_type="organization_report_access",
            resource_id=report_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.grant_report_access(organization_id=proposal.organization_id, report_id=proposal.arguments["report_id"], access_level=proposal.arguments["access_level"], granted_by_user_id=proposal.requested_by_user_id, expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_report_access", resource_id=proposal.arguments["report_id"], before={**proposal.changes[0].before, "version": proposal.observed_resource_version}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_report_grant(proposal.organization_id, proposal.arguments["report_id"])
        if state["status"] != ReportAccessStatus.ACTIVE.value or state["access_level"] != proposal.arguments["access_level"]:
            return None
        return AgentActionHandlerResult(resource_type="organization_report_access", resource_id=proposal.arguments["report_id"], before={**proposal.changes[0].before, "version": proposal.observed_resource_version}, after=state)


class RevokeOrganizationReportAccessHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        report_id = normalize_nonempty(arguments["report_id"], field_name="report_id")
        state = await self._resources.inspect_report_grant(organization_id, report_id)
        if state["status"] != ReportAccessStatus.ACTIVE.value:
            raise ValueError("Organization does not have active report access")
        return AgentActionPreparation(
            normalized_arguments={"report_id": report_id},
            changes=(AgentActionChange(field="report_access_status", before=state["status"], after=ReportAccessStatus.REVOKED.value),),
            observed_resource_version=state["version"],
            resource_type="organization_report_access",
            resource_id=report_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.revoke_report_access(organization_id=proposal.organization_id, report_id=proposal.arguments["report_id"], expected_version=proposal.observed_resource_version)
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(resource_type="organization_report_access", resource_id=proposal.arguments["report_id"], before={"status": "active", "version": proposal.observed_resource_version}, after=result)

    async def reconcile(self, *, proposal: AgentActionProposal, execution: AgentActionExecutionResult) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_report_grant(proposal.organization_id, proposal.arguments["report_id"])
        if state["status"] != ReportAccessStatus.REVOKED.value:
            return None
        return AgentActionHandlerResult(resource_type="organization_report_access", resource_id=proposal.arguments["report_id"], before={"status": "active", "version": proposal.observed_resource_version}, after=state)
