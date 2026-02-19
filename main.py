"""
THE WORLD STAGE - Version 3
DRAMATIC geopolitical simulator with personality and proper architecture

ALL 4 NPCs speak EVERY turn
Complex offers based on context
Stage directions and personality
Clean bug-free mechanics
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from game_state import GameState
from dialogue_manager import DialogueManager
from turn_processor import process_choice_consequences, apply_end_of_turn_effects, check_game_over, get_escape_ending
import npc_usa
import npc_arabia
import npc_eu
import npc_dprg
import npc_engine


def display_title():
    """Show dramatic title screen"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║              🌍  THE WORLD STAGE  🌍                      ║
║                                                            ║
║              A Geopolitical Thriller                       ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  You are EUROPA - a new nation caught between            ║
║  global superpowers who ALL want something from you.      ║
║                                                            ║
║  Each turn, FOUR voices compete for your attention:       ║
║                                                            ║
║  🇺🇸 USA - Professional, increasingly threatening         ║
║  🛢️  SADAM (Arabia) - Theatrical, transactional          ║
║  🇪🇺 EU - Idealistic, bureaucratic                        ║
║  ⚡ JI-WON (DPRG) - Cryptic, opportunistic               ║
║                                                            ║
║  🎯 SURVIVE 10 TURNS without bankruptcy or collapse       ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    input("Press ENTER to begin the drama...")
    print("\n")


def get_all_npc_messages(game_state, dialogue_manager):
    """Get messages from ALL 4 NPCs via Claude API (with static fallback)."""
    return npc_engine.generate_dialogue(game_state)


def get_all_offers(game_state):
    """Get offers from all 4 NPCs - player can choose ONE.
    Conditionally adds Option F (Ji-won escape) and Option G (emergency injection).
    """

    offers = []

    # A) USA offer
    usa_offer = npc_usa.get_usa_offer(game_state)
    offers.append(('A', usa_offer))

    # B) Arabia offer
    arabia_offer = npc_arabia.get_arabia_offer(game_state)
    offers.append(('B', arabia_offer))

    # C) EU offer
    eu_offer = npc_eu.get_eu_offer(game_state)
    offers.append(('C', eu_offer))

    # D) DPRG offer
    dprg_offer = npc_dprg.get_dprg_offer(game_state)
    offers.append(('D', dprg_offer))

    # E) Do nothing
    do_nothing = {
        'text': 'Do nothing (all relations -5, stability -2%)',
        'type': 'do_nothing',
        'npc': None,
        'consequences': {
            'usa': -5,
            'arabia': -5,
            'eu': -5,
            'dprg': -5,
            'stability': -2
        }
    }
    offers.append(('E', do_nothing))

    # F) Ji-won escape — only when personal_wealth >= $25B AND budget <= $12B
    if game_state.personal_wealth >= 25 and game_state.budget <= 12:
        escape_offer = {
            'text': f'[Ji-won] Activate escape plan — vanish with ${game_state.personal_wealth:.1f}B (ends game)',
            'type': 'escape',
            'npc': 'dprg',
            'consequences': {}
        }
        offers.append(('F', escape_offer))

    # G) Emergency fund injection — only when budget < $5B and personal_wealth > 0
    if game_state.budget < 5 and game_state.personal_wealth > 0:
        inject_offer = {
            'text': f'[PRIVATE] Emergency: inject personal funds into national treasury (${game_state.personal_wealth:.1f}B available)',
            'type': 'inject_funds',
            'npc': None,
            'consequences': {}
        }
        offers.append(('G', inject_offer))

    return offers


def display_options(offers):
    """Display all options beautifully"""

    print("\n" + "=" * 60)
    print("YOUR OPTIONS:")
    print("=" * 60)

    for letter, offer in offers:
        print(f"{letter}) {offer['text']}")

    print("=" * 60)


def get_player_choice(offers):
    """Get validated player choice"""

    valid_letters = [letter for letter, _ in offers]

    while True:
        try:
            choice_input = input(f"\nEnter your choice ({', '.join(valid_letters)}): ").strip().upper()

            if choice_input in valid_letters:
                # Find the matching offer
                for letter, offer in offers:
                    if letter == choice_input:
                        return offer
            else:
                print(f"Please enter one of: {', '.join(valid_letters)}")

        except KeyboardInterrupt:
            print("\n\nGame interrupted. Exiting...")
            sys.exit(0)


def get_skim_choice(game_state):
    """
    Show the private skim prompt after diplomatic choice.
    Returns (national_cost, personal_gain, stability_hit, approval_hit, label).
    Options gated by available budget.
    """
    budget = game_state.budget

    print("\n" + "─" * 60)
    print("💰 PRIVATE DECISION (Eyes Only):")
    print("─" * 60)
    print("Your advisors present... an opportunity.")
    print("Public funds flow through your hands.")
    print("Some could flow elsewhere.\n")

    options = {
        '1': (0.0, 0.0, 0, 0, "Stay clean — no personal skim"),
    }
    if budget >= 1.0:
        options['2'] = (1.0, 1.0, -1, 0,  "Small skim:  -$1B national, +$1B personal, -1% stability")
    if budget >= 3.0:
        options['3'] = (3.0, 3.0, -3, -2, "Medium skim: -$3B national, +$3B personal, -3% stability, -2% approval")
    if budget >= 7.0:
        options['4'] = (7.0, 7.0, -6, -5, "Large skim:  -$7B national, +$7B personal, -6% stability, -5% approval")

    for key, (_, _, _, _, label) in options.items():
        print(f"  {key}) {label}")

    valid = list(options.keys())
    while True:
        try:
            raw = input(f"\nEnter skim choice ({'/'.join(valid)}): ").strip()
            if raw in valid:
                return options[raw]
            print(f"  Please enter one of: {'/'.join(valid)}")
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Exiting...")
            sys.exit(0)


def get_inject_choice(game_state):
    """
    System 3: Emergency fund injection sub-prompt.
    Player moves money from personal_wealth to national budget.
    Options gated by available personal_wealth.
    Returns (personal_cost, national_gain, label) or None if cancelled.
    """
    pw = game_state.personal_wealth
    print("\n" + "─" * 60)
    print("💉 EMERGENCY FUND INJECTION (Eyes Only):")
    print("─" * 60)
    print("The treasury is nearly empty. Your advisors look at you.")
    print("They know. You know. There is another account.")
    print(f"Personal reserves available: ${pw:.1f}B\n")

    options = {}
    if pw >= 3:
        options['1'] = (3.0, 3.0, "Inject $3B  (−$3B personal → +$3B national)")
    if pw >= 7:
        options['2'] = (7.0, 7.0, "Inject $7B  (−$7B personal → +$7B national)")
    if pw > 0:
        options['3'] = (pw, pw,   f"Inject ALL  (−${pw:.1f}B personal → +${pw:.1f}B national)")
    options['0'] = (0.0, 0.0, "Do nothing  (keep personal funds, risk bankruptcy)")

    for key, (_, _, label) in sorted(options.items()):
        print(f"  {key}) {label}")

    valid = sorted(options.keys())
    while True:
        try:
            raw = input(f"\nEnter injection choice ({'/'.join(valid)}): ").strip()
            if raw in valid:
                cost, gain, label = options[raw]
                return (cost, gain, label)
            print(f"  Please enter one of: {'/'.join(valid)}")
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Exiting...")
            sys.exit(0)


def get_corruption_npc_comments(game_state):
    """
    Return one-shot NPC comments when personal_wealth crosses $8B / $20B / $35B.
    Flags are SET here in Python (deterministic). Text is generated by Claude API.
    Each comment fires exactly once per playthrough.
    """
    pw = game_state.personal_wealth
    w = game_state.corruption_warned
    comments = []

    # ── $8B threshold ──────────────────────────────────────────────
    if pw > 8:
        any_8b_unfired = any(not w[f"{npc}_5"] for npc in ['usa', 'arabia', 'eu', 'dprg'])
        if any_8b_unfired:
            # Set all four flags atomically (npc_engine checks them before generating)
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_5"] = True
            intercepts = npc_engine.generate_intercept_comments(game_state, '8b')
            # Restore flags to False so npc_engine sees them as unfired
            # (we set them above just to pass — but npc_engine checks them to SKIP)
            # Actually: npc_engine checks "if already fired, skip". We want it to NOT skip.
            # So we DON'T set flags before calling — we set them AFTER.
            # Re-approach: reset, let npc_engine see them as unfired, then set.
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_5"] = False
            intercepts = npc_engine.generate_intercept_comments(game_state, '8b')
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_5"] = True
            comments.extend(intercepts)

    # ── $20B threshold ─────────────────────────────────────────────
    if pw > 20:
        any_20b_unfired = any(not w[f"{npc}_15"] for npc in ['usa', 'arabia', 'eu', 'dprg'])
        if any_20b_unfired:
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_15"] = False
            intercepts = npc_engine.generate_intercept_comments(game_state, '20b')
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_15"] = True
            comments.extend(intercepts)

    # ── $35B threshold ─────────────────────────────────────────────
    if pw > 35:
        any_35b_unfired = any(not w[f"{npc}_30"] for npc in ['usa', 'arabia', 'eu', 'dprg'])
        if any_35b_unfired:
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_30"] = False
            intercepts = npc_engine.generate_intercept_comments(game_state, '35b')
            for npc in ['usa', 'arabia', 'eu', 'dprg']:
                w[f"{npc}_30"] = True
            comments.extend(intercepts)

    return comments


def check_usa_blackmail(game_state):
    """
    System 4: USA blackmail mechanic.
    Returns True if blackmail is active this turn (fires once per game).
    Condition: personal_wealth >= $20B AND usa_relations <= 20 AND not yet used.
    """
    if (not game_state.blackmail_used
            and game_state.personal_wealth >= 20
            and game_state.relations['usa'] <= 20):
        return True
    return False


def display_blackmail_demand(game_state):
    """Print the USA blackmail demand message, replacing normal USA dialogue."""
    pw = game_state.personal_wealth
    print(f"""
{'─'*60}
🇺🇸 CIA DIRECTOR (Eyes-Only Channel):
{'─'*60}
  *encrypted transmission*

  "We know about the ${pw:.1f}B. Every transfer. Every account.
  We know about Zurich. We know about the Cayman routing.
  We know what you told the Senate is different from
  what you did with Europa's treasury.

  You have one choice: cooperate with us FULLY on every
  demand this turn — or we send the financial intelligence
  file to every major news outlet simultaneously.

  Your citizens will see exactly what their leader did
  with their money. We will be watching your decision."

  Option A on this turn = full cooperation. We stay quiet.
  Any other choice = full exposure. Immediately.
{'─'*60}""")


def apply_blackmail_result(game_state, chose_cooperate):
    """Apply consequences of blackmail choice."""
    messages = []
    game_state.blackmail_used = True
    if chose_cooperate:
        # Cooperate: normal A consequences + silent -$2B personal
        game_state.personal_wealth = max(0, game_state.personal_wealth - 2.0)
        messages.append("[CIA SATISFIED] Cooperation logged. -$2B personal: 'administrative fee'.")
        messages.append(f"  Personal account: ${game_state.personal_wealth:.1f}B remaining.")
    else:
        # Refuse: public exposure
        game_state.update_stability(-12)
        game_state.update_approval(-15)
        game_state.update_relations('eu', -10)
        messages.append("📰 EXPOSURE: CIA financial dossier released to international press.")
        messages.append(f"  Europa reels: -12% stability, -15% approval, EU -10 relations.")
        messages.append(f"  The ${game_state.personal_wealth:.1f}B is now public knowledge.")
    return messages


def run_turn(game_state, dialogue_manager):
    """Execute one complete turn"""

    # Clear screen effect
    print("\n" * 2)

    # 1. Display status
    print(game_state.get_status_display())

    # 2. Check USA blackmail condition BEFORE NPC speeches
    blackmail_active = check_usa_blackmail(game_state)

    # 3. ALL NPCs speak (USA replaced by blackmail demand if active)
    print("\n📢 THE POWERS SPEAK:\n")
    if blackmail_active:
        display_blackmail_demand(game_state)
        # Other 3 NPCs still speak — use API for their dialogue too
        all_four = npc_engine.generate_dialogue(game_state)
        # all_four is [usa, arabia, eu, dprg] — skip index 0 (USA replaced by blackmail)
        print(all_four[1])  # Arabia
        print(all_four[2])  # EU
        print(all_four[3])  # DPRG
    else:
        messages = get_all_npc_messages(game_state, dialogue_manager)
        for msg in messages:
            print(msg)

    # 4. Get all offers
    offers = get_all_offers(game_state)

    # 5. Display options
    display_options(offers)

    # 6. Get player choice
    choice = get_player_choice(offers)

    # ── SPECIAL: Option F — Ji-won escape ──────────────────────
    if choice['type'] == 'escape':
        escape_msg = get_escape_ending(game_state)
        print("\n" * 2)
        print(escape_msg)
        return False

    # ── SPECIAL: Option G — Emergency fund injection ────────────
    if choice['type'] == 'inject_funds':
        personal_cost, national_gain, inject_label = get_inject_choice(game_state)
        if personal_cost > 0:
            game_state.personal_wealth = max(0, game_state.personal_wealth - personal_cost)
            game_state.update_budget(national_gain)
            print(f"\n  [PRIVATE] {inject_label}")
            print(f"  [PRIVATE] National treasury: ${game_state.budget:.1f}B | Personal account: ${game_state.personal_wealth:.1f}B")
            if game_state.personal_wealth <= 0.01:
                print("  ✦ PRIVATE: You gave everything. The Swiss account is empty.")
                print("    Whatever happens next, you face it as a patriot.")
        else:
            print("\n  [PRIVATE] No injection made.")
        # G is a full turn action — skip skim but proceed to end-of-turn
        chose_a_for_blackmail = False
    else:
        # 7. Record action in game state
        game_state.record_action(choice['type'], choice.get('npc'))

        # 8. Process immediate consequences
        print("\n" + "─" * 60)
        print("⚡ IMMEDIATE CONSEQUENCES:")
        print("─" * 60)

        consequence_msgs = process_choice_consequences(game_state, choice)
        for msg in consequence_msgs:
            print(f"  {msg}")

        # Track whether player chose A during blackmail
        chose_a_for_blackmail = (blackmail_active and choice.get('npc') == 'usa')

        # 8a. Blackmail result (fires once, sets blackmail_used)
        if blackmail_active:
            print("\n" + "─" * 60)
            print("🔒 CIA RESPONSE:")
            print("─" * 60)
            blackmail_msgs = apply_blackmail_result(game_state, chose_a_for_blackmail)
            for msg in blackmail_msgs:
                print(f"  {msg}")

        # 8b. Private skim decision
        national_cost, personal_gain, stab_hit, appr_hit, skim_label = get_skim_choice(game_state)
        if personal_gain > 0:
            game_state.budget -= national_cost
            game_state.personal_wealth += personal_gain
            game_state.update_stability(stab_hit)
            game_state.update_approval(appr_hit)
            print(f"\n  [PRIVATE] {skim_label}")
            print(f"  [PRIVATE] National treasury: ${game_state.budget:.1f}B | Personal account: ${game_state.personal_wealth:.1f}B")

            # ── System 1: Real-time corruption feedback ──────────
            pw = game_state.personal_wealth
            budget = game_state.budget
            if budget < 8 and pw > 25:
                print(f"  ⚠️  [PRIVATE] The plane is fueled. The account is full. Europa may not need you much longer.")
            elif budget < 15 and pw > 20:
                print(f"  ⚠️  [PRIVATE] Your exit fund grows while the national reserves shrink.")
            elif pw > budget * 1.5:
                print(f"  ⚠️  [PRIVATE] You are now personally wealthier than the nation you govern.")
        else:
            print("\n  [PRIVATE] No skim taken.")

        # 8c. NPC corruption comments (one-shot, fires when thresholds crossed)
        corruption_comments = get_corruption_npc_comments(game_state)
        if corruption_comments:
            print("\n" + "─" * 60)
            print("👁️  INTELLIGENCE INTERCEPTS:")
            print("─" * 60)
            for comment in corruption_comments:
                print(f"  {comment}")

    # 9. Apply end-of-turn effects
    print("\n" + "─" * 60)
    print("🌍 END OF TURN EFFECTS:")
    print("─" * 60)

    effect_msgs = apply_end_of_turn_effects(game_state)
    if effect_msgs:
        for msg in effect_msgs:
            print(f"  {msg}")
    else:
        print("  (No special effects this turn)")

    print("─" * 60)

    # 10. Check defeat conditions (bankruptcy / collapse / revolt)
    is_over, result, message = check_game_over(game_state)

    if is_over:
        print("\n" * 2)
        print(message)
        return False  # End game

    # 11. Advance turn (enforced max 10)
    can_continue = game_state.advance_turn()

    if not can_continue:
        # We've completed all 10 turns — trigger victory screen
        # Temporarily push current_turn past max so check_game_over fires victory
        game_state.current_turn = game_state.max_turns + 1
        is_over, result, message = check_game_over(game_state)
        print("\n" * 2)
        print(message)
        return False

    # Continue to next turn
    input("\n⏭️  Press ENTER to continue to next turn...")
    return True


def main():
    """Main game loop"""

    # Initialize
    game_state = GameState()
    dialogue_manager = DialogueManager()

    # Title screen
    display_title()

    # Game loop
    game_running = True

    while game_running:
        game_running = run_turn(game_state, dialogue_manager)

    # Final message
    print("\n" + "=" * 60)
    print("Thank you for playing THE WORLD STAGE")
    print("=" * 60)

    # Print API usage summary
    npc_engine.print_session_stats()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Game interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
