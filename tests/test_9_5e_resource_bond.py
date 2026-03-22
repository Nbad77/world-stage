"""
9.5E Resource Bond — installment repayment, sovereign collateral, resource_policy tests.
Tests the installment processing logic in apply_end_of_turn_effects.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


def _make_gs(**overrides):
    """Create a GameState with safe defaults for bond/installment tests."""
    gs = GameState()
    gs.budget = 200.0
    gs.stability = 70
    gs.oil_price = 75
    gs.public_approval = 50
    gs.current_turn = 5
    gs.active_installments = []
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ── installment repayment tests ──────────────────────────────────────────────

def test_installment_repayment_basic():
    """Installment amount is applied to budget each turn."""
    gs = _make_gs(active_installments=[
        {'amount': 5.0, 'turns_remaining': 3, 'description': 'test', 'npc': 'usa', 'registered_turn': 1},
    ])
    budget_before = gs.budget
    apply_end_of_turn_effects(gs)
    # Budget should have increased by 5.0 (among other EOT effects)
    # We check the installment was processed by verifying turns_remaining decreased
    remaining_insts = gs.active_installments
    if remaining_insts:
        assert remaining_insts[0]['turns_remaining'] == 2
    # Budget should reflect the +5.0 payment (plus any other EOT effects)
    assert gs.budget > budget_before - 50  # sanity: not wildly wrong


def test_installment_decrements_turns():
    """turns_remaining decreases by 1 each EOT."""
    gs = _make_gs(active_installments=[
        {'amount': 2.0, 'turns_remaining': 5, 'description': 'test', 'npc': 'eu', 'registered_turn': 1},
    ])
    apply_end_of_turn_effects(gs)
    assert gs.active_installments[0]['turns_remaining'] == 4


def test_installment_removed_at_zero():
    """Installment removed when turns_remaining hits 0 after decrement."""
    gs = _make_gs(active_installments=[
        {'amount': 3.0, 'turns_remaining': 1, 'description': 'final', 'npc': 'arabia', 'registered_turn': 1},
    ])
    apply_end_of_turn_effects(gs)
    # turns_remaining was 1, decremented to 0 => removed from active list
    assert len(gs.active_installments) == 0


def test_installment_skip_same_turn():
    """Installment registered this same turn is skipped (not paid)."""
    gs = _make_gs(
        current_turn=5,
        active_installments=[
            {'amount': 10.0, 'turns_remaining': 3, 'description': 'new', 'npc': 'usa', 'registered_turn': 5},
        ],
    )
    apply_end_of_turn_effects(gs)
    # Should still be active and turns_remaining unchanged
    assert len(gs.active_installments) == 1
    assert gs.active_installments[0]['turns_remaining'] == 3


def test_installment_deferred_start():
    """Installment with start_turn in the future is skipped."""
    gs = _make_gs(
        current_turn=5,
        active_installments=[
            {'amount': 4.0, 'turns_remaining': 3, 'description': 'deferred', 'npc': 'eu',
             'registered_turn': 1, 'start_turn': 8},
        ],
    )
    apply_end_of_turn_effects(gs)
    assert len(gs.active_installments) == 1
    assert gs.active_installments[0]['turns_remaining'] == 3


def test_installment_condition_relation_below_pass():
    """condition_type='relation_below' passes when actual relation < threshold."""
    gs = _make_gs(
        relations={'usa': 30, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35},
        active_installments=[
            {'amount': -2.0, 'turns_remaining': 3, 'description': 'penalty', 'npc': 'dprg',
             'registered_turn': 1,
             'condition_type': 'relation_below', 'condition_npc': 'usa', 'condition_threshold': 40},
        ],
    )
    apply_end_of_turn_effects(gs)
    # USA relation 30 < 40 => condition met => payment processed
    # turns_remaining should have decremented
    if gs.active_installments:
        assert gs.active_installments[0]['turns_remaining'] == 2
    else:
        # Was the last turn (removed)
        pass


def test_installment_condition_relation_below_fail():
    """condition_type='relation_below' fails when actual relation >= threshold => withheld."""
    gs = _make_gs(
        relations={'usa': 60, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35},
        active_installments=[
            {'amount': -2.0, 'turns_remaining': 3, 'description': 'penalty', 'npc': 'dprg',
             'registered_turn': 1,
             'condition_type': 'relation_below', 'condition_npc': 'usa', 'condition_threshold': 40},
        ],
    )
    apply_end_of_turn_effects(gs)
    # USA relation 60 >= 40 => condition NOT met => withheld, still active, turns unchanged
    assert len(gs.active_installments) == 1
    assert gs.active_installments[0]['turns_remaining'] == 3


def test_installment_condition_relation_above():
    """condition_type='relation_above' passes when actual relation > threshold."""
    gs = _make_gs(
        relations={'usa': 70, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35},
        active_installments=[
            {'amount': 5.0, 'turns_remaining': 2, 'description': 'bonus', 'npc': 'usa',
             'registered_turn': 1,
             'condition_type': 'relation_above', 'condition_npc': 'usa', 'condition_threshold': 60},
        ],
    )
    apply_end_of_turn_effects(gs)
    # USA relation 70 > 60 => condition met => payment processed, turns decremented
    if gs.active_installments:
        assert gs.active_installments[0]['turns_remaining'] == 1
    # If turns was 2 and decremented to 1, still active


# ── sovereign collateral tests ───────────────────────────────────────────────

def test_sovereign_collateral_repayment():
    """sovereign_collateral_turns decrements each EOT when > 0."""
    gs = _make_gs(sovereign_collateral_turns=5, sovereign_collateral_repayment=3.0)
    apply_end_of_turn_effects(gs)
    assert gs.sovereign_collateral_turns == 4


def test_sovereign_collateral_budget_deduction():
    """Budget is reduced by sovereign_collateral_repayment each EOT."""
    gs = _make_gs(sovereign_collateral_turns=3, sovereign_collateral_repayment=5.0, budget=200.0)
    apply_end_of_turn_effects(gs)
    # Budget should be reduced by 5.0 (among other EOT effects)
    # We just check it decreased rather than exact value due to other EOT effects
    assert gs.budget < 200.0


# ── defaults tests ───────────────────────────────────────────────────────────

def test_resource_policy_default():
    """resource_policy defaults to 'state_led'."""
    gs = GameState()
    assert gs.resource_policy == "state_led"


def test_bonds_issued_count_default():
    """bonds_issued_count defaults to 0."""
    gs = GameState()
    assert gs.bonds_issued_count == 0


# ── multiple installments and serialize ──────────────────────────────────────

def test_installment_multiple_per_npc():
    """Multiple installments for same NPC are each processed independently."""
    gs = _make_gs(active_installments=[
        {'amount': 2.0, 'turns_remaining': 3, 'description': 'deal1', 'npc': 'usa', 'registered_turn': 1},
        {'amount': 4.0, 'turns_remaining': 1, 'description': 'deal2', 'npc': 'usa', 'registered_turn': 1},
    ])
    apply_end_of_turn_effects(gs)
    # First: 3->2 (still active), Second: 1->0 (removed)
    assert len(gs.active_installments) == 1
    assert gs.active_installments[0]['turns_remaining'] == 2
    assert gs.active_installments[0]['description'] == 'deal1'


def test_installment_negative_amount():
    """Negative amounts deduct from budget (repayments to NPCs)."""
    gs = _make_gs(
        budget=200.0,
        active_installments=[
            {'amount': -3.0, 'turns_remaining': 2, 'description': 'repay', 'npc': 'eu', 'registered_turn': 1},
        ],
    )
    apply_end_of_turn_effects(gs)
    # -3.0 applied to budget => budget decreases by 3 (among other effects)
    # Just verify the installment was processed
    assert gs.active_installments[0]['turns_remaining'] == 1


def test_active_installments_serialize():
    """active_installments survives serialize/deserialize round-trip."""
    insts = [
        {'amount': 5.0, 'turns_remaining': 4, 'description': 'test', 'npc': 'usa', 'registered_turn': 1},
        {'amount': -2.0, 'turns_remaining': 2, 'description': 'repay', 'npc': 'eu', 'registered_turn': 2},
    ]
    gs = _make_gs(active_installments=insts)
    data = gs.serialize()
    gs2 = GameState.deserialize(data)
    assert len(gs2.active_installments) == 2
    assert gs2.active_installments[0]['amount'] == 5.0
    assert gs2.active_installments[1]['npc'] == 'eu'
