"""
Tests for NPC-Initiated Contact — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fixes_15 Fix A: Updated for two-tier INCOMING system.
Tier 1: Single condition + probability gate (mocked to always fire in tests).
Tier 2: 5% ambient random (tested via mock).
"""

import sys
import os
from unittest.mock import patch
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
    gs.current_turn = 5
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
    gs.usa_sanctions_tier = 0
    gs.brigade_operations_this_turn = []
    return gs


def test_usa_concern_dprg_trigger():
    """USA contacts player when sanctions tier >= 2 (probability mocked to always fire)."""
    gs = _fresh_gs()
    gs.usa_sanctions_tier = 2
    gs.usa_sanctions_active = True
    gs.relations['usa'] = 20
    gs.npc_contact_history = {}

    # Mock random to always fire (return value below all thresholds)
    with patch('random.random', return_value=0.01):
        apply_end_of_turn_effects(gs)

    contacts = gs.pending_npc_contacts
    usa_contacts = [c for c in contacts if c.get('npc') == 'usa']
    assert len(usa_contacts) >= 1, f"Expected at least 1 USA contact, got {len(usa_contacts)}: {contacts}"
    print("  PASS: USA sanctions concern contact triggers correctly")


def test_dprg_wealth_notice_trigger():
    """DPRG contacts player when personal wealth >= $15B AND DPRG relations >= 40."""
    gs = _fresh_gs()
    gs.personal_wealth = 20.0
    gs.relations['dprg'] = 45
    gs.current_turn = 7
    gs.npc_contact_history = {}

    with patch('random.random', return_value=0.01):
        apply_end_of_turn_effects(gs)

    contacts = gs.pending_npc_contacts
    dprg_contacts = [c for c in contacts if c.get('npc') == 'dprg']
    assert len(dprg_contacts) >= 1, f"Expected at least 1 DPRG contact, got {len(dprg_contacts)}: {contacts}"
    print("  PASS: DPRG wealth notice triggers correctly")


def test_arabia_drift_concern_trigger():
    """Arabia contacts player when Arabia relations < 40 (probability mocked to always fire)."""
    gs = _fresh_gs()
    gs.relations['arabia'] = 35  # below 40 threshold
    gs.npc_contact_history = {}

    with patch('random.random', return_value=0.01):
        apply_end_of_turn_effects(gs)

    contacts = gs.pending_npc_contacts
    arabia_contacts = [c for c in contacts if c.get('npc') == 'arabia']
    assert len(arabia_contacts) >= 1, \
        f"Expected at least 1 Arabia contact, got {len(arabia_contacts)}: {contacts}"
    print("  PASS: Arabia drift concern triggers correctly")


def test_contact_cooldown_enforcement():
    """Contacts should not re-trigger within cooldown period."""
    gs = _fresh_gs()
    gs.usa_sanctions_tier = 2
    gs.usa_sanctions_active = True
    gs.relations['usa'] = 20
    gs.current_turn = 5

    # Pre-set cooldown: USA concern fired on turn 3 (3 turn cooldown, needs > turn 6)
    gs.npc_contact_history = {'usa_sanctions_concern': 3}

    with patch('random.random', return_value=0.01):
        apply_end_of_turn_effects(gs)

    contacts = gs.pending_npc_contacts
    usa_contacts = [c for c in contacts if c.get('npc') == 'usa' and c.get('trigger') == 'usa_sanctions_concern']
    assert len(usa_contacts) == 0, \
        f"USA contact should be on cooldown (fired turn 3, now turn 5, needs > turn 6), got {len(usa_contacts)}"
    print("  PASS: contact cooldown prevents re-trigger within cooldown period")


def test_no_contacts_when_conditions_not_met():
    """No Tier 1 contacts should be queued when no trigger conditions are met."""
    gs = _fresh_gs()
    gs.usa_sanctions_tier = 0
    gs.oil_price = 70
    gs.personal_wealth = 5.0
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.npc_contact_history = {}

    # Mock random to never fire ambient (return > 0.05)
    with patch('random.random', return_value=0.99):
        apply_end_of_turn_effects(gs)

    contacts = gs.pending_npc_contacts
    # Filter to only Tier 1 contacts (exclude ambient)
    tier1_contacts = [c for c in contacts if not c.get('trigger', '').endswith('_ambient')]
    assert len(tier1_contacts) == 0, f"Expected 0 Tier 1 contacts, got {len(tier1_contacts)}: {tier1_contacts}"
    print("  PASS: no Tier 1 contacts when conditions not met")


if __name__ == '__main__':
    print("\n=== test_npc_contact.py ===\n")
    test_usa_concern_dprg_trigger()
    test_dprg_wealth_notice_trigger()
    test_arabia_drift_concern_trigger()
    test_contact_cooldown_enforcement()
    test_no_contacts_when_conditions_not_met()
    print("\nAll test_npc_contact tests passed!")
