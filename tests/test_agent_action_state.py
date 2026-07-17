from __future__ import annotations

import pytest

from app.agent.action_state import can_transition, require_transition


def test_only_declared_action_state_transitions_are_allowed() -> None:
    allowed = {
        ("pending_approval", "approved"),
        ("pending_approval", "rejected"),
        ("pending_approval", "expired"),
        ("pending_approval", "cancelled"),
        ("approved", "executing"),
        ("approved", "expired"),
        ("approved", "cancelled"),
        ("approved", "stale"),
        ("executing", "succeeded"),
        ("executing", "failed"),
        ("executing", "stale"),
        ("executing", "reconciliation_required"),
        ("reconciliation_required", "succeeded"),
        ("reconciliation_required", "failed"),
    }
    for current, target in allowed:
        assert can_transition(current, target)
        require_transition(current, target)

    forbidden = {
        ("rejected", "approved"),
        ("expired", "approved"),
        ("cancelled", "executing"),
        ("stale", "executing"),
        ("succeeded", "executing"),
        ("failed", "executing"),
        ("executing", "approved"),
    }
    for current, target in forbidden:
        assert not can_transition(current, target)
        with pytest.raises(ValueError):
            require_transition(current, target)
