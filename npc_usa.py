"""
USA NPC - Professional, escalating, increasingly threatening
Titles escalate: State Department → NSC → Pentagon → Emergency Broadcast
EXPANDED MESSAGE POOLS - Minimum 8 variants per situation
"""


def get_usa_message(game_state, dialogue_manager):
    """Generate USA message based on context with EXPANDED message pools"""

    turn = game_state.current_turn
    relations = game_state.relations['usa']
    arabia_relations = game_state.relations['arabia']
    ignored_count = game_state.consecutive_ignores['usa']
    budget = game_state.budget

    # Context variables for dynamic message formatting
    context = {
        'turn': turn,
        'relations': relations,
        'budget': budget,
        'ignored_count': ignored_count,
        'arabia_rel': arabia_relations
    }

    # Determine title based on severity
    if game_state.usa_sanctions_active:
        title = "USA (Emergency Broadcast)"
    elif relations < 25:
        title = "USA (Pentagon)"
    elif turn >= 7:
        title = "USA (National Security Council)"
    else:
        title = "USA (State Department)"

    # PRIORITY 1: Active sanctions - EXPANDED POOL (12 variants)
    if game_state.usa_sanctions_active:
        variants = [
            "Economic warfare is our specialty. The sanctions will continue until your government changes course.",
            "Your economy bleeds $2 billion per turn. Are you ready to negotiate yet?",
            "The Pentagon calculates you have limited time before economic collapse begins.",
            "Every turn costs you billions. One phone call to Washington ends this - but it requires submission.",
            "Your people starve while Sadam profits. Is this the Europa you envisioned?",
            "Turn {turn} under sanctions. Your budget hemorrhages. When will you learn?",
            "We've watched you choose oil over principles. The sanctions are permanent until you reverse course.",
            "The United States does not negotiate with nations that fund our enemies. Comply or collapse.",
            "Sanctions continue. Budget at ${budget:.1f}B and falling. Your move, Europa.",
            "Turn {turn}: The economic pressure intensifies. How long can your government endure this?",
            "Every billion you lose brings you closer to capitulation. The Pentagon is patient.",
            "Your stability crumbles while you cling to Sadam's oil money. Was it worth it?"
        ]
        message = dialogue_manager.get_unique_message('usa', variants, context)
        return dialogue_manager.format_npc_message('usa', title, message)

    # PRIORITY 2: Betrayal (took Arabia oil then sided with USA) - 8 variants
    if game_state.took_arabia_oil and relations > 40:
        variants = [
            "We see you took Sadam's oil money but now seek our friendship. That's... pragmatic. But trust must be rebuilt.",
            "Playing both sides is dangerous, Europa. We notice everything. Your Arabia deals complicate our relationship.",
            "You accepted their petroleum and now want our protection? The Pentagon has questions about your loyalties.",
            "Turn {turn}: Your previous Arabia partnership is noted. Rebuilding trust requires consistency, not opportunism.",
            "We appreciate your recent alignment, but your history with Sadam hasn't been forgotten. Prove yourself.",
            "The National Security Council debates whether your conversion is genuine or merely tactical.",
            "You've chosen the right side, but your past with Arabia's oil money raises red flags in Washington.",
            "Intelligence reports your Arabia deals total billions. Convince us you're not still compromised."
        ]
        message = dialogue_manager.get_unique_message('usa', variants, context)
        return dialogue_manager.format_npc_message('usa', title, message)

    # PRIORITY 3: Ignored multiple times - 8 variants
    if ignored_count >= 3:
        variants = [
            "You've ignored us {ignored_count} consecutive times. This is not how allies behave. There will be consequences.",
            "Silence is a choice, Europa. And choices have consequences. We're running out of patience.",
            "After {ignored_count} ignored communications, we must assume you're not interested in American partnership. Noted.",
            "Turn {turn}: {ignored_count} times ignored. The State Department considers this a pattern, not an accident.",
            "Your repeated silence speaks volumes. The Pentagon doesn't appreciate being dismissed by minor powers.",
            "Diplomatic overtures ignored {ignored_count} times. Washington takes this as intentional disrespect.",
            "We've attempted dialogue {ignored_count} consecutive turns. Perhaps economic pressure will be more persuasive.",
            "Turn {turn}: {ignored_count} ignored messages. The National Security Council recommends escalation protocols."
        ]
        message = dialogue_manager.get_unique_message('usa', variants, context)
        return dialogue_manager.format_npc_message('usa', title, message)

    # PRIORITY 4: High Arabia relations (pressure) - 8 variants
    if arabia_relations > 60:
        variants = [
            "We're watching your Arabia deals closely. This undermines our strategic position. Sanction them NOW.",
            "Your relationship with Sadam is becoming a problem. Choose a side, Europa. This tightrope won't hold.",
            "Every dollar you give Arabia funds instability. The State Department expects better from European nations.",
            "Turn {turn}: Arabia relations at {arabia_rel}. You're dangerously close to becoming part of the problem.",
            "Intelligence indicates deepening Europa-Arabia cooperation. This conflicts with American regional interests.",
            "The Pentagon views your Arabia partnership as strategic betrayal. Sanctions are being considered.",
            "Sadam laughs as you fill his coffers. Meanwhile, our allies question Europa's reliability.",
            "Turn {turn}: Choose between Arabian oil money and American security guarantees. You cannot have both."
        ]
        message = dialogue_manager.get_unique_message('usa', variants, context)
        return dialogue_manager.format_npc_message('usa', title, message)

    # PRIORITY 5: Turn-based escalation with EXPANDED POOLS (8 variants each)
    if turn <= 2:
        variants = [
            "Europa, we need reliable partners in this region. Show us where you stand.",
            "Welcome to the world stage. The United States values nations that share our principles. Will you be one of them?",
            "Early moves matter, Europa. We're watching to see if you'll be a strategic partner or a liability.",
            "Turn {turn}: The State Department extends an invitation to partnership. How you respond shapes everything.",
            "New nations face crucial early decisions. Align with the free world, and prosper. Oppose us... well.",
            "We're evaluating Europa's potential as an ally. Your first moves will determine our relationship for years.",
            "Turn {turn}: Choose your friends carefully. America rewards loyalty and punishes opportunism.",
            "The world is watching Europa's debut. Will you stand with the democratic West or drift toward authoritarians?"
        ]
    elif turn <= 4:
        variants = [
            "Turn {turn} already. Your neutrality is noted, but neutrality won't protect you in a crisis.",
            "We need commitment, not fence-sitting. Sanction Arabia and demonstrate you're with the free world.",
            "The window for easy partnership is closing. After this, our expectations will be... less flexible.",
            "Turn {turn}: The National Security Council grows impatient with ambiguity. Declare your position.",
            "Fence-sitting worked in the Cold War. This is a different era. Choose America or face the consequences.",
            "We've offered partnership for {turn} turns. How much longer will you play both sides?",
            "The Pentagon notes Europa's refusal to commit. This looks like cowardice, not diplomacy.",
            "Turn {turn}: Every day you delay choosing costs you leverage. Our offers won't last forever."
        ]
    elif turn <= 6:
        variants = [
            "We're past the halfway point. Still no clear commitment from Europa. This is disappointing.",
            "Our patience has limits. You need to decide: are you with us or against us? No more ambiguity.",
            "The Pentagon is asking why Europa refuses to sanction known hostile actors. I need an answer.",
            "Turn {turn}: Six turns of neutrality look less like diplomacy and more like collaboration with enemies.",
            "The National Security Council expected more from a European nation. Your hesitation aids our adversaries.",
            "Halfway through and you've aligned with neither freedom nor tyranny. Weakness, not wisdom.",
            "Turn {turn}: Time is running out to prove you're a reliable partner. The Pentagon drafts contingency plans.",
            "Six turns without commitment. Washington interprets this as tacit support for destabilizing actors."
        ]
    elif turn <= 8:
        variants = [
            "Turn {turn}. The endgame approaches. If you're not clearly aligned with us by Turn 10, we have protocols.",
            "Final opportunities are evaporating. Show loyalty now or face the reality of American economic power.",
            "We're entering the critical phase. Your next moves will determine whether sanctions become necessary.",
            "Turn {turn}: The Pentagon has authorized preparations for economic countermeasures. Comply or suffer.",
            "Eight turns of ambiguity. The National Security Council recommends treating Europa as non-aligned at best.",
            "Time to choose, Europa. Turn 10 approaches, and with it, permanent consequences for your decisions.",
            "Turn {turn}: The window closes. After this, you're either with America or you're irrelevant to us.",
            "Final turns mean final chances. The State Department won't extend partnership offers indefinitely."
        ]
    else:  # Turn 9-10 (8 variants)
        variants = [
            "This is it, Europa. Final turns. Choose America or face isolation. There is no middle ground anymore.",
            "Last chance to prove you understand how the world works. The Pentagon is preparing contingencies.",
            "Turn {turn} approaches the end. After this, your choices are permanent. History will record which side you chose.",
            "Final turn. The United States remembers its friends and its enemies. Which category will Europa occupy?",
            "This is the endgame. Align with us now, or spend the next decade explaining why you didn't.",
            "Turn {turn}: Your legacy is being written in real-time. Will you be remembered as ally or obstacle?",
            "Last opportunity. After Turn 10, American policy toward Europa is locked in. Choose wisely.",
            "The final hours. The Pentagon watches your every move. This determines Europa's future for a generation."
        ]

    message = dialogue_manager.get_unique_message('usa', variants, context)
    return dialogue_manager.format_npc_message('usa', title, message)


def get_usa_offer(game_state):
    """Generate USA's offer based on context"""

    turn = game_state.current_turn
    relations = game_state.relations['usa']

    # Different offers based on context
    if game_state.usa_sanctions_active:
        return {
            'text': 'Negotiate sanctions removal (costs $5B, +25 USA relations)',
            'type': 'accept_deal',
            'npc': 'usa',
            'consequences': {
                'budget': -5,
                'usa': 25,
                'special': 'remove_sanctions'
            }
        }

    if relations > 70:
        return {
            'text': 'Form military alliance (+stability, +15 USA relations, Arabia/DPRG furious)',
            'type': 'accept_deal',
            'npc': 'usa',
            'consequences': {
                'usa': 15,
                'stability': 8,
                'arabia': -20,
                'dprg': -15
            }
        }

    if turn >= 5:
        return {
            'text': 'Side with USA: Sanction Arabia (+20 USA relations, -30 Arabia relations)',
            'type': 'side_with',
            'npc': 'usa',
            'consequences': {
                'usa': 20,
                'arabia': -30
            }
        }

    # Default USA offer
    return {
        'text': 'Side with USA (+15 USA relations, -10 Arabia)',
        'type': 'side_with',
        'npc': 'usa',
        'consequences': {
            'usa': 15,
            'arabia': -10
        }
    }
