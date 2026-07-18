from __future__ import annotations

from pathlib import Path

from scripts.validate_angular_phase4 import validate

ROOT = Path(__file__).resolve().parents[1]


def test_phase4_conversation_contract() -> None:
    assert validate(ROOT) == []


def test_phase4_presentation_remains_compatible_after_durable_runs() -> None:
    docs = (ROOT / "frontend/docs/PHASE_4_CONVERSATION.md").read_text(
        encoding="utf-8"
    )
    assert "presentation components remain in use" in docs
    assert (
        ROOT / "frontend/src/app/core/agent-run/agent-run-stream.service.ts"
    ).is_file()
