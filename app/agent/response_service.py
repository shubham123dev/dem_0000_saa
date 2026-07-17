from __future__ import annotations

import hashlib

from app.agent.answer_contracts import AgentQueryCompletion
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.synthesis import AgentAnswerSynthesisService
from app.domain.models import User
from app.services.agent_action_service import AgentActionService


class ReadOnlyAgentResponseService:
    def __init__(
        self,
        *,
        orchestrator: ReadOnlyAgentOrchestrator,
        evidence_compiler: AgentEvidenceCompiler,
        synthesis_service: AgentAnswerSynthesisService,
        action_service: AgentActionService,
    ) -> None:
        self._orchestrator = orchestrator
        self._evidence_compiler = evidence_compiler
        self._synthesis_service = synthesis_service
        self._action_service = action_service

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        user_request: str,
        request_id: str | None = None,
    ) -> AgentQueryCompletion:
        agent_plan = await self._orchestrator.create_plan(user_request=user_request)
        if agent_plan.intent == "action_proposal":
            provenance = {
                "proposal_source": "agent_query",
                "planner": "configured_model",
                "request_hash": hashlib.sha256(
                    user_request.encode("utf-8")
                ).hexdigest(),
            }
            if request_id:
                provenance["request_id"] = request_id
            proposal = await self._action_service.propose(
                user=user,
                organization_id=organization_id,
                proposal_input=agent_plan.action_proposal,
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

        execution_result = await self._orchestrator.execute_read_plan(
            user=user,
            organization_id=organization_id,
            agent_plan=agent_plan,
        )
        evidence = self._evidence_compiler.compile(execution_result.results)
        synthesis = await self._synthesis_service.synthesize(
            user_request=user_request,
            evidence=evidence,
        )
        return AgentQueryCompletion(
            mode="read",
            answer=synthesis.answer,
            answer_source=synthesis.answer_source,
            evidence_ids=synthesis.evidence_ids,
            results=execution_result.results,
        )
