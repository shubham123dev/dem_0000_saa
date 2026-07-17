from __future__ import annotations

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
    VersionedOrganizationMutationGateway,
)
from app.domain.enums import ReportAccessLevel, Role, SeatType
from app.services.operational_resource_service import (
    OperationalResourceNotFoundError,
    OperationalResourceService,
)


class StaleActionResourceError(RuntimeError):
    pass


def normalize_email(value: str) -> str:
    normalized_value = value.strip().lower()
    local_part, separator, domain_part = normalized_value.partition("@")
    if (
        not separator
        or not local_part
        or "." not in domain_part
        or len(normalized_value) > 320
    ):
        raise ValueError("Email is invalid")
    return normalized_value


def normalize_nonempty(value: str, *, field_name: str, maximum_length: int) -> str:
    normalized_value = value.strip()
    if not normalized_value or len(normalized_value) > maximum_length:
        raise ValueError(f"{field_name} is invalid")
    return normalized_value


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
        updated_profile = await self._gateway.update_contact_email_if_version(
            proposal.organization_id,
            proposal.arguments["contact_email"],
            proposal.observed_resource_version,
        )
        if updated_profile is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization",
            resource_id=updated_profile.id,
            before={"contact_email": proposal.changes[0].before, "version": proposal.observed_resource_version},
            after={"contact_email": updated_profile.contact_email, "version": updated_profile.version},
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
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
        display_name = normalize_nonempty(arguments["display_name"], field_name="display_name", maximum_length=200)
        role = arguments["role"].strip()
        if role not in {Role.SANDBOX_ADMIN.value, Role.SANDBOX_READER.value}:
            raise ValueError("role is invalid")
        state = await self._resources.inspect_invitation(organization_id, email)
        if state["membership_status"] is not None:
            raise ValueError("User already has an organization membership")
        return AgentActionPreparation(
            normalized_arguments={"email": email, "display_name": display_name, "role": role},
            changes=(
                AgentActionChange(
                    field="organization_membership",
                    before=None,
                    after={"email": email, "display_name": display_name, "role": role, "status": "invited"},
                ),
            ),
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
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization_membership",
            resource_id=result["user_id"],
            before={"membership": None, "version": proposal.observed_resource_version},
            after=result,
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_invitation(proposal.organization_id, proposal.arguments["email"])
        if state["membership_status"] != "invited" or state["role"] != proposal.arguments["role"]:
            return None
        return AgentActionHandlerResult(
            resource_type="organization_membership",
            resource_id=state["user_id"],
            before={"membership": None, "version": proposal.observed_resource_version},
            after={**state, "email": proposal.arguments["email"], "display_name": proposal.arguments["display_name"]},
        )


class AssignOrganizationSeatHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        user_id = normalize_nonempty(arguments["user_id"], field_name="user_id", maximum_length=200)
        seat_type = arguments["seat_type"].strip()
        if seat_type != SeatType.STANDARD.value:
            raise ValueError("seat_type is invalid")
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
        result = await self._resources.assign_seat(
            organization_id=proposal.organization_id,
            user_id=proposal.arguments["user_id"],
            seat_type=proposal.arguments["seat_type"],
            assigned_by_user_id=proposal.requested_by_user_id,
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="seat_assignment",
            resource_id=result["assignment_id"],
            before={"active": False, "pool_version": proposal.observed_resource_version},
            after={**result, "active": True},
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_seat_assignment(
            proposal.organization_id,
            proposal.arguments["user_id"],
            proposal.arguments["seat_type"],
        )
        if not state["has_active_seat"]:
            return None
        return AgentActionHandlerResult(
            resource_type="seat_assignment",
            resource_id=proposal.arguments["user_id"],
            before={"active": False, "pool_version": proposal.observed_resource_version},
            after={**state, "active": True, "user_id": proposal.arguments["user_id"]},
        )


class GrantOrganizationReportAccessHandler:
    def __init__(self, resources: OperationalResourceService) -> None:
        self._resources = resources

    async def prepare(self, *, organization_id: str, arguments: dict[str, str]) -> AgentActionPreparation:
        report_id = normalize_nonempty(arguments["report_id"], field_name="report_id", maximum_length=200)
        access_level = arguments["access_level"].strip()
        if access_level not in {item.value for item in ReportAccessLevel}:
            raise ValueError("access_level is invalid")
        try:
            state = await self._resources.inspect_report_grant(organization_id, report_id)
        except OperationalResourceNotFoundError as exception:
            raise ValueError(str(exception)) from exception
        if state["status"] == "active" and state["access_level"] == access_level:
            raise ValueError("Organization already has this report access")
        return AgentActionPreparation(
            normalized_arguments={"report_id": report_id, "access_level": access_level},
            changes=(
                AgentActionChange(
                    field="report_access",
                    before={"access_level": state["access_level"], "status": state["status"]},
                    after={"access_level": access_level, "status": "active"},
                ),
            ),
            observed_resource_version=state["version"],
            resource_type="organization_report_access",
            resource_id=report_id,
        )

    async def execute(self, *, proposal: AgentActionProposal) -> AgentActionHandlerResult:
        result = await self._resources.grant_report_access(
            organization_id=proposal.organization_id,
            report_id=proposal.arguments["report_id"],
            access_level=proposal.arguments["access_level"],
            granted_by_user_id=proposal.requested_by_user_id,
            expected_version=proposal.observed_resource_version,
        )
        if result is None:
            raise StaleActionResourceError()
        return AgentActionHandlerResult(
            resource_type="organization_report_access",
            resource_id=proposal.arguments["report_id"],
            before={**proposal.changes[0].before, "version": proposal.observed_resource_version},
            after=result,
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        state = await self._resources.inspect_report_grant(
            proposal.organization_id,
            proposal.arguments["report_id"],
        )
        if state["status"] != "active" or state["access_level"] != proposal.arguments["access_level"]:
            return None
        return AgentActionHandlerResult(
            resource_type="organization_report_access",
            resource_id=proposal.arguments["report_id"],
            before={**proposal.changes[0].before, "version": proposal.observed_resource_version},
            after=state,
        )
