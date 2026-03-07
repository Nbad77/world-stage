"""
fixes_12 Fix 4 — Epitaph system removed, replaced by historian summary.

Tests verify:
1. generate_historian_summary exists and returns a string
2. _static_historian_fallback covers all terminal states
3. historian_summary field persists through serialize/deserialize
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from npc_engine import (
    generate_historian_summary,
    _static_historian_fallback,
    HISTORIAN_SYSTEM,
)


# ── Test 1: Static fallback covers all terminal states ─────────────────

def test_historian_fallback_covers_terminal_states():
    """Each terminal state (bankruptcy, collapse, revolt, victory) should
    produce a distinct non-empty fallback string."""
    fallbacks = set()

    # Bankruptcy
    gs = GameState()
    gs.budget = -5.0
    gs.personal_wealth = 10.0
    gs.stability = 50
    gs.public_approval = 50
    result = _static_historian_fallback(gs)
    assert len(result) > 20, f"Bankruptcy fallback too short: {result}"
    fallbacks.add(result)
    print(f"  Bankruptcy: {result[:60]}...")

    # Collapse
    gs2 = GameState()
    gs2.budget = 20.0
    gs2.stability = -5
    gs2.public_approval = 40
    gs2.personal_wealth = 5.0
    result2 = _static_historian_fallback(gs2)
    assert len(result2) > 20, f"Collapse fallback too short: {result2}"
    fallbacks.add(result2)
    print(f"  Collapse:   {result2[:60]}...")

    # Revolt
    gs3 = GameState()
    gs3.budget = 20.0
    gs3.stability = 50
    gs3.public_approval = -5
    gs3.personal_wealth = 3.0
    result3 = _static_historian_fallback(gs3)
    assert len(result3) > 20, f"Revolt fallback too short: {result3}"
    fallbacks.add(result3)
    print(f"  Revolt:     {result3[:60]}...")

    # Victory (none of the above trigger)
    gs4 = GameState()
    gs4.budget = 30.0
    gs4.stability = 70
    gs4.public_approval = 65
    gs4.personal_wealth = 15.0
    # FIX B: Victory now triggers at current_turn >= max_turns (no longer needs 11)
    gs4.current_turn = 10
    gs4.max_turns = 10
    result4 = _static_historian_fallback(gs4)
    assert len(result4) > 20, f"Victory fallback too short: {result4}"
    fallbacks.add(result4)
    print(f"  Victory:    {result4[:60]}...")

    assert len(fallbacks) == 4, "All 4 terminal states should produce distinct fallbacks"
    print(f"\n  PASSED: All 4 terminal states produce distinct historian fallbacks.")


# ── Test 2: HISTORIAN_SYSTEM prompt has key constraints ────────────────

def test_historian_system_prompt():
    """HISTORIAN_SYSTEM should contain required institutional role names."""
    assert 'Bill Hartwell' in HISTORIAN_SYSTEM
    assert 'Sadam' in HISTORIAN_SYSTEM
    assert 'Marsha' in HISTORIAN_SYSTEM
    assert 'Ji-won Ryang' in HISTORIAN_SYSTEM
    assert 'oligarch' in HISTORIAN_SYSTEM.lower()
    assert 'power broker' in HISTORIAN_SYSTEM.lower()
    assert 'historian' in HISTORIAN_SYSTEM.lower()

    print("  PASSED: HISTORIAN_SYSTEM contains required institutional roles and constraints.")


# ── Test 3: historian_summary persists through serialize/deserialize ────

def test_historian_summary_persistence():
    """historian_summary field should survive serialize/deserialize round-trip."""
    gs = GameState()
    gs.historian_summary = "The regime collapsed under its own contradictions."

    serialized = gs.serialize()
    assert serialized.get('historian_summary') == gs.historian_summary

    gs2 = GameState.deserialize(serialized)
    assert gs2.historian_summary == gs.historian_summary

    print(f"  PASSED: historian_summary persists through serialization.")


# ── Test 4: generate_historian_summary calls API or returns fallback ────

def test_generate_historian_summary_without_api():
    """Without API key, should return a static fallback."""
    gs = GameState()
    gs.budget = -1.0  # bankruptcy
    gs.personal_wealth = 5.0

    with patch.dict(os.environ, {}, clear=True):
        # Remove ANTHROPIC_API_KEY
        os.environ.pop('ANTHROPIC_API_KEY', None)
        result = generate_historian_summary(gs)

    assert isinstance(result, str)
    assert len(result) > 20
    print(f"  No-API result: {result[:60]}...")
    print(f"  PASSED: generate_historian_summary returns fallback without API key.")


if __name__ == '__main__':
    tests = [
        ("test_historian_fallback_covers_terminal_states", test_historian_fallback_covers_terminal_states),
        ("test_historian_system_prompt", test_historian_system_prompt),
        ("test_historian_summary_persistence", test_historian_summary_persistence),
        ("test_generate_historian_summary_without_api", test_generate_historian_summary_without_api),
    ]
    for name, fn in tests:
        print(f"\n=== {name} ===")
        fn()
    print("\n=== ALL HISTORIAN SUMMARY TESTS PASSED ===")
