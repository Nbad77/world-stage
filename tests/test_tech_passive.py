"""
Tests for Tech Level Passive Acquisition — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: fractional accumulation formula, regime modifier,
tech level advancement, and EOT integration.
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
    gs.tech_level = 0
    gs.tech_level_fractional = 0.0
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
    return gs


def test_tech_gain_formula():
    """Verify the weighted formula: EU*0.60 + USA*0.25 + DPRG*0.15"""
    gs = _fresh_gs()
    # EU 80, USA 60, DPRG 40 -> (0.80*0.60) + (0.60*0.25) + (0.40*0.15) = 0.48 + 0.15 + 0.06 = 0.69
    gs.relations = {'usa': 60, 'arabia': 50, 'eu': 80, 'dprg': 40}
    gs.state_identity['regime_type'] = 'Managed Democracy'

    expected_raw = (80/100.0) * 0.60 + (60/100.0) * 0.25 + (40/100.0) * 0.15
    # Managed Democracy multiplier: 1.1
    expected = round(expected_raw * 1.1, 3)

    # Run EOT and check fractional gain
    old_frac = gs.tech_level_fractional
    apply_end_of_turn_effects(gs)
    new_frac = gs.tech_level_fractional + (gs.tech_level - 0)  # add back any integer advances

    actual_gain = round(new_frac - old_frac, 3)
    assert abs(actual_gain - expected) < 0.01, \
        f"Expected tech gain ~{expected}, got {actual_gain}"
    print(f"  PASS: tech gain formula correct: {actual_gain} (expected {expected})")


def test_regime_modifier_slows_tech():
    """Authoritarian regimes should produce less tech gain than democracies."""
    # Run with Managed Democracy (1.1x)
    gs_dem = _fresh_gs()
    gs_dem.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs_dem.state_identity['regime_type'] = 'Managed Democracy'

    # Run with Totalitarian (0.5x)
    gs_tot = _fresh_gs()
    gs_tot.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs_tot.state_identity['regime_type'] = 'Totalitarian Regime'

    apply_end_of_turn_effects(gs_dem)
    apply_end_of_turn_effects(gs_tot)

    dem_tech = gs_dem.tech_level_fractional + gs_dem.tech_level
    tot_tech = gs_tot.tech_level_fractional + gs_tot.tech_level

    assert dem_tech > tot_tech, \
        f"Democracy tech ({dem_tech}) should exceed Totalitarian tech ({tot_tech})"
    print(f"  PASS: regime modifier — Democracy {dem_tech:.3f} > Totalitarian {tot_tech:.3f}")


def test_tech_level_advances_on_full_point():
    """When fractional tech >= 1.0, tech_level should increase by 1."""
    gs = _fresh_gs()
    gs.relations = {'usa': 100, 'arabia': 50, 'eu': 100, 'dprg': 100}
    gs.tech_level = 5
    gs.tech_level_fractional = 0.95  # Close to 1.0, high relations push over
    gs.state_identity['regime_type'] = 'Managed Democracy'

    apply_end_of_turn_effects(gs)

    assert gs.tech_level >= 6, \
        f"Tech level should have advanced from 5, got {gs.tech_level}"
    assert gs.tech_level_fractional < 1.0, \
        f"Fractional should be < 1.0 after advancement, got {gs.tech_level_fractional}"
    print(f"  PASS: tech level advanced to {gs.tech_level} (fractional: {gs.tech_level_fractional:.3f})")


def test_zero_relations_zero_tech_gain():
    """With all relations at 0, tech gain should be 0 (or near-0)."""
    gs = _fresh_gs()
    gs.relations = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0}
    gs.tech_level = 0
    gs.tech_level_fractional = 0.0
    gs.state_identity['regime_type'] = 'Managed Democracy'

    apply_end_of_turn_effects(gs)

    # Should be 0 gain: (0*0.60 + 0*0.25 + 0*0.15) * 1.1 = 0
    assert gs.tech_level_fractional == 0.0, \
        f"Expected 0 fractional gain at 0 relations, got {gs.tech_level_fractional}"
    assert gs.tech_level == 0, f"Tech level should stay at 0, got {gs.tech_level}"
    print("  PASS: zero relations -> zero tech gain")


if __name__ == '__main__':
    print("\n=== test_tech_passive.py ===\n")
    test_tech_gain_formula()
    test_regime_modifier_slows_tech()
    test_tech_level_advances_on_full_point()
    test_zero_relations_zero_tech_gain()
    print("\nAll test_tech_passive tests passed!")
