"""
fixes_10 Fix 2 — Personal wealth ledger tests.

3 tests verifying that domestic action costs are recorded in the
personal wealth ledger via update_personal_wealth().
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import apply_domestic_action, DOMESTIC_ACTION_CONSEQUENCES


def _setup_gs_with_wealth(pw=20.0):
    """Create a game state with enough personal wealth for any domestic action."""
    gs = GameState()
    gs.personal_wealth = pw
    # Ensure ledger exists and starts from the right balance
    gs.pw_ledger = [{'turn': 0, 'change': pw, 'source': 'test_setup', 'balance': pw}]
    return gs


# ── Test 1: Domestic action recorded in ledger ───────────────────────────

def test_domestic_action_recorded_in_ledger():
    """Enacting judicial_capture should create a ledger entry with
    amount=-4.0 and source containing 'domestic action'."""
    gs = _setup_gs_with_wealth(20.0)
    initial_ledger_len = len(gs.pw_ledger)

    success, changes = apply_domestic_action(gs, 'judicial_capture')
    assert success, f"Judicial Capture should succeed, got: {changes}"

    # Ledger should have grown by 1
    assert len(gs.pw_ledger) > initial_ledger_len, (
        f"Ledger should have new entry: was {initial_ledger_len}, now {len(gs.pw_ledger)}"
    )

    # Find the domestic action entry
    new_entries = gs.pw_ledger[initial_ledger_len:]
    domestic_entries = [e for e in new_entries if 'domestic action' in e.get('source', '').lower()]
    assert len(domestic_entries) >= 1, (
        f"Expected at least 1 domestic action ledger entry, got {len(domestic_entries)}. "
        f"All new entries: {new_entries}"
    )

    entry = domestic_entries[0]
    assert entry['change'] == -4.0, f"Expected change=-4.0, got {entry['change']}"

    print(f"  Ledger entry: {entry}")
    print(f"  PASSED: Domestic action creates correct ledger entry.")


# ── Test 2: Ledger sum matches personal wealth ───────────────────────────

def test_ledger_sum_matches_personal_wealth():
    """After a domestic action, the sum of all ledger changes should
    equal game_state.personal_wealth."""
    gs = _setup_gs_with_wealth(20.0)

    success, _ = apply_domestic_action(gs, 'suppress_press')
    assert success

    ledger_sum = sum(e['change'] for e in gs.pw_ledger)
    assert abs(ledger_sum - gs.personal_wealth) < 0.05, (
        f"Ledger sum ({ledger_sum}) != personal_wealth ({gs.personal_wealth})"
    )

    print(f"  Ledger sum: {ledger_sum}, personal_wealth: {gs.personal_wealth}")
    print(f"  PASSED: Ledger sum matches personal wealth after domestic action.")


# ── Test 3: All action types recorded ────────────────────────────────────

def test_all_action_types_recorded():
    """Each of the 5 domestic actions should create a ledger entry."""
    actions = list(DOMESTIC_ACTION_CONSEQUENCES.keys())
    assert len(actions) == 5, f"Expected 5 domestic actions, got {len(actions)}"

    for action_key in actions:
        gs = _setup_gs_with_wealth(30.0)
        cost = DOMESTIC_ACTION_CONSEQUENCES[action_key]['cost']
        label = DOMESTIC_ACTION_CONSEQUENCES[action_key]['label']
        initial_count = len(gs.pw_ledger)

        success, changes = apply_domestic_action(gs, action_key)
        assert success, f"{label} should succeed with $30B: {changes}"

        new_entries = gs.pw_ledger[initial_count:]
        domestic_entries = [e for e in new_entries if 'domestic action' in e.get('source', '').lower()]
        assert len(domestic_entries) >= 1, (
            f"{label}: no domestic action ledger entry found. New entries: {new_entries}"
        )
        assert domestic_entries[0]['change'] == -cost, (
            f"{label}: expected change=-{cost}, got {domestic_entries[0]['change']}"
        )
        print(f"  {label}: ledger entry -${cost}B ✓")

    print(f"\n  PASSED: All 5 domestic actions create correct ledger entries.")


if __name__ == '__main__':
    tests = [
        ("test_domestic_action_recorded_in_ledger", test_domestic_action_recorded_in_ledger),
        ("test_ledger_sum_matches_personal_wealth", test_ledger_sum_matches_personal_wealth),
        ("test_all_action_types_recorded", test_all_action_types_recorded),
    ]
    for name, fn in tests:
        print(f"\n=== {name} ===")
        fn()
    print("\n=== ALL 3 LEDGER TESTS PASSED ===")
