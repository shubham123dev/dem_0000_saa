from __future__ import annotations

import hashlib

from app.agent.answer_contracts import AgentQueryCompletion
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.run_contracts import AgentRunActivitySink, NullAgentRunActivitySink
from app.agent.tool_registry import InvalidAgentToolCallError
from app.agent.synthesis import AgentAnswerSynthesisService
from app.domain.models import User
from app.services.agent_action_service import AgentActionService
from app.services.agent_preflight_service import AgentAuthorizationPreflightService
from app.workplace_resources.operation_router import WorkplaceOperationRouter


class ReadOnlyAgentResponseService:
    def __init__(
        self,
        *,
        orchestrator: ReadOnlyAgentOrchestrator,
        evidence_compiler: AgentEvidenceCompiler,
        synthesis_service: AgentAnswerSynthesisService,
        action_service: AgentActionService,
        preflight_service: AgentAuthorizationPreflightService,
        operation_router: WorkplaceOperationRouter | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._evidence_compiler = evidence_compiler
        self._synthesis_service = synthesis_service
        self._action_service = action_service
        self._preflight_service = preflight_service
        self._operation_router = operation_router or WorkplaceOperationRouter()

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        user_request: str,
        request_id: str | None = None,
        agent_run_id: str | None = None,
        activity_sink: AgentRunActivitySink | None = None,
    ) -> AgentQueryCompletion:
        activity = activity_sink or NullAgentRunActivitySink()
        await activity.checkpoint()
        await activity.emit(stage="access_check", message="Checking your access")
        await self._preflight_service.authorize(
            user=user,
            organization_id=organization_id,
        )
        await activity.checkpoint()
        await activity.emit(
            stage="request_planning", message="Understanding your request"
        )
        agent_plan = await self._orchestrator.create_plan(user_request=user_request)
        await activity.checkpoint()
        if agent_plan.intent == "clarification_required":
            return AgentQueryCompletion(
                mode="clarification_required",
                answer=agent_plan.clarification_question
                or "More information is required.",
                answer_source="deterministic",
                missing_fields=agent_plan.missing_fields,
            )
        if agent_plan.intent == "action_proposal":
            await activity.emit(
                stage="proposal_preparation",
                message="Preparing a reviewable proposal",
            )
            await activity.checkpoint()
            provenance = {
                "proposal_source": "agent_query",
                "planner": "configured_model",
                "request_hash": hashlib.sha256(
                    user_request.encode("utf-8")
                ).hexdigest(),
            }
            if request_id:
                provenance["request_id"] = request_id
            if agent_run_id:
                provenance["agent_run_id"] = agent_run_id
            try:
                proposal_input = self._operation_router.normalize_action_proposal(
                    agent_plan.action_proposal
                )
            except ValueError as exception:
                raise InvalidAgentToolCallError(str(exception)) from exception
            await activity.checkpoint()
            proposal = await self._action_service.propose(
                user=user,
                organization_id=organization_id,
                proposal_input=proposal_input,
                provenance=provenance,
            )
            return AgentQueryCompletion(
                mode="action_proposal",
                answer=(
                    "The requested change was prepared as a dry-run proposal and "
                    "requires explicit approval before execution."
                ),
                answer_source="deterministic",
                action_proposal=proposal,
            )

        await activity.emit(
            stage="data_retrieval",
            message="Reading the relevant workspace information",
        )
        execution_result = await self._orchestrator.execute_read_plan(
            user=user,
            organization_id=organization_id,
            agent_plan=agent_plan,
        )
        await activity.checkpoint()
        await activity.emit(
            stage="answer_preparation", message="Preparing the answer"
        )
        evidence = self._evidence_compiler.compile(execution_result.results)
        synthesis = await self._synthesis_service.synthesize(
            user_request=user_request,
            evidence=evidence,
        )
        await activity.checkpoint()
        return AgentQueryCompletion(
            mode="read",
            answer=synthesis.answer,
            answer_source=synthesis.answer_source,
            evidence_ids=synthesis.evidence_ids,
            results=execution_result.results,
        )
