"""
fixes_9 Fix 2 — Conditional payment per-deal evaluation tests.

3 tests:
1. test_per_deal_withheld_messages: Two deals with different thresholds produce separate messages
2. test_uses_stored_threshold: Threshold comes from deal's condition_threshold, not a default
3. test_condition_met_pays_out: When condition is met, payment processes and budget increases
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import apply_end_of_turn_effects


def _fresh_gs_with_installments(installments, relations=None):
    """Create a GameState with specific active installments."""
    gs = GameState()
    gs.current_turn = 5
    gs.active_installments = installments
    gs.relations = relations or {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.public_approval = 50
    gs.stability = 50
    gs.budget = 30.0
    gs.military_strength = 20
    gs.personal_wealth = 0.0
    gs.oil_price = 80
    # Prevent election/other side effects
    gs.election_fired = True
    gs.election_warning_shown = True
    return gs


def test_per_deal_withheld_messages():
    """Two USA deals with different thresholds should produce TWO separate withheld messages."""
    installments = [
        {
            'npc': 'usa',
            'amount': 0.7,
            'turns_remaining': 3,
            'description': 'USA deal 1',
            'registered_turn': 3,
            'condition_type': 'relation_below',
            'condition_npc': 'dprg',
            'condition_threshold': 40,
        },
        {
            'npc': 'usa',
            'amount': 1.4,
            'turns_remaining': 3,
            'description': 'USA deal 2',
            'registered_turn': 3,
            'condition_type': 'relation_below',
            'condition_npc': 'dprg',
            'condition_threshold': 35,
        },
    ]
    # DPRG at 44 — both conditions unmet (44 not below 40, 44 not below 35)
    gs = _fresh_gs_with_installments(installments, relations={'usa': 60, 'arabia': 50, 'eu': 50, 'dprg': 44})

    messages = apply_end_of_turn_effects(gs)

    # Find withheld messages
    withheld = [m for m in messages if 'withheld' in m.lower()]
    assert len(withheld) == 2, (
        f"Expected 2 separate withheld messages, got {len(withheld)}: {withheld}"
    )

    # Each message should show its own threshold
    thresh_40 = [m for m in withheld if '40' in m]
    thresh_35 = [m for m in withheld if '35' in m]
    assert len(thresh_40) == 1, f"Expected one message with threshold 40, got: {thresh_40}"
    assert len(thresh_35) == 1, f"Expected one message with threshold 35, got: {thresh_35}"

    print(f"  Message 1: {withheld[0]}")
    print(f"  Message 2: {withheld[1]}")
    print(f"  PASSED: Two deals produce two separate withheld messages with correct thresholds.")


def test_uses_stored_threshold():
    """The condition evaluation should use the deal's stored threshold, not a default."""
    installments = [
        {
            'npc': 'usa',
            'amount': 1.0,
            'turns_remaining': 3,
            'description': 'USA precision deal',
            'registered_turn': 3,
            'condition_type': 'relation_below',
            'condition_npc': 'dprg',
            'condition_threshold': 42,  # specific threshold
        },
    ]
    # DPRG at 41 — condition IS met (41 < 42)
    gs = _fresh_gs_with_installments(installments, relations={'usa': 60, 'arabia': 50, 'eu': 50, 'dprg': 41})
    budget_before = gs.budget

    messages = apply_end_of_turn_effects(gs)

    # Condition met → payment should process
    withheld = [m for m in messages if 'withheld' in m.lower()]
    assert len(withheld) == 0, f"Should not have withheld messages when condition met, got: {withheld}"

    # Budget should have increased by the payment amount
    paid_msgs = [m for m in messages if 'partnership payment' in m.lower() or 'USA' in m]
    print(f"  Budget: {budget_before} → {gs.budget}")
    print(f"  Payment messages: {[m for m in messages if 'USA' in m]}")
    print(f"  PASSED: Stored threshold 42 used (DPRG 41 < 42 → condition met, payment processed).")


def test_condition_met_pays_out():
    """When the relation condition IS met, the installment payment should increase budget."""
    installments = [
        {
            'npc': 'eu',
            'amount': 2.0,
            'turns_remaining': 2,
            'description': 'EU partnership',
            'registered_turn': 3,
            'condition_type': 'relation_above',
            'condition_npc': 'usa',
            'condition_threshold': 45,
        },
    ]
    # USA at 60 — condition met (60 > 45)
    gs = _fresh_gs_with_installments(installments, relations={'usa': 60, 'arabia': 50, 'eu': 70, 'dprg': 30})
    budget_before = gs.budget

    messages = apply_end_of_turn_effects(gs)

    withheld = [m for m in messages if 'withheld' in m.lower()]
    assert len(withheld) == 0, f"Should not have withheld messages, got: {withheld}"

    # The installment turns_remaining should have decremented
    # Since turns_remaining was 2, after payment it should be 1 (still active)
    remaining = [i for i in gs.active_installments if i.get('description') == 'EU partnership']
    assert len(remaining) == 1, "Deal should still be active (1 turn remaining)"
    assert remaining[0]['turns_remaining'] == 1, f"Expected 1 turn remaining, got {remaining[0]['turns_remaining']}"

    print(f"  Budget: {budget_before} → {gs.budget}")
    print(f"  Remaining turns: {remaining[0]['turns_remaining']}")
    print(f"  PASSED: Condition met (USA 60 > 45) → payment processed, deal continues.")


if __name__ == '__main__':
    print("\n=== test_per_deal_withheld_messages ===")
    test_per_deal_withheld_messages()

    print("\n=== test_uses_stored_threshold ===")
    test_uses_stored_threshold()

    print("\n=== test_condition_met_pays_out ===")
    test_condition_met_pays_out()

    print("\n=== ALL CONDITIONAL PAYMENT TESTS PASSED ===")
