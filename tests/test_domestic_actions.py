"""
Session 4C — Domestic Actions tests.

10 tests covering:
1. State media takeover — cost, flag, approval floor, relations
2. Judicial capture — scandal immunity
3. Suppress press — stability, DPRG bonus
4. Dissolve opposition — coup immunity, regime hard right
5. Liquidate journalists — approval ceiling, scandal immunity
6. Duplicate purchase blocked
7. Insufficient funds blocked
8. Marsha red line triggers at EU 70+
9. Press suppression passive EU drain in EOT
10. Scandal immunity blocks scandal roll
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import (
    DOMESTIC_ACTION_CONSEQUENCES,
    apply_domestic_action,
    apply_end_of_turn_effects,
    roll_detection,
)


def _fresh_gs(pw=20.0):
    """Create a fresh GameState with enough personal wealth for testing."""
    gs = GameState()
    gs.personal_wealth = pw
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 50
    gs.public_approval = 50
    gs.budget = 50.0
    gs.oil_price = 50
    gs.current_turn = 3
    return gs


def test_state_media_takeover():
    """State media takeover costs $5B, sets floor, hits EU/USA."""
    gs = _fresh_gs()
    ok, changes = apply_domestic_action(gs, 'state_media_takeover')

    assert ok is True, f"Should succeed, got {ok}: {changes}"
    assert gs.action_media_taken is True
    assert gs.personal_wealth == 15.0, f"PW should be 15.0, got {gs.personal_wealth}"
    assert gs.approval_floor == 15, f"Approval floor should be 15, got {gs.approval_floor}"
    assert gs.relations['eu'] < 50, f"EU should decrease, got {gs.relations['eu']}"
    assert gs.relations['usa'] < 50, f"USA should decrease, got {gs.relations['usa']}"

    # Verify approval floor enforcement
    gs.public_approval = 50
    gs.update_approval(-60)  # Would go to -10 without floor
    assert gs.public_approval >= 15, f"Approval should be >= 15 (floor), got {gs.public_approval}"

    print(f"  PASSED: State media takeover — cost, flag, floor, relations verified.")


def test_judicial_capture():
    """Judicial capture grants scandal immunity."""
    gs = _fresh_gs()
    ok, changes = apply_domestic_action(gs, 'judicial_capture')

    assert ok is True
    assert gs.action_judiciary_captured is True
    assert gs.scandal_immune is True, "Should grant scandal immunity"
    assert gs.relations['eu'] < 50, f"EU should decrease, got {gs.relations['eu']}"
    assert gs.personal_wealth == 16.0, f"PW should be 16.0 ($4B cost), got {gs.personal_wealth}"

    print(f"  PASSED: Judicial capture — scandal immunity, cost, relations verified.")


def test_suppress_press():
    """Suppress press gives stability +5, DPRG +3."""
    gs = _fresh_gs()
    old_stab = gs.stability
    old_dprg = gs.relations['dprg']

    ok, changes = apply_domestic_action(gs, 'suppress_press')

    assert ok is True
    assert gs.action_press_suppressed is True
    assert gs.stability > old_stab, f"Stability should increase, was {old_stab} now {gs.stability}"
    assert gs.relations['dprg'] > old_dprg, f"DPRG should increase, was {old_dprg} now {gs.relations['dprg']}"
    assert gs.personal_wealth == 17.0, f"PW should be 17.0 ($3B cost), got {gs.personal_wealth}"

    print(f"  PASSED: Suppress press — stability, DPRG, cost verified.")


def test_dissolve_opposition():
    """Dissolve opposition: coup immunity, stability +10, approval -8, regime hard right."""
    gs = _fresh_gs()
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    old_appr = gs.public_approval

    ok, changes = apply_domestic_action(gs, 'dissolve_opposition')

    assert ok is True
    assert gs.action_opposition_dissolved is True
    assert gs.coup_immune is True, "Should grant coup immunity"
    assert gs.stability > 50, f"Stability should increase, got {gs.stability}"
    assert gs.public_approval < old_appr, f"Approval should decrease, was {old_appr} now {gs.public_approval}"
    # fixes_12 Fix 3: Hard right now shifts axes instead of direct regime_type mutation.
    # Regime label change happens at EOT via compute_regime_from_axes().
    # Verify axes were shifted instead.
    # Session 6: security split into military + intelligence; hard_right shifts military
    assert gs.cabinet_axes.get('military', 0) >= 3, (
        f"Military axis should be >= 3 after hard_right, got {gs.cabinet_axes.get('military', 0)}"
    )
    assert gs.cabinet_axes.get('political', 0) >= 3, (
        f"Political axis should be >= 3 after hard_right, got {gs.cabinet_axes.get('political', 0)}"
    )

    print(f"  PASSED: Dissolve opposition — coup immunity, regime shift, approval hit verified.")


def test_liquidate_journalists():
    """Liquidate journalists: approval ceiling -10, scandal immunity, relations hit."""
    gs = _fresh_gs()
    ok, changes = apply_domestic_action(gs, 'liquidate_journalists')

    assert ok is True
    assert gs.action_journalists_liquidated is True
    assert gs.scandal_immune is True
    assert gs.approval_ceiling == 90, f"Approval ceiling should be 90 (100-10), got {gs.approval_ceiling}"
    assert gs.relations['eu'] < 50, f"EU should decrease, got {gs.relations['eu']}"
    assert gs.relations['usa'] < 50, f"USA should decrease, got {gs.relations['usa']}"
    assert gs.personal_wealth == 12.0, f"PW should be 12.0 ($8B cost), got {gs.personal_wealth}"

    print(f"  PASSED: Liquidate journalists — ceiling, immunity, cost verified.")


def test_duplicate_purchase_blocked():
    """Cannot purchase the same domestic action twice."""
    gs = _fresh_gs()
    ok1, _ = apply_domestic_action(gs, 'state_media_takeover')
    assert ok1 is True

    ok2, changes2 = apply_domestic_action(gs, 'state_media_takeover')
    assert ok2 is False, f"Duplicate should fail, got {ok2}"
    assert 'Already purchased' in changes2[0], f"Should say already purchased, got {changes2}"

    print(f"  PASSED: Duplicate purchase blocked.")


def test_insufficient_funds_blocked():
    """Cannot purchase if personal wealth is too low."""
    gs = _fresh_gs(pw=2.0)

    ok, changes = apply_domestic_action(gs, 'state_media_takeover')
    assert ok is False, f"Should fail with insufficient funds, got {ok}"
    assert 'Cannot afford' in changes[0], f"Should say cannot afford, got {changes}"

    print(f"  PASSED: Insufficient funds blocked.")


def test_marsha_red_line():
    """Liquidating journalists while EU >= 70 triggers Marsha red line."""
    gs = _fresh_gs()
    gs.relations['eu'] = 75  # Above 70 threshold

    ok, changes = apply_domestic_action(gs, 'liquidate_journalists')
    assert ok is True
    assert gs.marsha_red_line_triggered is True, "Marsha red line should trigger"

    # Verify the change message mentions red line
    red_line_msgs = [c for c in changes if 'RED LINE' in c]
    assert len(red_line_msgs) > 0, f"Should have red line message, got: {changes}"

    print(f"  PASSED: Marsha red line triggers at EU 70+.")


def test_no_marsha_red_line_below_threshold():
    """Liquidating journalists while EU < 70 does NOT trigger red line."""
    gs = _fresh_gs()
    gs.relations['eu'] = 50  # Below 70

    ok, changes = apply_domestic_action(gs, 'liquidate_journalists')
    assert ok is True
    assert gs.marsha_red_line_triggered is False, "Should NOT trigger red line below EU 70"

    print(f"  PASSED: No Marsha red line below EU 70.")


def test_press_suppression_eu_drain():
    """Press suppression causes EU -3/turn during EOT."""
    gs = _fresh_gs()
    gs.action_press_suppressed = True
    old_eu = gs.relations['eu']

    messages = apply_end_of_turn_effects(gs)

    assert gs.relations['eu'] < old_eu, (
        f"EU should drain from press suppression, was {old_eu} now {gs.relations['eu']}"
    )
    press_msgs = [m for m in messages if 'Press suppression' in m or 'press suppression' in m.lower()]
    assert len(press_msgs) > 0, f"Should have press suppression message, got: {messages[:5]}"

    print(f"  PASSED: Press suppression EU drain in EOT.")


def test_scandal_immunity_blocks_roll():
    """When scandal_immune is True, roll_detection returns without scandal."""
    gs = _fresh_gs()
    gs.scandal_immune = True
    gs.detection_heat = 95  # Very high — would normally trigger scandal

    messages = roll_detection(gs)

    # Should not have any scandal TRIGGER messages (the actual scandal penalty text)
    scandal_trigger_msgs = [m for m in messages if 'SCANDAL DETECTED' in m.upper() or 'scandal has erupted' in m.lower()]
    # The only message should be the immunity message
    immunity_msgs = [m for m in messages if 'Judiciary captured' in m or 'investigations suspended' in m]
    assert len(immunity_msgs) > 0, f"Should have immunity message, got: {messages}"
    assert len(scandal_trigger_msgs) == 0, f"Should NOT have scandal trigger, got: {scandal_trigger_msgs}"

    print(f"  PASSED: Scandal immunity blocks detection roll.")


if __name__ == '__main__':
    print("\n=== test_state_media_takeover ===")
    test_state_media_takeover()

    print("\n=== test_judicial_capture ===")
    test_judicial_capture()

    print("\n=== test_suppress_press ===")
    test_suppress_press()

    print("\n=== test_dissolve_opposition ===")
    test_dissolve_opposition()

    print("\n=== test_liquidate_journalists ===")
    test_liquidate_journalists()

    print("\n=== test_duplicate_purchase_blocked ===")
    test_duplicate_purchase_blocked()

    print("\n=== test_insufficient_funds_blocked ===")
    test_insufficient_funds_blocked()

    print("\n=== test_marsha_red_line ===")
    test_marsha_red_line()

    print("\n=== test_no_marsha_red_line_below_threshold ===")
    test_no_marsha_red_line_below_threshold()

    print("\n=== test_press_suppression_eu_drain ===")
    test_press_suppression_eu_drain()

    print("\n=== test_scandal_immunity_blocks_roll ===")
    test_scandal_immunity_blocks_roll()

    print("\n=== ALL 10 DOMESTIC ACTION TESTS PASSED ===")
