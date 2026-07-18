from __future__ import annotations

from pathlib import Path

from scripts.validate_phase5_agent_runs import validate

ROOT = Path(__file__).resolve().parents[1]


def test_phase5_contract() -> None:
    assert validate(ROOT) == []


def test_phase5_never_persists_or_streams_private_reasoning() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "app/services/agent_run_worker.py",
            ROOT / "app/repositories/agent_run_repository.py",
            ROOT / "app/api/agent_run_routes.py",
            ROOT / "frontend/contracts/agent-run-event.schema.json",
        )
    ).lower()
    for forbidden in (
        "reasoning_json",
        "chain_of_thought",
        "system_prompt",
        "tool_arguments",
    ):
        assert forbidden not in sources


def test_phase5_keeps_webhooks_and_websockets_out_of_the_sse_slice() -> None:
    routes = (ROOT / "app/api/agent_run_routes.py").read_text(encoding="utf-8")
    stream = (
        ROOT / "frontend/src/app/core/agent-run/agent-run-stream.service.ts"
    ).read_text(encoding="utf-8")
    assert "webhook" not in routes.lower()
    assert "WebSocket(" not in stream
    assert "new EventSource" not in stream
