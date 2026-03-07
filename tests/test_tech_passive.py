"""
Tests for Tech Level Passive Acquisition — Redesigned
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: relationship-weighted formula, deal bonus multiplier,
float accumulation, and zero-relations edge case.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import apply_end_of_turn_effects


def _fresh_gs():
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 50
    gs.public_approval = 50
    gs.budget = 50.0
    gs.oil_price = 50
    gs.current_turn = 3
    gs.max_turns = 10
    gs.personal_wealth = 0.0
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.cabinet_axes = {'security': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}
    gs.tech_level = 0.0
    gs.tech_gain_last_turn = 0.0
    gs.advisors = []
    gs.advisor_pool = []
    gs.advisors_eliminated = []
    gs.advisor_actions_log = []
    gs.advisor_distortions = {}
    gs.tax_rates = {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25}
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.revenue_streams = {}
    gs.resource_endowment = {'oil_reserves': 0.7, 'mineral_deposits': 0.3, 'arable_land': 0.4, 'rare_earths': 0.1, 'coastal_access': 0.6}
    gs.soft_power = 0
    gs.diplomatic_capital = 0
    gs.npc_contact_history = {}
    gs.pending_npc_contacts = []
    gs.brigade_operations_this_turn = []
    gs.deal_history = []
    return gs


def test_tech_gain_formula():
    """Verify the weighted formula: EU*1.0 + USA*0.9 + DPRG*0.5 + Arabia*0.3, all × BASE_RATE 0.5"""
    gs = _fresh_gs()
    gs.relations = {'usa': 60, 'arabia': 40, 'eu': 80, 'dprg': 40}

    # Expected: (80/100*1.0 + 60/100*0.9 + 40/100*0.3 + 40/100*0.5) * 0.5
    #         = (0.80 + 0.54 + 0.12 + 0.20) * 0.5 = 1.66 * 0.5 = 0.83
    expected = round((0.80*1.0 + 0.60*0.9 + 0.40*0.3 + 0.40*0.5) * 0.5, 3)

    apply_end_of_turn_effects(gs)

    assert abs(gs.tech_level - expected) < 0.15, \
        f"Expected tech ~{expected}, got {gs.tech_level}"
    assert abs(gs.tech_gain_last_turn - expected) < 0.15, \
        f"Expected tech_gain_last_turn ~{expected}, got {gs.tech_gain_last_turn}"
    print(f"  PASS: tech gain formula correct: {gs.tech_level} (expected ~{expected})")


def test_deal_bonus_multiplier():
    """NPC with a deal accepted this turn gets 1.5× contribution."""
    gs_no_deal = _fresh_gs()
    gs_no_deal.relations = {'usa': 50, 'arabia': 50, 'eu': 80, 'dprg': 50}

    gs_with_deal = _fresh_gs()
    gs_with_deal.relations = {'usa': 50, 'arabia': 50, 'eu': 80, 'dprg': 50}
    gs_with_deal.deal_history = [{'npc': 'eu', 'turn_accepted': 3, 'summary': 'test deal'}]

    apply_end_of_turn_effects(gs_no_deal)
    apply_end_of_turn_effects(gs_with_deal)

    assert gs_with_deal.tech_level > gs_no_deal.tech_level, \
        f"Deal bonus should increase tech: with={gs_with_deal.tech_level}, without={gs_no_deal.tech_level}"
    print(f"  PASS: deal bonus — with deal: {gs_with_deal.tech_level}, without: {gs_no_deal.tech_level}")


def test_tech_accumulates_as_float():
    """Tech level should accumulate as a float across turns."""
    gs = _fresh_gs()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}

    apply_end_of_turn_effects(gs)
    first_level = gs.tech_level
    assert isinstance(first_level, float), f"tech_level should be float, got {type(first_level)}"
    assert first_level > 0, f"tech_level should be > 0, got {first_level}"

    # Second turn
    gs.current_turn = 4
    apply_end_of_turn_effects(gs)
    assert gs.tech_level > first_level, \
        f"Tech should accumulate: turn 2 ({gs.tech_level}) > turn 1 ({first_level})"
    print(f"  PASS: float accumulation — turn 1: {first_level}, turn 2: {gs.tech_level}")


def test_zero_relations_zero_tech_gain():
    """With all relations at 0, tech gain should be 0."""
    gs = _fresh_gs()
    gs.relations = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}
    gs.tech_level = 0.0

    apply_end_of_turn_effects(gs)

    assert gs.tech_gain_last_turn == 0.0, \
        f"Expected 0 gain at 0 relations, got {gs.tech_gain_last_turn}"
    assert gs.tech_level == 0.0, f"Tech level should stay at 0, got {gs.tech_level}"
    print("  PASS: zero relations -> zero tech gain")


if __name__ == '__main__':
    print("\n=== test_tech_passive.py ===\n")
    test_tech_gain_formula()
    test_deal_bonus_multiplier()
    test_tech_accumulates_as_float()
    test_zero_relations_zero_tech_gain()
    print("\nAll test_tech_passive tests passed!")
