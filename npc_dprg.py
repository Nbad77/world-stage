"""
DPRG (Ji-won) NPC - Cryptic, menacing, opportunistic
EXPANDED POOLS - 8 variants per situation, uses get_unique_message()
"""


def get_dprg_message(game_state, dialogue_manager):
    """Generate DPRG message - guaranteed unique every turn"""

    turn = game_state.current_turn
    relations = game_state.relations['dprg']
    usa_relations = game_state.relations['usa']
    budget = game_state.budget
    stability = game_state.stability

    context = {
        'turn': turn, 'relations': relations, 'usa_rel': usa_relations,
        'budget': budget, 'stability': stability
    }

    title = 'JI-WON'

    if relations > 70:
        stage_direction = '*rare smile*'
    elif relations > 50:
        stage_direction = '*chuckles softly*'
    elif usa_relations < 25:
        stage_direction = '*steps from shadows*'
    else:
        stage_direction = '*cryptic smile*'

    # PRIORITY 1: Desperate situation - 10 variants
    if budget < 20 or stability < 35:
        stage_direction = '*extends hand*'
        variants = [
            'Budget ${budget:.1f}B, stability {stability}%. The West abandons the desperate. I help those who help themselves. $10B loan. No strings... officially.',
            'Your government teeters. The Americans watch you collapse with indifference. I offer what they will not: unconditional support.',
            "Desperate times call for desperate allies. ${budget:.1f}B won't last. {stability}% stability won't hold. DPRG assistance? That is real.",
            'Europa bleeds. USA lectures. Arabia negotiates. EU bureaucratizes. I offer SURVIVAL. Will you take it?',
            'Turn {turn}: ${budget:.1f}B budget. {stability}% stability. In my country we have a saying: the drowning man does not ask who throws the rope.',
            "The West told you this would work. It is not working. I told you I would be here when it didn't. I am here.",
            'Turn {turn}: Look at your numbers. ${budget:.1f}B. {stability}%. Now look at my offer. $10 billion. No conditions. Simple.',
            'Your Western allies watch you suffer and offer lectures. I offer money. Which helps more in a crisis?',
            'Stability at {stability}%. This is the moment I have waited for - not with pleasure, but with patience. Let me help.',
            'Turn {turn}: The Americans could fix this with one phone call. They choose not to. I choose differently.'
        ]
        message = dialogue_manager.get_unique_message('dprg', variants, context)
        return dialogue_manager.format_npc_message('dprg', title, message, stage_direction)

    # PRIORITY 2: High relations - 8 variants
    if relations > 60:
        stage_direction = '*rare smile*'
        variants = [
            'Relations at {relations}/100. You understand what others do not: REAL power requires ruthlessness. I propose military cooperation.',
            "Few nations earn Ji-won's trust. You have. I offer what I offer almost none: joint exercises, weapons technology, true alliance.",
            '{relations}/100 - impressive. The DPRG does not make friends easily. But when we do... we are LOYAL. Let us formalize this.',
            "You've proven yourself different from the Western puppets. I offer protection they cannot: weapons that GUARANTEE sovereignty.",
            'Turn {turn}: {relations}/100 relations. In my experience, this level of trust between nations leads to... formal arrangements.',
            'The West calls us pariahs. You call us partners. At {relations}/100, that word begins to have real meaning.',
            'Turn {turn}: I do not smile often. But {relations}/100 relations with Europa is worth smiling about. A military pact awaits.',
            'Few reach this level of trust with the DPRG. Fewer still know what becomes available when they do. You are about to find out.'
        ]
        message = dialogue_manager.get_unique_message('dprg', variants, context)
        return dialogue_manager.format_npc_message('dprg', title, message, stage_direction)

    # PRIORITY 3: USA very hostile - 10 variants (key scenario)
    if usa_relations < 25:
        stage_direction = '*steps from shadows*'
        variants = [
            'USA relations at {usa_rel}/100. They have shown their true face: domination or destruction. But I offer alternative. True independence.',
            "The Americans sanction you now, yes? Predictable. They call it 'diplomacy.' I call it imperialism. The DPRG offers real partnership.",
            'Hartwell squeezes. I do not. Pentagon threatens. I protect. This is simple mathematics, Europa. Choose survival.',
            'Your conflict with USA ({usa_rel}/100) opens doors. The enemy of America is friend of DPRG. Let us discuss... arrangements.',
            'Turn {turn}: USA at {usa_rel}/100. They chose this. I did not force this outcome. But I can help you survive it.',
            '*calculating* USA sanctions hurt at $2B per turn. My weapons cost $2B once. The math is interesting, yes?',
            'Turn {turn}: The Americans thought their sanctions would break you. I am here to ensure they do not.',
            'You resist USA alone. But you need not be alone. The DPRG has resisted Hartwell for decades. We know how.',
            'USA relations at {usa_rel}/100. When the West turns against you, you learn quickly who your real friends are.',
            'Turn {turn}: I have watched USA destroy nations with sanctions. I have also watched nations survive them. With help.'
        ]
        message = dialogue_manager.get_unique_message('dprg', variants, context)
        return dialogue_manager.format_npc_message('dprg', title, message, stage_direction)

    # PRIORITY 4: Turn-based - 8 variants each range
    if turn <= 2:
        stage_direction = '*cryptic smile*'
        variants = [
            'New nation, new vulnerabilities. The DPRG watches. When you need power others fear to provide... we talk.',
            'Welcome to the world stage, Europa. The Americans will offer hollow promises. I offer something more... tangible.',
            'Turn {turn}. Already the sharks circle. But I... I am patient. When you see their true faces, remember mine.',
            'Everyone offers you something in Turn {turn}. USA offers chains disguised as protection. I offer options.',
            'A new nation. How interesting. The West will try to capture you early. I simply wait and watch.',
            'Turn {turn}: You have many offers today. Consider which ones come with conditions... and which do not.',
            'The Americans rush to claim new nations. I am unhurried. The best partnerships develop naturally.',
            'Turn {turn}: Watch carefully how USA and EU treat you. When their masks slip, the DPRG will be here.'
        ]
    elif turn <= 4:
        stage_direction = '*observing*'
        variants = [
            'USA cannot protect you. Arabia cannot trust you. EU cannot truly help you. But I... I UNDERSTAND you.',
            'Turn {turn}. You navigate between powers that would consume you. Wise. But eventually you need allies who ask nothing impossible.',
            'The West speaks of values, principles, democracy. I speak of SURVIVAL. Which matters when your budget reaches zero?',
            'Turn {turn}: I have watched you make {turn} turns of decisions. I see the pattern. I see what you will need.',
            'Others offer you money and alliances. I offer you something rarer: honest assessment of your situation.',
            'Turn {turn}: The Americans grow impatient with you. I grow... interested. There is opportunity in their frustration.',
            'You balance carefully between powers. Admirable. But balance requires two stable points. Are both stable?',
            'Turn {turn}: I do not rush these things. But by now you have seen enough of the others to judge. Compare carefully.'
        ]
    elif turn <= 6:
        stage_direction = '*chuckles*'
        variants = [
            'Midgame already. Your tightrope act is... entertaining. But ropes break, Europa. What then? Have you considered alternatives?',
            'Turn {turn}. The Americans pressure. Arabia bribes. EU lectures. And I? I simply wait. Desperation finds me eventually.',
            'The West believes you will choose their way. They are arrogant. I know better. Power recognizes power.',
            'Turn {turn}: Six turns in and still dancing. Amusing. But every dance ends. When yours does, call me.',
            'You have survived longer than some expected without choosing sides fully. Interesting. It cannot last.',
            'Turn {turn}: My analysts say you will face a crisis soon. Budget pressure, perhaps. Or stability. I am prepared.',
            'Midgame. The desperate deals come in the endgame. But relationships must be built now, before you need them.',
            'Turn {turn}: Others underestimate the DPRG. You seem... less certain of that than most. Wise.'
        ]
    elif turn <= 8:
        stage_direction = '*steps closer*'
        variants = [
            "Final turns approach. The West's promises evaporate. My offers remain. Weapons. Money. Surveillance. Protection. Real power.",
            'Turn {turn}. After Turn 10, you are locked into your choices. Permanently. Have you considered ALL options?',
            'The endgame reveals true strength. USA has bluster. Arabia has oil. EU has paperwork. DPRG has WEAPONS. Choose.',
            'Turn {turn}: We are near the end. I step closer because distance is no longer appropriate between potential partners.',
            'Eight turns of watching. Now I speak plainly: the DPRG needs partners who understand realpolitik. You seem to.',
            'Turn {turn}: The West will offer you final warnings and final deals. I offer final honesty: they need you more than they admit.',
            'The endgame approaches and the masks come off. Watch the Americans in these final turns. Then call me.',
            'Turn {turn}: I have waited long enough to speak plainly. Partner with the DPRG and gain what the West will never give you.'
        ]
    else:
        stage_direction = '*final offer*'
        variants = [
            'This is it. Last turn. The West showed you their way: sanctions, pressure, conditions, judgment. I showed mine: power. Decide.',
            'Turn {turn} approaches the end. After this, history judges. Will they say Europa chose freedom or submission to imperialism?',
            'The end. My final offer stands. Accept or refuse - but know: the DPRG does not forget. Either friends... or irrelevant.',
            'Final turn. Every decision you made brought you here. What does HERE look like? Could the DPRG have helped sooner?',
            'Turn {turn}: Last chance. I have been patient for 10 turns. That patience ends with the game. Choose now.',
            'The endgame. I offered help when you were desperate. I offered alliance when you were strong. One more offer remains.',
            'Turn {turn}: After Turn 10 there are no more decisions. Only consequences. Make this last one count.',
            'This is the last turn. Whatever we are to each other - partners, strangers, enemies - is decided right now.'
        ]

    message = dialogue_manager.get_unique_message('dprg', variants, context)
    return dialogue_manager.format_npc_message('dprg', title, message, stage_direction)


def get_dprg_offer(game_state):
    """Generate DPRG's context-aware offer"""
    relations = game_state.relations['dprg']
    budget = game_state.budget
    stability = game_state.stability
    usa_relations = game_state.relations['usa']

    # ITEM 5: DPRG cross-NPC penalties are now handled by process_choice_consequences
    # (scaled by deal size), so USA/EU penalties are removed from static offers.
    if budget < 20 or stability < 35:
        return {'text': 'Accept DPRG emergency loan (+$10B, +10 stability, ⚠️ USA/EU furious)',
                'type': 'accept_deal', 'npc': 'dprg',
                'consequences': {'budget': 10, 'stability': 10, 'dprg': 20}}
    if relations > 60:
        return {'text': 'Form DPRG military pact (+stability, Military +10, ⚠️ USA/EU/Arabia furious)',
                'type': 'accept_deal', 'npc': 'dprg',
                'consequences': {'dprg': 15, 'stability': 12, 'military': 10, 'arabia': -8}}
    if usa_relations < 30:
        return {'text': 'Purchase DPRG weapons (costs $2B, Military +10, +stability, +10 heat, ⚠️ USA/EU angry)',
                'type': 'accept_deal', 'npc': 'dprg',
                'consequences': {'budget': -2, 'stability': 6, 'military': 10, 'heat': 10, 'dprg': 12}}
    return {'text': 'Acknowledge DPRG (+8 DPRG relations, ⚠️ USA/EU penalties)',
            'type': 'side_with', 'npc': 'dprg',
            'consequences': {'dprg': 8}}