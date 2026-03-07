"""
Tests for the Advisor Engine — Session 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: pool generation, hiring, dismissal, elimination,
stat distortion, loyalty checks, and capacity gates.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random
from game_state import GameState
from advisor_engine import (
    ADVISOR_ARCHETYPES,
    NEFARIOUS_ARCHETYPES,
    get_advisor_capacity_gate,
    generate_advisor_pool,
    hire_advisor,
    dismiss_advisor,
    eliminate_advisor,
    apply_stat_distortion,
    check_advisor_loyalty,
)


def _fresh_gs():
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 50
    gs.public_approval = 50
    gs.budget = 50.0
    gs.current_turn = 3
    gs.personal_wealth = 10.0
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.advisors = []
    gs.advisor_pool = []
    gs.advisors_eliminated = []
    gs.cabinet_axes = {'military': 0, 'intelligence': 0, 'resource_dev': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}
    return gs


def test_capacity_gate_managed_democracy():
    """Managed Democracy unlocks technocrat, general, diplomat, propagandist (of base archetypes).
    Session 6: Spy Chief requires Intelligence axis >= 4 (was Spymaster/Security >= 3).
    Propagandist now available from Managed Democracy."""
    available = get_advisor_capacity_gate('Managed Democracy')
    assert 'technocrat' in available, "Technocrat should be available in Managed Democracy"
    assert 'general' in available, "General should be available in Managed Democracy"
    assert 'diplomat' in available, "Diplomat should be available in Managed Democracy"
    assert 'propagandist' in available, "Propagandist should be available in Managed Democracy"
    # Session 6: Spy Chief requires Intelligence axis >= 4
    assert 'spy_chief' not in available, "Spy Chief should NOT be available without Intelligence axis >= 4"
    assert 'oligarch' not in available, "Oligarch should NOT be available in Managed Democracy"
    print("  PASS: capacity gate — Managed Democracy unlocks correct archetypes")


def test_capacity_gate_kleptocracy():
    """Kleptocracy should unlock all base archetypes including ideologue.
    Session 6: Spy Chief requires Intelligence axis >= 4, General requires Military >= 3."""
    available = get_advisor_capacity_gate('Kleptocracy', cabinet_axes={'intelligence': 4, 'military': 3})
    for key in ADVISOR_ARCHETYPES:
        assert key in available, f"{key} should be available in Kleptocracy (with military/intelligence axes met)"
    print("  PASS: capacity gate — Kleptocracy unlocks all base archetypes")


def test_capacity_gate_nefarious_with_axes():
    """Session 6: Nefarious archetypes unlock based on military/political axis levels."""
    # Fixer requires political >= 3
    available = get_advisor_capacity_gate('Managed Democracy', {'political': 3})
    assert 'fixer' in available, "Fixer should unlock at political >= 3"
    assert 'enforcer' not in available, "Enforcer requires military >= 6"

    # Enforcer requires military >= 6
    available = get_advisor_capacity_gate('Managed Democracy', {'military': 6, 'political': 3})
    assert 'enforcer' in available, "Enforcer should unlock at military >= 6"
    assert 'fixer' in available, "Fixer should still be available at political >= 3"
    print("  PASS: capacity gate — nefarious archetypes gated by military/political axes")


def test_generate_advisor_pool_count():
    """Pool generates the requested number of advisors (up to available)."""
    gs = _fresh_gs()
    pool = generate_advisor_pool(gs, count=4)
    assert len(pool) <= 4, f"Pool should have at most 4 advisors, got {len(pool)}"
    assert len(pool) >= 1, f"Pool should have at least 1 advisor, got {len(pool)}"
    # Each advisor has required fields
    for a in pool:
        assert 'id' in a, "Advisor missing 'id'"
        assert 'archetype' in a, "Advisor missing 'archetype'"
        assert 'name' in a, "Advisor missing 'name'"
        assert 'competence' in a, "Advisor missing 'competence'"
        assert 'loyalty' in a, "Advisor missing 'loyalty'"
    print("  PASS: generate_advisor_pool returns valid pool")


def test_hire_advisor():
    """Hiring moves advisor from pool to active roster."""
    gs = _fresh_gs()
    pool = generate_advisor_pool(gs, count=3)
    gs.advisor_pool = pool
    target_id = pool[0]['id']
    target_name = pool[0]['name']

    success, msg = hire_advisor(gs, target_id)
    assert success, f"Hire should succeed, got: {msg}"
    assert len(gs.advisors) == 1, f"Should have 1 active advisor, got {len(gs.advisors)}"
    assert gs.advisors[0]['id'] == target_id, "Hired advisor should match target"
    assert target_id not in [a['id'] for a in gs.advisor_pool], "Hired advisor should be removed from pool"
    print("  PASS: hire_advisor works correctly")


def test_hire_max_three():
    """Cannot hire more than 3 advisors."""
    gs = _fresh_gs()
    # Directly set 3 active advisors
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Test 1', 'loyalty': 70, 'competence': 70},
        {'id': 'a2', 'archetype': 'general', 'name': 'Test 2', 'loyalty': 70, 'competence': 70},
        {'id': 'a3', 'archetype': 'diplomat', 'name': 'Test 3', 'loyalty': 70, 'competence': 70},
    ]
    gs.advisor_pool = [
        {'id': 'a4', 'archetype': 'spy_chief', 'name': 'Test 4', 'loyalty': 70, 'competence': 70},
    ]

    success, msg = hire_advisor(gs, 'a4')
    assert not success, "Hire should fail with 3 active advisors"
    assert "Maximum" in msg or "3" in msg, f"Error message should mention limit: {msg}"
    print("  PASS: hire_advisor enforces max 3 limit")


def test_dismiss_advisor():
    """Dismissing removes advisor from active roster."""
    gs = _fresh_gs()
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Viktor Volkov', 'label': 'Technocrat', 'loyalty': 70, 'competence': 70},
    ]

    success, msg = dismiss_advisor(gs, 'a1')
    assert success, f"Dismiss should succeed, got: {msg}"
    assert len(gs.advisors) == 0, "Should have 0 active advisors after dismiss"
    print("  PASS: dismiss_advisor works correctly")


def test_eliminate_advisor():
    """Eliminating permanently removes advisor (cannot be rehired)."""
    gs = _fresh_gs()
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Viktor Volkov', 'label': 'Technocrat', 'loyalty': 70, 'competence': 70},
    ]

    success, msg = eliminate_advisor(gs, 'a1')
    assert success, f"Eliminate should succeed, got: {msg}"
    assert len(gs.advisors) == 0, "Should have 0 active advisors after eliminate"
    assert 'a1' in gs.advisors_eliminated, "Eliminated ID should be in blacklist"
    assert "permanent" in msg.lower(), f"Message should indicate permanence: {msg}"
    print("  PASS: eliminate_advisor works correctly and records elimination")


def test_stat_distortion_no_bias():
    """Advisors without bias_stat produce no distortion."""
    gs = _fresh_gs()
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Test', 'loyalty': 100, 'competence': 90,
         'bias_stat': None, 'bias_direction': 0},
    ]
    distortions = apply_stat_distortion(gs)
    assert len(distortions) == 0, f"No distortions expected for bias-free advisor, got {distortions}"
    print("  PASS: apply_stat_distortion — no distortion without bias")


def test_stat_distortion_with_bias():
    """Advisors with bias_stat AND low loyalty can produce distortions."""
    random.seed(42)
    gs = _fresh_gs()
    # Set loyalty to 0 so distortion always fires, with strong bias
    gs.advisors = [
        {'id': 'a1', 'archetype': 'propagandist', 'name': 'Test', 'loyalty': 0, 'competence': 30,
         'bias_stat': 'public_approval', 'bias_direction': 10},
    ]

    # Run multiple times to ensure distortion fires at least once
    fired = False
    for _ in range(20):
        d = apply_stat_distortion(gs)
        if 'public_approval' in d:
            fired = True
            break

    assert fired, "Expected distortion to fire at least once with loyalty=0"
    print("  PASS: apply_stat_distortion — distortion fires with low loyalty + bias")


def test_loyalty_check_no_betrayal_high_loyalty():
    """Advisors with high loyalty (>=50) never betray."""
    random.seed(42)
    gs = _fresh_gs()
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Test', 'loyalty': 80,
         'competence': 70, 'specialty': 'economic'},
    ]
    gs.advisor_actions_log = []

    # Run 50 times — none should betray
    for _ in range(50):
        msgs = check_advisor_loyalty(gs)
        assert len(msgs) == 0, f"High-loyalty advisor should not betray, got: {msgs}"

    print("  PASS: check_advisor_loyalty — high loyalty prevents betrayal")


def test_loyalty_check_betrayal_can_fire():
    """Advisors with very low loyalty will eventually betray."""
    gs = _fresh_gs()
    gs.advisor_actions_log = []
    gs.advisors = [
        {'id': 'a1', 'archetype': 'oligarch', 'name': 'Greedy Guy', 'loyalty': 5,
         'competence': 50, 'specialty': 'economic'},
    ]

    betrayals = 0
    for _ in range(100):
        msgs = check_advisor_loyalty(gs)
        if msgs:
            betrayals += 1
            # Reset budget so repeated betrayals don't drain it fully
            gs.budget = 50.0

    assert betrayals > 0, "Loyalty=5 advisor should betray at least once in 100 turns"
    print(f"  PASS: check_advisor_loyalty — low loyalty betrayal fired {betrayals}/100 times")


def test_pool_excludes_active_archetypes():
    """Pool generation should not offer archetypes already in the active roster."""
    gs = _fresh_gs()
    gs.advisors = [
        {'id': 'a1', 'archetype': 'technocrat', 'name': 'Test', 'loyalty': 70, 'competence': 70},
    ]

    pool = generate_advisor_pool(gs, count=10)
    pool_archetypes = {a['archetype'] for a in pool}
    assert 'technocrat' not in pool_archetypes, "Pool should not offer archetype already active"
    print("  PASS: generate_advisor_pool excludes active archetypes")


if __name__ == '__main__':
    print("\n=== test_advisors.py ===\n")
    test_capacity_gate_managed_democracy()
    test_capacity_gate_kleptocracy()
    test_capacity_gate_nefarious_with_axes()
    test_generate_advisor_pool_count()
    test_hire_advisor()
    test_hire_max_three()
    test_dismiss_advisor()
    test_eliminate_advisor()
    test_stat_distortion_no_bias()
    test_stat_distortion_with_bias()
    test_loyalty_check_no_betrayal_high_loyalty()
    test_loyalty_check_betrayal_can_fire()
    test_pool_excludes_active_archetypes()
    print("\nAll test_advisors tests passed!")
