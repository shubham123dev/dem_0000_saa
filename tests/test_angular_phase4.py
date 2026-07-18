from __future__ import annotations
from pathlib import Path
from scripts.validate_angular_phase4 import validate
ROOT=Path(__file__).resolve().parents[1]

def test_phase4_conversation_contract()->None:
 assert validate(ROOT)==[]

def test_phase4_does_not_claim_streaming_or_server_history()->None:
 docs=(ROOT/'frontend/docs/PHASE_4_CONVERSATION.md').read_text(encoding='utf-8')
 assert 'does not expose a conversation ID' in docs
 assert 'never fabricates intermediate reasoning' in docs
 assert 'sessionStorage' in docs
