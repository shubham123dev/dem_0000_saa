from __future__ import annotations

from app.agent.answer_contracts import (
    AgentAnswerGateway,
    AgentEvidenceItem,
    AgentSynthesisResult,
)
from app.agent.errors import (
    AgentModelRequestFailedError,
    AgentModelResponseInvalidError,
    AgentModelUnavailableError,
)


class AgentAnswerSynthesisService:
    def __init__(self, answer_gateway: AgentAnswerGateway) -> None:
        self._answer_gateway = answer_gateway

    async def synthesize(
        self,
        *,
        user_request: str,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> AgentSynthesisResult:
        try:
            answer_draft = await self._answer_gateway.create_answer(
                user_request=user_request,
                evidence=evidence,
            )
            available_evidence_ids = {item.id for item in evidence}
            cited_evidence_ids = tuple(dict.fromkeys(answer_draft.evidence_ids))
            if not cited_evidence_ids:
                return self._deterministic_answer(evidence)
            if any(
                evidence_id not in available_evidence_ids
                for evidence_id in cited_evidence_ids
            ):
                return self._deterministic_answer(evidence)
            normalized_answer = answer_draft.answer.strip()
            if not normalized_answer:
                return self._deterministic_answer(evidence)
            return AgentSynthesisResult(
                answer=normalized_answer,
                evidence_ids=cited_evidence_ids,
                answer_source="model",
            )
        except (
            AgentModelUnavailableError,
            AgentModelRequestFailedError,
            AgentModelResponseInvalidError,
        ):
            return self._deterministic_answer(evidence)

    def _deterministic_answer(
        self,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> AgentSynthesisResult:
        evidence_ids = tuple(item.id for item in evidence)
        tool_names = ", ".join(item.tool_name for item in evidence)
        answer = (
            f"Completed the authorized read operations: {tool_names}. "
            f"See evidence: {', '.join(evidence_ids)}."
        )
        return AgentSynthesisResult(
            answer=answer,
            evidence_ids=evidence_ids,
            answer_source="deterministic",
        )
