from __future__ import annotations

import json

import httpx

from app.agent.answer_contracts import AgentAnswerDraft, AgentEvidenceItem
from app.agent.contracts import AgentToolResult
from app.agent.errors import AgentModelRequestFailedError
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway
from app.agent.synthesis import AgentAnswerSynthesisService


class FixedAnswerGateway:
    def __init__(self, answer_draft: AgentAnswerDraft) -> None:
        self.answer_draft = answer_draft
        self.received_evidence: tuple[AgentEvidenceItem, ...] = ()

    async def create_answer(self, *, user_request: str, evidence):
        self.received_evidence = evidence
        return self.answer_draft


class FailingAnswerGateway:
    async def create_answer(self, *, user_request: str, evidence):
        raise AgentModelRequestFailedError()


def build_provider(transport: httpx.AsyncBaseTransport):
    return OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=1,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
        http_client=httpx.AsyncClient(transport=transport),
    )


def provider_response(payload: dict) -> dict:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(payload),
                    }
                ],
            }
        ]
    }


def test_evidence_compiler_assigns_stable_ids_and_bounds_large_values() -> None:
    compiler = AgentEvidenceCompiler(
        maximum_item_characters=20,
        maximum_total_characters=30,
    )
    evidence = compiler.compile(
        (
            AgentToolResult(tool_name="first_tool", data={"value": "x" * 100}),
            AgentToolResult(tool_name="second_tool", data={"value": 2}),
        )
    )

    assert [item.id for item in evidence] == ["result-1", "result-2"]
    assert evidence[0].data["truncated"] is True
    assert evidence[1].tool_name == "second_tool"


async def test_synthesis_accepts_only_existing_evidence_references() -> None:
    evidence = (
        AgentEvidenceItem(id="result-1", tool_name="profile", data={"status": "active"}),
    )
    gateway = FixedAnswerGateway(
        AgentAnswerDraft(
            answer="The organization is active.",
            evidence_ids=("result-1",),
        )
    )
    result = await AgentAnswerSynthesisService(gateway).synthesize(
        user_request="What is the status?",
        evidence=evidence,
    )

    assert result.answer_source == "model"
    assert result.evidence_ids == ("result-1",)
    assert gateway.received_evidence == evidence


async def test_synthesis_falls_back_for_invented_evidence_reference() -> None:
    evidence = (
        AgentEvidenceItem(id="result-1", tool_name="profile", data={"status": "active"}),
    )
    result = await AgentAnswerSynthesisService(
        FixedAnswerGateway(
            AgentAnswerDraft(
                answer="Invented answer",
                evidence_ids=("result-99",),
            )
        )
    ).synthesize(user_request="What is the status?", evidence=evidence)

    assert result.answer_source == "deterministic"
    assert result.evidence_ids == ("result-1",)


async def test_synthesis_falls_back_when_provider_fails() -> None:
    evidence = (
        AgentEvidenceItem(id="result-1", tool_name="profile", data={"status": "active"}),
    )
    result = await AgentAnswerSynthesisService(FailingAnswerGateway()).synthesize(
        user_request="What is the status?",
        evidence=evidence,
    )

    assert result.answer_source == "deterministic"
    assert "result-1" in result.answer


async def test_openai_answer_request_contains_only_request_and_evidence() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=provider_response(
                {
                    "answer": "The organization is active.",
                    "evidence_ids": ["result-1"],
                }
            ),
        )

    gateway = build_provider(httpx.MockTransport(handler))
    answer = await gateway.create_answer(
        user_request="What is the status?",
        evidence=(
            AgentEvidenceItem(
                id="result-1",
                tool_name="get_organization_profile",
                data={"status": "active"},
            ),
        ),
    )

    serialized_payload = json.dumps(captured_payload)
    assert answer.evidence_ids == ("result-1",)
    assert "available_tools" not in serialized_payload
    assert "tool_calls" not in serialized_payload
    assert captured_payload["store"] is False
    await gateway._http_client.aclose()
