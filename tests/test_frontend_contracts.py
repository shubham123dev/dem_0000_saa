from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_frontend_contracts import validate_contracts

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_contracts_match_registered_backend() -> None:
    assert validate_contracts(ROOT) == []


def test_manifest_is_unique_and_contains_durable_run_surface() -> None:
    manifest = json.loads(
        (ROOT / "frontend/contracts/api-manifest.json").read_text(encoding="utf-8")
    )
    endpoints = manifest["endpoints"]
    assert manifest["endpoint_count"] == 36 == len(endpoints)
    keys = {(item["method"], item["path"]) for item in endpoints}
    assert len(keys) == len(endpoints)
    assert (
        "GET",
        "/workplace/organizations/{organization_id}/agent/runs/{run_id}/events",
    ) in keys


def test_browser_identity_remains_infrastructure_owned() -> None:
    manifest = json.loads(
        (ROOT / "frontend/contracts/api-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["authentication"]["header"] == "X-Mock-User-Id"
    assert "components never provide user IDs" in manifest["authentication"][
        "browser_rule"
    ]


def test_safe_activity_contract_never_exposes_private_reasoning() -> None:
    schema_text = (
        ROOT / "frontend/contracts/agent-run-event.schema.json"
    ).read_text(encoding="utf-8").lower()
    assert "activity.updated" in schema_text
    assert "chain_of_thought" not in schema_text
    assert "tool_arguments" not in schema_text
    assert "system_prompt" not in schema_text
