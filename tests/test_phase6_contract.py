from __future__ import annotations
from pathlib import Path
from scripts.validate_phase6_action_control_plane import validate
ROOT=Path(__file__).resolve().parents[1]
def test_phase6_contract()->None: assert validate(ROOT)==[]
def test_phase6_has_no_provider_webhook_scope()->None:
 text=(ROOT/'docs/GOVERNED_ACTION_CONTROL_PLANE.md').read_text(encoding='utf-8')
 assert 'Cloudflare webhook' not in text
 assert 'GitHub webhook' not in text
