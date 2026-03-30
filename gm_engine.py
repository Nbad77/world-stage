"""
GM INFERENCE LAYER — Session 7A Feature 10 Prototype + 10B-1 World Events
Separate Claude call for geopolitical reasoning about novel player proposals.
The GM does mechanical reasoning; the NPC does character work.

Prototype scope: Sadam (Arabia) + energy partnership proposals only.
10B-1: Daily world event generation for the briefing screen.
"""

import os
import json
import random
import string
import anthropic

# ── Module-level Anthropic client (10B-1) ──────────────────────────────────
# CLAUDE.md mandate: single module-level instance, never per-function
_api_key = os.getenv("ANTHROPIC_API_KEY")
_client = anthropic.Anthropic(
    api_key=_api_key,
    timeout=30.0,
    max_retries=0
) if _api_key else None

# ── Energy keyword detection ────────────────────────────────────────────────

ENERGY_KEYWORDS = {
    "energy", "oil", "exclusive", "partner", "supply",
    "barrel", "crude", "pipeline", "contract", "deal",
}


def is_energy_proposal(player_input: str) -> bool:
    """
    Returns True if the player input appears to be an energy
    partnership proposal directed at Arabia.
    Simple keyword detection: any two or more energy keywords present.
    """
    words = set(player_input.lower().split())
    # Also check for partial matches (e.g. "partnership" contains "partner")
    matches = 0
    input_lower = player_input.lower()
    for keyword in ENERGY_KEYWORDS:
        if keyword in input_lower:
            matches += 1
    return matches >= 2


# ── GM Inference Call ───────────────────────────────────────────────────────

GM_MODEL = "claude-haiku-4-5-20251001"

GM_SYSTEM_PROMPT = (
    "You are the GM of a geopolitical simulation. Your job is "
    "to reason about the mechanical consequences of player "
    "proposals — not to generate dialogue or character responses.\n"
    "Always respond with valid JSON only. No preamble, no "
    "explanation outside the JSON."
)

_DEFAULT_RESULT = {
    "proposal_summary": "Unable to analyze proposal.",
    "affected_parties": [],
    "contradicted_deals": [],
    "second_order_consequences": [],
    "commitment_type": "exploratory",
    "credibility_assessment": "questionable",
}


def _build_game_state_summary(gs) -> str:
    """Build a concise game state summary for the GM inference prompt."""
    relations = gs.relations or {}
    deal_history = getattr(gs, 'deal_history', [])
    active_deals = [
        d for d in deal_history
        if not d.get('broken')
        and d.get('expires_turn', 0) >= gs.current_turn
    ]
    active_commitments = getattr(gs, 'active_trade_commitments', [])

    # Domestic actions taken (regime identity indicators)
    regime = gs.state_identity.get('regime_type', 'Managed Democracy')
    power_base = gs.state_identity.get('power_base', 'Mass-Dependent')

    summary_lines = [
        f"Relations: USA={relations.get('usa', 50)}, Arabia={relations.get('arabia', 50)}, "
        f"EU={relations.get('eu', 50)}, DPRG={relations.get('dprg', 50)}",
        f"Budget: ${gs.budget:.1f}B, Personal wealth: ${gs.personal_wealth:.1f}B",
        f"Oil price: ${gs.oil_price}/bbl",
        f"Regime: {regime}, Power base: {power_base}",
        f"Stability: {gs.stability}%, Approval: {gs.public_approval}%",
    ]

    if active_deals:
        summary_lines.append("Active deals:")
        for d in active_deals:
            npc = d.get('npc', '?').upper()
            summary = d.get('summary', d.get('description', 'deal'))
            expires = d.get('expires_turn', '?')
            summary_lines.append(f"  - [{npc}] {summary} (expires turn {expires})")

    if active_commitments:
        summary_lines.append("Active trade commitments:")
        for c in active_commitments:
            desc = c.get('description', 'commitment')
            turns = c.get('turns_remaining', '?')
            summary_lines.append(f"  - {desc} ({turns} turns remaining)")

    if gs.oil_price_locked and gs.oil_price_lock_turns_remaining > 0:
        summary_lines.append(
            f"Oil price locked at ${gs.oil_price_lock_value}/bbl "
            f"for {gs.oil_price_lock_turns_remaining} more turn(s)"
        )

    if gs.arabia_embargo_active:
        summary_lines.append(f"Arabia embargo active (tier {gs.arabia_embargo_tier})")

    if gs.usa_sanctions_active:
        summary_lines.append(f"USA sanctions active (tier {gs.usa_sanctions_tier})")

    return "\n".join(summary_lines)


def run_gm_inference(player_input: str, gs) -> dict:
    """
    Makes a Claude API call (Haiku — high-frequency structural call).
    Returns a structured consequence object analyzing the player's
    energy partnership proposal.
    """
    import anthropic

    print(f"[GM] Energy proposal detected: {player_input[:50]}")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[GM] No API key — returning default result")
        return dict(_DEFAULT_RESULT)

    state_summary = _build_game_state_summary(gs)

    user_prompt = (
        f"Current game state:\n{state_summary}\n\n"
        f"Player's proposal (verbatim):\n\"{player_input}\"\n\n"
        f"Analyze this energy partnership proposal and respond with exactly this JSON schema:\n"
        f'{{\n'
        f'  "proposal_summary": "one sentence describing what the player is actually proposing",\n'
        f'  "affected_parties": ["list of NPCs and systems affected beyond Sadam — use lowercase npc keys: usa, arabia, eu, dprg"],\n'
        f'  "contradicted_deals": ["list of any active deals or commitments this conflicts with"],\n'
        f'  "second_order_consequences": ["2-3 ripple effects beyond the immediate deal"],\n'
        f'  "commitment_type": "one of: binding / conditional / exploratory / rhetorical",\n'
        f'  "credibility_assessment": "one of: believable / questionable / not_credible — based on current game state"\n'
        f'}}'
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=GM_MODEL,
            max_tokens=500,
            temperature=0.2,  # low temp for reliable structured output
            system=GM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()

        # Parse JSON — handle potential markdown code fences
        if raw_text.startswith("```"):
            # Strip ```json ... ``` wrapping
            lines = raw_text.split("\n")
            json_lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(json_lines)

        result = json.loads(raw_text)

        # Validate required fields exist
        for key in _DEFAULT_RESULT:
            if key not in result:
                result[key] = _DEFAULT_RESULT[key]

        print(f"[GM] Inference result: {json.dumps(result, indent=2)}")
        return result

    except json.JSONDecodeError as e:
        print(f"[GM] JSON parse error: {e}")
        print(f"[GM] Raw response: {raw_text[:200]}")
        return dict(_DEFAULT_RESULT)

    except Exception as e:
        print(f"[GM] Inference call failed: {e}")
        return dict(_DEFAULT_RESULT)


# ── 10B-1: World Event Generation ─────────────────────────────────────────

AUTHORED_EVENT_TYPES = [
    "energy_supply_pressure",       # Sadam/oil related
    "western_alignment_demand",     # Bill/Marsha democratic pressure
    "eastern_partnership_offer",    # Volkov/Wei overture
    "domestic_stability_risk",      # internal pressure
    "economic_shock",               # budget/treasury pressure
    "diplomatic_incident",          # NPC bilateral friction
    "regional_security_event",      # military/border
    "corruption_exposure_risk",     # heat/detection pressure
]

# NPC mapping for authored event types
_EVENT_TYPE_NPCS = {
    "energy_supply_pressure": ["sadam"],
    "western_alignment_demand": ["bill", "marsha"],
    "eastern_partnership_offer": ["volkov", "wei"],
    "domestic_stability_risk": [],
    "economic_shock": [],
    "diplomatic_incident": ["bill", "sadam", "volkov"],
    "regional_security_event": ["volkov", "ji_won"],
    "corruption_exposure_risk": ["bill", "marsha"],
}

_EVENT_SYSTEM_PROMPT = (
    "You are the game master for a geopolitical simulation. "
    "You generate world events that feel like natural consequences "
    "of the player's governance choices. Events should be specific "
    "to the current game state — not generic. The best events create "
    "dilemmas where both options have real costs.\n\n"
    "Never generate the same event twice in a row. Vary severity and category. "
    "At least one event per day should involve an NPC the player has been neglecting.\n\n"
    "Always respond with valid JSON only. No preamble, no explanation.\n\n"
    "Choices must be specific to the event situation. Never use "
    "generic labels. Only list NPCs in applicable_npcs who have "
    "a genuine stake in this specific event. Default to fewer "
    "NPCs, not more."
)


def _random_event_id():
    return "evt_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def _build_event_state_summary(gs) -> str:
    """Build a state summary optimized for world event generation."""
    relations = gs.relations or {}
    regime = gs.state_identity.get('regime_type', 'Managed Democracy')

    leg = getattr(gs, 'legitimacy_stability', gs.stability * 0.5)
    coe = getattr(gs, 'coercion_stability', gs.stability * 0.5)

    lines = [
        f"Regime: {regime}",
        f"Stability: {gs.stability}% (legitimacy: {leg:.0f}%, coercion: {coe:.0f}%)",
        f"Approval: {gs.public_approval}%",
        f"Treasury: ${gs.budget:.1f}B | Personal wealth: ${gs.personal_wealth:.1f}B",
    ]

    # NPC relations
    npc_map = {
        "bill": "Bill (USA)", "marsha": "Marsha (EU)",
        "sadam": "Sadam (Arabia)", "volkov": "Volkov (Russia)",
        "wei": "Wei (China)", "ji_won": "Ji-won (DPRG)",
    }
    rel_lines = []
    for npc_id, label in npc_map.items():
        val = relations.get(npc_id, relations.get(npc_id.split("_")[0], 50))
        rel_lines.append(f"  {label}: {val}")
    lines.append("NPC relations:\n" + "\n".join(rel_lines))

    # Neglected NPCs
    cdwr = getattr(gs, 'communique_days_without_response', {})
    neglected = {k: v for k, v in cdwr.items() if v > 2}
    if neglected:
        lines.append(f"Neglected NPCs (days without response): {neglected}")

    # Active conditions
    conditions = []
    if gs.usa_sanctions_active:
        conditions.append(f"USA sanctions tier {gs.usa_sanctions_tier}")
    if gs.arabia_embargo_active:
        conditions.append(f"Arabia embargo tier {gs.arabia_embargo_tier}")
    detection = getattr(gs, 'detection_heat', 0)
    if detection > 30:
        conditions.append(f"Detection heat: {detection}%")
    if conditions:
        lines.append(f"Active conditions: {', '.join(conditions)}")

    # Recent resolved events (last 3)
    daily = getattr(gs, 'daily_events', [])
    resolved = [e for e in daily if e.get('resolved')][-3:]
    if resolved:
        lines.append("Recent resolved events:")
        for e in resolved:
            lines.append(f"  - {e['title']}: {e.get('resolution', 'unknown')}")

    return "\n".join(lines)


def _build_event_user_prompt(gs, count: int) -> str:
    """Build the user prompt for event generation based on era."""
    state_summary = _build_event_state_summary(gs)
    era = getattr(gs, 'current_era', 1)
    turn = getattr(gs, 'current_turn', 1)

    era_instruction = ""
    if era <= 1:
        era_instruction = (
            f"Use only these event type categories: {AUTHORED_EVENT_TYPES}\n"
            "Instantiate each with specific details from the current game state.\n"
            f"Return exactly {count} events."
        )
    elif era <= 3:
        era_instruction = (
            "Generate a mix of authored-type events and reactive "
            "events based on current game state."
        )
    else:
        era_instruction = (
            "Generate events as natural consequences of accumulated "
            "game state. NPCs that have been ignored should feature prominently."
        )

    return (
        f"Generate {count} world events for Day {turn}, Era {era}.\n\n"
        f"Current state:\n{state_summary}\n\n"
        f"{era_instruction}\n\n"
        f"Return ONLY a JSON array. No preamble. No explanation. Each event object:\n"
        '{\n'
        '  "id": "evt_XXXXXX",\n'
        '  "title": "Short headline (max 8 words)",\n'
        '  "summary": "2-3 sentences. Be specific — reference exact figures, '
        'named actors, and current game state details like budget, stability score, '
        'and approval rating.",\n'
        '  "severity": "routine|moderate|urgent|critical",\n'
        '  "category": "diplomatic|economic|military|domestic|crisis",\n'
        '  "applicable_npcs": ["only NPCs with a genuine stake in this specific '
        'event — can be empty. A domestic labor dispute does not automatically '
        'involve all six NPCs."],\n'
        '  "choices": [\n'
        '    {\n'
        '      "label": "A",\n'
        '      "text": "Specific action (max 12 words, action-verb first)",\n'
        '      "hint": "One sentence on the tradeoff — what the player is '
        'risking or committing, not the outcome"\n'
        '    }\n'
        '  ],\n'
        '  "required": true or false,\n'
        '  "resolved": false,\n'
        '  "resolution": null,\n'
        '  "escalated_from_communique": false,\n'
        f'  "era": {era},\n'
        f'  "day": {turn}\n'
        '}\n\n'
        "Generate exactly 4 choices per event. Choices must be specific "
        "to THIS event situation — never generic. Cover the full option "
        "space: concede, negotiate, confront/suppress, deflect or delay. "
        "Name each concretely for this scenario.\n"
        "WRONG: 'Implement policy reforms'\n"
        "RIGHT: 'Negotiate a phased 8% wage increase with union leaders'\n"
        "The hint describes the tradeoff, not the outcome.\n\n"
        "Set required: false for all events.\n"
        "Severity rules:\n"
        "- routine: low stakes\n"
        "- moderate: worth addressing\n"
        "- urgent: should address today\n"
        "- critical: highest stakes\n"
        "At least 1 critical or urgent event per day."
    )


def _generate_fallback_events(gs) -> list:
    """Hardcoded fallback — never return empty events list."""
    era = getattr(gs, 'current_era', 1)
    turn = getattr(gs, 'current_turn', 1)
    templates = [
        {
            "title": "Energy Markets Under Pressure",
            "summary": "Global oil supply disruptions are creating uncertainty. "
                       "Europa's energy costs may rise unless diplomatic action is taken.",
            "severity": "urgent",
            "category": "economic",
            "applicable_npcs": ["sadam"],
            "required": True,
        },
        {
            "title": "Western Powers Demand Reforms",
            "summary": "A joint communiqué from Washington and Brussels calls for "
                       "transparent governance reforms in Europa.",
            "severity": "moderate",
            "category": "diplomatic",
            "applicable_npcs": ["bill", "marsha"],
            "required": True,
        },
        {
            "title": "Border Tensions Escalate",
            "summary": "Military movements near Europa's northern border have raised "
                       "concerns. Intelligence suggests a show of force rather than invasion.",
            "severity": "critical",
            "category": "military",
            "applicable_npcs": ["volkov"],
            "required": True,
        },
    ]
    events = []
    for t in templates:
        evt = dict(t)
        evt["id"] = _random_event_id()
        evt["resolved"] = False
        evt["resolution"] = None
        evt["escalated_from_communique"] = False
        evt["era"] = era
        evt["day"] = turn
        events.append(evt)
    return events


def _parse_events_json(raw_text: str) -> list:
    """Parse JSON event array, handling markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _validate_event(evt: dict, era: int, turn: int) -> dict:
    """Ensure all required fields exist with correct types."""
    evt.setdefault("id", _random_event_id())
    evt.setdefault("title", "Unnamed Event")
    evt.setdefault("summary", "No details available.")
    evt.setdefault("severity", "moderate")
    evt.setdefault("category", "diplomatic")
    evt.setdefault("applicable_npcs", [])
    evt.setdefault("required", False)
    evt.setdefault("resolved", False)
    evt.setdefault("resolution", None)
    evt.setdefault("escalated_from_communique", False)
    evt["era"] = era
    evt["day"] = turn
    # Ensure severity is valid
    if evt["severity"] not in ("routine", "moderate", "urgent", "critical"):
        evt["severity"] = "moderate"
    if evt["category"] not in ("diplomatic", "economic", "military", "domestic", "crisis"):
        evt["category"] = "diplomatic"
    return evt


def generate_daily_events(gs) -> list:
    """
    Generates 5-7 world events for the day.
    Returns list of event dicts. 3 are marked required=True, rest are optional.
    Uses module-level _client (Haiku).
    """
    era = getattr(gs, 'current_era', 1)
    turn = getattr(gs, 'current_turn', 1)
    count = random.randint(5, 7)

    # E7b: Pick up any player declarations pre-seeded from last turn
    pre_seeded = []
    _pending = getattr(gs, 'pending_declaration_events', [])
    if _pending:
        pre_seeded = list(_pending)
        gs.pending_declaration_events = []
        print(f"[DECLARATION_INJECT] pre_seeded={len(pre_seeded)} events injected")

    # Reduce Haiku generation count so total stays in range
    haiku_count = max(2, count - len(pre_seeded))

    if not _client:
        print("[GM-Events] No API key — returning fallback events")
        return pre_seeded + _generate_fallback_events(gs)

    user_prompt = _build_event_user_prompt(gs, haiku_count)

    try:
        response = _client.messages.create(
            model=GM_MODEL,
            max_tokens=3500,
            temperature=0.7,
            system=_EVENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = response.content[0].text.strip()
        print(f"[EVENT_GEN_RAW] response_length={len(raw_text)} "
              f"finish_reason={response.stop_reason}")
        events = _parse_events_json(raw_text)

        if not isinstance(events, list) or len(events) == 0:
            raise ValueError("Empty or non-list response")

        # Validate each event
        events = [_validate_event(e, era, turn) for e in events]

        # All events optional — player resolves any 3 to unlock EOT
        for e in events:
            e['required'] = False

        # Log choices validation
        choices_present = all(
            'choices' in e and len(e.get('choices', [])) == 4
            for e in events
        )
        print(f"[EVENT_GEN] day={turn} "
              f"events={len(events)} "
              f"choices_present={choices_present}")

        for e in events:
            if 'choices' not in e or not e.get('choices'):
                print(f"[EVENT_GEN_WARN] event={e.get('id')} "
                      f"missing choices — frontend fallback will apply")

        # Prepend pre-seeded declaration events
        events = pre_seeded + events
        print(f"[GM-Events] Generated {len(events)} events for Day {turn}, Era {era} "
              f"(pre_seeded={len(pre_seeded)})")
        return events

    except json.JSONDecodeError as e:
        print(f"[GM-Events] JSON parse error: {e}")
        return pre_seeded + _generate_fallback_events(gs)
    except Exception as e:
        print(f"[GM-Events] Generation failed: {e}")
        return pre_seeded + _generate_fallback_events(gs)
