"""
fixes_10 Fix 6 — Arabia embargo tier boundary warning tests.

2 tests verifying that the tier boundary warning fires at near-boundary
relations and stays silent when far from boundaries.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import apply_end_of_turn_effects


def _setup_gs(arabia_rel=50):
    """Create a game state with given Arabia relations and reasonable defaults."""
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': arabia_rel, 'eu': 50, 'dprg': 50}
    gs.budget = 30.0
    gs.stability = 50
    gs.public_approval = 50
    gs.oil_price = 75
    gs.current_turn = 3
    gs.max_turns = 10
    return gs


# ── Test 1: Near boundary warning fires ──────────────────────────────────

def test_near_boundary_warning_fires():
    """Arabia relations at 27 (within 5 of boundary 25) should produce
    a tier boundary warning in EOT messages."""
    gs = _setup_gs(arabia_rel=27)
    messages = apply_end_of_turn_effects(gs)

    # Look for the Arabia tier boundary warning
    tier_warnings = [m for m in messages if 'Arabia near oil tier boundary' in m]
    assert len(tier_warnings) >= 1, (
        f"Expected Arabia tier boundary warning at rel=27, got messages: {messages}"
    )

    print("  PASSED: Arabia tier boundary warning fires at rel=27 (near boundary 25).")


# ── Test 2: Far from boundary — no warning ───────────────────────────────

def test_far_from_boundary_no_warning():
    """Arabia relations at 50 (far from any boundary) should NOT produce
    a tier boundary warning."""
    gs = _setup_gs(arabia_rel=50)
    messages = apply_end_of_turn_effects(gs)

    tier_warnings = [m for m in messages if 'Arabia near oil tier boundary' in m]
    assert len(tier_warnings) == 0, (
        f"No tier boundary warning expected at rel=50, but got: {tier_warnings}"
    )

    print("  PASSED: No Arabia tier boundary warning when far from boundaries.")


if __name__ == '__main__':
    tests = [
        ("test_near_boundary_warning_fires", test_near_boundary_warning_fires),
        ("test_far_from_boundary_no_warning", test_far_from_boundary_no_warning),
    ]
    for name, fn in tests:
        print(f"\n=== {name} ===")
        fn()
    print("\n=== ALL 2 ARABIA TESTS PASSED ===")
