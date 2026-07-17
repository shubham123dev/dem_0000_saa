from __future__ import annotations

import json

from pydantic_core import to_jsonable_python

from app.agent.answer_contracts import AgentEvidenceItem
from app.agent.contracts import AgentToolResult


class AgentEvidenceCompiler:
    def __init__(
        self,
        *,
        maximum_item_characters: int = 12000,
        maximum_total_characters: int = 40000,
    ) -> None:
        self._maximum_item_characters = maximum_item_characters
        self._maximum_total_characters = maximum_total_characters

    def compile(
        self,
        tool_results: tuple[AgentToolResult, ...],
    ) -> tuple[AgentEvidenceItem, ...]:
        evidence_items: list[AgentEvidenceItem] = []
        consumed_characters = 0
        for result_index, tool_result in enumerate(tool_results, start=1):
            evidence_id = f"result-{result_index}"
            jsonable_data = to_jsonable_python(tool_result.data)
            serialized_data = json.dumps(
                jsonable_data,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            remaining_characters = max(
                0,
                self._maximum_total_characters - consumed_characters,
            )
            item_limit = min(self._maximum_item_characters, remaining_characters)
            if len(serialized_data) > item_limit:
                jsonable_data = {
                    "truncated": True,
                    "preview": serialized_data[:item_limit],
                }
                serialized_data = json.dumps(
                    jsonable_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            consumed_characters += len(serialized_data)
            evidence_items.append(
                AgentEvidenceItem(
                    id=evidence_id,
                    tool_name=tool_result.tool_name,
                    data=jsonable_data,
                )
            )
        return tuple(evidence_items)
