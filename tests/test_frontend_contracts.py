from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_frontend_contracts import validate_contracts

ROOT = Path(__file__).resolve().parents[1]


def test_phase0_contracts_match_registered_backend() -> None:
    assert validate_contracts(ROOT) == []


def test_manifest_is_pinned_and_unique() -> None:
    manifest = json.loads(
        (ROOT / "frontend/contracts/api-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["baseline_commit"] == "1863fc0ec62b148dc1976c154afa1f91e3375c16"
    endpoints = manifest["endpoints"]
    assert manifest["endpoint_count"] == 31 == len(endpoints)
    keys = {(item["method"], item["path"]) for item in endpoints}
    assert len(keys) == len(endpoints)


def test_browser_identity_is_interceptor_owned() -> None:
    manifest = json.loads(
        (ROOT / "frontend/contracts/api-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["authentication"]["header"] == "X-Mock-User-Id"
    assert "components never provide user IDs" in manifest["authentication"][
        "browser_rule"
    ]


def test_ui_event_contract_exposes_safe_activity_not_raw_reasoning() -> None:
    schema = json.loads(
        (ROOT / "frontend/contracts/ui-event.schema.json").read_text(
            encoding="utf-8"
        )
    )
    event_types = {
        definition["properties"]["type"]["const"]
        for definition in schema["$defs"].values()
    }
    assert "activity_update" in event_types
    assert "reasoning" not in event_types
    assert "chain_of_thought" not in event_types


def test_phase0_does_not_pretend_streaming_exists() -> None:
    event_doc = (ROOT / "frontend/docs/AGENT_EVENT_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    gap_doc = (ROOT / "frontend/docs/PHASE_0_GAPS.md").read_text(
        encoding="utf-8"
    )
    assert "does **not** claim that an SSE or WebSocket endpoint exists" in event_doc
    assert "No SSE or WebSocket agent-event endpoint exists" in gap_doc
