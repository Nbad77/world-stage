"""
Arabia (Sadam) NPC - Transactional, theatrical, uses stage directions
EXPANDED POOLS - 8-10 variants per situation, uses get_unique_message()
"""


def get_arabia_message(game_state, dialogue_manager):
    """Generate Arabia message - guaranteed unique every turn"""

    turn = game_state.current_turn
    relations = game_state.relations['arabia']
    usa_relations = game_state.relations['usa']
    consecutive_sides = game_state.consecutive_sides['arabia']
    oil_price = game_state.oil_price
    budget = game_state.budget

    context = {
        'turn': turn, 'relations': relations, 'usa_rel': usa_relations,
        'consecutive': consecutive_sides, 'oil': oil_price, 'budget': budget
    }

    title = 'SADAM'

    if relations > 80:
        stage_direction = '*brotherhood embrace*'
    elif relations > 60:
        stage_direction = '*warm handshake*'
    elif relations > 40:
        stage_direction = '*smiling*'
    elif relations > 25:
        stage_direction = '*lighting cigar*'
    else:
        stage_direction = '*cold stare*'

    # PRIORITY 1: Active embargo - 10 variants
    if game_state.arabia_embargo_active:
        stage_direction = '*cold stare*'
        variants = [
            'You made your choice. Now you pay market price like everyone else. The embargo stands.',
            'Betrayal has consequences. My oil flows to those who show RESPECT. You are not among them.',
            'The embargo continues. Watch prices climb while others enjoy my generosity. This is what disloyalty earns.',
            'Turn {turn}: ${oil:.0f} per barrel and rising. The cost of insulting Sadam. Apologize, or suffer.',
            'Turn {turn}: Still no apology. The embargo tightens. Your economy feels every dollar of this stubbornness.',
            'I have sold your oil allocation to other buyers. They appreciate it. You will learn to appreciate me again.',
            "Every turn you wait costs you more. One leader's pride against one nation's pain. Is it worth it?",
            'Turn {turn}: Other nations queue for my oil at discounts. You pay full price. Reconsider your stubbornness.',
            'The embargo is not personal. It is mathematics. You insult, prices rise. You apologize, prices fall.',
            'Your industries slow. Your budget bleeds. Your people suffer. All because you chose wrong. Fascinating.'
        ]
        message = dialogue_manager.get_unique_message('arabia', variants, context)
        return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)

    # PRIORITY 2: Betrayal - 8 variants
    if game_state.took_arabia_oil and usa_relations > relations:
        stage_direction = '*slamming fist on table*'
        variants = [
            'You took my oil money then RAN to the Americans? I do not forget betrayal, Europa. Ever.',
            'I offered you partnership and wealth. You chose the Pentagon instead. This insult will cost you dearly.',
            'Sadam rewards loyalty and DESTROYS traitors. You showed me which you are. The embargo is just the beginning.',
            'Turn {turn}: You think taking my money then appeasing USA goes unnoticed? Sadam notices everything.',
            'My intelligence tells me everything. Every deal, every choice. You used me, Europa. That has a price.',
            'You feasted at my table then invited my enemies to dinner. This is not how civilization works.',
            'The oil money sits in your budget. USA approval sits in your heart. Your loyalty sits... nowhere.',
            'Turn {turn}: Every bird that bites the hand that fed it eventually starves. Think about what you have done.'
        ]
        message = dialogue_manager.get_unique_message('arabia', variants, context)
        return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)

    # PRIORITY 3: Loyalty reward (3+ consecutive) - 8 variants
    if consecutive_sides >= 3:
        stage_direction = '*pouring expensive whiskey*'
        variants = [
            '{consecutive} consecutive times you stand with Arabia! THIS is loyalty. Your account grows heavy, my friend.',
            'Three times and more you choose wisely. Unlike the Americans, Sadam REWARDS true friends. Drink with me.',
            'Consistency is rare in this world. You have shown it {consecutive} times now. The oil flows freely to you.',
            'Turn {turn}: {consecutive} turns of loyalty. I count each one. Your premium partnership terms are being prepared.',
            '*counting on fingers* One, two, three... {consecutive} times you stand firm. A man of your word.',
            'The Americans demand loyalty but give nothing. I demand nothing and give everything. You chose correctly {consecutive} times.',
            "Turn {turn}: {consecutive} straight decisions in Arabia's favor. The investment I prepare will reward this.",
            'Brothers in defiance. {consecutive} times you proved it. Let Washington rage. We prosper regardless.'
        ]
        message = dialogue_manager.get_unique_message('arabia', variants, context)
        return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)

    # PRIORITY 4: USA hostile to player - 10 variants
    if usa_relations < 30:
        stage_direction = '*leaning forward*'
        variants = [
            'USA sanctions hurt. My oil deals heal. The choice: poverty with principles, or prosperity with pragmatism.',
            'I see USA threatens you. They are predictable - sanctions, pressure, ultimatums. But I... I offer WEALTH.',
            '*counting money* Turn {turn}. Your budget grows fat on my oil while Washington seethes. Beautiful.',
            "The Americans squeeze you, yes? Let them try. Arabia's vaults are deeper than Pentagon's patience.",
            "You've chosen wisely, Europa. My oil flows, your economy grows, USA rages. A perfect arrangement.",
            'Turn {turn} and still they sanction you for doing business with me. Their arrogance is breathtaking.',
            'Every turn you resist USA, I reward you. Every turn you comply, they demand more. Simple mathematics.',
            '*warm smile* Brothers in defiance. Let Washington impose their pressure. We have oil, money, and time.',
            'USA relations at {usa_rel}/100. They chose confrontation. I choose commerce. Which fills your treasury?',
            'Turn {turn}: Americans call our deal illegitimate. Yet your budget is healthier than ever. Who is right?'
        ]
        message = dialogue_manager.get_unique_message('arabia', variants, context)
        return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)

    # PRIORITY 5: High relations - 8 variants
    if relations > 70:
        stage_direction = '*generous gesture*'
        variants = [
            'Relations at {relations}! You understand the oil business. I offer premium partnership: $8 billion investment.',
            'You have proven trustworthy. Rare in this world. I offer what I offer almost no one: exclusive access.',
            'The Americans lecture. The EU bureaucratizes. But you and I? We make DEALS. Real power is economic power.',
            'Turn {turn}: {relations}/100 relations. My economists have prepared something special for our most valued partner.',
            'Trusted friend, the premium terms are yours. Other nations beg for what I give you freely.',
            '*spreading hands* What is mine is yours, my friend. {relations}/100 - this is brotherhood, not business.',
            'Turn {turn}: Your loyalty has made you wealthy. This is how partnerships should work. More to come.',
            'I have turned down American pressure and EU lectures to protect our arrangement. It was worth it.'
        ]
        message = dialogue_manager.get_unique_message('arabia', variants, context)
        return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)

    # PRIORITY 6: Turn-based - 8 variants each range
    if turn <= 2:
        stage_direction = '*lighting cigar*'
        variants = [
            'New nation, new opportunities. Arabia has oil. You need oil. The math is simple. Shall we negotiate?',
            'Welcome to the world stage, Europa. The Americans will offer protection. I offer something better: MONEY.',
            'Turn {turn} wisdom: everyone needs energy. I control the energy. Smart leaders become my friends early.',
            'Every great nation was built on energy. I have energy. You have ambition. This is a beautiful beginning.',
            'The Americans came with demands. The EU came with regulations. You simply need oil. Refreshing honesty.',
            'Turn {turn}: No history between us, no grudges. A clean slate and full oil reserves. Let us begin.',
            'I have watched new nations rise and fall. Those that thrived secured their energy on day one.',
            'You are new to this game, Europa. Advice: secure your oil first. Everything else follows naturally.'
        ]
    elif turn <= 4:
        stage_direction = '*studying you*'
        variants = [
            'I see Europa takes my oil but hesitates on commitment. The Americans pressure you. I can offer MORE.',
            'Turn {turn}. Still playing both sides? Cute. But eventually you must choose. I pay better than Pentagon promises.',
            'You dance between USA and Arabia. Entertaining. But the music stops, and you must sit at ONE table.',
            'Turn {turn}: I have studied your decisions carefully. You are cautious. Cautious leaders survive. Loyal ones thrive.',
            'My patience is considerable but not infinite. Show me where you truly stand before it runs out.',
            'Americans watch your Arabia deals with suspicion. I watch your American flirtations with amusement. Choose.',
            'Turn {turn}: Your hesitation costs you premium deals. Commit to Arabia and see what becomes available.',
            'Half-partnerships benefit no one. Either you are my business partner or you are not. Which is it?'
        ]
    elif turn <= 6:
        stage_direction = '*tapping fingers*'
        variants = [
            'Halfway through your experiment in leadership. I notice everything - every deal, every hesitation.',
            'The Americans threaten. I simply do business. But my patience has limits. Show commitment or watch prices rise.',
            'Turn {turn}. Your EU friends lecture about values. Can values fill your treasury? Can principles power your economy?',
            'Turn {turn}: Six turns in and I have learned much about you. More than you realize.',
            'Midgame. The desperate deals come later. Right now I offer generous terms. Generous terms expire.',
            'You have taken my oil and hesitated on loyalty. Acceptable for now. My generosity has a timer.',
            'Turn {turn}: Other leaders who sat where you sit chose Arabia. They are wealthy. Those who chose USA? Ask them.',
            "The tightrope grows thinner with each turn. Commit to one side or fall. Sadam's law of politics."
        ]
    elif turn <= 8:
        stage_direction = '*serious tone*'
        variants = [
            "The endgame approaches. Those who stood with Sadam will remember fondly. Those who didn't... will also remember.",
            'Final turns reveal true colors. I showed you mine: wealth, oil, pragmatism. What will you show me?',
            'Turn {turn}. After Turn 10, history is written. Will they say Europa was wise... or merely lucky?',
            'Turn {turn}: We near the end. The deals I offer now are the last generous ones. Take them or regret.',
            'Eight turns. I watched you navigate carefully. Now I ask for clarity: are we partners or not?',
            'My final generous offers are on the table, Europa. After Turn 10, terms become... standard.',
            'Turn {turn}: Every nation that allied with me in the final turns secured prosperity. Consider that.',
            'The endgame favors those who chose early. But late commitment still beats none. Your call.'
        ]
    else:
        stage_direction = '*final offer*'
        variants = [
            'This is it. Last chances evaporate like desert water. Choose Arabian wealth or American poverty. NOW.',
            'Turn {turn}: I have been patient. I have been generous. What I offer next depends on your choice here.',
            'The end. After this, deals are permanent. Alliances are locked. Choose carefully. This is your legacy.',
            'Final turn. Every barrel of oil, every billion in investment - decided right now. Choose.',
            'Turn {turn}: The last page of our story. Will it end as partners who prospered, or something less?',
            'I close my ledger after Turn 10. Your account with Arabia is profitable or closed. Permanently.',
            'This is my final offer. Not generosity - there are simply no more turns for second chances.',
            'Turn {turn}: History records whether Europa chose wealth and partnership, or lectures and poverty. Write it now.'
        ]

    message = dialogue_manager.get_unique_message('arabia', variants, context)
    return dialogue_manager.format_npc_message('arabia', title, message, stage_direction)


def get_arabia_offer(game_state):
    """Generate Arabia's context-aware offer"""
    relations = game_state.relations['arabia']
    turn = game_state.current_turn

    if game_state.arabia_embargo_active:
        return {'text': 'Apologize to Arabia (costs $4B, removes embargo, +25 relations)',
                'type': 'accept_deal', 'npc': 'arabia',
                'consequences': {'budget': -4, 'arabia': 25, 'special': 'remove_embargo'}}
    if relations > 70:
        return {'text': 'Accept Arabia premium partnership (+$12B, oil -$15, USA/EU very angry)',
                'type': 'accept_deal', 'npc': 'arabia',
                'consequences': {'budget': 12, 'oil_price': -15, 'arabia': 15, 'usa': -25, 'eu': -15}}
    if turn >= 4 and relations >= 45:
        return {'text': 'Accept Arabia enhanced oil deal (+$8B, oil -$10, USA -15)',
                'type': 'accept_deal', 'npc': 'arabia',
                'consequences': {'budget': 8, 'oil_price': -10, 'arabia': 12, 'usa': -15, 'special': 'took_arabia_oil'}}
    return {'text': 'Accept Arabia oil deal (+$5B, oil -$5, USA -10)',
            'type': 'accept_deal', 'npc': 'arabia',
            'consequences': {'budget': 5, 'oil_price': -5, 'arabia': 10, 'usa': -10, 'special': 'took_arabia_oil'}}
