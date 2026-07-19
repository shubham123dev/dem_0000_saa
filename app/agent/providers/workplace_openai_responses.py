from __future__ import annotations

import json

from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseOpenAIResponsesAgentModelGateway,
)


class OpenAIResponsesAgentModelGateway(BaseOpenAIResponsesAgentModelGateway):
    """Normalize a harmless optional question on an otherwise complete read plan.

    The provider schema requires the clarification field for every intent. A model
    can therefore attach a preference question even after selecting a complete,
    action-free read plan. The base parser intentionally rejects genuinely mixed
    plans, so this adapter clears only that one non-executable field when there
    are no missing fields and every action field is empty.
    """

    def _extract_output_text(self, response_payload: dict[str, object]) -> str:
        output_text = super()._extract_output_text(response_payload)
        try:
            payload = json.loads(output_text)
        except (json.JSONDecodeError, TypeError):
            return output_text

        if not isinstance(payload, dict) or payload.get("intent") != "read":
            return output_text

        action_arguments = payload.get("action_arguments")
        missing_fields = payload.get("missing_fields")
        clarification_question = payload.get("clarification_question")
        if (
            payload.get("action_name") is None
            and isinstance(action_arguments, dict)
            and all(value is None for value in action_arguments.values())
            and missing_fields == []
            and isinstance(clarification_question, str)
            and clarification_question.strip()
        ):
            payload["clarification_question"] = None
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        return output_text
