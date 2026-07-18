from __future__ import annotations

from app.agent.action_registry import AgentActionRegistry
from app.agent.contracts import (
    AgentExecutionResult,
    AgentModelGateway,
    AgentPlan,
    AgentToolCall,
    AgentToolResult,
)
from app.agent.tool_registry import InvalidAgentToolCallError, ReadOnlyAgentToolRegistry
from app.domain.models import User
from app.services.nucleus_organization_service import NucleusOrganizationService
from app.services.organization_service import OrganizationService


class ReadOnlyAgentOrchestrator:
    def __init__(
        self,
        *,
        model_gateway: AgentModelGateway,
        tool_registry: ReadOnlyAgentToolRegistry,
        organization_service: OrganizationService,
        nucleus_organization_service: NucleusOrganizationService | None = None,
        action_registry: AgentActionRegistry | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._tool_registry = tool_registry
        self._action_registry = action_registry or AgentActionRegistry()
        self._organization_service = organization_service
        self._nucleus_organization_service = nucleus_organization_service

    async def create_plan(self, *, user_request: str) -> AgentPlan:
        return await self._model_gateway.create_plan(
            user_request=user_request,
            available_tools=self._tool_registry.list_tool_definitions(),
            available_actions=self._action_registry.list_definitions(),
        )

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        user_request: str,
    ) -> AgentExecutionResult:
        agent_plan = await self.create_plan(user_request=user_request)
        return await self.execute_read_plan(
            user=user,
            organization_id=organization_id,
            agent_plan=agent_plan,
        )

    async def execute_read_plan(
        self,
        *,
        user: User,
        organization_id: str,
        agent_plan: AgentPlan,
    ) -> AgentExecutionResult:
        if agent_plan.intent != "read":
            raise InvalidAgentToolCallError("Read execution requires a read plan")
        tool_results = []
        for proposed_tool_call in agent_plan.tool_calls:
            validated_tool_call = self._tool_registry.validate_tool_call(
                proposed_tool_call
            )
            tool_results.append(
                await self._execute_tool_call(
                    user=user,
                    organization_id=organization_id,
                    tool_call=validated_tool_call,
                )
            )
        return AgentExecutionResult(results=tuple(tool_results))

    async def _execute_tool_call(
        self,
        *,
        user: User,
        organization_id: str,
        tool_call: AgentToolCall,
    ) -> AgentToolResult:
        if tool_call.tool_name == "get_organization_overview":
            overview, _ = await self._organization_service.read_overview(
                user=user,
                organization_id=organization_id,
            )
            result_data = overview
        elif tool_call.tool_name == "get_nucleus_organization_account":
            if self._nucleus_organization_service is None:
                raise InvalidAgentToolCallError("Nucleus organization service is unavailable")
            account, _ = await self._nucleus_organization_service.read_account(
                user=user,
                organization_id=organization_id,
            )
            result_data = account
        elif tool_call.tool_name == "get_nucleus_organization_license":
            if self._nucleus_organization_service is None:
                raise InvalidAgentToolCallError("Nucleus organization service is unavailable")
            license_info, _ = await self._nucleus_organization_service.read_license(
                user=user,
                organization_id=organization_id,
            )
            result_data = license_info
        elif tool_call.tool_name == "get_nucleus_organization_approval_status":
            if self._nucleus_organization_service is None:
                raise InvalidAgentToolCallError("Nucleus organization service is unavailable")
            approval, _ = (
                await self._nucleus_organization_service.read_approval_status(
                    user=user,
                    organization_id=organization_id,
                )
            )
            result_data = approval
        elif tool_call.tool_name == "get_nucleus_organization_entitlements":
            if self._nucleus_organization_service is None:
                raise InvalidAgentToolCallError("Nucleus organization service is unavailable")
            entitlements, _ = (
                await self._nucleus_organization_service.read_entitlements(
                    user=user,
                    organization_id=organization_id,
                )
            )
            result_data = entitlements
        elif tool_call.tool_name == "get_organization_profile":
            organization_profile, _ = await self._organization_service.read_profile(
                user=user,
                organization_id=organization_id,
            )
            result_data = organization_profile
        elif tool_call.tool_name == "list_organization_users":
            organization_members, _ = await self._organization_service.list_users(
                user=user,
                organization_id=organization_id,
            )
            result_data = organization_members
        elif tool_call.tool_name == "get_organization_seat_summary":
            seat_summary, _ = await self._organization_service.get_seat_summary(
                user=user,
                organization_id=organization_id,
            )
            result_data = seat_summary
        elif tool_call.tool_name == "list_organization_reports":
            organization_reports, _ = await self._organization_service.list_reports(
                user=user,
                organization_id=organization_id,
            )
            result_data = organization_reports
        elif tool_call.tool_name == "check_organization_report_access":
            report_access_decision, _ = (
                await self._organization_service.check_report_access(
                    user=user,
                    organization_id=organization_id,
                    report_id=tool_call.arguments["report_id"],
                )
            )
            result_data = report_access_decision
        elif tool_call.tool_name == "get_organization_audit_log":
            audit_events, _ = await self._organization_service.list_audit_events(
                user=user,
                organization_id=organization_id,
            )
            result_data = audit_events
        else:
            raise InvalidAgentToolCallError("Unknown read-only tool")

        return AgentToolResult(
            tool_name=tool_call.tool_name,
            data=result_data,
        )
