from __future__ import annotations

from pathlib import Path

from scripts.validate_angular_phase2 import validate

ROOT = Path(__file__).resolve().parents[1]


def test_phase2_design_system_contract() -> None:
    assert validate(ROOT) == []


def test_phase2_keeps_raw_agent_activity_out_of_the_showcase() -> None:
    template = (ROOT / 'frontend/src/app/app.component.html').read_text(encoding='utf-8')
    assert 'chain-of-thought' not in template.lower()
    assert 'fake activity' in template.lower()
