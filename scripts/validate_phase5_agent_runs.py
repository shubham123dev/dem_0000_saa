#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "alembic/versions/0016_agent_conversations_runs_events.py",
    "app/db/agent_run_models.py",
    "app/agent/run_contracts.py",
    "app/agent/instrumented_orchestrator.py",
    "app/repositories/agent_run_repository.py",
    "app/services/agent_run_service.py",
    "app/services/agent_run_activity.py",
    "app/services/agent_run_worker.py",
    "app/api/agent_run_routes.py",
    "app/schemas/agent_run.py",
    "frontend/contracts/agent-run-event.schema.json",
    "frontend/src/app/core/agent-run/agent-run-stream.service.ts",
    "frontend/src/app/core/agent-run/sse-frame-parser.ts",
    "frontend/src/app/features/assistant-conversation/assistant-activity/assistant-activity.component.ts",
    "frontend/docs/PHASE_5_DURABLE_RUNS_SSE.md",
    "frontend/docs/PHASE_5_ACCEPTANCE.md",
)


def _text(repo: Path, relative: str) -> str:
    return (repo / relative).read_text(encoding="utf-8")


def validate(repo: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (repo / relative).is_file():
            errors.append(f"{relative}: missing")

    migration = _text(repo, "alembic/versions/0016_agent_conversations_runs_events.py")
    for table in ("agent_conversations", "agent_messages", "agent_runs", "agent_run_events"):
        if table not in migration:
            errors.append(f"migration missing {table}")
    for required in (
        "uq_agent_run_request_idempotency",
        "uq_agent_run_event_sequence",
        "ix_agent_run_claim",
        "source_agent_run_id",
        "ux_agent_action_proposal_source_run",
        "uq_agent_run_active_conversation",
    ):
        if required not in migration:
            errors.append(f"migration missing durability constraint {required}")

    routes = _text(repo, "app/api/agent_run_routes.py")
    for required in (
        "StreamingResponse",
        "Last-Event-ID",
        "after_sequence",
        "text/event-stream",
        "X-Accel-Buffering",
        "request.is_disconnected",
        "current_run.terminal",
        "async_sessionmaker",
        "await session.close()",
    ):
        if required not in routes:
            errors.append(f"agent run routes missing {required}")
    if "repository._session" in routes:
        errors.append("SSE route must not reach into a repository private session")

    worker = _text(repo, "app/services/agent_run_worker.py")
    for required in (
        "claim_next",
        "renew_lease",
        "run_once",
        "AgentRunCancelled",
        "agent_run_id=run_id",
        "get_proposal_by_source_agent_run_id",
        "await session.rollback()",
    ):
        if required not in worker:
            errors.append(f"agent run worker missing {required}")

    service = _text(repo, "app/services/agent_run_service.py")
    if "self._preflight_service.authorize" not in service:
        errors.append("AgentRunService must authorize create, read, stream, and cancel access")

    repository = _text(repo, "app/repositories/agent_run_repository.py")
    for required in (
        "client_request_id",
        "next_event_sequence",
        "source_count",
        "proposal_id",
        "AgentConversationBusyRepositoryError",
        "active_slot",
    ):
        if required not in repository:
            errors.append(f"agent run repository missing {required}")
    proposal_metadata = repository.split("def _proposal_metadata", 1)[-1].split("def _completion_metadata", 1)[0]
    if '"id": proposal.id' in proposal_metadata:
        errors.append("public proposal metadata must not expose proposal IDs")

    action_repository = _text(repo, "app/repositories/agent_action_repository.py")
    hardened_service = _text(repo, "app/services/hardened_agent_action_service.py")
    action_model = _text(repo, "app/db/action_models.py")
    for source in (action_repository, hardened_service, action_model):
        if "source_agent_run_id" not in source:
            errors.append("action proposal persistence is not idempotent by source agent run")
            break

    response_service = _text(repo, "app/agent/response_service.py")
    for required in ("AgentRunActivitySink", "activity.checkpoint", "agent_run_id"):
        if required not in response_service:
            errors.append(f"response service missing real activity boundary {required}")

    stream = _text(repo, "frontend/src/app/core/agent-run/agent-run-stream.service.ts")
    for required in (
        "fetch(",
        "X-Mock-User-Id",
        "X-Request-Id",
        "Last-Event-ID",
        "after_sequence",
        "reconnecting",
        "TextDecoder",
        "AbortSignal",
        "frame.id",
        "frame.event",
    ):
        if required not in stream:
            errors.append(f"Angular stream missing {required}")
    for forbidden in ("new EventSource", "WebSocket(", "chain-of-thought", "setInterval("):
        if forbidden in stream:
            errors.append(f"Angular stream contains forbidden implementation: {forbidden}")

    store = _text(repo, "frontend/src/app/features/assistant-conversation/agent-conversation.store.ts")
    if "streamTransport === 'sse'" not in store:
        errors.append("conversation store does not select real SSE transport")
    if "private persistRecovery" not in store or "private removeRecovery" not in store:
        errors.append("conversation store is missing bounded recovery persistence")
    else:
        recovery_block = store.split("private persistRecovery", 1)[1].split(
            "private removeRecovery", 1
        )[0]
        if "sessionStorage.setItem" not in recovery_block or "messages:" in recovery_block:
            errors.append(
                "session recovery must keep identifiers/cursor only, not authoritative messages"
            )
    if "dismissClarification(): void { this.clearConversation(); }" not in store:
        errors.append("starting a new request after clarification must create a new conversation")

    parser = _text(repo, "frontend/src/app/core/agent-run/sse-frame-parser.ts")
    for required in ("pendingCarriageReturn", "data.join", "retry"):
        if required not in parser:
            errors.append(f"SSE parser missing {required}")

    config = json.loads(_text(repo, "frontend/public/config/app-config.json"))
    if config.get("streamTransport") != "sse":
        errors.append("runtime config must select sse")
    config_model = _text(repo, "frontend/src/app/core/config/app-config.model.ts")
    if "z.enum(['sse', 'rest'])" not in config_model:
        errors.append("runtime config must retain explicit REST fallback")

    package = json.loads(_text(repo, "frontend/package.json"))
    if "validate:phase5" not in package.get("scripts", {}):
        errors.append("package.json missing validate:phase5")

    main = _text(repo, "app/main.py")
    if "AgentRunCoordinator" not in main or "agent_run_routes.router" not in main:
        errors.append("FastAPI lifespan does not own the durable run coordinator")

    event_contract = _text(repo, "frontend/contracts/agent-run-event.schema.json").lower()
    for forbidden in ("chain_of_thought", "system_prompt", "tool_arguments", "sql"):
        if forbidden in event_contract:
            errors.append(f"safe event contract contains forbidden field {forbidden}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    errors = validate(Path(args.repo).resolve())
    if errors:
        print("Phase 5 validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Phase 5 is valid: durable conversations, idempotent leased runs, "
        "safe persisted events, resumable authenticated SSE, and Angular recovery pass."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
