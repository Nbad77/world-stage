"""
THE WORLD STAGE — FastAPI Backend
Serves game state, processes turns, calls npc_engine for dialogue.
Game logic is entirely in Python (game_state, turn_processor).
Claude generates dialogue only (npc_engine).

Endpoints:
  POST /game/new               → { session_id, game_state, offers, dialogue }
  GET  /game/{id}              → { game_state, offers }
  POST /game/{id}/action       → { consequences, blackmail, game_state, offers }
  POST /game/{id}/skim         → { skim_result, intercepts, eot_effects, game_state, status }
  POST /game/{id}/inject       → { inject_result, game_state }
  GET  /game/{id}/status       → { status: active|won|lost|escaped }
"""

import sys
import os
from pathlib import Path

# Ensure project root is importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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

    session_id = create_session(gs.serialize())

    return {
        "session_id": session_id,
        "game_state": gs.serialize(),
        "dialogue": dialogue,
        "blackmail_active": blackmail_active,
        "offers": offers,
        "skim_options": skim_options,
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

    # Build a full offer dict compatible with process_choice_consequences
    choice_dict = {
        "type": offer.get("type", "accept_deal"),
        "npc": offer.get("npc"),
        "consequences": offer.get("consequences", {}),
    }

    gs.record_action(choice_dict["type"], choice_dict.get("npc"))
    consequence_msgs = process_choice_consequences(gs, choice_dict)

    # Blackmail result
    blackmail_result = None
    if blackmail_active:
        chose_cooperate = (offer.get("npc") == "usa")
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
    _save_gs(session_id, gs)

    return {
        "action": "choice",
        "choice_letter": letter,
        "consequences": consequence_msgs,
        "blackmail_active": blackmail_active,
        "blackmail_result": blackmail_result,
        "skim_options": skim_options,
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

    # Generate next turn dialogue (if still playing)
    next_dialogue = None
    next_offers = None
    next_blackmail = False
    if status == "active":
        next_dialogue = npc_engine.generate_dialogue(gs)
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)

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
    if status == "active":
        next_dialogue = npc_engine.generate_dialogue(gs)
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)

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
        "game_state": gs.serialize(),
    }


@app.get("/game/{session_id}/status")
def get_status(session_id: str):
    """Quick status check."""
    gs = _load_gs(session_id)
    return {"status": _game_status(gs)}
