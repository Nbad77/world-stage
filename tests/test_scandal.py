"""
fixes_8 — Scandal threshold floor enforcement tests.

2 tests:
1. test_scandal_no_fire_below_30: heat=25, verify scandal never fires across 100 simulated rolls
2. test_scandal_fires_above_85: heat=95 (decays -5 to 90 in roll_detection), verify scandal fires frequently
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import roll_detection


def _fresh_gs(**overrides):
    """Create a GameState for scandal testing."""
    gs = GameState()
    gs.detection_heat = overrides.get('heat', 0)
    gs.personal_wealth = overrides.get('pw', 10.0)
    gs.scandals_triggered = overrides.get('scandals', 0)
    gs.last_scandal_turn = overrides.get('last_scandal', -10)  # far in past
    gs.current_turn = overrides.get('turn', 5)
    gs.corruption_upgrades = {}
    gs.public_approval = 50
    gs.stability = 50
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    return gs


def test_scandal_no_fire_below_30():
    """Heat=25: scandal should NEVER fire. Run 100 simulations."""
    fire_count = 0
    for _ in range(100):
        gs = _fresh_gs(heat=25, pw=10.0)
        msgs = roll_detection(gs)
        if any('SCANDAL' in m.upper() or 'CORRUPTION' in m.upper() for m in msgs):
            fire_count += 1

    assert fire_count == 0, f"Scandal fired {fire_count}/100 times at heat=25 (should be 0)"
    print(f"  PASSED: No scandals fired at heat=25 across 100 runs.")


def test_scandal_fires_above_85():
    """Heat=95 (decays to 90 after -5 turn decay): scandal should fire frequently (85% probability)."""
    fire_count = 0
    runs = 100
    for _ in range(runs):
        # Heat 95 decays -5 to 90 inside roll_detection, putting it in 90+ bracket (85% prob)
        gs = _fresh_gs(heat=95, pw=10.0)
        msgs = roll_detection(gs)
        if any('SCANDAL' in m.upper() or 'CORRUPTION' in m.upper() for m in msgs):
            fire_count += 1

    # At 85% probability, expect ~85 fires out of 100. Allow some variance.
    assert fire_count >= 60, f"Scandal fired only {fire_count}/{runs} times at heat=95 (expected ~85)"
    print(f"  PASSED: Scandal fired {fire_count}/{runs} times at heat=95 (expected ~85).")


def test_scandal_blocked_by_judicial_capture():
    """fixes_9 Fix 3: Judicial Capture active → scandal NEVER fires, even at max heat."""
    fire_count = 0
    for _ in range(100):
        gs = _fresh_gs(heat=95, pw=20.0)
        gs.action_judiciary_captured = True  # judicial capture enacted
        msgs = roll_detection(gs)
        if any('SCANDAL' in m.upper() and 'MINOR' in m.upper() or 'MAJOR' in m.upper() for m in msgs):
            fire_count += 1

    assert fire_count == 0, f"Scandal fired {fire_count}/100 times with judicial capture active (should be 0)"
    # Verify the immunity message is present
    gs_check = _fresh_gs(heat=95, pw=20.0)
    gs_check.action_judiciary_captured = True
    msgs = roll_detection(gs_check)
    immunity_msgs = [m for m in msgs if 'judiciary' in m.lower() or 'immunity' in m.lower() or 'suspended' in m.lower()]
    assert len(immunity_msgs) > 0, f"Expected immunity message, got: {msgs}"
    print("  PASSED: Scandal blocked by judicial capture across 100 runs at heat=95.")


if __name__ == '__main__':
    print("\n=== test_scandal_no_fire_below_30 ===")
    test_scandal_no_fire_below_30()

    print("\n=== test_scandal_fires_above_85 ===")
    test_scandal_fires_above_85()

    print("\n=== test_scandal_blocked_by_judicial_capture ===")
    test_scandal_blocked_by_judicial_capture()

    print("\n=== ALL SCANDAL TESTS PASSED ===")
