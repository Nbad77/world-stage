"""
EU NPC - Idealistic, bureaucratic, lectures about values
EXPANDED POOLS - 8 variants per situation, uses get_unique_message()
"""


def get_eu_message(game_state, dialogue_manager):
    """Generate EU message - guaranteed unique every turn"""

    turn = game_state.current_turn
    relations = game_state.relations['eu']
    usa_relations = game_state.relations['usa']
    arabia_relations = game_state.relations['arabia']
    dprg_relations = game_state.relations['dprg']
    stability = game_state.stability

    context = {
        'turn': turn, 'relations': relations, 'usa_rel': usa_relations,
        'arabia_rel': arabia_relations, 'dprg_rel': dprg_relations, 'stability': stability
    }

    if stability < 45:
        title = 'EU (Emergency Session)'
    elif dprg_relations > 65:
        title = 'EU (Parliament)'
    elif turn >= 7:
        title = 'EU (Commission President)'
    elif turn >= 4:
        title = 'EU (Foreign Policy Chief)'
    else:
        title = 'EU (Diplomatic Communique)'

    # PRIORITY 1: Both USA and Arabia hostile - 8 variants
    if usa_relations < 30 and arabia_relations < 30:
        variants = [
            "Europa, you're surrounded by hostile powers. The EU can mediate before this escalates to full economic warfare.",
            'Alienating both Hartwell AND Arabia? This is untenable. We offer diplomatic mediation while you can still accept.',
            'The Commission is alarmed. You cannot survive with both superpowers as enemies. Let us negotiate on your behalf.',
            'Emergency session: Europa faces crisis on two fronts. EU mediation is your only path to de-escalation.',
            'Turn {turn}: USA at {usa_rel}, Arabia at {arabia_rel}. This is not diplomacy - this is catastrophe. Accept our help.',
            'Both superpowers are hostile and you are alone. The EU has relationships with both. Use them. Now.',
            'We warned you about this. The Commission said: do not alienate everyone. Now here we are. Let us fix this.',
            'Turn {turn}: Your independence is admirable. Your current situation is not. Accept EU mediation before it worsens.'
        ]
        message = dialogue_manager.get_unique_message('eu', variants, context)
        return dialogue_manager.format_npc_message('eu', title, message)

    # PRIORITY 2: DPRG relations too high - 8 variants
    if dprg_relations > 65:
        variants = [
            'Your relationship with the DPRG ({dprg_rel}/100) is unacceptable. The EU demands you distance yourself immediately.',
            'A European nation cannot be seen as allied with a rogue state. Cut DPRG ties or face sanctions from Brussels.',
            'Parliament is furious. DPRG relations at {dprg_rel}? This jeopardizes everything Europa has built with Europe.',
            'The DPRG represents everything the EU opposes. Your closeness with them betrays European values.',
            "Turn {turn}: {dprg_rel}/100 DPRG relations. The Council considers suspending Europa's observer status.",
            'Ji-won offers weapons and loans. We offer civilization, rule of law, and a prosperous future. Choose correctly.',
            'Turn {turn}: European nations do not consort with authoritarian regimes. This is non-negotiable.',
            'The Commission has issued a formal warning. Distance yourself from the DPRG or face institutional consequences.'
        ]
        message = dialogue_manager.get_unique_message('eu', variants, context)
        return dialogue_manager.format_npc_message('eu', title, message)

    # PRIORITY 3: Stability critical - 8 variants
    if stability < 45:
        variants = [
            'Your stability has collapsed to {stability}%. The EU offers emergency stabilization funds worth $4 billion.',
            "Emergency session: Europa's stability ({stability}%) threatens regional security. We provide immediate assistance.",
            'A destabilized Europa destabilizes all of Europe. The Commission authorizes emergency aid before your government falls.',
            'Stability at {stability}% is catastrophic. EU emergency protocols activated. Accept our aid package immediately.',
            "Turn {turn}: {stability}% stability. We did not want to say 'we told you so,' but... please accept our help.",
            'The Commission President herself has authorized this aid. {stability}% stability is a European emergency.',
            'Turn {turn}: Your instability affects our markets, our borders, our security. Accept aid - for our sake if not yours.',
            'Emergency funds are ready. {stability}% stability means you have days before collapse. Accept. Now.'
        ]
        message = dialogue_manager.get_unique_message('eu', variants, context)
        return dialogue_manager.format_npc_message('eu', title, message)

    # PRIORITY 4: Turn-based - 8 variants each range
    if turn <= 2:
        variants = [
            "Welcome, Europa. The EU watches with hope that you'll align with European values: democracy, human rights, rule of law.",
            'Early days yet. Remember: you are European first. Geographically, culturally, politically. The EU is your natural home.',
            'Turn {turn} and already the superpowers circle. The EU offers partnership without domination. Consider that carefully.',
            'Every new nation faces this choice: align with power, or align with values. We believe values endure longer.',
            'The Americans will offer military protection. Arabia will offer money. We offer something rarer: genuine partnership.',
            'Turn {turn}: Your first steps define your path. Walk toward European values and the door to our institutions opens.',
            'We have watched many nations make these early decisions. Those who chose European alignment prospered longest.',
            'Europa, you were always European before you were a nation. Remember that as the superpowers make their offers.'
        ]
    elif turn <= 4:
        variants = [
            'Turn {turn}. Your choices shape whether Europa will truly be PART of Europe, or merely adjacent to it.',
            "We note Europa's choices. Principled neutrality requires principles. Opportunistic neutrality is cowardice.",
            'The EU values consistency, transparency, democratic values. We have seen some of those from you. Not all.',
            'Turn {turn}: Your Arabia dealings concern us. Oil money is fleeting. European institutional membership endures.',
            'The Commission notes your pattern of behavior. We hoped for more European commitment by now.',
            'Turn {turn}: Four turns in and still no clear alignment. The Foreign Policy Chief asks: what does Europa want?',
            'We do not demand servility like the Americans, nor bribes like Arabia. We ask only for shared values.',
            'Your hesitation disappoints but does not surprise us. Many nations take time to find their European identity.'
        ]
    elif turn <= 6:
        variants = [
            "Midway through and Europa still hasn't committed to European values. The Council grows impatient.",
            'Turn {turn}. The Americans bully. Arabia bribes. But we PARTNER. When will you see which approach is sustainable?',
            "The world watches Europa's alignment. Will you stand with European brothers or chase oil money and Pentagon promises?",
            "Turn {turn}: Six turns and the Commission's patience thins. Demonstrate European commitment or lose our goodwill.",
            'Halfway through this crisis. Your Arabia oil deals grow our concern. Your DPRG flirtations grow our alarm.',
            'Turn {turn}: The Foreign Policy Chief presents your file to the Council monthly. The reports grow less favorable.',
            'Values are not luxuries for peaceful times. They are foundations for all times. Europa seems to have forgotten this.',
            'Turn {turn}: We offer stability, integration, prosperity, legitimacy. Arabia offers cash. Choose what lasts.'
        ]
    elif turn <= 8:
        variants = [
            "Turn {turn}. The endgame approaches. The EU's patience has limits. Demonstrate European commitment before it's too late.",
            "Final turns reveal true character. Will Europa's legacy be as a European nation or as something... else?",
            'The Council demands clarity. Are you European or opportunist? The time for ambiguity has passed.',
            'Turn {turn}: Eight turns of watching Europa navigate between values and money. The Commission makes its assessment.',
            "Final turns. The Commission President prepares Europa's formal classification. Help us classify you correctly.",
            'Turn {turn}: The window for EU integration is narrowing. After Turn 10, the institutional doors begin to close.',
            'We have offered partnership consistently for {turn} turns. Consistency from Europa would be appreciated in return.',
            "Turn {turn}: The Council votes on Europa's observer status next session. Your current trajectory concerns them."
        ]
    else:
        variants = [
            "Turn {turn} approaches the end. After this, Europa's place in Europe is decided for a generation. Choose wisely.",
            'This is the end. The EU has offered partnership for 10 turns. Will you accept, or remain forever outside?',
            'Final turn. After this, the history books close. Will they record Europa as European or as a cautionary tale?',
            'Turn {turn}: Last chance for European alignment. The Commission President personally extends this final invitation.',
            'The final turn. Ten opportunities to choose European values. Will the tenth be the one that counts?',
            "Turn {turn}: After this, we must formally classify Europa's relationship with EU institutions. Make it easy for us.",
            'The end approaches. We do not beg. We do not threaten. We simply ask, one final time: are you European?',
            'Turn {turn}: Whatever you decide now, you will live with for a generation. The EU has been patient. Choose well.'
        ]

    message = dialogue_manager.get_unique_message('eu', variants, context)
    return dialogue_manager.format_npc_message('eu', title, message)


def get_eu_offer(game_state):
    """Generate EU's context-aware offer"""
    turn = game_state.current_turn
    relations = game_state.relations['eu']
    usa_relations = game_state.relations['usa']
    arabia_relations = game_state.relations['arabia']
    stability = game_state.stability

    if stability < 45:
        return {'text': 'Accept EU emergency aid (+$4B, +15 stability, +10 EU relations)',
                'type': 'accept_deal', 'npc': 'eu',
                'consequences': {'budget': 4, 'stability': 15, 'eu': 10}}
    if usa_relations < 30 and arabia_relations < 30:
        return {'text': 'Accept EU mediation (costs $2B, +15 USA, +15 Arabia, +12 EU)',
                'type': 'accept_deal', 'npc': 'eu',
                'consequences': {'budget': -2, 'usa': 15, 'arabia': 15, 'eu': 12}}
    if relations > 65 and turn >= 6:
        return {'text': 'Begin EU integration (+stability, +budget, +20 EU relations)',
                'type': 'accept_deal', 'npc': 'eu',
                'consequences': {'eu': 20, 'stability': 10, 'budget': 3}}
    return {'text': 'Align with EU values (+3% stability, +12 EU relations)',
            'type': 'side_with', 'npc': 'eu',
            'consequences': {'eu': 12, 'stability': 3}}