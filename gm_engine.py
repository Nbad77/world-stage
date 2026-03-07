"""
GM INFERENCE LAYER — Session 7A Feature 10 Prototype
Separate Claude call for geopolitical reasoning about novel player proposals.
The GM does mechanical reasoning; the NPC does character work.

Prototype scope: Sadam (Arabia) + energy partnership proposals only.
"""

import os
import json

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
