from __future__ import annotations

from app.agent.answer_contracts import AgentCompletedExecution
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.synthesis import AgentAnswerSynthesisService
from app.domain.models import User


class ReadOnlyAgentResponseService:
    def __init__(
        self,
        *,
        orchestrator: ReadOnlyAgentOrchestrator,
        evidence_compiler: AgentEvidenceCompiler,
        synthesis_service: AgentAnswerSynthesisService,
    ) -> None:
        self._orchestrator = orchestrator
        self._evidence_compiler = evidence_compiler
        self._synthesis_service = synthesis_service

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        user_request: str,
    ) -> AgentCompletedExecution:
        execution_result = await self._orchestrator.execute(
            user=user,
            organization_id=organization_id,
            user_request=user_request,
        )
        evidence = self._evidence_compiler.compile(execution_result.results)
        synthesis = await self._synthesis_service.synthesize(
            user_request=user_request,
            evidence=evidence,
        )
        return AgentCompletedExecution(
            results=execution_result.results,
            evidence=evidence,
            synthesis=synthesis,
        )
