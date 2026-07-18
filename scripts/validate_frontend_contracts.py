#!/usr/bin/env python3
"""Validate the browser-facing contract inventory against FastAPI OpenAPI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_ENDPOINT_COUNT = 36


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _ref_name(schema: dict[str, Any] | None) -> str | None:
    if not schema:
        return None
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    for key in ("allOf", "oneOf", "anyOf"):
        values = schema.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    found = _ref_name(value)
                    if found:
                        return found
    return None


def _operation_schema(
    operation: dict[str, Any], *, request: bool, response_status: int = 200
) -> dict[str, Any] | None:
    if request:
        return (
            operation.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema")
        )
    response = operation.get("responses", {}).get(str(response_status), {})
    content = response.get("content", {})
    for media_type in ("application/json", "text/event-stream"):
        schema = content.get(media_type, {}).get("schema")
        if schema:
            return schema
    return None


def _validate_ui_samples(examples_dir: Path, errors: list[str]) -> None:
    required_common = {"type", "event_id", "conversation_id", "occurred_at", "payload"}
    payload_requirements = {
        "activity_update": {"stage", "status", "title", "sequence"},
        "proposal": {"proposal"},
        "execution_update": {"proposal_id", "outcome", "steps"},
    }
    for path in sorted(examples_dir.glob("ui-*.json")):
        data = _load_json(path)
        missing = required_common - set(data)
        if missing:
            errors.append(f"{path}: missing UI event fields {sorted(missing)}")
            continue
        event_type = data.get("type")
        if event_type not in payload_requirements:
            errors.append(f"{path}: unsupported UI sample type {event_type!r}")
            continue
        payload = data.get("payload")
        if not isinstance(payload, dict):
            errors.append(f"{path}: payload must be an object")
            continue
        missing_payload = payload_requirements[event_type] - set(payload)
        if missing_payload:
            errors.append(f"{path}: missing payload fields {sorted(missing_payload)}")


def validate_contracts(repo: Path) -> list[str]:
    sys.path.insert(0, str(repo))

    from app.core.errors import ERROR_CODES
    from app.main import create_app
    from app.schemas.agent import AgentQueryResponse
    from app.schemas.agent_actions import (
        AgentActionApprovalResponse,
        AgentActionExecutionResponse,
        AgentActionProposalResponse,
    )
    from app.schemas.agent_run import (
        AgentConversationResponse,
        AgentRunCreateResponse,
        AgentRunEventOut,
        AgentRunOut,
    )
    from app.schemas.organization import CapabilitiesResponse
    from app.schemas.workplace_resources import WorkplaceResourceSearchResponse

    errors: list[str] = []
    contracts = repo / "frontend" / "contracts"
    manifest_path = contracts / "api-manifest.json"
    schema_path = contracts / "ui-event.schema.json"
    run_event_schema_path = contracts / "agent-run-event.schema.json"
    examples_dir = contracts / "examples"

    manifest = _load_json(manifest_path)
    endpoints = manifest.get("endpoints")
    if not isinstance(endpoints, list):
        return ["api-manifest.json: endpoints must be an array"]
    if manifest.get("endpoint_count") != len(endpoints):
        errors.append("api-manifest.json: endpoint_count does not match endpoints")
    if len(endpoints) != EXPECTED_ENDPOINT_COUNT:
        errors.append(
            f"api-manifest.json: expected {EXPECTED_ENDPOINT_COUNT} endpoints, found {len(endpoints)}"
        )

    seen: set[tuple[str, str]] = set()
    openapi = create_app().openapi()
    paths = openapi.get("paths", {})
    for item in endpoints:
        method = str(item.get("method", "")).upper()
        path = item.get("path")
        key = (method, path)
        if key in seen:
            errors.append(f"duplicate endpoint {method} {path}")
        seen.add(key)
        if path not in paths:
            errors.append(f"missing OpenAPI path {path}")
            continue
        operation = paths[path].get(method.lower())
        if not isinstance(operation, dict):
            errors.append(f"missing OpenAPI operation {method} {path}")
            continue

        parameter_names = {
            str(parameter.get("name", "")).lower()
            for parameter in operation.get("parameters", [])
            if isinstance(parameter, dict)
        }
        if item.get("auth") and "x-mock-user-id" not in parameter_names:
            errors.append(f"{method} {path}: missing X-Mock-User-Id header")

        request_model = item.get("request_model")
        if request_model:
            actual_request = _ref_name(_operation_schema(operation, request=True))
            if actual_request != request_model:
                errors.append(
                    f"{method} {path}: request model {actual_request!r}, expected {request_model!r}"
                )

        response_model = item.get("response_model")
        if response_model:
            status_code = int(item.get("response_status", 200))
            actual_response = _ref_name(
                _operation_schema(
                    operation,
                    request=False,
                    response_status=status_code,
                )
            )
            if actual_response != response_model:
                errors.append(
                    f"{method} {path}: response model {actual_response!r}, expected {response_model!r}"
                )

    model_samples = {
        "agent-read-answer.json": AgentQueryResponse,
        "agent-clarification.json": AgentQueryResponse,
        "agent-action-proposal.json": AgentQueryResponse,
        "proposal-pending.json": AgentActionProposalResponse,
        "approval-approved.json": AgentActionApprovalResponse,
        "execution-succeeded.json": AgentActionExecutionResponse,
        "execution-reconciliation-required.json": AgentActionExecutionResponse,
        "resource-search.json": WorkplaceResourceSearchResponse,
        "capabilities-shape.json": CapabilitiesResponse,
        "agent-run-created.json": AgentRunCreateResponse,
        "agent-run-conversation.json": AgentConversationResponse,
        "agent-run-state.json": AgentRunOut,
        "agent-run-activity.json": AgentRunEventOut,
        "agent-run-answer.json": AgentRunEventOut,
    }
    for filename, model in model_samples.items():
        try:
            model.model_validate(_load_json(examples_dir / filename))
        except Exception as exception:
            errors.append(f"{filename}: {exception}")

    error_sample = _load_json(examples_dir / "error-stale.json")
    envelope = error_sample.get("error")
    if not isinstance(envelope, dict):
        errors.append("error-stale.json: error must be an object")
    else:
        if set(envelope) != {"code", "message", "request_id"}:
            errors.append("error-stale.json: error envelope fields are not exact")
        if envelope.get("code") not in ERROR_CODES:
            errors.append("error-stale.json: unknown backend error code")

    ui_schema = _load_json(schema_path)
    definitions = ui_schema.get("$defs")
    if not isinstance(definitions, dict):
        errors.append("ui-event.schema.json: $defs must be an object")
    else:
        event_types = {
            definition.get("properties", {}).get("type", {}).get("const")
            for definition in definitions.values()
            if isinstance(definition, dict)
        }
        required_types = {
            "assistant_message",
            "clarification",
            "activity_update",
            "proposal",
            "approval_update",
            "execution_update",
            "receipt",
            "reconciliation",
            "error",
        }
        if event_types != required_types:
            errors.append("ui-event.schema.json: normalized event types do not match contract")
        if "reasoning" in event_types or "chain_of_thought" in event_types:
            errors.append("ui-event.schema.json: raw reasoning event is forbidden")

    run_event_schema = _load_json(run_event_schema_path)
    forbidden_serialized = json.dumps(run_event_schema).lower()
    for forbidden in ("chain_of_thought", "reasoning", "tool_arguments", "system_prompt"):
        if forbidden in forbidden_serialized:
            errors.append(f"agent-run-event.schema.json contains forbidden field {forbidden}")

    _validate_ui_samples(examples_dir, errors)

    gap_text = (repo / "frontend" / "docs" / "PHASE_0_GAPS.md").read_text(
        encoding="utf-8"
    )
    for resolved in (
        "Conversation persistence API | Resolved in Phase 5",
        "Streaming transport | Resolved in Phase 5",
        "Live activity trace | Resolved in Phase 5",
    ):
        if resolved not in gap_text:
            errors.append(f"PHASE_0_GAPS.md: missing resolved status {resolved}")
    for remaining in (
        "Stable execution-step endpoint",
        "Current-user endpoint",
        "File upload",
    ):
        if remaining not in gap_text:
            errors.append(f"PHASE_0_GAPS.md: missing remaining gap {remaining}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    errors = validate_contracts(Path(args.repo).resolve())
    if errors:
        print("Frontend contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Frontend contracts are valid: 36 endpoints, durable runs, and safe SSE events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
