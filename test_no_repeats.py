"""
STRESS TEST: Simulates the exact bug scenario from the player report.
- Takes Arabia oil deal every turn (USA relations tank → sanctions)
- Runs all 10 turns
- Verifies ZERO message repetition for all 4 NPCs

If ANY message repeats word-for-word → FAIL
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from game_state import GameState
from dialogue_manager import DialogueManager
from turn_processor import process_choice_consequences, apply_end_of_turn_effects
import npc_usa, npc_arabia, npc_eu, npc_dprg


def simulate_full_game_no_repeats():
    """
    Simulate 10 turns of Arabia-max strategy (reproduces the original bug).
    Verifies every single NPC message is unique.
    """
    gs = GameState()
    dm = DialogueManager()

    # Track every message seen per NPC
    seen = {'usa': [], 'arabia': [], 'eu': [], 'dprg': []}
    duplicates_found = []

    print("=" * 62)
    print("STRESS TEST: 10-turn Arabia-oil strategy (original bug scenario)")
    print("=" * 62)

    for turn in range(1, 11):
        gs.current_turn = turn

        # --- Collect all 4 NPC messages ---
        usa_msg    = npc_usa.get_usa_message(gs, dm)
        arabia_msg = npc_arabia.get_arabia_message(gs, dm)
        eu_msg     = npc_eu.get_eu_message(gs, dm)
        dprg_msg   = npc_dprg.get_dprg_message(gs, dm)

        msgs = {
            'usa': usa_msg,
            'arabia': arabia_msg,
            'eu': eu_msg,
            'dprg': dprg_msg
        }

        # --- Check for duplicates ---
        for npc, msg in msgs.items():
            if msg in seen[npc]:
                duplicates_found.append(
                    f"Turn {turn} {npc.upper()}: DUPLICATE DETECTED!\n  Message: {msg[:80]}..."
                )
            seen[npc].append(msg)

        # --- Apply Arabia oil deal (the bug-triggering scenario) ---
        # Get the Arabia offer and apply it
        offer = npc_arabia.get_arabia_offer(gs)
        process_choice_consequences(gs, offer)
        gs.record_action('accept_deal', 'arabia')
        apply_end_of_turn_effects(gs)

        print(f"Turn {turn:2d} | Budget: ${gs.budget:.1f}B | Stability: {gs.stability}% | "
              f"USA: {gs.relations['usa']} | Arabia: {gs.relations['arabia']} | "
              f"Sanctions: {'YES' if gs.usa_sanctions_active else 'no'}")

    # --- Results ---
    print("\n" + "=" * 62)
    print("UNIQUENESS REPORT")
    print("=" * 62)

    total_messages = sum(len(v) for v in seen.values())
    print(f"Total messages delivered: {total_messages} (10 turns x 4 NPCs)")

    all_pass = True

    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        msgs = seen[npc]
        unique = len(set(msgs))
        total  = len(msgs)
        status = "PASS" if unique == total else "FAIL"
        if unique != total:
            all_pass = False
        print(f"  {npc.upper():7s}: {unique}/{total} unique  [{status}]")

    if duplicates_found:
        print("\nDUPLICATES FOUND:")
        for d in duplicates_found:
            print(f"  {d}")
    else:
        print("\nNo duplicates found in any NPC's messages.")

    print("\n" + "=" * 62)
    if all_pass:
        print("RESULT: ALL PASS - Zero message repetition across 10 turns!")
    else:
        print("RESULT: FAILED - Duplicate messages detected!")
    print("=" * 62)

    return all_pass


def simulate_usa_sanctions_scenario():
    """
    Specifically tests USA sanctions messages across turns 5-10.
    This was the exact scenario where repetition was reported.
    """
    gs = GameState()
    dm = DialogueManager()

    print("\n" + "=" * 62)
    print("TARGETED TEST: USA sanctions messages (turns 5-10)")
    print("=" * 62)

    # Force sanctions active from turn 1
    gs.relations['usa'] = 10
    gs.usa_sanctions_active = True

    seen_usa = []
    duplicates = []

    for turn in range(1, 11):
        gs.current_turn = turn
        msg = npc_usa.get_usa_message(gs, dm)

        if msg in seen_usa:
            duplicates.append(f"Turn {turn}: REPEAT - {msg[:70]}...")
        seen_usa.append(msg)

        # Show the actual quote (the inner text between quotes)
        inner = msg.split('"')[1] if '"' in msg else msg[:70]
        print(f"  Turn {turn:2d}: \"{inner[:65]}...\"")

    unique = len(set(seen_usa))
    total  = len(seen_usa)
    print(f"\n  Result: {unique}/{total} unique USA sanction messages")

    if duplicates:
        print("  DUPLICATES:")
        for d in duplicates:
            print(f"    {d}")
        return False

    print("  PASS - No USA sanction message repeated!")
    return True


def simulate_dprg_usa_hostile_scenario():
    """
    Tests DPRG messages when USA is hostile (the other reported bug scenario).
    """
    gs = GameState()
    dm = DialogueManager()

    print("\n" + "=" * 62)
    print("TARGETED TEST: DPRG messages when USA hostile (turns 6-10)")
    print("=" * 62)

    # Force USA hostile
    gs.relations['usa'] = 0
    gs.usa_sanctions_active = True

    seen_dprg = []
    duplicates = []

    for turn in range(1, 11):
        gs.current_turn = turn
        msg = npc_dprg.get_dprg_message(gs, dm)

        if msg in seen_dprg:
            duplicates.append(f"Turn {turn}: REPEAT - {msg[:70]}...")
        seen_dprg.append(msg)

        inner = msg.split('"')[1] if '"' in msg else msg[:70]
        print(f"  Turn {turn:2d}: \"{inner[:65]}...\"")

    unique = len(set(seen_dprg))
    total  = len(seen_dprg)
    print(f"\n  Result: {unique}/{total} unique DPRG messages")

    if duplicates:
        print("  DUPLICATES:")
        for d in duplicates:
            print(f"    {d}")
        return False

    print("  PASS - No DPRG message repeated!")
    return True


def simulate_arabia_usa_hostile_scenario():
    """
    Tests Arabia messages across full 10 turns with USA hostile.
    This was the third reported repetition bug.
    """
    gs = GameState()
    dm = DialogueManager()

    print("\n" + "=" * 62)
    print("TARGETED TEST: Arabia messages with USA hostile (all 10 turns)")
    print("=" * 62)

    gs.relations['usa'] = 10
    gs.usa_sanctions_active = True

    seen_arabia = []
    duplicates = []

    for turn in range(1, 11):
        gs.current_turn = turn
        msg = npc_arabia.get_arabia_message(gs, dm)

        if msg in seen_arabia:
            duplicates.append(f"Turn {turn}: REPEAT - {msg[:70]}...")
        seen_arabia.append(msg)

        inner = msg.split('"')[1] if '"' in msg else msg[:70]
        print(f"  Turn {turn:2d}: \"{inner[:65]}...\"")

    unique = len(set(seen_arabia))
    total  = len(seen_arabia)
    print(f"\n  Result: {unique}/{total} unique Arabia messages")

    if duplicates:
        print("  DUPLICATES:")
        for d in duplicates:
            print(f"    {d}")
        return False

    print("  PASS - No Arabia message repeated!")
    return True


if __name__ == "__main__":
    results = []
    results.append(simulate_full_game_no_repeats())
    results.append(simulate_usa_sanctions_scenario())
    results.append(simulate_dprg_usa_hostile_scenario())
    results.append(simulate_arabia_usa_hostile_scenario())

    print("\n" + "=" * 62)
    passed = sum(results)
    total  = len(results)
    if passed == total:
        print(f"ALL {total}/{total} STRESS TESTS PASSED")
        print("The dialogue repetition bug is FIXED.")
    else:
        print(f"{passed}/{total} tests passed. STILL BROKEN.")
    print("=" * 62)
