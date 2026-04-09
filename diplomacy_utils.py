"""Session 11: Diplomatic Standing utilities.

Shared helpers for standing deltas, dampening, and recall checks.
Imported by game_state.py, turn_processor.py, and api.py — kept in its
own module to avoid circular imports.
"""

# Maps relations keys → npc_id keys for diplomatic_standing lookups
_RELATIONS_KEY_TO_NPC_ID = {
    "usa": "bill",
    "russia": "volkov",
    "arabia": "sadam",
    "china": "wei",
    "eu": "eu",
    "dprg": "dprg",
}

_NPC_ID_TO_NAME = {
    "bill": "Bill Hartwell",
    "eu": "Marsha",
    "volkov": "Nikolai Volkov",
    "wei": "Wei Jianming",
    "sadam": "Sadam",
    "dprg": "Ji-won Ryang",
}

STANDING_DELTAS = {
    "deal_kept":             +2.0,
    "deal_broken":           -4.0,
    "communique_ignored":    -1.0,
    "proactive_outreach":    +1.0,
    "summit_constructive":   +3.0,
    "summit_snub":           -3.0,
    "recall_unaddressed":    -1.0,   # applied per-day while recall active
    "sharp_incident":        -3.0,
}

STANDING_RECALL_THRESHOLDS = {
    "eu":     25.0,
    "bill":   20.0,
    "wei":    20.0,
    "dprg":   20.0,
    "volkov": 15.0,
    "sadam":  15.0,
}


def apply_standing_delta(gs, npc_id, delta_key):
    """Apply a standing delta to one NPC. Clamps 0-100. Returns new standing value.

    gs can be a GameState object or a plain dict (e.g. gs.__dict__).
    """
    delta = STANDING_DELTAS.get(delta_key, 0.0)

    # Support both dict-style and attribute-style access
    if isinstance(gs, dict):
        standing_dict = gs.get("diplomatic_standing", {})
    else:
        standing_dict = getattr(gs, "diplomatic_standing", {})

    current = standing_dict.get(npc_id, 50.0)
    new_val = max(0.0, min(100.0, current + delta))
    standing_dict[npc_id] = new_val
    print(f"[STANDING] {npc_id} {delta_key}: {current:.1f} -> {new_val:.1f}")
    return new_val


def calculate_diplomatic_dampening(gs, affected_npc_id):
    """Returns a dampening coefficient (0.0-0.40).
    effective_fallout = base_fallout * (1 - dampening)

    gs can be a GameState object or a plain dict.

    Formula:
      dampening = (standing_with_NPC * w_stand
                   + avg_standing_other_NPCs * w_other
                   + reliability_normalized * w_rel) / 100
      cap: 0.40

    NPC-specific weight adjustments:
      Marsha/Bill: reliability weight 0.35, standing weight 0.35
      Sadam/Volkov: standing weight 0.65, reliability weight 0.05
      Ji-won: all weights halved (capabilities-based, not reputation-based)
    """
    if isinstance(gs, dict):
        standing_dict = gs.get("diplomatic_standing", {})
        reliability = gs.get("reliability_score", 100.0)
    else:
        standing_dict = getattr(gs, "diplomatic_standing", {})
        reliability = getattr(gs, "reliability_score", 100.0)

    standing_with_npc = standing_dict.get(affected_npc_id, 50.0)

    other_standings = [v for k, v in standing_dict.items() if k != affected_npc_id]
    avg_other = sum(other_standings) / len(other_standings) if other_standings else 50.0

    reliability_norm = min(100.0, max(0.0, reliability))

    # NPC-specific weights
    if affected_npc_id in ("eu", "bill"):
        w_stand, w_other, w_rel = 0.35, 0.30, 0.35
    elif affected_npc_id in ("sadam", "volkov"):
        w_stand, w_other, w_rel = 0.65, 0.30, 0.05
    elif affected_npc_id == "dprg":
        w_stand, w_other, w_rel = 0.25, 0.25, 0.10
    else:
        w_stand, w_other, w_rel = 0.50, 0.30, 0.20

    raw = (standing_with_npc * w_stand + avg_other * w_other + reliability_norm * w_rel) / 100.0
    dampening = min(0.40, max(0.0, raw))

    print(f"[DAMPENING] {affected_npc_id}: standing={standing_with_npc:.1f} avg_other={avg_other:.1f} reliability={reliability_norm:.1f} -> dampening={dampening:.3f}")
    return dampening


def check_ambassador_recalls(gs):
    """Check all NPCs for recall threshold crossings. Fire recall or reinstate.
    Returns list of newly recalled npc_ids.

    gs must be a GameState object (attribute access).
    """
    newly_recalled = []
    standing_dict = getattr(gs, "diplomatic_standing", {})
    recalled_dict = getattr(gs, "ambassador_recalled", {})

    for npc_id, threshold in STANDING_RECALL_THRESHOLDS.items():
        standing = standing_dict.get(npc_id, 50.0)
        already_recalled = recalled_dict.get(npc_id, False)

        if standing < threshold and not already_recalled:
            recalled_dict[npc_id] = True
            newly_recalled.append(npc_id)
            print(f"[RECALL] FIRED: {npc_id} standing={standing:.1f} threshold={threshold}")
        elif standing >= (threshold + 10) and already_recalled:
            recalled_dict[npc_id] = False
            print(f"[RECALL] REINSTATED: {npc_id} standing={standing:.1f}")

    return newly_recalled
