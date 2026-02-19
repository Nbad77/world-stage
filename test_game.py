"""
Test suite for The World Stage v3
Verifies all critical bug fixes and mechanics
"""

import sys
import io

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from game_state import GameState
from dialogue_manager import DialogueManager
from turn_processor import check_game_over, apply_end_of_turn_effects
import npc_usa
import npc_arabia
import npc_eu
import npc_dprg


def test_turn_limit():
    """NO TURN 11 BUG - Game must stop at turn 10"""
    print("Testing Turn 11 bug fix...")
    gs = GameState()

    # Advance to turn 10
    for _ in range(9):
        result = gs.advance_turn()
        assert result == True, "Should allow advancing before turn 10"

    assert gs.current_turn == 10, f"Should be turn 10, got {gs.current_turn}"

    # Try to go past turn 10
    result = gs.advance_turn()
    assert result == False, "Should NOT allow turn 11"
    assert gs.current_turn == 10, f"Should stay at turn 10, got {gs.current_turn}"

    print("✓ Turn limit enforced - NO TURN 11!")


def test_oil_minimum():
    """NO NEGATIVE OIL - $20 minimum enforced"""
    print("\nTesting oil price minimum...")
    gs = GameState()

    # Try to crash oil price
    gs.update_oil_price(-100)
    assert gs.oil_price == 20, f"Should be $20, got ${gs.oil_price}"

    # Multiple negative updates
    gs.update_oil_price(-10)
    gs.update_oil_price(-50)
    assert gs.oil_price == 20, f"Should still be $20, got ${gs.oil_price}"

    print("✓ Oil price minimum ($20) enforced!")


def test_all_npcs_generate_messages():
    """All 4 NPCs must generate messages"""
    print("\nTesting all NPCs generate dialogue...")
    gs = GameState()
    dm = DialogueManager()

    usa_msg = npc_usa.get_usa_message(gs, dm)
    assert len(usa_msg) > 0, "USA should generate message"

    arabia_msg = npc_arabia.get_arabia_message(gs, dm)
    assert len(arabia_msg) > 0, "Arabia should generate message"

    eu_msg = npc_eu.get_eu_message(gs, dm)
    assert len(eu_msg) > 0, "EU should generate message"

    dprg_msg = npc_dprg.get_dprg_message(gs, dm)
    assert len(dprg_msg) > 0, "DPRG should generate message"

    print("✓ All 4 NPCs generate dialogue!")


def test_all_npcs_generate_offers():
    """All 4 NPCs must generate offers"""
    print("\nTesting all NPCs generate offers...")
    gs = GameState()

    usa_offer = npc_usa.get_usa_offer(gs)
    assert 'text' in usa_offer and 'consequences' in usa_offer, "USA offer malformed"

    arabia_offer = npc_arabia.get_arabia_offer(gs)
    assert 'text' in arabia_offer and 'consequences' in arabia_offer, "Arabia offer malformed"

    eu_offer = npc_eu.get_eu_offer(gs)
    assert 'text' in eu_offer and 'consequences' in eu_offer, "EU offer malformed"

    dprg_offer = npc_dprg.get_dprg_offer(gs)
    assert 'text' in dprg_offer and 'consequences' in dprg_offer, "DPRG offer malformed"

    print("✓ All 4 NPCs generate valid offers!")


def test_dialogue_uniqueness():
    """DialogueManager prevents exact repetition"""
    print("\nTesting dialogue uniqueness...")
    gs = GameState()
    dm = DialogueManager()

    variants = ["Message A", "Message B", "Message C"]
    context = {'turn': 1}

    msg1 = dm.get_unique_message('usa', variants, context)
    msg2 = dm.get_unique_message('usa', variants, context)
    msg3 = dm.get_unique_message('usa', variants, context)

    # All three should be different
    assert msg1 != msg2, f"Messages 1 & 2 should differ, got: '{msg1}'"
    assert msg2 != msg3, f"Messages 2 & 3 should differ, got: '{msg2}'"
    assert msg1 != msg3, f"Messages 1 & 3 should differ, got: '{msg1}'"

    # 4th call - all variants used, should get a unique fallback
    msg4 = dm.get_unique_message('usa', variants, {'turn': 4})
    assert msg4 not in [msg1, msg2, msg3], f"Fallback '{msg4}' should differ from all previous"

    print("✓ Dialogue uniqueness working - including fallback!")


def test_sanctions_activation():
    """USA sanctions activate at relations < 25"""
    print("\nTesting sanctions activation...")
    gs = GameState()

    # Lower USA relations below threshold
    gs.update_relations('usa', -30)  # 50 - 30 = 20
    assert gs.usa_sanctions_active, "Sanctions should activate at < 25"

    # Raise above threshold
    gs.update_relations('usa', 10)  # 20 + 10 = 30
    assert not gs.usa_sanctions_active, "Sanctions should deactivate at >= 25"

    print("✓ Sanctions system working!")


def test_embargo_activation():
    """Arabia embargo activates at relations < 25"""
    print("\nTesting embargo activation...")
    gs = GameState()

    # Lower Arabia relations
    gs.update_relations('arabia', -30)  # 50 - 30 = 20
    assert gs.arabia_embargo_active, "Embargo should activate at < 25"

    # Raise above threshold
    gs.update_relations('arabia', 10)  # 20 + 10 = 30
    assert not gs.arabia_embargo_active, "Embargo should deactivate at >= 25"

    print("✓ Embargo system working!")


def test_victory_condition():
    """Victory detected after turn 10"""
    print("\nTesting victory condition...")
    gs = GameState()

    # Should NOT be over at turn 10
    is_over, result, msg = check_game_over(gs)
    assert not is_over, "Should not be over at turn 1"

    # Simulate completing turn 10
    gs.current_turn = 11

    is_over, result, msg = check_game_over(gs)
    assert is_over, "Should be over after turn 10"
    assert result == 'victory', f"Should be victory, got {result}"

    print("✓ Victory condition working!")


def test_defeat_conditions():
    """Bankruptcy and collapse detected"""
    print("\nTesting defeat conditions...")

    # Bankruptcy
    gs1 = GameState()
    gs1.budget = -5
    is_over, result, msg = check_game_over(gs1)
    assert is_over and result == 'defeat', "Should detect bankruptcy"

    # Collapse
    gs2 = GameState()
    gs2.stability = -10
    is_over, result, msg = check_game_over(gs2)
    assert is_over and result == 'defeat', "Should detect collapse"

    print("✓ Defeat conditions working!")


def test_action_tracking():
    """Game state tracks player actions"""
    print("\nTesting action tracking...")
    gs = GameState()

    gs.record_action('side_with', 'usa')
    assert gs.times_sided_with['usa'] == 1, "Should count sided actions"
    assert gs.consecutive_sides['usa'] == 1, "Should track consecutive"

    gs.record_action('side_with', 'usa')
    assert gs.consecutive_sides['usa'] == 2, "Should increment consecutive"

    gs.record_action('side_with', 'arabia')
    assert gs.consecutive_sides['usa'] == 0, "Should reset when switching"
    assert gs.consecutive_sides['arabia'] == 1, "Should track new NPC"

    print("✓ Action tracking working!")


def run_all_tests():
    """Run complete test suite"""

    print("=" * 60)
    print("THE WORLD STAGE v3 - TEST SUITE")
    print("=" * 60)

    try:
        test_turn_limit()
        test_oil_minimum()
        test_all_npcs_generate_messages()
        test_all_npcs_generate_offers()
        test_dialogue_uniqueness()
        test_sanctions_activation()
        test_embargo_activation()
        test_victory_condition()
        test_defeat_conditions()
        test_action_tracking()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nCritical fixes verified:")
        print("  ✓ No Turn 11 bug")
        print("  ✓ No negative oil prices")
        print("  ✓ All 4 NPCs speak every turn")
        print("  ✓ No dialogue repetition")
        print("  ✓ Sanctions/embargo systems work")
        print("  ✓ Victory/defeat detection works")
        print("\n🎮 Game ready to play!")

        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    run_all_tests()
