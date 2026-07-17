from __future__ import annotations

from app.agent.contracts import (
    AgentExecutionResult,
    AgentModelGateway,
    AgentToolCall,
    AgentToolResult,
)
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.domain.models import User
from app.services.organization_service import OrganizationService


class ReadOnlyAgentOrchestrator:
    def __init__(
        self,
        *,
        model_gateway: AgentModelGateway,
        tool_registry: ReadOnlyAgentToolRegistry,
        organization_service: OrganizationService,
    ) -> None:
        self._model_gateway = model_gateway
        self._tool_registry = tool_registry
        self._organization_service = organization_service

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        user_request: str,
    ) -> AgentExecutionResult:
        agent_plan = await self._model_gateway.create_plan(
            user_request=user_request,
            available_tools=self._tool_registry.list_tool_definitions(),
        )
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
        if tool_call.tool_name == "get_organization_profile":
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
        else:
            audit_events, _ = await self._organization_service.list_audit_events(
                user=user,
                organization_id=organization_id,
            )
            result_data = audit_events

        return AgentToolResult(
            tool_name=tool_call.tool_name,
            data=result_data,
        )
