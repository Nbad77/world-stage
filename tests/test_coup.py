"""
fixes_8 — Coup detection tests at military 0.

2 tests:
1. test_coup_fires_at_military_zero: military=0, stability=20, coup_immune=False -> fires in majority of 100 runs
2. test_coup_blocked_by_immunity: military=0, stability=20, coup_immune=True -> never fires
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import check_game_over


def _fresh_gs(**overrides):
    """Create a GameState for coup testing."""
    gs = GameState()
    gs.military_strength = overrides.get('military', 20)
    gs.stability = overrides.get('stability', 50)
    gs.budget = overrides.get('budget', 30.0)
    gs.public_approval = overrides.get('approval', 50)
    gs.personal_wealth = overrides.get('pw', 5.0)
    gs.current_turn = overrides.get('turn', 5)
    gs.max_turns = 10
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.coup_immune = overrides.get('coup_immune', False)
    # Ensure these exist for check_game_over
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    return gs


def test_coup_fires_at_military_zero():
    """Military=0, stability=20, not immune: coup should fire in majority of runs."""
    coup_count = 0
    runs = 100
    for _ in range(runs):
        gs = _fresh_gs(military=0, stability=20, coup_immune=False)
        is_over, result, msg = check_game_over(gs)
        if is_over and result == 'defeat' and gs.stability <= 0:
            coup_count += 1

    # At military=0, stability=20: base prob 15%, x3 = 45%, so ~45 fires per 100
    assert coup_count >= 20, f"Coup fired only {coup_count}/{runs} times (expected ~45, min 20)"
    print(f"  PASSED: Coup fired {coup_count}/{runs} times at military=0, stability=20.")


def test_coup_blocked_by_immunity():
    """Military=0, stability=20, coup_immune=True: coup must NEVER fire."""
    coup_count = 0
    runs = 100
    for _ in range(runs):
        gs = _fresh_gs(military=0, stability=20, coup_immune=True)
        is_over, result, msg = check_game_over(gs)
        if is_over and result == 'defeat' and 'COLLAPSE' in (msg or '').upper():
            coup_count += 1

    assert coup_count == 0, f"Coup fired {coup_count}/{runs} times despite coup_immune=True"
    print(f"  PASSED: Coup never fired with coup_immune=True across {runs} runs.")


if __name__ == '__main__':
    print("\n=== test_coup_fires_at_military_zero ===")
    test_coup_fires_at_military_zero()

    print("\n=== test_coup_blocked_by_immunity ===")
    test_coup_blocked_by_immunity()

    print("\n=== ALL COUP TESTS PASSED ===")
