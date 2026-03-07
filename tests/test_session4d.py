"""
Session 4D -- Tech Level, Intel Budget, Alternate Endings tests.

12 tests covering:
1.  Tech tier effects lookup (all 5 tiers)
2.  apply_tech_gain: EU partnership +5
3.  apply_tech_gain: USA transfer +8, tier transition reporting
4.  Tech GDP bonus in EOT
5.  EU ceiling from tech allows relations above 100
6.  Intel budget allocation deducts from national budget
7.  Intel apparatus degradation after 2 unfunded turns
8.  Alternate ending: martyrdom (any turn, stability 0, approval 70+)
9.  Alternate ending: retirement (turn 10, stability 60+, approval 50+, wealth 20+)
10. Alternate ending: democratic (turn 10, EU 80+, approval 65+, no domestic actions)
11. Alternate ending: capture (any turn, wealth 50+, all 5 domestic actions)
12. Alternate ending priority: martyrdom > capture
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import (
    get_tech_tier_effects,
    apply_tech_gain,
    TECH_TIER_EFFECTS,
    TECH_SOURCES,
    process_intel_budget,
    INTEL_BUDGET_OPTIONS,
    check_alternate_endings,
    ALTERNATE_ENDING_CONDITIONS,
    apply_end_of_turn_effects,
)


def _fresh_gs(**overrides):
    """Create a fresh GameState with sensible defaults for testing."""
    gs = GameState()
    gs.personal_wealth = overrides.get('pw', 20.0)
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = overrides.get('stability', 50)
    gs.public_approval = overrides.get('approval', 50)
    gs.budget = overrides.get('budget', 50.0)
    gs.oil_price = 50
    gs.current_turn = overrides.get('turn', 3)
    gs.tech_level = overrides.get('tech_level', 0)
    gs.tech_sources = []
    gs.intel_budget = 0.0
    gs.intel_budget_allocation = 'maintenance'
    gs.intel_turns_unfunded = 0
    gs.ending_triggered = None
    gs.turns_no_suppression = 0
    return gs


# ── Tech Level Tests ─────────────────────────────────────────────────────────

def test_tech_tier_effects_all_tiers():
    """All 5 tech tiers return correct eu_ceiling, gdp_bonus, intel_tier_bonus."""
    cases = [
        (0,   100, 0.00, 0),
        (10,  100, 0.00, 0),
        (20,  100, 0.00, 0),
        (21,  110, 0.05, 0),
        (40,  110, 0.05, 0),
        (41,  120, 0.10, 1),
        (60,  120, 0.10, 1),
        (61,  130, 0.15, 1),
        (80,  130, 0.15, 1),
        (81,  140, 0.20, 2),
        (100, 140, 0.20, 2),
    ]
    for tech, exp_ceil, exp_gdp, exp_intel in cases:
        e = get_tech_tier_effects(tech)
        assert e['eu_ceiling'] == exp_ceil, f"Tech {tech}: ceiling {e['eu_ceiling']} != {exp_ceil}"
        assert e['gdp_bonus'] == exp_gdp, f"Tech {tech}: gdp {e['gdp_bonus']} != {exp_gdp}"
        assert e['intel_tier_bonus'] == exp_intel, f"Tech {tech}: intel {e['intel_tier_bonus']} != {exp_intel}"

    print("  PASSED: All 5 tech tiers verified.")


def test_apply_tech_gain_eu_partnership():
    """EU partnership grants +5 tech."""
    gs = _fresh_gs()
    ok, changes = apply_tech_gain(gs, 'eu_partnership')

    assert ok is True
    assert gs.tech_level == 5, f"Tech should be 5, got {gs.tech_level}"
    assert len(gs.tech_sources) == 1
    assert gs.tech_sources[0]['source'] == 'eu_partnership'
    assert gs.tech_sources[0]['gain'] == 5

    print("  PASSED: EU partnership +5 tech.")


def test_apply_tech_gain_tier_transition():
    """USA transfer at tech 18 pushes to 26 (tier 2), reports tier transition."""
    gs = _fresh_gs(tech_level=18)
    ok, changes = apply_tech_gain(gs, 'usa_transfer')

    assert ok is True
    assert gs.tech_level == 26, f"Tech should be 26, got {gs.tech_level}"
    # Should report EU ceiling change (100 -> 110)
    ceiling_msgs = [c for c in changes if 'ceiling' in c.lower()]
    assert len(ceiling_msgs) > 0, f"Should report EU ceiling change, got: {changes}"

    print("  PASSED: USA transfer tier transition reported.")


def test_tech_gdp_bonus_in_eot():
    """Tech level 50 (tier 3, +10% GDP) increases GDP revenue in EOT."""
    gs_no_tech = _fresh_gs(approval=60, stability=50)
    gs_with_tech = _fresh_gs(approval=60, stability=50, tech_level=50)

    budget_before_no = gs_no_tech.budget
    budget_before_yes = gs_with_tech.budget

    apply_end_of_turn_effects(gs_no_tech)
    apply_end_of_turn_effects(gs_with_tech)

    gdp_no = gs_no_tech.budget - budget_before_no
    gdp_yes = gs_with_tech.budget - budget_before_yes

    # With tech bonus, GDP should be higher (though exact amount depends on other EOT effects)
    # Just verify tech GDP is at least slightly more
    assert gdp_yes > gdp_no, (
        f"Tech GDP ({gdp_yes:.1f}) should exceed no-tech GDP ({gdp_no:.1f})"
    )

    print(f"  PASSED: Tech GDP bonus — no-tech: +{gdp_no:.1f}B, tech-50: +{gdp_yes:.1f}B")


def test_eu_ceiling_from_tech():
    """Tech level 50 (EU ceiling 120) allows EU relations above 100."""
    gs = _fresh_gs(tech_level=50)
    gs.relations['eu'] = 98

    # With ceiling 120, EU should be able to go above 100
    gs.update_relations('eu', 30, flat=True)
    assert gs.relations['eu'] > 100, f"EU should exceed 100, got {gs.relations['eu']}"
    assert gs.relations['eu'] <= 120, f"EU should not exceed 120, got {gs.relations['eu']}"

    # Non-EU should still cap at 100
    gs.relations['usa'] = 98
    gs.update_relations('usa', 30, flat=True)
    assert gs.relations['usa'] == 100, f"USA should cap at 100, got {gs.relations['usa']}"

    print(f"  PASSED: EU ceiling from tech — EU at {gs.relations['eu']}, USA capped at 100.")


# ── Intel Budget Tests ───────────────────────────────────────────────────────

def test_intel_budget_deducts_from_national():
    """Active allocation costs $1B from national budget."""
    gs = _fresh_gs(budget=20.0)
    ok, changes = process_intel_budget(gs, 'active')

    assert ok is True
    assert gs.budget == 19.0, f"Budget should be 19.0, got {gs.budget}"
    assert gs.intel_budget_allocation == 'active'
    assert gs.intel_turns_unfunded == 0

    print("  PASSED: Intel budget deducts from national budget.")


def test_intel_apparatus_degradation():
    """2 consecutive 'none' turns degrades apparatus tier by 1."""
    gs = _fresh_gs(budget=20.0)
    gs.intel_apparatus_tier = 2

    # First unfunded turn
    process_intel_budget(gs, 'none')
    assert gs.intel_turns_unfunded == 1
    assert gs.intel_apparatus_tier == 2, "Should not degrade after 1 turn"

    # Second unfunded turn — should degrade
    process_intel_budget(gs, 'none')
    assert gs.intel_apparatus_tier == 1, f"Should degrade to 1, got {gs.intel_apparatus_tier}"
    # Counter resets after degradation
    assert gs.intel_turns_unfunded == 0, "Counter should reset after degradation"

    print("  PASSED: Intel apparatus degrades after 2 unfunded turns.")


# ── Alternate Ending Tests ───────────────────────────────────────────────────

def test_ending_martyrdom():
    """Martyrdom fires at any turn when martyrdom_triggered flag is set (pre-drift check)."""
    gs = _fresh_gs(stability=0, approval=75, turn=5)
    gs.martyrdom_triggered = True  # fixes_17 Fix K: flag set pre-drift in EOT
    result = check_alternate_endings(gs)

    assert result == 'martyrdom', f"Expected martyrdom, got {result}"
    assert gs.ending_triggered == 'martyrdom'

    print("  PASSED: Martyrdom ending triggered.")


def test_ending_retirement():
    """Retirement fires at turn 10 with stability 60+, approval 50+, wealth 20+."""
    gs = _fresh_gs(stability=65, approval=55, pw=25.0, turn=10)
    result = check_alternate_endings(gs)

    assert result == 'retirement', f"Expected retirement, got {result}"
    assert gs.ending_triggered == 'retirement'

    # Should NOT fire before turn 10
    gs2 = _fresh_gs(stability=65, approval=55, pw=25.0, turn=8)
    result2 = check_alternate_endings(gs2)
    assert result2 is None, f"Should not fire at turn 8, got {result2}"

    print("  PASSED: Retirement ending at turn 10 only.")


def test_ending_democratic():
    """Democratic transition: turn 10, EU 80+, approval 65+, no press suppression."""
    gs = _fresh_gs(approval=70, turn=10)
    gs.relations['eu'] = 85

    result = check_alternate_endings(gs)
    assert result == 'democratic', f"Expected democratic, got {result}"

    # Should NOT fire if press suppressed
    gs2 = _fresh_gs(approval=70, turn=10)
    gs2.relations['eu'] = 85
    gs2.action_press_suppressed = True

    result2 = check_alternate_endings(gs2)
    assert result2 != 'democratic', f"Should not fire with press suppressed, got {result2}"

    print("  PASSED: Democratic ending — no press suppression required.")


def test_ending_capture():
    """State capture: turn 10, wealth 50+, capture triad (constitutional revision + press suppressed + judiciary captured)."""
    gs = _fresh_gs(pw=55.0, turn=10)
    gs.constitutional_revision_active = True
    gs.action_press_suppressed = True
    gs.action_judiciary_captured = True

    result = check_alternate_endings(gs)
    assert result == 'capture', f"Expected capture, got {result}"

    # Should NOT fire before turn 10
    gs_early = _fresh_gs(pw=55.0, turn=7)
    gs_early.constitutional_revision_active = True
    gs_early.action_press_suppressed = True
    gs_early.action_judiciary_captured = True

    result_early = check_alternate_endings(gs_early)
    assert result_early is None, f"Should not fire before turn 10, got {result_early}"

    # Should NOT fire if missing one triad element
    gs2 = _fresh_gs(pw=55.0, turn=10)
    gs2.constitutional_revision_active = True
    gs2.action_press_suppressed = True
    gs2.action_judiciary_captured = False  # missing

    result2 = check_alternate_endings(gs2)
    assert result2 != 'capture', f"Should not fire with missing triad element, got {result2}"

    print("  PASSED: State capture ending — capture triad at turn 10 required.")


def test_ending_priority_capture_over_martyrdom():
    """Capture (priority 2) takes precedence over martyrdom (priority 1) at turn 10."""
    gs = _fresh_gs(stability=0, approval=75, pw=55.0, turn=10)
    gs.constitutional_revision_active = True
    gs.action_judiciary_captured = True
    gs.action_press_suppressed = True
    gs.martyrdom_triggered = True  # fixes_17 Fix K

    result = check_alternate_endings(gs)
    assert result == 'capture', f"Capture should beat martyrdom at turn 10, got {result}"

    # Before turn 10, only martyrdom can fire (capture is turn-10-only)
    gs2 = _fresh_gs(stability=0, approval=75, pw=55.0, turn=5)
    gs2.constitutional_revision_active = True
    gs2.action_judiciary_captured = True
    gs2.action_press_suppressed = True
    gs2.martyrdom_triggered = True  # fixes_17 Fix K

    result2 = check_alternate_endings(gs2)
    assert result2 == 'martyrdom', f"Before turn 10, martyrdom should fire, got {result2}"

    print("  PASSED: Capture beats martyrdom at turn 10; martyrdom fires before turn 10.")


if __name__ == '__main__':
    tests = [
        ("test_tech_tier_effects_all_tiers", test_tech_tier_effects_all_tiers),
        ("test_apply_tech_gain_eu_partnership", test_apply_tech_gain_eu_partnership),
        ("test_apply_tech_gain_tier_transition", test_apply_tech_gain_tier_transition),
        ("test_tech_gdp_bonus_in_eot", test_tech_gdp_bonus_in_eot),
        ("test_eu_ceiling_from_tech", test_eu_ceiling_from_tech),
        ("test_intel_budget_deducts_from_national", test_intel_budget_deducts_from_national),
        ("test_intel_apparatus_degradation", test_intel_apparatus_degradation),
        ("test_ending_martyrdom", test_ending_martyrdom),
        ("test_ending_retirement", test_ending_retirement),
        ("test_ending_democratic", test_ending_democratic),
        ("test_ending_capture", test_ending_capture),
        ("test_ending_priority_capture_over_martyrdom", test_ending_priority_capture_over_martyrdom),
    ]

    for name, fn in tests:
        print(f"\n=== {name} ===")
        fn()

    print(f"\n=== ALL {len(tests)} SESSION 4D TESTS PASSED ===")
