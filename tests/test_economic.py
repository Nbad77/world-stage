"""
Tests for Economic Development Model — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: GDP growth formula, revenue stream calculation,
stability modifier on growth, sanctions suppression, and
revenue_streams persistence.
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


def test_gdp_grows_each_turn():
    """GDP base should increase by the growth rate each turn."""
    gs = _fresh_gs()
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.stability = 50  # neutral — no modifier

    old_gdp = gs.gdp_base
    apply_end_of_turn_effects(gs)

    # Growth should be ~2% (stability 50 = no modifier, no sanctions)
    assert gs.gdp_base > old_gdp, f"GDP should grow: {old_gdp} -> {gs.gdp_base}"
    # Expected: 100 * 1.02 = 102.0
    expected = round(100.0 * 1.02, 1)
    assert abs(gs.gdp_base - expected) < 1.0, \
        f"GDP should be ~{expected}, got {gs.gdp_base}"
    print(f"  PASS: GDP grew from {old_gdp} to {gs.gdp_base} (~{expected} expected)")


def test_high_stability_boosts_growth():
    """Stability >= 70 should add +0.01 to growth rate."""
    gs = _fresh_gs()
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.stability = 85  # high enough to stay >= 70 after EOT effects (approval drift etc.)

    apply_end_of_turn_effects(gs)

    # Expected growth: 0.02 + 0.01 = 0.03 -> 100 * 1.03 = 103.0
    expected = round(100.0 * 1.03, 1)
    assert gs.gdp_base >= expected - 0.5, \
        f"High stability GDP should be ~{expected}, got {gs.gdp_base}"
    print(f"  PASS: high stability boosted GDP to {gs.gdp_base} (expected ~{expected})")


def test_low_stability_penalizes_growth():
    """Stability < 30 should subtract -0.02 from growth rate."""
    gs = _fresh_gs()
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.stability = 20  # low -> -0.02 growth penalty

    apply_end_of_turn_effects(gs)

    # Expected growth: 0.02 - 0.02 = 0.00 -> 100 * 1.00 = 100.0
    expected = round(100.0 * 1.00, 1)
    assert gs.gdp_base <= expected + 0.5, \
        f"Low stability GDP should be ~{expected}, got {gs.gdp_base}"
    print(f"  PASS: low stability penalized GDP to {gs.gdp_base} (expected ~{expected})")


def test_sanctions_suppress_growth():
    """USA sanctions tier >= 2 should reduce growth by -0.01."""
    gs = _fresh_gs()
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.stability = 50
    gs.usa_sanctions_tier = 2
    gs.usa_sanctions_active = True
    gs.relations['usa'] = 20  # low enough to keep sanctions active through EOT

    apply_end_of_turn_effects(gs)

    # Expected growth: 0.02 - 0.01 = 0.01 -> 100 * 1.01 = 101.0
    expected = round(100.0 * 1.01, 1)
    assert gs.gdp_base <= expected + 0.5, \
        f"Sanctions should slow GDP to ~{expected}, got {gs.gdp_base}"
    print(f"  PASS: sanctions suppressed GDP to {gs.gdp_base} (expected ~{expected})")


def test_revenue_streams_populated():
    """Revenue streams should be populated after EOT."""
    gs = _fresh_gs()
    gs.tax_rates = {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25}
    gs.gdp_base = 100.0

    apply_end_of_turn_effects(gs)

    rev = gs.revenue_streams
    assert rev.get('income_tax', 0) > 0, f"Income tax revenue should be > 0, got {rev.get('income_tax')}"
    assert rev.get('corporate_tax', 0) > 0, f"Corporate tax revenue should be > 0, got {rev.get('corporate_tax')}"
    assert rev.get('resource_tax', 0) > 0, f"Resource tax revenue should be > 0, got {rev.get('resource_tax')}"

    print(f"  PASS: revenue streams populated: income=${rev.get('income_tax')}B, "
          f"corp=${rev.get('corporate_tax')}B, resource=${rev.get('resource_tax')}B")


def test_revenue_streams_survive_serialization():
    """Revenue streams should persist through serialize/deserialize."""
    gs = _fresh_gs()
    gs.revenue_streams = {'income_tax': 2.0, 'corporate_tax': 1.2, 'resource_tax': 2.1,
                          'trade_tariffs': 0.0, 'foreign_aid': 0.0, 'tourism': 0.0,
                          'arms_exports': 0.0, 'financial_sector': 0.0}

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert gs2.revenue_streams.get('income_tax') == 2.0, \
        f"Income tax mismatch: {gs2.revenue_streams.get('income_tax')}"
    assert gs2.revenue_streams.get('corporate_tax') == 1.2, \
        f"Corporate tax mismatch: {gs2.revenue_streams.get('corporate_tax')}"
    print("  PASS: revenue_streams survive serialize/deserialize")


if __name__ == '__main__':
    print("\n=== test_economic.py ===\n")
    test_gdp_grows_each_turn()
    test_high_stability_boosts_growth()
    test_low_stability_penalizes_growth()
    test_sanctions_suppress_growth()
    test_revenue_streams_populated()
    test_revenue_streams_survive_serialization()
    print("\nAll test_economic tests passed!")
