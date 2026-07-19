from __future__ import annotations

import json
import logging

from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseOpenAIResponsesAgentModelGateway,
)

logger = logging.getLogger("app.agent_model")


class OpenAIResponsesAgentModelGateway(BaseOpenAIResponsesAgentModelGateway):
    """Normalize only harmless optional questions on complete plans.

    The provider schema requires clarification fields for every intent. A model can
    therefore attach an optional follow-up question even after selecting a complete
    read or action plan. This adapter clears only that non-executable field when the
    plan is otherwise exclusive and reports no missing business fields. The strict
    base parser remains authoritative for operation names, exact argument keys,
    required values, mixed intents and every other invalid response.
    """

    def _extract_output_text(self, response_payload: dict[str, object]) -> str:
        output_text = super()._extract_output_text(response_payload)
        try:
            payload = json.loads(output_text)
        except (json.JSONDecodeError, TypeError):
            return output_text

        if not isinstance(payload, dict):
            return output_text

        intent = payload.get("intent")
        tool_calls = payload.get("tool_calls")
        action_name = payload.get("action_name")
        action_arguments = payload.get("action_arguments")
        missing_fields = payload.get("missing_fields")
        clarification_question = payload.get("clarification_question")

        if (
            not isinstance(clarification_question, str)
            or not clarification_question.strip()
            or missing_fields != []
            or not isinstance(action_arguments, dict)
        ):
            return output_text

        normalization_reason: str | None = None
        if (
            intent == "read"
            and isinstance(tool_calls, list)
            and bool(tool_calls)
            and action_name is None
            and all(value is None for value in action_arguments.values())
        ):
            normalization_reason = "complete_read_optional_question"
        elif (
            intent == "action_proposal"
            and tool_calls == []
            and isinstance(action_name, str)
            and action_name.strip()
        ):
            normalization_reason = "complete_action_optional_question"

        if normalization_reason is None:
            return output_text

        payload["clarification_question"] = None
        logger.info(
            "Normalized non-blocking planner question",
            extra={
                "planner_normalization": normalization_reason,
                "provider_response_id": response_payload.get("id"),
                "action_name": action_name if intent == "action_proposal" else None,
            },
        )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
