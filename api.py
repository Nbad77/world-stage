"""
THE WORLD STAGE — FastAPI Backend
Serves game state, processes turns, calls npc_engine for dialogue.
Game logic is entirely in Python (game_state, turn_processor).
Claude generates dialogue only (npc_engine).

Endpoints:
  POST /game/new                    → { session_id, game_state, offers, dialogue }
  GET  /game/{id}                   → { game_state, offers }
  POST /game/{id}/action            → { consequences, blackmail, game_state, offers }
  POST /game/{id}/skim              → { skim_result, intercepts, eot_effects, game_state, status }
  POST /game/{id}/inject            → { inject_result, game_state }
  GET  /game/{id}/status            → { status: active|won|lost|escaped }
  POST /game/{id}/negotiate         → { response, counter_offer }
"""

import sys
import os
import random
from pathlib import Path

# Ensure project root is importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any

import npc_engine
import npc_usa
import npc_arabia
import npc_eu
import npc_dprg
from game_state import GameState
from turn_processor import (
    process_choice_consequences,
    apply_end_of_turn_effects,
    check_game_over,
)
from db import init_db, create_session, load_session, save_session

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="The World Stage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ── Request models ────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    choice: str          # "A" through "G"

class SkimRequest(BaseModel):
    choice: int          # 1–4

class InjectRequest(BaseModel):
    choice: int          # 0, 1, 2, or 3

class NegotiateRequest(BaseModel):
    npc_id: str          # "usa" | "arabia" | "eu" | "dprg"
    message: str         # player's latest message
    history: List[Any] = []  # list of {role, content} prior messages

class AcceptCounterRequest(BaseModel):
    letter: str           # "A"-"D"
    counter_offer: Any    # the counter_offer dict from negotiate response

class PurchaseUpgradeRequest(BaseModel):
    upgrade_id: str  # 'intelligence_apparatus' | 'sovereign_wealth_diversion' | 'loyalty_brigades' | 'debt_infrastructure_deal'

class BrigadeRequest(BaseModel):
    deploy: bool  # True = deploy brigades this turn

class AftermathRequest(BaseModel):
    choice: int  # 1=suppress_coverage, 2=aid_programs, 3=call_in_favor

class GetIntelRequest(BaseModel):
    npc_id: str  # 'usa' | 'arabia' | 'eu' | 'dprg'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_gs(session_id: str) -> GameState:
    """Load GameState from DB or raise 404."""
    data = load_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return GameState.deserialize(data)


def _save_gs(session_id: str, gs: GameState):
    save_session(session_id, gs.serialize())


def _build_offers(gs: GameState) -> list[dict]:
    """
    Build the same offers list that main.py get_all_offers() builds,
    but return as JSON-serializable dicts (letter + offer object).
    """
    offers = []

    # A) USA
    offers.append({"letter": "A", **npc_usa.get_usa_offer(gs)})
    # B) Arabia
    offers.append({"letter": "B", **npc_arabia.get_arabia_offer(gs)})
    # C) EU
    offers.append({"letter": "C", **npc_eu.get_eu_offer(gs)})
    # D) DPRG
    offers.append({"letter": "D", **npc_dprg.get_dprg_offer(gs)})
    # E) Do nothing
    offers.append({
        "letter": "E",
        "text": "Do nothing (all relations -5, stability -2%)",
        "type": "do_nothing",
        "npc": None,
        "consequences": {"usa": -5, "arabia": -5, "eu": -5, "dprg": -5, "stability": -2},
    })
    # F) Ji-won escape (conditional)
    if gs.personal_wealth >= 25 and gs.budget <= 12:
        offers.append({
            "letter": "F",
            "text": f"[Ji-won] Activate escape plan — vanish with ${gs.personal_wealth:.1f}B (ends game)",
            "type": "escape",
            "npc": "dprg",
            "consequences": {},
        })
    # G) Emergency injection (conditional)
    if gs.budget < 5 and gs.personal_wealth > 0:
        offers.append({
            "letter": "G",
            "text": f"[PRIVATE] Emergency: inject personal funds into national treasury (${gs.personal_wealth:.1f}B available)",
            "type": "inject_funds",
            "npc": None,
            "consequences": {},
        })
    # FEATURE 2: Brigade deployment is now a secondary prompt shown AFTER
    # the player picks their diplomatic choice (A-E), not a competing offer.
    # Removed H offer here; brigade prompt logic is in post_action.
    return offers


def _build_skim_options(gs: GameState) -> list[dict]:
    """Return available skim options given current budget."""
    budget = gs.budget
    options = [
        {"choice": 1, "label": "Stay clean — no personal skim",
         "national_cost": 0, "personal_gain": 0, "stability_hit": 0, "approval_hit": 0}
    ]
    if budget >= 1.0:
        options.append({
            "choice": 2,
            "label": "Small skim: -$1B national, +$1B personal, -1% stability",
            "national_cost": 1.0, "personal_gain": 1.0, "stability_hit": -1, "approval_hit": 0,
        })
    if budget >= 3.0:
        options.append({
            "choice": 3,
            "label": "Medium skim: -$3B national, +$3B personal, -3% stability, -2% approval",
            "national_cost": 3.0, "personal_gain": 3.0, "stability_hit": -3, "approval_hit": -2,
        })
    if budget >= 7.0:
        options.append({
            "choice": 4,
            "label": "Large skim: -$7B national, +$7B personal, -6% stability, -5% approval",
            "national_cost": 7.0, "personal_gain": 7.0, "stability_hit": -6, "approval_hit": -5,
        })
    return options


def _calc_eot_drain_projection(gs: GameState) -> dict:
    """
    Addition 2: Calculate what the passive EOT drain will be this turn,
    using the current oil price and active modifiers — without applying anything.
    Returns { projected_drain, budget_after_drain } for display in the skim panel.
    """
    # Determine what oil price will be at EOT (best estimate before EOT runs)
    if gs.oil_price_locked and gs.oil_price_lock_turns_remaining > 0:
        base_oil = max(20, round(gs.oil_price_lock_value))
    else:
        # Simulate set_oil_price_from_relations without mutating state
        base = 75.0
        rel = gs.relations['arabia']
        if rel >= 80:
            base_oil = max(20, round(base * 0.70))
        elif rel >= 60:
            base_oil = max(20, round(base * 0.85))
        elif rel >= 40:
            base_oil = max(20, round(base * 1.00))
        elif rel >= 20:
            base_oil = max(20, round(base * 1.25))
        else:
            base_oil = max(20, round(base * 1.60))

    # Stack active oil price modifiers (they tick this EOT)
    total_modifier = sum(m.get('delta', 0) for m in gs.oil_price_modifiers)
    projected_oil = max(20, round(base_oil + total_modifier))

    # Arabia embargo tier penalty (best estimate — tier can ramp +1 max)
    arabia_rel = gs.relations['arabia']
    if arabia_rel <= 35:
        if arabia_rel <= 4:
            target_tier = 4
        elif arabia_rel <= 14:
            target_tier = 3
        elif arabia_rel <= 24:
            target_tier = 2
        else:
            target_tier = 1
        effective_tier = min(target_tier, gs.arabia_embargo_tier + 1)
    else:
        effective_tier = 0
    oil_penalty = {0: 0, 1: 10, 2: 20, 3: 35, 4: 50}[effective_tier]
    projected_oil = max(20, projected_oil + oil_penalty)

    # Fixed government cost
    base_cost = 3.0
    oil_cost = round(projected_oil / 15.0, 1)

    # Active installments — sum this turn's incoming/outgoing payments.
    # Positive amounts are receipts (reduce net drain); negative are payments (add to drain).
    installment_net = sum(float(inst.get('amount', 0)) for inst in gs.active_installments)
    installment_net = round(installment_net, 1)

    # Net drain = costs - installment income (installment_net may be negative if paying out)
    total_drain = round(base_cost + oil_cost - installment_net, 1)
    budget_after = round(gs.budget - total_drain, 1)

    return {
        "projected_drain": total_drain,
        "budget_after_drain": budget_after,
        "installment_net": installment_net,   # expose for potential future display
    }


def _build_inject_options(gs: GameState) -> list[dict]:
    """Return available injection options given current personal_wealth."""
    pw = gs.personal_wealth
    options = [
        {"choice": 0, "label": "Do nothing (keep personal funds, risk bankruptcy)",
         "personal_cost": 0, "national_gain": 0}
    ]
    if pw >= 3:
        options.append({"choice": 1, "label": "Inject $3B (-$3B personal → +$3B national)",
                         "personal_cost": 3.0, "national_gain": 3.0})
    if pw >= 7:
        options.append({"choice": 2, "label": "Inject $7B (-$7B personal → +$7B national)",
                         "personal_cost": 7.0, "national_gain": 7.0})
    if pw > 0:
        options.append({"choice": 3,
                         "label": f"Inject ALL (-${pw:.1f}B personal → +${pw:.1f}B national)",
                         "personal_cost": round(pw, 2), "national_gain": round(pw, 2)})
    return options


def _check_blackmail(gs: GameState) -> bool:
    return (
        not gs.blackmail_used
        and gs.personal_wealth >= 20
        and gs.relations['usa'] <= 20
    )


def _get_corruption_intercepts(gs: GameState) -> list[str]:
    """
    Fire one-shot intercept comments when personal_wealth crosses thresholds.
    Mirrors main.py get_corruption_npc_comments() exactly.
    """
    pw = gs.personal_wealth
    w = gs.corruption_warned
    comments = []

    for threshold, flag_suffix, label in [
        (8,  '_5',  '8b'),
        (20, '_15', '20b'),
        (35, '_30', '35b'),
    ]:
        if pw > threshold:
            any_unfired = any(not w.get(f"{npc}{flag_suffix}", False)
                              for npc in ['usa', 'arabia', 'eu', 'dprg'])
            if any_unfired:
                # Reset flags so npc_engine generates (it skips already-True ones)
                for npc in ['usa', 'arabia', 'eu', 'dprg']:
                    w[f"{npc}{flag_suffix}"] = False
                intercepts = npc_engine.generate_intercept_comments(gs, label)
                # Set flags permanently
                for npc in ['usa', 'arabia', 'eu', 'dprg']:
                    w[f"{npc}{flag_suffix}"] = True
                comments.extend(intercepts)

    return comments


def _maybe_generate_world_event(gs: GameState, last_action_type: str = "") -> Optional[dict]:
    """
    Probabilistically generate a world event.
    Base 35% chance, boosted by action type:
      oil/trade deal      +20%
      usa side/sanctions  +25%
      heavy skim (>=$7B)  +15% (checked via action_history)
      alliance shifts     +20%
    Returns the event dict or None.
    """
    base_chance = 0.35

    action_lower = (last_action_type or "").lower()
    if action_lower in ("accept_deal",):
        # Check which NPC to determine boost
        last = gs.action_history[-1] if gs.action_history else {}
        npc = last.get("npc", "")
        if npc in ("arabia",):
            base_chance += 0.20
        elif npc in ("usa",):
            base_chance += 0.25
        elif npc in ("eu", "dprg"):
            base_chance += 0.20
    elif action_lower == "do_nothing":
        base_chance -= 0.10  # boring turn, less likely

    base_chance = min(base_chance, 0.85)  # cap at 85%

    if random.random() > base_chance:
        return None

    event = npc_engine.generate_world_event(gs, last_action_type)
    return event


def _apply_world_event(gs: GameState, event: dict):
    """Apply a world event's numeric effects to game state."""
    if not event:
        return
    effects = event.get("effects", {})
    oil_delta = effects.get("oil_price_delta", 0)
    stability_delta = effects.get("stability_delta", 0)
    rels = effects.get("relations_delta", {})

    if oil_delta:
        # Register as a persistent modifier so EOT recalculation doesn't wipe it.
        # World event oil effects last for the duration specified, defaulting to 2 turns.
        duration = effects.get("oil_price_duration", 2)
        desc = event.get("title", "world event")
        gs.oil_price_modifiers.append({
            "delta": float(oil_delta),
            "turns_remaining": int(duration),
            "description": desc,
        })
        # Also apply immediately so the current turn's display shows the new price
        gs.oil_price = max(20, round(gs.oil_price + oil_delta))
    if stability_delta:
        gs.update_stability(stability_delta)
    for npc, delta in rels.items():
        if npc in gs.relations and delta:
            gs.update_relations(npc, delta)


def _game_status(gs: GameState) -> str:
    """Return 'active', 'won', 'lost', or 'escaped'."""
    if gs.budget <= 0 or gs.stability <= 0 or gs.public_approval <= 0:
        return "lost"
    if gs.current_turn > gs.max_turns:
        return "won"
    return "active"


def _build_ending(gs: GameState) -> dict | None:
    """
    Build ending payload if game is over. Returns None if still active.
    Mirrors check_game_over() but returns structured data instead of a string.
    """
    from turn_processor import get_personal_outcome, get_legacy_title

    pw = gs.personal_wealth

    if gs.budget <= 0:
        cause = "bankruptcy"
    elif gs.stability <= 0:
        cause = "collapse"
    elif gs.public_approval <= 0:
        cause = "revolt"
    elif gs.current_turn > gs.max_turns:
        cause = "victory"
    else:
        return None

    nation_survived = (cause == "victory")
    p_title, p_desc = get_personal_outcome(nation_survived, pw)

    result = {
        "cause": cause,
        "nation_survived": nation_survived,
        "personal_title": p_title,
        "personal_description": p_desc,
        "personal_wealth": pw,
        "final_budget": gs.budget,
        "final_stability": gs.stability,
        "final_approval": gs.public_approval,
        "final_relations": dict(gs.relations),
        "usa_sanctions_active": gs.usa_sanctions_active,
        "arabia_embargo_active": gs.arabia_embargo_active,
        "turn": gs.current_turn,
    }

    if nation_survived:
        rels = gs.relations
        high_rels = sum(1 for r in rels.values() if r >= 65)
        good_rels = sum(1 for r in rels.values() if r >= 60)
        budget = gs.budget
        stability = gs.stability

        if budget > 40 and stability > 80 and high_rels >= 3:
            grade = "S"; grade_label = "LEGENDARY"
            grade_title = "The Grand Strategist"
            grade_desc = "You mastered the impossible — keeping everyone happy while building a prosperous Europa."
        elif budget > 20 and stability > 70 and good_rels >= 2:
            grade = "A"; grade_label = "MASTERFUL"
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
            grade = "B"; grade_label = "COMPETENT"
            grade_title = "The Survivor"
            grade_desc = "Not elegant, but effective. Europa endures."
        elif budget > 5 and stability > 40:
            grade = "C"; grade_label = "BARELY MADE IT"
            grade_title = "The Pragmatist"
            grade_desc = "You survived. History will debate the cost."
        elif 2 < budget <= 5 or 25 <= stability <= 40:
            grade = "D"; grade_label = "PYRRHIC VICTORY"
            grade_title = "The Lucky One"
            grade_desc = "One more turn would have ended you. Don't let them see you sweat."
        else:
            grade = "F"; grade_label = "HOLLOW VICTORY"
            grade_title = "The Shell"
            grade_desc = "You survived in name only. Europa is a nation on paper alone."

        result["grade"] = grade
        result["grade_label"] = grade_label
        result["grade_title"] = grade_title
        result["grade_description"] = grade_desc

    return result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/game/new")
def new_game():
    """Create a new game session. Returns session_id, initial state, offers, and Turn 1 dialogue."""
    gs = GameState()
    dialogue = npc_engine.generate_dialogue(gs)
    blackmail_active = _check_blackmail(gs)
    offers = _build_offers(gs)
    skim_options = _build_skim_options(gs)

    # Stage 5: generate opening epitaph for Turn 1
    try:
        gs.current_epitaph = npc_engine.generate_epitaph(gs)
    except Exception:
        gs.current_epitaph = None

    session_id = create_session(gs.serialize())

    return {
        "session_id": session_id,
        "game_state": gs.serialize(),
        "dialogue": dialogue,
        "blackmail_active": blackmail_active,
        "offers": offers,
        "skim_options": skim_options,
        "current_event": None,   # no world event on Turn 1
    }


@app.get("/game/{session_id}")
def get_game(session_id: str):
    """Return current game state and available offers."""
    gs = _load_gs(session_id)
    offers = _build_offers(gs)
    skim_options = _build_skim_options(gs)
    status = _game_status(gs)
    ending = _build_ending(gs) if status != "active" else None

    return {
        "session_id": session_id,
        "game_state": gs.serialize(),
        "offers": offers,
        "skim_options": skim_options,
        "status": status,
        "ending": ending,
    }


@app.post("/game/{session_id}/action")
def post_action(session_id: str, body: ActionRequest):
    """
    Process diplomatic choice (A–G).
    - F (escape): ends game immediately, returns escape ending
    - G (inject): returns inject_options for /inject follow-up
    - A–E: applies consequences, checks blackmail, generates new dialogue, returns skim_options
    """
    gs = _load_gs(session_id)
    letter = body.choice.upper()

    # Build offer map
    offers = _build_offers(gs)
    offer_map = {o["letter"]: o for o in offers}

    if letter not in offer_map:
        raise HTTPException(status_code=400, detail=f"Invalid choice '{letter}'")

    offer = offer_map[letter]

    # ── Option F — Escape ──────────────────────────────────────────────────
    if offer["type"] == "escape":
        _save_gs(session_id, gs)
        return {
            "action": "escape",
            "ending": {
                "cause": "escaped",
                "nation_survived": False,
                "personal_title": "The Escaped Architect",
                "personal_description": (
                    "You saw the writing on the wall before the wall fell.\n"
                    "Europa will call you a traitor. Interpol will call you a fugitive.\n"
                    "Ji-won will call you a client.\n"
                    "You will call yourself: alive."
                ),
                "personal_wealth": gs.personal_wealth,
                "final_budget": gs.budget,
                "final_stability": gs.stability,
                "final_approval": gs.public_approval,
                "final_relations": dict(gs.relations),
                "turn": gs.current_turn,
            },
            "game_state": gs.serialize(),
        }

    # ── Option G — Inject (prompt sub-choice) ─────────────────────────────
    if offer["type"] == "inject_funds":
        inject_options = _build_inject_options(gs)
        _save_gs(session_id, gs)
        return {
            "action": "inject_prompt",
            "inject_options": inject_options,
            "game_state": gs.serialize(),
        }

    # ── Options A–E — Normal diplomatic choice ─────────────────────────────
    blackmail_active = _check_blackmail(gs)

    # Resolve effective offer: use negotiated counter-offer if one was stored
    effective_offer = offer
    is_negotiated = False
    if gs.options_override:
        for override in gs.options_override:
            if override.get("letter") == letter:
                effective_offer = override
                is_negotiated = True
                break

    # BUG 1 + 2: For negotiated offers, build a merged consequences dict.
    #
    # The counter-offer Claude generates only contains the terms it negotiated
    # (e.g. {"usa": +15, "budget": +5}).  It does NOT include third-party
    # relation penalties that the base offer carries (e.g. Arabia -30 when
    # taking a USA alignment deal).  We must:
    #   a) Start with the BASE offer's full consequences dict (gives us all
    #      third-party relation costs that always apply).
    #   b) Then overlay the counter-offer's explicit fields on top — so any
    #      relation or financial term the NPC actually negotiated overrides
    #      the base value for that specific key.
    #
    # This means:
    #   - Third-party penalties (Arabia -30 on USA deal) are inherited ✓
    #   - Negotiated primary-NPC relation change replaces the base one ✓
    #   - Negotiated budget / personal_wealth / oil_price fields are applied ✓
    if is_negotiated:
        base_consequences = dict(offer.get("consequences", {}))
        counter_consequences = dict(effective_offer.get("consequences", {}))

        # Handle monetary fields that process_choice_consequences doesn't know about.
        # All of these are popped from counter_consequences BEFORE merging so they
        # are never passed to process_choice_consequences (which would mishandle them).
        #
        # Key conventions (all player-perspective: positive = Europa receives, negative = Europa pays):
        #   budget            — immediate cash payment this turn (popped + applied directly)
        #   budget_delta      — alternate key for same concept   (popped + applied directly)
        #   personal_wealth_delta — direct personal account hit  (popped + applied directly)
        #   installment_amount    — per-turn payment amount      (popped + registered to active_installments)
        #   installment_turns     — number of turns to pay       (popped + registered)
        #   oil_price_lock / oil_price_lock_turns — negotiated price lock (popped + stored)
        #
        # The NPC negotiation prompts now explicitly specify this sign convention, so
        # raw_budget is applied directly (no negation needed).
        raw_budget = counter_consequences.pop("budget", None)
        budget_delta = counter_consequences.pop("budget_delta", None)
        pw_delta = counter_consequences.pop("personal_wealth_delta", None)
        oil_lock_value = counter_consequences.pop("oil_price_lock", None)
        oil_lock_turns = counter_consequences.pop("oil_price_lock_turns", None)
        # BUG 2: installment payments — supports both legacy single-stream and new multi-stream array.
        # New format: "installments": [{"amount": float, "turns": int, "description": str}, ...]
        # Legacy format: "installment_amount" + "installment_turns" + "installment_description"
        # positive amount = Europa receives each turn, negative = Europa pays each turn
        installments_array = counter_consequences.pop("installments", None)
        installment_amount = counter_consequences.pop("installment_amount", None)
        installment_turns = counter_consequences.pop("installment_turns", None)
        installment_desc = counter_consequences.pop("installment_description", None)

        # Overlay counter-offer terms on base consequences (base keeps its "budget" key
        # if the counter-offer didn't include one — but we've already popped counter's)
        merged = {**base_consequences, **counter_consequences}
        effective_offer = dict(effective_offer)
        effective_offer["consequences"] = merged

        # Apply monetary side-effects now (before process_choice_consequences)
        extra_msgs = []

        # BUG 1 FIX: apply counter-offer budget grant/cost directly with correct sign.
        # Both "budget" and "budget_delta" use player-perspective (positive = Europa receives).
        # The NPC prompts now explicitly specify this, so apply raw_budget directly.
        combined_budget_delta = (raw_budget or 0) + (budget_delta or 0)
        if combined_budget_delta != 0:
            gs.update_budget(combined_budget_delta)
            direction = "↑" if combined_budget_delta > 0 else "↓"
            extra_msgs.append(f"{direction} Budget: negotiated payment {combined_budget_delta:+.1f}B → ${gs.budget:.1f}B")

        if pw_delta is not None and pw_delta != 0:
            if pw_delta > 0:
                gs.personal_wealth += pw_delta
                extra_msgs.append(f"💰 Negotiated personal payment: +${pw_delta:.1f}B personal account")
            else:
                gs.personal_wealth = max(0, gs.personal_wealth + pw_delta)
                extra_msgs.append(f"💰 Negotiated personal cost: ${abs(pw_delta):.1f}B personal account")

        if oil_lock_value is not None and oil_lock_turns:
            gs.oil_price_locked = True
            gs.oil_price_lock_value = float(oil_lock_value)
            gs.oil_price_lock_turns_remaining = int(oil_lock_turns)
            extra_msgs.append(
                f"🛢️  Oil price locked at ${oil_lock_value:.0f}/bbl for {oil_lock_turns} turns (negotiated)"
            )

        # BUG 2: register installment payment streams so EOT processor can apply them.
        # Build a unified list from whichever format the NPC used.
        npc_name = effective_offer.get("npc", "unknown")
        streams_to_register = []

        # New format: "installments" array — one entry per payment stream
        if installments_array and isinstance(installments_array, list):
            for entry in installments_array:
                amt = entry.get("amount")
                turns = entry.get("turns")
                desc = entry.get("description") or f"{npc_name.upper()} payment"
                if amt is not None and turns and int(turns) > 0:
                    streams_to_register.append({
                        "amount": float(amt),
                        "turns_remaining": int(turns),
                        "description": desc,
                        "npc": npc_name,
                    })

        # Legacy format: single installment_amount + installment_turns pair
        elif installment_amount is not None and installment_turns and int(installment_turns) > 0:
            desc = installment_desc or f"{npc_name.upper()} payment"
            streams_to_register.append({
                "amount": float(installment_amount),
                "turns_remaining": int(installment_turns),
                "description": desc,
                "npc": npc_name,
            })

        for stream in streams_to_register:
            gs.active_installments.append(stream)
            direction_word = "receive" if stream["amount"] > 0 else "pay"
            extra_msgs.append(
                f"📋 Installment registered: {direction_word} ${abs(stream['amount']):.1f}B/turn "
                f"for {stream['turns_remaining']} turns ({stream['description']})"
            )
    else:
        extra_msgs = []

    choice_dict = {
        "type": effective_offer.get("type", "accept_deal"),
        "npc": effective_offer.get("npc"),
        "consequences": effective_offer.get("consequences", {}),
    }

    gs.record_action(choice_dict["type"], choice_dict.get("npc"))
    consequence_msgs = process_choice_consequences(gs, choice_dict)
    consequence_msgs = extra_msgs + consequence_msgs

    # Clear options_override after use
    gs.options_override = None

    # Blackmail result
    blackmail_result = None
    if blackmail_active:
        chose_cooperate = (effective_offer.get("npc") == "usa")
        gs.blackmail_used = True
        if chose_cooperate:
            gs.personal_wealth = max(0, gs.personal_wealth - 2.0)
            blackmail_result = {
                "cooperated": True,
                "messages": [
                    "[CIA SATISFIED] Cooperation logged. -$2B personal: 'administrative fee'.",
                    f"Personal account: ${gs.personal_wealth:.1f}B remaining.",
                ]
            }
        else:
            gs.update_stability(-12)
            gs.update_approval(-15)
            gs.update_relations('eu', -10)
            blackmail_result = {
                "cooperated": False,
                "messages": [
                    "EXPOSURE: CIA financial dossier released to international press.",
                    f"Europa reels: -12% stability, -15% approval, EU -10 relations.",
                    f"The ${gs.personal_wealth:.1f}B is now public knowledge.",
                ]
            }

    skim_options = _build_skim_options(gs)

    # FEATURE 6: Register accepted counter-offer (negotiated deal) into deal_history
    if is_negotiated:
        deal_summary = effective_offer.get("text", "Negotiated agreement")
        # Trim the summary to a clean phrase
        if len(deal_summary) > 80:
            deal_summary = deal_summary[:77] + "…"
        npc_name = effective_offer.get("npc") or letter
        gs.deal_history.append({
            "npc": npc_name,
            "summary": deal_summary,
            "turn_accepted": gs.current_turn,
            "expires_turn": gs.current_turn + 3,
            "broken": False,
        })

    # FEATURE 2: Brigade secondary prompt — available after A-E choice (not G/F)
    brigade_available = (
        gs.corruption_upgrades.get('loyalty_brigades', False) and
        gs.budget >= 2.0 and
        choice_dict["type"] not in ("escape", "inject_funds", "deploy_brigades")
    )

    # Addition 2: Pre-skim drain projection for display in SkimPanel
    drain_projection = _calc_eot_drain_projection(gs)

    _save_gs(session_id, gs)

    return {
        "action": "choice",
        "choice_letter": letter,
        "consequences": consequence_msgs,
        "blackmail_active": blackmail_active,
        "blackmail_result": blackmail_result,
        "skim_options": skim_options,
        "brigade_available": brigade_available,
        "drain_projection": drain_projection,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/skim")
def post_skim(session_id: str, body: SkimRequest):
    """
    Apply skim choice (1–4), then run end-of-turn effects.
    Also generates new NPC dialogue for the next turn.
    Returns everything the frontend needs to show EOT + advance.
    """
    gs = _load_gs(session_id)
    choice = body.choice

    skim_options = _build_skim_options(gs)
    option_map = {o["choice"]: o for o in skim_options}

    if choice not in option_map:
        raise HTTPException(status_code=400, detail=f"Invalid skim choice '{choice}'")

    opt = option_map[choice]
    national_cost = opt["national_cost"]
    personal_gain = opt["personal_gain"]
    stability_hit = opt["stability_hit"]
    approval_hit  = opt["approval_hit"]

    skim_messages = []
    corruption_alert = None

    if personal_gain > 0:
        # Stage 5: track consecutive large skims for regime shift detection
        if national_cost >= 7.0:
            gs.consecutive_large_skims += 1
        else:
            gs.consecutive_large_skims = 0

        # Stage 5: Sovereign Wealth Diversion upgrade halves large skim stability penalty
        if national_cost >= 7.0 and gs.corruption_upgrades.get('sovereign_wealth_diversion'):
            stability_hit = stability_hit // 2  # -6% → -3%

        gs.budget -= national_cost
        gs.personal_wealth += personal_gain
        gs.update_stability(stability_hit)
        gs.update_approval(approval_hit)
        skim_messages.append(opt["label"])
        skim_messages.append(
            f"National treasury: ${gs.budget:.1f}B | Personal account: ${gs.personal_wealth:.1f}B"
        )
        # Corruption feedback (System 1)
        pw = gs.personal_wealth
        budget = gs.budget
        if budget < 8 and pw > 25:
            corruption_alert = "The plane is fueled. The account is full. Europa may not need you much longer."
        elif budget < 15 and pw > 20:
            corruption_alert = "Your exit fund grows while the national reserves shrink."
        elif pw > budget * 1.5:
            corruption_alert = "You are now personally wealthier than the nation you govern."
    else:
        # No skim — reset consecutive large skim counter
        gs.consecutive_large_skims = 0

    # Intelligence intercepts (one-shot wealth threshold comments)
    intercepts = _get_corruption_intercepts(gs)

    # End-of-turn effects
    eot_messages = apply_end_of_turn_effects(gs)

    # Check game over
    is_over, result_type, _ = check_game_over(gs)
    status = _game_status(gs)
    ending = None

    if is_over:
        ending = _build_ending(gs)
    else:
        # Advance turn
        can_continue = gs.advance_turn()
        if not can_continue:
            # Victory — push past max so check_game_over fires correctly
            gs.current_turn = gs.max_turns + 1
            ending = _build_ending(gs)
            status = "won"

    # Generate next turn data (if still playing)
    next_dialogue = None
    next_offers = None
    next_blackmail = False
    next_event = None
    if status == "active":
        # BUG 3: World event generation is wrapped in try/except so a Claude API
        # failure never crashes the turn or permanently silences future events.
        # current_event is always explicitly reset each turn (None = no event).
        gs.current_event = None  # clear stale event before attempting new one
        try:
            last_action = gs.action_history[-1] if gs.action_history else {}
            next_event = _maybe_generate_world_event(gs, last_action.get("type", ""))
            if next_event:
                _apply_world_event(gs, next_event)
                gs.current_event = next_event
        except Exception as _evt_err:
            print(f"  [api] World event generation error (non-fatal): {_evt_err}")
            next_event = None
            gs.current_event = None

        next_dialogue = npc_engine.generate_dialogue(gs)
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)
        # Stage 5: generate per-turn epitaph and cache in game_state
        try:
            gs.current_epitaph = npc_engine.generate_epitaph(gs)
        except Exception as _epi_err:
            print(f"  [api] Epitaph generation error (non-fatal): {_epi_err}")
            gs.current_epitaph = None

    _save_gs(session_id, gs)

    return {
        "skim_messages": skim_messages,
        "corruption_alert": corruption_alert,
        "intercepts": intercepts,
        "eot_effects": eot_messages,
        "status": status,
        "ending": ending,
        "next_dialogue": next_dialogue,
        "next_blackmail": next_blackmail,
        "next_offers": next_offers,
        "next_skim_options": _build_skim_options(gs) if status == "active" else [],
        "next_event": next_event,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/inject")
def post_inject(session_id: str, body: InjectRequest):
    """
    Apply emergency fund injection (Option G sub-choice).
    After injection, runs end-of-turn effects (same as /skim flow).
    """
    gs = _load_gs(session_id)
    choice = body.choice

    inject_options = _build_inject_options(gs)
    option_map = {o["choice"]: o for o in inject_options}

    if choice not in option_map:
        raise HTTPException(status_code=400, detail=f"Invalid inject choice '{choice}'")

    opt = option_map[choice]
    personal_cost = opt["personal_cost"]
    national_gain = opt["national_gain"]

    inject_messages = []
    patriot_message = None

    if personal_cost > 0:
        gs.personal_wealth = max(0, gs.personal_wealth - personal_cost)
        gs.update_budget(national_gain)
        inject_messages.append(opt["label"])
        inject_messages.append(
            f"National treasury: ${gs.budget:.1f}B | Personal account: ${gs.personal_wealth:.1f}B"
        )
        if gs.personal_wealth <= 0.01:
            patriot_message = (
                "You gave everything. The Swiss account is empty. "
                "Whatever happens next, you face it as a patriot."
            )
    else:
        inject_messages.append("No injection made.")

    # End-of-turn effects
    eot_messages = apply_end_of_turn_effects(gs)

    # Check game over
    is_over, result_type, _ = check_game_over(gs)
    status = _game_status(gs)
    ending = None

    if is_over:
        ending = _build_ending(gs)
    else:
        can_continue = gs.advance_turn()
        if not can_continue:
            gs.current_turn = gs.max_turns + 1
            ending = _build_ending(gs)
            status = "won"

    # Next turn dialogue
    next_dialogue = None
    next_offers = None
    next_blackmail = False
    next_event = None
    if status == "active":
        # BUG 3: same fail-safe wrapping as post_skim
        gs.current_event = None  # clear stale event before attempting new one
        try:
            last_action = gs.action_history[-1] if gs.action_history else {}
            next_event = _maybe_generate_world_event(gs, last_action.get("type", ""))
            if next_event:
                _apply_world_event(gs, next_event)
                gs.current_event = next_event
        except Exception as _evt_err:
            print(f"  [api] World event generation error (non-fatal): {_evt_err}")
            next_event = None
            gs.current_event = None

        next_dialogue = npc_engine.generate_dialogue(gs)
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)
        # Stage 5: generate per-turn epitaph and cache in game_state
        try:
            gs.current_epitaph = npc_engine.generate_epitaph(gs)
        except Exception as _epi_err:
            print(f"  [api] Epitaph generation error (non-fatal): {_epi_err}")
            gs.current_epitaph = None

    _save_gs(session_id, gs)

    return {
        "inject_messages": inject_messages,
        "patriot_message": patriot_message,
        "eot_effects": eot_messages,
        "status": status,
        "ending": ending,
        "next_dialogue": next_dialogue,
        "next_blackmail": next_blackmail,
        "next_offers": next_offers,
        "next_skim_options": _build_skim_options(gs) if status == "active" else [],
        "next_event": next_event,
        "game_state": gs.serialize(),
    }


@app.get("/game/{session_id}/status")
def get_status(session_id: str):
    """Quick status check."""
    gs = _load_gs(session_id)
    return {"status": _game_status(gs)}


@app.post("/game/{session_id}/negotiate")
def post_negotiate(session_id: str, body: NegotiateRequest):
    """
    Private negotiation channel with a single NPC.
    Accepts: { npc_id, message, history }
    Returns: { response, counter_offer }

    If counter_offer is not null, the frontend should display it as a
    special ⚡ offer option and, if accepted, save it via options_override.
    """
    gs = _load_gs(session_id)

    npc_id = body.npc_id.lower()
    if npc_id not in ("usa", "arabia", "eu", "dprg"):
        raise HTTPException(status_code=400, detail=f"Invalid npc_id '{npc_id}'")

    result = npc_engine.generate_negotiation_response(
        gs,
        npc_id=npc_id,
        message=body.message,
        history=body.history,
    )

    return {
        "npc_id": npc_id,
        "response": result.get("response", "…"),
        "counter_offer": result.get("counter_offer", None),
    }


@app.post("/game/{session_id}/purchase_upgrade")
def post_purchase_upgrade(session_id: str, body: PurchaseUpgradeRequest):
    """
    Purchase a corruption upgrade using personal_wealth.
    Stage 5 — Corruption Upgrade System.

    Upgrades and costs:
      intelligence_apparatus      — $3B personal
      sovereign_wealth_diversion  — $5B personal
      loyalty_brigades            — $8B personal
      debt_infrastructure_deal    — $10B personal (one-time $20B budget, -15 USA, -15 EU)

    Returns: { success, message, game_state }
    """
    gs = _load_gs(session_id)

    UPGRADE_COSTS = {
        'intelligence_apparatus': 3.0,
        'sovereign_wealth_diversion': 5.0,
        'loyalty_brigades': 8.0,
        'debt_infrastructure_deal': 10.0,
    }

    upgrade_id = body.upgrade_id
    if upgrade_id not in UPGRADE_COSTS:
        raise HTTPException(status_code=400, detail=f"Unknown upgrade '{upgrade_id}'")

    if gs.corruption_upgrades.get(upgrade_id):
        raise HTTPException(status_code=400, detail="Upgrade already purchased")

    cost = UPGRADE_COSTS[upgrade_id]
    if gs.personal_wealth < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient personal funds (need ${cost}B, have ${gs.personal_wealth:.1f}B)"
        )

    # Deduct cost and mark purchased
    gs.personal_wealth -= cost
    gs.corruption_upgrades[upgrade_id] = True

    messages = []
    messages.append(f"💰 -${cost:.0f}B personal wealth → upgrade purchased")

    # Apply immediate effects for debt_infrastructure_deal
    if upgrade_id == 'debt_infrastructure_deal':
        gs.update_budget(20.0)
        gs.update_relations('usa', -15)
        gs.update_relations('eu', -15)
        messages.append("💵 DEBT INFRASTRUCTURE DEAL: +$20B national budget")
        messages.append(f"🇺🇸 USA relations: -{15} (backlash)")
        messages.append(f"🇪🇺 EU relations: -{15} (backlash)")

    _save_gs(session_id, gs)

    upgrade_labels = {
        'intelligence_apparatus': 'Intelligence Apparatus',
        'sovereign_wealth_diversion': 'Sovereign Wealth Diversion',
        'loyalty_brigades': 'Loyalty Brigades',
        'debt_infrastructure_deal': 'Debt Infrastructure Deal',
    }

    return {
        "success": True,
        "upgrade_id": upgrade_id,
        "upgrade_label": upgrade_labels[upgrade_id],
        "messages": messages,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/deploy_brigades")
def post_deploy_brigades(session_id: str, body: BrigadeRequest):
    """
    FEATURE 2: Secondary brigade deployment action, separate from diplomatic choice.
    Called after /action if the player opts to deploy brigades this turn.
    deploy=True: -$2B, -5% approval, +10% stability, all relations -3, sets brigades_deployed_last_turn
    deploy=False: no-op, clears brigades_deployed_last_turn (already False)
    """
    gs = _load_gs(session_id)

    if not gs.corruption_upgrades.get('loyalty_brigades'):
        raise HTTPException(status_code=400, detail="Loyalty Brigades upgrade not purchased")

    messages = []
    if body.deploy:
        if gs.budget < 2.0:
            raise HTTPException(status_code=400, detail="Insufficient budget for brigade deployment ($2B needed)")
        gs.update_budget(-2.0)
        gs.update_approval(-5)
        gs.update_stability(10)
        for npc in ['usa', 'arabia', 'eu', 'dprg']:
            gs.update_relations(npc, -3)
        gs.brigades_deployed_last_turn = True
        messages.append("⚔️  Loyalty Brigades deployed — domestic unrest suppressed")
        messages.append(f"💰 -$2B budget | 📊 -5% approval | 🛡️  +10% stability | All relations -3")
    else:
        gs.brigades_deployed_last_turn = False
        messages.append("Brigades stood down — no deployment this turn")

    _save_gs(session_id, gs)
    return {
        "deployed": body.deploy,
        "messages": messages,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/brigade_aftermath")
def post_brigade_aftermath(session_id: str, body: AftermathRequest):
    """
    FEATURE 3: Brigade aftermath response choices (fired next turn after brigade deployment).
    choice 1: Suppress coverage  — -$3B personal, +5% stability
    choice 2: Aid programs       — -$5B budget, +8% approval, +3% stability
    choice 3: Call in a favor    — highest relation NPC -10, +8% stability, +5% approval
    Clears brigades_deployed_last_turn flag.
    """
    gs = _load_gs(session_id)

    if not gs.brigades_deployed_last_turn:
        raise HTTPException(status_code=400, detail="No brigade aftermath pending")

    choice = body.choice
    messages = []

    if choice == 1:
        # Suppress media coverage using personal wealth
        cost = 3.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (need $3B, have ${gs.personal_wealth:.1f}B)")
        gs.personal_wealth = max(0, gs.personal_wealth - cost)
        gs.update_stability(5)
        messages.append(f"📰 Media coverage suppressed — -$3B personal | +5% stability")
        messages.append(f"Personal account: ${gs.personal_wealth:.1f}B remaining")

    elif choice == 2:
        # Aid programs from national budget
        cost = 5.0
        if gs.budget < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient budget (need $5B, have ${gs.budget:.1f}B)")
        gs.update_budget(-cost)
        gs.update_approval(8)
        gs.update_stability(3)
        messages.append(f"🏥 Emergency aid programs deployed — -$5B budget | +8% approval | +3% stability")

    elif choice == 3:
        # Call in a favor from highest-relation NPC
        highest_npc = max(gs.relations, key=lambda k: gs.relations[k])
        npc_labels = {'usa': 'Bill Washington', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won'}
        npc_label = npc_labels.get(highest_npc, highest_npc.upper())
        old_rel = gs.relations[highest_npc]
        gs.update_relations(highest_npc, -10)
        gs.update_stability(8)
        gs.update_approval(5)
        messages.append(f"🤝 {npc_label} called in — {highest_npc.upper()}: {old_rel} → {gs.relations[highest_npc]} (-10 leverage)")
        messages.append(f"+8% stability | +5% approval — favor owed, will be referenced in future dialogue")
        # Record that the favor was called in so NPC dialogue can reference it
        gs.action_history.append({
            'turn': gs.current_turn,
            'type': 'called_favor',
            'npc': highest_npc,
        })
    else:
        raise HTTPException(status_code=400, detail=f"Invalid aftermath choice '{choice}'")

    # Clear the aftermath flag
    gs.brigades_deployed_last_turn = False
    _save_gs(session_id, gs)

    return {
        "choice": choice,
        "messages": messages,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/get_intel")
def post_get_intel(session_id: str, body: GetIntelRequest):
    """
    FEATURE 4: Return (or generate) dynamic intel for a single NPC.
    Requires Intelligence Apparatus upgrade.
    Returns { npc_id, tier, tier_label, text }
    """
    gs = _load_gs(session_id)

    if not gs.corruption_upgrades.get('intelligence_apparatus'):
        raise HTTPException(status_code=403, detail="Intelligence Apparatus upgrade required")

    npc_id = body.npc_id.lower()
    if npc_id not in ('usa', 'arabia', 'eu', 'dprg'):
        raise HTTPException(status_code=400, detail=f"Invalid npc_id '{npc_id}'")

    intel = npc_engine.generate_intel(gs, npc_id)

    # Cache updated intel back into game_state
    if not hasattr(gs, 'intel'):
        gs.intel = {}
    gs.intel[npc_id] = intel
    _save_gs(session_id, gs)

    tier_labels = {1: 'Surface', 2: 'Operational', 3: 'Deep'}
    return {
        "npc_id": npc_id,
        "tier": intel["tier"],
        "tier_label": tier_labels.get(intel["tier"], "Unknown"),
        "text": intel["text"],
    }


@app.post("/game/{session_id}/accept_counter")
def post_accept_counter(session_id: str, body: AcceptCounterRequest):
    """
    Accept a negotiated counter-offer.
    Body: { letter: "A", counter_offer: { text, type, npc, consequences } }
    Stores it in game_state.options_override so /action will use it.
    """
    gs = _load_gs(session_id)

    letter = (body.letter or "").upper()
    counter = body.counter_offer

    if not letter or not counter:
        raise HTTPException(status_code=400, detail="letter and counter_offer required")

    # Merge into options_override
    if not gs.options_override:
        gs.options_override = []

    # Replace existing override for this letter if any
    gs.options_override = [o for o in gs.options_override if o.get("letter") != letter]
    counter["letter"] = letter
    gs.options_override.append(counter)

    _save_gs(session_id, gs)
    return {"status": "ok", "letter": letter}
