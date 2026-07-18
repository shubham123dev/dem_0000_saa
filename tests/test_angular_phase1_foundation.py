from __future__ import annotations

import importlib.util
from pathlib import Path


def _validator_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "validate_angular_phase1.py"
    spec = importlib.util.spec_from_file_location("validate_angular_phase1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_angular_phase1_static_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    _validator_module().validate(root)


def test_frontend_does_not_claim_streaming_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    config = (root / "frontend/public/config/app-config.json").read_text(encoding="utf-8")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "frontend/src/app").rglob("*.ts")
    )
    assert '"streamTransport": "rest"' in config
    assert "new EventSource" not in source
    assert "new WebSocket" not in source
