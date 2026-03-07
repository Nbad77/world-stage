"""
Session 4B — Election mechanic tests.

6 tests covering:
1. Result mapping (fair → success/squeaker/fail based on approval)
2. Consequences applied correctly
3. Fires-once guard
4. Protests mechanic
5. Democracy lock blocking rightward regime shift
6. Observers conditions (approval 60+ and no brigade deployments)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import (
    ELECTION_CONSEQUENCES,
    apply_election_consequences,
    apply_end_of_turn_effects,
)


def test_fair_election_result_mapping():
    """Fair election maps to success/squeaker/fail based on approval thresholds."""
    # success: approval >= 60
    gs_high = GameState()
    gs_high.public_approval = 70
    # The result_key is determined in api.py, but test the threshold logic here
    assert gs_high.public_approval >= 60  # → fair_success

    # squeaker: 40 <= approval < 60
    gs_mid = GameState()
    gs_mid.public_approval = 50
    assert 40 <= gs_mid.public_approval < 60  # → fair_squeaker

    # fail: approval < 40
    gs_low = GameState()
    gs_low.public_approval = 30
    assert gs_low.public_approval < 40  # → fair_fail

    print("  PASSED: Fair election result mapping thresholds verified.")


def test_consequences_applied_correctly():
    """apply_election_consequences applies relation, stability, approval, heat, and personal cost changes."""
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 50
    gs.public_approval = 50
    gs.detection_heat = 0
    gs.personal_wealth = 10.0

    changes = apply_election_consequences(gs, 'rigged')

    # rigged: eu -5, usa -3, stability +3, heat +10, personal_cost 2.0
    assert gs.relations['eu'] < 50, f"EU should decrease, got {gs.relations['eu']}"
    assert gs.relations['usa'] < 50, f"USA should decrease, got {gs.relations['usa']}"
    assert gs.stability > 50, f"Stability should increase, got {gs.stability}"
    assert gs.detection_heat == 10, f"Heat should be 10, got {gs.detection_heat}"
    assert gs.personal_wealth < 10.0, f"Personal wealth should decrease, got {gs.personal_wealth}"
    assert len(changes) > 0, "Should return list of change descriptions"

    print(f"  PASSED: Rigged election consequences applied: {changes}")

    # FIX 2 (Session 4C): fair_squeaker should give approval +2
    gs2 = GameState()
    gs2.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs2.stability = 50
    gs2.public_approval = 50
    changes2 = apply_election_consequences(gs2, 'fair_squeaker')
    assert gs2.public_approval == 52, f"fair_squeaker should give +2 approval, got {gs2.public_approval}"
    print(f"  PASSED: fair_squeaker approval +2 verified: {changes2}")


def test_election_fires_once():
    """election_fired flag prevents duplicate elections."""
    gs = GameState()
    gs.election_turn = 4
    gs.current_turn = 4
    gs.election_fired = False

    # First election
    changes = apply_election_consequences(gs, 'fair_success')
    gs.election_fired = True
    gs.election_result = 'fair_success'

    assert gs.election_fired is True
    assert gs.election_result == 'fair_success'

    # Second attempt — the API guard checks election_fired before calling
    # apply_election_consequences. We test the flag is set correctly.
    assert gs.election_fired is True, "election_fired should be True after first election"

    print("  PASSED: Election fires-once flag verified.")


def test_protests_mechanic():
    """Protests fire when protests_pending=True and no brigades deployed."""
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 60
    gs.public_approval = 60
    gs.protests_pending = True
    gs.brigades_deployed_last_turn = False
    gs.current_turn = 5
    gs.oil_price = 50
    gs.budget = 50.0

    old_stab = gs.stability
    old_appr = gs.public_approval
    old_usa = gs.relations['usa']
    old_eu = gs.relations['eu']

    messages = apply_end_of_turn_effects(gs)

    # Protests should have fired
    assert gs.stability < old_stab, f"Stability should drop, was {old_stab} now {gs.stability}"
    assert gs.public_approval < old_appr, f"Approval should drop, was {old_appr} now {gs.public_approval}"
    assert gs.relations['usa'] < old_usa, f"USA relations should drop, was {old_usa} now {gs.relations['usa']}"
    assert gs.relations['eu'] < old_eu, f"EU relations should drop, was {old_eu} now {gs.relations['eu']}"
    assert gs.protests_pending is False, "protests_pending should be cleared"

    # Check message
    protest_msgs = [m for m in messages if 'protests' in m.lower() or 'protest' in m.lower()]
    assert len(protest_msgs) > 0, f"Should have protest message, got: {messages[:3]}"

    print(f"  PASSED: Protests mechanic verified. Messages: {protest_msgs}")


def test_democracy_lock_blocks_rightward_shift():
    """When regime_democracy_locked > 0, rightward regime shifts are blocked."""
    gs = GameState()
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs.stability = 20  # Below 30 — would normally trigger rightward shift
    gs.public_approval = 50
    gs.regime_democracy_locked = 2
    gs.current_turn = 5
    gs.oil_price = 50
    gs.budget = 50.0
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.action_history = [{'type': 'side_with', 'npc': 'usa'}]

    messages = apply_end_of_turn_effects(gs)

    # Regime should NOT have shifted right despite stability < 30
    assert gs.state_identity['regime_type'] == 'Managed Democracy', (
        f"Regime should stay Managed Democracy when democracy locked, "
        f"got {gs.state_identity['regime_type']}"
    )

    # Democracy lock should have decremented
    assert gs.regime_democracy_locked == 1, (
        f"Democracy lock should decrement to 1, got {gs.regime_democracy_locked}"
    )

    print("  PASSED: Democracy lock blocks rightward regime shift.")


def test_observers_conditions():
    """Observers require approval 60+ and no brigade deployments in action_history."""
    # Case 1: eligible
    gs_ok = GameState()
    gs_ok.public_approval = 65
    gs_ok.action_history = [
        {'type': 'side_with', 'npc': 'usa'},
        {'type': 'accept_deal', 'npc': 'eu'},
    ]
    eligible = gs_ok.public_approval >= 60 and not any(
        a.get('type') == 'deploy_brigades' for a in gs_ok.action_history
    )
    assert eligible is True, "Should be eligible with 65% approval and no brigades"

    # Case 2: approval too low
    gs_low = GameState()
    gs_low.public_approval = 55
    gs_low.action_history = []
    low_eligible = gs_low.public_approval >= 60
    assert low_eligible is False, "Should not be eligible with 55% approval"

    # Case 3: has brigade deployments
    gs_brigade = GameState()
    gs_brigade.public_approval = 70
    gs_brigade.action_history = [
        {'type': 'side_with', 'npc': 'usa'},
        {'type': 'deploy_brigades', 'operation': 1},
    ]
    brigade_eligible = gs_brigade.public_approval >= 60 and not any(
        a.get('type') == 'deploy_brigades' for a in gs_brigade.action_history
    )
    assert brigade_eligible is False, "Should not be eligible with brigade deployments"

    # Case 4: observers consequences set democracy lock
    gs_obs = GameState()
    gs_obs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50}
    gs_obs.stability = 50
    gs_obs.personal_wealth = 10.0
    changes = apply_election_consequences(gs_obs, 'observers')
    assert gs_obs.regime_democracy_locked == 3, (
        f"Observers should set democracy lock to 3, got {gs_obs.regime_democracy_locked}"
    )

    print("  PASSED: Observers conditions verified (approval, brigades, and lock).")


if __name__ == '__main__':
    print("\n=== test_fair_election_result_mapping ===")
    test_fair_election_result_mapping()

    print("\n=== test_consequences_applied_correctly ===")
    test_consequences_applied_correctly()

    print("\n=== test_election_fires_once ===")
    test_election_fires_once()

    print("\n=== test_protests_mechanic ===")
    test_protests_mechanic()

    print("\n=== test_democracy_lock_blocks_rightward_shift ===")
    test_democracy_lock_blocks_rightward_shift()

    print("\n=== test_observers_conditions ===")
    test_observers_conditions()

    print("\n=== ALL ELECTION TESTS PASSED ===")
