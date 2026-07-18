from __future__ import annotations

from app.agent.contracts import AgentExecutionResult, AgentPlan
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.run_contracts import AgentRunActivitySink, safe_activity_for_tool
from app.agent.tool_registry import InvalidAgentToolCallError
from app.domain.models import User


class InstrumentedReadOnlyAgentOrchestrator(ReadOnlyAgentOrchestrator):
    """The existing orchestrator with cooperative run activity checkpoints."""

    def __init__(self, *args, activity_sink: AgentRunActivitySink, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._activity_sink = activity_sink

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
            await self._activity_sink.checkpoint()
            await self._activity_sink.emit(
                stage="data_retrieval",
                message=safe_activity_for_tool(validated_tool_call.tool_name),
            )
            tool_results.append(
                await self._execute_tool_call(
                    user=user,
                    organization_id=organization_id,
                    tool_call=validated_tool_call,
                )
            )
        return AgentExecutionResult(results=tuple(tool_results))
