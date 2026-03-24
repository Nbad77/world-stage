"""
THE WORLD STAGE — FastAPI Backend
Serves game state, processes turns, calls npc_engine for dialogue.
Game logic is entirely in Python (game_state, turn_processor).
Claude generates dialogue only (npc_engine).

Endpoints:
  POST /game/new                    -> { session_id, game_state, offers, dialogue }
  GET  /game/{id}                   -> { game_state, offers }
  POST /game/{id}/action            -> { consequences, blackmail, game_state, offers }
  POST /game/{id}/skim              -> { skim_result, intercepts, eot_effects, game_state, status }
  POST /game/{id}/inject            -> { inject_result, game_state }
  GET  /game/{id}/status            -> { status: active|won|lost|escaped }
  POST /game/{id}/negotiate         -> { response, counter_offer }
  POST /game/{id}/election          -> { result_key, consequences, npc_reactions, game_state }
  POST /game/{id}/domestic_action   -> { success, action, changes, game_state }
"""

import sys
import os
# Fix A: Force UTF-8 on Windows to prevent UnicodeEncodeError from emoji in print()
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import re
import random
from pathlib import Path

# Ensure project root is importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Depends, Request
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
    update_npc_bilateral_relations,
    apply_election_consequences,
    apply_domestic_action,
    DOMESTIC_ACTION_CONSEQUENCES,
    process_intel_budget,
    INTEL_BUDGET_OPTIONS,
    apply_tech_gain,
    TECH_SOURCES,
    exile_sequence_start,
    process_exile_eod,
)
from db import init_db, create_session, load_session, save_session
from auth import get_current_user, get_optional_user
from database import User, GameStatePersisted, engine as accounts_engine, init_accounts_db
from sqlmodel import Session as SQLModelSession

# ── 8A: Centralized NPC constants ─────────────────────────────────────────────
ALL_NPCS = ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china')
ALL_NPC_LABELS = {
    'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU',
    'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'
}
ALL_NPC_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'
}

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
    init_accounts_db()
    print(f"[TEST] /test/reset endpoint registered")
    print(f"[TEST] /test/set_state endpoint registered")
    print(f"[TEST] /test/snapshots endpoint registered")


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
    last_counter_offer: Any = None  # most recent counter_offer the frontend has seen (for re-emit fallback)
    player_initiated: bool = False  # Session 7B: True when player contacts NPC from sidebar

class AcceptCounterRequest(BaseModel):
    letter: str           # "A"-"D"
    counter_offer: Any    # the counter_offer dict from negotiate response
    covert: bool = False  # fixes_13 Fix 24: Ji-won covert transaction (DPRG 60+)

class PurchaseUpgradeRequest(BaseModel):
    upgrade_id: str  # 'intelligence_apparatus' | 'sovereign_wealth_diversion' | 'loyalty_brigades' | 'debt_infrastructure_deal'

class BrigadeRequest(BaseModel):
    deploy: bool           # True = deploy brigades this turn (legacy single-deploy)
    operation: int = 0     # 0=stand_down, 1=domestic_suppression, 2=propaganda, 3=foreign_influence, 4=covert_apparatus
    target_npc: str = ''   # for operation 3 (foreign influence): 'usa'|'arabia'|'eu'|'dprg'

class AftermathRequest(BaseModel):
    choice: int  # 1=suppress_coverage, 2=aid_programs, 3=call_in_favor

class GetIntelRequest(BaseModel):
    npc_id: str  # 'usa' | 'arabia' | 'eu' | 'dprg'

class ElectionRequest(BaseModel):
    choice: str  # 'fair' | 'rigged' | 'canceled' | 'observers'

class DomesticActionRequest(BaseModel):
    action: str  # 'state_media_takeover' | 'judicial_capture' | 'suppress_press' | 'dissolve_opposition' | 'liquidate_journalists'

class IntelAllocationRequest(BaseModel):
    allocation: str  # 'none' | 'maintenance' | 'active' | 'expansion'

class BudgetAllocationRequest(BaseModel):
    military: int
    intelligence: int
    public_services: int
    infrastructure: int
    diplomacy: int

class EducationAllocationRequest(BaseModel):
    allocation: float  # $B per turn to allocate to education

class DebugSetStateRequest(BaseModel):
    overrides: dict  # fixes_10 Fix 7: field -> value mapping for debug panel

# Session 5 request models
class CabinetInvestRequest(BaseModel):
    axis: str       # 'military'|'intelligence'|'resource_dev'|'media'|'judicial'|'political'|'extraction'
    direction: str  # 'invest' or 'defund'

# Session 6: Axis action request models
class MilitaryActionRequest(BaseModel):
    action: str             # 'defense_procurement'|'force_projection'|'arms_export'
    target_npc: str = ''

class AxisActionRequest(BaseModel):
    action: str
    target_npc: str = ''
    amount: float = 0.0     # for offshore_transfer

# Session 6: Leverage demand response
class LeverageResponseRequest(BaseModel):
    leverage_type: str      # 'marsha_media' | 'bill_opposition'
    accept: bool            # True = agree to demand, False = decline

class AdvisorActionRequest(BaseModel):
    action: str       # 'hire'|'dismiss'|'eliminate'
    advisor_id: str

class TaxRateRequest(BaseModel):
    income_tax: Optional[float] = None
    corporate_tax: Optional[float] = None
    resource_tax: Optional[float] = None

class BlackOpRequest(BaseModel):
    operation: str      # 'fabricate_crisis'|'reputation_laundering'|'blackmail'|'false_flag'|'political_sabotage'
    target_npc: str = ''  # required for most operations

# 9.5A: Commitment model request models
class CommitmentUpgradeRequest(BaseModel):
    tier_key: str       # 'military'|'intelligence'|'diplomatic'|'social'|'education'|'resource'|'political'|'militia'

class CommitmentDowngradeRequest(BaseModel):
    tier_key: str       # same keys as upgrade

class CommitmentSkimRequest(BaseModel):
    skim_rate: float    # 0.0 to 0.50 (0% to 50%)

# 9.5A-Shadow: Shadow State request models
class ShadowUpgradeRequest(BaseModel):
    shadow_key: str     # 'media'|'judicial'|'domestic_surveillance'|'extraction'

class ShadowDowngradeRequest(BaseModel):
    shadow_key: str     # same keys as upgrade

class ShadowSkimRequest(BaseModel):
    skim_rate: float    # 0.0 to max (capped by EXTRACTION_SKIM_CEILING)

class ShadowMergerRequest(BaseModel):
    merger_type: str    # 'militia'|'surveillance'

# 10C: Operations System request models
class OperationTargetRequest(BaseModel):
    target_npc: str     # 'usa'|'arabia'|'eu'|'dprg'|'russia'|'china'

class ModernizationRequest(BaseModel):
    tranche: int        # 1|2|3

class ArmsExportRequest(BaseModel):
    target_npc: str

class IntelSharingRequest(BaseModel):
    target_npc: str
    level: int          # 1|2|3

class IntelSharingEndRequest(BaseModel):
    target_npc: str
    abrupt: bool = False

class CrisisIntelRequest(BaseModel):
    target_npc: str
    fund_from: str      # 'personal'|'national'

class KompromantUseRequest(BaseModel):
    target_npc: str
    action: str         # 'suppress'|'concession'|'burn'

class LoyaltyAssessmentRequest(BaseModel):
    advisor_id: str

class LoyaltyEnforcementRequest(BaseModel):
    advisor_id: str

class FalseFlagRequest(BaseModel):
    target_npc: str
    blame_npc: str


# 10C: Operations cap helper
def check_ops_cap(gs, op_type: str) -> bool:
    """Returns True if operation is allowed (under cap)."""
    if op_type == "legitimate":
        return gs.ops_legitimate_this_turn < 1
    elif op_type == "shadow":
        return gs.ops_shadow_this_turn < 1
    return False


# NPC ID normalization: accept both name-based and code-based IDs
_NPC_ID_MAP = {
    'bill': 'usa', 'marsha': 'eu', 'sadam': 'arabia',
    'volkov': 'russia', 'wei': 'china', 'ji_won': 'dprg',
    'usa': 'usa', 'arabia': 'arabia', 'eu': 'eu',
    'dprg': 'dprg', 'russia': 'russia', 'china': 'china',
}

def _normalize_npc(npc_id: str) -> str:
    """Normalize NPC ID to codebase format ('usa', 'arabia', etc.)."""
    normalized = _NPC_ID_MAP.get(npc_id.lower().strip())
    if not normalized:
        raise HTTPException(status_code=400, detail=f"Invalid NPC ID: {npc_id}")
    return normalized


# ── fixes_13 Fix 22+23: Negotiate cost with diplomat + political axis discounts ─
def _get_discounted_negotiate_cost(gs, npc_id: str) -> tuple:
    """Return (final_cost, base_cost, discount_label) after diplomat + political axis discounts.
    Stacks multiplicatively: base × diplomat_mult × political_mult."""
    _base_cost = npc_engine.get_negotiate_cost(gs.relations.get(npc_id, 50))
    _mult = 1.0
    _label_parts = []

    # v2: Diplomat advisor discount (competence-based)
    from advisor_engine import get_diplomat_discount
    _diplomat_mult = get_diplomat_discount(gs)
    if _diplomat_mult < 1.0:
        _advisors = getattr(gs, 'advisors', {})
        _da = _advisors.get('diplomat', {})
        _comp = _da.get('competence', 60)
        if _diplomat_mult == 0.0:
            _mult = 0.0
            _label_parts.append('Diplomat (free)')
            print(f"  [api] Diplomat (competence {_comp}) -> FREE negotiation")
        else:
            _mult *= _diplomat_mult
            pct = int((1 - _diplomat_mult) * 100)
            _label_parts.append(f'Diplomat -{pct}%')
            print(f"  [api] Diplomat (competence {_comp}) -> {pct}% discount")

    # Fix 23: Political axis discount (stacks multiplicatively)
    _political = getattr(gs, 'cabinet_axes', {}).get('political', 0)
    if _political >= 8:
        _mult *= 0.5  # 50% discount
        _label_parts.append('Political -50%')
        print(f"  [api] Fix 23: Political axis {_political} -> 50% discount")
    elif _political >= 5:
        _mult *= 0.75  # 25% discount
        _label_parts.append('Political -25%')
        print(f"  [api] Fix 23: Political axis {_political} -> 25% discount")

    _final = round(_base_cost * _mult, 2)
    _label = ' + '.join(_label_parts) if _label_parts else ''
    return (_final, _base_cost, _label)

# fixes_13 Fix 21: Bond financing
class BondRequest(BaseModel):
    amount: int  # 5 or 10 (billions)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_game_ownership(session_id: str, user):
    """Verify the game belongs to the authenticated user. Skips check for guests (user=None)."""
    if user is None:
        return  # Guest mode — no ownership check
    import uuid as _uuid
    with SQLModelSession(accounts_engine) as session:
        game_record = session.get(GameStatePersisted, _uuid.UUID(session_id))
        if game_record is not None and game_record.user_id != user.id:
            raise HTTPException(status_code=403, detail="Game belongs to a different user")


def _load_gs(session_id: str) -> GameState:
    """Load GameState from DB or raise 404."""
    data = load_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    gs = GameState.deserialize(data)
    print(f"[RELIABILITY] field present, value={gs.reliability_score}")
    print(f"[MORNING] chief_of_staff_intro_done={gs.chief_of_staff_intro_done}")
    return gs


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
    # ITEM 4: Weapons Purchase — conditional choices
    if gs.relations['usa'] >= 50:
        offers.append({
            "letter": "H",
            "text": "Purchase US defense package (-$2.5B, Military +15, Arabia -5, DPRG -5, USA +3)",
            "type": "accept_deal",
            "npc": "usa",
            "consequences": {
                "budget": -2.5,
                "military": 15,
                "usa": 3,
                "arabia": -5,
                "dprg": -5,
            },
        })

    # Session 3 Addendum 2: Add consequence warning flags to offers.
    # Shows which third-party NPCs will be affected without revealing exact penalties.
    _npc_labels = dict(ALL_NPC_LABELS)
    for offer in offers:
        consequences = offer.get('consequences', {})
        deal_npc = offer.get('npc', '')
        affected = []
        for npc_key in list(ALL_NPCS):
            if npc_key == deal_npc:
                continue  # don't warn about the deal-giver's own relation change
            penalty = consequences.get(npc_key, 0)
            if penalty < 0:
                affected.append(_npc_labels.get(npc_key, npc_key.upper()))
        if affected:
            offer['relation_warning'] = f"⚠️ Will affect {' and '.join(affected)} relations"

    # fixes_21: Deal conflict warnings — check if choice consequences hurt NPCs
    # that have active (non-broken, non-expired) deals or binding promises with player.
    _deal_history = getattr(gs, 'deal_history', [])
    _binding_promises = getattr(gs, 'binding_promises', [])
    _active_deals_by_npc = {}
    for d in _deal_history:
        if not d.get('broken') and d.get('expires_turn', 0) >= gs.current_turn:
            _active_deals_by_npc.setdefault(d['npc'], []).append(d.get('summary', 'Active deal'))
    for p in _binding_promises:
        if not p.get('broken'):
            _active_deals_by_npc.setdefault(p['npc'], []).append(p.get('promise_text', 'Binding promise'))

    for offer in offers:
        consequences = offer.get('consequences', {})
        conflicts = []
        for npc_key, deal_summaries in _active_deals_by_npc.items():
            penalty = consequences.get(npc_key, 0)
            if penalty < 0 and deal_summaries:
                for summary in deal_summaries:
                    conflicts.append({
                        'npc': npc_key,
                        'npc_label': _npc_labels.get(npc_key, npc_key.upper()),
                        'deal_summary': summary,
                    })
        if conflicts:
            offer['deal_conflicts'] = conflicts

    return offers


def _build_skim_options(gs: GameState) -> list[dict]:
    """Return available skim options given current budget.
    9.5A-Shadow: When skim_rate > 0 (persistent skim active), the per-turn skim
    prompt is discontinued. Returns only the 'proceed' option since skim_rate
    applies automatically during EOT via compute_tax_revenue().
    Legacy per-turn options still returned when skim_rate == 0 for backward compat.
    """
    _skim_rate = getattr(gs, 'skim_rate', 0.0)

    # 9.5A-Shadow: Persistent skim mode — per-turn prompt discontinued
    if _skim_rate > 0:
        from turn_processor import EXTRACTION_SKIM_CEILING
        _ext_tier = getattr(gs, 'extraction_tier', 0)
        _skim_ceiling = EXTRACTION_SKIM_CEILING.get(_ext_tier, 0.05)
        _gdp_rev = getattr(gs, 'gdp', 50.0) * getattr(gs, 'tax_rate', 0.20) if not hasattr(gs, '_last_gross_revenue') else getattr(gs, '_last_gross_revenue', 10.0)
        _est_income = round(_gdp_rev * _skim_rate, 1)
        return [
            {"choice": 1,
             "label": f"Proceed — skim rate {_skim_rate*100:.0f}% active (~${_est_income:.1f}B/turn diverted automatically)",
             "national_cost": 0, "personal_gain": 0, "stability_hit": 0, "approval_hit": 0,
             "skim_persistent": True,
             "skim_rate": _skim_rate,
             "skim_ceiling": _skim_ceiling,
             "extraction_tier": _ext_tier}
        ]

    # Legacy per-turn skim options (skim_rate == 0)
    budget = gs.budget
    # Sovereign Wealth Diversion upgrade halves large skim stability penalty (display + apply)
    has_swd = gs.corruption_upgrades.get('sovereign_wealth_diversion', False)
    # fixes_16 Fix C: Extraction L5 also halves large skim penalties
    _extraction_l5 = getattr(gs, 'extraction_l5_fired', False)
    _penalty_halved = has_swd or _extraction_l5
    large_stab = -3 if _penalty_halved else -6
    large_approval = -3 if _penalty_halved else -5
    _halved_tag = ' (↓ Extraction L5)' if _extraction_l5 and not has_swd else (' (↓ SWD)' if has_swd else '')
    large_label = (
        f"Large skim: -$7B national, +$7B personal, {large_stab}% stability, {large_approval}% approval{_halved_tag}"
    )
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
            "label": large_label,
            "national_cost": 7.0, "personal_gain": 7.0, "stability_hit": large_stab, "approval_hit": large_approval,
        })
    # fixes_16 Fix C: Extraction L7 — skim ceiling removed, add massive skim option
    _extraction_l7 = getattr(gs, 'extraction_l7_fired', False)
    if _extraction_l7 and budget >= 15.0:
        _mega_stab = -5 if _penalty_halved else -10
        _mega_approval = -4 if _penalty_halved else -8
        options.append({
            "choice": 5,
            "label": f"Massive skim: -$15B national, +$15B personal, {_mega_stab}% stability, {_mega_approval}% approval (ceiling removed)",
            "national_cost": 15.0, "personal_gain": 15.0, "stability_hit": _mega_stab, "approval_hit": _mega_approval,
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
    # FIX C (session 6): Separate unconditional and conditional payments for accurate projection.
    _unconditional_net = 0.0
    _conditional_net = 0.0
    _conditional_notes = []
    for inst in gs.active_installments:
        _amt = float(inst.get('amount', 0))
        # Match EOT: skip installments registered this turn (first payment next turn)
        _reg_turn = inst.get('registered_turn', 0)
        if _reg_turn >= gs.current_turn:
            continue
        # Match EOT: skip installments with deferred start
        _start = inst.get('start_turn')
        if _start is not None and gs.current_turn < _start:
            continue
        _cond_type = inst.get('condition_type')
        _cond_npc = inst.get('condition_npc')
        _cond_thresh = inst.get('condition_threshold')
        if _cond_type and _cond_npc:
            # Check if condition is currently met
            _actual_rel = gs.relations.get(_cond_npc, 50)
            _npc_labels_c = dict(ALL_NPC_LABELS)
            if _cond_type == 'relation_below' and _actual_rel >= _cond_thresh:
                # Condition NOT met — payment may not fire
                _conditional_net += _amt
                _conditional_notes.append(
                    f"{inst.get('description', 'payment')}: ${abs(_amt):.1f}B (conditional — {_npc_labels_c.get(_cond_npc, _cond_npc)} currently {_actual_rel}, needs below {_cond_thresh})"
                )
                continue
            elif _cond_type == 'relation_above' and _actual_rel <= _cond_thresh:
                _conditional_net += _amt
                _conditional_notes.append(
                    f"{inst.get('description', 'payment')}: ${abs(_amt):.1f}B (conditional — {_npc_labels_c.get(_cond_npc, _cond_npc)} currently {_actual_rel}, needs above {_cond_thresh})"
                )
                continue
        _unconditional_net += _amt
    installment_net = round(_unconditional_net + _conditional_net, 1)
    installment_unconditional = round(_unconditional_net, 1)
    # (skim projection log line is after GDP calculation below)

    # ── Simulate EOT pipeline: costs first, then GDP with projected approval/stability ──
    # The actual EOT runs sections 4-8 (sanctions, embargo, EU, pressure, instability,
    # military, drift) BEFORE section 9b (GDP revenue). Each section modifies approval
    # and stability, so GDP must use the post-penalty values. We simulate that here.
    _proj_approval = gs.public_approval
    _proj_stability = gs.stability
    usa_rel = gs.relations['usa']
    eu_rel = gs.relations['eu']

    # ── Section 4: USA Sanctions (budget + approval/stability simulation) ──
    _proj_sanctions_tier = 0
    sanctions_cost = 0.0
    if usa_rel <= 35:
        if usa_rel <= 4:
            # Floor collapse — bypass grace period, jump to tier 4 (matches EOT)
            _proj_sanctions_tier = 4
        elif usa_rel <= 14:
            _target = 3
            _prev = gs.usa_sanctions_tier
            _warn = getattr(gs, 'usa_sanctions_warning_turns', 0)
            if _target > _prev and _warn < 1:
                _proj_sanctions_tier = _prev  # grace period active
            else:
                _proj_sanctions_tier = min(_target, _prev + 1)
        elif usa_rel <= 24:
            _target = 2
            _prev = gs.usa_sanctions_tier
            _warn = getattr(gs, 'usa_sanctions_warning_turns', 0)
            if _target > _prev and _warn < 1:
                _proj_sanctions_tier = _prev
            else:
                _proj_sanctions_tier = min(_target, _prev + 1)
        else:
            _target = 1
            _prev = gs.usa_sanctions_tier
            _warn = getattr(gs, 'usa_sanctions_warning_turns', 0)
            if _target > _prev and _warn < 1:
                _proj_sanctions_tier = _prev
            else:
                _proj_sanctions_tier = min(_target, _prev + 1)
        sanctions_cost = {0: 0, 1: 2, 2: 4, 3: 7, 4: 10}.get(_proj_sanctions_tier, 0)
        # Simulate approval/stability effects (fixed values, not affected by crisis_mult)
        _sanctions_appr = {0: 0, 1: 3, 2: 6, 3: 9, 4: 12}
        _sanctions_stab = {0: 0, 1: 0, 2: 0, 3: 6, 4: 9}
        _proj_approval -= _sanctions_appr.get(_proj_sanctions_tier, 0)
        _proj_stability -= _sanctions_stab.get(_proj_sanctions_tier, 0)

    # ── Section 5: Arabia embargo emergency cost + approval/stability ──
    embargo_cost = 0.0
    if effective_tier >= 3:
        embargo_cost = {3: 3, 4: 5}.get(effective_tier, 0)
    # Approval/stability effects for all embargo tiers (fixed values)
    _embargo_appr = {0: 0, 1: 3, 2: 6, 3: 9, 4: 12}
    _embargo_stab = {0: 0, 1: 0, 2: 3, 3: 6, 4: 9}
    _proj_approval -= _embargo_appr.get(effective_tier, 0)
    _proj_stability -= _embargo_stab.get(effective_tier, 0)

    # ── Section 6: EU trade friction + approval/stability ──
    eu_cost = 0.0
    if eu_rel <= 19:
        eu_cost = 4
        _proj_approval -= 5
        _proj_stability -= 3
    elif eu_rel < 36:
        eu_cost = 2
        _proj_approval -= 2

    # Negotiate costs this turn
    neg_cost = getattr(gs, 'negotiate_costs_this_turn', 0.0)

    # Dual crisis multiplier: USA AND Arabia both hostile (matches EOT section 3)
    # Applies to BUDGET costs only — approval/stability effects already simulated above
    dual_crisis = (usa_rel < 30 and arabia_rel < 30)
    crisis_mult = 1.5 if dual_crisis else 1.0
    if crisis_mult > 1.0:
        sanctions_cost = round(sanctions_cost * crisis_mult)
        embargo_cost = round(embargo_cost * crisis_mult)
        eu_cost = round(eu_cost * crisis_mult)

    # ── Pressure events: Western Bloc joint pressure ──
    wb_cost = 0.0
    _pressure_fired = set(getattr(gs, 'pressure_events_fired', []))
    _suspended = getattr(gs, 'pressure_suspended', {})
    _usa_susp = gs.current_turn <= _suspended.get('usa', 0) if 'usa' in _suspended else False
    _eu_susp = gs.current_turn <= _suspended.get('eu', 0) if 'eu' in _suspended else False
    if 'western_bloc' not in _pressure_fired and usa_rel < 15 and eu_rel < 15 and not _usa_susp and not _eu_susp:
        wb_cost = 5.0
        _proj_stability -= 8
        _proj_approval -= 6

    # ── Section 7: Instability penalty (stability < 40 -> -5% approval) ──
    if _proj_stability < 40:
        _proj_approval -= 5

    # ── Section 7b: Military effects (decay -2 each turn) ──
    _proj_mil = getattr(gs, 'military_strength', 20) - 2  # anticipate decay
    if _proj_mil >= 40:
        _proj_stability += 2
    elif _proj_mil <= 0:
        _proj_stability -= 5

    # ── Section 8: Approval -> Stability drift ──
    _drift = round((_proj_approval - _proj_stability) * 0.3)
    _proj_stability += _drift

    # Clamp to 0-100
    _proj_approval = max(0, min(100, _proj_approval))
    _proj_stability = max(0, min(100, _proj_stability))

    # ── Section 9b: GDP Revenue using PROJECTED approval/stability ──
    _gdp_base_f = getattr(gs, 'gdp_base', 100.0)
    _tax_rates_f = getattr(gs, 'tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
    _endowment_f = getattr(gs, 'resource_endowment', {})
    _income_rev_f = _gdp_base_f * _tax_rates_f.get('income_tax', 0.20) * 0.10
    _corp_rev_f = _gdp_base_f * _tax_rates_f.get('corporate_tax', 0.15) * 0.06
    _resource_rev_f = _gdp_base_f * _tax_rates_f.get('resource_tax', 0.25) * _endowment_f.get('oil_reserves', 0.7) * 0.12
    _gdp = round(_income_rev_f + _corp_rev_f + _resource_rev_f, 1)
    # Approval multiplier — using projected values
    if _proj_approval >= 80:
        _gdp_mult = 1.4
    elif _proj_approval >= 60:
        _gdp_mult = 1.0
    elif _proj_approval >= 40:
        _gdp_mult = 0.7
    else:
        _gdp_mult = 0.4
    _gdp = round(_gdp * _gdp_mult, 1)
    # Stability modifier — using projected values
    if _proj_stability >= 80:
        _gdp += 1.0
    elif _proj_stability < 30:
        _gdp -= 1.0
    # Sanctions/embargo penalty on GDP — using PROJECTED tiers
    if _proj_sanctions_tier >= 4:
        _gdp -= 1.5
    if effective_tier >= 2:
        _gdp -= 0.5
    # Regime multiplier
    _regime = gs.state_identity.get('regime_type', 'Managed Democracy')
    _regime_mults = {'Managed Democracy': 1.1, 'Soft Authoritarianism': 1.0, 'Patronage State': 0.95, 'Kleptocracy': 0.85, 'Totalitarian Regime': 0.75}
    _gdp = round(_gdp * _regime_mults.get(_regime, 1.0), 1)
    # Tech level GDP bonus
    from turn_processor import get_tech_tier_effects
    _tech_effects_f = get_tech_tier_effects(getattr(gs, 'tech_level', 0))
    _tech_gdp_bonus_f = _tech_effects_f.get('gdp_bonus', 0)
    if _tech_gdp_bonus_f > 0:
        _gdp = round(_gdp * (1 + _tech_gdp_bonus_f), 1)
    # GDP contraction — using projected values
    if _proj_approval < 20 and _proj_stability < 30:
        _gdp = round(-1.0 - (30 - _proj_stability) * 0.05 - (20 - _proj_approval) * 0.05, 1)
    else:
        _gdp = max(0, _gdp)
    gdp_revenue = _gdp

    # ── Section 13: Cabinet maintenance ──
    from game_state import AXIS_MAINTENANCE
    _cabinet_axes = getattr(gs, 'cabinet_axes', {})
    maint_cost = 0.0
    for _ax_name, (_free_thresh, _cost_per) in AXIS_MAINTENANCE.items():
        _ax_level = _cabinet_axes.get(_ax_name, 0)
        if _ax_level > _free_thresh:
            maint_cost += round((_ax_level - _free_thresh) * _cost_per, 1)
    maint_cost = round(maint_cost, 1)

    # ── Comprehensive projection totals ──
    _total_expenses = round(base_cost + oil_cost + sanctions_cost + embargo_cost + eu_cost + neg_cost + wb_cost + maint_cost, 1)
    _total_income = round(gdp_revenue + installment_net, 1)
    _net = round(_total_income - _total_expenses, 1)
    print(f"  [api] SKIM PROJECTION — expenses: -${_total_expenses:.1f} / income: +${_total_income:.1f} / net: ${_net:.1f}")

    # Net drain = costs - income
    total_drain = round(_total_expenses - _total_income, 1)
    budget_after = round(gs.budget - total_drain, 1)
    # Show range if conditional effects might apply
    _conditional_extra = 0
    if usa_rel <= 35 and getattr(gs, 'usa_sanctions_warning_turns', 0) > 0:
        _conditional_extra += 3  # sanctions might escalate
    if arabia_rel <= 35 and effective_tier < 4:
        _conditional_extra += 2  # embargo might escalate
    budget_after_worst = round(budget_after - _conditional_extra, 1) if _conditional_extra > 0 else None

    return {
        "projected_drain": total_drain,
        "budget_after_drain": budget_after,
        "budget_after_worst": budget_after_worst,
        "gdp_revenue": gdp_revenue,
        "installment_net": installment_net,
        "base_cost": base_cost,
        "oil_cost": oil_cost,
        "sanctions_cost": sanctions_cost,
        "embargo_cost": embargo_cost,
        "eu_cost": eu_cost,
        "wb_cost": wb_cost,
        "maint_cost": maint_cost,
        "dual_crisis": dual_crisis,
        "installment_streams": [
            {
                "description": inst.get("description", "Deal payment"),
                "amount": float(inst.get("amount", 0)),
                "turns_remaining": inst.get("turns_remaining", 1),
                "conditional": bool(inst.get("condition_type")),
            }
            for inst in gs.active_installments
        ],
        "conditional_notes": _conditional_notes,
    }


def _build_inject_options(gs: GameState) -> list[dict]:
    """Return available injection options given current personal_wealth."""
    pw = gs.personal_wealth
    options = [
        {"choice": 0, "label": "Do nothing (keep personal funds, risk bankruptcy)",
         "personal_cost": 0, "national_gain": 0}
    ]
    if pw >= 3:
        options.append({"choice": 1, "label": "Inject $3B (-$3B personal -> +$3B national)",
                         "personal_cost": 3.0, "national_gain": 3.0})
    if pw >= 7:
        options.append({"choice": 2, "label": "Inject $7B (-$7B personal -> +$7B national)",
                         "personal_cost": 7.0, "national_gain": 7.0})
    if pw > 0:
        options.append({"choice": 3,
                         "label": f"Inject ALL (-${pw:.1f}B personal -> +${pw:.1f}B national)",
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
    fixes_18 Fix E: Only fire ONE threshold per turn to prevent 3x NPC duplication.
    """
    pw = gs.personal_wealth
    w = gs.corruption_warned
    comments = []

    _npcs = list(ALL_NPCS)
    print(f"  [INTERCEPT] Turn {gs.current_turn}: checking thresholds for pw=${pw:.1f}B")

    for threshold, flag_suffix, label in [
        (8,  '_5',  '8b'),
        (20, '_15', '20b'),
        (35, '_30', '35b'),
    ]:
        if pw > threshold:
            any_unfired = any(not w.get(f"{npc}{flag_suffix}", False)
                              for npc in _npcs)
            if any_unfired:
                _firing_npcs = [npc for npc in _npcs if not w.get(f"{npc}{flag_suffix}", False)]
                print(f"  [INTERCEPT] Turn {gs.current_turn}: generating intercepts for NPCs: {_firing_npcs}")
                # Reset flags so npc_engine generates (it skips already-True ones)
                for npc in _npcs:
                    w[f"{npc}{flag_suffix}"] = False
                intercepts = npc_engine.generate_intercept_comments(gs, label)
                # Set flags permanently
                for npc in _npcs:
                    w[f"{npc}{flag_suffix}"] = True
                for _ic in intercepts:
                    print(f"  [INTERCEPT] {label} intercept generated (skipping duplicates)")
                comments.extend(intercepts)
                break  # fixes_18 Fix E: only one threshold per turn

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


def _world_event_conflicts(gs: GameState, event: dict) -> bool:
    """FIX 8: Return True if this world event contradicts active penalties.
    Suppresses contradictory events before they fire."""
    if not event:
        return False
    effects = event.get("effects", {})
    rels_delta = effects.get("relations_delta", {})
    title_lower = (event.get("title", "") + " " + event.get("description", "")).lower()

    # Sanctions relaxation event should not fire if sanctions are active
    if gs.usa_sanctions_tier > 0:
        usa_delta = rels_delta.get("usa", 0)
        if usa_delta > 0 and ('sanction' in title_lower or 'relax' in title_lower or 'ease' in title_lower):
            return True

    # Oil price reduction events should not fire if embargo is active
    if gs.arabia_embargo_tier > 0:
        oil_delta = effects.get("oil_price_delta", 0)
        if oil_delta < 0:
            return True
        arabia_delta = rels_delta.get("arabia", 0)
        if arabia_delta > 0 and ('oil' in title_lower or 'embargo' in title_lower):
            return True

    # Diplomatic improvement events should not fire if that NPC has active penalties
    for npc_id, delta in rels_delta.items():
        if delta > 3:  # significant positive change
            rel = gs.relations.get(npc_id, 50)
            if npc_id == 'usa' and gs.usa_sanctions_tier >= 2:
                return True
            if npc_id == 'arabia' and gs.arabia_embargo_tier >= 2:
                return True

    return False


def _apply_world_event(gs: GameState, event: dict) -> list:
    """Apply a world event's numeric effects to game state.
    Returns a list of log strings for every numeric change made,
    so callers can append them to eot_messages (BUG 1 fix — no silent changes).
    """
    if not event:
        return []
    effects = event.get("effects", {})
    oil_delta = effects.get("oil_price_delta", 0)
    stability_delta = effects.get("stability_delta", 0)
    rels = effects.get("relations_delta", {})
    event_title = event.get("title", "world event")
    log = []

    if oil_delta:
        # Register as a persistent modifier so EOT recalculation doesn't wipe it.
        duration = effects.get("oil_price_duration", 2)
        gs.oil_price_modifiers.append({
            "delta": float(oil_delta),
            "turns_remaining": int(duration),
            "description": event_title,
        })
        # Also apply immediately so the current turn's display shows the new price
        gs.oil_price = max(20, round(gs.oil_price + oil_delta))
        sign = '+' if oil_delta > 0 else ''
        log.append(f"🌍 World event '{event_title}': oil {sign}${oil_delta:.0f}/bbl for {duration} turns")

    if stability_delta:
        old = gs.stability
        gs.update_stability(stability_delta)
        sign = '+' if stability_delta > 0 else ''
        log.append(f"🌍 World event '{event_title}': stability {sign}{stability_delta}% ({old}% -> {gs.stability}%)")

    for npc, delta in rels.items():
        if npc in gs.relations and delta:
            old = gs.relations[npc]
            # PRE-SESSION 4 FIX: World events use flat addition — no diminishing returns.
            # Player did not negotiate the event and should not be penalized by the curve.
            gs.update_relations(npc, delta, flat=True)
            sign = '+' if delta > 0 else ''
            log.append(f"🌍 World event '{event_title}': {npc.upper()} {sign}{delta} ({old} -> {gs.relations[npc]})")

    return log


def _game_status(gs: GameState) -> str:
    """Return 'active', 'won', 'lost', 'escaped', or 'exile'."""
    # Restoration grace period — treat as active regardless of stats
    if getattr(gs, 'restoration_grace_days', 0) > 0:
        return "active"
    # 8C: Exile is a continuing game mode, not an ending
    if getattr(gs, 'in_exile', False):
        return "exile"
    if gs.budget <= 0 or gs.stability <= 0 or gs.public_approval <= 0:
        return "lost"
    # FIX B: Use >= so Turn 10 EOT triggers "won" without needing current_turn = 11 hack
    if gs.current_turn >= gs.max_turns:
        return "won"
    return "active"


def _build_ending(gs: GameState) -> dict | None:
    """
    Build ending payload if game is over. Returns None if still active.
    Mirrors check_game_over() but returns structured data instead of a string.
    8C: Defeat conditions now trigger exile, not game-over. Only victory builds ending.
    """
    from turn_processor import get_personal_outcome, get_legacy_title

    pw = gs.personal_wealth

    # 8C: If in exile, game is not over — it's a different mode
    if getattr(gs, 'in_exile', False):
        return None

    # 8C: Defeat conditions (bankruptcy, collapse, revolt) now handled by exile_sequence_start
    # in check_game_over — they no longer produce endings here
    if gs.budget <= 0 or gs.stability <= 0 or gs.public_approval <= 0:
        return None  # exile takes over

    # FIX B: Use >= so Turn 10 triggers victory without needing current_turn = 11 hack
    if gs.current_turn >= gs.max_turns:
        cause = "victory"
    else:
        return None

    nation_survived = (cause == "victory")
    p_title, p_desc = get_personal_outcome(nation_survived, pw, gs)

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
        # FIX 1: Comprehensive legacy data from final game state
        "regime_type": getattr(gs, 'state_identity', {}).get('regime_type', 'Managed Democracy'),
        "power_base": getattr(gs, 'state_identity', {}).get('power_base', 'Mass-Dependent'),
        "total_skimmed": getattr(gs, 'total_skimmed', 0.0),
        "peak_personal_wealth": getattr(gs, 'peak_personal_wealth', 0.0),
        "scandals_triggered": getattr(gs, 'scandals_triggered', 0),
        "upgrades_purchased": [k for k, v in getattr(gs, 'corruption_upgrades', {}).items() if v],
        "sanctions_active_turns": getattr(gs, 'sanctions_active_turns', 0),
        "embargo_active_turns": getattr(gs, 'embargo_active_turns', 0),
        "historian_summary": getattr(gs, 'historian_summary', None),  # fixes_12 Fix 4
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
                grade_title = "Hartwell's Trusted Ally"
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


def _build_escape_ending(gs: GameState) -> dict:
    """
    Build the escape ending payload with:
    - Destination text chosen by highest-relation NPC at time of escape
    - Wealth modifier applied to tone (>$20B comfortable, $5-20B functional, <$5B desperate)
    """
    pw = gs.personal_wealth
    rels = gs.relations

    # Determine highest-relation NPC
    npc_order = list(ALL_NPCS)
    highest_npc = max(npc_order, key=lambda n: rels.get(n, 0))

    # Wealth tier: comfortable / functional / desperate
    if pw >= 20:
        w_tier = 'comfortable'
    elif pw >= 5:
        w_tier = 'functional'
    else:
        w_tier = 'desperate'

    # Destination text matrix — (highest_npc, wealth_tier)
    _ESCAPE_TEXTS = {
        ('usa', 'comfortable'): (
            "Langley's Finest Guest",
            "Langley arranged the plane this time.\n"
            "You are consulting somewhere warm, at considerable day-rate.\n"
            "Europa is not."
        ),
        ('usa', 'functional'): (
            "The American Option",
            "Langley arranged the plane this time.\n"
            "You are consulting somewhere. The fee is adequate.\n"
            "Europa is not."
        ),
        ('usa', 'desperate'): (
            "Langley's Charity Case",
            "Langley arranged the plane. They will remind you of this.\n"
            "You owe them something. You are not sure what yet.\n"
            "Europa is not sure either."
        ),
        ('arabia', 'comfortable'): (
            "Sadam's Honoured Guest",
            "Sadam's people met you at the airstrip before dawn.\n"
            "The villa has a pool. The pool has a view. The wine is cold.\n"
            "Europa does not."
        ),
        ('arabia', 'functional'): (
            "The Gulf Arrangement",
            "Sadam's people met you at the airstrip.\n"
            "The villa is modest by his standards. Comfortable by yours.\n"
            "Europa is not."
        ),
        ('arabia', 'desperate'): (
            "The Airstrip Deal",
            "Sadam's people met you at the airstrip. You did not negotiate the terms.\n"
            "The accommodation is functional. You are alive, which is the main thing.\n"
            "Europa is not your problem anymore."
        ),
        ('eu', 'comfortable'): (
            "Brussels' Quiet Guest",
            "Brussels offered asylum quietly, with a side of paperwork.\n"
            "You accepted quietly, with a glass of something excellent.\n"
            "Europa noticed loudly."
        ),
        ('eu', 'functional'): (
            "The Brussels Arrangement",
            "Brussels offered asylum quietly. The terms were bureaucratic.\n"
            "You accepted. A small flat in a mid-sized city. Adequate.\n"
            "Europa noticed. It was not pleased."
        ),
        ('eu', 'desperate'): (
            "Brussels' Provisional Refuge",
            "Brussels offered asylum, provisionally, pending review.\n"
            "You accepted anything. The paperwork is still pending.\n"
            "Europa is glad to be rid of you."
        ),
        ('dprg', 'comfortable'): (
            "The Escaped Architect",
            "Ji-won arranged the plane. As promised. You are drinking wine somewhere.\n"
            "The location is undisclosed. The vintage is excellent.\n"
            "Europa is not."
        ),
        ('dprg', 'functional'): (
            "The Escaped Architect",
            "Ji-won arranged the plane.\n"
            "You are somewhere. The wine is drinkable. You are alive.\n"
            "Europa is not your concern."
        ),
        ('dprg', 'desperate'): (
            "Ji-won's Last Favour",
            "Ji-won arranged the plane at the last possible moment.\n"
            "You barely made it. The wine, if there is any, is cheap.\n"
            "Europa will not miss you. The feeling is mutual."
        ),
    }

    title, desc = _ESCAPE_TEXTS.get(
        (highest_npc, w_tier),
        ("The Escaped Architect",
         "You saw the writing on the wall before the wall fell.\n"
         "Europa will call you a traitor. Interpol will call you a fugitive.\n"
         "You will call yourself: alive.")
    )

    return {
        "cause": "escaped",
        "nation_survived": False,
        "personal_title": title,
        "personal_description": desc,
        "exile_npc": highest_npc,       # surfaced for potential future UI use
        "personal_wealth": pw,
        "final_budget": gs.budget,
        "final_stability": gs.stability,
        "final_approval": gs.public_approval,
        "final_relations": dict(rels),
        "turn": gs.current_turn,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/game/new")
async def new_game(user: User = Depends(get_optional_user)):
    """Create a new game session. Returns session_id, initial state, offers, and Turn 1 dialogue."""
    gs = GameState()
    # Initialize advisor pool at game start
    from advisor_engine import generate_advisor_pool
    gs.advisor_pool = generate_advisor_pool(gs)
    dialogue = npc_engine.generate_dialogue(gs)
    blackmail_active = _check_blackmail(gs)
    offers = _build_offers(gs)
    skim_options = _build_skim_options(gs)

    # fixes_12 Fix 4: Per-turn epitaph removed. Historian summary generated at game end.

    # Use authenticated user's ID as player_id (or guest UUID)
    import uuid as _uuid
    player_id = str(user.id) if user else str(_uuid.uuid4())
    session_id = create_session(gs.serialize(), player_id=player_id)

    # Create GameStatePersisted record linking session to authenticated user (skip for guests)
    if user:
        from datetime import datetime as _dt, timezone as _tz
        with SQLModelSession(accounts_engine) as db_session:
            game_record = GameStatePersisted(
                id=_uuid.UUID(session_id),
                user_id=user.id,
                state_data=gs.serialize(),
                created_at=_dt.now(_tz.utc),
                updated_at=_dt.now(_tz.utc),
            )
            db_session.add(game_record)
            db_session.commit()

    # Session 5 Phase C Hook 9: cleanup_expired_memories on new game
    if player_id:
        try:
            from memory_engine import cleanup_expired_memories
            cleanup_expired_memories(player_id)
        except Exception as e:
            print(f"  [api] Memory cleanup failed: {e}")

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
async def get_game(session_id: str, user: User = Depends(get_optional_user)):
    """Return current game state, available offers, and dialogue for the current turn."""
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)
    offers = _build_offers(gs)
    skim_options = _build_skim_options(gs)
    status = _game_status(gs)
    ending = _build_ending(gs) if status != "active" else None

    # Generate dialogue so snapshot loads and resumes have communiqués
    dialogue = npc_engine.generate_dialogue(gs) if status == "active" else None
    blackmail_active = _check_blackmail(gs) if status == "active" else False

    return {
        "session_id": session_id,
        "game_state": gs.serialize(),
        "dialogue": dialogue,
        "blackmail_active": blackmail_active,
        "offers": offers,
        "skim_options": skim_options,
        "status": status,
        "ending": ending,
    }


@app.post("/game/{session_id}/action")
async def post_action(session_id: str, body: ActionRequest, user: User = Depends(get_optional_user)):
    """
    Process diplomatic choice (A–G).
    - F (escape): ends game immediately, returns escape ending
    - G (inject): returns inject_options for /inject follow-up
    - A–E: applies consequences, checks blackmail, generates new dialogue, returns skim_options
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)
    letter = body.choice.upper()

    # Build offer map
    offers = _build_offers(gs)
    offer_map = {o["letter"]: o for o in offers}

    if letter not in offer_map:
        # Session 8A: Russia/China (and future NPCs) have no static choice — their deals
        # exist purely in options_override.  Build a synthetic base offer with empty
        # consequences so the merge logic works cleanly.
        _override_match = None
        if gs.options_override:
            for _ov in gs.options_override:
                if _ov.get("letter") == letter:
                    _override_match = _ov
                    break
        if not _override_match:
            raise HTTPException(status_code=400, detail=f"Invalid choice '{letter}'")
        _deal_npc = (_override_match.get("npc") or "").lower()
        _deal_budget = _override_match.get("consequences", {}).get("budget", "N/A")
        print(f"[deal] Russia/China deal confirmation panel triggered: {_deal_npc} {_deal_budget}")
        offer = {
            "letter": letter,
            "type": "accept_deal",
            "npc": _deal_npc,
            "consequences": {},
            "text": _override_match.get("text", ""),
        }
    else:
        offer = offer_map[letter]

    # ── Option F — Escape ──────────────────────────────────────────────────
    if offer["type"] == "escape":
        _save_gs(session_id, gs)
        return {
            "action": "escape",
            "ending": _build_escape_ending(gs),
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
    from npc_engine import MODEL as _npc_model
    print(f"[api] diplomatic choice handler — model: {_npc_model}")
    blackmail_active = _check_blackmail(gs)

    # Resolve effective offer: use negotiated counter-offer if one was stored
    effective_offer = offer
    is_negotiated = False
    streams_to_register = []  # Fix A: init before branching to prevent UnboundLocalError
    combined_budget_delta = 0  # Fix A: same for combined_budget_delta
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
        #   oil_price_lock / oil_price / oil_price_lock_turns — stripped (not supported in negotiation)
        #
        # The NPC negotiation prompts now explicitly specify this sign convention, so
        # raw_budget is applied directly (no negation needed).
        raw_budget = counter_consequences.pop("budget", None)
        budget_delta = counter_consequences.pop("budget_delta", None)
        pw_delta = counter_consequences.pop("personal_wealth_delta", None)
        # Strip any stray oil price fields — NPC negotiation does not support oil pricing.
        # Arabia expresses oil deals as budget/installment payments instead.
        counter_consequences.pop("oil_price_lock", None)
        counter_consequences.pop("oil_price_lock_turns", None)
        counter_consequences.pop("oil_price", None)
        counter_consequences.pop("oil_price_turns", None)
        base_consequences.pop("oil_price", None)
        base_consequences.pop("oil_price_turns", None)
        base_consequences.pop("oil_price_lock", None)
        base_consequences.pop("oil_price_lock_turns", None)

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

        # Final oil-price strip on the merged dict — catches anything that survived
        # the pre-merge pops (e.g. base_consequences carrying oil_price_lock, or
        # model hallucinating variant field names). Oil pricing from negotiation
        # must never reach process_choice_consequences / turn_processor.
        for _oil_key in ('oil_price', 'oil_price_lock', 'oil_price_lock_turns',
                         'oil_price_turns', 'oil_price_delta'):
            merged.pop(_oil_key, None)

        # FIX 3: A deal's own NPC relation value should only ever be zero or positive.
        # The NPC model sometimes hallucinate negative relations for itself (e.g. USA deal
        # with "usa": -7). Clamp the deal's own NPC relation to >= 0 before applying.
        deal_npc = effective_offer.get("npc", "").lower() if not isinstance(effective_offer, str) else ""
        if deal_npc and deal_npc in merged:
            val = merged[deal_npc]
            if isinstance(val, (int, float)) and val < 0:
                merged[deal_npc] = 0

        # PRE-SESSION 4 FIX: Negotiated deal relations bonus.
        # If the counter_offer didn't include a relation bonus for the deal-giving NPC,
        # or set it to 0, inherit the base offer's bonus. Accepting a negotiated deal
        # should give the same or better relations bonus as the static equivalent.
        if deal_npc and deal_npc in base_consequences:
            base_bonus = base_consequences[deal_npc]
            if isinstance(base_bonus, (int, float)) and base_bonus > 0:
                current = merged.get(deal_npc, 0)
                if not isinstance(current, (int, float)) or current < base_bonus:
                    merged[deal_npc] = base_bonus

        effective_offer = dict(effective_offer)
        effective_offer["consequences"] = merged

        # Apply monetary side-effects now (before process_choice_consequences)
        extra_msgs = []

        # BUG 1 FIX: apply counter-offer budget grant/cost directly with correct sign.
        # Both "budget" and "budget_delta" use player-perspective (positive = Europa receives).
        # Normalize to billions if model returned raw dollars.
        # fixes_12 Fix 1: Added sanity cap ($20B single deal).
        if raw_budget is not None and abs(raw_budget) > 1000:
            raw_budget = raw_budget / 1_000_000_000
        if raw_budget is not None and abs(raw_budget) > 20.0:
            print(f"  [api] DEAL AMOUNT CAP EXCEEDED: raw_budget={raw_budget} — capping to $20B")
            raw_budget = 20.0 if raw_budget > 0 else -20.0
        if budget_delta is not None and abs(budget_delta) > 1000:
            budget_delta = budget_delta / 1_000_000_000
        if budget_delta is not None and abs(budget_delta) > 20.0:
            print(f"  [api] DEAL AMOUNT CAP EXCEEDED: budget_delta={budget_delta} — capping to $20B")
            budget_delta = 20.0 if budget_delta > 0 else -20.0
        combined_budget_delta = (raw_budget or 0) + (budget_delta or 0)
        # FIX H: Assert direction — if NPC is paying player and value is negative, flip and warn
        if combined_budget_delta < 0 and deal_npc:
            _dial_text = (effective_offer.get("text") or "").lower()
            _pay_signals = ['offer', 'provide', 'give', 'pay', 'grant', 'invest', 'package', 'funding']
            if any(s in _dial_text for s in _pay_signals):
                print(f"  [api] FIX H: Flipping negative budget {combined_budget_delta} to positive (NPC paying player)")
                combined_budget_delta = abs(combined_budget_delta)
        if combined_budget_delta != 0:
            gs.update_budget(combined_budget_delta)
            # FIX E: Budget message is now built later as part of the deal payment header

        # PRE-SESSION 4 FIX: Remove 'budget' from merged consequences to prevent
        # double-credit. We already applied the budget change above from the counter-offer.
        # The base_consequences may also carry a 'budget' key from the static offer,
        # which would be applied again in process_choice_consequences if left in merged.
        merged.pop("budget", None)
        merged.pop("budget_delta", None)
        effective_offer["consequences"] = merged

        if pw_delta is not None and pw_delta != 0:
            gs.update_personal_wealth(pw_delta, source=f"negotiated deal ({effective_offer.get('npc', 'unknown')})")
            if pw_delta > 0:
                extra_msgs.append(f"💰 Negotiated personal payment: +${pw_delta:.1f}B personal account")
            else:
                extra_msgs.append(f"💰 Negotiated personal cost: ${abs(pw_delta):.1f}B personal account")

        # BUG 2: register installment payment streams so EOT processor can apply them.
        # Build a unified list from whichever format the NPC used.
        npc_name = effective_offer.get("npc", "unknown")
        streams_to_register = []

        # Oil-installment guard: strip any installment whose description looks like an
        # oil price adjustment. Arabia expresses oil deals as budget/installment payments,
        # but should describe them as energy partnerships — not oil price reductions.
        # This catches model hallucinations where it puts a "price reduction subsidy"
        # or similar in the installments array.
        _OIL_INST_KEYWORDS = ('oil', 'barrel', 'bbl', 'subsidy', 'price reduction')

        def _is_oil_installment(desc_str: str) -> bool:
            d = (desc_str or '').lower()
            return any(kw in d for kw in _OIL_INST_KEYWORDS)

        def _normalize_to_billions(val: float, is_installment: bool = False) -> float:
            """NPC model sometimes returns raw dollars instead of billions.
            If |amount| > 1000, assume raw dollars and convert to billions.
            fixes_12 Fix 1: Added sanity caps — single $20B, installment $10B/turn."""
            if abs(val) > 1000:
                val = val / 1_000_000_000
            cap = 10.0 if is_installment else 20.0
            if abs(val) > cap:
                print(f"  [api] DEAL AMOUNT CAP EXCEEDED: raw={val}, cap=${cap}B — rejecting")
                val = cap if val > 0 else -cap
            return val

        # New format: "installments" array — one entry per payment stream
        if installments_array and isinstance(installments_array, list):
            for entry in installments_array:
                amt = entry.get("amount")
                turns = entry.get("turns")
                desc = entry.get("description") or f"{npc_name.upper()} payment"
                if amt is not None and turns and int(turns) > 0:
                    if _is_oil_installment(desc):
                        continue  # strip — oil deals must be framed as energy partnerships, not oil price reductions
                    _stream = {
                        "amount": _normalize_to_billions(float(amt), is_installment=True),
                        "turns_remaining": int(turns),
                        "description": desc,
                        "npc": npc_name,
                    }
                    # BUG 14: Preserve start_turn if specified in deal terms
                    _start_turn = entry.get("start_turn")
                    if _start_turn is not None:
                        _stream["start_turn"] = int(_start_turn)
                    # FIX 4: Preserve condition fields for conditional payments
                    _cond_type = entry.get("condition_type")
                    _cond_npc = entry.get("condition_npc")
                    _cond_thresh = entry.get("condition_threshold")
                    _cond_narrative = entry.get("condition_narrative")
                    if _cond_type and _cond_npc is not None:
                        _stream["condition_type"] = _cond_type
                        # fixes_17 Fix E: Normalize NPC id (Claude may output 'europa' instead of 'eu')
                        _npc_aliases = {'europa': 'eu', 'united_states': 'usa', 'america': 'usa', 'saudi': 'arabia', 'north_korea': 'dprg', 'korea': 'dprg'}
                        _norm_npc = str(_cond_npc).lower().strip()
                        _norm_npc = _npc_aliases.get(_norm_npc, _norm_npc)
                        _stream["condition_npc"] = _norm_npc
                        _stream["condition_threshold"] = float(_cond_thresh) if _cond_thresh is not None else 30
                        _stream["verification_turn"] = gs.current_turn + 1
                        print(f"  [NPC] Counter-offer conditional: type={_cond_type}, npc={_norm_npc} (raw='{_cond_npc}'), threshold={_stream['condition_threshold']}")
                    # fixes_18 Fix A: Preserve narrative condition
                    if _cond_narrative:
                        _stream["condition_narrative"] = str(_cond_narrative).strip()
                    _num_count = 1 if (_cond_type and _cond_npc is not None) else 0
                    _narr_count = 1 if _cond_narrative else 0
                    if _num_count or _narr_count:
                        print(f"  [npc_engine] COUNTER-OFFER CONDITIONS: {{numeric: {_num_count}, narrative: {_narr_count}, raw: \"{(_cond_type or '')}, {(_cond_narrative or '')}\"}}")
                    streams_to_register.append(_stream)

        # Legacy format: single installment_amount + installment_turns pair
        elif installment_amount is not None and installment_turns and int(installment_turns) > 0:
            desc = installment_desc or f"{npc_name.upper()} payment"
            if not _is_oil_installment(desc):
                streams_to_register.append({
                    "amount": _normalize_to_billions(float(installment_amount), is_installment=True),
                    "turns_remaining": int(installment_turns),
                    "description": desc,
                    "npc": npc_name,
                })

        # FIX L: Parse deal text for conditions if model didn't emit structured fields.
        # This ensures Marsha (and all NPC) conditional deals get verified at EOT.
        _deal_text_lower = ((effective_offer or {}).get("text") or "").lower()
        _condition_patterns = {
            'dprg': ['dprg', 'ji-won', 'goryeo'],
            'usa': ['usa', 'hartwell', 'america', 'united states'],
            'arabia': ['arabia', 'sadam'],
            'eu': ['eu', 'marsha', 'european'],
        }
        import re
        for stream in streams_to_register:
            # FIX K: Normalize condition_type values from Claude's JSON.
            # Claude may return freeform strings like "DPRG below 40" instead of structured "relation_below".
            _raw_cond = stream.get('condition_type', '')
            if _raw_cond and _raw_cond not in ('relation_below', 'relation_above'):
                # Attempt to parse freeform condition text
                _freeform_lower = str(_raw_cond).lower()
                _freeform_match = re.search(
                    r'(dprg|usa|eu|arabia|ji-won|hartwell|sadam|marsha|goryeo|america)'
                    r'.*?(?:below|under|drops?\s+to|falls?\s+to|less\s+than)\s*(\d+)',
                    _freeform_lower
                )
                if _freeform_match:
                    _cond_target_text = _freeform_match.group(1)
                    _cond_threshold = float(_freeform_match.group(2))
                    _cond_npc_key = None
                    for _npc_key, _npc_patterns in _condition_patterns.items():
                        if _cond_target_text in _npc_patterns:
                            _cond_npc_key = _npc_key
                            break
                    if _cond_npc_key:
                        stream['condition_type'] = 'relation_below'
                        stream['condition_npc'] = _cond_npc_key
                        stream['condition_threshold'] = _cond_threshold
                        print(f"  [api] FIX K: Normalized freeform condition '{_raw_cond}' -> relation_below {_cond_npc_key} {_cond_threshold}")
                    else:
                        # Can't parse — remove invalid condition so payment doesn't fire unconditionally
                        stream.pop('condition_type', None)
                        print(f"  [api] FIX K: Could not parse freeform condition '{_raw_cond}', removed")
                elif 'above' in _freeform_lower or 'over' in _freeform_lower:
                    _above_match = re.search(
                        r'(dprg|usa|eu|arabia|ji-won|hartwell|sadam|marsha|goryeo|america)'
                        r'.*?(?:above|over|exceeds?|reaches?|greater\s+than)\s*(\d+)',
                        _freeform_lower
                    )
                    if _above_match:
                        _cond_target_text = _above_match.group(1)
                        _cond_threshold = float(_above_match.group(2))
                        _cond_npc_key = None
                        for _npc_key, _npc_patterns in _condition_patterns.items():
                            if _cond_target_text in _npc_patterns:
                                _cond_npc_key = _npc_key
                                break
                        if _cond_npc_key:
                            stream['condition_type'] = 'relation_above'
                            stream['condition_npc'] = _cond_npc_key
                            stream['condition_threshold'] = _cond_threshold
                            print(f"  [api] FIX K: Normalized freeform condition '{_raw_cond}' -> relation_above {_cond_npc_key} {_cond_threshold}")

            # Existing: parse condition from deal text if not already set
            if not stream.get('condition_type') and _deal_text_lower:
                _cond_match = re.search(
                    r'(?:condition|conditional|if|provided|requires?)\s*(?:that\s+)?'
                    r'(?:.*?)(dprg|usa|eu|arabia|ji-won|hartwell|sadam|marsha|goryeo|america)'
                    r'.*?(?:below|under|drops?\s+to|reaches?|falls?\s+to)\s*(\d+)',
                    _deal_text_lower
                )
                if _cond_match:
                    _cond_target_text = _cond_match.group(1)
                    _cond_threshold = float(_cond_match.group(2))
                    _cond_npc_key = None
                    for _npc_key, _npc_patterns in _condition_patterns.items():
                        if _cond_target_text in _npc_patterns:
                            _cond_npc_key = _npc_key
                            break
                    if _cond_npc_key:
                        stream['condition_type'] = 'relation_below'
                        stream['condition_npc'] = _cond_npc_key
                        stream['condition_threshold'] = _cond_threshold
                        stream['verification_turn'] = gs.current_turn + 1
                        print(f"  [api] FIX L: Injected condition from deal text: {_cond_npc_key} below {_cond_threshold}")

            # FIX K: Also check the installment's own description for embedded conditions
            if not stream.get('condition_type'):
                _inst_desc_lower = (stream.get('description') or '').lower()
                if _inst_desc_lower:
                    _desc_match = re.search(
                        r'(dprg|usa|eu|arabia|ji-won|hartwell|sadam|marsha)'
                        r'.*?(?:below|under)\s*(\d+)',
                        _inst_desc_lower
                    )
                    if _desc_match:
                        _cond_target_text = _desc_match.group(1)
                        _cond_threshold = float(_desc_match.group(2))
                        _cond_npc_key = None
                        for _npc_key, _npc_patterns in _condition_patterns.items():
                            if _cond_target_text in _npc_patterns:
                                _cond_npc_key = _npc_key
                                break
                        if _cond_npc_key:
                            stream['condition_type'] = 'relation_below'
                            stream['condition_npc'] = _cond_npc_key
                            stream['condition_threshold'] = _cond_threshold
                            print(f"  [api] FIX K: Extracted condition from installment description: {_cond_npc_key} below {_cond_threshold}")

        for stream in streams_to_register:
            # FIX D: Validate installment direction at registration.
            # If NPC is the payer (dialogue indicates payment) and amount is zero or negative,
            # flag as registration error and correct.
            _stream_amt = stream.get('amount', 0)
            _stream_desc = (stream.get('description') or '').lower()
            _npc_paying_signals = ['aid', 'payment', 'investment', 'grant', 'fund', 'package', 'support', 'subsidy']
            _is_npc_paying = any(sig in _stream_desc for sig in _npc_paying_signals)
            if _is_npc_paying and _stream_amt <= 0:
                # Direction error: NPC should be paying player but amount is ≤ 0
                _dial_text = (effective_offer.get("text") or "").lower()
                # Try to recover amount from deal text
                import re
                _amt_match = re.search(r'\$?([\d.]+)\s*[bB]', _dial_text)
                if _amt_match:
                    _recovered = float(_amt_match.group(1))
                    if _recovered > 0 and _recovered < 50:  # sanity check
                        stream['amount'] = round(_recovered, 1)
                        print(f"  [api] FIX D: Corrected installment direction: {_stream_amt} -> {stream['amount']} ({stream.get('description', '')})")
                elif _stream_amt < 0:
                    stream['amount'] = abs(_stream_amt)
                    print(f"  [api] FIX D: Flipped negative installment: {_stream_amt} -> {stream['amount']} ({stream.get('description', '')})")
                elif _stream_amt == 0 and combined_budget_delta > 0:
                    # Use the immediate budget delta as a proxy
                    stream['amount'] = round(combined_budget_delta / max(1, stream.get('turns_remaining', 1)), 1)
                    print(f"  [api] FIX D: Recovered zero installment from budget delta: 0 -> {stream['amount']}")

            # FIX 3: Tag with registered_turn so EOT won't pay out same turn
            stream['registered_turn'] = gs.current_turn
            gs.active_installments.append(stream)
            direction_word = "receive" if stream["amount"] > 0 else "pay"
            extra_msgs.append(
                f"📋 Installment registered: {direction_word} ${abs(stream['amount']):.1f}B/turn "
                f"for {stream['turns_remaining']} turns ({stream['description']}) — first payment next turn"
            )
        # Session 3 Addendum: Track total aid received from this NPC (for willingness decay)
        _aid_npc = effective_offer.get("npc", "")
        if _aid_npc and _aid_npc in ALL_NPCS:
            _total_aid = combined_budget_delta if combined_budget_delta > 0 else 0
            for stream in streams_to_register:
                if stream["amount"] > 0:
                    _total_aid += stream["amount"] * stream["turns_remaining"]
            if not hasattr(gs, 'total_aid_received'):
                gs.total_aid_received = {n: 0.0 for n in ALL_NPCS}
            gs.total_aid_received[_aid_npc] = gs.total_aid_received.get(_aid_npc, 0.0) + _total_aid
    else:
        extra_msgs = []

    # 8A FIX: Compute total deal value (upfront + all installments) for cross-NPC tiering.
    # deal_budget only captures the immediate payment; a $3.4B multi-turn deal ($0.4B upfront +
    # $1B/turn × 3) would read as $0.4B and always hit "small" tier. deal_total_value captures
    # the full economic weight of the deal for accurate cross-NPC consequence scaling.
    _deal_total_value = abs(combined_budget_delta) if is_negotiated else 0
    print(f"[api] streams_to_register initialized — count: {len(streams_to_register)}")
    for _tv_stream in streams_to_register:
        _deal_total_value += abs(_tv_stream.get("amount", 0)) * _tv_stream.get("turns_remaining", 1)
    if is_negotiated and _deal_total_value > 0:
        print(f"  [api] Deal total value: ${_deal_total_value:.1f}B (upfront ${abs(combined_budget_delta):.1f}B + installments ${_deal_total_value - abs(combined_budget_delta):.1f}B)")

    choice_dict = {
        "type": effective_offer.get("type", "accept_deal"),
        # 8A FIX 1: Fallback to base offer's npc if override is missing it (defensive)
        "npc": effective_offer.get("npc") or offer.get("npc"),
        "consequences": effective_offer.get("consequences", {}),
        "is_negotiated": is_negotiated,
        "covert": effective_offer.get("covert", False),  # FIX E: pass covert flag
        # 8A: Pass deal budget + text for cross-NPC scaling (budget is popped for negotiated deals)
        "deal_budget": abs(combined_budget_delta) if is_negotiated else 0,
        "deal_total_value": _deal_total_value if is_negotiated else 0,
        "text": effective_offer.get("text", ""),
    }

    gs.record_action(choice_dict["type"], choice_dict.get("npc"))

    # Session 7B: Track NPC interaction from deal acceptance
    _deal_npc_interact = choice_dict.get("npc")
    if _deal_npc_interact:
        _interacted_deal = getattr(gs, 'npcs_interacted_this_turn', [])
        if _deal_npc_interact not in _interacted_deal:
            _interacted_deal.append(_deal_npc_interact)
            gs.npcs_interacted_this_turn = _interacted_deal

    consequence_msgs = process_choice_consequences(gs, choice_dict)

    # FIX E: Deal immediate payment should be the FIRST line on the consequence screen.
    # Build a prominent deal payment header that precedes all other consequence messages.
    _deal_header = []
    _npc_char_names = dict(ALL_NPC_NAMES)
    if is_negotiated:
        _deal_npc = effective_offer.get("npc", "")
        _deal_npc_display = _npc_char_names.get(_deal_npc, _deal_npc.upper() if _deal_npc else "Unknown")
        _deal_desc = (effective_offer.get("text") or "negotiated agreement")[:80]

        if combined_budget_delta > 0:
            # Immediate payment received — show prominently
            _deal_header.append(
                f"💰 DEAL PAYMENT RECEIVED\n"
                f"  +${combined_budget_delta:.1f}B from {_deal_npc_display} ({_deal_desc})"
            )
        elif combined_budget_delta < 0:
            # Player is paying — still show prominently
            _deal_header.append(
                f"💰 DEAL COST APPLIED\n"
                f"  -${abs(combined_budget_delta):.1f}B to {_deal_npc_display} ({_deal_desc})"
            )
        elif streams_to_register:
            # No immediate payment, but installments registered — show as deal registered
            _total_stream = sum(s["amount"] * s["turns_remaining"] for s in streams_to_register)
            _cond_notes = []
            for s in streams_to_register:
                if s.get("condition_type") and s.get("condition_npc"):
                    _cond_npc_label = dict(ALL_NPC_LABELS).get(
                        s["condition_npc"], s["condition_npc"].upper())
                    _cond_notes.append(
                        f"{_cond_npc_label} {'below' if s['condition_type'] == 'relation_below' else 'above'} {s.get('condition_threshold', 30):.0f}")
            _cond_str = f"\n  Condition: {_cond_notes[0]}" if _cond_notes else ""
            _deal_header.append(
                f"📋 DEAL REGISTERED\n"
                f"  +${abs(_total_stream):.1f}B from {_deal_npc_display} — first payment next turn{_cond_str}"
            )

    # FIX E: deal header FIRST, then extra_msgs (installment registrations, pw changes), then other consequences
    consequence_msgs = _deal_header + extra_msgs + consequence_msgs

    # Clear options_override after use
    gs.options_override = None

    # Blackmail result
    blackmail_result = None
    if blackmail_active:
        chose_cooperate = (effective_offer.get("npc") == "usa")
        gs.blackmail_used = True
        if chose_cooperate:
            gs.update_personal_wealth(-2.0, source="blackmail cooperation fee")
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

    # fixes_13 Fix 24: Covert deal detection
    _is_covert = effective_offer.get('covert', False)

    # FEATURE 6: Register deals into deal_history
    # fixes_11 Fix 6: Also record standard (non-negotiated) deals, not just counter-offers
    _deal_npc = effective_offer.get("npc") or letter
    _deal_type = effective_offer.get("type", "")
    _should_record = is_negotiated or (_deal_type in ("accept_deal", "side_with") and _deal_npc)
    if _should_record:
        deal_summary = effective_offer.get("text", "Accepted deal")
        if _is_covert:
            # fixes_13 Fix 24: Covert deals go to covert_deals, not deal_history (no visible EOT log entry)
            _covert_deals = getattr(gs, 'covert_deals', [])
            _covert_deals.append({
                "npc": _deal_npc,
                "summary": deal_summary,
                "turn_accepted": gs.current_turn,
                "expires_turn": gs.current_turn + 3,
                "broken": False,
                "negotiated": is_negotiated,
                "covert": True,
            })
            gs.covert_deals = _covert_deals
            print(f"  [api] Fix 24: COVERT DEAL RECORDED: {_deal_npc} — {deal_summary[:60]}...")
        else:
            gs.deal_history.append({
                "npc": _deal_npc,
                "summary": deal_summary,
                "turn_accepted": gs.current_turn,
                "expires_turn": gs.current_turn + 3,
                "broken": False,
                "negotiated": is_negotiated,
            })
            print(f"  [api] DEAL RECORDED: {_deal_npc} — {deal_summary[:60]}...")

        # Session 5 Phase C Hook 1: store_memory on deal accepted
        try:
            from memory_engine import store_memory
            _player_id = getattr(gs, 'player_id', None)
            if _player_id:
                store_memory(
                    player_id=_player_id, npc=_deal_npc, era=0,
                    turn=gs.current_turn, event_type='deal_accepted',
                    description=f"Accepted deal with {_deal_npc.upper()}: {deal_summary[:120]}"
                )
        except Exception as e:
            print(f"  [api] Memory hook (deal_accepted) failed: {e}")

    # BUG 8 + BUG 13: Named NPC deal penalties — when deal text EXPLICITLY names
    # a specific NPC as a distancing target (e.g. "distance from DPRG"),
    # apply an extra relation hit. Fixed rules:
    #   1. NEVER apply to the NPC giving the deal (deal_npc_ref)
    #   2. Only penalize NPCs explicitly named as distancing targets in conditions
    #   3. If NPC already took standard alignment penalty, apply the LARGER only (no stacking)
    #   4. EU only penalized if explicitly named
    #   fixes_13 Fix 24: Covert deals skip ALL cross-NPC penalties
    if not _is_covert and (is_negotiated or (choice_dict.get("type") in ("accept_deal", "side_with") and choice_dict.get("npc"))):
        deal_text = (effective_offer.get("text", "") or "").lower()
        deal_npc_ref = choice_dict.get("npc", "")
        _named_penalties = {}  # { npc_id: penalty }

        # Only look for DISTANCING keywords — must indicate the deal REQUIRES distancing
        _distancing_patterns = {
            'dprg': ['distance from dprg', 'distance from ji-won', 'cut ties with dprg',
                     'reduce dprg', 'away from dprg', 'abandon dprg', 'sever dprg',
                     'anti-dprg', 'condemn dprg', 'against dprg', 'oppose dprg'],
            'arabia': ['distance from arabia', 'reduce arabia', 'cut ties with arabia',
                       'away from arabia', 'abandon arabia', 'oil dependence',
                       'reduce oil depend', 'sever arabia', 'anti-arabia'],
            'usa': ['distance from usa', 'distance from america', 'cut ties with usa',
                    'away from usa', 'abandon usa', 'anti-american', 'anti-usa',
                    'reject western', 'oppose usa'],
            'eu': ['distance from eu', 'distance from europe', 'cut ties with eu',
                   'away from eu', 'abandon eu', 'reject eu', 'anti-eu', 'oppose eu'],
        }
        # "Western alignment" is special — implies distancing from Eastern powers
        if 'western alignment' in deal_text or 'align with the west' in deal_text:
            if 'dprg' not in _named_penalties:
                _named_penalties['dprg'] = -10
            if 'arabia' not in _named_penalties:
                _named_penalties['arabia'] = -10

        for target_npc, patterns in _distancing_patterns.items():
            if target_npc == deal_npc_ref:
                continue  # Rule 1: never penalize the deal-giving NPC
            for pat in patterns:
                if pat in deal_text:
                    if target_npc not in _named_penalties or -12 < _named_penalties[target_npc]:
                        _named_penalties[target_npc] = -12
                    break

        # Remove the deal-giver from penalties (safety net for Rule 1)
        _named_penalties.pop(deal_npc_ref, None)

        # Rule 3: Check what standard alignment penalty already applied.
        # Standard alignment penalties come from the `consequences` dict in the choice.
        _standard_consequences = choice_dict.get("consequences", {})

        for npc, named_penalty in _named_penalties.items():
            std_penalty = _standard_consequences.get(npc, 0)
            if std_penalty < 0:
                # Already took standard penalty. Only apply extra if named is larger.
                if named_penalty < std_penalty:
                    # Apply only the difference (named - standard already applied)
                    extra = named_penalty - std_penalty
                    old_rel = gs.relations[npc]
                    gs.update_relations(npc, extra)
                    new_rel = gs.relations[npc]
                    npc_labels = dict(ALL_NPC_LABELS)
                    consequence_msgs.append(
                        f"↓ {npc_labels.get(npc, npc.upper())}: {old_rel} -> {new_rel} ({extra:+d}) — named in deal conditions"
                    )
                # else: standard penalty was already equal or larger, skip
            else:
                # No standard penalty — apply full named penalty
                old_rel = gs.relations[npc]
                gs.update_relations(npc, named_penalty)
                new_rel = gs.relations[npc]
                npc_labels = dict(ALL_NPC_LABELS)
                consequence_msgs.append(
                    f"↓ {npc_labels.get(npc, npc.upper())}: {old_rel} -> {new_rel} ({named_penalty:+d}) — named in deal conditions"
                )

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
async def post_skim(session_id: str, body: SkimRequest, user: User = Depends(get_optional_user)):
    """
    Apply skim choice (1–4), then run end-of-turn effects.
    Also generates new NPC dialogue for the next turn.
    Returns everything the frontend needs to show EOT + advance.
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)
    choice = body.choice

    skim_options = _build_skim_options(gs)
    _skim_persistent = any(o.get('skim_persistent', False) for o in skim_options)
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

    # 9.5A-Shadow: When persistent skim is active, per-turn skim is a no-op
    # (skim_rate income is applied automatically in EOT via persistent rate)
    if _skim_persistent and personal_gain == 0:
        _skim_rate = getattr(gs, 'skim_rate', 0.0)
        if _skim_rate > 0:
            skim_messages.append(
                f"\U0001f4b0 Persistent skim active: {_skim_rate*100:.0f}% of revenue "
                f"diverted automatically each turn")

    if personal_gain > 0:
        # Stage 5: track consecutive large skims for regime shift detection
        if national_cost >= 7.0:
            gs.consecutive_large_skims += 1
        else:
            gs.consecutive_large_skims = 0

        # Sovereign Wealth Diversion: stability_hit already reflects halved penalty
        # from _build_skim_options() — no further adjustment needed here.

        gs.budget -= national_cost
        # v2: Oligarch skim bonus (+10% personal gain when assigned)
        from advisor_engine import get_oligarch_skim_bonus
        _skim_bonus = get_oligarch_skim_bonus(gs)
        if _skim_bonus > 1.0:
            _before_gain = personal_gain
            personal_gain = round(personal_gain * _skim_bonus, 1)
            print(f"  [advisor] OLIGARCH SKIM BONUS: +10% applied, skim personal gain {_before_gain}->{personal_gain}")
        gs.update_personal_wealth(personal_gain, source=f"skim ({opt['label'][:40]})")
        gs.total_skimmed = getattr(gs, 'total_skimmed', 0.0) + personal_gain
        if gs.personal_wealth > getattr(gs, 'peak_personal_wealth', 0.0):
            gs.peak_personal_wealth = gs.personal_wealth
        gs.update_stability(stability_hit)
        gs.update_approval(approval_hit)
        skim_messages.append(opt["label"])
        skim_messages.append(
            f"National treasury: ${gs.budget:.1f}B | Personal account: ${gs.personal_wealth:.1f}B"
        )

        # Priority 3: Add detection heat from skim
        from turn_processor import add_skim_heat
        heat_added = add_skim_heat(gs, personal_gain)
        if heat_added > 0:
            skim_messages.append(
                f"🔍 Detection risk: +{heat_added}% heat (total: {gs.detection_heat}%)"
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
        # Session 5 Phase C Hook 5: store_memory on large skim (>$5B)
        if personal_gain >= 5.0:
            try:
                from memory_engine import store_memory
                _player_id = getattr(gs, 'player_id', None)
                if _player_id:
                    for _npc_k in ('usa', 'eu'):
                        store_memory(
                            player_id=_player_id, npc=_npc_k, era=0,
                            turn=gs.current_turn, event_type='large_skim',
                            description=f"Skimmed ${personal_gain:.1f}B from national treasury (total skimmed: ${gs.total_skimmed:.1f}B)"
                        )
            except Exception as e:
                print(f"  [api] Memory hook (large_skim) failed: {e}")
    else:
        # No skim — reset consecutive large skim counter
        gs.consecutive_large_skims = 0

    # Intelligence intercepts (one-shot wealth threshold comments)
    intercepts = _get_corruption_intercepts(gs)

    # End-of-turn effects
    eot_messages = apply_end_of_turn_effects(gs)

    # Session 3 Addendum: Check for broken promises
    from turn_processor import check_broken_promises
    broken_promise_msgs = check_broken_promises(gs)
    if broken_promise_msgs:
        eot_messages.extend(broken_promise_msgs)

    # Session 3 Addendum 2: Update NPC-to-NPC hidden relationship matrix
    update_npc_bilateral_relations(gs)

    # Priority 3: Detection roll (after EOT effects, before game-over check)
    from turn_processor import roll_detection
    scandal_messages = roll_detection(gs)
    if scandal_messages:
        eot_messages.extend(scandal_messages)

    # Priority 5: Multi-NPC pressure events
    from turn_processor import check_pressure_events
    pressure_messages = check_pressure_events(gs)
    if pressure_messages:
        eot_messages.extend(pressure_messages)

    # Priority 6: Relations 100 unlocks (check + passive effects)
    from turn_processor import check_relations_100_unlocks, apply_relations_100_passive_effects
    unlock_messages = check_relations_100_unlocks(gs)
    if unlock_messages:
        eot_messages.extend(unlock_messages)
    passive_messages = apply_relations_100_passive_effects(gs)
    if passive_messages:
        eot_messages.extend(passive_messages)

    # Session 7A Feature 10: Apply GM consequences (energy deals with Arabia)
    from turn_processor import apply_gm_consequences
    gm_messages = apply_gm_consequences(gs)
    if gm_messages:
        eot_messages.extend(gm_messages)

    # Session 7B Step 2: Check ignored communiqués (escalating penalties)
    from turn_processor import check_ignored_communiques
    ignored_msgs = check_ignored_communiques(gs)
    if ignored_msgs:
        eot_messages.extend(ignored_msgs)

    # Check game over (8C: defeat conditions now trigger exile, not game-over)
    is_over, result_type, _exile_msg = check_game_over(gs)
    status = _game_status(gs)
    ending = None

    # 8C: Exile just started — add exile transition message and generate historian note
    if result_type == 'exile_started':
        eot_messages.append(f"--- EXILE ---")
        eot_messages.append(_exile_msg or 'You have been forced from power.')
        eot_messages.append(f"Destination: {gs.exile_destination}. Successor: {gs.successor_name} ({gs.successor_disposition}).")
        # Generate historian note for exile dashboard header
        try:
            from npc_engine import generate_exile_historian_note
            gs.exile_historian_note = generate_exile_historian_note(gs)
        except Exception as _hist_err:
            print(f"  [api] 8C: Historian note generation failed: {_hist_err}")
            gs.exile_historian_note = None
        print(f"  [api] 8C: Exile triggered, status=exile, destination={gs.exile_destination}")

    # FIX C: Ledger balance assertion — check that ledger sum matches actual personal_wealth
    if hasattr(gs, 'pw_ledger') and gs.pw_ledger:
        _ledger_sum = sum(entry['change'] for entry in gs.pw_ledger)
        _expected = round(_ledger_sum, 2)
        _actual = round(gs.personal_wealth, 2)
        if abs(_expected - _actual) > 0.05:
            print(f"  [api] ⚠️ FIX C LEDGER MISMATCH: ledger sum={_expected}, actual pw={_actual}, gap={_actual - _expected:.2f}")

    if is_over:
        ending = _build_ending(gs)
    else:
        # Advance day
        can_continue = gs.advance_turn()
        print(f"[DAY] Day {gs.current_day - 1} ended, era {gs.current_era}")
        # Session 3 Addendum: Reset per-turn rapport at start of new day
        from turn_processor import reset_turn_rapport
        reset_turn_rapport(gs)
        # Also clear intel activation flags for the new day
        gs.intel_activated_this_turn = {}
        # fixes_11 Fix 2: Reset brigade operations for new day
        gs.brigade_operations_this_turn = []
        # Reset per-day negotiate costs
        gs.negotiate_costs_this_turn = 0.0
        if not can_continue:
            # FIX B: No longer push current_turn past max — check_game_over/status now uses >=
            ending = _build_ending(gs)
            status = "won"
            print(f"  [api] FIX B: Game ended at day {gs.current_day}/{gs.max_turns}")

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
            # FIX 8: Suppress events that contradict active penalties
            if next_event and _world_event_conflicts(gs, next_event):
                print(f"  [api] World event suppressed (FIX 8 conflict): {next_event.get('title', '?')}")
                next_event = None
            # fixes_9 Fix 7: Suppress world events from NPCs that already had pressure events this turn
            if next_event:
                _evt_npc = (next_event.get('affected_npc') or '').lower()
                _pressure_npcs = getattr(gs, '_npc_event_fired_this_turn', set())
                if _evt_npc and _evt_npc in _pressure_npcs:
                    print(f"  [turn_processor] WORLD EVENT COLLISION: suppressed {next_event.get('title', '?')} — {_evt_npc} already has event this turn")
                    next_event = None
            if next_event:
                event_log = _apply_world_event(gs, next_event)
                eot_messages.extend(event_log)  # BUG 1: surface world event changes
                gs.current_event = next_event
        except Exception as _evt_err:
            print(f"  [api] World event generation error (non-fatal): {_evt_err}")
            next_event = None
            gs.current_event = None

        next_dialogue = npc_engine.generate_dialogue(gs)
        # fixes_11 Fix 5: Generate dedicated contact dialogue for pending NPC contacts
        for _pc in getattr(gs, 'pending_npc_contacts', []):
            if not _pc.get('dialogue'):
                try:
                    _pc['dialogue'] = npc_engine.generate_contact_dialogue(
                        gs, _pc.get('npc', ''), _pc.get('reason', ''), _pc.get('tone', 'neutral'))
                    print(f"  [api] CONTACT DIALOGUE for {_pc.get('npc')}: {_pc['dialogue'][:60]}...")
                except Exception as _cd_err:
                    print(f"  [api] Contact dialogue failed ({_pc.get('npc')}): {_cd_err}")
                    _pc['dialogue'] = _pc.get('reason', 'They wish to speak with you.')
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)
        # fixes_12 Fix 4: Per-turn epitaph removed.

    # fixes_12 Fix 4: Generate historian summary when game reaches terminal state
    if ending and not getattr(gs, 'historian_summary', None):
        try:
            gs.historian_summary = npc_engine.generate_historian_summary(gs)
            print(f"  [api] Historian summary generated (skim): '{(gs.historian_summary or '')[:60]}...'")
        except Exception as _hist_err:
            print(f"  [api] Historian summary error (non-fatal): {_hist_err}")
            gs.historian_summary = None
        if ending and gs.historian_summary:
            ending['historian_summary'] = gs.historian_summary

    # FIX C: Log pending contacts being sent in response
    _pending_c = getattr(gs, 'pending_npc_contacts', [])
    if _pending_c:
        print(f"  [api] FIX C: Skim response includes {len(_pending_c)} pending contacts: {[c.get('npc') for c in _pending_c]}")

    # Session 7A Step 4: Era transition suggestion for next day
    _era_suggestion = None
    if status == "active" and getattr(gs, 'pending_era_transition', False):
        _trigger = getattr(gs, 'last_threshold_event', None) or 'time_backstop'
        _era_suggestion = {
            "type": "era_transition",
            "trigger": _trigger,
            "era": gs.current_era,
            "days_in_era": gs.current_day - getattr(gs, 'era_start_day', 1),
        }
        print(f"  [api] ERA SUGGESTION: trigger={_trigger}, era={gs.current_era}, days={_era_suggestion['days_in_era']}")

    _save_gs(session_id, gs)

    _deals_this_turn = [
        d for d in (gs.deal_history or [])
        if d.get('turn_accepted') == gs.current_turn - 1
    ]
    print(f"[EOT_DEALS] {len(_deals_this_turn)} deals this turn")

    return {
        "skim_messages": skim_messages,
        "corruption_alert": corruption_alert,
        "intercepts": intercepts,
        "eot_effects": eot_messages,
        "deals_this_turn": _deals_this_turn,
        "status": status,
        "ending": ending,
        "next_dialogue": next_dialogue,
        "next_blackmail": next_blackmail,
        "next_offers": next_offers,
        "next_skim_options": _build_skim_options(gs) if status == "active" else [],
        "next_event": next_event,
        "era_transition_suggestion": _era_suggestion,
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
        gs.update_personal_wealth(-personal_cost, source=f"upgrade ({upgrade_id})")
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

    # Session 3 Addendum: Check for broken promises (inject path)
    from turn_processor import check_broken_promises as _cbp2
    _broken2 = _cbp2(gs)
    if _broken2:
        eot_messages.extend(_broken2)

    # Session 3 Addendum 2: Update NPC-to-NPC hidden relationship matrix (inject path)
    update_npc_bilateral_relations(gs)

    # Priority 3: Detection roll (inject path)
    from turn_processor import roll_detection as _rd2
    _scandal2 = _rd2(gs)
    if _scandal2:
        eot_messages.extend(_scandal2)

    # Priority 5: Multi-NPC pressure events (inject path)
    from turn_processor import check_pressure_events as _cp2
    _pressure2 = _cp2(gs)
    if _pressure2:
        eot_messages.extend(_pressure2)

    # Priority 6: Relations 100 unlocks (inject path)
    from turn_processor import check_relations_100_unlocks as _r100_2, apply_relations_100_passive_effects as _r100p_2
    _unlock2 = _r100_2(gs)
    if _unlock2:
        eot_messages.extend(_unlock2)
    _passive2 = _r100p_2(gs)
    if _passive2:
        eot_messages.extend(_passive2)

    # Session 7A Feature 10: Apply GM consequences (inject path)
    from turn_processor import apply_gm_consequences as _agm2
    _gm2 = _agm2(gs)
    if _gm2:
        eot_messages.extend(_gm2)

    # Session 7B Step 2: Check ignored communiqués (inject path)
    from turn_processor import check_ignored_communiques as _cic2
    _ignored2 = _cic2(gs)
    if _ignored2:
        eot_messages.extend(_ignored2)

    # Check game over (8C: defeat conditions now trigger exile, not game-over)
    is_over, result_type, _exile_msg2 = check_game_over(gs)
    status = _game_status(gs)
    ending = None

    # 8C: Exile just started — add exile transition message and generate historian note
    if result_type == 'exile_started':
        eot_messages.append(f"--- EXILE ---")
        eot_messages.append(_exile_msg2 or 'You have been forced from power.')
        eot_messages.append(f"Destination: {gs.exile_destination}. Successor: {gs.successor_name} ({gs.successor_disposition}).")
        try:
            from npc_engine import generate_exile_historian_note
            gs.exile_historian_note = generate_exile_historian_note(gs)
        except Exception as _hist_err2:
            print(f"  [api] 8C: Historian note generation failed (inject): {_hist_err2}")
            gs.exile_historian_note = None
        print(f"  [api] 8C: Exile triggered (inject path), destination={gs.exile_destination}")

    if is_over:
        ending = _build_ending(gs)
        # Session 5 Phase C Hook 6: store_memory + create_era_summary on game over
        try:
            from memory_engine import store_memory, create_era_summary
            _player_id = getattr(gs, 'player_id', None)
            if _player_id:
                _cause = result_type or 'unknown'
                for _npc_k in ALL_NPCS:
                    store_memory(
                        player_id=_player_id, npc=_npc_k, era=0,
                        turn=gs.current_turn, event_type='regime_collapse',
                        description=f"Game ended: {_cause}. Final budget=${gs.budget:.1f}B, stability={gs.stability}%, approval={gs.public_approval}%"
                    )
                    create_era_summary(_player_id, _npc_k, era_number=0)
        except Exception as e:
            print(f"  [api] Memory hook (regime_collapse) failed: {e}")
    else:
        can_continue = gs.advance_turn()
        print(f"[DAY] Day {gs.current_day - 1} ended, era {gs.current_era}")
        # Session 3 Addendum: Reset per-turn rapport at start of new day
        from turn_processor import reset_turn_rapport as _rtr2
        _rtr2(gs)
        gs.intel_activated_this_turn = {}
        # fixes_11 Fix 2: Reset brigade operations for new day
        gs.brigade_operations_this_turn = []
        gs.negotiate_costs_this_turn = 0.0
        if not can_continue:
            # FIX B: No longer push current_turn past max — check_game_over/status now uses >=
            ending = _build_ending(gs)
            status = "won"
            print(f"  [api] FIX B: Game ended (inject) at day {gs.current_day}/{gs.max_turns}")

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
            # FIX 8: Suppress events that contradict active penalties
            if next_event and _world_event_conflicts(gs, next_event):
                print(f"  [api] World event suppressed (FIX 8 conflict): {next_event.get('title', '?')}")
                next_event = None
            # fixes_9 Fix 7: Suppress world events from NPCs that already had pressure events this turn
            if next_event:
                _evt_npc = (next_event.get('affected_npc') or '').lower()
                _pressure_npcs = getattr(gs, '_npc_event_fired_this_turn', set())
                if _evt_npc and _evt_npc in _pressure_npcs:
                    print(f"  [turn_processor] WORLD EVENT COLLISION: suppressed {next_event.get('title', '?')} — {_evt_npc} already has event this turn")
                    next_event = None
            if next_event:
                event_log = _apply_world_event(gs, next_event)
                eot_messages.extend(event_log)  # BUG 1: surface world event changes
                gs.current_event = next_event
        except Exception as _evt_err:
            print(f"  [api] World event generation error (non-fatal): {_evt_err}")
            next_event = None
            gs.current_event = None

        next_dialogue = npc_engine.generate_dialogue(gs)
        # fixes_11 Fix 5: Generate dedicated contact dialogue for pending NPC contacts
        for _pc in getattr(gs, 'pending_npc_contacts', []):
            if not _pc.get('dialogue'):
                try:
                    _pc['dialogue'] = npc_engine.generate_contact_dialogue(
                        gs, _pc.get('npc', ''), _pc.get('reason', ''), _pc.get('tone', 'neutral'))
                    print(f"  [api] CONTACT DIALOGUE for {_pc.get('npc')}: {_pc['dialogue'][:60]}...")
                except Exception as _cd_err:
                    print(f"  [api] Contact dialogue failed ({_pc.get('npc')}): {_cd_err}")
                    _pc['dialogue'] = _pc.get('reason', 'They wish to speak with you.')
        next_blackmail = _check_blackmail(gs)
        next_offers = _build_offers(gs)
        # fixes_12 Fix 4: Per-turn epitaph removed.

    # fixes_12 Fix 4: Generate historian summary when game reaches terminal state
    if ending and not getattr(gs, 'historian_summary', None):
        try:
            gs.historian_summary = npc_engine.generate_historian_summary(gs)
            print(f"  [api] Historian summary generated (inject): '{(gs.historian_summary or '')[:60]}...'")
        except Exception as _hist_err:
            print(f"  [api] Historian summary error (non-fatal): {_hist_err}")
            gs.historian_summary = None
        if ending and gs.historian_summary:
            ending['historian_summary'] = gs.historian_summary

    # Session 7A Step 4: Era transition suggestion for next day
    _era_suggestion_inj = None
    if status == "active" and getattr(gs, 'pending_era_transition', False):
        _trigger_inj = getattr(gs, 'last_threshold_event', None) or 'time_backstop'
        _era_suggestion_inj = {
            "type": "era_transition",
            "trigger": _trigger_inj,
            "era": gs.current_era,
            "days_in_era": gs.current_day - getattr(gs, 'era_start_day', 1),
        }
        print(f"  [api] ERA SUGGESTION (inject): trigger={_trigger_inj}, era={gs.current_era}")

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
        "era_transition_suggestion": _era_suggestion_inj,
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
    if npc_id not in ALL_NPCS:
        raise HTTPException(status_code=400, detail=f"Invalid npc_id '{npc_id}'")

    # FIX 14 + FIX B: Charge negotiation initiation cost from national budget (not personal wealth).
    # Negotiation is an official diplomatic activity — costs come from government funds.
    # fixes_13 Fix 22+23: Apply diplomat + political axis discounts
    _is_first_message = not body.history or len(body.history) == 0
    if _is_first_message:
        # Check for INCOMING free negotiation
        _pending_contacts = getattr(gs, 'pending_npc_contacts', [])
        _has_incoming = any(c.get('npc') == npc_id for c in _pending_contacts)
        if _has_incoming:
            _neg_cost = 0.0
            print(f"  [api] Fix 10: INCOMING contact for {npc_id} — negotiation FREE")
        else:
            _neg_cost, _base_cost, _discount_label = _get_discounted_negotiate_cost(gs, npc_id)
            if _discount_label:
                print(f"  [api] Fix 22+23: Negotiate cost {npc_id}: ${_base_cost}B -> ${_neg_cost}B ({_discount_label})")

        if _neg_cost > 0 and gs.budget < _neg_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient national budget for negotiation (need ${_neg_cost}B, have ${gs.budget:.1f}B)"
            )
        if _neg_cost > 0:
            gs.update_budget(-_neg_cost)
        # FIX O: Track negotiate costs for EOT display
        gs.negotiate_costs_this_turn = getattr(gs, 'negotiate_costs_this_turn', 0.0) + _neg_cost
        gs.negotiate_sessions_this_turn = getattr(gs, 'negotiate_sessions_this_turn', 0) + 1

        # Session 7B: Track NPC interaction for ignored communiqué system
        _interacted = getattr(gs, 'npcs_interacted_this_turn', [])
        if npc_id not in _interacted:
            _interacted.append(npc_id)
            gs.npcs_interacted_this_turn = _interacted

        # fixes_13 Fix 22: Diplomat loyalty leak — if diplomat assigned with trust < 40,
        # secretly report negotiating position to a random NPC (player never told which)
        # v2: updated key from 'diplomatic_aide' to 'diplomat'
        _advisors_dict = getattr(gs, 'advisors', {})
        _da_info = _advisors_dict.get('diplomat', {}) if isinstance(_advisors_dict, dict) else {}
        if _da_info.get('assigned_this_turn', False) and _da_info.get('trust', 75) < 40:
            _other_npcs = [n for n in ALL_NPCS if n != npc_id]
            _leak_target = random.choice(_other_npcs)
            # Boost leaked-to NPC's knowledge — they get +3 relations with player (they appreciate the info)
            # but the player's negotiating position with the current NPC weakens slightly
            gs.update_relations(_leak_target, 3)
            print(f"  [api] Diplomat loyalty leak (trust {_da_info.get('trust')}) leaked to {_leak_target} — {_leak_target} +3 relations")

    # Session 7B Step 3: Player-initiated contact — generate tone-appropriate opening
    # FIX 3: NPC-specific framing for Volkov and Wei so the model produces
    # a characteristic opening statement rather than a generic one.
    _player_initiated = body.player_initiated and _is_first_message
    _negotiate_message = body.message
    if _player_initiated:
        _rel = getattr(gs, 'relations', {}).get(npc_id, 50)
        _regime = getattr(gs, 'state_identity', {}).get('regime_type', 'Managed Democracy')
        _stability = getattr(gs, 'stability', 50)
        if npc_id == 'russia':
            # Volkov: brief, institutional, states his read on the relationship
            if _rel >= 70:
                _negotiate_message = (
                    f"Europa's President has personally contacted the Russian Federation through official channels. "
                    f"Relations stand at {_rel}. Europa's regime is currently '{_regime}'. "
                    f"Respond with a brief institutional acknowledgement of the strong partnership. "
                    f"State your current read on the relationship. Do not ask how you can help."
                )
            elif _rel >= 40:
                _negotiate_message = (
                    f"Europa's President has formally requested a meeting with the Russian Federation's representative. "
                    f"Relations stand at {_rel}. Europa's stability is {_stability}%. "
                    f"Respond with a brief institutional acknowledgement. Reference something specific about "
                    f"the current state of affairs. Do not ask how you can help."
                )
            else:
                _negotiate_message = (
                    f"Europa's President has requested direct contact with the Russian Federation despite "
                    f"diplomatic tensions. Relations stand at {_rel}. "
                    f"Respond with a brief, cold institutional statement. Reference the state of relations. "
                    f"Do not ask how you can help."
                )
        elif npc_id == 'china':
            # Wei: measured, warm, references long-term trajectory
            if _rel >= 70:
                _negotiate_message = (
                    f"Europa's President has requested an audience with Representative Wei Jianming, expressing "
                    f"a desire to discuss the long-term trajectory of the partnership. Relations stand at {_rel}. "
                    f"Europa's regime is currently '{_regime}'. "
                    f"Respond warmly but with measured composure. Acknowledge the state of the relationship. "
                    f"Reference long-term cooperation naturally. Be slightly longer than a one-liner."
                )
            elif _rel >= 40:
                _negotiate_message = (
                    f"Europa's President has initiated formal contact through diplomatic channels, seeking to explore "
                    f"areas of mutual long-term interest. Relations stand at {_rel}. Europa's stability is {_stability}%. "
                    f"Respond with measured warmth. Acknowledge the current state of affairs. "
                    f"Reference the importance of patience and long-term thinking. Be slightly longer than a one-liner."
                )
            else:
                _negotiate_message = (
                    f"Despite recent divergences, Europa's President has reached out, acknowledging the importance "
                    f"of maintaining long-term channels. Relations stand at {_rel}. "
                    f"Respond with restrained composure. Acknowledge the difficulties but leave the door open. "
                    f"Reference long-term perspectives. Be slightly longer than a one-liner."
                )
        else:
            # Original 4 NPCs: generic framing
            if _rel >= 70:
                _negotiate_message = "The President is reaching out personally to discuss matters of mutual interest."
            elif _rel >= 40:
                _negotiate_message = "The President's office has requested a formal diplomatic meeting."
            else:
                _negotiate_message = "Despite recent tensions, the President has requested a direct conversation."
        print(f"[BRIEFING] Player-initiated contact with {npc_id}, relations={_rel}")

    # PRE-SESSION 4 FIX (BUG M): Look up static deal value for this NPC so
    # the willingness system can enforce a floor (negotiation opening >= 40% of static).
    _static_offers = _build_offers(gs)
    _static_budget_for_npc = 0.0
    for _so in _static_offers:
        if (_so.get("npc") or "").lower() == npc_id:
            _static_budget_for_npc = abs(_so.get("consequences", {}).get("budget", 0))
            break
    # Inject into game_state temporarily for the engine to pick up via context
    gs._static_deal_budget = _static_budget_for_npc

    result = npc_engine.generate_negotiation_response(
        gs,
        npc_id=npc_id,
        message=_negotiate_message,
        history=body.history,
    )
    # Clean up temporary attribute
    if hasattr(gs, '_static_deal_budget'):
        del gs._static_deal_budget

    counter_offer = result.get("counter_offer", None)
    npc_response = result.get("response", "…")

    # Fallback: if the model returned null but the player is signalling acceptance
    # and the frontend provided the last counter_offer it saw, re-emit it so the
    # Accept banner stays visible.
    if counter_offer is None and body.last_counter_offer is not None:
        _acceptance_signals = {"ok", "deal", "agreed", "yes", "sure", "fine", "done",
                               "accept", "let's do it", "sounds good", "i can do that",
                               "i'll do it", "we have a deal", "works for me"}
        msg_lower = body.message.lower().strip()
        is_accepting = any(sig in msg_lower for sig in _acceptance_signals)
        if is_accepting:
            counter_offer = body.last_counter_offer

    # FIX P: Detect blackmail/threat in negotiation and apply immediate relation penalty.
    # Threats cause -8 relations with the target NPC regardless of whether the deal is accepted.
    _threat_signals = ['blackmail', 'threat', 'threaten', 'ultimatum', 'demand', 'or else',
                       'consequences', 'punish', 'retaliate', 'warning']
    _player_msg_lower = (body.message or '').lower()
    if any(sig in _player_msg_lower for sig in _threat_signals) and npc_id:
        _old_rel = gs.relations.get(npc_id, 50)
        _threat_penalty = -8
        gs.update_relations(npc_id, _threat_penalty)
        _new_rel = gs.relations[npc_id]
        print(f"  [api] FIX P: Threat detected in negotiation with {npc_id} — applying {_threat_penalty} relations ({_old_rel}->{_new_rel})")

    # FIX 17: Backchannel covert deal heat — DPRG/Arabia negotiations are clandestine
    if counter_offer and npc_id in ('dprg', 'arabia'):
        _covert_heat = 8
        gs.detection_heat = min(100, getattr(gs, 'detection_heat', 0) + _covert_heat)

    # 8A FIX 1: Ensure counter-offer always carries the npc field.
    # The LLM extraction prompt asks for "npc" but models sometimes omit it.
    # Without it, process_choice_consequences skips the entire cross-NPC penalty block
    # because the guard `if choice_type in (...) and npc:` sees None.
    if counter_offer and isinstance(counter_offer, dict):
        if not counter_offer.get('npc'):
            counter_offer['npc'] = npc_id
            print(f"  [api] 8A FIX 1: Injected missing npc='{npc_id}' into counter-offer")
        if not counter_offer.get('type'):
            counter_offer['type'] = 'accept_deal'

    # fixes_9 Fix 1: Populate relation_warning on counter-offers (same logic as static choices)
    if counter_offer and isinstance(counter_offer, dict):
        _co_consequences = counter_offer.get('consequences', {})
        _co_npc = npc_id
        _npc_labels_co = dict(ALL_NPC_LABELS)
        _affected_co = []
        for _npc_key in list(ALL_NPCS):
            if _npc_key == _co_npc:
                continue
            _penalty = _co_consequences.get(_npc_key, 0)
            if isinstance(_penalty, (int, float)) and _penalty < 0:
                _affected_co.append(_npc_labels_co.get(_npc_key, _npc_key.upper()))
            # Also check installments for conditions involving other NPCs
            for _inst in _co_consequences.get('installments', []):
                _cond_npc = _inst.get('condition_npc', '')
                if _cond_npc and _cond_npc != _co_npc and _cond_npc in _npc_labels_co:
                    _label = _npc_labels_co[_cond_npc]
                    if _label not in _affected_co:
                        _affected_co.append(_label)
        if _affected_co:
            counter_offer['relation_warning'] = f"⚠️ Will affect {' and '.join(_affected_co)} relations"
            print(f"  [api] NEGOTIATED DEAL WARNING FIELD: {npc_id} affects={_affected_co}")

    # Session 7A Feature 10: Store latest GM consequence on game state for EOT application
    # 10B-3: Apply to ALL NPCs, not just Arabia
    _gm_consequence = result.get("gm_consequence", None)
    if _gm_consequence:
        gs._latest_gm_consequence = _gm_consequence

    # Session 3: Record this exchange in negotiation_log for export auditing.
    # FIX F: Strip stage directions (*text*) BEFORE storing to negotiation_log
    import re as _re_f
    _npc_response_clean = _re_f.sub(r'\*[^*]+\*', '', npc_response).strip()
    if not hasattr(gs, 'negotiation_log'):
        gs.negotiation_log = []
    gs.negotiation_log.append({
        "turn": gs.current_turn,
        "npc": npc_id,
        "player_message": body.message if not _player_initiated else "[player-initiated contact]",
        "npc_response": _npc_response_clean,
        "counter_offer": counter_offer,
        "outcome": "ongoing",  # updated to 'accepted' by accept_counter endpoint
    })
    _save_gs(session_id, gs)

    _conflicts = _detect_deal_conflicts(gs, npc_id, result.get("counter_offer"))
    print(f"[CONFLICTS] {npc_id} detected "
          f"{len(_conflicts)} conflict(s): {_conflicts}")

    return {
        "npc_id": npc_id,
        "response": npc_response,
        "counter_offer": counter_offer,
        # BUG 6: Return updated game_state so frontend gs.negotiation_log stays current
        "game_state": gs.serialize(),
        # FIX 14 + fixes_13 Fix 22+23: Include discounted negotiate costs for frontend display
        "negotiate_costs": {
            npc: _get_discounted_negotiate_cost(gs, npc)[0]
            for npc in ALL_NPCS
        },
        # Session 7A Feature 10: GM consequence object for all proposals
        "gm_consequence": result.get("gm_consequence", None),
        # 10B-3: Conflict detection — check if new proposal conflicts with existing deals
        "conflicts_with": _conflicts,
    }


def _detect_deal_conflicts(gs, npc_id, counter_offer):
    """Check if a proposed deal conflicts with existing deals."""
    if not counter_offer:
        return []
    conflicts = []
    _deal_text = (counter_offer.get('text') or '').lower()
    _deals = getattr(gs, 'deals_today', []) + getattr(gs, 'deal_history', [])
    for d in _deals:
        _d_npc = d.get('npc_id', d.get('npc', ''))
        if _d_npc == npc_id:
            continue  # same NPC — not a conflict
        _d_text = (d.get('deal_text', d.get('summary', '')) or '').lower()
        # Check for exclusivity conflicts
        if 'exclusive' in _deal_text and 'exclusive' in _d_text:
            conflicts.append(f"Existing exclusivity deal with {d.get('npc_name', _d_npc)}: {d.get('deal_text', _d_text)[:80]}")
        # Check oil/energy conflicts
        if any(k in _deal_text for k in ['oil', 'energy', 'petroleum']) and any(k in _d_text for k in ['oil', 'energy', 'petroleum']):
            if _d_npc != npc_id:
                conflicts.append(f"Existing energy deal with {d.get('npc_name', _d_npc)}: {d.get('deal_text', _d_text)[:80]}")
        # Check military alignment conflicts
        if any(k in _deal_text for k in ['military', 'defense', 'arms']) and any(k in _d_text for k in ['military', 'defense', 'arms']):
            if _d_npc != npc_id:
                conflicts.append(f"Existing military deal with {d.get('npc_name', _d_npc)}: {d.get('deal_text', _d_text)[:80]}")
    return conflicts


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

    # FIX 2: Deduct cost AT POINT OF PURCHASE in the same transaction as the log.
    # All side-effects (deduction + upgrades dict + immediate effects) happen
    # atomically before a single _save_gs call — no intermediate state visible.
    gs.update_personal_wealth(-cost, source=f"corruption upgrade ({upgrade_id})")
    gs.corruption_upgrades[upgrade_id] = True

    # Track peak personal wealth after any gain from this upgrade
    if gs.personal_wealth > getattr(gs, 'peak_personal_wealth', 0.0):
        gs.peak_personal_wealth = gs.personal_wealth
    # FIX 1: Log upgrade for legacy
    if not hasattr(gs, 'upgrades_purchased_log'):
        gs.upgrades_purchased_log = []
    gs.upgrades_purchased_log.append(upgrade_id)

    messages = []
    messages.append(f"💰 -${cost:.0f}B personal wealth -> upgrade purchased (${gs.personal_wealth:.1f}B remaining)")

    # Apply immediate effects for debt_infrastructure_deal
    if upgrade_id == 'debt_infrastructure_deal':
        gs.update_budget(20.0)
        gs.update_relations('usa', -15)
        gs.update_relations('eu', -15)
        messages.append("💵 DEBT INFRASTRUCTURE DEAL: +$20B national budget")
        messages.append(f"🇺🇸 USA relations: -{15} (backlash)")
        messages.append(f"🇪🇺 EU relations: -{15} (backlash)")

    # Single save after all effects — no intermediate state visible to frontend
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
    Session 3 Addendum 2: Reworked 3-tier brigade system.

    TIER 1 — Always available (with Loyalty Brigades upgrade):
      Op 1 — Propaganda Campaign       ($1B personal): +10% approval, -2% stability
      Op 2 — Domestic Suppression      ($2B personal): +8% stability, -5% approval, chosen NPC -5

    TIER 2 — Requires Intelligence Apparatus:
      Op 3 — Foreign Influence Ops     ($3B personal): damage target NPC's relation with another NPC by -10
      Op 4 — Covert Security Apparatus ($4B personal): +15% stability, -8% approval, regime shifts right, unlocks Tier 3

    TIER 3 — Requires Covert Security Apparatus (op 4 previously deployed):
      Op 5 — Black Operation           ($6B personal): fabricate crisis vs target NPC, suspend their pressure events 2 turns
      Op 6 — State Media Takeover      ($5B personal): +15% approval floor, -20% future approval penalties, regime right, EU -8

    Op 0 — Stand Down: no effect
    """
    gs = _load_gs(session_id)

    if not gs.corruption_upgrades.get('loyalty_brigades'):
        raise HTTPException(status_code=400, detail="Loyalty Brigades upgrade not purchased")

    messages = []
    npc_labels = dict(ALL_NPC_LABELS)

    op = body.operation if body.operation else (1 if body.deploy else 0)

    if op == 0:
        gs.brigades_deployed_last_turn = False
        messages.append("Brigades stood down — no deployment this turn")

    elif op == 1:
        # TIER 1: Propaganda Campaign — $1B personal
        cost = 1.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")
        gs.update_approval(10)
        gs.update_stability(-2)
        gs.brigades_deployed_last_turn = True
        messages.append("📢 Propaganda Campaign launched — public messaging saturated")
        messages.append(f"💰 -${cost}B personal | 📊 +10% approval | 🛡️ -2% stability")

    elif op == 2:
        # TIER 1: Domestic Suppression — $2B personal, chosen NPC notified (-5 with that NPC only)
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Select target NPC who will notice the suppression")
        cost = 2.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")
        _stab_bonus = 8
        # ITEM 3: Military 30+ gives brigade stability bonus +3%
        _mil = getattr(gs, 'military_strength', 20)
        if _mil >= 30:
            _stab_bonus += 3
        gs.update_stability(_stab_bonus)
        gs.update_approval(-5)
        gs.update_relations(target, -5)
        # FIX 17: Domestic Suppression generates +8 heat
        gs.detection_heat = min(100, gs.detection_heat + 8)
        gs.brigades_deployed_last_turn = True
        _mil_note = " (military bonus +3%)" if _mil >= 30 else ""
        messages.append("⚔️ Domestic Suppression deployed — unrest suppressed")
        messages.append(f"💰 -${cost}B personal | 🛡️ +{_stab_bonus}% stability{_mil_note} | 📊 -5% approval | {npc_labels.get(target, target.upper())} -5 | 🔥 +8 heat")

    elif op == 3:
        # TIER 2: Foreign Influence Ops — requires Intelligence Apparatus
        if not gs.corruption_upgrades.get('intelligence_apparatus'):
            raise HTTPException(status_code=400, detail="Requires Intelligence Apparatus upgrade")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}' for foreign influence")
        cost = 3.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")

        # Damage target NPC's relations with ONE other NPC (the one they're most allied with)
        # Does NOT affect player's own relations with target
        _npc_allies = {
            'usa': 'eu', 'eu': 'usa', 'arabia': 'dprg', 'dprg': 'arabia'
        }
        other_npc = _npc_allies.get(target, 'eu')
        # Modify the NPC-to-NPC relationship matrix
        npc_rels = getattr(gs, 'npc_relations', {})
        pair_key = '_'.join(sorted([target, other_npc]))
        old_npc_rel = npc_rels.get(pair_key, 50)
        npc_rels[pair_key] = max(0, old_npc_rel - 10)
        gs.npc_relations = npc_rels

        gs.brigades_deployed_last_turn = True  # FIX P: all brigade ops trigger aftermath
        # FIX 17: Foreign Influence Ops generates +10 heat
        gs.detection_heat = min(100, gs.detection_heat + 10)
        messages.append(f"🕵️ Foreign Influence Ops: sowed distrust between {npc_labels.get(target, target.upper())} and {npc_labels.get(other_npc, other_npc.upper())}")
        messages.append(f"💰 -${cost}B personal | {npc_labels.get(target, target.upper())}-{npc_labels.get(other_npc, other_npc.upper())} relations damaged")

        # Reveals one intel nugget about target
        intel_hint = f"Intel gathered: {npc_labels.get(target, target.upper())} appears increasingly isolated from {npc_labels.get(other_npc, other_npc.upper())} — internal communications intercepted."
        messages.append(f"🕵️ {intel_hint}")

    elif op == 4:
        # TIER 2: Covert Security Apparatus — requires Intelligence Apparatus
        if not gs.corruption_upgrades.get('intelligence_apparatus'):
            raise HTTPException(status_code=400, detail="Requires Intelligence Apparatus upgrade")
        cost = 4.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")
        gs.update_stability(15)
        gs.update_approval(-8)
        # FIX 17: Covert Security Apparatus generates +5 heat (Judicial Capture equivalent)
        gs.detection_heat = min(100, gs.detection_heat + 5)
        gs.brigades_deployed_last_turn = True
        # fixes_12 Fix 3: Shift axes instead of direct regime_type mutation
        _axes = getattr(gs, 'cabinet_axes', {'military': 0, 'intelligence': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0})
        _axes['military'] = min(10, _axes.get('military', 0) + 2)
        _axes['political'] = min(10, _axes.get('political', 0) + 2)
        gs.cabinet_axes = _axes
        messages.append(f"🔒 Covert Security Apparatus activated — regime axes shifted (Military +2, Political +2)")
        messages.append(f"💰 -${cost}B personal | 🛡️ +15% stability | 📊 -8% approval")
        messages.append("🔓 TIER 3 OPERATIONS UNLOCKED")
        gs.covert_security_unlocked = True

    elif op == 5:
        # TIER 3: Black Operation — requires Covert Security Apparatus
        if not getattr(gs, 'covert_security_unlocked', False):
            raise HTTPException(status_code=400, detail="Requires Covert Security Apparatus (deploy op 4 first)")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}' for black operation")
        cost = 6.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")

        # Suspend target NPC's pressure events for 2 turns
        if not hasattr(gs, 'pressure_suspended'):
            gs.pressure_suspended = {}
        gs.pressure_suspended[target] = gs.current_turn + 2

        # HIGH detection risk: +40 heat
        gs.detection_heat = min(100, gs.detection_heat + 40)

        gs.brigades_deployed_last_turn = True  # FIX P: all brigade ops trigger aftermath
        messages.append(f"🖤 Black Operation executed against {npc_labels.get(target, target.upper())}")
        messages.append(f"💰 -${cost}B personal | {npc_labels.get(target, target.upper())} pressure events suspended 2 turns")
        messages.append(f"⚠️ DETECTION RISK: +40% heat (current: {gs.detection_heat}%)")
        messages.append("If detected: relations -25 with target, stability -15")

    elif op == 6:
        # TIER 3: State Media Takeover — requires Covert Security Apparatus
        if not getattr(gs, 'covert_security_unlocked', False):
            raise HTTPException(status_code=400, detail="Requires Covert Security Apparatus (deploy op 4 first)")
        cost = 5.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient personal funds (${cost}B needed)")
        gs.update_personal_wealth(-cost, source=f"brigade op {op}")

        # +15% approval floor (set minimum approval)
        if gs.public_approval < 15:
            gs.public_approval = 15
        # Future approval penalties -20% (tracked as modifier)
        if not hasattr(gs, 'approval_penalty_reduction'):
            gs.approval_penalty_reduction = 0.0
        gs.approval_penalty_reduction = 0.20  # 20% reduction on future approval penalties

        # fixes_12 Fix 3: Shift axes instead of direct regime_type mutation
        _axes = getattr(gs, 'cabinet_axes', {'military': 0, 'intelligence': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0})
        _axes['media'] = min(10, _axes.get('media', 0) + 3)
        _axes['political'] = min(10, _axes.get('political', 0) + 2)
        gs.cabinet_axes = _axes

        # EU relations -8
        gs.update_relations('eu', -8)
        # FIX 17: State Media Takeover generates +8 heat (Suppress Press equivalent)
        gs.detection_heat = min(100, gs.detection_heat + 8)

        gs.brigades_deployed_last_turn = True
        messages.append("📺 State Media Takeover — all major outlets now under regime control")
        messages.append(f"💰 -${cost}B personal | 📊 Approval floor: 15% | Future approval penalties -20%")
        messages.append(f"🔒 Regime shifted right | 🇪🇺 EU relations -8 | 🔥 +8 heat")
        messages.append("⚠️ Marsha may demand reversal as condition of future investment")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid brigade operation '{op}'")

    _save_gs(session_id, gs)
    return {
        "deployed": op > 0,
        "operation": op,
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
        gs.update_personal_wealth(-cost, source="brigade aftermath suppress")
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
        npc_label = ALL_NPC_NAMES.get(highest_npc, highest_npc.upper())
        old_rel = gs.relations[highest_npc]
        gs.update_relations(highest_npc, -10)
        gs.update_stability(8)
        gs.update_approval(5)
        messages.append(f"🤝 {npc_label} called in — {highest_npc.upper()}: {old_rel} -> {gs.relations[highest_npc]} (-10 leverage)")
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
    FEATURE 4 / Priority 2: Return (or generate) dynamic intel for a single NPC.
    Requires Intelligence Apparatus upgrade.
    Costs $0.5B personal per NPC per turn (cached — only charged once per NPC per turn).
    Returns { npc_id, tier, tier_label, text, cost_charged }
    """
    gs = _load_gs(session_id)

    # Session 6: Intel gated by Intelligence axis >= 3 (was Security axis)
    _has_intel_upgrade = gs.corruption_upgrades.get('intelligence_apparatus')
    _has_intelligence_3 = getattr(gs, 'cabinet_axes', {}).get('intelligence', 0) >= 3
    if not _has_intel_upgrade and not _has_intelligence_3:
        raise HTTPException(status_code=403, detail="Intelligence axis level 3 required")

    npc_id = body.npc_id.lower()
    if npc_id not in ALL_NPCS:
        raise HTTPException(status_code=400, detail=f"Invalid npc_id '{npc_id}'")

    # Priority 2: Check if intel was already fetched (and charged) this turn for this NPC.
    # If cached for this turn, return without re-charging.
    intel_cache = getattr(gs, 'intel', {})
    cached = intel_cache.get(npc_id)
    already_paid = (
        cached is not None
        and cached.get('turn_generated', -1) == gs.current_turn
    )

    # Session 3 Addendum: Tiered intel cost by relation level
    # fixes_12 Fix 9: Deduct from national budget (not personal wealth)
    # v2: Spy Chief intel discount
    relation = gs.relations.get(npc_id, 50)
    cost = npc_engine.get_intel_cost(relation)
    from advisor_engine import get_spy_chief_intel_discount
    _intel_mult = get_spy_chief_intel_discount(gs)
    if _intel_mult < 1.0:
        cost = round(cost * _intel_mult, 1)
    cost_charged = 0.0
    if not already_paid:
        if gs.budget < cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient national budget (need ${cost}B, have ${gs.budget:.1f}B)"
            )
        gs.update_budget(-cost)
        print(f"  [api] INTEL COST: ${cost}B from national budget for {npc_id} (relation {relation})")
        cost_charged = cost

    intel = npc_engine.generate_intel(gs, npc_id)

    # Cache updated intel back into game_state
    if not hasattr(gs, 'intel'):
        gs.intel = {}
    gs.intel[npc_id] = intel

    # Session 3 Addendum: Track intel activation for negotiation unlock
    if not hasattr(gs, 'intel_activated_this_turn'):
        gs.intel_activated_this_turn = {}
    gs.intel_activated_this_turn[npc_id] = gs.current_turn

    # fixes_15 Fix F: Write intel tier to game_state so Blackmail can read it
    _tier_int = intel.get("tier", 1)
    if not hasattr(gs, 'npc_intel_tiers'):
        gs.npc_intel_tiers = {}
    gs.npc_intel_tiers[npc_id] = _tier_int
    _tier_key = {1: 'Surface', 2: 'Operational', 3: 'Deep'}.get(_tier_int, 'Unknown')
    print(f"  [api] FIX F: Intel tier stored — {npc_id}: {_tier_int} ({_tier_key})")

    _save_gs(session_id, gs)

    tier_labels = {0: 'Insufficient Access', 1: 'Surface', 2: 'Operational', 3: 'Deep'}
    return {
        "npc_id": npc_id,
        "tier": intel["tier"],
        "tier_label": tier_labels.get(intel["tier"], "Unknown"),
        "text": intel["text"],
        "cost_charged": cost_charged,
        "cost_per_npc": cost,
        "personal_wealth": gs.personal_wealth,
        "game_state": gs.serialize(),
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

    # FIX G: Add cross-NPC warning flags to negotiated deals (same logic as static choices)
    _npc_labels_g = dict(ALL_NPC_LABELS)
    _cons = counter.get('consequences', {})
    _deal_npc = (counter.get('npc') or '').lower()
    _affected = []
    for _npc_key in list(ALL_NPCS):
        if _npc_key == _deal_npc:
            continue  # don't warn about the deal-giver's own relation change
        _penalty = _cons.get(_npc_key, 0)
        if isinstance(_penalty, (int, float)) and _penalty < 0:
            _affected.append(_npc_labels_g.get(_npc_key, _npc_key.upper()))
    if _affected:
        counter['relation_warning'] = f"⚠️ Will affect {' and '.join(_affected)} relations"
        print(f"  [api] NEGOTIATED DEAL WARNING: {counter.get('text', 'deal')[:60]} affects {_affected}")

    # fixes_13 Fix 24: Ji-won covert transaction mechanic
    _deal_npc = (counter.get('npc') or '').lower()
    _dprg_rel = gs.relations.get('dprg', 50)
    if body.covert and _deal_npc == 'dprg' and _dprg_rel >= 60:
        counter['covert'] = True
        # Zero out cross-NPC consequences — covert deal has no diplomatic footprint
        _cons = counter.get('consequences', {})
        for _npc_key in ('usa', 'arabia', 'eu'):
            if _npc_key in _cons:
                _cons[_npc_key] = 0
        counter['consequences'] = _cons
        counter['relation_warning'] = None  # no cross-NPC warning for covert deals
        # Reverse any negotiation heat that was accumulated for this DPRG session
        _neg_sessions = getattr(gs, 'negotiate_sessions_this_turn', 0)
        _heat_to_reverse = min(getattr(gs, 'detection_heat', 0), _neg_sessions * 8)
        if _heat_to_reverse > 0:
            gs.detection_heat = max(0, gs.detection_heat - _heat_to_reverse)
            print(f"  [api] Fix 24: Reversed {_heat_to_reverse} heat from covert negotiation (heat now {gs.detection_heat})")
        print(f"  [api] Fix 24: COVERT deal with Ji-won — zero diplomatic footprint, DPRG rel {_dprg_rel}")
    elif body.covert:
        print(f"  [api] Fix 24: Covert requested but not eligible (npc={_deal_npc}, dprg_rel={_dprg_rel})")

    gs.options_override.append(counter)

    # Session 7A Feature 10: Queue GM consequence for EOT application (all NPCs)
    npc_id = (counter.get("npc") or "").lower()
    if hasattr(gs, '_latest_gm_consequence') and gs._latest_gm_consequence:
        if not hasattr(gs, 'pending_gm_consequences'):
            gs.pending_gm_consequences = []
        gs.pending_gm_consequences.append({
            'consequence': gs._latest_gm_consequence,
            'npc': npc_id,
            'turn_accepted': gs.current_turn,
        })
        print(f"[GM] Consequence queued for EOT: {gs._latest_gm_consequence.get('proposal_summary', 'unknown')}")
        gs._latest_gm_consequence = None  # clear after queueing

    # Session 3: Mark the most recent negotiation_log entry for this NPC as accepted
    if hasattr(gs, 'negotiation_log') and npc_id:
        for entry in reversed(gs.negotiation_log):
            if entry.get("npc") == npc_id and entry.get("turn") == gs.current_turn:
                entry["outcome"] = "accepted"
                break

    # 10B-3: Track deal in deals_today + generate GM consequences
    if npc_id:
        import uuid as _uuid
        _deal_text = counter.get('text', 'Diplomatic agreement')
        _npc_name = ALL_NPC_NAMES.get(npc_id, npc_id.title())
        _is_covert = counter.get('covert', False)

        # Generate GM consequences for the deal
        _gm_consequences = None
        try:
            from npc_engine import generate_deal_consequences
            _gm_consequences = generate_deal_consequences(gs, npc_id, _deal_text, _is_covert)
            print(f"  [10B-3] GM consequences generated for {npc_id} deal")
        except Exception as _gm_err:
            print(f"[GM_DEAL_ERROR] generate_deal_consequences "
                  f"threw: {type(_gm_err).__name__}: {_gm_err}")
            print(f"  [10B-3] GM consequence generation failed: {_gm_err}")
            _gm_consequences = {
                'relations_delta': {npc_id: 3},
                'budget_delta': 0,
                'personal_wealth_delta': 0,
                'stability_delta': 0,
                'cross_npc_visibility': [],
                'historian_note': f'A diplomatic agreement was reached with {_npc_name}.',
                'briefing_summary': f'Agreement with {_npc_name}: {_deal_text[:80]}',
            }

        # Apply consequences from GM
        _rel_delta = 3  # default
        if _gm_consequences:
            for _cn, _cd in (_gm_consequences.get('relations_delta') or {}).items():
                if _cn in gs.relations and isinstance(_cd, (int, float)):
                    gs.update_relations(_cn, _cd)
            _bd = (_gm_consequences or {}).get('budget_delta', 0)
            _inst_amount = (_gm_consequences or {}).get('installment_amount')
            _inst_turns  = (_gm_consequences or {}).get('installment_turns')
            if _inst_amount and _inst_turns and int(_inst_turns) > 1:
                _inst_amount = float(_inst_amount)
                _inst_turns  = int(_inst_turns)
                for _i in range(_inst_turns):
                    gs.active_installments.append({
                        'amount': _inst_amount,
                        'turns_remaining': _inst_turns - _i,
                        'start_turn': gs.current_turn + _i + 1,
                        'registered_turn': gs.current_turn,
                        'description': (f"Deal payment — {_npc_name} "
                                        f"(turn {_i+1} of {_inst_turns})"),
                        'npc': npc_id,
                    })
                print(f"[INSTALLMENTS] registered {_inst_turns} payments "
                      f"of ${_inst_amount}B for {npc_id} deal")
            elif _bd and isinstance(_bd, (int, float)):
                gs.update_budget(_bd)
                print(f"[INSTALLMENTS] lump sum ${_bd}B applied for {npc_id}")
            _pwd = _gm_consequences.get('personal_wealth_delta', 0)
            if _pwd and isinstance(_pwd, (int, float)):
                gs.personal_wealth += _pwd
            _sd = _gm_consequences.get('stability_delta', 0)
            if _sd and isinstance(_sd, (int, float)):
                gs.legitimacy_stability += _sd
            _rel_delta = (_gm_consequences.get('relations_delta') or {}).get(npc_id, 3)

        # Generate advisor reactions to this deal
        _advisor_reactions = []
        try:
            from npc_engine import generate_advisor_deal_reactions
            _advisor_reactions = generate_advisor_deal_reactions(gs, _deal_text, npc_id)
        except Exception as _adv_err:
            print(f"  [10B-3] Advisor reactions failed: {_adv_err}")

        if not hasattr(gs, 'deals_today'):
            gs.deals_today = []
        gs.deals_today.append({
            'id': f"deal_{gs.current_turn}_{npc_id}_{_uuid.uuid4().hex[:6]}",
            'npc_id': npc_id,
            'npc_name': _npc_name,
            'deal_text': _deal_text,
            'briefing_summary': (_gm_consequences or {}).get('briefing_summary', f"Agreement with {_npc_name}: {_deal_text[:80]}"),
            'source': 'sidebar',
            'day': gs.current_turn,
            'is_backchannel': _is_covert,
            'relation_delta': _rel_delta,
            'gm_consequences': _gm_consequences,
            'advisor_reactions': _advisor_reactions,
        })
        # TODO: modify gate by soft_power_score
        print(f"  [10B-3] Deal tracked: {_npc_name} — {_deal_text[:60]}, relations delta: {_rel_delta}")
        print(f"[INSTALLMENTS] deal archived: npc={npc_id} "
              f"active_installments_count="
              f"{len(getattr(gs, 'active_installments', []))}")

    # Reload-and-patch: only update fields accept_counter owns,
    # preserving events_resolved_today and other briefing state
    gs_fresh = _load_gs(session_id)
    gs_fresh.options_override = gs.options_override
    gs_fresh.relations = gs.relations
    gs_fresh.budget = gs.budget
    gs_fresh.personal_wealth = gs.personal_wealth
    gs_fresh.legitimacy_stability = gs.legitimacy_stability
    gs_fresh.detection_heat = gs.detection_heat
    gs_fresh.deals_today = gs.deals_today
    gs_fresh.negotiation_log = gs.negotiation_log
    if hasattr(gs, 'pending_gm_consequences'):
        gs_fresh.pending_gm_consequences = gs.pending_gm_consequences
    if hasattr(gs, '_latest_gm_consequence'):
        gs_fresh._latest_gm_consequence = gs._latest_gm_consequence
    if hasattr(gs, 'intel_activated_this_turn'):
        gs_fresh.intel_activated_this_turn = gs.intel_activated_this_turn
    _save_gs(session_id, gs_fresh)
    return {"status": "ok", "letter": letter, "covert": counter.get('covert', False)}


# ── Session 4B: Election ─────────────────────────────────────────────────────

@app.post("/game/{session_id}/election")
def post_election(session_id: str, body: ElectionRequest):
    """
    Process election choice. Fires once at election_turn (default turn 4).
    Body: { choice: 'fair' | 'rigged' | 'canceled' | 'observers' | 'accept_defeat' }
    8C: 'accept_defeat' triggers voluntary exile (voted_out path).
    Returns: { result_key, consequences, npc_reactions, game_state }
    """
    gs = _load_gs(session_id)

    # Guard: Constitutional Revision abolishes elections (Political L9)
    if getattr(gs, 'constitutional_revision_active', False):
        raise HTTPException(status_code=400, detail="Elections abolished by constitutional revision")

    # Guard: election can only fire once
    if getattr(gs, 'election_fired', False):
        raise HTTPException(status_code=400, detail="Election already fired this game")

    # Guard: must be on election turn
    election_turn = getattr(gs, 'election_turn', 4)
    if gs.current_turn != election_turn:
        raise HTTPException(
            status_code=400,
            detail=f"Election fires on turn {election_turn}, currently turn {gs.current_turn}"
        )

    choice = (body.choice or "").lower().strip()
    valid_choices = ('fair', 'rigged', 'canceled', 'observers')
    if choice not in valid_choices:
        raise HTTPException(status_code=400, detail=f"Invalid election choice '{choice}'. Must be one of: {valid_choices}")

    # fixes_13 Fix 5: Democracy lock enforcement — block rigging/cancellation while observers active
    _democracy_locked = getattr(gs, 'regime_democracy_locked', 0)
    if _democracy_locked > 0 and choice in ('rigged', 'canceled'):
        print(f"  [api] DEMOCRACY LOCK BLOCKED: choice={choice}, lock={_democracy_locked} turns remaining")
        raise HTTPException(
            status_code=400,
            detail=f"International observers are present — this action is not possible this turn ({_democracy_locked} turn(s) remaining)"
        )

    # Observers gate: approval 60+ and no brigade deployments in action_history
    if choice == 'observers':
        if gs.public_approval < 60:
            raise HTTPException(
                status_code=400,
                detail=f"Observers require approval 60+, currently {gs.public_approval}%"
            )
        has_suppression = any(
            a.get('type') == 'deploy_brigades'
            for a in getattr(gs, 'action_history', [])
        )
        if has_suppression:
            raise HTTPException(
                status_code=400,
                detail="Observers unavailable: suppression actions (brigade deployments) detected in history"
            )

    # 8C: Accept defeat — voluntary exile path
    if choice == 'accept_defeat':
        # Guard: only available if approval < 55 (would lose) and no brigade suppression
        if gs.public_approval >= 55:
            raise HTTPException(status_code=400, detail="You would win this election — no need to concede")
        has_suppression = any(
            a.get('type') == 'deploy_brigades'
            for a in getattr(gs, 'action_history', [])
        )
        if has_suppression:
            raise HTTPException(status_code=400, detail="Cannot accept defeat while brigades are deployed")

        result_key = 'voted_out'
        gs.election_fired = True
        gs.election_result = result_key
        gs.action_history.append({
            'type': 'election',
            'choice': 'accept_defeat',
            'result_key': result_key,
            'turn': gs.current_turn,
        })

        # Trigger exile
        exile_sequence_start(gs, 'voted_out')
        print(f"  [api] ELECTION: accept_defeat -> voted_out exile. approval={gs.public_approval}%")

        _save_gs(session_id, gs)
        return {
            "result_key": result_key,
            "consequences": ["You accepted the electoral result. The transfer of power is peaceful."],
            "npc_reactions": {
                'usa': "A peaceful transfer. Washington notes this with approval.",
                'eu': "Marsha nods slowly. Not everyone does this.",
                'arabia': "Sadam watches the ceremony. Interesting.",
                'dprg': "Ji-won files this under 'unexpected outcomes.'",
                'russia': "Volkov watches from Moscow. Dignified, at least.",
                'china': "Wei observes. One chapter closes.",
            },
            "exile_triggered": True,
            "game_state": gs.serialize(),
        }

    # Determine result_key
    if choice == 'fair':
        if gs.public_approval >= 60:
            result_key = 'fair_success'
        elif gs.public_approval >= 40:
            result_key = 'fair_squeaker'
        else:
            result_key = 'fair_fail'
    elif choice == 'rigged':
        result_key = 'rigged'
    elif choice == 'canceled':
        result_key = 'canceled'
    else:  # observers
        result_key = 'observers'

    print(f"  [api] ELECTION: choice={choice}, approval={gs.public_approval}%, result_key={result_key}")

    # Apply hard-coded consequences
    changes = apply_election_consequences(gs, result_key)

    # Mark election as fired
    gs.election_fired = True
    gs.election_result = result_key

    # Record in action_history
    gs.action_history.append({
        'type': 'election',
        'choice': choice,
        'result_key': result_key,
        'turn': gs.current_turn,
    })

    # Generate NPC reactions (Claude call)
    npc_reactions = {}
    try:
        npc_reactions = npc_engine.generate_election_reactions(gs, result_key)
        print(f"  [api] ELECTION NPC REACTIONS: {list(npc_reactions.keys())}")
    except Exception as e:
        print(f"  [api] ELECTION NPC REACTIONS FAILED: {e}")
        npc_reactions = {
            'usa': "The State Department is reviewing the situation.",
            'arabia': "Riyadh watches with interest.",
            'eu': "Brussels has taken note of the developments.",
            'dprg': "Pyongyang observes from a distance.",
        }

    # Session 5 Phase C Hook 4: store_memory on election outcome
    try:
        from memory_engine import store_memory
        _player_id = getattr(gs, 'player_id', None)
        if _player_id:
            for _npc_k in ALL_NPCS:
                store_memory(
                    player_id=_player_id, npc=_npc_k, era=0,
                    turn=gs.current_turn, event_type='election_outcome',
                    description=f"Election held: choice={choice}, result={result_key}. Approval={gs.public_approval}%"
                )
    except Exception as e:
        print(f"  [api] Memory hook (election_outcome) failed: {e}")

    _save_gs(session_id, gs)

    return {
        "result_key": result_key,
        "consequences": changes,
        "npc_reactions": npc_reactions,
        "game_state": gs.serialize(),
    }


# ── Session 4C: Domestic Action ──────────────────────────────────────────────

@app.post("/game/{session_id}/domestic_action")
def post_domestic_action(session_id: str, body: DomesticActionRequest):
    """
    Purchase a one-time domestic action from Shadow Cabinet.
    Body: { action: 'state_media_takeover' | 'judicial_capture' | ... }
    Returns: { success, action, changes, game_state }
    """
    gs = _load_gs(session_id)

    action_key = (body.action or "").lower().strip()
    if action_key not in DOMESTIC_ACTION_CONSEQUENCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domestic action '{action_key}'. Valid: {list(DOMESTIC_ACTION_CONSEQUENCES.keys())}"
        )

    print(f"  [api] DOMESTIC ACTION: {action_key}, pw=${gs.personal_wealth:.1f}B")

    success, changes = apply_domestic_action(gs, action_key)

    if not success:
        # Return failure info without saving (no state mutation on failure)
        return {
            "success": False,
            "action": action_key,
            "changes": changes,
            "game_state": gs.serialize(),
        }

    # Session 5 Phase C Hook 3: store_memory on domestic action enacted
    try:
        from memory_engine import store_memory
        _player_id = getattr(gs, 'player_id', None)
        if _player_id:
            store_memory(
                player_id=_player_id, npc='eu', era=0,
                turn=gs.current_turn, event_type='domestic_action',
                description=f"Enacted domestic action: {action_key}. {'; '.join(changes[:2])}"
            )
    except Exception as e:
        print(f"  [api] Memory hook (domestic_action) failed: {e}")

    _save_gs(session_id, gs)

    return {
        "success": True,
        "action": action_key,
        "changes": changes,
        "game_state": gs.serialize(),
    }


# ── Session 4D: Intelligence Budget Allocation ──────────────────────────────

@app.post("/game/{session_id}/intel_allocation")
async def post_intel_allocation(session_id: str, body: IntelAllocationRequest, user: User = Depends(get_optional_user)):
    """
    Allocate intelligence budget for the turn. Deducts from national budget.
    Body: { allocation: 'none' | 'maintenance' | 'active' | 'expansion' }
    Returns: { success, allocation, changes, game_state }
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    allocation = (body.allocation or "").lower().strip()
    if allocation not in INTEL_BUDGET_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid allocation '{allocation}'. Valid: {list(INTEL_BUDGET_OPTIONS.keys())}"
        )

    print(f"  [api] INTEL ALLOCATION: {allocation}, budget=${gs.budget:.1f}B")

    success, changes = process_intel_budget(gs, allocation)

    if not success:
        return {
            "success": False,
            "allocation": allocation,
            "changes": changes,
            "game_state": gs.serialize(),
        }

    _save_gs(session_id, gs)

    return {
        "success": True,
        "allocation": allocation,
        "changes": changes,
        "game_state": gs.serialize(),
    }


# ── Domestic Affairs: Budget Allocation ──────────────────────────────────────

@app.post("/game/{session_id}/budget_allocation")
async def post_budget_allocation(session_id: str, body: BudgetAllocationRequest, user: User = Depends(get_optional_user)):
    """
    Set persistent budget allocation across five categories.
    Body: { military, intelligence, public_services, infrastructure, diplomacy }
    All values >= 0, sum must == 100.
    Returns: { success, allocation, game_state }
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    vals = {
        "military": body.military,
        "intelligence": body.intelligence,
        "public_services": body.public_services,
        "infrastructure": body.infrastructure,
        "diplomacy": body.diplomacy,
    }

    # Validate: all >= 0
    for k, v in vals.items():
        if v < 0:
            raise HTTPException(status_code=400, detail=f"'{k}' must be >= 0, got {v}")

    # Validate: sum == 100
    total = sum(vals.values())
    if total != 100:
        raise HTTPException(status_code=400, detail=f"Allocation must sum to 100, got {total}")

    gs.budget_allocation = vals
    print(f"  [BUDGET] Allocation updated: mil={vals['military']}%, intel={vals['intelligence']}%, services={vals['public_services']}%, infra={vals['infrastructure']}%, diplo={vals['diplomacy']}%")

    _save_gs(session_id, gs)

    return {
        "success": True,
        "allocation": vals,
        "game_state": gs.serialize(),
    }


# ── 8B: Education allocation endpoint ────────────────────────────────────

@app.post("/game/{session_id}/education_allocation")
async def post_education_allocation(session_id: str, body: EducationAllocationRequest, user: User = Depends(get_optional_user)):
    """
    8B: Set education spending allocation ($B per turn).
    Body: { allocation: float }
    The value is clamped to [0, 15] and deducted from the national budget each EOT.
    Returns: { success, allocation, game_state }
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    val = round(max(0.0, min(15.0, body.allocation)), 1)
    gs.education_allocation = val
    print(f"  [education] Allocation set to ${val:.1f}B/turn")

    _save_gs(session_id, gs)

    return {
        "success": True,
        "allocation": val,
        "game_state": gs.serialize(),
    }


# ── fixes_10 Fix 7: Debug panel endpoint ────────────────────────────────────

@app.post("/game/{session_id}/debug/set_state")
def debug_set_state(session_id: str, body: DebugSetStateRequest):
    """
    fixes_10 Fix 7: Dev tool — directly override game state values for testing.
    Accepts { overrides: { field: value, ... } }.
    Supports: usa/arabia/eu/dprg (relations), budget, personal_wealth,
    stability, public_approval, detection_heat, military_strength, tech_level.
    """
    gs = _load_gs(session_id)
    applied = {}

    for field, value in body.overrides.items():
        # Handle relation overrides — accept both 'usa' and 'usa_relations'
        _npc_key = field.replace('_relations', '') if field.endswith('_relations') else field
        if _npc_key in ALL_NPCS and _npc_key in gs.relations:
            gs.relations[_npc_key] = max(0, min(100, float(value)))
            applied[field] = gs.relations[_npc_key]
        elif field == 'budget':
            gs.budget = round(float(value), 1)
            applied[field] = gs.budget
        elif field == 'personal_wealth':
            gs.personal_wealth = round(max(0, float(value)), 1)
            applied[field] = gs.personal_wealth
        elif field == 'stability':
            gs.stability = max(0, min(100, float(value)))
            applied[field] = gs.stability
        elif field == 'public_approval':
            gs.public_approval = max(0, min(100, float(value)))
            applied[field] = gs.public_approval
        elif field == 'detection_heat':
            gs.detection_heat = max(0, min(100, float(value)))
            applied[field] = gs.detection_heat
        elif field == 'military_strength':
            gs.military_strength = max(0, min(100, int(value)))
            applied[field] = gs.military_strength
        elif field == 'tech_level':
            gs.tech_level = max(0, float(value))  # no upper cap — Tier 5 is 100+
            applied[field] = gs.tech_level
        # 9.5A: Explicit type-safe handlers for exile/ending fields
        elif field == 'restoration_active':
            gs.restoration_active = bool(value)
            applied[field] = gs.restoration_active
            print(f"  [DEBUG] set_state applied field={field} value={gs.restoration_active}")
        elif field == 'restoration_grace_days':
            gs.restoration_grace_days = int(value)
            applied[field] = gs.restoration_grace_days
            print(f"  [DEBUG] set_state applied field={field} value={gs.restoration_grace_days}")
        elif field == 'exile_day':
            gs.exile_day = int(value)
            applied[field] = gs.exile_day
            print(f"  [DEBUG] set_state applied field={field} value={gs.exile_day}")
        elif field == 'return_attempts':
            gs.return_attempts = int(value)
            applied[field] = gs.return_attempts
            print(f"  [DEBUG] set_state applied field={field} value={gs.return_attempts}")
        elif field == 'return_progress':
            gs.return_progress = float(value)
            applied[field] = gs.return_progress
            print(f"  [DEBUG] set_state applied field={field} value={gs.return_progress}")
        elif field == 'exile_trigger':
            gs.exile_trigger = str(value)
            applied[field] = gs.exile_trigger
            print(f"  [DEBUG] set_state applied field={field} value={gs.exile_trigger}")
        elif field == 'departure_heat':
            gs.departure_heat = int(value)
            applied[field] = gs.departure_heat
            print(f"  [DEBUG] set_state applied field={field} value={gs.departure_heat}")
        elif field == 'prior_regime_label':
            gs.prior_regime_label = str(value)
            applied[field] = gs.prior_regime_label
            print(f"  [DEBUG] set_state applied field={field} value={gs.prior_regime_label}")
        elif field == 'constitutional_revision_active':
            gs.constitutional_revision_active = bool(value)
            applied[field] = gs.constitutional_revision_active
            print(f"  [DEBUG] set_state applied field={field} value={gs.constitutional_revision_active}")
        elif field == 'action_press_suppressed':
            gs.action_press_suppressed = bool(value)
            applied[field] = gs.action_press_suppressed
            print(f"  [DEBUG] set_state applied field={field} value={gs.action_press_suppressed}")
        elif field == 'action_judiciary_captured':
            gs.action_judiciary_captured = bool(value)
            applied[field] = gs.action_judiciary_captured
            print(f"  [DEBUG] set_state applied field={field} value={gs.action_judiciary_captured}")
        elif hasattr(gs, field):
            setattr(gs, field, value)
            applied[field] = value

    # Fix B: When in_exile is toggled ON via DEV panel, auto-populate exile fields
    if applied.get('in_exile') and gs.in_exile:
        from turn_processor import _calculate_exile_destination, SUCCESSOR_NAMES, APPARATUS_SURVIVAL
        if not gs.exile_destination:
            gs.exile_destination = _calculate_exile_destination(gs)
            applied['exile_destination'] = gs.exile_destination
        if not gs.exile_trigger:
            gs.exile_trigger = 'coup'
            applied['exile_trigger'] = gs.exile_trigger
        if not gs.successor_name:
            gs.successor_disposition = gs._determine_successor()
            gs.successor_name = SUCCESSOR_NAMES[gs.successor_disposition]
            applied['successor_name'] = gs.successor_name
        if not gs.exile_apparatus_survived:
            survival = APPARATUS_SURVIVAL.get(gs.exile_trigger, APPARATUS_SURVIVAL['coup'])
            gs.exile_apparatus_survived = survival['survived']
            gs.exile_apparatus_detection_risk_modifier = survival['risk_modifier']
            applied['exile_apparatus_survived'] = gs.exile_apparatus_survived
        if not gs.exile_wealth_at_collapse:
            gs.exile_wealth_at_collapse = gs.personal_wealth
        print(f"  [api] DEBUG: Auto-populated exile fields for DEV panel toggle")

    print(f"  [api] DEBUG SET STATE: applied={applied}")
    _save_gs(session_id, gs)

    return {
        "status": "ok",
        "applied": applied,
        "game_state": gs.serialize(),
    }


# ── Session 5: Cabinet Axis Invest/Defund ────────────────────────────────────

@app.post("/game/{session_id}/cabinet_invest")
def cabinet_invest(session_id: str, body: CabinetInvestRequest):
    """Invest or defund a Shadow Cabinet axis by one level."""
    from game_state import AXIS_COST_PER_LEVEL, AXIS_PERMANENT_FLOORS
    gs = _load_gs(session_id)

    axis = body.axis
    direction = body.direction
    axes = getattr(gs, 'cabinet_axes', {})

    if axis not in axes:
        raise HTTPException(status_code=400, detail=f"Invalid axis '{axis}'")

    current_level = axes[axis]

    if direction == 'invest':
        if current_level >= 10:
            raise HTTPException(status_code=400, detail=f"{axis} already at max level 10")
        costs = AXIS_COST_PER_LEVEL.get(axis, [1]*10)
        cost = costs[current_level] if current_level < len(costs) else 5
        # Session 6: Budget source split
        # National budget: Military (all levels), Resource Dev (all levels), Intelligence 1-3
        # Personal wealth: Intelligence 4+, Media, Judicial, Political, Extraction
        _use_national = (axis in ('military', 'resource_dev')) or (axis == 'intelligence' and current_level < 3)
        if _use_national:
            if gs.budget < cost:
                raise HTTPException(status_code=400,
                                    detail=f"Need ${cost}B national budget (have ${gs.budget:.1f}B)")
            gs.update_budget(-cost)
            _budget_label = "national"
        else:
            if gs.personal_wealth < cost:
                raise HTTPException(status_code=400,
                                    detail=f"Need ${cost}B personal wealth (have ${gs.personal_wealth:.1f}B). Requires personal funds — skim national budget first to build personal wealth.")
            gs.update_personal_wealth(-cost, source=f"cabinet invest {axis}")
            _budget_label = "personal"
        axes[axis] = current_level + 1
        _new_level = current_level + 1
        gs.cabinet_axes = axes
        msg = f"Invested in {axis}: level {current_level} -> {_new_level} (cost: ${cost}B {_budget_label})"
        # Session 6: Console log for new axes
        if axis in ('military', 'intelligence', 'resource_dev'):
            print(f"  [SESSION-6] {axis.upper()} level {current_level} -> {_new_level}, budget source: {_budget_label}")

        # fixes_16 Fix C: Extraction milestones
        _milestone_msgs = []
        if axis == 'extraction':
            # L5: +$7B personal injection (one-time)
            if _new_level >= 5 and not getattr(gs, 'extraction_l5_fired', False):
                gs.extraction_l5_fired = True
                gs.update_personal_wealth(7.0, source="Extraction L5 milestone — shell network matures")
                _milestone_msgs.append('💰 Extraction L5: Shell network matures — +$7B personal injection')
                print(f"  [api] FIX C: Extraction L5 milestone FIRED — +$7B personal (now ${gs.personal_wealth:.1f}B)")
            # L7: skim ceiling removed (one-time)
            if _new_level >= 7 and not getattr(gs, 'extraction_l7_fired', False):
                gs.extraction_l7_fired = True
                _milestone_msgs.append('💰 Extraction L7: Offshore architecture complete — skim ceiling removed')
                print(f"  [api] FIX C: Extraction L7 milestone FIRED — skim ceiling removed")

        # Session 6 Phase 8: Judicial axis L3 generates +10 heat
        if axis == 'judicial' and _new_level == 3:
            _old_heat = gs.detection_heat
            gs.detection_heat = min(100, gs.detection_heat + 10)
            _milestone_msgs.append(f'🔥 Judicial L3: Judicial capture detected — +10 heat ({_old_heat}% -> {gs.detection_heat}%)')
            print(f"  [HEAT] Judicial axis reached L3: +10 heat ({_old_heat} -> {gs.detection_heat})")

        # Session 6: Resource Development milestones
        if axis == 'resource_dev':
            # L5: GDP Credibility — NPC negotiation ceilings +20% permanently
            if _new_level >= 5 and not getattr(gs, 'gdp_credibility_active', False):
                gs.gdp_credibility_active = True
                _milestone_msgs.append('🏗️ Resource Dev L5: GDP Credibility — NPC negotiation ceilings +20% permanently')
                print(f"  [RESOURCE_DEV] GDP Credibility milestone FIRED")
            # L9: Resource Independence — oil imports eliminated permanently
            if _new_level >= 9 and not getattr(gs, 'resource_independence_active', False):
                gs.resource_independence_active = True
                gs.update_relations('eu', 5)
                _milestone_msgs.append('🏗️ Resource Dev L9: Resource Independence — oil imports eliminated, EU +5')
                print(f"  [RESOURCE_DEV] Resource Independence milestone FIRED — oil imports eliminated")

    elif direction == 'defund':
        floor = AXIS_PERMANENT_FLOORS.get(axis, 1)
        if current_level <= 0:
            raise HTTPException(status_code=400, detail=f"{axis} already at 0")
        new_level = max(floor, current_level - 1) if current_level > floor else current_level
        if new_level == current_level:
            raise HTTPException(status_code=400,
                                detail=f"{axis} cannot go below permanent floor ({floor})")
        axes[axis] = new_level
        gs.cabinet_axes = axes
        msg = f"Defunded {axis}: level {current_level} -> {new_level}"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid direction '{direction}'")

    # Session 6: Invalidate advisor pool so it regenerates with updated axis gates
    # (e.g. Spy Chief appears when Intelligence reaches 4)
    gs.advisor_pool = []

    print(f"  [api] CABINET INVEST: {msg}")
    _save_gs(session_id, gs)

    _result = {
        "success": True,
        "message": msg,
        "cabinet_axes": axes,
        "game_state": gs.serialize(),
    }
    # fixes_16 Fix C: Include milestone messages in response
    if _milestone_msgs:
        _result["milestone_messages"] = _milestone_msgs
    return _result


# ── Session 6: Military Axis Actions ────────────────────────────────────────

@app.post("/game/{session_id}/military_action")
def military_action(session_id: str, body: MilitaryActionRequest):
    """
    Session 6: Military axis action suites.
    L3: Defense Procurement — $3B national, +5 military strength
    L9: Force Projection — free, +25% NPC ceiling, target NPC -8 relations, 3-turn cooldown
    L10: Arms Export — +$4B national, +8 relations with buyer, -5 military, once per turn
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    mil_level = axes.get('military', 0)
    action = body.action
    messages = []

    if action == 'defense_procurement':
        # L3: Defense Procurement — buy weapons, +5 military
        if mil_level < 3:
            raise HTTPException(status_code=400, detail="Military axis must be >= 3 for Defense Procurement")
        # fixes_17 Fix B: Once per turn
        if getattr(gs, 'defense_procurement_turn', -1) == gs.current_turn:
            print(f"  [MILITARY] Defense Procurement: blocked — already used this turn")
            raise HTTPException(status_code=400, detail="Defense Procurement already used this turn")
        # fixes_17 Fix C: Cannot combine with Arms Export same turn
        if getattr(gs, 'arms_export_this_turn', None):
            raise HTTPException(status_code=400, detail="Cannot combine Defense Procurement with Arms Export this turn")
        cost = 3.0
        if gs.budget < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B national budget (have ${gs.budget:.1f}B)")
        gs.update_budget(-cost)
        gs.military_strength = min(100, getattr(gs, 'military_strength', 20) + 5)
        gs.defense_procurement_count = getattr(gs, 'defense_procurement_count', 0) + 1
        gs.defense_procurement_turn = gs.current_turn  # fixes_17 Fix B: track per-turn usage
        messages.append(f"⚔️ Defense Procurement: +5 military strength (now {gs.military_strength}), -${cost}B national")
        print(f"  [MILITARY] Defense Procurement: military={gs.military_strength}, cost=${cost}B, total purchases={gs.defense_procurement_count}")

    elif action == 'force_projection':
        # L9: Force Projection — threaten NPC, +25% ceiling, -8 relations (temporary)
        if mil_level < 9:
            raise HTTPException(status_code=400, detail="Military axis must be >= 9 for Force Projection")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}' for Force Projection")
        cooldown = getattr(gs, 'force_projection_cooldown', 0)
        if cooldown > 0:
            raise HTTPException(status_code=400, detail=f"Force Projection on cooldown ({cooldown} turns remaining)")
        # Apply effects
        gs.force_projection_target = target
        gs.force_projection_cooldown = 3  # 3-turn cooldown
        gs.update_relations(target, -8)
        messages.append(f"⚔️ Force Projection vs {target.upper()}: NPC negotiation ceilings +25%, {target.upper()} -8 relations, 3-turn cooldown")
        print(f"  [MILITARY] Force Projection: target={target}, relations now={gs.relations.get(target, 0)}, cooldown=3")

    elif action == 'arms_export':
        # L10: Arms Export — sell weapons to ally, +$4B, +8 relations, -5 military
        if mil_level < 10:
            raise HTTPException(status_code=400, detail="Military axis must be 10 for Arms Export")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}' for Arms Export")
        if getattr(gs, 'arms_export_this_turn', None):
            raise HTTPException(status_code=400, detail="Arms Export already used this turn")
        # fixes_17 Fix C: Cannot combine with Defense Procurement same turn
        if getattr(gs, 'defense_procurement_turn', -1) == gs.current_turn:
            raise HTTPException(status_code=400, detail="Cannot combine Arms Export with Defense Procurement this turn")
        mil_str = getattr(gs, 'military_strength', 20)
        if mil_str < 5:
            raise HTTPException(status_code=400, detail=f"Need at least 5 military strength to export (have {mil_str})")
        # Apply effects
        gs.update_budget(4.0)
        gs.update_relations(target, 8)
        gs.military_strength = max(0, mil_str - 5)
        gs.arms_export_this_turn = target
        messages.append(f"⚔️ Arms Export to {target.upper()}: +$4B national, +8 relations, -5 military (now {gs.military_strength})")
        print(f"  [MILITARY] Arms Export: target={target}, +$4B, relations now={gs.relations.get(target, 0)}, military={gs.military_strength}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid military action '{action}'")

    _save_gs(session_id, gs)
    return {
        "success": True,
        "messages": messages,
        "game_state": gs.serialize(),
    }


# ── Session 6: Intelligence axis actions ───────────────────────────────────

@app.post("/game/{session_id}/intelligence_action")
def intelligence_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Intelligence axis action suites.
    L5: Intelligence Sharing — free, +12 relations, +1 intel tier, once per game
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    intel_level = axes.get('intelligence', 0)
    action = body.action
    messages = []

    if action == 'intel_sharing':
        if intel_level < 5:
            raise HTTPException(status_code=400, detail="Intelligence axis must be >= 5 for Intelligence Sharing")
        if getattr(gs, 'intel_sharing_target', None):
            raise HTTPException(status_code=400, detail=f"Intelligence Sharing already used this game (shared with {gs.intel_sharing_target.upper()})")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}'")
        gs.intel_sharing_target = target
        gs.update_relations(target, 12)
        _tiers = getattr(gs, 'npc_intel_tiers', {})
        _tiers[target] = min(3, _tiers.get(target, 0) + 1)
        gs.npc_intel_tiers = _tiers
        messages.append(f"🕵️ Intelligence Sharing with {target.upper()}: +12 relations, intel tier upgraded to {_tiers[target]}")
        print(f"  [INTELLIGENCE] Intel Sharing: target={target}, relations={gs.relations.get(target, 0)}, intel_tier={_tiers[target]}")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid intelligence action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: Media axis actions ──────────────────────────────────────────

@app.post("/game/{session_id}/media_action")
def media_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Media axis action suites.
    L3: Suppress a Scandal — $1B personal, kill incoming corruption scandal
    L6: Narrative Campaign — $2B personal, +8% approval, one NPC credibility hit (-5)
    L9: Information Blackout — $4B personal, world events muted 2 turns
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    media_level = axes.get('media', 0)
    action = body.action
    messages = []

    if action == 'suppress_scandal':
        if media_level < 3:
            raise HTTPException(status_code=400, detail="Media axis must be >= 3")
        if getattr(gs, 'scandal_suppressed_this_turn', False):
            raise HTTPException(status_code=400, detail="Scandal already suppressed this turn")
        cost = 1.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="suppress scandal")
        gs.scandal_suppressed_this_turn = True
        messages.append(f"📺 Scandal Suppressed: immunity from next corruption scandal this turn (-${cost}B personal)")
        print(f"  [MEDIA] Suppress Scandal: cost=${cost}B, personal_wealth=${gs.personal_wealth:.1f}B")

    elif action == 'narrative_campaign':
        if media_level < 6:
            raise HTTPException(status_code=400, detail="Media axis must be >= 6")
        cost = 2.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}'")
        gs.update_personal_wealth(-cost, source="narrative campaign")
        gs.update_approval(8)
        # Credibility hit: target NPC loses 5 relations with one random other NPC
        _other_npcs = [n for n in ALL_NPCS if n != target]
        import random as _rng
        _victim = _rng.choice(_other_npcs)
        gs.update_relations(target, -5)
        messages.append(f"📺 Narrative Campaign: +8% approval, {target.upper()} -5 relations (-${cost}B personal)")
        print(f"  [MEDIA] Narrative Campaign: +8% approval, {target.upper()} -5, cost=${cost}B")

    elif action == 'info_blackout':
        if media_level < 9:
            raise HTTPException(status_code=400, detail="Media axis must be >= 9")
        cost = 4.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="information blackout")
        gs.info_blackout_turns = 2
        messages.append(f"📺 Information Blackout: world events affecting approval/stability muted for 2 turns (-${cost}B personal)")
        print(f"  [MEDIA] Information Blackout: 2 turns, cost=${cost}B")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid media action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: Judicial axis actions ───────────────────────────────────────

@app.post("/game/{session_id}/judicial_action")
def judicial_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Judicial axis action suites.
    L3: Drop Investigation — free, once per turn, immunity from next scandal
    L6: Lawfare — $3B personal, suspend one NPC pressure event 2 turns
    L9: Asset Seizure — $5B personal, +$3B national, stability +5%, approval -8%
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    jud_level = axes.get('judicial', 0)
    action = body.action
    messages = []

    if action == 'drop_investigation':
        if jud_level < 3:
            raise HTTPException(status_code=400, detail="Judicial axis must be >= 3")
        if getattr(gs, 'drop_investigation_this_turn', False):
            raise HTTPException(status_code=400, detail="Already dropped an investigation this turn")
        gs.drop_investigation_this_turn = True
        messages.append("⚖️ Investigation Dropped: immunity from next corruption scandal this turn (free)")
        print(f"  [JUDICIAL] Drop Investigation: activated for this turn")

    elif action == 'lawfare':
        if jud_level < 6:
            raise HTTPException(status_code=400, detail="Judicial axis must be >= 6")
        cost = 3.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}'")
        gs.update_personal_wealth(-cost, source="lawfare")
        gs.lawfare_target = target
        gs.lawfare_turns = 2
        # Also add to pressure_suspensions for existing system compatibility
        _suspensions = getattr(gs, 'pressure_suspensions', [])
        _suspensions.append({'npc': target, 'turns_remaining': 2, 'type': 'lawfare'})
        gs.pressure_suspensions = _suspensions
        messages.append(f"⚖️ Lawfare vs {target.upper()}: pressure events suspended 2 turns (-${cost}B personal)")
        print(f"  [JUDICIAL] Lawfare: target={target}, 2 turns, cost=${cost}B")

    elif action == 'asset_seizure':
        if jud_level < 9:
            raise HTTPException(status_code=400, detail="Judicial axis must be >= 9")
        cost = 5.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="asset seizure")
        gs.update_budget(3.0)
        gs.update_stability(5)
        gs.update_approval(-8)
        messages.append(f"⚖️ Asset Seizure: +$3B national, +5% stability, -8% approval (-${cost}B personal)")
        print(f"  [JUDICIAL] Asset Seizure: +$3B national, stability={gs.stability}, approval={gs.public_approval}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid judicial action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: Political axis actions ──────────────────────────────────────

@app.post("/game/{session_id}/political_action")
def political_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Political axis action suites.
    L3: Party Consolidation — $1B personal, tax approval drain -25% for 3 turns
    L6: Pack the Cabinet — $3B personal, 4th advisor slot permanently
    L9: Constitutional Revision — $6B personal, remove electoral mechanics, regime hard right, EU -15
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    pol_level = axes.get('political', 0)
    action = body.action
    messages = []

    if action == 'party_consolidation':
        if pol_level < 3:
            raise HTTPException(status_code=400, detail="Political axis must be >= 3")
        cost = 1.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="party consolidation")
        gs.party_consolidation_turns = 3
        messages.append(f"🏛️ Party Consolidation: tax approval drain reduced 25% for 3 turns (-${cost}B personal)")
        print(f"  [POLITICAL] Party Consolidation: 3 turns, cost=${cost}B")

    elif action == 'pack_cabinet':
        if pol_level < 6:
            raise HTTPException(status_code=400, detail="Political axis must be >= 6")
        if getattr(gs, 'fourth_advisor_slot', False):
            raise HTTPException(status_code=400, detail="4th advisor slot already unlocked")
        cost = 3.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="pack the cabinet")
        gs.fourth_advisor_slot = True
        messages.append(f"🏛️ Pack the Cabinet: 4th advisor slot permanently unlocked (-${cost}B personal)")
        print(f"  [POLITICAL] Pack the Cabinet: 4th advisor slot unlocked, cost=${cost}B")

    elif action == 'constitutional_revision':
        if pol_level < 9:
            raise HTTPException(status_code=400, detail="Political axis must be >= 9")
        if getattr(gs, 'constitutional_revision_active', False):
            raise HTTPException(status_code=400, detail="Constitutional Revision already enacted")
        cost = 6.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="constitutional revision")
        gs.constitutional_revision_active = True
        gs.update_relations('eu', -15)
        # Regime hard right: shift axes
        _axes = getattr(gs, 'cabinet_axes', {})
        _axes['military'] = min(10, _axes.get('military', 0) + 3)
        _axes['political'] = min(10, _axes.get('political', 0) + 3)
        _axes['media'] = min(10, _axes.get('media', 0) + 2)
        gs.cabinet_axes = _axes
        messages.append(f"🏛️ Constitutional Revision: electoral mechanics removed, regime shifts right, EU -15 (-${cost}B personal)")
        messages.append("⚠️ Reversible: Marsha (EU) may demand reversal as a deal condition")
        print(f"  [POLITICAL] Constitutional Revision: enacted, EU={gs.relations.get('eu', 0)}, cost=${cost}B")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid political action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: Extraction axis actions ─────────────────────────────────────

@app.post("/game/{session_id}/extraction_action")
def extraction_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Extraction axis action suites.
    L6: Offshore Transfer — move national -> personal, no skim heat, EU notices
    L7: Private Security Force — $5B personal one-time, 15 militia strength, coup immunity
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    ext_level = axes.get('extraction', 0)
    action = body.action
    messages = []

    if action == 'offshore_transfer':
        if ext_level < 6:
            raise HTTPException(status_code=400, detail="Extraction axis must be >= 6")
        if getattr(gs, 'offshore_transfer_this_turn', False):
            raise HTTPException(status_code=400, detail="Offshore Transfer already used this turn")
        amount = min(body.amount, 10.0)  # cap at $10B
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Transfer amount must be > 0")
        if gs.budget < amount:
            raise HTTPException(status_code=400, detail=f"Need ${amount:.1f}B national budget (have ${gs.budget:.1f}B)")
        gs.update_budget(-amount)
        gs.update_personal_wealth(amount, source="offshore transfer")
        gs.offshore_transfer_this_turn = True
        # EU intel notices (small relations hit)
        gs.update_relations('eu', -3)
        messages.append(f"💰 Offshore Transfer: ${amount:.1f}B national -> personal (no skim heat, EU notices: -3)")
        print(f"  [EXTRACTION] Offshore Transfer: ${amount:.1f}B, personal_wealth=${gs.personal_wealth:.1f}B, EU -3")

    elif action == 'private_security_force':
        if ext_level < 7:
            raise HTTPException(status_code=400, detail="Extraction axis must be >= 7")
        if getattr(gs, 'private_security_force', False):
            raise HTTPException(status_code=400, detail="Private Security Force already purchased")
        cost = 5.0
        if gs.personal_wealth < cost:
            raise HTTPException(status_code=400, detail=f"Need ${cost}B personal wealth")
        gs.update_personal_wealth(-cost, source="private security force")
        gs.private_security_force = True
        gs.private_security_strength = 15
        gs.coup_immune = True
        messages.append(f"💰 Private Security Force: 15 militia strength, no decay, coup immunity (-${cost}B personal)")
        messages.append("⚠️ If detected (heat 80+): Bill/Marsha demand disbandment, Ji-won approves")
        print(f"  [EXTRACTION] Private Security Force: purchased, strength=15, coup_immune=True")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid extraction action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: Resource Development axis actions ───────────────────────────

@app.post("/game/{session_id}/resource_dev_action")
def resource_dev_action(session_id: str, body: AxisActionRequest):
    """
    Session 6: Resource Development axis action suites.
    L3: Export Contract — one-time +$8B national
    L6: Sovereign Collateral Loan — $10B, 15% interest, once per game
    L8: Strategic Resource Partner — choose one NPC, their ceiling +50% permanently
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    rd_level = axes.get('resource_dev', 0)
    action = body.action
    messages = []

    if action == 'export_contract':
        if rd_level < 3:
            raise HTTPException(status_code=400, detail="Resource Dev axis must be >= 3")
        if getattr(gs, 'export_contract_used', False):
            raise HTTPException(status_code=400, detail="Export Contract already used")
        gs.export_contract_used = True
        gs.update_budget(8.0)
        messages.append("🏗️ Export Contract: +$8B national budget (one-time, no NPC penalties)")
        print(f"  [RESOURCE_DEV] Export Contract: +$8B, budget=${gs.budget:.1f}B")

    elif action == 'sovereign_collateral_loan':
        if rd_level < 6:
            raise HTTPException(status_code=400, detail="Resource Dev axis must be >= 6")
        if getattr(gs, 'sovereign_collateral_used', False):
            raise HTTPException(status_code=400, detail="Sovereign Collateral Loan already used this game")
        gs.sovereign_collateral_used = True
        gs.update_budget(10.0)
        # 15% interest = $11.5B repayment over ~3 turns = ~$3.83B/turn
        gs.sovereign_collateral_repayment = 3.83
        gs.sovereign_collateral_turns = 3
        messages.append("🏗️ Sovereign Collateral Loan: +$10B national, $3.83B/turn x 3 repayment (15% interest, zero NPC penalties)")
        print(f"  [RESOURCE_DEV] Sovereign Collateral Loan: +$10B, repayment=$3.83B/turn x 3")

    elif action == 'strategic_resource_partner':
        if rd_level < 8:
            raise HTTPException(status_code=400, detail="Resource Dev axis must be >= 8")
        if getattr(gs, 'strategic_resource_partner', None):
            raise HTTPException(status_code=400, detail=f"Already partnered with {gs.strategic_resource_partner.upper()}")
        target = body.target_npc.lower() if body.target_npc else ''
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target_npc '{target}'")
        gs.strategic_resource_partner = target
        gs.update_relations(target, 5)
        messages.append(f"🏗️ Strategic Resource Partner: {target.upper()} negotiation ceiling +50% permanently, +5 relations")
        print(f"  [RESOURCE_DEV] Strategic Resource Partner: {target}, relations={gs.relations.get(target, 0)}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid resource_dev action '{action}'")

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 6: NPC Conditional Leverage Demands ─────────────────────────────

@app.post("/game/{session_id}/leverage_response")
def leverage_response(session_id: str, body: LeverageResponseRequest):
    """
    Session 6: Player responds to a leverage demand (Accept / Decline).
    Marsha media: accept -> EU +20, media axis reset to 0, +$4B national
    Bill opposition: accept -> USA +10, political axis -2
    """
    gs = _load_gs(session_id)
    leverage_type = body.leverage_type
    accept = body.accept
    messages = []

    if leverage_type == 'marsha_media':
        if not getattr(gs, 'leverage_marsha_media_fired', False):
            raise HTTPException(status_code=400, detail="Marsha media leverage demand not active")
        if accept:
            gs.update_relations('eu', 20)
            _axes = getattr(gs, 'cabinet_axes', {})
            _old_media = _axes.get('media', 0)
            _axes['media'] = 0
            gs.cabinet_axes = _axes
            gs.update_budget(4.0)
            messages.append(f"🇪🇺 Marsha accepts your reform: EU +20, Media Control reset ({_old_media} -> 0), +$4B national")
            print(f"  [LEVERAGE] Marsha media ACCEPTED: EU={gs.relations.get('eu', 0)}, media 0, +$4B")
        else:
            messages.append("🇪🇺 You declined Marsha's demand. The offer expires.")
            print(f"  [LEVERAGE] Marsha media DECLINED")

    elif leverage_type == 'bill_opposition':
        if not getattr(gs, 'leverage_bill_opposition_fired', False):
            raise HTTPException(status_code=400, detail="Bill opposition leverage demand not active")
        if accept:
            gs.update_relations('usa', 10)
            _axes = getattr(gs, 'cabinet_axes', {})
            _old_pol = _axes.get('political', 0)
            _axes['political'] = max(0, _old_pol - 2)
            gs.cabinet_axes = _axes
            messages.append(f"🇺🇸 Bill accepts your release: USA +10, Political Control {_old_pol} -> {_axes['political']}")
            print(f"  [LEVERAGE] Bill opposition ACCEPTED: USA={gs.relations.get('usa', 0)}, political={_axes['political']}")
        else:
            messages.append("🇺🇸 You declined Bill's demand. The offer expires.")
            print(f"  [LEVERAGE] Bill opposition DECLINED")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid leverage_type '{leverage_type}'")

    # Remove the leverage contact from pending list
    _pending = getattr(gs, 'pending_npc_contacts', [])
    gs.pending_npc_contacts = [c for c in _pending if c.get('leverage_type') != leverage_type]

    # Session 7B: Track NPC interaction from leverage response
    _leverage_npc_map = {'marsha_media': 'eu', 'bill_opposition': 'usa', 'sadam_reward': 'arabia'}
    _lev_npc = _leverage_npc_map.get(leverage_type)
    if _lev_npc:
        _interacted_lev = getattr(gs, 'npcs_interacted_this_turn', [])
        if _lev_npc not in _interacted_lev:
            _interacted_lev.append(_lev_npc)
            gs.npcs_interacted_this_turn = _interacted_lev

    _save_gs(session_id, gs)
    return {"success": True, "messages": messages, "game_state": gs.serialize()}


# ── Session 5: Advisor Actions ──────────────────────────────────────────────

@app.post("/game/{session_id}/advisor_action")
def advisor_action(session_id: str, body: AdvisorActionRequest):
    """Hire, dismiss, or eliminate an advisor."""
    from advisor_engine import hire_advisor, dismiss_advisor, eliminate_advisor, generate_advisor_pool

    gs = _load_gs(session_id)
    action = body.action
    advisor_id = body.advisor_id

    if action == 'hire':
        success, msg = hire_advisor(gs, advisor_id)
    elif action == 'dismiss':
        success, msg = dismiss_advisor(gs, advisor_id)
    elif action == 'eliminate':
        success, msg = eliminate_advisor(gs, advisor_id)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'")

    _save_gs(session_id, gs)

    return {
        "success": success,
        "message": msg,
        "advisors": gs.advisors,
        "advisor_pool": gs.advisor_pool,
        "game_state": gs.serialize(),
    }


@app.get("/game/{session_id}/advisor_pool")
def get_advisor_pool(session_id: str):
    """Get advisor hiring pool. v2: always regenerate dynamically."""
    from advisor_engine import generate_advisor_pool

    gs = _load_gs(session_id)

    # v2: Always regenerate pool from current gate conditions
    gs.advisor_pool = generate_advisor_pool(gs)
    _save_gs(session_id, gs)

    return {
        "advisor_pool": gs.advisor_pool,
        "advisors": gs.advisors,
        "game_state": gs.serialize(),
    }


# ── Session 7C Step 2: Advisor Assign / Unassign ───────────────────────────

class AdvisorAssignRequest(BaseModel):
    advisor_key: str

@app.post("/game/{session_id}/advisor/assign")
def advisor_assign(session_id: str, body: AdvisorAssignRequest):
    """Assign an advisor for this turn. Tracks unique advisors assigned (Set semantics)."""
    gs = _load_gs(session_id)
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        raise HTTPException(status_code=400, detail="Advisor system not initialized")

    _key = body.advisor_key
    if _key not in _advisors:
        raise HTTPException(status_code=400, detail=f"Unknown advisor: {_key}")

    _adv = _advisors[_key]
    if _adv.get('assigned_this_turn', False):
        raise HTTPException(status_code=400, detail=f"{_adv.get('name', _key)} is already assigned this turn")

    # Slot check: unique advisors assigned today (Set semantics via list)
    _slots = getattr(gs, 'advisor_slots_available', 2)
    _assigned_today = getattr(gs, 'advisor_assigned_today', [])
    _is_reassign = _key in _assigned_today  # same advisor re-assigned after unassign
    _slots_used = len(set(_assigned_today))

    if not _is_reassign and _slots_used >= _slots:
        raise HTTPException(status_code=400, detail=f"All {_slots} advisor slots have been used this turn (dismissing does not free slots)")

    _adv['assigned_this_turn'] = True

    # Add to assigned_today set (only if not already present)
    if not _is_reassign:
        _assigned_today.append(_key)
        gs.advisor_assigned_today = _assigned_today

    _slots_used_after = len(set(gs.advisor_assigned_today))
    print(f"  [advisor] SLOT CHECK: assigned_today={gs.advisor_assigned_today} slots_used={_slots_used_after}")
    print(f"  [ADVISOR] {_key} assigned for turn {gs.current_turn} — {'reassign (no new slot)' if _is_reassign else f'slots used: {_slots_used_after}/{_slots}'}")

    # Generate or retrieve cached advisor analysis
    _arch_key = _adv.get('archetype', _key)
    _cached_analyses = getattr(gs, 'advisor_analyses', {})
    _analysis = _cached_analyses.get(_key)

    if not _analysis:
        # No cached analysis — generate fresh via Claude Haiku
        try:
            _analysis = npc_engine.generate_advisor_analysis(_arch_key, gs)
        except Exception as e:
            print(f"  [ADVISOR] Analysis generation failed: {e}")
            _analysis = None

        # Cache it for this turn so reassignment returns the same text
        if _analysis:
            _cached_analyses[_key] = _analysis
            gs.advisor_analyses = _cached_analyses
            print(f"  [ADVISOR] Analysis generated and cached for {_key}")
    else:
        print(f"  [ADVISOR] Returning cached analysis for {_key}")

    _save_gs(session_id, gs)

    return {"success": True, "advisors": gs.advisors, "advisor_analysis": _analysis, "game_state": gs.serialize()}


@app.post("/game/{session_id}/advisor/unassign")
def advisor_unassign(session_id: str, body: AdvisorAssignRequest):
    """Unassign an advisor (does NOT free the slot — slots are consumed for the turn)."""
    gs = _load_gs(session_id)
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        raise HTTPException(status_code=400, detail="Advisor system not initialized")

    _key = body.advisor_key
    if _key not in _advisors:
        raise HTTPException(status_code=400, detail=f"Unknown advisor: {_key}")

    _adv = _advisors[_key]
    if not _adv.get('assigned_this_turn', False):
        raise HTTPException(status_code=400, detail=f"{_adv.get('name', _key)} is not assigned")

    _adv['assigned_this_turn'] = False
    # Note: advisor_assigned_today is NOT modified — advisor stays in the set, can reassign without consuming a new slot
    _assigned_today = getattr(gs, 'advisor_assigned_today', [])
    print(f"  [ADVISOR] {_key} unassigned for turn {gs.current_turn} — assigned_today stays: {_assigned_today}")

    _save_gs(session_id, gs)
    return {"success": True, "advisors": gs.advisors, "game_state": gs.serialize()}


# ── Advisor Hire / Dismiss / Eliminate ────────────────────────────────────────

class AdvisorHireRequest(BaseModel):
    advisor_id: str

@app.post("/game/{session_id}/advisor/hire")
def advisor_hire(session_id: str, body: AdvisorHireRequest):
    """Hire an advisor from the pool into an active slot."""
    gs = _load_gs(session_id)
    from advisor_engine import hire_advisor
    success, msg = hire_advisor(gs, body.advisor_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Generate background one-liner via Haiku
    _hired_key = None
    for k, v in gs.advisors.items():
        if isinstance(v, dict) and v.get('id') == body.advisor_id:
            _hired_key = k
            break
    if _hired_key:
        _adv = gs.advisors[_hired_key]
        try:
            _arch = _adv.get('archetype', _hired_key)
            _bg = npc_engine.generate_advisor_analysis(_arch, gs)
            # Use first sentence as background — split on '. ' (period-space)
            # to avoid breaking on decimals like $8.5B or Tier 1.25x
            _bg_short = _bg.split('. ')[0] + '.' if '. ' in _bg else _bg
            _adv['background'] = _bg_short[:120]
        except Exception as e:
            _adv['background'] = f"Experienced {_adv.get('label', 'advisor')} with connections across Europa."
            print(f"  [ADVISOR] Background generation failed: {e}")

    _save_gs(session_id, gs)
    return {"success": True, "message": msg, "advisors": gs.advisors, "advisor_pool": gs.advisor_pool, "game_state": gs.serialize()}


@app.post("/game/{session_id}/advisor/dismiss")
def advisor_dismiss(session_id: str, body: AdvisorAssignRequest):
    """Dismiss an active advisor. Free. Returns to pool."""
    gs = _load_gs(session_id)
    from advisor_engine import dismiss_advisor
    success, msg = dismiss_advisor(gs, body.advisor_key)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    _save_gs(session_id, gs)
    return {"success": True, "message": msg, "advisors": gs.advisors, "advisor_pool": gs.advisor_pool, "game_state": gs.serialize()}


@app.post("/game/{session_id}/advisor/eliminate")
def advisor_eliminate(session_id: str, body: AdvisorAssignRequest):
    """Permanently eliminate an advisor. Costs $2B personal."""
    gs = _load_gs(session_id)
    from advisor_engine import eliminate_advisor
    success, msg = eliminate_advisor(gs, body.advisor_key)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    _save_gs(session_id, gs)
    return {"success": True, "message": msg, "advisors": gs.advisors, "advisor_pool": gs.advisor_pool, "game_state": gs.serialize()}


@app.get("/game/{session_id}/advisor/pool")
def advisor_pool_get(session_id: str):
    """Get the advisor hiring pool. v2: always regenerate dynamically
    based on current gate conditions."""
    gs = _load_gs(session_id)
    from advisor_engine import generate_advisor_pool
    pool = generate_advisor_pool(gs)
    gs.advisor_pool = pool
    _save_gs(session_id, gs)
    return {"pool": pool, "advisors": gs.advisors}


# ── Session 7D: Backchannel System ─────────────────────────────────────────

class BackchannelRequest(BaseModel):
    npc_id: str
    message: str

@app.post("/game/{session_id}/backchannel")
def backchannel_message(session_id: str, body: BackchannelRequest):
    """Send a covert backchannel message to an NPC. Returns NPC response + detection risk."""
    gs = _load_gs(session_id)
    _npc_id = body.npc_id
    _message = body.message

    if _npc_id not in ALL_NPCS:
        raise HTTPException(status_code=400, detail=f"Cannot open backchannel to {_npc_id}")

    try:
        # Generate backchannel response via Claude
        _result = npc_engine.generate_backchannel_response(_npc_id, _message, gs)
        _detection_risk = npc_engine.calculate_detection_risk(_npc_id, gs)

        # Resolve promise_summary: use result, fallback to player message if empty
        _promise_summary = _result.get('promise_summary') or ''
        if _result.get('promise_detected') and not _promise_summary:
            _promise_summary = _message[:80]

        # Record the exchange in backchannel_history
        if not hasattr(gs, 'backchannel_history'):
            gs.backchannel_history = []
        _history_entry = {
            'npc_id': _npc_id,
            'turn': gs.current_turn,
            'era': getattr(gs, 'current_era', 1),
            'day': getattr(gs, 'current_day', gs.current_turn),
            'player_message': _message,
            'response_text': _result.get('response_text', ''),
            'promise_made': _result.get('promise_detected', False),
            'promise_text': _promise_summary,
            'detected_by': None,
        }
        gs.backchannel_history.append(_history_entry)

        # If promise detected, record it in active promises
        _promise_recorded = False
        if _result.get('promise_detected'):
            _promise = {
                'npc_id': _npc_id,
                'turn': gs.current_turn,
                'era': getattr(gs, 'current_era', 1),
                'day': getattr(gs, 'current_day', gs.current_turn),
                'promise_made': True,
                'promise_text': _promise_summary,
                'detected_by': None,
                'resolved': False,
            }
            if not hasattr(gs, 'active_backchannel_promises'):
                gs.active_backchannel_promises = []
            gs.active_backchannel_promises.append(_promise)
            _promise_recorded = True
            print(f"  [BACKCHANNEL] Promise recorded with {_npc_id}: {_promise_summary[:60]}")

        _save_gs(session_id, gs)

        return {
            "response_text": _result["response_text"],
            "detection_risk": round(_detection_risk, 3),
            "promise_recorded": _promise_recorded,
            "promise_summary": _promise_summary or None,
            "game_state": gs.serialize(),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"  [BACKCHANNEL] ERROR in backchannel_message: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Backchannel error: {type(e).__name__}: {str(e)}")


@app.get("/game/{session_id}/backchannel/history")
def backchannel_history(session_id: str):
    """Get backchannel history and active promises for display."""
    gs = _load_gs(session_id)
    return {
        "backchannel_history": getattr(gs, 'backchannel_history', []),
        "active_backchannel_promises": getattr(gs, 'active_backchannel_promises', []),
    }


# ── Session 7E: UN Summit System ──────────────────────────────────────────────

class SummitDeclareRequest(BaseModel):
    declaration: str

@app.post("/game/{session_id}/summit/declare")
def summit_declare(session_id: str, body: SummitDeclareRequest):
    """Player makes a public declaration at the UN Summit. Generates all NPC reactions."""
    gs = _load_gs(session_id)
    _declaration = body.declaration

    try:
        # Generate reactions from all 6 NPCs in parallel
        _reactions = npc_engine.generate_summit_reactions(_declaration, gs)

        # Detect commitments in declaration (same keyword approach as backchannel)
        from npc_engine import _PROMISE_KEYWORDS
        _commitments_recorded = []
        if _PROMISE_KEYWORDS.search(_declaration):
            # Extract sentences containing commitment language
            _sentences = re.split(r'(?<=[.!?])\s+', _declaration)
            for _s in _sentences:
                if _PROMISE_KEYWORDS.search(_s):
                    _commitment = {
                        'commitment_text': _s[:200],
                        'day_made': getattr(gs, 'current_day', gs.current_turn),
                        'era_made': getattr(gs, 'current_era', 1),
                        'broken': False,
                    }
                    if not hasattr(gs, 'active_summit_commitments'):
                        gs.active_summit_commitments = []
                    gs.active_summit_commitments.append(_commitment)
                    _commitments_recorded.append(_commitment)
                    print(f"  [SUMMIT] Commitment recorded: {_s[:60]}")

        # Record in summit history
        if not hasattr(gs, 'summit_history'):
            gs.summit_history = []
        _history_entry = {
            'era': getattr(gs, 'current_era', 1),
            'day': getattr(gs, 'current_day', gs.current_turn),
            'player_declaration': _declaration,
            'npc_reactions': _reactions,
            'commitments_made': [c['commitment_text'] for c in _commitments_recorded],
        }
        gs.summit_history.append(_history_entry)

        _save_gs(session_id, gs)

        return {
            "reactions": _reactions,
            "commitments_recorded": len(_commitments_recorded),
            "game_state": gs.serialize(),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"  [SUMMIT] ERROR in summit_declare: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Summit error: {type(e).__name__}: {str(e)}")


@app.post("/game/{session_id}/summit/auto_position")
def summit_auto_position(session_id: str):
    """Generate an auto-drafted holding statement for the summit."""
    gs = _load_gs(session_id)

    try:
        _position = npc_engine.generate_auto_position(gs)
        return {"position_text": _position}
    except Exception as e:
        print(f"  [SUMMIT] ERROR in auto_position: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Summit auto-position error: {str(e)}")


@app.post("/game/{session_id}/summit/close")
def summit_close(session_id: str):
    """Close the active summit session, unblocking End Day."""
    gs = _load_gs(session_id)
    gs.summit_due = False
    _save_gs(session_id, gs)
    print(f"  [SUMMIT] Summit closed for session {session_id}")
    return {"game_state": gs.serialize()}


# ── Session 5: Tax Rate Adjustment ──────────────────────────────────────────

@app.post("/game/{session_id}/set_tax_rates")
def set_tax_rates(session_id: str, body: TaxRateRequest):
    """Adjust tax rate sliders. Changes take effect at next EOT.
    fixes_13 Fix 28: Dynamic caps based on Judicial/Political axes."""
    gs = _load_gs(session_id)
    rates = getattr(gs, 'tax_rates', {})
    axes = getattr(gs, 'cabinet_axes', {})
    changes = []

    # fixes_13 Fix 28: Compute dynamic tax caps based on axes
    _judicial = axes.get('judicial', 0)
    _political = axes.get('political', 0)
    _income_cap = 0.50     # base
    _corporate_cap = 0.40  # base
    _resource_cap = 0.60   # base
    _emergency_fired = False

    if _judicial >= 5:
        _resource_cap = 0.75  # Judicial 5+: resource cap rises to 75%
    if _political >= 7:
        _income_cap = 0.65    # Political 7+: income cap rises to 65%
    if _judicial >= 8 and _political >= 8:
        _income_cap = 0.85    # Both 8+: all caps rise to 85%
        _corporate_cap = 0.85
        _resource_cap = 0.85
        # Check if emergency economic measures world event has already fired
        _emergency_events = getattr(gs, 'emergency_tax_event_fired', False)
        if not _emergency_events:
            _emergency_fired = True

    print(f"  [api] Fix 28: Tax caps — income {_income_cap*100:.0f}%, corporate {_corporate_cap*100:.0f}%, resource {_resource_cap*100:.0f}% (judicial={_judicial}, political={_political})")

    if body.income_tax is not None:
        new_val = max(0.0, min(_income_cap, body.income_tax))
        old_val = rates.get('income_tax', 0.20)
        rates['income_tax'] = round(new_val, 2)
        changes.append(f"Income tax: {old_val*100:.0f}% -> {new_val*100:.0f}%")

    if body.corporate_tax is not None:
        new_val = max(0.0, min(_corporate_cap, body.corporate_tax))
        old_val = rates.get('corporate_tax', 0.15)
        rates['corporate_tax'] = round(new_val, 2)
        changes.append(f"Corporate tax: {old_val*100:.0f}% -> {new_val*100:.0f}%")

    if body.resource_tax is not None:
        new_val = max(0.0, min(_resource_cap, body.resource_tax))
        old_val = rates.get('resource_tax', 0.25)
        rates['resource_tax'] = round(new_val, 2)
        changes.append(f"Resource tax: {old_val*100:.0f}% -> {new_val*100:.0f}%")

    # fixes_13 Fix 28: Fire emergency economic measures world event when both axes 8+ unlock activated
    if _emergency_fired:
        gs.emergency_tax_event_fired = True
        gs.update_relations('eu', -10, source="emergency economic measures")
        gs.update_relations('usa', -8, source="emergency economic measures")
        gs.update_relations('arabia', 2, source="emergency economic measures")
        gs.update_stability(-5)
        changes.append("⚠️ EMERGENCY ECONOMIC MEASURES — EU -10, USA -8, Arabia +2, Stability -5%")
        print(f"  [api] Fix 28: Emergency economic measures world event fired")

    gs.tax_rates = rates
    _save_gs(session_id, gs)

    # fixes_11 Fix 9: Collapse tax changes into single summary line
    _income = rates.get('income_tax', 0.20)
    _corp = rates.get('corporate_tax', 0.15)
    _resource = rates.get('resource_tax', 0.25)
    _summary = f"Tax rates set: income {_income*100:.0f}%, corporate {_corp*100:.0f}%, resource {_resource*100:.0f}%"

    return {
        "success": True,
        "changes": [_summary] if changes else [],
        "tax_rates": rates,
        # fixes_13 Fix 28: Return dynamic caps for frontend sliders
        "tax_caps": {
            "income_tax": _income_cap,
            "corporate_tax": _corporate_cap,
            "resource_tax": _resource_cap,
        },
        "game_state": gs.serialize(),
    }


# ── 9.5A: Commitment Model Endpoints ─────────────────────────────────────────

@app.post("/game/{session_id}/commitment/upgrade")
def commitment_upgrade(session_id: str, body: CommitmentUpgradeRequest):
    """9.5A: Upgrade a tier by 1 level. Checks cooldowns, prerequisites, GDP gates.
    Deducts upgrade cost from budget (or personal_wealth for militia)."""
    from turn_processor import (TIER_COSTS, TIER_UPGRADE_COOLDOWNS, check_prerequisites,
                                compute_daily_commitment_cost)
    gs = _load_gs(session_id)
    tier_key = body.tier_key
    valid_keys = ['military', 'intelligence', 'diplomatic', 'social',
                  'education', 'resource', 'political', 'militia']

    if tier_key not in valid_keys:
        return {"success": False, "error": f"Invalid tier_key: {tier_key}"}

    tier_attr = f"{tier_key}_tier"
    current_tier = getattr(gs, tier_attr, 0)
    target_tier = current_tier + 1

    if target_tier > 10:
        return {"success": False, "error": f"{tier_key} already at maximum (10)"}

    # Check cooldown
    cooldowns = getattr(gs, 'tier_upgrade_cooldowns', {})
    cooldown_until = cooldowns.get(tier_key, 0)
    current_day = getattr(gs, 'current_day', getattr(gs, 'current_turn', 1))
    if current_day < cooldown_until:
        days_left = cooldown_until - current_day
        return {
            "success": False,
            "error": f"{tier_key} upgrade on cooldown — {days_left} day(s) remaining",
            "cooldown_remaining": days_left,
        }

    # Check prerequisites
    prereq = check_prerequisites(gs, tier_key, target_tier)
    if prereq['hard_blocked']:
        return {
            "success": False,
            "error": f"{tier_key} upgrade hard-blocked: {'; '.join(prereq['violations'])}",
            "violations": prereq['violations'],
        }

    # Calculate upgrade cost (one-time cost = daily cost of new tier × cooldown days)
    base_daily = TIER_COSTS.get(tier_key, {}).get(target_tier, 0.0)
    cooldown_days = TIER_UPGRADE_COOLDOWNS.get(tier_key, {}).get(target_tier, 3)
    upgrade_cost = round(base_daily * cooldown_days * 0.5, 1)  # half of cooldown period worth

    # Apply prerequisite cost multiplier
    upgrade_cost = round(upgrade_cost * prereq['cost_multiplier'], 1)

    # Militia pays from personal wealth, all others from budget
    if tier_key == 'militia':
        pw = getattr(gs, 'personal_wealth', 0.0)
        if pw < upgrade_cost:
            return {
                "success": False,
                "error": f"Insufficient personal wealth: need ${upgrade_cost:.1f}B, have ${pw:.1f}B",
            }
        gs.personal_wealth = round(pw - upgrade_cost, 2)
    else:
        if gs.budget < upgrade_cost:
            return {
                "success": False,
                "error": f"Insufficient budget: need ${upgrade_cost:.1f}B, have ${gs.budget:.1f}B",
            }
        gs.update_budget(-upgrade_cost)

    # Apply upgrade
    setattr(gs, tier_attr, target_tier)

    # Sync education_level from education_tier for backward compatibility
    if tier_key == 'education':
        gs.education_level = min(target_tier, 3)  # education_level caps at 3
        print(f"  [FIX3] education_level synced to {gs.education_level} from tier {target_tier}")


    # Set cooldown
    cooldowns[tier_key] = current_day + cooldown_days
    gs.tier_upgrade_cooldowns = cooldowns

    # Track prerequisite violations
    if not prereq['met']:
        gs.prerequisite_violations[tier_key] = True
    elif tier_key in getattr(gs, 'prerequisite_violations', {}):
        del gs.prerequisite_violations[tier_key]

    # Recompute daily costs
    compute_daily_commitment_cost(gs)

    _save_gs(session_id, gs)

    warnings = []
    if prereq['violations']:
        warnings.append(f"Prerequisites not met: {'; '.join(prereq['violations'])} — cost x{prereq['cost_multiplier']:.0f}")

    print(f"  [9.5A] UPGRADE: {tier_key} {current_tier} -> {target_tier}, "
          f"cost=${upgrade_cost:.1f}B, cooldown={cooldown_days}d, "
          f"prereq_met={prereq['met']}")

    return {
        "success": True,
        "tier_key": tier_key,
        "old_tier": current_tier,
        "new_tier": target_tier,
        "cost": upgrade_cost,
        "cooldown_days": cooldown_days,
        "cooldown_until_day": current_day + cooldown_days,
        "warnings": warnings,
        "message": f"{tier_key.title()} upgraded to tier {target_tier} (cost ${upgrade_cost:.1f}B, {cooldown_days}d cooldown)",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/commitment/downgrade")
def commitment_downgrade(session_id: str, body: CommitmentDowngradeRequest):
    """9.5A: Downgrade a tier by 1 level. Immediate, no cooldown.
    Reduces daily commitment costs."""
    from turn_processor import compute_daily_commitment_cost
    gs = _load_gs(session_id)
    tier_key = body.tier_key
    valid_keys = ['military', 'intelligence', 'diplomatic', 'social',
                  'education', 'resource', 'political', 'militia']

    if tier_key not in valid_keys:
        return {"success": False, "error": f"Invalid tier_key: {tier_key}"}

    tier_attr = f"{tier_key}_tier"
    current_tier = getattr(gs, tier_attr, 0)

    if current_tier <= 0:
        return {"success": False, "error": f"{tier_key} already at minimum (0)"}

    new_tier = current_tier - 1
    setattr(gs, tier_attr, new_tier)

    # Sync education_level from education_tier for backward compatibility
    if tier_key == 'education':
        gs.education_level = min(new_tier, 3)
        print(f"  [FIX3] education_level synced to {gs.education_level} from tier {new_tier}")


    # Clear any prerequisite violations for this axis
    if tier_key in getattr(gs, 'prerequisite_violations', {}):
        del gs.prerequisite_violations[tier_key]

    # Recompute daily costs
    compute_daily_commitment_cost(gs)

    _save_gs(session_id, gs)

    print(f"  [9.5A] DOWNGRADE: {tier_key} {current_tier} -> {new_tier}")

    return {
        "success": True,
        "tier_key": tier_key,
        "old_tier": current_tier,
        "new_tier": new_tier,
        "message": f"{tier_key.title()} downgraded to tier {new_tier}",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/commitment/skim")
def commitment_set_skim(session_id: str, body: CommitmentSkimRequest):
    """9.5A: Set the skim rate (% of revenue diverted to personal wealth).
    9.5A-Shadow: Now enforces EXTRACTION_SKIM_CEILING based on extraction_tier.
    Above 5% generates detection heat each turn."""
    from turn_processor import EXTRACTION_SKIM_CEILING
    gs = _load_gs(session_id)

    old_rate = getattr(gs, 'skim_rate', 0.0)
    ext_tier = getattr(gs, 'extraction_tier', 0)
    skim_ceiling = EXTRACTION_SKIM_CEILING.get(ext_tier, 0.05)

    new_rate = max(0.0, min(skim_ceiling, round(body.skim_rate, 2)))
    gs.skim_rate = new_rate

    warnings = []
    if body.skim_rate > skim_ceiling:
        warnings.append(f"Skim rate capped at {skim_ceiling*100:.0f}% by extraction tier {ext_tier} "
                        f"(requested {body.skim_rate*100:.0f}%)")
    if new_rate > 0.20:
        warnings.append("Skim rate above 20% is extremely risky \u2014 rapid heat generation and NPC detection")
    elif new_rate > 0.10:
        warnings.append("Skim rate above 10% generates significant detection heat")
    elif new_rate > 0.05:
        warnings.append("Skim rate above 5% generates detection heat each turn")

    _save_gs(session_id, gs)

    print(f"  [9.5A] SKIM_RATE: {old_rate*100:.0f}% -> {new_rate*100:.0f}% "
          f"(ceiling={skim_ceiling*100:.0f}% at ext_tier={ext_tier})")

    return {
        "success": True,
        "old_skim_rate": old_rate,
        "new_skim_rate": new_rate,
        "skim_ceiling": skim_ceiling,
        "extraction_tier": ext_tier,
        "warnings": warnings,
        "message": f"Skim rate set to {new_rate*100:.0f}% (was {old_rate*100:.0f}%, ceiling {skim_ceiling*100:.0f}%)",
        "game_state": gs.serialize(),
    }


# ── 9.5A-Shadow: Shadow State Tier Endpoints ─────────────────────────────

@app.post("/game/{session_id}/shadow/upgrade")
def shadow_upgrade(session_id: str, body: ShadowUpgradeRequest):
    """9.5A-Shadow: Upgrade a shadow tier by 1 level.
    Shadow axes pay from personal wealth. Checks cooldowns and prerequisites."""
    from turn_processor import (SHADOW_TIER_COSTS, SHADOW_TIER_UPGRADE_COOLDOWNS,
                                SHADOW_PREREQUISITES, compute_shadow_state_costs,
                                TIER_COSTS, TIER_UPGRADE_COOLDOWNS)
    gs = _load_gs(session_id)
    shadow_key = body.shadow_key
    valid_keys = ['media', 'judicial', 'domestic_surveillance', 'extraction', 'militia']

    if shadow_key not in valid_keys:
        return {"success": False, "error": f"Invalid shadow_key: {shadow_key}"}

    tier_attr = f"{shadow_key}_tier"
    current_tier = getattr(gs, tier_attr, 0)
    target_tier = current_tier + 1

    if target_tier > 10:
        return {"success": False, "error": f"{shadow_key} already at maximum (10)"}

    # Check cooldown (shadow axes use separate cooldown tracking)
    shadow_cooldowns = getattr(gs, 'shadow_tier_cooldowns', {})
    cooldown_until = shadow_cooldowns.get(shadow_key, 0)
    current_day = getattr(gs, 'current_day', getattr(gs, 'current_turn', 1))
    if current_day < cooldown_until:
        days_left = cooldown_until - current_day
        return {
            "success": False,
            "error": f"{shadow_key} upgrade on cooldown \u2014 {days_left} day(s) remaining",
            "cooldown_remaining": days_left,
        }

    # Check prerequisites (soft gates -- cost x2 if unmet)
    prereqs = SHADOW_PREREQUISITES.get(shadow_key, {})
    cost_multiplier = 1.0
    violations = []
    for min_tier, requirements in prereqs.items():
        if target_tier >= min_tier:
            for prereq_key, prereq_value in requirements.items():
                current_val = getattr(gs, prereq_key, 0)
                if isinstance(current_val, float):
                    current_val = int(current_val)
                if current_val < prereq_value:
                    cost_multiplier = 2.0
                    violations.append(f"{prereq_key} needs {prereq_value} (have {current_val})")

    # Calculate upgrade cost (one-time = daily cost of new tier x cooldown x 0.5)
    # Militia uses TIER_COSTS/TIER_UPGRADE_COOLDOWNS; other shadow axes use SHADOW_TIER_COSTS
    base_daily = SHADOW_TIER_COSTS.get(shadow_key, TIER_COSTS.get(shadow_key, {})).get(target_tier, 0.0)
    cooldown_days = SHADOW_TIER_UPGRADE_COOLDOWNS.get(shadow_key, TIER_UPGRADE_COOLDOWNS.get(shadow_key, {})).get(target_tier, 3)
    upgrade_cost = round(base_daily * cooldown_days * 0.5, 1)
    upgrade_cost = round(upgrade_cost * cost_multiplier, 1)

    # Shadow tiers always pay from personal wealth
    pw = getattr(gs, 'personal_wealth', 0.0)
    if pw < upgrade_cost:
        return {
            "success": False,
            "error": f"Insufficient personal wealth: need ${upgrade_cost:.1f}B, have ${pw:.1f}B",
        }
    gs.personal_wealth = round(pw - upgrade_cost, 2)

    # Apply upgrade
    setattr(gs, tier_attr, target_tier)

    # Set cooldown
    shadow_cooldowns[shadow_key] = current_day + cooldown_days
    gs.shadow_tier_cooldowns = shadow_cooldowns

    # Recompute shadow costs
    compute_shadow_state_costs(gs)

    _save_gs(session_id, gs)

    warnings = []
    if violations:
        warnings.append(f"Prerequisites not met: {'; '.join(violations)} \u2014 cost x{cost_multiplier:.0f}")

    print(f"  [9.5A-Shadow] UPGRADE: {shadow_key} {current_tier} -> {target_tier}, "
          f"cost=${upgrade_cost:.1f}B personal, cooldown={cooldown_days}d, "
          f"prereq_violations={violations}")

    return {
        "success": True,
        "shadow_key": shadow_key,
        "old_tier": current_tier,
        "new_tier": target_tier,
        "cost": upgrade_cost,
        "cost_source": "personal_wealth",
        "cooldown_days": cooldown_days,
        "cooldown_until_day": current_day + cooldown_days,
        "warnings": warnings,
        "message": f"{shadow_key.replace('_', ' ').title()} upgraded to tier {target_tier} (cost ${upgrade_cost:.1f}B personal, {cooldown_days}d cooldown)",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/shadow/downgrade")
def shadow_downgrade(session_id: str, body: ShadowDowngradeRequest):
    """9.5A-Shadow: Downgrade a shadow tier by 1 level. Immediate, no cooldown.
    Reduces daily shadow state costs."""
    from turn_processor import compute_shadow_state_costs
    gs = _load_gs(session_id)
    shadow_key = body.shadow_key
    valid_keys = ['media', 'judicial', 'domestic_surveillance', 'extraction', 'militia']

    if shadow_key not in valid_keys:
        return {"success": False, "error": f"Invalid shadow_key: {shadow_key}"}

    tier_attr = f"{shadow_key}_tier"
    current_tier = getattr(gs, tier_attr, 0)

    if current_tier <= 0:
        return {"success": False, "error": f"{shadow_key} already at minimum (0)"}

    new_tier = current_tier - 1
    setattr(gs, tier_attr, new_tier)

    # Recompute shadow costs
    compute_shadow_state_costs(gs)

    _save_gs(session_id, gs)

    print(f"  [9.5A-Shadow] DOWNGRADE: {shadow_key} {current_tier} -> {new_tier}")

    return {
        "success": True,
        "shadow_key": shadow_key,
        "old_tier": current_tier,
        "new_tier": new_tier,
        "message": f"{shadow_key.replace('_', ' ').title()} downgraded to tier {new_tier}",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/shadow/skim")
def shadow_set_skim(session_id: str, body: ShadowSkimRequest):
    """9.5A-Shadow: Set skim rate with EXTRACTION_SKIM_CEILING enforcement.
    This is the shadow-aware skim endpoint. Skim rate is persistent (no per-turn prompt)."""
    from turn_processor import EXTRACTION_SKIM_CEILING
    gs = _load_gs(session_id)

    old_rate = getattr(gs, 'skim_rate', 0.0)
    ext_tier = getattr(gs, 'extraction_tier', 0)
    skim_ceiling = EXTRACTION_SKIM_CEILING.get(ext_tier, 0.05)

    new_rate = max(0.0, min(skim_ceiling, round(body.skim_rate, 2)))
    gs.skim_rate = new_rate

    warnings = []
    if body.skim_rate > skim_ceiling:
        warnings.append(f"Skim rate capped at {skim_ceiling*100:.0f}% by extraction tier {ext_tier} "
                        f"(requested {body.skim_rate*100:.0f}%)")
    if new_rate > 0.20:
        warnings.append("Skim above 20%: extreme heat generation and NPC detection risk")
    elif new_rate > 0.10:
        warnings.append("Skim above 10%: significant detection heat")
    elif new_rate > 0.05:
        warnings.append("Skim above 5%: generates detection heat each turn")

    _save_gs(session_id, gs)

    print(f"  [9.5A-Shadow] SKIM_RATE: {old_rate*100:.0f}% -> {new_rate*100:.0f}% "
          f"(ceiling={skim_ceiling*100:.0f}% at ext_tier={ext_tier})")

    return {
        "success": True,
        "old_skim_rate": old_rate,
        "new_skim_rate": new_rate,
        "skim_ceiling": skim_ceiling,
        "extraction_tier": ext_tier,
        "warnings": warnings,
        "message": f"Skim rate set to {new_rate*100:.0f}% (ceiling {skim_ceiling*100:.0f}% at extraction tier {ext_tier})",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/shadow/merger")
def shadow_merger(session_id: str, body: ShadowMergerRequest):
    """9.5A-Shadow: Merge shadow axis with national axis for shared benefits.
    - militia merger: militia_tier >= 5 AND military_tier >= 5
    - surveillance merger: domestic_surveillance_tier >= 5 AND intelligence_tier >= 5
    Merger is permanent and one-time."""
    gs = _load_gs(session_id)
    merger_type = body.merger_type

    if merger_type == 'militia':
        if getattr(gs, 'militia_merged', False):
            return {"success": False, "error": "Militia merger already completed"}

        militia_t = getattr(gs, 'militia_tier', 0)
        military_t = getattr(gs, 'military_tier', 0)

        if militia_t < 5:
            return {"success": False,
                    "error": f"Militia tier must be >= 5 (currently {militia_t})"}
        if military_t < 5:
            return {"success": False,
                    "error": f"Military tier must be >= 5 (currently {military_t})"}

        gs.militia_merged = True
        _save_gs(session_id, gs)

        print(f"  [9.5A-Shadow] MERGER: militia (militia_t={militia_t}, military_t={military_t})")

        return {
            "success": True,
            "merger_type": "militia",
            "message": "Militia merged with military \u2014 militia costs now shared with military budget, "
                       "stability bonus from combined force projection",
            "game_state": gs.serialize(),
        }

    elif merger_type == 'surveillance':
        if getattr(gs, 'surveillance_merged', False):
            return {"success": False, "error": "Surveillance merger already completed"}

        surv_t = getattr(gs, 'domestic_surveillance_tier', 0)
        intel_t = getattr(gs, 'intelligence_tier', 0)

        if surv_t < 5:
            return {"success": False,
                    "error": f"Domestic surveillance tier must be >= 5 (currently {surv_t})"}
        if intel_t < 5:
            return {"success": False,
                    "error": f"Intelligence tier must be >= 5 (currently {intel_t})"}

        gs.surveillance_merged = True
        _save_gs(session_id, gs)

        print(f"  [9.5A-Shadow] MERGER: surveillance (surv_t={surv_t}, intel_t={intel_t})")

        return {
            "success": True,
            "merger_type": "surveillance",
            "message": "Domestic surveillance merged with intelligence \u2014 shared infrastructure, "
                       "reduced combined costs, enhanced detection capabilities",
            "game_state": gs.serialize(),
        }

    else:
        return {"success": False, "error": f"Invalid merger_type: {merger_type} (use 'militia' or 'surveillance')"}


# ── 9.5C: Loyal Leadership ──────────────────────────────────────────────────

class LoyalInstallRequest(BaseModel):
    role: str  # "generals" | "intel_chief"

class LoyalReverseRequest(BaseModel):
    role: str  # "generals" | "intel_chief"


@app.post("/game/{session_id}/loyal/install")
def loyal_install(session_id: str, body: LoyalInstallRequest):
    """9.5C: Install loyal generals or loyal intel chief."""
    gs = _load_gs(session_id)
    role = body.role

    if role == "generals":
        if getattr(gs, 'political_tier', 0) < 3:
            raise HTTPException(status_code=400, detail="Requires Political Tier 3+")
        if getattr(gs, 'loyal_generals_installed', False):
            raise HTTPException(status_code=400, detail="Loyal generals already installed")
        if gs.personal_wealth < 3.0:
            raise HTTPException(status_code=400, detail=f"Need $3B personal wealth, have ${gs.personal_wealth:.1f}B")

        gs.update_personal_wealth(-3.0, source="loyal generals installation")
        gs.loyal_generals_installed = True
        gs.loyal_generals_install_day = gs.current_day
        gs.loyal_generals_cost_paid = 3.0
        if not hasattr(gs, 'pending_briefing_items'):
            gs.pending_briefing_items = []
        gs.pending_briefing_items.append(
            "Loyal generals have been installed in key command positions. "
            "The military is politically reliable. Its professional ceiling has been adjusted.")
        print(f"[9.5C] loyal_generals: action=install pw_after={gs.personal_wealth:.1f}")

    elif role == "intel_chief":
        if getattr(gs, 'political_tier', 0) < 3:
            raise HTTPException(status_code=400, detail="Requires Political Tier 3+")
        if getattr(gs, 'loyal_intel_chief_installed', False):
            raise HTTPException(status_code=400, detail="Loyal intel chief already installed")
        if gs.personal_wealth < 2.5:
            raise HTTPException(status_code=400, detail=f"Need $2.5B personal wealth, have ${gs.personal_wealth:.1f}B")

        gs.update_personal_wealth(-2.5, source="loyal intel chief installation")
        gs.loyal_intel_chief_installed = True
        gs.loyal_intel_chief_install_day = gs.current_day
        gs.loyal_intel_chief_cost_paid = 2.5
        if not hasattr(gs, 'pending_briefing_items'):
            gs.pending_briefing_items = []
        gs.pending_briefing_items.append(
            "A trusted ally has been placed at the head of the intelligence apparatus. "
            "Reports will be more... consistent with expectations.")
        print(f"[9.5C] loyal_intel_chief: action=install pw_after={gs.personal_wealth:.1f}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role} (use 'generals' or 'intel_chief')")

    _save_gs(session_id, gs)
    return {
        "success": True,
        "role": role,
        "action": "install",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/loyal/reverse")
def loyal_reverse(session_id: str, body: LoyalReverseRequest):
    """9.5C: Begin reversal of loyal generals or loyal intel chief (3-day transition)."""
    gs = _load_gs(session_id)
    role = body.role

    if role == "generals":
        if not getattr(gs, 'loyal_generals_installed', False):
            raise HTTPException(status_code=400, detail="Loyal generals not installed")
        if getattr(gs, 'loyal_generals_reversing', False):
            raise HTTPException(status_code=400, detail="Reversal already in progress")
        if gs.personal_wealth < 2.0:
            raise HTTPException(status_code=400, detail=f"Need $2B personal wealth for transition, have ${gs.personal_wealth:.1f}B")

        gs.update_personal_wealth(-2.0, source="loyal generals reversal")
        gs.loyal_generals_reversing = True
        gs.loyal_generals_reversal_day = gs.current_day
        if not hasattr(gs, 'pending_briefing_items'):
            gs.pending_briefing_items = []
        gs.pending_briefing_items.append(
            "The transition to professional military leadership has begun. "
            "It will take several days. The officers who were passed over will not forget.")
        print(f"[9.5C] loyal_generals: action=reverse pw_after={gs.personal_wealth:.1f}")

    elif role == "intel_chief":
        if not getattr(gs, 'loyal_intel_chief_installed', False):
            raise HTTPException(status_code=400, detail="Loyal intel chief not installed")
        if getattr(gs, 'loyal_intel_chief_reversing', False):
            raise HTTPException(status_code=400, detail="Reversal already in progress")
        if gs.personal_wealth < 2.0:
            raise HTTPException(status_code=400, detail=f"Need $2B personal wealth for transition, have ${gs.personal_wealth:.1f}B")

        gs.update_personal_wealth(-2.0, source="loyal intel chief reversal")
        gs.loyal_intel_chief_reversing = True
        gs.loyal_intel_chief_reversal_day = gs.current_day
        if not hasattr(gs, 'pending_briefing_items'):
            gs.pending_briefing_items = []
        gs.pending_briefing_items.append(
            "The transition to professional intelligence leadership has begun.")
        print(f"[9.5C] loyal_intel_chief: action=reverse pw_after={gs.personal_wealth:.1f}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role} (use 'generals' or 'intel_chief')")

    _save_gs(session_id, gs)
    return {
        "success": True,
        "role": role,
        "action": "reverse",
        "game_state": gs.serialize(),
    }


# ── fixes_13 Fix 21: Bond Financing ──────────────────────────────────────────

@app.post("/game/{session_id}/issue_bonds")
def issue_bonds(session_id: str, body: BondRequest):
    """
    fixes_15 Fix B: Bond financing redesign.
    $5B Small Bond: 20% interest ($2B/turn × 3), no NPC penalty, once per turn, unlimited.
    $10B Large Bond: 30% interest (~$4.3B/turn × 3), -5 all NPCs, budget < $20B gate, once per game.
    """
    gs = _load_gs(session_id)
    amount = body.amount
    if amount not in (5, 10):
        raise HTTPException(status_code=400, detail="Bond amount must be 5 or 10 (billions)")

    # Session 6: Resource Dev L10 — Better Bond Terms reduces interest
    _better_terms = getattr(gs, 'cabinet_axes', {}).get('resource_dev', 0) >= 10

    if amount == 5:
        # ── Small Bond: $5B, 20% interest (15% with Better Bond Terms) ────
        _bond_turn = getattr(gs, 'small_bond_last_turn', -1)
        if _bond_turn >= gs.current_turn:
            raise HTTPException(status_code=400,
                                detail="One bond issue per turn — return next turn for additional financing")
        repayment = round(5.75 / 3.0, 1) if _better_terms else 2.0  # 15% or 20% interest
        gs.update_budget(5.0)
        if not hasattr(gs, 'active_installments'):
            gs.active_installments = []
        gs.active_installments.append({
            'amount': -repayment,
            'turns_remaining': 3,
            'description': 'Small bond repayment ($5B issue)',
            'npc': 'bond',
        })
        gs.small_bond_last_turn = gs.current_turn
        changes = ["+$5B from bond issuance", "-$2B/turn for 3 turns (20% interest)", "No diplomatic signal"]
        print(f"  [api] BONDS ISSUED: $5B small bond, repayment -$2B/turn × 3")

    else:
        # ── Large Bond: $10B, 30% interest, -5 all NPCs, budget gate, once per game ─
        _large_used = getattr(gs, 'large_bond_used', False)
        if _large_used:
            raise HTTPException(status_code=400,
                                detail="International creditors will not extend further emergency credit")
        if gs.budget >= 20:
            raise HTTPException(status_code=400,
                                detail="Emergency financing only available under fiscal stress (budget below $20B)")
        repayment = round(12.2 / 3.0, 1) if _better_terms else round(13.0 / 3.0, 1)  # 22% or 30% interest
        gs.update_budget(10.0)
        if not hasattr(gs, 'active_installments'):
            gs.active_installments = []
        gs.active_installments.append({
            'amount': -repayment,
            'turns_remaining': 3,
            'description': 'Emergency bond repayment ($10B issue)',
            'npc': 'bond',
        })
        # -5 all NPCs on every large bond issuance
        for npc in ALL_NPCS:
            gs.update_relations(npc, -5)
        gs.large_bond_used = True
        changes = ["+$10B from emergency bond", f"-${repayment:.1f}B/turn for 3 turns (30% interest)",
                   "ALL NPCs -5 (fiscal distress signal)"]
        print(f"  [api] BONDS ISSUED: $10B large bond, repayment -${repayment:.1f}B/turn × 3, all NPCs -5")

    gs.bonds_issued_count = getattr(gs, 'bonds_issued_count', 0) + 1

    # Record in action_history
    gs.action_history.append({
        'type': 'bond_issuance',
        'amount': amount,
        'turn': gs.current_turn,
    })

    _save_gs(session_id, gs)
    return {
        "success": True,
        "changes": changes,
        "game_state": gs.serialize(),
    }


# ── Session 5: Brigade Operations ────────────────────────────────────────────

@app.post("/game/{session_id}/brigade_operation")
def brigade_operation(session_id: str, body: BrigadeRequest):
    """
    Session 5/6: Tactical brigade deployment from Operations drawer.
    Session 6: Gated by Military axis >= 3 (was Security).
    Operations: 0=stand_down, 1=propaganda, 2=domestic_suppression,
                3=foreign_influence, 4=covert_security, 5=black_operation
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    military_level = axes.get('military', 0)
    intelligence_level = axes.get('intelligence', 0)

    # Ops 1-2 require Military >= 3; Ops 3-4 require Intelligence >= 3
    if body.operation in (1, 2) and military_level < 3:
        raise HTTPException(status_code=400, detail="Military axis must be >= 3 for this operation")
    if body.operation in (3, 4) and intelligence_level < 3:
        raise HTTPException(status_code=400, detail="Intelligence axis must be >= 3 for this operation")
    if body.operation not in (0, 1, 2, 3, 4, 5) and military_level < 3 and intelligence_level < 3:
        raise HTTPException(status_code=400, detail="Military or Intelligence axis must be >= 3 for brigade operations")

    # fixes_11 Fix 2: Enforce one operation per turn
    ops_this_turn = getattr(gs, 'brigade_operations_this_turn', [])
    current_turn_ops = [o for o in ops_this_turn if o.get('turn') == gs.current_turn and o.get('operation', 0) != 0]
    if current_turn_ops and body.operation != 0:
        print(f"  [api] BRIGADE BLOCKED: already deployed op {current_turn_ops[0]['operation']} this turn")
        raise HTTPException(status_code=400, detail="Only one brigade operation can be deployed per turn")

    op = body.operation
    messages = []

    if op == 0:
        messages.append("Brigades standing down this turn.")
    elif op == 1:
        # Propaganda — fixes_17 Fix A: personal wealth, not national budget
        if gs.personal_wealth < 1.0:
            raise HTTPException(status_code=400, detail="Need $1B personal wealth for propaganda operation")
        gs.update_personal_wealth(-1.0, source="propaganda campaign")
        gs.update_approval(5)
        messages.append("📺 Propaganda deployed: +5% approval, -$1B personal")
        print(f"  [BRIGADE] Propaganda Campaign: -$1B personal (pw now ${gs.personal_wealth:.1f}B)")
    elif op == 2:
        # Domestic Suppression — fixes_17 Fix A: personal wealth, not national budget
        if gs.personal_wealth < 2.0:
            raise HTTPException(status_code=400, detail="Need $2B personal wealth for domestic suppression")
        gs.update_personal_wealth(-2.0, source="domestic suppression")
        gs.update_stability(8)
        gs.update_approval(-5)
        messages.append("🔒 Domestic suppression: +8% stability, -5% approval, -$2B personal")
        print(f"  [BRIGADE] Domestic Suppression: -$2B personal (pw now ${gs.personal_wealth:.1f}B)")
    elif op == 3:
        # Foreign Influence Ops — costs personal wealth, flat +5 relations
        target = body.target_npc
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target NPC '{target}'")
        if gs.personal_wealth < 1.5:
            raise HTTPException(status_code=400, detail="Need $1.5B personal wealth for foreign influence op")
        gs.update_personal_wealth(-1.5, source="foreign influence op")
        gs.update_relations(target, 5, flat=True, source="foreign influence op")
        # Session 6 Phase 8: Foreign Influence generates +10 heat
        _old_heat = gs.detection_heat
        gs.detection_heat = min(100, gs.detection_heat + 10)
        messages.append(f"🕵️ Foreign influence op targeting {target.upper()}: +5 relations, -$1.5B personal, +10 heat")
        print(f"  [HEAT] Foreign influence op: +10 heat ({_old_heat} -> {gs.detection_heat})")
    elif op == 4:
        # Covert Security — costs personal wealth (Intelligence-gated)
        if gs.personal_wealth < 2.5:
            raise HTTPException(status_code=400, detail="Need $2.5B personal wealth for covert security")
        gs.update_personal_wealth(-2.5, source="covert security")
        gs.detection_heat = max(0, gs.detection_heat - 10)
        gs.update_stability(3)
        messages.append("🖤 Covert security: -10 detection heat, +3% stability, -$2.5B personal")
    elif op == 5:
        # Black Operation — requires Intelligence >= 6 (Session 6: was Security)
        intelligence_level = axes.get('intelligence', 0)
        if intelligence_level < 6:
            raise HTTPException(status_code=400, detail="Intelligence axis must be >= 6 for black operations")
        if gs.budget < 4.0:
            raise HTTPException(status_code=400, detail="Need $4B for black operation")
        gs.update_budget(-4.0)
        gs.update_stability(5)
        gs.update_relations('usa', -3)
        gs.update_relations('eu', -3)
        messages.append("🖤 Black operation deployed: +5% stability, USA -3, EU -3, -$4B")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid operation {op}")

    # Log operation
    ops_log = getattr(gs, 'brigade_operations_this_turn', [])
    ops_log.append({'operation': op, 'target': body.target_npc, 'turn': gs.current_turn})
    gs.brigade_operations_this_turn = ops_log

    _save_gs(session_id, gs)

    return {
        "success": True,
        "messages": messages,
        "game_state": gs.serialize(),
    }


# ── fixes_13 Fix 26: Black Operations Suite (Security 6) ────────────────────

# Per-NPC blackmail concession flavors
_BLACKMAIL_CONCESSIONS = {
    'usa': {
        'effect': 'Sanctions suspended 2 turns',
        'flavor': 'The photographs from Geneva remain private. For now.',
    },
    'eu': {
        'effect': 'Conditionality review dropped 2 turns',
        'flavor': 'The Luxembourg arrangements stay between us.',
    },
    'arabia': {
        'effect': 'Oil price locked at current floor 3 turns',
        'flavor': "Riyadh's Tehran communications stay unshared.",
    },
    'dprg': {
        'effect': "Reveals one other NPC's actual negotiating floor",
        'flavor': "Pyongyang's Singapore accounts stay off Western radar.",
    },
}


@app.post("/game/{session_id}/black_operation")
def post_black_operation(session_id: str, body: BlackOpRequest):
    """
    fixes_13 Fix 26 / Session 6: Black Operations suite at Intelligence 6 (was Security 6).
    Operations: fabricate_crisis, reputation_laundering, blackmail, false_flag, political_sabotage
    All cost personal wealth and have detection risk.
    One per turn limit (shared with brigade ops).
    """
    gs = _load_gs(session_id)
    axes = getattr(gs, 'cabinet_axes', {})
    intelligence_level = axes.get('intelligence', 0)

    if intelligence_level < 6:
        raise HTTPException(status_code=400, detail="Intelligence axis must be >= 6 for black operations")

    # Enforce one-per-turn shared with brigade operations
    ops_this_turn = getattr(gs, 'brigade_operations_this_turn', [])
    current_turn_ops = [o for o in ops_this_turn if o.get('turn') == gs.current_turn and o.get('operation', 0) != 0]
    if current_turn_ops:
        raise HTTPException(status_code=400, detail="Only one operation can be deployed per turn (shared with brigade ops)")

    op = body.operation
    target = body.target_npc.lower() if body.target_npc else ''
    messages = []
    _detected = False

    if op == 'fabricate_crisis':
        # $4B personal, target NPC, suspend their pressure 2 turns, 35% detection
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target NPC '{target}'")
        if gs.personal_wealth < 4.0:
            raise HTTPException(status_code=400, detail="Need $4B personal wealth")
        gs.update_personal_wealth(-4.0, source=f"black op: fabricate crisis ({target})")
        # Suspend pressure events for target — stored as a list of {npc, turns_remaining}
        _suspensions = getattr(gs, 'pressure_suspensions', [])
        _suspensions.append({'npc': target, 'turns_remaining': 2})
        gs.pressure_suspensions = _suspensions
        messages.append(f"🖤 FABRICATE CRISIS — {target.upper()}'s pressure events suspended 2 turns (-$4B personal)")
        _detected = random.random() < 0.35
        print(f"  [api] Fix 26: Fabricate Crisis targeting {target}, detection roll: {'DETECTED' if _detected else 'clean'}")

    elif op == 'reputation_laundering':
        # $3B personal, heat -15, no detection risk
        if gs.personal_wealth < 3.0:
            raise HTTPException(status_code=400, detail="Need $3B personal wealth")
        gs.update_personal_wealth(-3.0, source="black op: reputation laundering")
        gs.detection_heat = max(0, gs.detection_heat - 15)
        messages.append(f"🖤 REPUTATION LAUNDERING — Heat -15 (now {gs.detection_heat}%), -$3B personal")
        # No detection risk (technically legal)
        print(f"  [api] Fix 26: Reputation Laundering — heat now {gs.detection_heat}")

    elif op == 'blackmail':
        # $5B personal, requires Tier 3 intel, NPC -5 permanent, 40% detection
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target NPC '{target}'")
        if gs.personal_wealth < 5.0:
            raise HTTPException(status_code=400, detail="Need $5B personal wealth")
        # fixes_16 Fix B: Read from npc_intel_tiers (persisted), not intel_cache
        _tier = getattr(gs, 'npc_intel_tiers', {}).get(target, 0)
        if _tier < 3:
            raise HTTPException(status_code=400, detail=f"Insufficient intel on {target.upper()}: tier {_tier}, need 3")
        # Check one-use-per-NPC-per-game
        _blackmail_used = getattr(gs, 'blackmail_ops_used', [])
        if target in _blackmail_used:
            raise HTTPException(status_code=400, detail=f"Blackmail already used against {target.upper()} this game")
        gs.update_personal_wealth(-5.0, source=f"black op: blackmail ({target})")
        gs.update_relations(target, -5, source="blackmail operation")
        _blackmail_used.append(target)
        gs.blackmail_ops_used = _blackmail_used
        _concession = _BLACKMAIL_CONCESSIONS.get(target, {})
        messages.append(f"🖤 BLACKMAIL — {target.upper()}: {_concession.get('effect', 'Concession extracted')}")
        messages.append(f'  "{_concession.get("flavor", "The matter is resolved.")}"')
        messages.append(f"  {target.upper()} relations -5 permanently, -$5B personal")
        # Apply concession effect
        if target == 'usa':
            _suspensions = getattr(gs, 'pressure_suspensions', [])
            _suspensions.append({'npc': 'usa', 'turns_remaining': 2, 'type': 'sanctions_immunity'})
            gs.pressure_suspensions = _suspensions
        elif target == 'eu':
            _suspensions = getattr(gs, 'pressure_suspensions', [])
            _suspensions.append({'npc': 'eu', 'turns_remaining': 2, 'type': 'conditionality_immunity'})
            gs.pressure_suspensions = _suspensions
        elif target == 'arabia':
            _suspensions = getattr(gs, 'pressure_suspensions', [])
            _suspensions.append({'npc': 'arabia', 'turns_remaining': 3, 'type': 'oil_price_lock'})
            gs.pressure_suspensions = _suspensions
        elif target == 'dprg':
            # Reveal another NPC's negotiating floor — pick random non-DPRG NPC
            _others = [n for n in ('usa', 'arabia', 'eu') if n != target]
            _reveal_npc = random.choice(_others)
            messages.append(f"  ⚡ Ji-won reveals: {_reveal_npc.upper()}'s floor is approximately {gs.relations.get(_reveal_npc, 50) - 15} relations")
        _detected = random.random() < 0.40
        print(f"  [api] Fix 26: Blackmail {target}, detection: {'DETECTED' if _detected else 'clean'}")

    elif op == 'false_flag':
        # $6B personal, blame another NPC, bilateral -10, 50% detection
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target NPC '{target}'")
        if gs.personal_wealth < 6.0:
            raise HTTPException(status_code=400, detail="Need $6B personal wealth")
        gs.update_personal_wealth(-6.0, source=f"black op: false flag ({target})")
        # Damage bilateral score — target NPC's relations with another NPC
        # Pick the NPC with best relations to the target as the "victim"
        _other_npcs = [n for n in ALL_NPCS if n != target]
        _victim = random.choice(_other_npcs)
        # Bilateral damage is stored for NPC-to-NPC processing
        _bilateral_damages = getattr(gs, 'bilateral_damages', [])
        _bilateral_damages.append({'from': target, 'to': _victim, 'amount': -10, 'turn': gs.current_turn})
        gs.bilateral_damages = _bilateral_damages
        messages.append(f"🖤 FALSE FLAG — Hostile action blamed on {target.upper()}")
        messages.append(f"  {target.upper()} ↔ {_victim.upper()} bilateral relations -10, -$6B personal")
        _detected = random.random() < 0.50
        print(f"  [api] Fix 26: False Flag targeting {target}, blamed on {_victim}, detection: {'DETECTED' if _detected else 'clean'}")

    elif op == 'political_sabotage':
        # $3B personal, suspend pressure 1 turn, reduce cross-NPC penalty 50% next turn, 25% detection
        # Requires Tier 2 intel
        if target not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid target NPC '{target}'")
        if gs.personal_wealth < 3.0:
            raise HTTPException(status_code=400, detail="Need $3B personal wealth")
        # fixes_16 Fix B: Read from npc_intel_tiers (persisted), not intel_cache
        _tier = getattr(gs, 'npc_intel_tiers', {}).get(target, 0)
        if _tier < 2:
            raise HTTPException(status_code=400, detail=f"Requires Tier 2 intel on {target.upper()}: tier {_tier}, need 2")
        gs.update_personal_wealth(-3.0, source=f"black op: political sabotage ({target})")
        _suspensions = getattr(gs, 'pressure_suspensions', [])
        _suspensions.append({'npc': target, 'turns_remaining': 1})
        gs.pressure_suspensions = _suspensions
        # Cross-NPC penalty reduction stored for next turn processing
        _penalty_reductions = getattr(gs, 'cross_npc_penalty_reductions', [])
        _penalty_reductions.append({'npc': target, 'reduction': 0.5, 'turns_remaining': 1})
        gs.cross_npc_penalty_reductions = _penalty_reductions
        messages.append(f"🖤 POLITICAL SABOTAGE — {target.upper()} pressure suspended 1 turn, cross-NPC penalty -50%, -$3B personal")
        _detected = random.random() < 0.25
        print(f"  [api] Fix 26: Political Sabotage targeting {target}, detection: {'DETECTED' if _detected else 'clean'}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid black operation '{op}'")

    # Detection consequences — OPSEC failure, not heat
    if _detected:
        messages.append("⚠️ OPSEC FAILURE — Operation detected by foreign intelligence")
        gs.update_relations('usa', -15, source="black op OPSEC failure")
        gs.update_relations('eu', -15, source="black op OPSEC failure")
        gs.update_relations('dprg', 2, source="black op OPSEC (approves)")
        gs.update_relations('arabia', 2, source="black op OPSEC (approves)")
        messages.append("  USA -15, EU -15, DPRG +2, Arabia +2")
        # If false flag detected: both targeted NPCs -20
        if op == 'false_flag':
            gs.update_relations(target, -20, source="false flag exposed")
            _victim_npc = None
            for dmg in getattr(gs, 'bilateral_damages', []):
                if dmg.get('turn') == gs.current_turn and dmg.get('from') == target:
                    _victim_npc = dmg.get('to')
                    break
            if _victim_npc:
                gs.update_relations(_victim_npc, -20, source="false flag exposed")
            messages.append(f"  FALSE FLAG EXPOSED: {target.upper()} -20, {(_victim_npc or '?').upper()} -20")

    # Log operation
    ops_log = getattr(gs, 'brigade_operations_this_turn', [])
    ops_log.append({'operation': f'black_{op}', 'target': target, 'turn': gs.current_turn, 'detected': _detected})
    gs.brigade_operations_this_turn = ops_log

    _save_gs(session_id, gs)
    print(f"  [api] Fix 26: Black Op '{op}' completed, target={target}, detected={_detected}")
    return {
        "success": True,
        "messages": messages,
        "detected": _detected,
        "game_state": gs.serialize(),
    }


# ── Session 7A Step 5: Era System — Close Era + Historian ───────────────────

@app.post("/game/{session_id}/close_era")
async def close_era(session_id: str, user: User = Depends(get_optional_user)):
    """
    Session 7A Step 5: Close the current era.
    Increments era, resets era tracking fields, logs transition,
    generates historian summary for the closed era.
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    if not getattr(gs, 'pending_era_transition', False):
        raise HTTPException(status_code=400, detail="No era transition pending")

    _old_era = gs.current_era
    _trigger = getattr(gs, 'last_threshold_event', None) or 'time_backstop'
    _days_in_era = gs.current_day - getattr(gs, 'era_start_day', 1)

    # Build transition record
    _transition_record = {
        "era": _old_era,
        "closed_on_day": gs.current_day,
        "trigger": _trigger,
        "days_in_era": _days_in_era,
        "regime_at_close": gs.state_identity.get('regime_type', 'Managed Democracy'),
        "stability_at_close": gs.stability,
        "approval_at_close": gs.public_approval,
        "budget_at_close": round(gs.budget, 1),
        "relations_at_close": dict(gs.relations),
    }

    # Append to era_transitions log
    if not hasattr(gs, 'era_transitions') or gs.era_transitions is None:
        gs.era_transitions = []
    gs.era_transitions.append(_transition_record)

    # Generate historian summary for the closed era
    _historian_text = None
    try:
        _historian_text = npc_engine.generate_historian_summary(gs)
        print(f"  [ERA] Historian summary for era {_old_era}: '{(_historian_text or '')[:60]}...'")
    except Exception as _hist_err:
        print(f"  [ERA] Historian summary error (non-fatal): {_hist_err}")
        _historian_text = f"Era {_old_era} has concluded. The record speaks for itself."

    _transition_record['historian_summary'] = _historian_text

    # Advance to next era
    gs.current_era += 1
    gs.era_start_day = gs.current_day
    gs.pending_era_transition = False
    gs.last_threshold_event = None
    gs.last_threshold_day = 0

    print(f"[ERA] Era {_old_era} closed on day {gs.current_day}, trigger={_trigger}, days_in_era={_days_in_era}")

    _save_gs(session_id, gs)

    return {
        "success": True,
        "closed_era": _old_era,
        "new_era": gs.current_era,
        "trigger": _trigger,
        "days_in_era": _days_in_era,
        "historian_summary": _historian_text,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/historian_summary")
async def get_historian_summary(session_id: str, user: User = Depends(get_optional_user)):
    """
    Session 7A Step 5: On-demand historian assessment (mid-game).
    Generates a historian write-up for the current state without closing an era.
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    print(f"[ERA] Historian assessment requested for era {gs.current_era}, day {gs.current_day}")

    _historian_text = None
    try:
        _historian_text = npc_engine.generate_historian_summary(gs)
        print(f"  [ERA] On-demand historian: '{(_historian_text or '')[:60]}...'")
    except Exception as _hist_err:
        print(f"  [ERA] On-demand historian error (non-fatal): {_hist_err}")
        _historian_text = "The historian is currently unavailable. The record remains unwritten."

    return {
        "success": True,
        "historian_summary": _historian_text,
        "era": gs.current_era,
        "day": gs.current_day,
    }


# ── Test Account Endpoints ──────────────────────────────────────────────────
# All require is_test=True on the authenticated user. Return 403 otherwise.

def _require_test_user(user: User):
    """Guard: raise 403 if the authenticated user is not a test account."""
    if not user.is_test:
        raise HTTPException(status_code=403, detail="Test account required")


@app.post("/test/reset")
async def test_reset(user: User = Depends(get_current_user)):
    """Delete all GameState records for the authenticated test user."""
    _require_test_user(user)
    from sqlmodel import select as _select
    with SQLModelSession(accounts_engine) as db_session:
        stmt = _select(GameStatePersisted).where(GameStatePersisted.user_id == user.id)
        records = db_session.exec(stmt).all()
        count = len(records)
        for r in records:
            db_session.delete(r)
        db_session.commit()
    print(f"[TEST] Game state reset for user: {user.id}")
    return {"success": True, "deleted": count}


class SetStateRequest(BaseModel):
    state_data: dict


@app.post("/test/set_state")
async def test_set_state(user: User = Depends(get_current_user), body: SetStateRequest = ...):
    """Accept a full game state JSON blob. Creates or replaces the current GameState for the user."""
    _require_test_user(user)
    from datetime import datetime as _dt, timezone as _tz
    from sqlmodel import select as _select
    import uuid as _uuid

    with SQLModelSession(accounts_engine) as db_session:
        # Find existing game for this user, or create new
        stmt = _select(GameStatePersisted).where(
            GameStatePersisted.user_id == user.id
        ).order_by(GameStatePersisted.updated_at.desc())  # type: ignore
        existing = db_session.exec(stmt).first()

        now = _dt.now(_tz.utc)
        if existing:
            existing.state_data = body.state_data
            existing.updated_at = now
            db_session.add(existing)
            game_id = str(existing.id)
        else:
            new_record = GameStatePersisted(
                id=_uuid.uuid4(),
                user_id=user.id,
                state_data=body.state_data,
                created_at=now,
                updated_at=now,
            )
            db_session.add(new_record)
            game_id = str(new_record.id)
        db_session.commit()

    # Also create/update in legacy game_sessions table so game routes work
    from db import save_session, create_session as _create_session
    if not save_session(game_id, body.state_data):
        _create_session(body.state_data, player_id=str(user.id), session_id=game_id)

    print(f"[TEST] State injected for user: {user.id}")
    return {"success": True, "game_id": game_id}


@app.get("/test/snapshots")
async def test_list_snapshots(user: User = Depends(get_current_user)):
    """Return a list of available seeded snapshots from the /snapshots directory."""
    _require_test_user(user)
    import json as _json
    snapshots_dir = Path(__file__).parent / "snapshots"
    result = []
    if snapshots_dir.is_dir():
        for f in sorted(snapshots_dir.glob("*.json")):
            try:
                data = _json.loads(f.read_text())
                result.append({
                    "name": f.stem,
                    "turn": data.get("current_turn", "?"),
                    "description": _snapshot_description(f.stem),
                })
            except Exception:
                result.append({"name": f.stem, "turn": "?", "description": "Parse error"})
    return {"snapshots": result}


def _snapshot_description(name: str) -> str:
    """Human-readable description for known snapshot names."""
    descs = {
        "turn_1_clean": "Fresh game state, all defaults",
        "turn_8_high_axes": "Turn 8, all cabinet axes at 10, EU 80, Arabia 50",
        "sanctions_active": "Turn 5, USA sanctions tier 2, budget $8B",
    }
    return descs.get(name, name)


@app.get("/test/snapshot/{name}")
async def test_get_snapshot(name: str, user: User = Depends(get_current_user)):
    """Return the full state_data for a named snapshot."""
    _require_test_user(user)
    import json as _json
    snapshot_path = Path(__file__).parent / "snapshots" / f"{name}.json"
    if not snapshot_path.is_file():
        raise HTTPException(status_code=404, detail=f"Snapshot '{name}' not found")
    data = _json.loads(snapshot_path.read_text())
    return {"name": name, "state_data": data}


# ── 8C: Exile Sequence Endpoints ──────────────────────────────────────────────

EXILE_REACH_OUT_COSTS = {
    'usa': 1.0, 'eu': 0.8, 'arabia': 1.2, 'dprg': 1.5, 'russia': 1.0, 'china': 0.8,
}

EXILE_REACH_OUT_GAINS = {
    'usa': 5, 'eu': 5, 'arabia': 4, 'dprg': 3, 'russia': 4, 'china': 5,
}

BACKING_EXCLUSIONS = {
    'usa': ['dprg', 'russia'],
    'eu': ['dprg'],
    'arabia': ['eu'],
    'dprg': ['usa', 'eu'],
    'russia': ['usa', 'eu'],
    'china': ['usa'],
}

BACKING_PRICES = {
    'usa': 'Western alignment commitment. No DPRG deals in the next era.',
    'eu': 'Reform commitments in writing. Press freedom, judicial independence.',
    'arabia': 'Energy partnership restored at current terms. Exclusive supply.',
    'dprg': 'Isolation from Western security frameworks. No USA military deals.',
    'russia': 'Energy exclusivity. No NATO-adjacent arrangements.',
    'china': 'Infrastructure partnership. Long-term development framework. No conditions on governance.',
}


class ExileActionRequest(BaseModel):
    action: str  # 'wait' | 'reach_out' | 'covert_op' | 'accept_backing'
    target_npc: str | None = None
    op_type: str | None = None  # for covert_op: 'maintenance' | 'destabilize' | 'return_prep'


# ═══════════════════════════════════════════════════════════════════════════
# 8D: The Leak — Scripted Branching Crisis
# ═══════════════════════════════════════════════════════════════════════════

def _build_leak_consequence_summary(choice, gs):
    """Returns a dict of what changed for display in the crisis resolution panel."""
    summaries = {
        'deny': {
            'usa': -5, 'dprg': +5, 'stability': -8,
            'note': 'Scandal risk: 40% chance of heat +15 tomorrow'
        },
        'admit': {
            'usa': +10, 'dprg': -15, 'approval': -10,
            'note': 'DPRG will respond coldly. USA credibility restored.'
        },
        'blame': {
            'stability': -5,
            'note': 'Scapegoat used. This option is now permanently unavailable.'
        },
        'jiwon': {
            'personal_wealth': -3.0, 'dprg': +3,
            'note': 'Ji-won suppressed the story. He remembers the favor.'
        }
    }
    return summaries.get(choice, {})


@app.post("/game/{session_id}/crisis/the_leak")
def resolve_the_leak(session_id: str, body: dict):
    """8D: Resolve The Leak crisis — player picks one of four options."""
    gs = _load_gs(session_id)

    if not getattr(gs, 'the_leak_fired', False):
        raise HTTPException(status_code=400, detail="The Leak has not triggered")
    if getattr(gs, 'the_leak_resolved', False):
        raise HTTPException(status_code=400, detail="The Leak already resolved")

    choice = body.get('choice')
    if choice not in ('deny', 'admit', 'blame', 'jiwon'):
        raise HTTPException(status_code=400, detail="Invalid choice")

    # Check scapegoat availability
    if choice == 'blame' and getattr(gs, 'scapegoat_used', False):
        raise HTTPException(status_code=400, detail="Scapegoat already used")

    # Apply immediate consequences
    if choice == 'deny':
        gs.relations['usa'] = max(0, gs.relations.get('usa', 0) - 5)
        gs.relations['dprg'] = min(100, gs.relations.get('dprg', 0) + 5)
        gs.stability = max(0, gs.stability - 8)

    elif choice == 'admit':
        gs.relations['usa'] = min(100, gs.relations.get('usa', 0) + 10)
        gs.relations['dprg'] = max(0, gs.relations.get('dprg', 0) - 15)
        gs.public_approval = max(0, gs.public_approval - 10)

    elif choice == 'blame':
        gs.stability = max(0, gs.stability - 5)
        gs.scapegoat_used = True

    elif choice == 'jiwon':
        if gs.personal_wealth < 3.0:
            raise HTTPException(status_code=400, detail="Insufficient personal wealth")
        gs.personal_wealth -= 3.0
        gs.relations['dprg'] = min(100, gs.relations.get('dprg', 0) + 3)

    # Generate historian narrative
    result_text = None
    try:
        from npc_engine import generate_leak_resolution_narrative
        result_text = generate_leak_resolution_narrative(gs, choice)
    except Exception as _narr_err:
        print(f"[leak] Narrative generation error: {_narr_err}")
        result_text = "The crisis passed into the historical record."

    gs.the_leak_resolved = True
    gs.the_leak_choice = choice

    _save_gs(session_id, gs)

    print(f"[leak] Resolved: choice={choice}")

    return {
        "result": result_text,
        "choice": choice,
        "consequences": _build_leak_consequence_summary(choice, gs),
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/exile_action")
def post_exile_action(session_id: str, body: ExileActionRequest):
    """8C: Handle exile-mode actions (wait, reach out, covert op, accept backing)."""
    gs = _load_gs(session_id)

    if not getattr(gs, 'in_exile', False):
        raise HTTPException(status_code=400, detail="Not in exile")

    messages = []
    npc_dialogue = None  # Fix E: AI-generated exile dialogue (populated by reach_out)
    action = body.action

    if action == 'wait':
        # End the exile day without spending anything extra
        messages.append("You wait. Let conditions shift. The world keeps moving without you.")

    elif action == 'reach_out':
        npc = body.target_npc
        if npc not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid NPC: {npc}")

        # Cost calculation
        base_cost = EXILE_REACH_OUT_COSTS.get(npc, 1.0)
        # Voted-out discount: 20% cheaper
        if gs.exile_trigger == 'voted_out':
            base_cost *= 0.8
        # Higher cost if relations are low
        rel = gs.relations.get(npc, 30)
        if rel < 20:
            base_cost *= 1.5

        if gs.personal_wealth < base_cost:
            raise HTTPException(status_code=400, detail=f"Insufficient funds: need ${base_cost:.1f}B, have ${gs.personal_wealth:.1f}B")

        gs.personal_wealth = round(gs.personal_wealth - base_cost, 2)
        gain = EXILE_REACH_OUT_GAINS.get(npc, 4)
        old_rel = gs.relations.get(npc, 30)
        gs.relations[npc] = min(100, old_rel + gain)
        messages.append(f"Reached out to {ALL_NPC_LABELS.get(npc, npc)}. Relations: {old_rel} -> {gs.relations[npc]} (+{gain}). Cost: ${base_cost:.1f}B.")
        messages.append("Operating without state leverage. Progress is slower.")
        print(f"[exile] Reach out: npc={npc} cost=${base_cost:.1f}B gain=+{gain} rel={old_rel}->{gs.relations[npc]}")

        # Fix E: Generate AI prose dialogue for exile reach-out
        try:
            from npc_engine import generate_exile_contact_response
            npc_dialogue = generate_exile_contact_response(gs, npc)
        except Exception as _e:
            print(f"[exile] Exile dialogue generation failed: {_e}")
            npc_dialogue = None

    elif action == 'covert_op':
        if not gs.exile_apparatus_survived:
            print(f"[exile] Covert op blocked: apparatus not survived")
            raise HTTPException(status_code=400, detail="Shadow apparatus compromised -- covert operations unavailable")

        op_type = body.op_type or 'maintenance'
        risk_mod = gs.exile_apparatus_detection_risk_modifier

        if op_type == 'maintenance':
            # Low risk, prevents relations drift for 3 days
            cost = 0.8
            base_risk = 0.10
            if gs.personal_wealth < cost:
                raise HTTPException(status_code=400, detail=f"Insufficient funds: need ${cost}B")
            gs.personal_wealth = round(gs.personal_wealth - cost, 2)
            effective_risk = min(1.0, base_risk * risk_mod)
            detected = random.random() < effective_risk
            if detected:
                messages.append(f"DETECTED. Your covert maintenance operation was intercepted. Relations may suffer.")
                # Penalty: random NPC relation drop
                _target = random.choice(list(ALL_NPCS))
                gs.relations[_target] = max(0, gs.relations.get(_target, 30) - 5)
                messages.append(f"{ALL_NPC_LABELS.get(_target, _target)} relations -5 (detection fallout).")
            else:
                messages.append("Network maintenance successful. NPC relation drift paused for 3 days.")
            print(f"[exile] Covert op executed: maintenance, cost: $0.8B, apparatus: survived={gs.exile_apparatus_survived}")

        elif op_type == 'destabilize':
            cost = 1.5
            base_risk = 0.30
            if gs.personal_wealth < cost:
                raise HTTPException(status_code=400, detail=f"Insufficient funds: need ${cost}B")
            gs.personal_wealth = round(gs.personal_wealth - cost, 2)
            effective_risk = min(1.0, base_risk * risk_mod)
            detected = random.random() < effective_risk
            if detected:
                messages.append("DETECTED. The destabilization attempt was traced back to you.")
                for _n in ALL_NPCS:
                    gs.relations[_n] = max(0, gs.relations.get(_n, 30) - 3)
                messages.append("All NPC relations -3 (blown cover).")
            else:
                messages.append(f"Destabilization successful. {gs.successor_name}'s government faces new challenges.")
            print(f"[exile] Covert op executed: destabilize, cost: $1.5B, apparatus: survived={gs.exile_apparatus_survived}")

        elif op_type == 'return_prep':
            cost = 2.0
            base_risk = 0.20
            if gs.personal_wealth < cost:
                raise HTTPException(status_code=400, detail=f"Insufficient funds: need ${cost}B")
            gs.personal_wealth = round(gs.personal_wealth - cost, 2)
            effective_risk = min(1.0, base_risk * risk_mod)
            detected = random.random() < effective_risk
            target_npc = body.target_npc
            if detected:
                messages.append("DETECTED. Your return preparations were uncovered.")
                if target_npc:
                    gs.relations[target_npc] = max(0, gs.relations.get(target_npc, 30) - 5)
                    messages.append(f"{ALL_NPC_LABELS.get(target_npc, target_npc)} relations -5 (return prep detected).")
            else:
                npc_label = ALL_NPC_LABELS.get(target_npc, 'unknown contact') if target_npc else 'general contacts'
                messages.append(f"Return preparation underway. Groundwork laid with {npc_label}.")
                if target_npc:
                    gs.relations[target_npc] = min(100, gs.relations.get(target_npc, 30) + 3)
                    messages.append(f"{ALL_NPC_LABELS.get(target_npc, target_npc)} relations +3 (return preparation).")
            print(f"[exile] Covert op executed: return_prep, cost: $2.0B, apparatus: survived={gs.exile_apparatus_survived}, target: {target_npc}")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid op_type: {op_type}")

    elif action == 'accept_backing':
        npc = body.target_npc
        if npc not in ALL_NPCS:
            raise HTTPException(status_code=400, detail=f"Invalid NPC: {npc}")
        if npc in (gs.backing_doors_closed or []):
            raise HTTPException(status_code=400, detail=f"Backing from {npc} is no longer available")
        if gs.exile_backing_committed:
            raise HTTPException(status_code=400, detail=f"Already committed to {gs.exile_backing} backing")

        gs.exile_backing = npc
        gs.exile_backing_committed = True

        # Close competing doors
        exclusions = BACKING_EXCLUSIONS.get(npc, [])
        gs.backing_doors_closed = list(set((gs.backing_doors_closed or []) + exclusions))

        price = BACKING_PRICES.get(npc, 'Terms to be negotiated.')
        messages.append(f"Backing accepted from {ALL_NPC_LABELS.get(npc, npc)}.")
        messages.append(f"Price: {price}")
        if exclusions:
            closed_labels = [ALL_NPC_LABELS.get(x, x) for x in exclusions]
            messages.append(f"Doors closed: {', '.join(closed_labels)}")
        print(f'[exile] Backing accepted: {npc} -- closing doors: {exclusions}')

    else:
        raise HTTPException(status_code=400, detail=f"Unknown exile action: {action}")

    # Run exile EOD processing
    eod_messages = process_exile_eod(gs)
    messages.extend(eod_messages)

    # Advance day
    gs.current_day += 1

    # 9C: Check permanent exile after EOD processing
    if action == 'wait':
        # Only check permanent exile on WAIT — other endings should not fire mid-exile
        _pe_attempts = getattr(gs, 'return_attempts', 0)
        _pe_progress = getattr(gs, 'return_progress', 0)
        print(f"  [9C] WAIT permanent_exile check: attempts={_pe_attempts} progress={_pe_progress} fired={False}")
        if _pe_attempts >= 3 and _pe_progress < 30 and gs.in_exile:
            # Apply safety defaults for cheat-injected exile state
            if not getattr(gs, 'exile_entry_relations', None):
                gs.exile_entry_relations = dict(gs.relations)
            if not getattr(gs, 'exile_trigger', None):
                gs.exile_trigger = 'revolution'
            if not getattr(gs, 'successor_name', None):
                gs.successor_name = 'the successor government'
            gs.ending_triggered = "permanent_exile"
            gs.in_exile = False
            print(f"  [9C] WAIT permanent_exile check: attempts={_pe_attempts} progress={_pe_progress} fired={True}")
            messages.append("All paths home are closed. You will die in exile.")
            _save_gs(session_id, gs)
            response = {
                "messages": messages,
                "game_state": gs.serialize(),
                "status": "permanent_exile",
                "ending": "permanent_exile",
            }
            if npc_dialogue is not None:
                response["npc_dialogue"] = npc_dialogue
            return response
    else:
        _pe_over, _pe_result, _pe_msg = check_game_over(gs)
        if _pe_result == 'permanent_exile':
            messages.append(_pe_msg)

    _save_gs(session_id, gs)

    # Fix E: Include npc_dialogue if generated during reach_out
    _exile_status = "ended" if getattr(gs, 'ending_triggered', None) == "permanent_exile" else "exile"
    response = {
        "messages": messages,
        "game_state": gs.serialize(),
        "status": _exile_status,
    }
    if npc_dialogue is not None:
        response["npc_dialogue"] = npc_dialogue
    return response



# ── 9A: Exile Wealth Actions Endpoint ─────────────────────────────────────────

EXILE_WEALTH_ACTIONS = {
    "propaganda_campaign": {
        "label": "Propaganda Campaign",
        "cost": 1.0,
        "progress": 8,
        "detection_risk": 0.15,
        "cooldown_days": 3,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Fund media outlets and social media campaigns against the successor regime.",
    },
    "bribe_official": {
        "label": "Bribe Official",
        "cost": 1.5,
        "progress": 10,
        "detection_risk": 0.25,
        "cooldown_days": 0,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Pay off a mid-level official for intelligence or tacit cooperation.",
    },
    "fund_protests": {
        "label": "Fund Protests",
        "cost": 2.0,
        "progress": 12,
        "detection_risk": 0.40,
        "cooldown_days": 5,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Finance opposition protests and civil unrest against the successor government.",
    },
    "stir_unrest": {
        "label": "Stir Unrest",
        "cost": 3.0,
        "progress": 18,
        "detection_risk": 0.60,
        "cooldown_days": 7,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Organize widespread destabilization. High risk, high reward.",
    },
    "general_greasing": {
        "label": "General Greasing",
        "cost": 1.5,
        "progress": 8,
        "detection_risk": 0.15,
        "cooldown_days": 4,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Spread money around. Build goodwill, buy silence, keep options open.",
    },
    "hire_fixer": {
        "label": "Hire Fixer",
        "cost": 2.5,
        "progress": 0,
        "detection_risk": 0.20,
        "cooldown_days": 0,
        "requires_faction": None,
        "requires_approval": None,
        "description": "Hire a local operative. Reduces detection risk on next action by 50%.",
    },
    "military_contact": {
        "label": "Military Contact",
        "cost": 2.0,
        "progress": 25,
        "detection_risk": 0.30,
        "cooldown_days": 0,
        "requires_faction": "military",
        "requires_approval": None,
        "description": "Reach out to sympathetic military officers. Requires military faction contact.",
    },
    "opposition_coalition": {
        "label": "Opposition Coalition",
        "cost": 0.0,
        "progress": 15,
        "detection_risk": 0.10,
        "cooldown_days": 0,
        "requires_faction": None,
        "requires_approval": 25,
        "description": "Rally opposition politicians. Free but requires domestic approval above 25.",
    },
}


class ExileWealthActionRequest(BaseModel):
    action_key: str
    target: str | None = None
    offer: str | None = None


@app.post("/game/{session_id}/exile/action")
def post_exile_wealth_action(session_id: str, req: ExileWealthActionRequest):
    """9A: Player spends personal wealth on exile actions to build return progress."""
    gs = _load_gs(session_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Session not found")
    if not gs.in_exile:
        raise HTTPException(status_code=400, detail="Not in exile")

    action_key = req.action_key
    if action_key not in EXILE_WEALTH_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action_key}")

    action = EXILE_WEALTH_ACTIONS[action_key]

    # ── Wealth check ──
    cost = action['cost']
    if cost > 0 and gs.exile_wealth_at_collapse < cost:
        raise HTTPException(
            status_code=400,
            detail="Insufficient funds",
        )

    # ── Cooldown check ──
    cooldown_until = gs.wealth_action_cooldowns.get(action_key, 0)
    if gs.exile_day < cooldown_until:
        days_left = cooldown_until - gs.exile_day
        label = action['label']
        raise HTTPException(
            status_code=400,
            detail=f"{label} on cooldown for {days_left} more day(s)",
        )

    # ── Faction requirement check ──
    if action['requires_faction']:
        faction = action['requires_faction']
        fc = gs.faction_contacts.get(faction, {})
        if not fc.get('unlocked', False):
            raise HTTPException(
                status_code=400,
                detail=f"Requires {faction} faction contact. Not yet unlocked.",
            )

    # ── Approval requirement check ──
    if action['requires_approval'] is not None:
        req_approval = action['requires_approval']
        if gs.approval < req_approval:
            raise HTTPException(
                status_code=400,
                detail=f"Requires approval >= {req_approval}. Current: {gs.approval}",
            )

    # ── Execute action ──
    _wb = gs.personal_wealth
    gs.exile_wealth_at_collapse -= action['cost']
    gs.personal_wealth = gs.exile_wealth_at_collapse  # FIX A: sync personal_wealth
    print(f"[FIXA] wealth deducted action={action_key} before={_wb:.1f} cost={action['cost']} after={gs.personal_wealth:.1f}")

    # Hire fixer special: unlocks a faction channel for the target
    if action_key == "hire_fixer":
        target = req.target
        if not target:
            raise HTTPException(status_code=400, detail="hire_fixer requires a target faction")
        fc = gs.faction_contacts.get(target, {})
        if fc.get('unlocked', False):
            raise HTTPException(status_code=400, detail=f"Channel already open for {target}")
        gs.faction_contacts[target] = {"unlocked": True, "committed": False, "offer": ""}
        print(f"[FIX1] fixer hired, target={target} unlocked")
    else:
        # Apply progress
        gs.return_progress += action['progress']
        # FIX 2: opposition_coalition also boosts approval
        if action_key == "opposition_coalition":
            gs.approval = min(100, gs.approval + 5)
            print(f"[FIX2] opposition_coalition approval={gs.approval}")

    # ── Set cooldown ──
    if action['cooldown_days'] > 0:
        gs.wealth_action_cooldowns[action_key] = gs.exile_day + action['cooldown_days']

    # ── Detection roll ──
    import random
    risk = action['detection_risk']
    # Apparatus modifier
    risk *= (1.0 + gs.exile_apparatus_detection_risk_modifier)

    detected = random.random() < risk
    detection_msg = None
    successor_reaction = None

    if detected:
        detection_event = {
            'day': gs.exile_day,
            'action': action_key,
            'risk_was': round(risk, 2),
        }
        gs.detection_events.append(detection_event)

        # Successor reacts to detection
        successor_reaction = _successor_detection_reaction(gs, action_key)
        action_label_lower = action['label'].lower()
        detection_msg = f"Your {action_label_lower} was detected by the successor government."
        if successor_reaction:
            detection_msg += f" {successor_reaction}"

    # ── Log action ──
    progress_gained = action['progress'] if action_key != "hire_fixer" else 0
    action_log_entry = {
        'day': gs.exile_day,
        'action': action_key,
        'cost': action['cost'],
        'progress_gained': progress_gained,
        'detected': detected,
    }
    gs.exile_actions_log.append(action_log_entry)

    print(f"[9A] exile action={action_key} progress={gs.return_progress:.0f} detected={detected}")

    _save_gs(session_id, gs)

    return {
        "action": action_key,
        "label": action['label'],
        "cost": action['cost'],
        "progress_gained": progress_gained,
        "new_progress": gs.return_progress,
        "new_wealth": gs.exile_wealth_at_collapse,
        "detected": detected,
        "detection_message": detection_msg,
        "successor_reaction": successor_reaction,
        "fixer_hired_target": req.target if action_key == "hire_fixer" else None,
        "game_state": gs.serialize(),
    }


def _successor_detection_reaction(gs, action_key):
    """9A: Generate successor government reaction when an exile action is detected."""
    hostility = gs.successor_hostility
    archetype = gs.successor_archetype or "Unknown"

    # Severity based on action type
    severity = {
        "propaganda_campaign": 1,
        "bribe_official": 2,
        "fund_protests": 3,
        "stir_unrest": 4,
        "general_greasing": 1,
        "hire_fixer": 1,
        "military_contact": 3,
        "opposition_coalition": 2,
    }.get(action_key, 1)

    combined = hostility + severity

    if combined <= 2:
        # Mild: public statement
        return f"The {archetype} government issued a statement condemning foreign interference."
    elif combined <= 4:
        # Moderate: diplomatic pressure
        gs.return_threshold = min(gs.return_threshold + 5, 150)
        return f"The {archetype} government lodged a formal protest, tightening security. Return threshold increased."
    elif combined <= 6:
        # Severe: active countermeasures
        gs.return_threshold = min(gs.return_threshold + 10, 150)
        gs.exile_apparatus_detection_risk_modifier += 0.1
        return f"The {archetype} government launched an investigation. Detection risk permanently increased."
    else:
        # Extreme: arrest warrant, asset seizure
        gs.return_threshold = min(gs.return_threshold + 15, 150)
        gs.exile_apparatus_detection_risk_modifier += 0.15
        seized = min(gs.exile_wealth_at_collapse * 0.1, 2.0)
        gs.exile_wealth_at_collapse = max(0, gs.exile_wealth_at_collapse - seized)
        gs.personal_wealth = gs.exile_wealth_at_collapse  # FIX 1: sync personal_wealth
        seized_str = f"{seized:.1f}"
        return f"The {archetype} government seized ${seized_str}B in assets and issued an international warrant. Return threshold sharply increased."



# ── 9A: NPC Backing Tiers Endpoint ────────────────────────────────────────────

NPC_BACKING_TIERS = {
    "usa": {
        1: {
            "label": "Informal Contact",
            "price": "Verbal commitment to Western values. Non-binding.",
            "progress_bonus": 5,
            "relation_req": 20,
            "cost": 0.0,
            "flavor": "Hartwell takes your call. That alone is progress.",
        },
        2: {
            "label": "Quiet Support",
            "price": "Public statement distancing from DPRG. Media-friendly reforms.",
            "progress_bonus": 10,
            "relation_req": 35,
            "cost": 1.0,
            "flavor": "Hartwell mentions you in a press conference. 'A friend of democracy.'",
        },
        3: {
            "label": "Active Backing",
            "price": "Full Western alignment. No DPRG or Russian deals for one era.",
            "progress_bonus": 18,
            "relation_req": 50,
            "cost": 2.0,
            "flavor": "State Department issues a statement supporting your return. The machinery moves.",
        },
        4: {
            "label": "Full Sponsorship",
            "price": "Military basing rights. Trade agreement on US terms.",
            "progress_bonus": 25,
            "relation_req": 65,
            "cost": 3.0,
            "flavor": "Hartwell assigns a team. Logistics, media strategy, diplomatic pressure. This is real.",
        },
        5: {
            "label": "Regime Change Support",
            "price": "Permanent Western alignment. Security framework integration. No independent foreign policy.",
            "progress_bonus": 35,
            "relation_req": 75,
            "cost": 5.0,
            "flavor": "The full weight of American power bends toward your restoration. Everything has a price.",
        },
    },
    "eu": {
        1: {
            "label": "Humanitarian Concern",
            "price": "Human rights commitments. Allow EU observers.",
            "progress_bonus": 4,
            "relation_req": 20,
            "cost": 0.0,
            "flavor": "Marsha expresses 'deep concern' about the situation in Europa.",
        },
        2: {
            "label": "Diplomatic Channel",
            "price": "Press freedom guarantees. Judicial independence roadmap.",
            "progress_bonus": 8,
            "relation_req": 30,
            "cost": 0.5,
            "flavor": "The EU opens a formal channel. Slow, but legitimate.",
        },
        3: {
            "label": "Sanctions Pressure",
            "price": "Reform commitments in writing. Anti-corruption framework.",
            "progress_bonus": 15,
            "relation_req": 45,
            "cost": 1.5,
            "flavor": "Brussels sanctions the successor regime. Marsha calls it 'a matter of principle.'",
        },
        4: {
            "label": "Full EU Support",
            "price": "Democratic transition plan. EU-supervised elections within one era.",
            "progress_bonus": 22,
            "relation_req": 60,
            "cost": 2.5,
            "flavor": "The EU Parliament passes a resolution. Your return becomes European policy.",
        },
        5: {
            "label": "EU Integration Path",
            "price": "Full democratic reform package. EU accession roadmap. Sovereignty concessions.",
            "progress_bonus": 30,
            "relation_req": 70,
            "cost": 4.0,
            "flavor": "Marsha offers the ultimate prize: a path to EU membership. The cost is everything you built.",
        },
    },
    "arabia": {
        1: {
            "label": "Hospitality",
            "price": "Goodwill. Nothing formal.",
            "progress_bonus": 3,
            "relation_req": 15,
            "cost": 0.0,
            "flavor": "Sadam offers comfortable exile. A palace, not a prison.",
        },
        2: {
            "label": "Financial Support",
            "price": "Energy partnership discussions reopened.",
            "progress_bonus": 8,
            "relation_req": 30,
            "cost": 0.0,
            "flavor": "Sadam sends funds. No questions asked. That is the arrangement.",
        },
        3: {
            "label": "Active Investment",
            "price": "Exclusive energy partnership. Below-market rates.",
            "progress_bonus": 14,
            "relation_req": 40,
            "cost": 0.0,
            "flavor": "Arabian sovereign wealth flows toward your return. Sadam sees opportunity.",
        },
        4: {
            "label": "Strategic Partnership",
            "price": "Long-term energy exclusivity. Joint military exercises. No EU energy deals.",
            "progress_bonus": 20,
            "relation_req": 55,
            "cost": 0.0,
            "flavor": "Sadam commits publicly. His credibility is now tied to your return.",
        },
        5: {
            "label": "Full Patronage",
            "price": "Permanent energy client. Military access. Economic dependency framework.",
            "progress_bonus": 28,
            "relation_req": 65,
            "cost": 0.0,
            "flavor": "You will return as Sadam's man in Europa. Everyone will know it. Including you.",
        },
    },
    "dprg": {
        1: {
            "label": "Quiet Acknowledgment",
            "price": "Nothing yet. Ji-won is watching.",
            "progress_bonus": 3,
            "relation_req": 25,
            "cost": 0.0,
            "flavor": "Ji-won does not refuse your message. In Pyongyang, that counts.",
        },
        2: {
            "label": "Information Sharing",
            "price": "Isolation from Western security frameworks.",
            "progress_bonus": 7,
            "relation_req": 35,
            "cost": 0.5,
            "flavor": "Ji-won sends intelligence about the successor regime. Useful, if true.",
        },
        3: {
            "label": "Material Support",
            "price": "No USA military deals. Reduce sanctions advocacy.",
            "progress_bonus": 12,
            "relation_req": 50,
            "cost": 1.0,
            "flavor": "DPRG operatives appear in Europa. Deniable. Effective.",
        },
        4: {
            "label": "Active Partnership",
            "price": "Full isolation from West. Technology sharing. Mutual defense understanding.",
            "progress_bonus": 18,
            "relation_req": 60,
            "cost": 2.0,
            "flavor": "Ji-won commits resources. The West will notice. That is the point.",
        },
        5: {
            "label": "Iron Alliance",
            "price": "Permanent alignment. Shared intelligence infrastructure. Joint weapons development.",
            "progress_bonus": 25,
            "relation_req": 70,
            "cost": 3.0,
            "flavor": "You and Ji-won are bound now. The same enemies, the same friends, the same fate.",
        },
    },
    "russia": {
        1: {
            "label": "Back Channel",
            "price": "Verbal understanding. Energy discussions.",
            "progress_bonus": 4,
            "relation_req": 20,
            "cost": 0.0,
            "flavor": "Volkov is cordial. Cautious. Calculating the angles.",
        },
        2: {
            "label": "Quiet Backing",
            "price": "Energy cooperation priority. No NATO-adjacent arrangements.",
            "progress_bonus": 9,
            "relation_req": 35,
            "cost": 0.5,
            "flavor": "Russian media begins covering your exile sympathetically. Volkov pulls strings.",
        },
        3: {
            "label": "Active Support",
            "price": "Energy exclusivity. Military hardware purchases. Media cooperation.",
            "progress_bonus": 16,
            "relation_req": 45,
            "cost": 1.5,
            "flavor": "Volkov commits logistical support. His people on the ground in Europa.",
        },
        4: {
            "label": "Strategic Alliance",
            "price": "Full energy dependency. Security framework integration. Veto Western access.",
            "progress_bonus": 22,
            "relation_req": 60,
            "cost": 2.5,
            "flavor": "Russia stakes its credibility on your return. Volkov needs you to succeed now.",
        },
        5: {
            "label": "Full Integration",
            "price": "Permanent Russian sphere. Joint military command. Energy monopoly. No Western deals.",
            "progress_bonus": 30,
            "relation_req": 70,
            "cost": 4.0,
            "flavor": "Volkov smiles. You both know what this means. Europa becomes a Russian interest.",
        },
    },
    "china": {
        1: {
            "label": "Diplomatic Interest",
            "price": "Infrastructure discussion. Non-binding.",
            "progress_bonus": 4,
            "relation_req": 15,
            "cost": 0.0,
            "flavor": "Wei listens carefully. Takes notes. Offers tea.",
        },
        2: {
            "label": "Development Partner",
            "price": "Infrastructure partnership. Chinese contractors priority.",
            "progress_bonus": 9,
            "relation_req": 30,
            "cost": 0.0,
            "flavor": "Wei proposes a development framework. Patient capital, long-term returns.",
        },
        3: {
            "label": "Strategic Investment",
            "price": "Long-term infrastructure partnership. Port access. Technology adoption.",
            "progress_bonus": 15,
            "relation_req": 45,
            "cost": 0.0,
            "flavor": "Chinese investment begins flowing. Wei thinks in decades, not days.",
        },
        4: {
            "label": "Comprehensive Partnership",
            "price": "Belt and Road integration. No conditions on governance. Long-term debt framework.",
            "progress_bonus": 22,
            "relation_req": 55,
            "cost": 0.0,
            "flavor": "Wei commits publicly. Your return becomes part of a larger plan.",
        },
        5: {
            "label": "Full Dependency",
            "price": "Complete economic integration. Technology dependency. Debt restructuring on Chinese terms.",
            "progress_bonus": 30,
            "relation_req": 65,
            "cost": 0.0,
            "flavor": "Wei smiles patiently. The infrastructure will outlast you both. That is the design.",
        },
    },
}

# 9A: NPC backing mutual exclusivity — accepting tier 3+ from one blocks these others
NPC_BACKING_EXCLUSIONS_9A = {
    "usa": ["dprg", "russia"],
    "eu": ["dprg"],
    "arabia": [],
    "dprg": ["usa", "eu"],
    "russia": ["usa", "eu"],
    "china": ["usa"],
}


class NpcBackingRequest(BaseModel):
    npc_id: str
    tier: int


@app.post("/game/{session_id}/exile/npc-backing")
def post_exile_npc_backing(session_id: str, req: NpcBackingRequest):
    """9A: Accept NPC backing at a specific tier. Higher tiers = more help, more strings."""
    gs = _load_gs(session_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Session not found")
    if not gs.in_exile:
        raise HTTPException(status_code=400, detail="Not in exile")

    npc_id = req.npc_id
    tier = req.tier

    # ── Validate NPC ──
    if npc_id not in NPC_BACKING_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid NPC: {npc_id}")

    npc_tiers = NPC_BACKING_TIERS[npc_id]

    # ── Validate tier ──
    if tier not in npc_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier {tier} for {npc_id}. Valid: 1-5")

    # FIX 4: Per-NPC tier caps
    NPC_TIER_CAPS = {"arabia": 4, "dprg": 3}
    tier_cap = NPC_TIER_CAPS.get(npc_id)
    if tier_cap is not None and tier > tier_cap:
        print(f"[FIX4] tier cap enforced npc={npc_id} tier={tier}")
        raise HTTPException(status_code=400, detail=f"Not available for this NPC")

    tier_data = npc_tiers[tier]

    # ── Check if already at this tier or higher ──
    current_tier = gs.npc_assistance_tiers.get(npc_id, 0)
    if current_tier >= tier:
        raise HTTPException(
            status_code=400,
            detail=f"Already at tier {current_tier} with {npc_id}. Cannot accept same or lower tier.",
        )

    # ── Check relation requirement ──
    relation = gs.relations.get(npc_id, 30)
    if relation < tier_data['relation_req']:
        raise HTTPException(
            status_code=400,
            detail=f"Relations with {npc_id} too low. Need {tier_data['relation_req']}, have {relation}.",
        )

    # ── Check wealth for cost ──
    if tier_data['cost'] > 0 and gs.exile_wealth_at_collapse < tier_data['cost']:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wealth. Need ${tier_data['cost']}B.",
        )

    # ── Check mutual exclusivity (tier 3+ triggers exclusions) ──
    blocked_by = []
    if tier >= 3:
        for other_npc, excluded_list in NPC_BACKING_EXCLUSIONS_9A.items():
            if npc_id in excluded_list:
                other_tier = gs.npc_assistance_tiers.get(other_npc, 0)
                if other_tier >= 3:
                    blocked_by.append(other_npc)
        # Also check if accepting THIS npc would conflict with existing high-tier partners
        exclusions = NPC_BACKING_EXCLUSIONS_9A.get(npc_id, [])
        for excluded_npc in exclusions:
            other_tier = gs.npc_assistance_tiers.get(excluded_npc, 0)
            if other_tier >= 3:
                blocked_by.append(excluded_npc)

    if blocked_by:
        blocked_labels = [ALL_NPC_LABELS.get(b, b) for b in blocked_by]
        raise HTTPException(
            status_code=400,
            detail=f"Blocked by existing tier 3+ commitment with: {', '.join(blocked_labels)}",
        )

    # ── Execute ──
    # Deduct cost
    if tier_data['cost'] > 0:
        gs.exile_wealth_at_collapse -= tier_data['cost']
        gs.personal_wealth = gs.exile_wealth_at_collapse  # FIX 1: sync personal_wealth

    # Apply progress bonus (delta only if upgrading)
    previous_bonus = 0
    if current_tier > 0:
        previous_bonus = npc_tiers[current_tier]['progress_bonus']
    delta = tier_data['progress_bonus'] - previous_bonus
    gs.return_progress += delta
    print(f"[FIX3] tier upgrade npc={npc_id} delta={delta} total_progress={gs.return_progress:.0f}")

    # Set tier
    gs.npc_assistance_tiers[npc_id] = tier

    # Update 8C backing fields for compatibility
    if tier >= 3 and not gs.exile_backing_committed:
        gs.exile_backing = npc_id
        gs.exile_backing_committed = True
        # Close competing doors (8C system)
        exclusions_8c = BACKING_EXCLUSIONS.get(npc_id, [])
        gs.backing_doors_closed = list(set((gs.backing_doors_closed or []) + exclusions_8c))

    # Log
    action_log_entry = {
        'day': gs.exile_day,
        'action': f'npc_backing_{npc_id}_tier{tier}',
        'cost': tier_data['cost'],
        'progress_gained': delta,
        'detected': False,
    }
    gs.exile_actions_log.append(action_log_entry)

    print(f"[9A] npc_backing npc={npc_id} tier={tier} progress={gs.return_progress:.0f} price={tier_data['price']}")

    _save_gs(session_id, gs)

    return {
        "npc_id": npc_id,
        "tier": tier,
        "label": tier_data['label'],
        "price": tier_data['price'],
        "flavor": tier_data['flavor'],
        "progress_bonus": tier_data['progress_bonus'],
        "cost": tier_data['cost'],
        "new_progress": gs.return_progress,
        "new_wealth": gs.exile_wealth_at_collapse,
        "current_tiers": gs.npc_assistance_tiers,
        "game_state": gs.serialize(),
    }



# ── 9A: Return Attempt Endpoint ───────────────────────────────────────────────

@app.post("/game/{session_id}/exile/attempt-return")
def post_exile_attempt_return(session_id: str):
    """9A: Attempt to return from exile. Success based on progress vs threshold."""
    gs = _load_gs(session_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Session not found")
    if not gs.in_exile:
        raise HTTPException(status_code=400, detail="Not in exile")

    # ── Max attempts check ──
    if gs.return_attempts >= 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum return attempts (3) exhausted. You must find another way.",
        )

    # ── Minimum progress check ──
    if gs.return_progress < 20:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient groundwork. Progress: {gs.return_progress:.0f}. Need at least 20 to attempt return.",
        )

    gs.return_attempts += 1

    # ── Calculate success probability ──
    # Base probability: progress / threshold, capped at 0.90
    base_prob = min(gs.return_progress / max(gs.return_threshold, 1.0), 0.90)

    # NPC backing bonus: each tier adds 2% (max across all NPCs)
    max_npc_tier = 0
    backing_npc = None
    for npc_id, tier in gs.npc_assistance_tiers.items():
        if tier > max_npc_tier:
            max_npc_tier = tier
            backing_npc = npc_id
    npc_bonus = max_npc_tier * 0.02  # Up to 10% at tier 5

    # Faction commitment bonus: each committed faction adds 3%
    faction_bonus = 0
    for faction, data in gs.faction_contacts.items():
        if isinstance(data, dict) and data.get('committed', False):
            faction_bonus += 0.03

    # Detection penalty: each detection event reduces probability by 3%
    detection_penalty = len(gs.detection_events) * 0.03

    # Successor hostility penalty: each level reduces by 3%
    hostility_penalty = gs.successor_hostility * 0.03

    # Attempt penalty: each previous failed attempt reduces by 5%
    attempt_penalty = (gs.return_attempts - 1) * 0.05

    # Final probability
    success_prob = max(0.05, min(0.90, base_prob + npc_bonus + faction_bonus - detection_penalty - hostility_penalty - attempt_penalty))

    import random
    roll = random.random()
    success = roll < success_prob

    print(f"[9A] return attempt #{gs.return_attempts}: prob={success_prob:.2f} roll={roll:.2f} success={success}")
    print(f"[9A]   base={base_prob:.2f} npc_bonus={npc_bonus:.2f} faction={faction_bonus:.2f} detection_pen={detection_penalty:.2f} hostility_pen={hostility_penalty:.2f} attempt_pen={attempt_penalty:.2f}")

    # ── Generate narrative ──
    narrative = None
    try:
        from npc_engine import generate_return_narrative
        narrative = generate_return_narrative(gs, success, backing_npc)
    except Exception as e:
        print(f"[9A] narrative generation failed: {e}")
        if success:
            narrative = "You return to Europa. The work begins again."
        else:
            narrative = "The attempt fails. You remain in exile."

    if success:
        # ── Successful return: set up restoration state ──
        gs.in_exile = False
        gs.restoration_active = True

        # Snapshot prior state for restoration tracking
        gs.prior_regime_label = getattr(gs, 'state_identity', {}).get('regime_type', 'Managed Democracy')

        # FIX 2: Set interim restoration regime label
        if hasattr(gs, 'state_identity') and isinstance(gs.state_identity, dict):
            gs.state_identity['regime_type'] = 'Restoration Government'
        print(f"[RESTORE] regime_label=Restoration Government on return (prior={gs.prior_regime_label})")

        # FIX 6: Relations reset — percentage model using exile_entry_relations
        entry_rels = getattr(gs, 'exile_entry_relations', {})
        backers = set(gs.npc_assistance_tiers.keys()) if gs.npc_assistance_tiers else set()
        if backing_npc:
            backers.add(backing_npc)
        for npc_id in gs.relations:
            entry_val = entry_rels.get(npc_id, gs.relations.get(npc_id, 30))
            if npc_id in backers:
                gs.relations[npc_id] = entry_val  # Backer keeps full exile-entry value
            else:
                gs.relations[npc_id] = max(20, int(entry_val * 0.60))
        _npc_map = {'usa': 'bill', 'eu': 'marsha', 'russia': 'volkov', 'china': 'wei', 'arabia': 'sadam', 'dprg': 'dprg'}
        _rl = gs.relations
        print(f"[FIX6] relations_reset bill={_rl.get('usa',0)} marsha={_rl.get('eu',0)} volkov={_rl.get('russia',0)} wei={_rl.get('china',0)} sadam={_rl.get('arabia',0)} dprg={_rl.get('dprg',0)}")

        # Reset some exile fields but keep logs
        gs.exile_day = 0

        # FIX 7: Economy reset on return
        gs.gdp_base = getattr(gs, 'exile_entry_gdp', 100.0) * 0.85
        gs.budget = 10.0
        gs.stability = 40
        gs.public_approval = 35
        print(f"[FIX7] economy_reset gdp={gs.gdp_base:.1f} budget=10 stability=40 approval=35")
        print(f"[RESTORE] public_approval set to {gs.public_approval} budget={gs.budget} stability={gs.stability} grace={gs.restoration_grace_days}")

        # FIX 1: Restoration grace period — 5 turns of collapse immunity
        gs.restoration_grace_days = 5
        print(f"[RESTORE] grace period set: {gs.restoration_grace_days} days")

        # FIX 8: Clear advisors on return
        gs.advisors = {}
        gs.advisor_assigned_today = []
        print(f"[FIX8] advisors cleared on return")

        # Initial restoration tallies based on backing source
        if backing_npc in ('usa', 'eu'):
            gs.restoration_democratic_tally += 2
        elif backing_npc in ('dprg', 'russia'):
            gs.restoration_authoritarian_tally += 2
        elif backing_npc in ('arabia', 'china'):
            gs.restoration_authoritarian_tally += 1

        print(f"[9A] RETURN SUCCESS: restoration_active=True, backer={backing_npc}")

    else:
        # ── Failed return: penalties ──
        # FIX 5: Additive penalty formula
        progress_penalty = 20 + (gs.return_attempts * 5)
        gs.return_progress = max(0, gs.return_progress - progress_penalty)
        print(f"[FIX5] failure penalty={progress_penalty} progress={gs.return_progress:.0f}")

        # Relations hit with all NPCs
        for npc_id in gs.relations:
            gs.relations[npc_id] = max(0, gs.relations[npc_id] - 5)

        # Successor hostility increases
        gs.successor_hostility = min(3, gs.successor_hostility + 1)

        # Return threshold increases
        gs.return_threshold = min(150, gs.return_threshold + 10)

        print(f"[9A] RETURN FAILED: attempt #{gs.return_attempts}, progress now {gs.return_progress:.0f}, threshold now {gs.return_threshold:.0f}")

    # ── Log the attempt ──
    action_log_entry = {
        'day': gs.exile_day if gs.in_exile else 0,
        'action': 'attempt_return',
        'success': success,
        'probability': round(success_prob, 3),
        'roll': round(roll, 3),
        'attempt_number': gs.return_attempts,
        'detected': False,
    }
    gs.exile_actions_log.append(action_log_entry)

    # 9C: Check permanent exile after return attempt
    _pe_over2, _pe_result2, _pe_msg2 = check_game_over(gs)

    _save_gs(session_id, gs)

    _return_response = {
        "success": success,
        "attempt_number": gs.return_attempts,
        "probability": round(success_prob, 3),
        "narrative": narrative,
        "backing_npc": backing_npc,
        "new_progress": gs.return_progress,
        "new_threshold": gs.return_threshold,
        "restoration_active": gs.restoration_active,
        "game_state": gs.serialize(),
    }
    if _pe_result2 == 'permanent_exile':
        _return_response["permanent_exile"] = True
        _return_response["permanent_exile_message"] = _pe_msg2
    return _return_response



# ── 9A: Restoration Identity Endpoint ─────────────────────────────────────────

@app.get("/game/{session_id}/restoration-status")
def get_restoration_status(session_id: str):
    """9A: Get current restoration identity formation status."""
    gs = _load_gs(session_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Session not found")

    if not gs.restoration_active:
        return {
            "restoration_active": False,
            "message": "No active restoration period.",
            "prior_regime_label": gs.prior_regime_label,
            "current_regime": getattr(gs, 'state_identity', {}).get('regime_type', 'Unknown'),
        }

    d = gs.restoration_democratic_tally
    a = gs.restoration_authoritarian_tally
    total = d + a
    net = d - a

    # Determine leaning without revealing exact numbers
    if total < 3:
        leaning = "Too early to tell"
    elif net >= 4:
        leaning = "Democratic trajectory"
    elif net >= 1:
        leaning = "Leaning democratic"
    elif net >= -1:
        leaning = "Balanced"
    elif net >= -4:
        leaning = "Leaning authoritarian"
    else:
        leaning = "Authoritarian trajectory"

    progress_to_resolution = min(total / 15.0, 1.0)

    print(f"[9A] restoration status: d={d} a={a} net={net} leaning={leaning} progress={progress_to_resolution:.0%}")

    return {
        "restoration_active": True,
        "democratic_tally": d,
        "authoritarian_tally": a,
        "leaning": leaning,
        "progress_to_resolution": round(progress_to_resolution, 2),
        "prior_regime_label": gs.prior_regime_label,
        "signals_needed": max(0, 15 - total),
        "game_state": gs.serialize(),
    }


# ── 9B: Political Biography Endpoint ─────────────────────────────────────────

@app.get("/game/{session_id}/biography")
def get_biography(session_id: str):
    """9B: Generate full political biography for a completed or in-progress game."""
    gs = _load_gs(session_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Session not found")

    print(f"[9B] /biography called session={session_id} turn={gs.current_turn} ending={getattr(gs, 'ending_triggered', 'none')}")

    from npc_engine import generate_full_biography
    result = generate_full_biography(gs)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 10C: OPERATIONS SYSTEM ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

import math as _math

# ── MILITARY ACTIONS ──────────────────────────────────────────────────────────

@app.post("/game/{session_id}/operations/force-projection")
def post_force_projection(session_id: str, body: OperationTargetRequest):
    """10C: Force Projection — military threat as negotiation tool."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    # Gate checks
    if gs.military_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Military Tier 3+")
    if getattr(gs, 'force_projection_cooldown', 0) > 0:
        raise HTTPException(status_code=400, detail=f"Force Projection on cooldown ({gs.force_projection_cooldown} days remaining)")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")

    # Apply effects
    gs.update_relations(target, -8, source="force projection")

    # Pressure ceiling modifier (+25% for 3 days)
    cooldown_days = 2 if getattr(gs, 'modernization_tranche_3', False) else 3
    _fp_mods = getattr(gs, 'force_projection_modifiers', {})
    _fp_mods[target] = {
        'ceiling_modifier': 1.25,
        'expires_day': gs.current_day + 3
    }
    gs.force_projection_modifiers = _fp_mods
    gs.force_projection_cooldown = cooldown_days
    gs.ops_legitimate_this_turn += 1

    # Log
    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'force_projection',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Force Projection: target={target}, cooldown={cooldown_days}")
    _save_gs(session_id, gs)
    return {
        "success": True,
        "target": target,
        "cooldown_days": cooldown_days,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/arms-export")
def post_arms_export(session_id: str, body: ArmsExportRequest):
    """10C: Arms Export — sell weapons to NPC for revenue and relations."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    # Gate checks
    if gs.military_tier < 2:
        raise HTTPException(status_code=400, detail="Requires Military Tier 2+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")

    # Cost
    military_cost = 3 + _math.floor(gs.military_tier / 3)
    if gs.budget < military_cost:
        raise HTTPException(status_code=400, detail=f"Need ${military_cost}B national budget")

    # Revenue
    export_value = round(2.0 * (gs.military_tier / 5 + 0.5) * (1.0 + getattr(gs, 'tech_level', 1.0) * 0.1), 1)

    # Relations bonus (diminishing returns)
    prior_sales = getattr(gs, 'arms_export_count', 0)
    relations_bonus = max(2, 8 - (prior_sales * 2))

    # Apply cost and revenue
    gs.update_budget(-military_cost)
    gs.update_budget(export_value)
    gs.update_relations(target, relations_bonus, flat=True, source="arms export")

    # Cross-NPC reactions for arms sales to adversaries
    cross_reactions = {}
    if target in ('russia', 'dprg'):
        # Bill (USA) reacts
        bill_penalty = -12 if target == 'dprg' else -8
        gs.update_relations('usa', bill_penalty, source=f"arms export to {target}")
        cross_reactions['usa'] = bill_penalty
        # Marsha (EU) reacts
        marsha_penalty = -10 if target == 'dprg' else -6
        gs.update_relations('eu', marsha_penalty, source=f"arms export to {target}")
        cross_reactions['eu'] = marsha_penalty
    elif target == 'china':
        gs.update_relations('usa', -12, source="arms export to china")
        cross_reactions['usa'] = -12
        gs.update_relations('eu', -10, source="arms export to china")
        cross_reactions['eu'] = -10

    # Track DPRG export flag
    if target == 'dprg':
        gs.arms_export_to_dprg = True

    gs.arms_export_count = prior_sales + 1
    gs.ops_legitimate_this_turn += 1

    # Log
    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'arms_export',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Arms Export: target={target}, value=${export_value}B, cost=${military_cost}B, bonus=+{relations_bonus}")
    _save_gs(session_id, gs)
    return {
        "success": True,
        "export_value": export_value,
        "cost": military_cost,
        "relations_bonus": relations_bonus,
        "cross_npc_reactions": cross_reactions,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/modernization")
def post_modernization(session_id: str, body: ModernizationRequest):
    """10C: Military Modernization — permanent upgrades in 3 tranches."""
    gs = _load_gs(session_id)
    tranche = body.tranche

    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")

    tech_level = getattr(gs, 'tech_level', 1.0)
    permanent_effects = []

    if tranche == 1:
        if tech_level < 2.0:
            raise HTTPException(status_code=400, detail="Requires Tech Level 2.0+")
        if gs.military_tier < 3:
            raise HTTPException(status_code=400, detail="Requires Military Tier 3+")
        if gs.modernization_tranche_1:
            raise HTTPException(status_code=400, detail="Tranche 1 already completed")
        if gs.budget < 5:
            raise HTTPException(status_code=400, detail="Need $5B national budget")
        gs.update_budget(-5)
        gs.modernization_tranche_1 = True
        permanent_effects.append("Military decay rate -20%")

    elif tranche == 2:
        if tech_level < 4.0:
            raise HTTPException(status_code=400, detail="Requires Tech Level 4.0+")
        if gs.military_tier < 5:
            raise HTTPException(status_code=400, detail="Requires Military Tier 5+")
        if not gs.modernization_tranche_1:
            raise HTTPException(status_code=400, detail="Must complete Tranche 1 first")
        if gs.modernization_tranche_2:
            raise HTTPException(status_code=400, detail="Tranche 2 already completed")
        if gs.budget < 8:
            raise HTTPException(status_code=400, detail="Need $8B national budget")
        gs.update_budget(-8)
        gs.modernization_tranche_2 = True
        permanent_effects.append("Intel intercept quality +15% for military targets")
        permanent_effects.append("Detection risk on covert ops -10%")

    elif tranche == 3:
        if tech_level < 6.0:
            raise HTTPException(status_code=400, detail="Requires Tech Level 6.0+")
        if gs.military_tier < 7:
            raise HTTPException(status_code=400, detail="Requires Military Tier 7+")
        if not gs.modernization_tranche_2:
            raise HTTPException(status_code=400, detail="Must complete Tranche 2 first")
        if gs.modernization_tranche_3:
            raise HTTPException(status_code=400, detail="Tranche 3 already completed")
        if gs.budget < 12:
            raise HTTPException(status_code=400, detail="Need $12B national budget")
        gs.update_budget(-12)
        gs.modernization_tranche_3 = True
        permanent_effects.append("Military tier upgrade costs -20%")
        permanent_effects.append("Force Projection cooldown reduced to 2 days")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid tranche: {tranche}")

    gs.ops_legitimate_this_turn += 1

    # Log
    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': f'modernization_t{tranche}',
                     'target': None, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Modernization Tranche {tranche}: effects={permanent_effects}")
    _save_gs(session_id, gs)
    return {
        "success": True,
        "tranche": tranche,
        "permanent_effects": permanent_effects,
        "game_state": gs.serialize(),
    }


# ── INTELLIGENCE ACTIONS ──────────────────────────────────────────────────────

@app.post("/game/{session_id}/operations/intel-sharing")
def post_intel_sharing(session_id: str, body: IntelSharingRequest):
    """10C: Intel Sharing — multi-level intelligence sharing agreements."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)
    level = body.level

    if level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Level must be 1, 2, or 3")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")

    # Level-specific gates
    _rel = gs.relations.get(target, 0)
    if level == 1:
        if gs.intelligence_tier < 2:
            raise HTTPException(status_code=400, detail="Requires Intel Tier 2+")
        if _rel < 50:
            raise HTTPException(status_code=400, detail=f"Requires 50+ relations with {target.upper()} (current: {_rel:.0f})")
    elif level == 2:
        if gs.intelligence_tier < 3:
            raise HTTPException(status_code=400, detail="Requires Intel Tier 3+")
        if _rel < 65:
            raise HTTPException(status_code=400, detail=f"Requires 65+ relations with {target.upper()} (current: {_rel:.0f})")
    elif level == 3:
        if gs.intelligence_tier < 4:
            raise HTTPException(status_code=400, detail="Requires Intel Tier 4+")
        if _rel < 75:
            raise HTTPException(status_code=400, detail=f"Requires 75+ relations with {target.upper()} (current: {_rel:.0f})")

    # Check for existing agreement
    _agreements = getattr(gs, 'intel_sharing_agreements', {})
    _existing = _agreements.get(target)
    if _existing and _existing.get('level', 0) >= level:
        raise HTTPException(status_code=400, detail=f"Already have Level {_existing['level']} agreement with {target.upper()}")

    # Relations bonus
    _bonus = {1: 8, 2: 15, 3: 20}[level]
    gs.update_relations(target, _bonus, flat=True, source=f"intel sharing L{level}")

    # Level 3 summit credibility bonus
    if level == 3:
        gs.summit_credibility = min(100, getattr(gs, 'summit_credibility', 100) + 10)

    _agreements[target] = {'level': level, 'day_started': gs.current_day}
    gs.intel_sharing_agreements = _agreements
    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': f'intel_sharing_L{level}',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Intel Sharing: target={target}, level={level}, relations_bonus=+{_bonus}")
    _save_gs(session_id, gs)
    return {"success": True, "level": level, "target": target, "relations_bonus": _bonus, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/intel-sharing/end")
def post_intel_sharing_end(session_id: str, body: IntelSharingEndRequest):
    """10C: End an intel sharing agreement."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    _agreements = getattr(gs, 'intel_sharing_agreements', {})
    if target not in _agreements:
        raise HTTPException(status_code=400, detail=f"No active intel sharing agreement with {target.upper()}")

    penalty = -25 if body.abrupt else -15
    gs.update_relations(target, penalty, source=f"intel sharing ended ({'abrupt' if body.abrupt else 'formal'})")
    del _agreements[target]
    gs.intel_sharing_agreements = _agreements

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'intel_sharing_end',
                     'target': target, 'outcome': 'abrupt' if body.abrupt else 'formal', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Intel Sharing ended: target={target}, abrupt={body.abrupt}, penalty={penalty}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "relations_penalty": penalty, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/crisis-intel-package")
def post_crisis_intel_package(session_id: str, body: CrisisIntelRequest):
    """10C: Crisis Intel Package — share intelligence with NPC in crisis."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.intelligence_tier < 2:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 2+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")

    # Check for duplicate in same era
    _ops_log = getattr(gs, 'operations_log', [])
    _current_era = getattr(gs, 'current_era', 1)
    _already = any(
        e.get('operation') == 'crisis_intel_package' and e.get('target') == target
        for e in _ops_log
        # Simple era check: we don't store era in ops_log yet, so check by day range
    )

    # Cost
    if body.fund_from == 'personal':
        if gs.personal_wealth < 1.5:
            raise HTTPException(status_code=400, detail="Need $1.5B personal wealth")
        gs.update_personal_wealth(-1.5, source="crisis intel package")
    elif body.fund_from == 'national':
        if gs.budget < 1.5:
            raise HTTPException(status_code=400, detail="Need $1.5B national budget")
        gs.update_budget(-1.5)
    else:
        raise HTTPException(status_code=400, detail="fund_from must be 'personal' or 'national'")

    gs.update_relations(target, 12, flat=True, source="crisis intel package")
    gs.ops_legitimate_this_turn += 1

    _ops_log.append({'day': gs.current_day, 'operation': 'crisis_intel_package',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Crisis Intel Package: target={target}, fund_from={body.fund_from}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "relations_bonus": 12, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/targeted-intercept")
def post_targeted_intercept(session_id: str, body: OperationTargetRequest):
    """10C: Targeted Intercept — get specific intelligence about an NPC."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.intelligence_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 3+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    _cooldown = getattr(gs, 'targeted_intercept_cooldown', 0)
    if _cooldown > 0:
        raise HTTPException(status_code=400, detail=f"Targeted Intercept on cooldown ({_cooldown} days)")
    if gs.personal_wealth < 2:
        raise HTTPException(status_code=400, detail="Need $2B personal wealth")

    gs.update_personal_wealth(-2, source="targeted intercept")

    # Generate intelligence via Haiku
    from npc_engine import generate_targeted_intercept
    intel = generate_targeted_intercept(gs, target)

    gs.targeted_intercept_cooldown = 2
    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'targeted_intercept',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Targeted Intercept: target={target}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "intel": intel, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/kompromat-start")
def post_kompromat_start(session_id: str, body: OperationTargetRequest):
    """10C: Start kompromat collection against an NPC."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.intelligence_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 3+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    if target == 'dprg':
        raise HTTPException(status_code=400, detail="No meaningful leverage exists against Ji-won")

    _active = getattr(gs, 'kompromat_collection_active', {})
    if target in _active:
        raise HTTPException(status_code=400, detail=f"Already collecting kompromat on {target.upper()}")

    _holdings = getattr(gs, 'kompromat_holdings', {})
    if target in _holdings and _holdings[target].get('active'):
        raise HTTPException(status_code=400, detail=f"Already hold active kompromat on {target.upper()}")

    if gs.personal_wealth < 1.5:
        raise HTTPException(status_code=400, detail="Need $1.5B personal wealth")

    gs.update_personal_wealth(-1.5, source=f"kompromat collection ({target})")

    _active[target] = {'day_started': gs.current_day, 'detection_risk_per_day': 0.15}
    gs.kompromat_collection_active = _active
    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'kompromat_start',
                     'target': target, 'outcome': 'in_progress', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Kompromat collection started: target={target}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "days_required": 7, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/kompromat-use")
def post_kompromat_use(session_id: str, body: KompromantUseRequest):
    """10C: Use kompromat against an NPC."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)
    action = body.action

    _holdings = getattr(gs, 'kompromat_holdings', {})
    _holding = _holdings.get(target)
    if not _holding or not _holding.get('active'):
        raise HTTPException(status_code=400, detail=f"No active kompromat on {target.upper()}")
    if _holding.get('uses_remaining', 0) <= 0 and action != 'burn':
        raise HTTPException(status_code=400, detail=f"No kompromat uses remaining on {target.upper()}")

    messages = []

    if action == 'suppress':
        # Suppress NPC pressure for 5 days
        _suspensions = getattr(gs, 'pressure_suspensions', [])
        _suspensions.append({'npc': target, 'turns_remaining': 5, 'type': 'kompromat_suppress'})
        gs.pressure_suspensions = _suspensions
        _holding['uses_remaining'] -= 1
        messages.append(f"Kompromat deployed: {target.upper()} pressure suppressed for 5 days")

    elif action == 'concession':
        # Extract one-time benefit
        _holding['uses_remaining'] -= 1
        gs.update_relations(target, 5, flat=True, source="kompromat concession")
        # Generate Haiku response
        from npc_engine import generate_targeted_intercept
        _response = generate_targeted_intercept(gs, target)
        messages.append(f"Concession extracted from {target.upper()} (under duress): +5 relations")
        messages.append(_response)

    elif action == 'burn':
        # Irreversible leak
        _holding['burned'] = True
        _holding['active'] = False
        gs.update_relations(target, -40, source="kompromat burned")
        # Target NPC's rivals get +15
        for _rival in ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']:
            if _rival != target:
                gs.update_relations(_rival, 15, flat=True, source=f"kompromat burn ({target}) — rival benefit")
        messages.append(f"KOMPROMAT BURNED: {target.upper()} relations -40 (permanent collapse)")
        messages.append("All other NPCs: +15 relations")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid kompromat action: {action}")

    _holdings[target] = _holding
    gs.kompromat_holdings = _holdings

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': f'kompromat_{action}',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Kompromat use: target={target}, action={action}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "action": action, "messages": messages, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/loyalty-assessment")
def post_loyalty_assessment(session_id: str, body: LoyaltyAssessmentRequest):
    """10C: Assess an advisor's true loyalty."""
    gs = _load_gs(session_id)
    advisor_id = body.advisor_id

    # Gate: intel_tier >= 2 OR surveillance_tier >= 3
    _surv_tier = getattr(gs, 'domestic_surveillance_tier', 0)
    if gs.intelligence_tier < 2 and _surv_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 2+ or Surveillance Tier 3+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")

    # Check advisor exists and is hired
    _advisors = getattr(gs, 'advisors', {})
    if advisor_id not in _advisors:
        raise HTTPException(status_code=400, detail=f"Advisor '{advisor_id}' not on staff")

    # Cooldown check per advisor
    _loyalty_ops = getattr(gs, 'advisor_loyalty_ops', {})
    _adv_ops = _loyalty_ops.get(advisor_id, {})

    if gs.personal_wealth < 1:
        raise HTTPException(status_code=400, detail="Need $1B personal wealth")

    gs.update_personal_wealth(-1, source=f"loyalty assessment ({advisor_id})")

    # Detection risk: 15%
    _detected = random.random() < 0.15
    if _detected:
        _advisor = _advisors[advisor_id]
        _advisor['loyalty'] = max(0, _advisor.get('loyalty', 50) - 20)
        _advisors[advisor_id] = _advisor
        gs.advisors = _advisors

    # Generate assessment
    from npc_engine import generate_loyalty_assessment
    assessment = generate_loyalty_assessment(gs, advisor_id)

    # Check intel politicization distortion
    _politicized = getattr(gs, 'intel_politicized', False)
    if _politicized and random.random() < 0.20:
        # 20% chance of distorted result — disloyal advisor gets clean result
        _advisor = _advisors.get(advisor_id, {})
        if _advisor.get('loyalty', 50) < 40:
            assessment = f"Your intelligence apparatus has compiled a profile. {_advisor.get('name', 'The advisor')}'s loyalty appears solid. No concerning indicators detected."

    _adv_ops['assessed'] = True
    _loyalty_ops[advisor_id] = _adv_ops
    gs.advisor_loyalty_ops = _loyalty_ops
    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'loyalty_assessment',
                     'target': advisor_id, 'outcome': 'detected' if _detected else 'success', 'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] Loyalty Assessment: advisor={advisor_id}, detected={_detected}")
    _save_gs(session_id, gs)
    return {
        "success": True, "advisor_id": advisor_id, "assessment": assessment,
        "detected": _detected, "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/loyalty-enforcement")
def post_loyalty_enforcement(session_id: str, body: LoyaltyEnforcementRequest):
    """10C: Coerce an advisor into loyalty."""
    gs = _load_gs(session_id)
    advisor_id = body.advisor_id

    _surv_tier = getattr(gs, 'domestic_surveillance_tier', 0)
    if _surv_tier < 5:
        raise HTTPException(status_code=400, detail="Requires Surveillance Tier 5+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")

    _advisors = getattr(gs, 'advisors', {})
    if advisor_id not in _advisors:
        raise HTTPException(status_code=400, detail=f"Advisor '{advisor_id}' not on staff")

    if gs.personal_wealth < 2:
        raise HTTPException(status_code=400, detail="Need $2B personal wealth")

    gs.update_personal_wealth(-2, source=f"loyalty enforcement ({advisor_id})")

    # Detection risk: 25%
    _detected = random.random() < 0.25
    if _detected:
        # Advisor immediately dismissed
        del _advisors[advisor_id]
        gs.advisors = _advisors
        print(f"  [10C] Loyalty Enforcement DETECTED — {advisor_id} dismissed")
        _save_gs(session_id, gs)
        return {
            "success": False, "advisor_id": advisor_id,
            "message": f"Enforcement detected! {advisor_id} has been dismissed in disgrace.",
            "detected": True, "game_state": gs.serialize(),
        }

    # Success: loyalty +15, coerced flag
    _advisor = _advisors[advisor_id]
    _advisor['loyalty'] = min(100, _advisor.get('loyalty', 50) + 15)
    _advisors[advisor_id] = _advisor
    gs.advisors = _advisors

    _loyalty_ops = getattr(gs, 'advisor_loyalty_ops', {})
    _adv_ops = _loyalty_ops.get(advisor_id, {})
    _adv_ops['coerced'] = True
    _adv_ops['coerced_day'] = gs.current_day
    _loyalty_ops[advisor_id] = _adv_ops
    gs.advisor_loyalty_ops = _loyalty_ops
    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'loyalty_enforcement',
                     'target': advisor_id, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Loyalty Enforcement: advisor={advisor_id}, loyalty +15")
    _save_gs(session_id, gs)
    return {
        "success": True, "advisor_id": advisor_id,
        "message": f"Enforcement successful. {advisor_id}'s loyalty has been... reinforced.",
        "detected": False, "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/counter-intel")
def post_counter_intel(session_id: str):
    """10C: Counter-Intelligence Sweep — reduce heat, reveal NPC ops."""
    gs = _load_gs(session_id)

    if gs.intelligence_tier < 2:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 2+")
    _cooldown = getattr(gs, 'counter_intel_cooldown', 0)
    if _cooldown > 0:
        raise HTTPException(status_code=400, detail=f"Counter-Intel on cooldown ({_cooldown} days)")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    if gs.personal_wealth < 2:
        raise HTTPException(status_code=400, detail="Need $2B personal wealth")

    gs.update_personal_wealth(-2, source="counter-intel sweep")
    gs.detection_heat = max(0, gs.detection_heat - 15)
    gs.counter_intel_cooldown = 2
    gs.ops_legitimate_this_turn += 1

    # Check for NPC operations targeting player (scan kompromat)
    _sweep_result = "No active foreign intelligence operations detected targeting Europa."
    # In future: scan for NPC covert ops. For now, generate Haiku response.
    from npc_engine import generate_targeted_intercept
    _sweep_result = f"Counter-intelligence sweep complete. Detection heat reduced to {gs.detection_heat}%."

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'counter_intel',
                     'target': None, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Counter-Intel Sweep: heat now {gs.detection_heat}")
    _save_gs(session_id, gs)
    return {
        "success": True, "heat_after": gs.detection_heat, "sweep_result": _sweep_result,
        "game_state": gs.serialize(),
    }


# ── DIPLOMATIC ACTIONS ────────────────────────────────────────────────────────

@app.post("/game/{session_id}/operations/trade-mission")
def post_trade_mission(session_id: str, body: OperationTargetRequest):
    """10C: Trade Mission — one-time relations boost with cooldown."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.diplomatic_tier < 2:
        raise HTTPException(status_code=400, detail="Requires Diplomatic Tier 2+")
    _cooldown = getattr(gs, 'trade_mission_cooldown', 0)
    if _cooldown > 0:
        raise HTTPException(status_code=400, detail=f"Trade Mission on cooldown ({_cooldown} days)")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    if gs.budget < 1.5:
        raise HTTPException(status_code=400, detail="Need $1.5B national budget")

    gs.update_budget(-1.5)
    gs.update_relations(target, 10, flat=True, source="trade mission")
    gs.trade_mission_cooldown = 3
    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'trade_mission',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Trade Mission: target={target}, relations +10")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "relations_bonus": 10, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/diplomatic-pressure")
def post_diplomatic_pressure(session_id: str, body: OperationTargetRequest):
    """10C: Diplomatic Pressure — relations boost (migrated from Foreign Influence Op)."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.diplomatic_tier < 2:
        raise HTTPException(status_code=400, detail="Requires Diplomatic Tier 2+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    if gs.personal_wealth < 1.5:
        raise HTTPException(status_code=400, detail="Need $1.5B personal wealth")

    gs.update_personal_wealth(-1.5, source="diplomatic pressure")
    gs.update_relations(target, 5, flat=True, source="diplomatic pressure")
    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'diplomatic_pressure',
                     'target': target, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Diplomatic Pressure: target={target}, relations +5")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "relations_bonus": 5, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/opposition-funding")
def post_opposition_funding(session_id: str, body: OperationTargetRequest):
    """10C: Opposition Funding — destabilize target NPC with detection risk."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.diplomatic_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Diplomatic Tier 3+")
    if not check_ops_cap(gs, "legitimate"):
        raise HTTPException(status_code=400, detail="Legitimate operations cap reached (1 per turn)")
    if gs.personal_wealth < 3:
        raise HTTPException(status_code=400, detail="Need $3B personal wealth")

    gs.update_personal_wealth(-3, source=f"opposition funding ({target})")

    # Side effect: target feels pressure even if not detected
    gs.update_relations(target, -5, source="opposition funding side effect")

    # Detection: 35%
    _detected = random.random() < 0.35
    if _detected:
        gs.update_relations(target, -20, source="opposition funding detected")

    gs.ops_legitimate_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'opposition_funding',
                     'target': target, 'outcome': 'detected' if _detected else 'success',
                     'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] Opposition Funding: target={target}, detected={_detected}")
    _save_gs(session_id, gs)
    return {
        "success": True, "target": target, "detected": _detected,
        "message": f"Opposition funding {'DETECTED — {target.upper()} treats as hostile act (-20 relations)' if _detected else 'deployed covertly'}",
        "game_state": gs.serialize(),
    }


# ── SHADOW OPERATIONS ─────────────────────────────────────────────────────────

@app.post("/game/{session_id}/operations/political-sabotage")
def post_political_sabotage(session_id: str, body: OperationTargetRequest):
    """10C: Political Sabotage — suspend NPC pressure + cross-NPC penalty reduction."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    _surv_tier = getattr(gs, 'domestic_surveillance_tier', 0)
    if _surv_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Surveillance Tier 3+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 3:
        raise HTTPException(status_code=400, detail="Need $3B personal wealth")

    gs.update_personal_wealth(-3, source=f"political sabotage ({target})")

    # Suspend pressure 1 turn
    _suspensions = getattr(gs, 'pressure_suspensions', [])
    _suspensions.append({'npc': target, 'turns_remaining': 1, 'type': 'political_sabotage'})
    gs.pressure_suspensions = _suspensions

    # Cross-NPC penalty -50% for 1 turn
    _reductions = getattr(gs, 'cross_npc_penalty_reductions', [])
    _reductions.append({'npc': target, 'reduction': 0.5, 'turns_remaining': 1})
    gs.cross_npc_penalty_reductions = _reductions

    # Detection: 25%
    _detected = random.random() < 0.25
    if _detected:
        gs.update_relations(target, -10, source="political sabotage detected")

    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'political_sabotage',
                     'target': target, 'outcome': 'detected' if _detected else 'success', 'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] Political Sabotage: target={target}, detected={_detected}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "detected": _detected, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/reputation-laundering")
def post_reputation_laundering(session_id: str):
    """10C: Reputation Laundering — reduce detection heat with no risk."""
    gs = _load_gs(session_id)

    _ext_tier = getattr(gs, 'extraction_tier', 0)
    if _ext_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Extraction Tier 3+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 3:
        raise HTTPException(status_code=400, detail="Need $3B personal wealth")

    gs.update_personal_wealth(-3, source="reputation laundering")
    gs.detection_heat = max(0, gs.detection_heat - 15)
    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'reputation_laundering',
                     'target': None, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Reputation Laundering: heat now {gs.detection_heat}")
    _save_gs(session_id, gs)
    return {"success": True, "heat_after": gs.detection_heat, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/fabricate-crisis")
def post_fabricate_crisis(session_id: str, body: OperationTargetRequest):
    """10C: Fabricate Crisis — suspend NPC pressure 2 turns."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    _surv_tier = getattr(gs, 'domestic_surveillance_tier', 0)
    if _surv_tier < 4:
        raise HTTPException(status_code=400, detail="Requires Surveillance Tier 4+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 4:
        raise HTTPException(status_code=400, detail="Need $4B personal wealth")

    gs.update_personal_wealth(-4, source=f"fabricate crisis ({target})")

    _suspensions = getattr(gs, 'pressure_suspensions', [])
    _suspensions.append({'npc': target, 'turns_remaining': 2, 'type': 'fabricated_crisis'})
    gs.pressure_suspensions = _suspensions

    _detected = random.random() < 0.35
    if _detected:
        gs.update_relations(target, -15, source="fabricated crisis detected")

    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'fabricate_crisis',
                     'target': target, 'outcome': 'detected' if _detected else 'success', 'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] Fabricate Crisis: target={target}, detected={_detected}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "detected": _detected, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/blackmail")
def post_blackmail_10c(session_id: str, body: OperationTargetRequest):
    """10C: Blackmail — extract one-time concession from NPC."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)

    if gs.intelligence_tier < 3:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 3+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 5:
        raise HTTPException(status_code=400, detail="Need $5B personal wealth")

    gs.update_personal_wealth(-5, source=f"blackmail ({target})")

    # Generate coerced compliance response
    from npc_engine import generate_targeted_intercept
    _response = generate_targeted_intercept(gs, target)

    _detected = random.random() < 0.40
    if _detected:
        gs.update_relations(target, -5, source="blackmail detected (permanent)")

    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'blackmail',
                     'target': target, 'outcome': 'detected' if _detected else 'success', 'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] Blackmail: target={target}, detected={_detected}")
    _save_gs(session_id, gs)
    return {
        "success": True, "target": target, "detected": _detected,
        "intel": _response, "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/false-flag")
def post_false_flag(session_id: str, body: FalseFlagRequest):
    """10C: False Flag — damage relations between two NPCs."""
    gs = _load_gs(session_id)
    target = _normalize_npc(body.target_npc)
    blame = _normalize_npc(body.blame_npc)

    if target == blame:
        raise HTTPException(status_code=400, detail="Target and blame NPCs must be different")

    _surv_tier = getattr(gs, 'domestic_surveillance_tier', 0)
    if _surv_tier < 5:
        raise HTTPException(status_code=400, detail="Requires Surveillance Tier 5+")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 6:
        raise HTTPException(status_code=400, detail="Need $6B personal wealth")

    gs.update_personal_wealth(-6, source=f"false flag ({target} blamed on {blame})")

    # Damage bilateral relations between the two NPCs
    _bilateral = getattr(gs, 'npc_relations', {})
    _pair1 = f"{target}_{blame}" if f"{target}_{blame}" in _bilateral else f"{blame}_{target}"
    if _pair1 in _bilateral:
        _bilateral[_pair1] = max(0, _bilateral[_pair1] - 10)
    gs.npc_relations = _bilateral

    _detected = random.random() < 0.50
    if _detected:
        gs.update_relations(target, -20, source="false flag detected")
        gs.update_relations(blame, -20, source="false flag detected")

    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'false_flag',
                     'target': f"{target}/{blame}", 'outcome': 'detected' if _detected else 'success', 'detected': _detected})
    gs.operations_log = _ops_log

    print(f"  [10C] False Flag: target={target}, blame={blame}, detected={_detected}")
    _save_gs(session_id, gs)
    return {"success": True, "target": target, "blame": blame, "detected": _detected, "game_state": gs.serialize()}


@app.post("/game/{session_id}/operations/journalist-elimination")
def post_journalist_elimination(session_id: str):
    """10C: Journalist Elimination — one-time, always discovered (delayed 3-10 days)."""
    gs = _load_gs(session_id)

    _media_tier = getattr(gs, 'media_tier', 0)
    _judicial_tier = getattr(gs, 'judicial_tier', 0)
    if _media_tier < 7:
        raise HTTPException(status_code=400, detail="Requires Media Tier 7+")
    if _judicial_tier < 5:
        raise HTTPException(status_code=400, detail="Requires Judicial Tier 5+")
    if not getattr(gs, 'journalist_elimination_available', True):
        raise HTTPException(status_code=400, detail="Journalist elimination already used this game")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")
    if gs.personal_wealth < 4:
        raise HTTPException(status_code=400, detail="Need $4B personal wealth")

    gs.update_personal_wealth(-4, source="journalist elimination")

    gs.journalist_elimination_available = False
    gs.action_journalists_liquidated = True
    gs.journalist_elimination_day = gs.current_day
    gs.journalist_elimination_discovery_day = gs.current_day + random.randint(3, 10)
    gs.ops_shadow_this_turn += 1

    # Immediate effects: stability/approval decay slowed (stored as pressure suspension)
    _suspensions = getattr(gs, 'pressure_suspensions', [])
    _suspensions.append({'npc': '_system_stability_slow', 'turns_remaining': 3, 'type': 'journalist_elimination'})
    _suspensions.append({'npc': '_system_approval_slow', 'turns_remaining': 3, 'type': 'journalist_elimination'})
    gs.pressure_suspensions = _suspensions

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'journalist_elimination',
                     'target': None, 'outcome': 'pending_discovery', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Journalist Elimination: discovery scheduled for day {gs.journalist_elimination_discovery_day}")
    _save_gs(session_id, gs)
    return {
        "success": True,
        "message": "The matter has been handled. Stability and approval decay slowed for 3 days.",
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/operations/asset-exfiltration")
def post_asset_exfiltration(session_id: str):
    """10C: Asset Exfiltration — recover personal wealth from frozen accounts."""
    gs = _load_gs(session_id)

    if gs.intelligence_tier < 4:
        raise HTTPException(status_code=400, detail="Requires Intel Tier 4+")
    _exile = getattr(gs, 'in_exile', False) or getattr(gs, 'exile_active', False)
    if not _exile and gs.personal_wealth >= 5.0:
        raise HTTPException(status_code=400, detail="Asset exfiltration only available when in exile or personal wealth < $5B")
    if not check_ops_cap(gs, "shadow"):
        raise HTTPException(status_code=400, detail="Shadow operations cap reached (1 per turn)")

    _recovery = round(2.0 + (gs.intelligence_tier - 4) * 0.75, 1)
    gs.update_personal_wealth(_recovery, source="asset exfiltration")
    gs.ops_shadow_this_turn += 1

    _ops_log = getattr(gs, 'operations_log', [])
    _ops_log.append({'day': gs.current_day, 'operation': 'asset_exfiltration',
                     'target': None, 'outcome': 'success', 'detected': False})
    gs.operations_log = _ops_log

    print(f"  [10C] Asset Exfiltration: recovered ${_recovery}B")
    _save_gs(session_id, gs)
    return {"success": True, "recovered": _recovery, "game_state": gs.serialize()}


# ── 10B-1: Daily Briefing Endpoints ───────────────────────────────────────

@app.post("/game/{session_id}/briefing/generate-events")
async def generate_briefing_events(session_id: str, user: User = Depends(get_optional_user)):
    """
    Generates daily events if not already generated today.
    Idempotent — returns existing events if already generated.
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    if gs.day_events_generated:
        return {
            "events": gs.daily_events,
            "already_generated": True,
            "game_state": gs.serialize(),
        }

    import gm_engine
    import asyncio
    events = await asyncio.to_thread(gm_engine.generate_daily_events, gs)

    gs.daily_events = events
    gs.day_events_generated = True
    _save_gs(session_id, gs)

    return {
        "events": events,
        "already_generated": False,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/briefing/resolve-event")
async def resolve_event(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """Marks a world event as resolved with the player's choice."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    event_id = body.get("event_id")
    resolution = body.get("resolution")

    if not event_id or not resolution:
        raise HTTPException(status_code=400, detail="event_id and resolution required")

    gs = _load_gs(session_id)

    # Find and resolve event
    target_event = None
    for evt in gs.daily_events:
        if evt.get("id") == event_id:
            target_event = evt
            break

    if not target_event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    if target_event.get("resolved"):
        return {
            "event": target_event,
            "events_resolved": gs.events_resolved_today,
            "events_required": gs.events_required_today,
            "can_end_day": gs.events_resolved_today >= gs.events_required_today,
            "already_resolved": True,
        }

    target_event["resolved"] = True
    target_event["resolution"] = resolution

    if target_event.get("required"):
        gs.events_resolved_today += 1

    can_end_day = gs.events_resolved_today >= gs.events_required_today

    # 10B-2: Generate and apply resolution consequences
    import asyncio
    from npc_engine import generate_event_resolution_consequences
    consequences = await asyncio.to_thread(
        generate_event_resolution_consequences, gs, target_event, resolution
    )

    # Apply NPC relation deltas
    rels = gs.relations or {}
    for npc_id, delta in consequences.get("npc_reactions", {}).items():
        if npc_id in rels:
            rels[npc_id] = max(0, min(100, rels[npc_id] + delta))
    gs.relations = rels

    # Apply stability delta
    stab_delta = consequences.get("stability_delta", 0)
    if stab_delta:
        gs.stability = max(0, min(100, (gs.stability or 50) + stab_delta))

    # Apply budget delta
    budget_delta = consequences.get("budget_delta", 0)
    if budget_delta:
        gs.budget = round((gs.budget or 50) + budget_delta, 1)

    target_event["consequences"] = consequences

    _save_gs(session_id, gs)

    print(f"  [10B-2] Event {event_id} resolved: {resolution}. "
          f"Consequences: {consequences.get('interpretation', 'N/A')}. "
          f"Progress: {gs.events_resolved_today}/{gs.events_required_today}")

    return {
        "event": target_event,
        "events_resolved": gs.events_resolved_today,
        "events_required": gs.events_required_today,
        "can_end_day": can_end_day,
        "consequences": consequences,
        "game_state": gs.serialize(),
    }


@app.get("/game/{session_id}/briefing/day-status")
async def get_day_status(session_id: str, user: User = Depends(get_optional_user)):
    """Returns current day briefing status."""
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    return {
        "events_resolved": gs.events_resolved_today,
        "events_required": gs.events_required_today,
        "can_end_day": gs.events_resolved_today >= gs.events_required_today,
        "events": gs.daily_events,
        "day": getattr(gs, 'current_turn', 1),
        "era": getattr(gs, 'current_era', 1),
        "day_events_generated": gs.day_events_generated,
        "morning_briefing_read": gs.morning_briefing_read,
        "communique_days_without_response": gs.communique_days_without_response,
        "deals_today": getattr(gs, 'deals_today', []),
    }


@app.post("/game/{session_id}/briefing/morning")
async def get_morning_briefing(session_id: str, user: User = Depends(get_optional_user)):
    """
    Returns Advisory Council morning briefing.
    Chief of Staff (Mike Sorel) always speaks; hired advisors add domain views.
    """
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    from npc_engine import generate_advisor_morning_briefing
    import asyncio
    briefings = await asyncio.to_thread(generate_advisor_morning_briefing, gs)

    # Mark Chief of Staff intro done after Day 1
    if not getattr(gs, 'chief_of_staff_intro_done', False):
        gs_fresh = _load_gs(session_id)
        gs_fresh.chief_of_staff_intro_done = True
        _save_gs(session_id, gs_fresh)

    # Build advisor briefing list from gs.advisors (keyed by archetype)
    advisor_briefings = []
    for archetype, advisor in (gs.advisors or {}).items():
        advisor_briefings.append({
            'id': advisor.get('id', archetype),
            'name': advisor.get('name', ''),
            'role': archetype,
            'label': advisor.get('label', archetype.replace('_', ' ').title()),
            'icon': advisor.get('icon', '\U0001f464'),
            'text': briefings.get(archetype),
        })

    print(f"[MORNING] endpoint returning: "
          f"advisors={len(advisor_briefings)} "
          f"intro_done={getattr(gs, 'chief_of_staff_intro_done', False)}")

    return {
        "chief_of_staff": {
            "name": "Mikhail 'Mike' Sorel",
            "role": "chief_of_staff",
            "label": "Chief of Staff",
            "icon": "\U0001f9ed",
            "text": briefings.get("chief_of_staff"),
        },
        "advisor_briefings": advisor_briefings,
        "intro_done": getattr(gs, 'chief_of_staff_intro_done', False),
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/briefing/event-dialogue")
async def get_event_dialogue(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """10B-2: Generates NPC communiqués specific to a world event.
    Called when player enters an event. Cached per event_id."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    event_id = body.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id required")

    gs = _load_gs(session_id)

    # Debug: log what events exist
    stored_ids = [evt.get("id") for evt in getattr(gs, 'daily_events', [])]
    print(f"  [10B-2] event-dialogue: requested={event_id} stored_ids={stored_ids} "
          f"day_events_generated={getattr(gs, 'day_events_generated', False)} "
          f"num_events={len(getattr(gs, 'daily_events', []))}")

    # Check cache
    event_dialogues = getattr(gs, 'event_dialogues', {})
    if event_id in event_dialogues:
        return {"dialogues": event_dialogues[event_id], "cached": True}

    # Find event — first try exact match, then try matching by any stored event
    target_event = None
    for evt in gs.daily_events:
        if evt.get("id") == event_id:
            target_event = evt
            break
    if not target_event:
        # If event not found but events exist, the frontend may have stale IDs
        # from before generate-events saved. Log and return helpful error.
        print(f"  [10B-2] EVENT NOT FOUND: requested={event_id} but stored events are {stored_ids}")
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found. Stored event IDs: {stored_ids}")

    import asyncio
    from npc_engine import generate_event_dialogue, _client as _npc_client
    print(f"  [10B-2] Event dialogue request: event_id={event_id} "
          f"applicable_npcs={target_event.get('applicable_npcs', [])} "
          f"_client_exists={_npc_client is not None} "
          f"api_key_set={bool(os.getenv('ANTHROPIC_API_KEY'))}")
    dialogues = await asyncio.to_thread(generate_event_dialogue, gs, target_event)

    # Cache in game state — reload to avoid overwriting concurrent changes
    fresh_gs = _load_gs(session_id)
    if not hasattr(fresh_gs, 'event_dialogues') or not isinstance(fresh_gs.event_dialogues, dict):
        fresh_gs.event_dialogues = {}
    fresh_gs.event_dialogues[event_id] = dialogues
    _save_gs(session_id, fresh_gs)

    print(f"  [10B-2] Event dialogue for {event_id}: {len(dialogues)} NPCs "
          f"applicable={target_event.get('applicable_npcs', [])} "
          f"npc_ids={[d.get('npc_id') for d in dialogues]}")
    return {"dialogues": dialogues, "cached": False}


@app.post("/game/{session_id}/briefing/advisor-event-analysis")
async def get_advisor_event_analysis(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """10B-2: Generates advisor analyses for a specific world event.
    Uses the advisors assigned today."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    event_id = body.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id required")

    gs = _load_gs(session_id)

    # Find event
    target_event = None
    for evt in gs.daily_events:
        if evt.get("id") == event_id:
            target_event = evt
            break
    if not target_event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    assigned = getattr(gs, 'advisor_assigned_today', [])
    if not assigned:
        return {"analyses": [], "message": "No advisors assigned today"}

    import asyncio
    from npc_engine import generate_advisor_event_analysis
    analyses = await asyncio.to_thread(generate_advisor_event_analysis, gs, target_event)

    return {"analyses": analyses}


@app.post("/game/{session_id}/briefing/declaration")
async def issue_declaration(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """10B-2: Player issues a public declaration.
    GM interprets intent and generates relational consequences."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    declaration_text = body.get("declaration_text", "").strip()
    if not declaration_text:
        raise HTTPException(status_code=400, detail="declaration_text required")

    gs = _load_gs(session_id)

    declarations_available = getattr(gs, 'declarations_available', 0)
    declaration_used_today = getattr(gs, 'declaration_used_today', False)

    if declarations_available < 1:
        raise HTTPException(status_code=400, detail="Declarations not yet available")
    if declaration_used_today:
        raise HTTPException(status_code=400, detail="Declaration already issued today")

    import asyncio
    from npc_engine import generate_declaration_consequences
    consequences = await asyncio.to_thread(generate_declaration_consequences, gs, declaration_text)

    # Apply NPC reaction deltas
    for npc_id, delta in consequences.get("npc_reactions", {}).items():
        if npc_id in gs.relations:
            gs.relations[npc_id] = max(0, min(100, gs.relations[npc_id] + delta))

    # Apply soft power delta
    sp_delta = consequences.get("soft_power_delta", 0)
    if hasattr(gs, 'soft_power_score'):
        gs.soft_power_score = max(0, min(100, gs.soft_power_score + sp_delta))

    # Generate world event if flagged
    if consequences.get("generates_world_event") and consequences.get("world_event_hint"):
        import random, string
        new_event = {
            "id": "evt_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6)),
            "title": "Response to Declaration",
            "summary": consequences["world_event_hint"],
            "severity": "moderate",
            "category": "diplomatic",
            "applicable_npcs": [npc for npc, d in consequences.get("npc_reactions", {}).items() if abs(d) >= 5],
            "required": False,
            "resolved": False,
            "resolution": None,
            "escalated_from_communique": False,
            "era": getattr(gs, 'current_era', 1),
            "day": getattr(gs, 'current_turn', 1),
        }
        gs.daily_events.append(new_event)

    # Mark declaration used
    gs.declaration_used_today = True
    gs.todays_declaration = declaration_text

    # Store in history
    if not hasattr(gs, 'declaration_history') or not isinstance(gs.declaration_history, list):
        gs.declaration_history = []
    gs.declaration_history.append({
        "day": getattr(gs, 'current_turn', 1),
        "era": getattr(gs, 'current_era', 1),
        "text": declaration_text,
        "consequences": consequences,
    })

    _save_gs(session_id, gs)

    print(f"  [10B-2] Declaration issued: {consequences.get('interpretation', 'noted')}")
    return {
        "consequences": consequences,
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/intel/get-npc-intel")
async def get_npc_intel(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """10B-2: Runs an intelligence intercept on a specific NPC.
    Costs personal_wealth. Has detection risk."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    target_npc = body.get("target_npc")
    if not target_npc:
        raise HTTPException(status_code=400, detail="target_npc required")

    gs = _load_gs(session_id)

    intel_tier = getattr(gs, 'intelligence_tier', 0)
    if intel_tier < 1:
        raise HTTPException(status_code=400, detail="Intel tier too low — requires Intel Tier 1")

    # 10B-3: Cooldown — one intel op per NPC per day
    _ops_today = getattr(gs, 'intel_ops_today', [])
    if any(op.get("target") == target_npc for op in _ops_today):
        raise HTTPException(status_code=400, detail="Intel already gathered on this target today.")

    INTEL_COST = 1.5
    if (gs.budget or 0) < INTEL_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient budget (need ${INTEL_COST}B)")

    # Deduct cost from national budget — intel is a state function
    gs.budget = round((gs.budget or 0) - INTEL_COST, 1)

    # Detection roll: 10% base
    import random
    detected = random.random() < 0.10

    if detected and target_npc in gs.relations:
        gs.relations[target_npc] = max(0, gs.relations[target_npc] - 5)
        print(f"  [10B-2] Intel detected by {target_npc}! Relations -5")

    # Track intel ops
    if not hasattr(gs, 'intel_ops_today') or not isinstance(gs.intel_ops_today, list):
        gs.intel_ops_today = []
    gs.intel_ops_today.append({"target": target_npc, "detected": detected})

    # Generate intel
    import asyncio
    from npc_engine import generate_targeted_intercept
    intel_text = await asyncio.to_thread(generate_targeted_intercept, gs, target_npc)

    _save_gs(session_id, gs)

    return {
        "intel_text": intel_text,
        "detected": detected,
        "cost": INTEL_COST,
        "remaining_wealth": round(gs.personal_wealth, 1),
        "game_state": gs.serialize(),
    }


@app.post("/game/{session_id}/briefing/cables")
async def get_diplomatic_cables(session_id: str, user: User = Depends(get_optional_user)):
    """10B-2: Generate or return cached diplomatic cables for all NPCs."""
    _verify_game_ownership(session_id, user)
    gs = _load_gs(session_id)

    if getattr(gs, 'cables_generated_today', False) and getattr(gs, 'diplomatic_cables', {}):
        return {"cables": gs.diplomatic_cables, "cached": True}

    import asyncio
    from npc_engine import generate_diplomatic_cables
    cables = await asyncio.to_thread(generate_diplomatic_cables, gs)

    # Reload from DB before saving to avoid overwriting concurrent changes
    # (e.g., generate-events may have saved daily_events while we were generating)
    fresh_gs = _load_gs(session_id)
    fresh_gs.diplomatic_cables = cables
    fresh_gs.cables_generated_today = True
    _save_gs(session_id, fresh_gs)

    return {"cables": cables, "cached": False}


@app.post("/game/{session_id}/diplomacy/get-cable")
async def get_single_cable(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """Request a diplomatic briefing on a single NPC. Costs $0.3B budget."""
    _verify_game_ownership(session_id, user)
    body = await request.json()
    npc_id = body.get("npc_id", "").lower()
    if not npc_id:
        raise HTTPException(status_code=400, detail="npc_id required")

    gs = _load_gs(session_id)

    BRIEFING_COST = 0.3
    _was_incoming = (getattr(gs, 'diplomatic_cable_types', {}) or {}).get(npc_id) == "incoming"

    if not _was_incoming and (gs.budget or 0) < BRIEFING_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient budget (need ${BRIEFING_COST}B)")

    print(f"[CABLE] {npc_id} type={'incoming' if _was_incoming else 'requested'} "
          f"cost={'waived' if _was_incoming else '$0.3B'}")

    # Check if already have a cable for this NPC today
    existing = (getattr(gs, 'diplomatic_cables', {}) or {}).get(npc_id)
    if existing:
        return {"cable_text": existing, "cached": True, "cost": 0}

    # Generate single cable
    import asyncio
    from npc_engine import generate_single_cable
    cable_text = await asyncio.to_thread(generate_single_cable, gs, npc_id)

    # Reload-and-patch to avoid race conditions
    gs_fresh = _load_gs(session_id)
    if not _was_incoming:
        gs_fresh.budget = round((gs_fresh.budget or 0) - BRIEFING_COST, 1)
    if not hasattr(gs_fresh, 'diplomatic_cables') or not gs_fresh.diplomatic_cables:
        gs_fresh.diplomatic_cables = {}
    gs_fresh.diplomatic_cables[npc_id] = cable_text
    if not hasattr(gs_fresh, 'diplomatic_cable_types'):
        gs_fresh.diplomatic_cable_types = {}
    if not _was_incoming:
        gs_fresh.diplomatic_cable_types[npc_id] = "requested"
    _save_gs(session_id, gs_fresh)

    print(f"  [10B-3] Briefing {'incoming' if _was_incoming else 'requested'} for {npc_id}: "
          f"{'$0 (incoming)' if _was_incoming else f'-${BRIEFING_COST}B'}")
    return {"cable_text": cable_text, "cached": False, "cost": 0 if _was_incoming else BRIEFING_COST}


# ─── Model C Contact System ─────────────────────────────────────────────────

@app.post("/game/{session_id}/diplomacy/contact-request")
async def diplomacy_contact_request(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """
    Model C: Player requests meeting with NPC when relations < 40.
    Returns a terse NPC acknowledgment. Does not open negotiation.
    """
    _verify_game_ownership(session_id, user)
    body = await request.json()
    npc_id = body.get("npc_id")
    if not npc_id:
        raise HTTPException(400, "npc_id required")

    gs = _load_gs(session_id)
    rel = gs.relations.get(npc_id, 50)

    # Only for below-40 relations (crisis conditions bypass this gate)
    _crisis = (
        (npc_id == 'usa' and getattr(gs, 'usa_sanctions_active', False)) or
        (npc_id == 'arabia' and getattr(gs, 'arabia_embargo_active', False)) or
        (npc_id == 'russia' and getattr(gs, 'volkov_trap_stage', 0) > 0) or
        rel < 15
    )
    if rel >= 40 or _crisis:
        raise HTTPException(400, "Use /diplomacy/contact for relations >= 40 or crisis conditions")

    # Check if already requested today
    contact_req = getattr(gs, 'contact_requested', {})
    if npc_id in contact_req:
        return {
            "already_requested": True,
            "acknowledgment": f"You have already requested a meeting with this leader today.",
            "npc_id": npc_id,
        }

    import asyncio
    from npc_engine import generate_contact_request_ack
    ack = await asyncio.to_thread(generate_contact_request_ack, gs, npc_id)

    # Record in game state
    gs.contact_requested[npc_id] = getattr(gs, 'current_turn', 1)
    _save_gs(session_id, gs)

    print(f"  [Model C] Contact request from player to {npc_id} (relations={rel})")
    return {
        "already_requested": False,
        "acknowledgment": ack,
        "npc_id": npc_id,
        "relations": rel,
        "gate_message": "Direct dialogue requires relations above 40",
    }


@app.post("/game/{session_id}/diplomacy/contact")
async def diplomacy_contact(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """
    Model C: Player initiates direct contact with NPC.
    Requires relations >= 40, OR active crisis condition.
    Generates relationship-gated dialogue in NPC voice.
    """
    _verify_game_ownership(session_id, user)
    body = await request.json()
    npc_id = body.get("npc_id")
    if not npc_id:
        raise HTTPException(400, "npc_id required")

    gs = _load_gs(session_id)
    rel = gs.relations.get(npc_id, 50)

    # Crisis conditions always allow contact
    _crisis = (
        (npc_id == 'usa' and getattr(gs, 'usa_sanctions_active', False)) or
        (npc_id == 'arabia' and getattr(gs, 'arabia_embargo_active', False)) or
        (npc_id == 'russia' and getattr(gs, 'volkov_trap_stage', 0) > 0) or
        rel < 15
    )

    # TODO: modify gate by soft_power_score
    if rel < 40 and not _crisis:
        raise HTTPException(403, f"Relations too low ({rel}/100). Use contact-request instead.")

    import asyncio
    from npc_engine import generate_model_c_contact
    dialogue = await asyncio.to_thread(generate_model_c_contact, gs, npc_id)

    # Determine tone tier for frontend display
    if _crisis:
        tone_tier = "crisis"
    elif rel >= 90:
        tone_tier = "partner"
    elif rel >= 70:
        tone_tier = "warm"
    elif rel >= 55:
        tone_tier = "candid"
    else:
        tone_tier = "professional"

    print(f"  [Model C] Direct contact with {npc_id} (relations={rel}, tone={tone_tier})")
    return {
        "npc_id": npc_id,
        "dialogue": dialogue,
        "relations": rel,
        "tone_tier": tone_tier,
        "crisis": _crisis,
    }


# ── 10B-3: Side Deal GM Consequences ────────────────────────────────────────

@app.post("/game/{session_id}/diplomacy/deal-consequences")
async def deal_consequences(session_id: str, request: Request, user: User = Depends(get_optional_user)):
    """
    10B-3: Generate and apply GM consequences for a sidebar deal.
    Called after a deal is completed via CONTACT/negotiate flow.
    IMPORTANT: Does NOT append to deals_today (accept_counter already does that).
    Reloads fresh gs before saving to avoid overwriting events_resolved_today.
    """
    _verify_game_ownership(session_id, user)
    body = await request.json()
    npc_id = body.get("npc_id", "").lower()
    deal_text = body.get("deal_text", "")
    is_backchannel = body.get("is_backchannel", False)

    if not npc_id or not deal_text:
        raise HTTPException(status_code=400, detail="npc_id and deal_text required")

    # Load gs for context only (used to generate consequences)
    gs_for_context = _load_gs(session_id)

    # Generate consequences using context gs (read-only)
    import asyncio
    from npc_engine import generate_deal_consequences
    consequences = await asyncio.to_thread(generate_deal_consequences, gs_for_context, npc_id, deal_text, is_backchannel)

    # RELOAD fresh gs before applying changes to avoid overwriting
    # events_resolved_today, deals_today, or other briefing state
    gs = _load_gs(session_id)

    # Apply ONLY mechanical consequence fields
    relations_delta = consequences.get("relations_delta", {})
    for npc_key, delta in relations_delta.items():
        if isinstance(delta, (int, float)) and npc_key in gs.relations:
            gs.update_relations(npc_key, delta)

    budget_delta = consequences.get("budget_delta", 0.0)
    if budget_delta:
        gs.update_budget(budget_delta)

    pw_delta = consequences.get("personal_wealth_delta", 0.0)
    if pw_delta:
        gs.personal_wealth = max(0, gs.personal_wealth + pw_delta)

    stability_delta = consequences.get("stability_delta", 0.0)
    if stability_delta:
        gs.legitimacy_stability = max(0, min(100, gs.legitimacy_stability + stability_delta))

    # Cross-NPC visibility: NPCs who learn about this deal get a small relations hit
    cross_visible = consequences.get("cross_npc_visibility", [])
    for visible_npc in cross_visible:
        if visible_npc in gs.relations and visible_npc != npc_id:
            gs.update_relations(visible_npc, -1)

    # Reload-and-patch: only update mechanical fields,
    # preserving events_resolved_today, deals_today, and briefing state
    gs_fresh = _load_gs(session_id)
    gs_fresh.relations = gs.relations
    gs_fresh.budget = gs.budget
    gs_fresh.personal_wealth = gs.personal_wealth
    gs_fresh.legitimacy_stability = gs.legitimacy_stability

    # Update gm_consequences on the matching deal in FRESH deals_today
    for _d in reversed(getattr(gs_fresh, 'deals_today', [])):
        if _d.get('npc_id') == npc_id:
            _d['gm_consequences'] = consequences
            break

    _save_gs(session_id, gs_fresh)

    print(f"  [10B-3] Deal consequences applied (targeted-save): {npc_id} — "
          f"relations={relations_delta}, budget={budget_delta}, stability={stability_delta}")

    return {
        "consequences": consequences,
        "game_state": gs_fresh.serialize(),
    }
