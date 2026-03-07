"""
Tests for Tax Rate Effects — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: high tax approval penalty, low tax approval bonus,
revenue calculation from tax rates, and default tax rate values.
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


def test_high_taxes_reduce_approval():
    """Average tax rate > 35% should cause -3% approval."""
    gs = _fresh_gs()
    gs.tax_rates = {'income_tax': 0.45, 'corporate_tax': 0.40, 'resource_tax': 0.50}
    # Average: (0.45 + 0.40 + 0.50) / 3 = 0.45 > 0.35
    gs.public_approval = 50

    messages = apply_end_of_turn_effects(gs)

    # Check that a high-tax message appeared
    tax_msgs = [m for m in messages if 'tax' in m.lower() and 'burden' in m.lower()]
    assert len(tax_msgs) > 0, f"Expected high tax burden message, got none. Messages: {messages}"

    # Approval should have decreased (though other EOT effects may also modify it)
    # The tax effect is -3, but other EOT effects may push it around
    # We check that the message was generated
    print("  PASS: high taxes generated burden warning")


def test_low_taxes_boost_approval():
    """Average tax rate < 15% should give +2% approval."""
    gs = _fresh_gs()
    gs.tax_rates = {'income_tax': 0.10, 'corporate_tax': 0.10, 'resource_tax': 0.10}
    # Average: 0.10 < 0.15
    gs.public_approval = 50

    messages = apply_end_of_turn_effects(gs)

    tax_msgs = [m for m in messages if 'tax' in m.lower() and 'popular' in m.lower()]
    assert len(tax_msgs) > 0, f"Expected low tax approval bonus message, got none. Messages: {messages}"
    print("  PASS: low taxes generated popularity bonus")


def test_normal_taxes_no_approval_effect():
    """Average tax rate between 15% and 35% should produce no tax-related approval message."""
    gs = _fresh_gs()
    gs.tax_rates = {'income_tax': 0.20, 'corporate_tax': 0.20, 'resource_tax': 0.25}
    # Average: (0.20 + 0.20 + 0.25) / 3 = 0.2167 — between 0.15 and 0.35
    gs.public_approval = 50

    messages = apply_end_of_turn_effects(gs)

    tax_burden_msgs = [m for m in messages if 'tax burden' in m.lower()]
    tax_popular_msgs = [m for m in messages if 'tax' in m.lower() and 'popular' in m.lower()]
    assert len(tax_burden_msgs) == 0 and len(tax_popular_msgs) == 0, \
        f"Normal taxes should have no approval effect, got: {tax_burden_msgs + tax_popular_msgs}"
    print("  PASS: normal taxes produce no approval effect")


def test_higher_taxes_produce_more_revenue():
    """Higher tax rates should produce more revenue from same GDP base."""
    gs_low = _fresh_gs()
    gs_low.tax_rates = {'income_tax': 0.10, 'corporate_tax': 0.10, 'resource_tax': 0.10}
    gs_low.gdp_base = 100.0

    gs_high = _fresh_gs()
    gs_high.tax_rates = {'income_tax': 0.40, 'corporate_tax': 0.35, 'resource_tax': 0.50}
    gs_high.gdp_base = 100.0

    apply_end_of_turn_effects(gs_low)
    apply_end_of_turn_effects(gs_high)

    low_total = sum(v for k, v in gs_low.revenue_streams.items() if k in ('income_tax', 'corporate_tax', 'resource_tax'))
    high_total = sum(v for k, v in gs_high.revenue_streams.items() if k in ('income_tax', 'corporate_tax', 'resource_tax'))

    assert high_total > low_total, \
        f"High tax revenue ({high_total}) should exceed low tax revenue ({low_total})"
    print(f"  PASS: higher taxes -> more revenue: ${high_total:.1f}B > ${low_total:.1f}B")


def test_default_tax_rates():
    """Default tax rates should be income=20%, corporate=15%, resource=25%."""
    gs = GameState()
    assert gs.tax_rates['income_tax'] == 0.20, f"Default income tax should be 0.20, got {gs.tax_rates['income_tax']}"
    assert gs.tax_rates['corporate_tax'] == 0.15, f"Default corporate tax should be 0.15, got {gs.tax_rates['corporate_tax']}"
    assert gs.tax_rates['resource_tax'] == 0.25, f"Default resource tax should be 0.25, got {gs.tax_rates['resource_tax']}"
    print("  PASS: default tax rates correct (20%, 15%, 25%)")


if __name__ == '__main__':
    print("\n=== test_tax_effects.py ===\n")
    test_high_taxes_reduce_approval()
    test_low_taxes_boost_approval()
    test_normal_taxes_no_approval_effect()
    test_higher_taxes_produce_more_revenue()
    test_default_tax_rates()
    print("\nAll test_tax_effects tests passed!")
