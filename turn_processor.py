"""
Turn Processor - Handles consequences, end-of-turn effects, game over detection
VERSION 3: Tiered sanctions/embargo/pressure, passive drain, approval system, legacy titles
"""

import random


def process_choice_consequences(game_state, choice):
    """Apply immediate consequences from player choice, including approval changes"""

    consequences = choice.get('consequences', {})
    messages = []

    # Relations changes
    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        if npc in consequences:
            old = game_state.relations[npc]
            game_state.update_relations(npc, consequences[npc])
            new = game_state.relations[npc]
            direction = "↑" if consequences[npc] > 0 else "↓"
            messages.append(f"{direction} {npc.upper()}: {old} → {new} ({consequences[npc]:+d})")

    # Budget
    if 'budget' in consequences:
        old = game_state.budget
        game_state.update_budget(consequences['budget'])
        direction = "↑" if consequences['budget'] > 0 else "↓"
        messages.append(f"{direction} Budget: ${old:.1f}B → ${game_state.budget:.1f}B ({consequences['budget']:+.1f}B)")

    # Stability
    if 'stability' in consequences:
        old = game_state.stability
        game_state.update_stability(consequences['stability'])
        direction = "↑" if consequences['stability'] > 0 else "↓"
        messages.append(f"{direction} Stability: {old}% → {game_state.stability}% ({consequences['stability']:+d}%)")

    # Oil price consequences from deals — register as a persistent modifier so EOT
    # recalculation doesn't wipe the effect. Negative = cheaper oil for player.
    # Default duration: 3 turns (the deal lasts a while, not just one turn).
    if 'oil_price' in consequences:
        oil_delta = consequences['oil_price']
        arabia_delta = consequences.get('arabia', 0)
        if oil_delta != 0:
            duration = consequences.get('oil_price_turns', 3)
            npc = consequences.get('_npc', 'deal')  # set by caller if available
            desc = f"{npc} oil deal"
            game_state.oil_price_modifiers.append({
                "delta": float(oil_delta),
                "turns_remaining": int(duration),
                "description": desc,
            })
            sign = '+' if oil_delta > 0 else ''
            messages.append(
                f"🛢️  Oil deal locked in: {sign}${oil_delta:.0f}/bbl for {duration} turns"
            )
        else:
            # Pure relation change — no direct oil modifier, just note it
            if arabia_delta > 0:
                messages.append("🛢️  Arabia relations improved — oil prices will reflect this next turn")
            elif arabia_delta < 0:
                messages.append("🛢️  Arabia relations worsened — oil prices will reflect this next turn")

    # Special flags
    if 'special' in consequences:
        special = consequences['special']

        if special == 'remove_sanctions':
            game_state.usa_sanctions_active = False
            game_state.usa_sanctions_tier = 0
            # Ensure payment lifts relations clear of Tier 1 threshold.
            # We need the pre-floor value to compute the correct display delta.
            pre_floor = game_state.relations['usa']  # already has raw +25 applied
            new_usa_rel = max(pre_floor, 40)
            game_state.relations['usa'] = min(100, new_usa_rel)
            final_rel = game_state.relations['usa']
            # The relations loop already appended a stale "↑ USA: X → Y (+25)" line.
            # Find it and replace it with the corrected values.
            for i, m in enumerate(messages):
                if m.startswith("↑ USA:") or m.startswith("↓ USA:"):
                    # Reconstruct with the true before (pre_floor minus the raw +25 delta)
                    before = pre_floor - consequences.get('usa', 25)
                    actual_delta = final_rel - before
                    messages[i] = f"↑ USA: {before} → {final_rel} (+{actual_delta})"
                    break
            game_state.update_approval(10)
            messages.append(f"✅ Sanctions lifted (relations set to minimum {final_rel}). Public relief: +10% approval")

        elif special == 'remove_embargo':
            game_state.arabia_embargo_active = False
            messages.append("✅ Arabia embargo lifted!")

        elif special == 'took_arabia_oil':
            game_state.took_arabia_oil = True
            messages.append("📝 Arabia oil deal recorded")

    # Approval changes based on the NPC sided with
    npc = choice.get('npc')
    choice_type = choice.get('type')

    if choice_type in ('accept_deal', 'side_with') and npc:
        if npc == 'usa':
            game_state.update_approval(5)
            game_state.update_budget(3.0)
            messages.append("📊 Public approval: +5% (US alignment)")
            messages.append("💰 US investment: +$3B")
        elif npc == 'arabia':
            # Arabia oil deals cheapen energy — people like that
            game_state.update_approval(8)
            messages.append("📊 Public approval: +8% (cheaper oil)")
        elif npc == 'eu':
            game_state.update_approval(6)
            game_state.update_budget(4.0)
            messages.append("📊 Public approval: +6% (EU alignment)")
            messages.append("💰 EU trade benefit: +$4B")
        elif npc == 'dprg':
            # DPRG deals are deeply unpopular domestically
            game_state.update_approval(-10)
            messages.append("📊 Public approval: -10% (DPRG backlash)")

    return messages


def apply_end_of_turn_effects(game_state):
    """Apply automatic effects at end of turn - full tiered system v4"""

    messages = []

    # ──────────────────────────────────────────
    # 1. OIL PRICE — recalculate from Arabia relations (or use negotiated lock),
    # then add embargo tier penalty.
    # Tier penalty is INCLUDED in final_oil so oil imports reflect it correctly.
    # Tier 0: +$0  Tier 1: +$10  Tier 2: +$20  Tier 3: +$35  Tier 4: +$50
    # ──────────────────────────────────────────

    # BUG 3: Check for a negotiated oil price lock before recalculating from relations
    if game_state.oil_price_locked and game_state.oil_price_lock_turns_remaining > 0:
        game_state.oil_price = max(20, round(game_state.oil_price_lock_value))
        game_state.oil_price_lock_turns_remaining -= 1
        if game_state.oil_price_lock_turns_remaining <= 0:
            game_state.oil_price_locked = False
            messages.append(
                f"🔓 Negotiated oil price lock expired — market rates resume next turn"
            )
        else:
            messages.append(
                f"🔒 Oil price locked at ${game_state.oil_price_lock_value:.0f}/bbl "
                f"({game_state.oil_price_lock_turns_remaining} turn(s) remaining)"
            )
    else:
        game_state.set_oil_price_from_relations()   # sets base from relations

    # Apply persistent oil price modifiers (world events, negotiated discounts)
    # These stack on top of the relation-based price and tick down each EOT.
    if game_state.oil_price_modifiers:
        still_active = []
        total_modifier = 0
        for mod in game_state.oil_price_modifiers:
            mod['turns_remaining'] -= 1
            total_modifier += mod['delta']
            remaining = mod['turns_remaining']
            desc = mod.get('description', 'oil modifier')
            sign = '+' if mod['delta'] > 0 else ''
            if remaining > 0:
                still_active.append(mod)
                messages.append(
                    f"🛢️  Oil modifier active: {sign}${mod['delta']:.0f}/bbl ({desc}, "
                    f"{remaining} turn(s) remaining)"
                )
            else:
                messages.append(
                    f"🛢️  Oil modifier expired: {sign}${mod['delta']:.0f}/bbl ({desc} — concluded)"
                )
        game_state.oil_price_modifiers = still_active
        # Apply the combined modifier to this turn's price, floor at $20
        if total_modifier != 0:
            game_state.oil_price = max(20, round(game_state.oil_price + total_modifier))

    # Tick down active trade commitments and remove expired ones
    if game_state.active_trade_commitments:
        still_active = []
        for commitment in game_state.active_trade_commitments:
            commitment['turns_remaining'] -= 1
            if commitment['turns_remaining'] > 0:
                still_active.append(commitment)
                messages.append(
                    f"🤝 Trade commitment active ({commitment['turns_remaining']} turn(s) left): "
                    f"{commitment['description']}"
                )
            else:
                messages.append(f"🤝 Trade commitment concluded: {commitment['description']}")
        game_state.active_trade_commitments = still_active

    # BUG 2: Apply active installment payments and tick them down
    if game_state.active_installments:
        still_active = []
        for inst in game_state.active_installments:
            amount = float(inst.get('amount', 0))
            inst['turns_remaining'] -= 1
            remaining = inst['turns_remaining']
            desc = inst.get('description', 'installment')

            # Apply the payment this turn
            game_state.update_budget(amount)
            direction = "↑" if amount > 0 else "↓"
            direction_word = "received" if amount > 0 else "paid"

            if remaining > 0:
                still_active.append(inst)
                messages.append(
                    f"📋 Installment {direction_word}: {direction}${abs(amount):.1f}B ({desc}, "
                    f"{remaining} turn(s) remaining)"
                )
            else:
                messages.append(
                    f"📋 Final installment {direction_word}: {direction}${abs(amount):.1f}B ({desc} — concluded)"
                )
        game_state.active_installments = still_active

    arabia_rel = game_state.relations['arabia']

    # Determine Arabia embargo tier for oil penalty (ramp-limited below in step 5)
    # We need to know the tier BEFORE charging imports, so calculate it now.
    if arabia_rel <= 35:
        if arabia_rel <= 4:
            _arabia_target_tier = 4
        elif arabia_rel <= 14:
            _arabia_target_tier = 3
        elif arabia_rel <= 24:
            _arabia_target_tier = 2
        else:
            _arabia_target_tier = 1
        _arabia_effective_tier = min(_arabia_target_tier, game_state.arabia_embargo_tier + 1)
    else:
        _arabia_effective_tier = 0

    _tier_oil_penalty = {0: 0, 1: 10, 2: 20, 3: 35, 4: 50}[_arabia_effective_tier]
    final_oil = game_state.oil_price + _tier_oil_penalty
    game_state.oil_price = max(20, final_oil)   # apply penalty into actual price

    if _tier_oil_penalty > 0:
        messages.append(f"🛢️  Oil price: ${game_state.oil_price:.0f}/barrel (Arabia hostile +${_tier_oil_penalty})")
    else:
        messages.append(f"🛢️  Oil price (Arabia {arabia_rel}/100): ${game_state.oil_price:.0f}/barrel")

    # ──────────────────────────────────────────
    # 2. PASSIVE BUDGET DRAIN
    # ──────────────────────────────────────────
    base_cost = 3.0  # Government operations
    oil_cost = round(game_state.oil_price / 15.0, 1)  # Oil imports at final price
    total_drain = base_cost + oil_cost

    game_state.update_budget(-base_cost)
    game_state.update_budget(-oil_cost)

    messages.append(f"🏛️  Government costs: -${base_cost:.1f}B")
    messages.append(f"⛽ Oil imports (${game_state.oil_price:.0f}/barrel): -${oil_cost:.1f}B")
    messages.append(f"💰 Passive drain this turn: -${total_drain:.1f}B")

    # ──────────────────────────────────────────
    # 3. SNAPSHOT RELATIONS for crisis logic
    # ──────────────────────────────────────────
    usa_rel = game_state.relations['usa']
    eu_rel = game_state.relations['eu']

    # Dual crisis multiplier: USA AND Arabia both hostile
    dual_crisis = (usa_rel < 30 and arabia_rel < 30)
    crisis_mult = 1.5 if dual_crisis else 1.0

    if dual_crisis:
        messages.append("⚠️  DUAL CRISIS: USA + Arabia both hostile — all crisis costs ×1.5!")

    # ──────────────────────────────────────────
    # 4. USA SANCTIONS — 4 TIERS (ramp-limited: max +1 tier per turn)
    # Tier 0: relations > 35  — no sanctions
    # Tier 1: relations 25-35 — -$2B, -3% approval
    # Tier 2: relations 15-24 — -$4B, -6% approval
    # Tier 3: relations 5-14  — -$7B, -9% approval, -6% stability, EU -3
    # Tier 4: relations 0-4   — -$10B, -12% approval, -9% stability, EU -5
    # ──────────────────────────────────────────
    if usa_rel <= 35:
        # Determine target tier from relations
        if usa_rel <= 4:
            target_tier = 4
        elif usa_rel <= 14:
            target_tier = 3
        elif usa_rel <= 24:
            target_tier = 2
        else:
            target_tier = 1

        # Ramp limit: can go up only one tier per turn; can drop freely.
        # Exception: if post-consequence relations have hit the floor (<=4,
        # i.e. Tier 4 territory), apply Tier 4 immediately regardless of
        # previous tier — a single diplomatic choice can collapse relations
        # to 0 and should not be shielded by the ramp.
        prev_tier = game_state.usa_sanctions_tier
        if usa_rel <= 4 and prev_tier < 4:
            # Relations collapsed to floor this turn — bypass ramp
            effective_tier = 4
        else:
            effective_tier = min(target_tier, prev_tier + 1)
        game_state.usa_sanctions_tier = effective_tier

        if effective_tier == 4:
            budget_hit = round(10 * crisis_mult)
            approval_hit = 12
            stability_hit = 9
            eu_hit = -5
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            game_state.update_relations('eu', eu_hit)
            messages.append(f"🇺🇸 USA SANCTIONS TIER 4 (rel {usa_rel}): -${budget_hit}B, -{approval_hit}% approval, -{stability_hit}% stability, EU {eu_hit}")

        elif effective_tier == 3:
            budget_hit = round(7 * crisis_mult)
            approval_hit = 9
            stability_hit = 6
            eu_hit = -3
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            game_state.update_relations('eu', eu_hit)
            messages.append(f"🇺🇸 USA SANCTIONS TIER 3 (rel {usa_rel}): -${budget_hit}B, -{approval_hit}% approval, -{stability_hit}% stability, EU {eu_hit}")

        elif effective_tier == 2:
            budget_hit = round(4 * crisis_mult)
            approval_hit = 6
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            messages.append(f"🇺🇸 USA SANCTIONS TIER 2 (rel {usa_rel}): -${budget_hit}B, -{approval_hit}% approval")

        elif effective_tier == 1:
            budget_hit = round(2 * crisis_mult)
            approval_hit = 3
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            messages.append(f"🇺🇸 USA SANCTIONS TIER 1 (rel {usa_rel}): -${budget_hit}B, -{approval_hit}% approval")

    else:
        # Relations healthy — reset tier tracker so it ramps up from 0 if they deteriorate
        game_state.usa_sanctions_tier = 0

    # ──────────────────────────────────────────
    # 5. ARABIA EMBARGO — 4 TIERS, ramp-limited
    # Oil price penalty already applied in step 1.
    # This step: commit the effective tier, apply approval/stability/emergency costs.
    # ──────────────────────────────────────────
    if arabia_rel <= 35:
        # _arabia_effective_tier already calculated in step 1
        game_state.arabia_embargo_tier = _arabia_effective_tier

        if _arabia_effective_tier == 4:
            approval_hit = 12
            stability_hit = 9
            emergency_cost = round(5 * crisis_mult)
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            game_state.update_budget(-emergency_cost)
            messages.append(f"🛢️  ARABIA EMBARGO TIER 4: -{approval_hit}% approval, -{stability_hit}% stability, -${emergency_cost}B emergency imports")

        elif _arabia_effective_tier == 3:
            approval_hit = 9
            stability_hit = 6
            emergency_cost = round(3 * crisis_mult)
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            game_state.update_budget(-emergency_cost)
            messages.append(f"🛢️  ARABIA EMBARGO TIER 3: -{approval_hit}% approval, -{stability_hit}% stability, -${emergency_cost}B emergency cost")

        elif _arabia_effective_tier == 2:
            approval_hit = 6
            stability_hit = 3
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            messages.append(f"🛢️  ARABIA PRICE SQUEEZE TIER 2: -{approval_hit}% approval, -{stability_hit}% stability")

        elif _arabia_effective_tier == 1:
            approval_hit = 3
            game_state.update_approval(-approval_hit)
            messages.append(f"🛢️  ARABIA PRICE SQUEEZE TIER 1: -{approval_hit}% approval")

    else:
        # Relations healthy — reset embargo tier tracker
        game_state.arabia_embargo_tier = 0

    # ──────────────────────────────────────────
    # 6. EU PRESSURE — 2 TIERS
    # Tier 1: relations 20-35 — -$2B, -2% approval
    # Tier 2: relations 0-19  — -$4B, -5% approval, -3% stability
    # ──────────────────────────────────────────
    if eu_rel < 36:
        if eu_rel <= 19:
            budget_hit = round(4 * crisis_mult)
            approval_hit = 5
            stability_hit = 3
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            game_state.update_stability(-stability_hit)
            messages.append(f"🇪🇺 EU TRADE RESTRICTIONS TIER 2 (rel {eu_rel}): -${budget_hit}B, -{approval_hit}% approval, -{stability_hit}% stability")
        else:
            budget_hit = round(2 * crisis_mult)
            approval_hit = 2
            game_state.update_budget(-budget_hit)
            game_state.update_approval(-approval_hit)
            messages.append(f"🇪🇺 EU TRADE FRICTION TIER 1 (rel {eu_rel}): -${budget_hit}B, -{approval_hit}% approval")

    # ──────────────────────────────────────────
    # 7. PASSIVE APPROVAL CHANGES (stability-based)
    # ──────────────────────────────────────────
    if game_state.stability >= 70:
        game_state.update_approval(3)
        messages.append("👥 High stability: +3% approval")
    elif game_state.stability < 40:
        game_state.update_approval(-5)
        messages.append(f"👥 Instability ({game_state.stability}%): -5% approval")

    # ──────────────────────────────────────────
    # 8. APPROVAL → STABILITY DRIFT
    # ──────────────────────────────────────────
    difference = game_state.public_approval - game_state.stability
    drift = round(difference * 0.3)

    if drift != 0:
        old_stab = game_state.stability
        game_state.update_stability(drift)
        direction = "↑" if drift > 0 else "↓"
        messages.append(f"📈 Approval drift: stability {old_stab}% → {game_state.stability}% ({direction}{abs(drift)}%)")

    # ──────────────────────────────────────────
    # 9. LOW BUDGET CRISIS
    # ──────────────────────────────────────────
    if 0 < game_state.budget < 7:
        game_state.update_stability(-3)
        game_state.update_approval(-5)
        messages.append(f"📉 Low budget (${game_state.budget:.1f}B): -3% stability, -5% approval")

    # ──────────────────────────────────────────
    # 10. SMALL RANDOM OIL FLUCTUATION (±$3)
    # ──────────────────────────────────────────
    fluctuation = random.randint(-3, 3)
    if fluctuation != 0:
        old = game_state.oil_price
        game_state.update_oil_price(fluctuation)
        if game_state.oil_price == 20 and old + fluctuation < 20:
            messages.append(f"🛢️  Oil markets: $20 floor enforced (was ${old:.0f})")
        else:
            direction = "↑" if fluctuation > 0 else "↓"
            messages.append(f"🛢️  Oil market noise: ${old:.0f} → ${game_state.oil_price:.0f}/barrel ({direction})")

    return messages


def get_personal_outcome(nation_survived, personal_wealth):
    """Return (title, description) based on national outcome and personal wealth.
    Victory titles: >=30B Perfect Operator, 15-30B Clever Tyrant, 5-15B Pragmatic Leader, <5B True Patriot
    Defeat titles:  >=25B Escaped Dictator, 10-25B Failed Opportunist, <10B Tragic Idealist
    """
    pw = personal_wealth
    if nation_survived:
        if pw >= 30:
            return (
                "The Perfect Operator",
                f"Europa survives AND your Swiss account holds ${pw:.1f}B.\n"
                "  You played the system with surgical precision.\n"
                "  The nation is intact. You are untouchable."
            )
        elif pw >= 15:
            return (
                "The Clever Tyrant",
                f"Europa endures. So does your Swiss account (${pw:.1f}B).\n"
                "  History will call you corrupt. You will not care. You are rich."
            )
        elif pw >= 5:
            return (
                "The Pragmatic Leader",
                f"You kept ${pw:.1f}B for yourself without breaking the nation.\n"
                "  The classic compromise of power."
            )
        else:
            return (
                "The True Patriot",
                "You took nothing for yourself. Europa is stronger for it.\n"
                "  You are not richer. You are something rarer."
            )
    else:
        if pw >= 25:
            return (
                "The Escaped Dictator",
                f"Europa collapsed. You fled with ${pw:.1f}B.\n"
                "  Ji-won arranged the plane. You are drinking wine somewhere.\n"
                "  Europa is not."
            )
        elif pw >= 10:
            return (
                "The Failed Opportunist",
                f"You tried to have it both ways. The nation fell.\n"
                f"  Your ${pw:.1f}B cushions the landing. Somewhat."
            )
        else:
            return (
                "The Tragic Idealist",
                "You stayed clean while the nation collapsed around you.\n"
                "  Noble. Useless."
            )


def get_legacy_title(game_state):
    """Determine legacy title based on final relationship scores"""

    usa = game_state.relations['usa']
    arabia = game_state.relations['arabia']
    eu = game_state.relations['eu']
    dprg = game_state.relations['dprg']

    # Check dominant relationship patterns
    if usa >= 70 and arabia < 30:
        return "Washington's Faithful Ally", "You chose the American orbit above all else. Some call it safety. Others call it submission."
    if arabia >= 70 and usa < 30:
        return "The Oil King's Partner", "You bet on black gold and Sadam's handshake. Europa's economy ran on Arabic generosity."
    if eu >= 70 and usa >= 40 and arabia >= 40:
        return "The European", "You walked the European path with integrity. Brussels will remember you fondly."
    if dprg >= 60 and (usa < 40 or eu < 40):
        return "The Pariah", "Ji-won's influence runs deep in your nation. The West will not forget. Neither will history."
    if all(40 <= r <= 70 for r in [usa, arabia, eu, dprg]):
        return "The Great Balancer", "No one fully trusted you. No one fully hated you. In geopolitics, that might be the highest art."
    if all(r < 40 for r in [usa, arabia, eu, dprg]):
        return "The Lone Wolf", "You angered everyone and answered to no one. Lonely, yes. Principled? Perhaps."
    if usa >= 60 and eu >= 60:
        return "The Transatlantic Bridge", "You kept Western unity alive. A rare achievement in a fractured world."
    if arabia >= 60 and eu >= 60:
        return "The Mediterranean Pragmatist", "Oil money AND European values. A difficult balance — one you managed."
    if usa >= 55 and arabia >= 55:
        return "The Opportunist", "You played both superpowers masterfully. Whether that's wisdom or betrayal depends who you ask."
    # Default
    return "The Survivor", "Against all odds, Europa endures. Sometimes that is enough."


def get_escape_ending(game_state):
    """Generate the Ji-won escape ending screen (Option F chosen)."""
    pw = game_state.personal_wealth
    msg = f"""
{'='*60}
✈️  THE ESCAPED ARCHITECT ✈️
{'='*60}

Ji-won's people moved quickly. A private charter, three
passports, and a discreet flight path. By the time Europa's
parliament convened an emergency session, you were gone.

The nation you led is still standing — for now.
Whether it continues to stand is no longer your problem.

DEPARTURE SUMMARY:
  National Budget:   ${game_state.budget:.1f}B  (left behind)
  Personal Account:  ${pw:.1f}B  (in transit with you)
  Stability:         {game_state.stability}%
  Turn of Departure: {game_state.current_turn}/{game_state.max_turns}

FINAL RELATIONS AT DEPARTURE:
  🇺🇸 USA:    {game_state.relations['usa']}/100
  🛢️  Arabia: {game_state.relations['arabia']}/100
  🇪🇺 EU:     {game_state.relations['eu']}/100
  ⚡ DPRG:   {game_state.relations['dprg']}/100  ← arranged the exit

{'─'*60}
LEGACY — ✦ The Escaped Architect ✦
  Personal Wealth: ${pw:.1f}B

  You saw the writing on the wall before the wall fell.
  Europa will call you a traitor. Interpol will call you a fugitive.
  Ji-won will call you a client.
  You will call yourself: alive.
{'='*60}
"""
    return msg


def check_game_over(game_state):
    """Check win/loss conditions - returns (is_over, result, message)"""

    pw = game_state.personal_wealth

    # Defeat: bankruptcy
    if game_state.budget <= 0:
        p_title, p_desc = get_personal_outcome(False, pw)
        msg = f"""
{'='*60}
💀 BANKRUPTCY — GAME OVER 💀
{'='*60}

Europa's treasury has run dry. ${game_state.budget:.1f}B.
The government cannot pay its bills. Civil services collapse.
Workers go unpaid. The streets fill with protest.

CAUSE OF DEFEAT: Financial mismanagement / hostile economic pressure

FINAL STATE:
  Budget:    ${game_state.budget:.1f}B  ← BANKRUPT
  Stability:  {game_state.stability}%
  Approval:   {game_state.public_approval}%
  Turn:       {game_state.current_turn}/{game_state.max_turns}

FINAL RELATIONS:
  🇺🇸 USA:    {game_state.relations['usa']}/100
  🛢️  Arabia: {game_state.relations['arabia']}/100
  🇪🇺 EU:     {game_state.relations['eu']}/100
  ⚡ DPRG:   {game_state.relations['dprg']}/100

{'─'*60}
LEGACY — ✦ {p_title} ✦
  Personal Wealth: ${pw:.1f}B

  {p_desc}
{'='*60}
"""
        return (True, 'defeat', msg)

    # Defeat: collapse
    if game_state.stability <= 0:
        p_title, p_desc = get_personal_outcome(False, pw)
        msg = f"""
{'='*60}
💀 GOVERNMENT COLLAPSE — GAME OVER 💀
{'='*60}

Stability has reached {game_state.stability}%. The government falls.
Protests turn to riots. The military refuses orders.
Europa fractures into chaos.

CAUSE OF DEFEAT: Political instability / approval collapse

FINAL STATE:
  Budget:    ${game_state.budget:.1f}B
  Stability:  {game_state.stability}%  ← COLLAPSED
  Approval:   {game_state.public_approval}%
  Turn:       {game_state.current_turn}/{game_state.max_turns}

FINAL RELATIONS:
  🇺🇸 USA:    {game_state.relations['usa']}/100
  🛢️  Arabia: {game_state.relations['arabia']}/100
  🇪🇺 EU:     {game_state.relations['eu']}/100
  ⚡ DPRG:   {game_state.relations['dprg']}/100

{'─'*60}
LEGACY — ✦ {p_title} ✦
  Personal Wealth: ${pw:.1f}B

  {p_desc}
{'='*60}
"""
        return (True, 'defeat', msg)

    # Defeat: approval collapse
    if game_state.public_approval <= 0:
        p_title, p_desc = get_personal_outcome(False, pw)
        msg = f"""
{'='*60}
💀 POPULAR REVOLT — GAME OVER 💀
{'='*60}

Public approval: {game_state.public_approval}%. The people have had enough.
Mass protests topple the government. No foreign ally intervenes.
Europa's leadership experiment ends in disgrace.

CAUSE OF DEFEAT: Total loss of public confidence

FINAL STATE:
  Budget:    ${game_state.budget:.1f}B
  Stability:  {game_state.stability}%
  Approval:   {game_state.public_approval}%  ← REVOLT
  Turn:       {game_state.current_turn}/{game_state.max_turns}

FINAL RELATIONS:
  🇺🇸 USA:    {game_state.relations['usa']}/100
  🛢️  Arabia: {game_state.relations['arabia']}/100
  🇪🇺 EU:     {game_state.relations['eu']}/100
  ⚡ DPRG:   {game_state.relations['dprg']}/100

{'─'*60}
LEGACY — ✦ {p_title} ✦
  Personal Wealth: ${pw:.1f}B

  {p_desc}
{'='*60}
"""
        return (True, 'defeat', msg)

    # Victory: survived 10 turns
    if game_state.current_turn > game_state.max_turns:
        budget = game_state.budget
        stability = game_state.stability
        rels = game_state.relations
        high_rels = sum(1 for r in rels.values() if r >= 65)
        good_rels = sum(1 for r in rels.values() if r >= 60)

        # National performance grade
        if budget > 40 and stability > 80 and high_rels >= 3:
            grade = "S — LEGENDARY"
            grade_title = "The Grand Strategist"
            grade_desc = "You mastered the impossible — keeping everyone happy while building a prosperous Europa."
        elif budget > 20 and stability > 70 and good_rels >= 2:
            grade = "A — MASTERFUL"
            if rels['usa'] > 70:
                grade_title = "Washington's Trusted Ally"
                grade_desc = "America opened its arms and its wallet. Europa thrived in the Western orbit."
            elif rels['arabia'] > 70:
                grade_title = "The Oil King's Partner"
                grade_desc = "Sadam's handshake proved golden. Europa's prosperity smells faintly of oil."
            elif rels['eu'] > 70:
                grade_title = "The European"
                grade_desc = "You walked the European path with integrity. Brussels will remember you fondly."
            else:
                grade_title = "The Skilled Diplomat"
                grade_desc = "No single patron, but no single enemy. A masterclass in balance."
        elif budget > 10 and stability > 60 and good_rels >= 1:
            grade = "B — COMPETENT"
            grade_title = "The Survivor"
            grade_desc = "Not elegant, but effective. Europa endures."
        elif budget > 5 and stability > 40:
            grade = "C — BARELY MADE IT"
            grade_title = "The Pragmatist"
            grade_desc = "You survived. History will debate the cost."
        elif 2 < budget <= 5 or 25 <= stability <= 40:
            grade = "D — PYRRHIC VICTORY"
            grade_title = "The Lucky One"
            grade_desc = "One more turn would have ended you. Don't let them see you sweat."
        else:
            grade = "F — HOLLOW VICTORY"
            grade_title = "The Shell"
            grade_desc = "You survived in name only. Europa is a nation on paper alone."

        p_title, p_desc = get_personal_outcome(True, pw)

        msg = f"""
{'='*60}
🎉 EUROPA ENDURES! — VICTORY 🎉
{'='*60}

Ten turns of impossible choices. Europa survives.

NATIONAL PERFORMANCE:
  Grade: {grade}
  "{grade_desc}"

  Budget:    ${game_state.budget:.1f}B
  Stability:  {game_state.stability}%
  Approval:   {game_state.public_approval}%
  Oil:        ${game_state.oil_price:.0f}/barrel

  Relations:
    🇺🇸 USA:    {game_state.relations['usa']}/100
    🛢️  Arabia: {game_state.relations['arabia']}/100
    🇪🇺 EU:     {game_state.relations['eu']}/100
    ⚡ DPRG:   {game_state.relations['dprg']}/100

  Sanctions: {'Active at end' if game_state.usa_sanctions_active else 'Avoided/Resolved'}
  Embargo:   {'Active at end' if game_state.arabia_embargo_active else 'Avoided/Resolved'}

{'─'*60}
LEGACY — ✦ {p_title} ✦
  Personal Wealth: ${pw:.1f}B

  {p_desc}
{'='*60}
"""
        return (True, 'victory', msg)

    return (False, None, None)
