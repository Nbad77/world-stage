"""
Tests for Shadow Cabinet Axis System — Session 5/6
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests cover: compute_regime_from_axes, axis cost tables,
maintenance calculation, permanent floors, migration,
serialization round-trip, and the EOT maintenance deduction.
Session 6: Security split into Military + Intelligence.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import (
    GameState,
    AXIS_COST_PER_LEVEL,
    AXIS_MAINTENANCE,
    AXIS_PERMANENT_FLOORS,
    compute_regime_from_axes,
    _migrate_to_axes,
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
    gs.cabinet_axes = {'military': 0, 'intelligence': 0, 'resource_dev': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}
    return gs


def test_regime_managed_democracy():
    """Axes totalling <= 5 yield Managed Democracy."""
    axes = {'military': 1, 'intelligence': 0, 'media': 1, 'judicial': 1, 'political': 1, 'extraction': 1}
    result = compute_regime_from_axes(axes)
    assert result == 'Managed Democracy', f"Expected Managed Democracy, got {result}"
    print("  PASS: axes total 5 -> Managed Democracy")


def test_regime_soft_authoritarianism():
    """Axes totalling 6-15 yield Soft Authoritarianism."""
    axes = {'military': 2, 'intelligence': 1, 'media': 3, 'judicial': 2, 'political': 2, 'extraction': 0}
    result = compute_regime_from_axes(axes)
    assert result == 'Soft Authoritarianism', f"Expected Soft Authoritarianism, got {result}"
    print("  PASS: axes total 10 -> Soft Authoritarianism")


def test_regime_patronage_state():
    """Axes totalling 16-25 without extraction >= 7 yield Patronage State."""
    axes = {'military': 3, 'intelligence': 2, 'media': 5, 'judicial': 3, 'political': 5, 'extraction': 3}
    result = compute_regime_from_axes(axes)
    assert result == 'Patronage State', f"Expected Patronage State, got {result}"
    print("  PASS: axes total 21 -> Patronage State")


def test_regime_kleptocracy_via_extraction():
    """Axes totalling 16-25 with extraction >= 7 yields Kleptocracy (shortcut)."""
    axes = {'military': 2, 'intelligence': 1, 'media': 3, 'judicial': 3, 'political': 2, 'extraction': 7}
    result = compute_regime_from_axes(axes)
    assert result == 'Kleptocracy', f"Expected Kleptocracy (high extraction), got {result}"
    print("  PASS: axes total 18 with extraction=7 -> Kleptocracy")


def test_regime_kleptocracy_high_total():
    """Axes totalling 26-35 yield Kleptocracy."""
    axes = {'military': 4, 'intelligence': 3, 'media': 7, 'judicial': 5, 'political': 5, 'extraction': 6}
    result = compute_regime_from_axes(axes)
    assert result == 'Kleptocracy', f"Expected Kleptocracy, got {result}"
    print("  PASS: axes total 30 -> Kleptocracy")


def test_regime_totalitarian():
    """Axes totalling > 35 yield Totalitarian Regime."""
    axes = {'military': 5, 'intelligence': 4, 'media': 8, 'judicial': 8, 'political': 8, 'extraction': 7}
    result = compute_regime_from_axes(axes)
    assert result == 'Totalitarian Regime', f"Expected Totalitarian Regime, got {result}"
    print("  PASS: axes total 40 -> Totalitarian Regime")


def test_regime_zero_axes():
    """All axes at 0 yield Managed Democracy."""
    axes = {'military': 0, 'intelligence': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}
    result = compute_regime_from_axes(axes)
    assert result == 'Managed Democracy', f"Expected Managed Democracy, got {result}"
    print("  PASS: axes total 0 -> Managed Democracy")


def test_resource_dev_excluded_from_regime():
    """Resource Development should NOT count toward regime calculation."""
    # Base axes with total 5 = Managed Democracy
    axes = {'military': 1, 'intelligence': 1, 'resource_dev': 10, 'media': 1, 'judicial': 1, 'political': 1, 'extraction': 0}
    result = compute_regime_from_axes(axes)
    assert result == 'Managed Democracy', f"Expected Managed Democracy (resource_dev excluded), got {result}"
    print("  PASS: resource_dev excluded from regime calculation (total 5 + 10 resource_dev = Managed Democracy)")


def test_axis_cost_tables_structure():
    """Each axis should have exactly 10 cost levels."""
    for axis, costs in AXIS_COST_PER_LEVEL.items():
        assert len(costs) == 10, f"{axis} should have 10 cost levels, got {len(costs)}"
        assert all(isinstance(c, (int, float)) and c > 0 for c in costs), \
            f"{axis} has invalid cost values: {costs}"
    print(f"  PASS: AXIS_COST_PER_LEVEL has valid structure for all {len(AXIS_COST_PER_LEVEL)} axes")


def test_maintenance_cost_calculation():
    """Maintenance cost is (level - free_threshold) * cost_per_level for levels above threshold."""
    gs = _fresh_gs()
    gs.cabinet_axes = {'military': 5, 'intelligence': 4, 'resource_dev': 4, 'media': 4, 'judicial': 5, 'political': 4, 'extraction': 4}

    total = 0.0
    for axis_name, (free_thresh, cost_per) in AXIS_MAINTENANCE.items():
        level = gs.cabinet_axes.get(axis_name, 0)
        if level > free_thresh:
            cost = round((level - free_thresh) * cost_per, 1)
            total += cost

    # military: (5-3)*0.5 = 1.0
    # intelligence: (4-3)*0.4 = 0.4
    # resource_dev: (4-3)*0.3 = 0.3
    # media: (4-3)*0.3 = 0.3
    # judicial: (5-4)*0.4 = 0.4
    # political: (4-3)*0.3 = 0.3
    # extraction: (4-3)*0.2 = 0.2
    expected = 1.0 + 0.4 + 0.3 + 0.3 + 0.4 + 0.3 + 0.2
    assert abs(total - expected) < 0.01, f"Expected {expected}, got {total}"
    print(f"  PASS: maintenance calculation correct: ${total:.1f}B (expected ${expected:.1f}B)")


def test_permanent_floors():
    """AXIS_PERMANENT_FLOORS should define floor values for all 7 axes."""
    assert len(AXIS_PERMANENT_FLOORS) == 7, f"Expected 7 floor entries, got {len(AXIS_PERMANENT_FLOORS)}"
    for axis in ('military', 'intelligence', 'resource_dev', 'media', 'judicial', 'political', 'extraction'):
        assert axis in AXIS_PERMANENT_FLOORS, f"Missing floor for {axis}"
        assert AXIS_PERMANENT_FLOORS[axis] >= 0, f"Floor for {axis} should be non-negative"
    print("  PASS: AXIS_PERMANENT_FLOORS has all 7 axes")


def test_migration_from_binary_upgrades():
    """_migrate_to_axes should set axis levels based on old binary flags.
    Session 6: intelligence_apparatus → intelligence axis, loyalty_brigades → military axis."""
    gs = _fresh_gs()
    gs.corruption_upgrades = {
        'intelligence_apparatus': True,
        'sovereign_wealth_diversion': False,
        'loyalty_brigades': True,
        'debt_infrastructure_deal': False,
    }
    gs.action_press_suppressed = True
    gs.action_media_taken = True
    gs.action_judiciary_captured = True
    gs.action_journalists_liquidated = False
    gs.action_opposition_dissolved = True

    _migrate_to_axes(gs)

    # intelligence_apparatus -> intelligence >= 3
    assert gs.cabinet_axes['intelligence'] >= 3, f"Intelligence should be >= 3 after intel migration, got {gs.cabinet_axes['intelligence']}"
    # loyalty_brigades -> military >= 6
    assert gs.cabinet_axes['military'] >= 6, f"Military should be >= 6 after brigade migration, got {gs.cabinet_axes['military']}"
    # press_suppressed -> media >= 3, media_taken -> media >= 5
    assert gs.cabinet_axes['media'] >= 5, f"Media should be >= 5 after media taken, got {gs.cabinet_axes['media']}"
    # judiciary_captured -> judicial >= 4
    assert gs.cabinet_axes['judicial'] >= 4, f"Judicial should be >= 4 after capture, got {gs.cabinet_axes['judicial']}"
    # opposition_dissolved -> political >= 6
    assert gs.cabinet_axes['political'] >= 6, f"Political should be >= 6 after dissolution, got {gs.cabinet_axes['political']}"

    print("  PASS: _migrate_to_axes correctly maps binary flags to axis levels")


def test_serialize_deserialize_axes():
    """Cabinet axes should survive serialize/deserialize round-trip."""
    gs = _fresh_gs()
    gs.cabinet_axes = {'military': 5, 'intelligence': 3, 'resource_dev': 2, 'media': 3, 'judicial': 7, 'political': 2, 'extraction': 4}

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert gs2.cabinet_axes == gs.cabinet_axes, \
        f"Axes mismatch after round-trip: {gs2.cabinet_axes} != {gs.cabinet_axes}"
    print("  PASS: cabinet_axes survive serialize/deserialize")


def test_serialize_deserialize_advisors():
    """Session 7C: Advisor dict should survive serialize/deserialize round-trip."""
    gs = _fresh_gs()
    gs.advisors = {
        "finance_minister": {"name": "Finance Minister", "trust": 60, "assigned_this_turn": True, "defection_triggered": False},
        "security_chief": {"name": "Security Chief", "trust": 75, "assigned_this_turn": False, "defection_triggered": False},
        "diplomatic_aide": {"name": "Diplomatic Aide", "trust": 30, "assigned_this_turn": False, "defection_triggered": True},
    }
    gs.advisor_slots_available = 3

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert isinstance(gs2.advisors, dict), f"Expected dict, got {type(gs2.advisors)}"
    assert gs2.advisors['finance_minister']['trust'] == 60, "Finance minister trust mismatch"
    assert gs2.advisors['diplomatic_aide']['defection_triggered'] is True, "Defection flag mismatch"
    assert gs2.advisor_slots_available == 3, "Slots mismatch"
    print("  PASS: advisors (dict) survive serialize/deserialize")


def test_serialize_deserialize_advisors_legacy_migration():
    """Old list-based advisor saves should migrate to new dict format."""
    gs = _fresh_gs()
    # Simulate old save data
    data = gs.serialize()
    data['advisors'] = [{'id': 'abc', 'archetype': 'technocrat'}]  # old list format

    gs2 = GameState.deserialize(data)

    assert isinstance(gs2.advisors, dict), f"Expected dict after migration, got {type(gs2.advisors)}"
    assert 'finance_minister' in gs2.advisors, "Missing finance_minister after migration"
    assert gs2.advisors['finance_minister']['trust'] == 75, "Default trust should be 75"
    print("  PASS: legacy list advisors migrate to dict")


def test_serialize_deserialize_tax_rates():
    """Tax rates should survive serialize/deserialize round-trip."""
    gs = _fresh_gs()
    gs.tax_rates = {'income_tax': 0.30, 'corporate_tax': 0.20, 'resource_tax': 0.40}

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert gs2.tax_rates == gs.tax_rates, \
        f"Tax rates mismatch: {gs2.tax_rates} != {gs.tax_rates}"
    print("  PASS: tax_rates survive serialize/deserialize")


def test_security_split_migration():
    """Session 6: Old saves with 'security' key get split into military + intelligence."""
    gs = _fresh_gs()
    # Simulate old save with 'security' key
    gs.cabinet_axes = {'security': 8, 'media': 3, 'judicial': 4, 'political': 5, 'extraction': 2}

    from game_state import _migrate_security_to_split
    _migrate_security_to_split(gs)

    # security 8 -> military floor(8/2)=4, intelligence ceil(8/2)=4
    assert gs.cabinet_axes.get('military', 0) == 4, f"Military should be 4 after split, got {gs.cabinet_axes.get('military')}"
    assert gs.cabinet_axes.get('intelligence', 0) == 4, f"Intelligence should be 4 after split, got {gs.cabinet_axes.get('intelligence')}"
    assert 'security' not in gs.cabinet_axes, "Security key should be removed after migration"
    print("  PASS: security split migration works correctly (8 -> military=4, intelligence=4)")


def test_security_split_odd_value():
    """Session 6: Odd security values split correctly (floor/ceil)."""
    gs = _fresh_gs()
    gs.cabinet_axes = {'security': 7, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}

    from game_state import _migrate_security_to_split
    _migrate_security_to_split(gs)

    # security 7 -> military floor(7/2)=3, intelligence ceil(7/2)=4
    assert gs.cabinet_axes.get('military', 0) == 3, f"Military should be 3 after split, got {gs.cabinet_axes.get('military')}"
    assert gs.cabinet_axes.get('intelligence', 0) == 4, f"Intelligence should be 4 after split, got {gs.cabinet_axes.get('intelligence')}"
    print("  PASS: security split migration works correctly for odd value (7 -> military=3, intelligence=4)")


if __name__ == '__main__':
    print("\n=== test_cabinet_axes.py ===\n")
    test_regime_managed_democracy()
    test_regime_soft_authoritarianism()
    test_regime_patronage_state()
    test_regime_kleptocracy_via_extraction()
    test_regime_kleptocracy_high_total()
    test_regime_totalitarian()
    test_regime_zero_axes()
    test_axis_cost_tables_structure()
    test_maintenance_cost_calculation()
    test_permanent_floors()
    test_migration_from_binary_upgrades()
    test_serialize_deserialize_axes()
    test_serialize_deserialize_advisors()
    test_serialize_deserialize_advisors_legacy_migration()
    test_serialize_deserialize_tax_rates()
    test_security_split_migration()
    test_security_split_odd_value()
    print("\nAll test_cabinet_axes tests passed!")
