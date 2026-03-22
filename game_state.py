"""
Game State Management - The World Stage v3
Enhanced with personality tracking, betrayal detection, and public approval
"""

# ── Session 5: Shadow Cabinet Axes ──────────────────────────────────────────

AXIS_COST_PER_LEVEL = {
    # axis: list of costs to reach level 1, 2, ..., 10
    # Session 6: Security split into Military + Intelligence; Resource Development added
    'military':      [1, 1, 2, 3, 3, 4, 5, 6, 7, 8],
    'intelligence':  [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
    'resource_dev':  [1, 2, 3, 3, 4, 5, 5, 6, 7, 8],
    'media':         [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
    'judicial':      [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
    'political':     [1, 1, 2, 2, 3, 3, 4, 5, 6, 7],
    'extraction':    [1, 1, 1, 2, 2, 3, 3, 4, 5, 6],
}

AXIS_MAINTENANCE = {
    # axis: (free_threshold, cost_per_level_above_threshold)
    # Session 6: Security split into Military + Intelligence; Resource Development added
    'military':      (3, 0.5),
    'intelligence':  (3, 0.4),
    'resource_dev':  (3, 0.3),
    'media':         (3, 0.3),
    'judicial':      (4, 0.4),
    'political':     (3, 0.3),
    'extraction':    (3, 0.2),
}

AXIS_PERMANENT_FLOORS = {
    # Session 6: Security split into Military + Intelligence; Resource Development added
    'military': 2,
    'intelligence': 1,
    'resource_dev': 0,
    'media': 2,
    'judicial': 2,
    'political': 2,
    'extraction': 1,
}


# ── 8C: Exile Sequence Constants ─────────────────────────────────────────
SUCCESSOR_NAMES = {
    'reformist': 'Minister Aleksander Voss',
    'hardliner': 'General Dmitri Kern',
    'technocrat': 'Director Irena Solak',
    'populist': 'Deputy Premier Tomas Varga',
}

APPARATUS_SURVIVAL = {
    'voted_out':  {'survived': True, 'risk_modifier': 0.9},   # intact, low risk
    'debt':       {'survived': True, 'risk_modifier': 1.2},   # partial exposure
    'revolution': {'survived': True, 'risk_modifier': 1.6},   # assets may have defected
    'coup':       {'survived': True, 'risk_modifier': 2.0},   # actively hunted
}


def compute_regime_from_axes(axes):
    """Derive regime_type from the combination of axes.
    Session 6: resource_dev excluded from total — it represents legitimate state
    economic development (the 'clean path'). Including it would penalize democratic
    players who invest in national infrastructure. Only coercive/corrupt axes
    (military, intelligence, media, judicial, political, extraction) count."""
    total = sum(v for k, v in axes.items() if k != 'resource_dev')
    if total <= 5:
        return 'Managed Democracy'
    elif total <= 15:
        return 'Soft Authoritarianism'
    elif total <= 25:
        if axes.get('extraction', 0) >= 7:
            return 'Kleptocracy'
        return 'Patronage State'
    elif total <= 35:
        return 'Kleptocracy'
    else:
        return 'Totalitarian Regime'


def _migrate_to_axes(game_state):
    """One-time migration from binary upgrades to seven axes.
    Called during deserialize when cabinet_axes is absent from save data.
    Session 6: Security split into Military + Intelligence."""
    axes = game_state.cabinet_axes

    # Migrate corruption upgrades
    # Session 6: intelligence_apparatus -> intelligence axis, loyalty_brigades -> military axis
    cu = getattr(game_state, 'corruption_upgrades', {})
    if cu.get('intelligence_apparatus'):
        axes['intelligence'] = max(axes['intelligence'], 3)
    if cu.get('loyalty_brigades'):
        axes['military'] = max(axes['military'], 6)
    if cu.get('sovereign_wealth_diversion'):
        axes['extraction'] = max(axes['extraction'], 3)
    if cu.get('debt_infrastructure_deal'):
        axes['extraction'] = max(axes['extraction'], 5)

    # Migrate domestic actions
    if getattr(game_state, 'action_press_suppressed', False):
        axes['media'] = max(axes['media'], 3)
    if getattr(game_state, 'action_media_taken', False):
        axes['media'] = max(axes['media'], 5)
    if getattr(game_state, 'action_judiciary_captured', False):
        axes['judicial'] = max(axes['judicial'], 4)
    if getattr(game_state, 'action_journalists_liquidated', False):
        axes['judicial'] = max(axes['judicial'], 7)
    if getattr(game_state, 'action_opposition_dissolved', False):
        axes['political'] = max(axes['political'], 6)

    game_state.cabinet_axes = axes
    print(f"  [game_state] AXES MIGRATED: {axes}")


def _migrate_security_to_split(game_state):
    """Session 6: Migrate old 'security' axis into military + intelligence.
    security: N -> military: floor(N/2), intelligence: ceil(N/2)."""
    import math
    axes = game_state.cabinet_axes
    old_security = axes.pop('security', 0)
    if old_security > 0:
        axes['military'] = max(axes.get('military', 0), math.floor(old_security / 2))
        axes['intelligence'] = max(axes.get('intelligence', 0), math.ceil(old_security / 2))
        print(f"  [game_state] SECURITY SPLIT: {old_security} -> military={axes['military']}, intelligence={axes['intelligence']}")
    # Ensure both keys exist
    axes.setdefault('military', 0)
    axes.setdefault('intelligence', 0)
    game_state.cabinet_axes = axes


class GameState:
    """Central state manager with NPC memory and relationship tracking"""

    def __init__(self):
        # Core resources
        self.budget = 65.0  # Billions (national treasury)
        self.stability = 70  # Percentage
        self.oil_price = 75  # Dollars per barrel (min $20)
        self.public_approval = 60  # Percentage (0-100), drifts stability each turn

        # Personal corruption system
        self.personal_wealth = 0.0  # Leader's hidden skimmed funds (billions)
        # Track which NPC corruption messages have already fired (one-shot)
        self.corruption_warned = {
            'usa_5': False, 'usa_15': False, 'usa_30': False,
            'arabia_5': False, 'arabia_15': False, 'arabia_30': False,
            'eu_5': False, 'eu_15': False, 'eu_30': False,
            'dprg_5': False, 'dprg_15': False, 'dprg_30': False,
        }

        # Turn tracking
        self.current_turn = 1
        self.max_turns = 10

        # Day/Era tracking (Session 7A)
        self.current_day = 1
        self.current_era = 1
        self.era_start_day = 1
        self.era_transitions = []        # log of past era transitions
        self.pending_era_transition = False
        self.last_threshold_event = None  # e.g. "regime_shift", "election"
        self.last_threshold_day = 0

        # NPC relationships (0-100)
        self.relations = {
            'usa': 50,
            'arabia': 50,
            'eu': 50,
            'dprg': 50,
            'russia': 35,   # 8A: Full NPC — Nikolai Volkov
            'china': 35,    # 8A: Full NPC — Wei Jianming
        }

        # NPC memory - tracks player behavior
        self.times_sided_with = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0, 'russia': 0, 'china': 0}
        self.times_ignored = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0, 'russia': 0, 'china': 0}
        self.consecutive_sides = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0, 'russia': 0, 'china': 0}
        self.consecutive_ignores = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0, 'russia': 0, 'china': 0}

        # Last 5 actions for context
        self.action_history = []

        # Active crises
        self.usa_sanctions_active = False
        self.arabia_embargo_active = False

        # Sanctions/embargo tier ramp limiters (max +1 tier per turn)
        self.usa_sanctions_tier = 0
        self.arabia_embargo_tier = 0

        # Betrayal tracking
        self.took_arabia_oil = False
        self.took_usa_side_after_arabia_oil = False
        self.took_arabia_side_after_usa_alliance = False

        # USA blackmail mechanic — fires once per game
        self.blackmail_used = False

        # Session 3 Addendum 2: NPC-to-NPC hidden relationship matrix
        # 6 bilateral scores — never displayed directly to player.
        # Shift based on world events and player actions.
        self.npc_relations = {
            'arabia_dprg': 45,   # moderate — arms/energy corridor
            'arabia_eu': 25,     # cool — oil dependency tension
            'arabia_usa': 30,    # strained — sanctions friction
            'dprg_eu': 15,       # hostile — ideological opposition
            'dprg_usa': 10,      # near-hostile — adversarial
            'eu_usa': 75,        # strong allies — Western bloc
            # 8A: Russia/China bilateral scores
            'china_russia': 45,  # wary coexistence
            'russia_usa': 15,    # deep hostility
            'china_usa': 25,     # competitive tension
            'eu_russia': 20,     # adversarial
            'china_eu': 50,      # transactional
            'arabia_russia': 40, # pragmatic energy partners
            'china_dprg': 35,    # cautious alignment
            'arabia_china': 40,  # economic partners
            'dprg_russia': 30,   # legacy alliance
        }
        # Tier 3 brigade: pressure event suspension per NPC
        self.pressure_suspended = {}  # { npc_id: expiry_turn }
        # Tier 3 brigade: approval penalty reduction from State Media Takeover
        self.approval_penalty_reduction = 0.0

        # Stage 4: World Events & Negotiation
        self.current_event = None        # dict | None — world event active this turn
        self.options_override = None     # list | None — negotiated counter-offers

        # Stage 4: Persistent negotiated deal effects
        self.oil_price_locked = False           # True while a negotiated oil lock is active
        self.oil_price_lock_value = 0.0         # The locked price per barrel
        self.oil_price_lock_turns_remaining = 0  # Turns left on the lock
        self.active_trade_commitments = []      # list of {description, turns_remaining}
        self.active_installments = []           # list of {amount, turns_remaining, description, npc}
        # Persistent oil price modifiers — applied on top of relation-based price each EOT.
        # list of {delta: float, turns_remaining: int, description: str}
        # Negative delta = cheaper oil (e.g. Arabia deal -$5 -> price drops $5).
        # Positive delta = more expensive (e.g. supply shock +$10).
        # Used for world events and negotiated per-barrel discounts.
        self.oil_price_modifiers = []

        # ── Stage 5: State Identity Progression ──────────────────────────────
        # regime_type: how the player's rule is characterized by history
        # Progression (left -> right with more corruption/authoritarianism):
        #   "Managed Democracy" -> "Soft Authoritarianism" -> "Patronage State"
        #   -> "Kleptocracy" -> "Totalitarian Regime"
        # power_base: who the player depends on for political survival
        #   "Mass-Dependent" -> "Mixed" -> "Elite-Captured"
        self.state_identity = {
            'regime_type': 'Managed Democracy',
            'power_base': 'Mass-Dependent',
        }

        # Regime shift tracking counters (reset each turn after checking)
        self.consecutive_large_skims = 0   # turns in a row with skim ≥ $7B
        self.low_approval_turns = 0        # turns with approval < 35%
        self.high_approval_turns = 0       # turns with approval > 65%

        # ── Stage 5: Corruption Upgrade System ───────────────────────────────
        self.corruption_upgrades = {
            'intelligence_apparatus': False,    # $3B personal — intel tooltip on NPC cards
            'sovereign_wealth_diversion': False,# $5B personal — large skim stability -6% -> -3%
            'loyalty_brigades': False,          # $8B personal — unlock brigade deployment
            'debt_infrastructure_deal': False,  # $10B personal — $20B budget, USA -15, EU -15
        }

        # ── fixes_12 Fix 4: Epitaph removed, historian summary at game end ────
        self.historian_summary = None  # str | None — generated once at terminal state
        self.pw_ledger = []           # FIX C: personal wealth transaction ledger
        self.negotiate_costs_this_turn = 0.0  # FIX O: track negotiate costs for EOT display
        self.negotiate_sessions_this_turn = 0  # FIX O: count of negotiation sessions

        # ── Stage 5 Session 2: Brigade aftermath ──────────────────────────────
        # Set True after brigades are deployed; cleared after aftermath resolves
        self.brigades_deployed_last_turn = False
        # Session 3 Addendum 2: Brigade tier progression
        # Tier 3 unlocks after Covert Security Apparatus (op 4) is deployed
        self.covert_security_unlocked = False

        # ── Addition 1: Oil tier change visibility ─────────────────────────────
        # Stores the relation-based oil base price from last EOT, so we can
        # detect and log when a tier boundary is crossed.
        self.previous_oil_base = 75  # matches starting oil_price

        # ── Stage 5 Session 2: Dynamic intel cache ────────────────────────────
        # intel: { npc_id: { tier: int, text: str, turn_generated: int, relation_at_generation: int } }
        self.intel = {}
        # Session 3 Addendum: Tracks which NPCs had intel activated this turn (for negotiation unlock)
        # dict of { npc_id: turn_number } — intel unlock only valid for the turn it was activated
        self.intel_activated_this_turn = {}  # { 'usa': 3, 'arabia': 3, ... }

        # ── Session 7A Feature 10: Pending GM consequences (applied at EOT) ──
        # list of { gm_consequence_dict, npc, turn_accepted }
        self.pending_gm_consequences = []

        # ── Session 7B Step 2: Ignored communiqué tracking ──────────────────
        # { npc_id: { ignore_count: int, first_ignored_day: int } }
        self.ignored_communiques = {}
        # Set of NPC keys interacted with this turn (cleared at EOT)
        self.npcs_interacted_this_turn = []

        # ── Session 7B Step 4: Budget trend tracking ──────────────────────────
        self.budget_last_eot = None  # budget snapshot at last EOT for trend display

        # ── Stage 5 Session 2: Deal history ───────────────────────────────────
        # list of { npc, summary, turn_accepted, expires_turn, broken }
        self.deal_history = []

        # ── Session 3: Negotiation log ────────────────────────────────────────
        # Full record of every negotiation exchange for export log auditing.
        # list of { turn, npc, player_message, npc_response, counter_offer, outcome }
        # outcome: 'accepted' | 'rejected' | 'ongoing' | 'walked_away'
        self.negotiation_log = []

        # Session 3 Addendum: Track total aid received from each NPC (for willingness decay)
        self.total_aid_received = {'usa': 0.0, 'arabia': 0.0, 'eu': 0.0, 'dprg': 0.0, 'russia': 0.0, 'china': 0.0}

        # Session 3 Addendum: Per-conversation rapport tracking (resets each turn)
        # { npc_id: { score: int, flattery_used: bool, promises: [...], false_claims: int } }
        self.current_rapport = {}
        # Binding promises made during negotiations
        # list of { npc: str, promise_text: str, turn_made: int, broken: bool }
        self.binding_promises = []

        # ── Session 3 Priority 3: Detection risk system ──────────────────────
        # Tracks cumulative detection heat from corruption activities.
        # Heat decays slowly each turn (-5) but ratchets up from skimming.
        # When a detection roll succeeds, a scandal fires.
        self.detection_heat = 0       # 0-100 (probability percentage)
        self.scandals_triggered = 0   # count of scandals this game
        self.last_scandal_turn = 0    # turn of most recent scandal

        # ── Pre-Session 4: Legacy tracking ─────────────────────────────────
        # Accumulated data for the legacy generator to produce accurate verdicts.
        self.regime_history = []          # list of {"turn": N, "from": str, "to": str, "trigger": str}
        self.total_skimmed = 0.0          # sum of all personal_gain across all turns
        self.peak_personal_wealth = 0.0   # highest personal_wealth reached
        self.relations_high = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}
        self.relations_low = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}
        self.corruption_events_fired = []  # list of event description strings
        self.upgrades_purchased_log = []   # list of upgrade names purchased
        self.sanctions_active_turns = 0    # total turns with USA sanctions active
        self.embargo_active_turns = 0      # total turns with Arabia embargo active

        # ── ITEM 3: Military Strength ─────────────────────────────────────────
        self.military_strength = 20  # 0-100, starts at 20

        # ── Session 3 Priority 4: Leverage system ────────────────────────────
        # Leverage per NPC (0-100) computed each turn from:
        #   - relation level, active deals, sided-with history, NPC dependency
        # Leverage tiers: 0-24 Weak, 25-49 Moderate, 50-74 Strong, 75+ Dominant
        # Higher leverage = better negotiation terms, more NPC concessions
        # Computed dynamically via get_leverage() — not persisted.
        # leverage_events tracks special leverage-granting occurrences
        self.leverage_events = {}  # {npc_id: [event_desc, ...]} — special leverage sources

        # ── Session 3 Priority 5: Multi-NPC pressure events ──────────────────
        # Tracks which pressure events have fired (each fires once per game)
        self.pressure_events_fired = []  # list of event ID strings

        # ── Session 3 Priority 6: Relations 100 unlocks ──────────────────────
        # Permanent benefits unlocked when relations hit 100 with any NPC.
        # Each fires once per NPC per game.
        # { 'usa': True, 'arabia': True, ... } — True = unlocked
        self.relations_100_unlocks = {
            'usa': False,
            'arabia': False,
            'eu': False,
            'dprg': False,
            'russia': False,
            'china': False,
        }

        # ── Session 4B: Election Mechanic ──────────────────────────────────
        self.election_turn = 4              # which turn the election fires
        self.election_fired = False         # has the election happened yet
        self.election_result = None         # 'fair_success' | 'fair_squeaker' | 'fair_fail'
                                            # | 'rigged' | 'canceled' | 'observers'
        self.election_warning_shown = False  # pre-warning shown on turn 3
        self.regime_democracy_locked = 0    # turns remaining where regime cannot shift right
                                            # (set to 3 by observers option)
        self.protests_pending = False       # protests fire next turn after election

        # Session 4C: Domestic actions (permanent, one-time purchases)
        self.action_media_taken = False
        self.action_judiciary_captured = False
        self.action_press_suppressed = False
        self.action_opposition_dissolved = False
        self.action_journalists_liquidated = False
        self.domestic_actions_enacted_turns = {}  # fixes_10 Fix 8: {flag_name: turn_enacted}

        # Session 4C: Passive effect state
        self.approval_floor = 0             # minimum approval (0 = no floor)
        self.approval_ceiling = 100         # maximum approval (100 = no ceiling)
        self.scandal_immune = False         # heat never triggers scandal
        self.coup_immune = False            # coup cannot trigger
        self.marsha_red_line_triggered = False  # journalists liquidated while EU 70+

        # Session 4D: Tech Level — redesigned as passive float accumulation
        self.tech_level = 0.0             # float, accumulates via relationship-weighted passive gain
        self.tech_sources = []            # log of how tech was acquired
        self.tech_gain_last_turn = 0.0    # last turn's gain for display
        self.middle_power_transition = False  # fires once on first reaching Tier 5

        # Session 4D: Intelligence Budget (national, separate from personal wealth)
        self.intel_budget = 0.0           # current intel budget pool (national funds)
        self.intel_budget_allocation = "maintenance"  # "none"|"maintenance"|"active"|"expansion"
        self.intel_turns_unfunded = 0     # consecutive turns at allocation "none"

        # Domestic Affairs: Persistent Budget Allocation (percentages, sum to 100)
        self.budget_allocation = {
            "military": 20,
            "intelligence": 20,
            "public_services": 20,
            "infrastructure": 20,
            "diplomacy": 20,
        }

        # Session 4D: Alternate endings
        self.ending_triggered = None      # None|"retirement"|"democratic"|"capture"|"martyrdom"
        self.martyrdom_triggered = False  # fixes_17 Fix K: set True pre-drift when stability<=0 & approval>=70
        self.turns_no_suppression = 0     # consecutive turns with no suppression actions

        # ── Session 5/6: Shadow Cabinet Axes ──
        self.cabinet_axes = {
            'military': 0,
            'intelligence': 0,
            'resource_dev': 0,
            'media': 0,
            'judicial': 0,
            'political': 0,
            'extraction': 0,
        }
        self.cabinet_maintenance_paid = 0.0  # total maintenance paid this game
        self.extraction_injections_given = []  # tracks one-time budget injections at extraction levels
        # ── Session 6: Military axis action state ──────────────────────────
        self.defense_procurement_count = 0    # L3: number of weapons purchases this game
        self.defense_procurement_turn = -1    # fixes_17 Fix B: last turn Defense Procurement used
        self.force_projection_target = None   # L9: NPC targeted this turn (None if not used)
        self.force_projection_cooldown = 0    # L9: turns remaining before re-use
        self.arms_export_this_turn = None     # L10: NPC sold to this turn (reset each turn)
        # ── Session 6: Intelligence axis action state ────────────────────
        self.intel_sharing_target = None      # L5: NPC offered intel sharing (once per game)
        # ── Session 6: Media axis action state ───────────────────────────
        self.scandal_suppressed_this_turn = False  # L3: suppress scandal once per turn
        self.info_blackout_turns = 0          # L9: turns remaining of info blackout
        # ── Session 6: Judicial axis action state ────────────────────────
        self.drop_investigation_this_turn = False  # L3: free, once per turn
        self.lawfare_target = None            # L6: NPC whose pressure is suspended
        self.lawfare_turns = 0               # L6: turns remaining
        # ── Session 6: Political axis action state ───────────────────────
        self.party_consolidation_turns = 0    # L3: turns remaining of tax drain reduction
        self.fourth_advisor_slot = False      # L6: permanent 4th advisor slot
        self.constitutional_revision_active = False  # L9: electoral mechanics removed
        # ── Session 6: Extraction axis action state ──────────────────────
        self.private_security_force = False   # L7: one-time purchase
        self.private_security_strength = 0    # L7: militia strength (no decay)
        self.offshore_transfer_this_turn = False  # L6: once per turn
        # ── Session 6: Resource Development axis action state ────────────
        self.export_contract_used = False     # L3: one-time +$8B
        self.gdp_credibility_active = False   # L5: permanent NPC ceiling bonus (set on reaching L5)
        self.sovereign_collateral_used = False  # L6: once per game
        self.sovereign_collateral_repayment = 0.0  # per-turn repayment amount
        self.sovereign_collateral_turns = 0   # turns remaining
        self.strategic_resource_partner = None  # L8: NPC name (permanent)
        self.resource_independence_active = False  # L9: oil imports eliminated (set on reaching L9)

        # ── Session 6: NPC Conditional Leverage Demands ─────────────────
        self.leverage_marsha_media_fired = False    # EU 60+, media taken -> negotiate
        self.leverage_bill_opposition_fired = False # USA 70+, opposition dissolved -> negotiate
        self.leverage_sadam_judicial_fired = False  # Arabia 70+, judiciary captured -> auto reward
        self.leverage_jiwon_press_fired = False     # DPRG 60+, press suppressed -> auto reward

        # ── fixes_13: Bond financing ─────────────────────────────────────
        self.bonds_issued_count = 0           # number of bond issuances (second+ triggers penalties)
        self.covert_deals = []                # fixes_13 Fix 24: Ji-won covert transactions
        # ── fixes_13 Fix 26: Black Operations ────────────────────────────
        self.pressure_suspensions = []        # [{npc, turns_remaining, type?}]
        self.blackmail_ops_used = []          # list of NPC IDs blackmailed (one per game)
        self.bilateral_damages = []           # [{from, to, amount, turn}]
        self.cross_npc_penalty_reductions = []  # [{npc, reduction, turns_remaining}]
        # ── fixes_13 Fix 27: NPC 100 unlocks state ──────────────────────
        self.relations_caps = {}              # {npc: max_relation} enforced by 100 unlocks
        self.dprg_coup_deterrence = False     # one-time coup failure at DPRG 100
        # ── fixes_13 Fix 28: Emergency tax event ────────────────────────
        self.emergency_tax_event_fired = False

        # ── 8A: Russia/China relations now in self.relations dict ──
        # Legacy self.russia_relations / self.china_relations removed.
        # Backward compat handled in serialize()/deserialize().

        # ── Session 7D: Backchannel System ──
        self.backchannel_history = []         # resolved entries: {npc_id, turn, era, day, promise_made, promise_text, detected_by, resolved}
        self.active_backchannel_promises = [] # unresolved promises: same schema, resolved=False
        self.opsec_level = 0                  # derived from intelligence axis: 0-3->0, 4-6->1, 7-10->2

        # ── Session 7E: UN Summit System ──
        self.summit_due = False               # True when current_day % 20 == 0 and current_day > 0
        self.summit_history = []              # closed summits: {era, day, player_declaration, npc_reactions, commitments_made}
        self.active_summit_commitments = []   # unresolved public commitments: {commitment_text, day_made, era_made, broken}
        self.summit_credibility = 100.0       # starts 100, drops when commitments broken

        # ── Advisor System (v2: full 9-archetype system with gate-based pool) ──
        self.advisors = {}  # dict keyed by archetype: {archetype, name, background, trust, competence, loyalty, ...}
        self.advisor_slots_available = 2  # daily assignment slots (can increase via Shadow Cabinet)
        self.advisor_pool = []  # list of eligible-to-hire advisors (dynamic, updates on gate change)
        self.advisors_eliminated = []  # list of permanently eliminated archetype keys
        self.advisor_actions_log = []  # betrayal/elimination event log
        self.advisor_distortions = {}  # computed stat distortions for frontend
        self.advisor_analyses = {}  # cached analysis text per archetype key, persists for the turn
        self.advisor_assigned_today = []  # list of unique advisor keys assigned this turn (acts as Set for JSON compat)

        # ── Session 5: Economic Development Model ──────────────────────────
        self.tax_rates = {
            'income_tax': 0.20,       # 0.00-0.50, default 20%
            'corporate_tax': 0.15,    # 0.00-0.40, default 15%
            'resource_tax': 0.25,     # 0.00-0.60, default 25% (oil/mineral extraction)
        }
        self.gdp_base = 100.0             # nominal GDP in billions (starting value)
        self.gdp_growth_rate = 0.02       # 2% baseline growth
        self.revenue_streams = {
            'income_tax': 0.0,        # calculated each turn
            'corporate_tax': 0.0,     # calculated each turn
            'resource_tax': 0.0,      # calculated each turn
            'trade_tariffs': 0.0,     # STUB — Session 6+
            'foreign_aid': 0.0,       # STUB — Session 6+
            'tourism': 0.0,           # STUB — Session 6+
            'arms_exports': 0.0,      # STUB — Session 6+
            'financial_sector': 0.0,  # STUB — Session 6+
        }
        self.resource_endowment = {
            'oil_reserves': 0.7,       # 0-1 richness factor
            'mineral_deposits': 0.3,
            'arable_land': 0.4,
            'rare_earths': 0.1,
            'coastal_access': 0.6,
        }
        self.soft_power = 0              # 0-100, computed from relations + tech + approval
        self.diplomatic_capital = 0      # 0-100, computed from deals + leverage + alliances

        # ── Session 5: NPC-Initiated Contact ───────────────────────────────
        self.npc_contact_history = {}     # { trigger_id: last_turn_fired }
        self.pending_npc_contacts = []    # set by EOT, consumed by next turn's dialogue

        # ── Session 5: Brigade Operations ──────────────────────────────────
        # Per-turn tactical deployments (distinct from Security axis investment)
        self.brigade_operations_this_turn = []  # list of operation dicts deployed this turn

        # ── 8B: Education System ─────────────────────────────────────────
        # education_level: 0-3 (Underdeveloped / Basic / Developed / Advanced)
        # Progression driven by education_allocation spending each turn.
        # Underfunding triggers decay after grace period.
        self.education_level = 0              # current level (0-3)
        self.education_allocation = 0.0       # $B/turn allocated from national budget
        self.education_decay_clock = 0        # consecutive days below maintenance (max 5 before decay)
        self.education_gain_progress = 0.0    # fractional progress toward next level (0.0-1.0, resets on level-up)

        # ── 8C: Exile Sequence ─────────────────────────────────────────────
        self.in_exile = False
        self.exile_trigger = None              # 'coup' | 'revolution' | 'debt' | 'voted_out'
        self.exile_destination = None          # NPC key: 'usa' | 'arabia' | 'eu' | 'dprg' | 'russia' | 'china'
        self.exile_day = 0                     # days spent in exile
        self.exile_backing = None              # NPC key of accepted backer, or None
        self.exile_backing_committed = False
        self.exile_wealth_at_collapse = 0.0    # snapshot for biography
        self.exile_apparatus_survived = False   # True if personal shadow apparatus intact
        self.exile_apparatus_detection_risk_modifier = 1.0  # multiplier on all ops
        self.successor_name = None             # generated on exile start
        self.successor_disposition = None      # 'technocrat' | 'hardliner' | 'populist' | 'reformist'
        self.successor_events_fired = []       # list of event keys already fired
        self.backing_doors_closed = []         # list of NPC keys made unavailable by backing choice
        self.exile_historian_note = None       # 2-3 sentence historian observation at collapse

        # ── 9A: Comeback Mechanics ──────────────────────────────────────────
        self.departure_heat = 0                # 1-5, computed at exile moment
        self.return_progress = 0.0             # 0-100, fills toward return_threshold
        self.return_attempts = 0               # max 3 total
        self.return_threshold = 100.0          # set at exile based on heat + collapse type
        self.npc_assistance_tiers = {}         # {npc_id: tier_accepted (1-5)}
        self.faction_contacts = {}             # {faction: {"unlocked": bool, "committed": bool, "offer": str}}
        self.wealth_action_cooldowns = {}      # {action_key: day_available}
        self.detection_events = []             # log of caught exile actions
        self.restoration_active = False
        self.restoration_grace_days = 0          # FIX 1: turns of collapse immunity after return
        self.restoration_democratic_tally = 0
        self.restoration_authoritarian_tally = 0
        self.prior_regime_label = ""
        self.exile_entry_gdp = 0.0             # snapshot at exile for restoration calc
        self.exile_entry_relations = {}        # snapshot of relations at exile moment
        self.successor_archetype = None        # e.g. "Opposition Democracy", "Military Junta"
        self.successor_hostility = 0           # 0-3
        self.exile_successor_log = []          # log of GM-generated successor events
        self.exile_actions_log = []            # log of player exile actions for GM context

        # ── 9.5A: Commitment Model Foundation ─────────────────────────────
        # Core axis tiers (0–10 scale)
        self.military_tier = 1
        self.intelligence_tier = 1
        self.diplomatic_tier = 0
        self.social_tier = 1
        self.education_tier = 0      # synced from education_level on init
        self.resource_tier = 0       # synced from cabinet_axes['resource_dev'] on init
        self.political_tier = 0
        self.militia_tier = 0

        # Daily costs (computed, stored for display)
        self.daily_military_cost = 0.0
        self.daily_intel_cost = 0.0
        self.daily_diplomatic_cost = 0.0
        self.daily_social_cost = 0.0
        self.daily_education_cost = 0.0
        self.daily_resource_cost = 0.0
        self.total_daily_commitment = 0.0

        # Tax system
        self.income_tax_rate = 0.25
        self.corporate_tax_rate = 0.20
        # resource_tax_rate is inside self.tax_rates['resource_tax'] — kept there
        self.tax_structure = "balanced"  # "elite_heavy" | "balanced" | "mass_heavy"

        # Skim rate (new standalone field — percentage of revenue diverted)
        self.skim_rate = 0.0
        self.last_gross_revenue = 5.5     # last computed gross tax revenue (for frontend skim estimate; 5.5 = approx starting tax rev)
        self.last_net_revenue = 5.5       # last computed net tax revenue (after skim; 5.5 = approx starting)
        self.last_skim_amount = 0.0       # last computed skim amount ($B diverted)

        # Resource policy
        self.resource_policy = "state_led"  # "state_led" | "private_sector"
        self.resource_policy_transition_days = 0

        # Tier upgrade cooldowns: {tier_key: day_available}
        self.tier_upgrade_cooldowns = {}

        # Prerequisite soft gates (tracks violations): {tier_key: bool}
        self.prerequisite_violations = {}

        # Stability composition (used in 9.5B)
        # Initialized: split current stability 70/30 legitimacy/coercion for democratic start
        self.legitimacy_stability = self.stability * 0.70
        self.coercion_stability = self.stability * 0.30

        # 9.5B: Two-component stability fields
        self.sudden_collapse_risk = False       # True when coercion > legitimacy * 1.5 and stability > 20
        self.stability_resilient = False        # True when legitimacy > coercion * 2
        self.external_stability = 0.0           # Stub for 9.5F peacekeeping mechanic
        self.prev_legitimacy_stability = 0.0    # Previous turn's legitimacy for transition detection

        print(f"[9.5B] new stability fields initialized")

        # Coup amplifier
        self.coup_amplifier_active = False

        # Intelligence politicization
        self.intel_politicized = False

        # Western alignment ceiling (computed)
        self.eu_relations_ceiling = 100

        # Sustainability gap — days consecutive that commitments exceed revenue
        self.commitment_deficit_days = 0

        # Loyal generals / loyal intel chief
        self.loyal_generals_installed = False
        self.loyal_intel_chief_installed = False

        # 9.5C: Loyal leadership tracking
        self.loyal_generals_cost_paid = 0.0
        self.loyal_intel_chief_cost_paid = 0.0
        self.loyal_generals_install_day = 0
        self.loyal_intel_chief_install_day = 0
        self.loyal_generals_reversing = False
        self.loyal_intel_chief_reversing = False
        self.loyal_generals_reversal_day = 0
        self.loyal_intel_chief_reversal_day = 0
        self.intel_distortion_active = False
        self.coup_warnings_suppressed = False
        self.pending_briefing_items = []  # consumed at next turn start

        print(f"[9.5C] loyal leadership fields ready")

        # Sync education_tier from education_level at init
        self.education_tier = self.education_level

        print(f"[9.5A] GameState fields initialized: "
              f"mil_tier={self.military_tier} "
              f"intel_tier={self.intelligence_tier} "
              f"diplo_tier={self.diplomatic_tier} "
              f"social_tier={self.social_tier} "
              f"edu_tier={self.education_tier} "
              f"resource_tier={self.resource_tier} "
              f"political_tier={self.political_tier} "
              f"militia_tier={self.militia_tier}")

        # ── 9.5A-Shadow: Shadow State Fields ─────────────────────────────
        # Shadow tiers (0–10 scale, funded from personal wealth)
        self.media_tier = 0
        self.judicial_tier = 0
        self.domestic_surveillance_tier = 0
        self.extraction_tier = 0
        # militia_tier already defined above in commitment section

        # Daily shadow costs (computed, stored for display)
        self.daily_media_cost = 0.0
        self.daily_judicial_cost = 0.0
        self.daily_surveillance_cost = 0.0
        self.daily_extraction_cost = 0.0
        self.daily_militia_cost = 0.0
        self.daily_extraction_revenue = 0.0
        self.total_shadow_commitment = 0.0

        # Shadow state progression
        self.shadow_state_unlocked = False    # unlocked when any shadow tier > 0
        self.militia_merged = False           # militia merged into military apparatus
        self.surveillance_merged = False      # surveillance merged into intelligence
        self.shadow_tier_cooldowns = {}       # {shadow_key: cooldown_until_day}

        # Advisor elimination fear effect
        self.advisor_elimination_count = 0
        self.advisor_elimination_last_day = 0
        self.advisors_with_fear_bonus = []         # advisor keys with active loyalty bonus
        self.advisors_witnessed_elimination = []   # advisor keys who saw an elimination
        self.advisors_chronically_fearful = []     # advisor keys with chronic fear (3+ eliminations)

        print(f"[9.5A-Shadow] Shadow State fields initialized: "
              f"media_tier={self.media_tier} "
              f"judicial_tier={self.judicial_tier} "
              f"surveillance_tier={self.domestic_surveillance_tier} "
              f"extraction_tier={self.extraction_tier} "
              f"shadow_unlocked={self.shadow_state_unlocked}")

        # ── 10C: Operations System Fields ─────────────────────────────────
        # Operations turn tracking (reset each EOT)
        self.ops_legitimate_this_turn = 0   # max 1 per turn (Military/Intel/Diplomatic)
        self.ops_shadow_this_turn = 0       # max 1 per turn (Shadow Operations)

        # Military operation state
        self.arms_export_count = 0          # total exports for diminishing returns
        self.modernization_tranche_1 = False
        self.modernization_tranche_2 = False
        self.modernization_tranche_3 = False

        # Intelligence sharing state (per NPC)
        # {npc_id: {"level": 0-3, "day_started": int}}
        self.intel_sharing_agreements = {}

        # Kompromat state (per NPC)
        # {npc_id: {"active": bool, "uses_remaining": int, "day_collected": int, "burned": bool}}
        self.kompromat_holdings = {}
        # {npc_id: {"day_started": int, "detection_risk_per_day": float}}
        self.kompromat_collection_active = {}

        # Loyalty operations
        # {advisor_id: {"assessed": bool, "coerced": bool, "coerced_day": int}}
        self.advisor_loyalty_ops = {}
        self.counter_intel_cooldown = 0
        self.targeted_intercept_cooldown = 0

        # Diplomatic operations cooldowns
        self.trade_mission_cooldown = 0

        # Shadow operations (detection tracking)
        self.journalist_elimination_available = True  # one-time per game
        self.journalist_elimination_day = 0
        self.journalist_elimination_discovery_day = 0

        # Operations log for biography/historian context
        # List of {day, operation, target, outcome, detected}
        self.operations_log = []

        # Force projection pressure ceiling modifiers
        # {npc_id: {"ceiling_modifier": float, "expires_day": int}}
        self.force_projection_modifiers = {}

        print(f"[10C] Operations fields initialized")

        # 8D: The Leak — scripted branching crisis
        self.the_leak_fired = False            # True once triggered, never fires again
        self.the_leak_resolved = False         # True once player picks a response
        self.the_leak_choice = None            # 'deny' | 'admit' | 'blame' | 'jiwon'
        self.the_leak_followup_fired = False   # True once follow-up consequences fire
        self.scapegoat_used = False            # True once blame-a-minister has been used

        # 10B-1: Daily Briefing System
        self.daily_events = []                 # List of world event dicts for today
        self.events_resolved_today = 0         # Resets each EOT
        self.events_required_today = 3         # Tunable constant
        self.day_events_generated = False       # Prevents re-generation within same day

        # Communiqué escalation tracking
        self.communique_days_without_response = {}  # {npc_id: int} — increments each EOT

        # Morning briefing
        self.morning_briefing_read = False      # Resets each day

        # Declaration gating (10B-2 will use these)
        self.declarations_available = 0         # 0 until day 5, then 1/day
        self.declaration_used_today = False
        self.todays_declaration = ""
        self.declaration_history = []  # {day, era, text, consequences}

        # 10B-2: Event dialogue cache, diplomatic cables, intel ops
        self.event_dialogues = {}       # {event_id: [{npc_id, message}]}
        self.diplomatic_cables = {}     # {npc_id: cable_text}
        self.cables_generated_today = False
        self.intel_ops_today = []       # [{target, detected}]

        # 10B-3: Today's completed deals for briefing display
        self.deals_today = []           # [{id, npc_id, npc_name, deal_text, briefing_summary, source, day, consequences}]

        # 10B-2 Model C: Contact request tracking for low-relations NPCs
        self.contact_requested = {}     # {npc_id: day_requested}

        print(f"[10B-1] Daily briefing fields initialized")

    def record_action(self, choice_type, npc_target=None):
        """
        Record player action with full context
        choice_type: 'side_with', 'ignore', 'accept_deal', 'do_nothing'
        """
        action = {
            'turn': self.current_turn,
            'type': choice_type,
            'npc': npc_target
        }
        self.action_history.append(action)

        # Keep last 5
        if len(self.action_history) > 5:
            self.action_history.pop(0)

        # Update counters
        if choice_type == 'side_with' and npc_target:
            self.times_sided_with[npc_target] += 1
            self.consecutive_sides[npc_target] += 1
            # Reset others
            for npc in self.consecutive_sides:
                if npc != npc_target:
                    self.consecutive_sides[npc] = 0

        elif choice_type == 'ignore' and npc_target:
            self.times_ignored[npc_target] += 1
            self.consecutive_ignores[npc_target] += 1

        elif choice_type in ['accept_deal', 'side_with']:
            # Reset ignore counters when engaging
            if npc_target:
                self.consecutive_ignores[npc_target] = 0

        # Betrayal detection
        if choice_type == 'accept_deal' and npc_target == 'arabia':
            self.took_arabia_oil = True

        if self.took_arabia_oil and choice_type == 'side_with' and npc_target == 'usa':
            self.took_usa_side_after_arabia_oil = True

    def update_relations(self, npc, change, flat=False, source=""):
        """Update relationship with diminishing returns on positive gains, check crisis thresholds.

        Diminishing returns (positive change only — negative is always full):
          current 0-60  -> 100% of change
          current 61-80 ->  75% of change
          current 81-95 ->  40% of change
          current 96-99 ->  10% of change
          current 100   ->   0% (locked — already at cap)

        PRE-SESSION 4 FIX: flat=True bypasses diminishing returns entirely.
        Use flat=True for world events and system-level changes that the player
        did not negotiate and should not be penalized for.
        FIX Q: All relation changes are logged for audit trail.
        """
        _old = self.relations[npc]
        _cap = 100  # hard cap for all NPCs

        # EU soft cap from tech level: 60 + (tech × 2), capped at 100
        # Above soft cap: positive gains halved (stacks with diminishing returns)
        _eu_soft_cap_mult = 1.0
        if npc == 'eu' and change > 0 and not flat:
            _tech = float(getattr(self, 'tech_level', 0))
            _eu_soft = min(100, 60 + int(_tech * 2))
            if self.relations[npc] >= _eu_soft:
                _eu_soft_cap_mult = 0.5

        if change > 0 and not flat:
            cur = self.relations[npc]
            if cur >= _cap:
                effective = 0.0
            elif cur >= 96:
                effective = change * 0.10
            elif cur >= 81:
                effective = change * 0.40
            elif cur >= 61:
                effective = change * 0.75
            else:
                effective = float(change)
            effective *= _eu_soft_cap_mult
            self.relations[npc] = max(0, min(_cap, cur + effective))
        else:
            # Domestic Affairs: diplomacy allocation moderates negative drift during EOT
            _diplo_mod = getattr(self, '_diplo_drift_modifier', 1.0)
            _eff_change = change * _diplo_mod if (change < 0 and _diplo_mod < 1.0) else change
            self.relations[npc] = max(0, min(_cap, self.relations[npc] + _eff_change))

        # FIX Q: Log every relation change for audit trail
        _new = self.relations[npc]
        if _old != _new:
            if not hasattr(self, 'relations_log'):
                self.relations_log = []
            self.relations_log.append({
                'turn': self.current_turn,
                'npc': npc,
                'old': round(_old, 1),
                'new': round(_new, 1),
                'change': round(_new - _old, 1),
                'requested': change,
                'source': source or 'unspecified',
            })

        # Track relation highs/lows for legacy
        cur = self.relations[npc]
        if hasattr(self, 'relations_high'):
            if cur > self.relations_high.get(npc, 50):
                self.relations_high[npc] = cur
        if hasattr(self, 'relations_low'):
            if cur < self.relations_low.get(npc, 50):
                self.relations_low[npc] = cur

        # Crisis triggers
        if npc == 'usa':
            if self.relations['usa'] < 25:
                self.usa_sanctions_active = True
            else:
                self.usa_sanctions_active = False

        if npc == 'arabia':
            if self.relations['arabia'] < 25:
                self.arabia_embargo_active = True
            else:
                self.arabia_embargo_active = False

    def update_personal_wealth(self, change, source="unknown"):
        """FIX C: Atomically update personal wealth and record in transaction ledger.
        Every credit and debit is logged with source label."""
        old = self.personal_wealth
        self.personal_wealth = round(max(0, self.personal_wealth + change), 2)
        if not hasattr(self, 'pw_ledger'):
            self.pw_ledger = []
        self.pw_ledger.append({
            'turn': self.current_turn,
            'change': round(change, 2),
            'source': source,
            'old': round(old, 2),
            'new': self.personal_wealth,
        })

    def update_budget(self, change):
        """Update budget (can go negative for loss condition)"""
        self.budget += change

    def update_stability(self, change):
        """Update stability (0-90 max — mirrors approval cap)"""
        self.stability = max(0, min(90, self.stability + change))

    def update_oil_price(self, change):
        """Update oil price with ENFORCED $20 minimum"""
        self.oil_price += change
        if self.oil_price < 20:
            self.oil_price = 20

    def update_approval(self, change):
        """Update public approval (0-90 max — 100% unrealistic under geopolitical pressure).
        Session 3 Addendum 2: approval_penalty_reduction (from State Media Takeover)
        reduces negative approval changes by the stored percentage (e.g. 0.20 = 20% reduction).
        Session 4C: approval_floor/approval_ceiling enforce bounds from domestic actions.
        8B: Education approval sensitivity — higher education dampens negative approval swings."""
        if change < 0:
            # 8B: Education approval sensitivity (applied first, before other reductions)
            _edu_sensitivity = {0: 1.0, 1: 0.95, 2: 0.85, 3: 0.70}
            _edu_lvl = getattr(self, 'education_level', 0)
            _sens = _edu_sensitivity.get(_edu_lvl, 1.0)
            if _sens < 1.0:
                change = round(change * _sens)
            # Session 3 Addendum 2: State Media Takeover reduction
            if self.approval_penalty_reduction > 0:
                change = round(change * (1.0 - self.approval_penalty_reduction))
        ceiling = min(90, getattr(self, 'approval_ceiling', 100))
        floor = max(0, getattr(self, 'approval_floor', 0))
        self.public_approval = max(floor, min(ceiling, self.public_approval + change))

    def _determine_successor(self):
        """8C: Determine successor disposition based on how the player governed.
        Successor takes the OPPOSITE political course to the player."""
        regime = self.state_identity.get('regime_type', 'Managed Democracy')

        # Player was authoritarian -> successor is Reformist or Technocrat
        if regime in ('Totalitarian Regime', 'Kleptocracy', 'Soft Authoritarianism'):
            if self.relations.get('eu', 50) < 50:
                return 'reformist'
            else:
                return 'technocrat'

        # Player was Western-aligned and democratic -> successor is Hardliner
        if self.relations.get('eu', 50) > 70 and self.relations.get('usa', 50) > 70:
            return 'hardliner'

        # Player was kleptocratic but popular -> successor is Technocrat
        if self.personal_wealth > 20.0:
            return 'technocrat'

        # Default
        return 'populist'

    def advance_turn(self):
        """Move to next day/turn - ENFORCED 10 TURN MAX"""
        if self.current_turn < self.max_turns:
            self.current_turn += 1
            self.current_day += 1
            return True
        return False

    def get_last_n_actions(self, n=3):
        """Get last N actions for NPC reference"""
        return self.action_history[-n:] if len(self.action_history) >= n else self.action_history

    def get_approval_indicator(self):
        """Return color-coded approval indicator (max 90%)"""
        a = self.public_approval
        if a >= 70:
            return f"🟢 {a}%"
        elif a >= 50:
            return f"🟡 {a}%"
        elif a >= 30:
            return f"🔴 {a}%"
        else:
            return f"💀 {a}%"

    def set_oil_price_from_relations(self):
        """
        Recalculate oil price each turn based on Arabia relations.
        Does NOT carry forward previous price — resets to relation-based value.
        Base oil price = $75. Then apply multiplier from Arabia relations.
        Returns the new base price (before embargo tier surcharges).
        """
        base = 75.0
        arabia_rel = self.relations['arabia']
        if arabia_rel >= 80:
            new_price = base * 0.70   # ~$52
        elif arabia_rel >= 60:
            new_price = base * 0.85   # ~$64
        elif arabia_rel >= 40:
            new_price = base * 1.00   # $75
        elif arabia_rel >= 20:
            new_price = base * 1.25   # ~$94
        else:
            new_price = base * 1.60   # ~$120
        self.oil_price = max(20.0, round(new_price))
        return int(self.oil_price)

    def get_leverage(self, npc_id: str) -> dict:
        """
        Compute leverage score and tier for one NPC.
        Leverage = weighted sum of:
          - Relation level (0-100): 40% weight
          - Times sided with (0-10 capped): 20% weight
          - Active deals count (0-3 capped): 15% weight
          - Opposing NPC hostility (if their rival is hostile to Europa, this NPC depends on us more): 15% weight
          - Special leverage events: 10% weight
        Returns { score: int, tier: str, tier_num: int }
        """
        relation = self.relations.get(npc_id, 50)
        sided = min(10, self.times_sided_with.get(npc_id, 0))

        # Active deals with this NPC
        deal_history = getattr(self, 'deal_history', [])
        active_deals = len([
            d for d in deal_history
            if d.get('npc') == npc_id
            and not d.get('broken')
            and d.get('expires_turn', 0) >= self.current_turn
        ])
        active_deals = min(3, active_deals)

        # Opposing NPC hostility: if their geopolitical rival is hostile to Europa,
        # this NPC has more reason to court Europa -> higher leverage for us.
        # USA vs Arabia/DPRG, EU vs DPRG, Arabia vs USA/EU
        _rivals = {
            'usa': ['arabia', 'dprg', 'russia'],
            'arabia': ['usa', 'eu'],
            'eu': ['dprg', 'arabia', 'russia'],
            'dprg': ['usa', 'eu'],
            'russia': ['usa', 'eu'],
            'china': ['usa'],
        }
        rival_hostility = 0
        for rival in _rivals.get(npc_id, []):
            rival_rel = self.relations.get(rival, 50)
            if rival_rel < 30:
                rival_hostility += (30 - rival_rel) / 30.0  # 0-1 per rival

        rival_hostility = min(1.0, rival_hostility)  # cap at 1.0

        # Special leverage events
        leverage_events = getattr(self, 'leverage_events', {})
        special_count = min(3, len(leverage_events.get(npc_id, [])))

        # Weighted score
        score = (
            (relation / 100.0) * 40.0 +
            (sided / 10.0) * 20.0 +
            (active_deals / 3.0) * 15.0 +
            rival_hostility * 15.0 +
            (special_count / 3.0) * 10.0
        )
        score = max(0, min(100, round(score)))

        # Tier
        if score >= 75:
            tier, tier_num = 'Dominant', 3
        elif score >= 50:
            tier, tier_num = 'Strong', 2
        elif score >= 25:
            tier, tier_num = 'Moderate', 1
        else:
            tier, tier_num = 'Weak', 0

        return {'score': score, 'tier': tier, 'tier_num': tier_num}

    def get_threshold_warnings(self):
        """ITEM 2: Generate pre-warning messages for existential thresholds.
        Returns list of warning dicts with level ('warning' or 'danger') and text."""
        warnings = []
        arabia_rel = self.relations.get('arabia', 50)
        usa_rel = self.relations.get('usa', 50)
        stab = self.stability
        approval = self.public_approval
        budget = self.budget

        # FIX I: Early caution at Arabia 35, full embargo risk at Arabia 25
        if arabia_rel < 25:
            warnings.append({
                'level': 'warning',
                'text': '🛢️ ⚠️ EMBARGO RISK — Arabia relations critical. Oil supply weaponization possible next turn. Secure alternative energy or repair relations immediately.'
            })
        elif arabia_rel < 35:
            warnings.append({
                'level': 'warning',
                'text': '🛢️ ⚠️ Arabia relations declining — sustained USA alignment will trigger oil price increases.'
            })
        if budget < 4:
            warnings.append({
                'level': 'danger',
                'text': '💸 🚨 BANKRUPTCY IMMINENT — One turn from insolvency. Emergency action required.'
            })
        elif budget < 8:
            warnings.append({
                'level': 'warning',
                'text': '💸 ⚠️ SOLVENCY WARNING — National treasury critically low. Bankruptcy possible this turn if drain exceeds available funds.'
            })
        if stab < 20:
            warnings.append({
                'level': 'danger',
                'text': '🛡️ ⚠️ COUP RISK — Military may act. Stability this low invites regime change regardless of approval.'
            })
        if approval < 20:
            warnings.append({
                'level': 'danger',
                'text': '📊 ⚠️ REVOLUTION RISK — Public legitimacy near collapse. Mass unrest events likely.'
            })
        if usa_rel < 20 and usa_rel > 0:
            warnings.append({
                'level': 'warning',
                'text': '🇺🇸 ⚠️ SANCTIONS ESCALATION RISK — Tier 4 sanctions possible next turn. Consider diplomatic intervention.'
            })
        # Military coup risk (ITEM 3 integration)
        _mil = getattr(self, 'military_strength', 20)
        if _mil <= 0:
            warnings.append({
                'level': 'danger',
                'text': '⚔️ 🚨 MILITARY COLLAPSE — No military capacity. Coup risk extreme.'
            })
        return warnings

    def get_status_display(self):
        """Generate status display"""
        sanctions_flag = " ⚠️ SANCTIONS!" if self.usa_sanctions_active else ""
        embargo_flag = " ⚠️ EMBARGO!" if self.arabia_embargo_active else ""
        approval_str = self.get_approval_indicator()
        personal_str = f"🏦 Personal: ${self.personal_wealth:.1f}B" if self.personal_wealth > 0 else "🏦 Personal: $0"

        return f"""
{'='*60}
TURN {self.current_turn}/{self.max_turns} - EUROPA STATUS
Budget: ${self.budget:.1f}B | {personal_str} | Stability: {self.stability}%
Oil: ${self.oil_price:.0f}/barrel | Approval: {approval_str}
Relations: USA {self.relations['usa']} | Arabia {self.relations['arabia']} | EU {self.relations['eu']} | DPRG {self.relations['dprg']}
{sanctions_flag}{embargo_flag}
{'='*60}
"""

    def _compute_tech_tier(self):
        """Compute tech tier (0-5) from tech_level."""
        tl = float(getattr(self, 'tech_level', 0))
        if tl >= 100: return 5
        if tl >= 75:  return 4
        if tl >= 50:  return 3
        if tl >= 25:  return 2
        if tl >= 10:  return 1
        return 0

    def _compute_tech_tier_name(self):
        """Compute tech tier name from tech_level."""
        _names = {0: "Pre-Industrial", 1: "Emerging Capability", 2: "Functional Modernization",
                  3: "Strategic Capability", 4: "Advanced Economy", 5: "Frontier"}
        return _names[self._compute_tech_tier()]

    def _compute_advisor_distortions(self):
        """Compute stat distortions from active assigned advisors for frontend."""
        try:
            from advisor_engine import compute_all_distortions
            return compute_all_distortions(self)
        except Exception:
            return {}

    def serialize(self):
        """Convert full GameState to a JSON-serializable dict for database storage."""
        return {
            'budget': self.budget,
            'stability': self.stability,
            'oil_price': self.oil_price,
            'public_approval': self.public_approval,
            'personal_wealth': self.personal_wealth,
            'corruption_warned': self.corruption_warned,
            'current_turn': self.current_turn,
            'max_turns': self.max_turns,
            'current_day': self.current_day,
            'current_era': self.current_era,
            'era_start_day': self.era_start_day,
            'era_transitions': self.era_transitions,
            'pending_era_transition': self.pending_era_transition,
            'last_threshold_event': self.last_threshold_event,
            'last_threshold_day': self.last_threshold_day,
            'relations': self.relations,
            'times_sided_with': self.times_sided_with,
            'times_ignored': self.times_ignored,
            'consecutive_sides': self.consecutive_sides,
            'consecutive_ignores': self.consecutive_ignores,
            'action_history': self.action_history,
            'usa_sanctions_active': self.usa_sanctions_active,
            'arabia_embargo_active': self.arabia_embargo_active,
            'usa_sanctions_tier': self.usa_sanctions_tier,
            'arabia_embargo_tier': self.arabia_embargo_tier,
            'took_arabia_oil': self.took_arabia_oil,
            'took_usa_side_after_arabia_oil': self.took_usa_side_after_arabia_oil,
            'took_arabia_side_after_usa_alliance': self.took_arabia_side_after_usa_alliance,
            'blackmail_used': self.blackmail_used,
            'npc_relations': self.npc_relations,
            'pressure_suspended': self.pressure_suspended,
            'approval_penalty_reduction': self.approval_penalty_reduction,
            'current_event': self.current_event,
            'options_override': self.options_override,
            'oil_price_locked': self.oil_price_locked,
            'oil_price_lock_value': self.oil_price_lock_value,
            'oil_price_lock_turns_remaining': self.oil_price_lock_turns_remaining,
            'active_trade_commitments': self.active_trade_commitments,
            'active_installments': self.active_installments,
            'oil_price_modifiers': self.oil_price_modifiers,
            # Stage 5
            'state_identity': self.state_identity,
            'consecutive_large_skims': self.consecutive_large_skims,
            'low_approval_turns': self.low_approval_turns,
            'high_approval_turns': self.high_approval_turns,
            'corruption_upgrades': self.corruption_upgrades,
            'historian_summary': getattr(self, 'historian_summary', None),  # fixes_12 Fix 4
            'pw_ledger': self.pw_ledger,
            'negotiate_costs_this_turn': self.negotiate_costs_this_turn,
            'negotiate_sessions_this_turn': self.negotiate_sessions_this_turn,
            # Session 2
            'brigades_deployed_last_turn': self.brigades_deployed_last_turn,
            'covert_security_unlocked': self.covert_security_unlocked,
            'intel': self.intel,
            'intel_activated_this_turn': self.intel_activated_this_turn,
            'deal_history': self.deal_history,
            'pending_gm_consequences': self.pending_gm_consequences,
            'ignored_communiques': self.ignored_communiques,
            'npcs_interacted_this_turn': list(self.npcs_interacted_this_turn),
            'budget_last_eot': self.budget_last_eot,
            'previous_oil_base': self.previous_oil_base,
            # Session 3
            'negotiation_log': self.negotiation_log,
            'total_aid_received': self.total_aid_received,
            'current_rapport': self.current_rapport,
            'binding_promises': self.binding_promises,
            'detection_heat': self.detection_heat,
            'scandals_triggered': self.scandals_triggered,
            'last_scandal_turn': self.last_scandal_turn,
            'leverage_events': self.leverage_events,
            'pressure_events_fired': self.pressure_events_fired,
            'relations_100_unlocks': self.relations_100_unlocks,
            # Pre-Session 4: Legacy tracking
            'regime_history': self.regime_history,
            'total_skimmed': self.total_skimmed,
            'peak_personal_wealth': self.peak_personal_wealth,
            'relations_high': self.relations_high,
            'relations_low': self.relations_low,
            'corruption_events_fired': self.corruption_events_fired,
            'upgrades_purchased_log': self.upgrades_purchased_log,
            'sanctions_active_turns': self.sanctions_active_turns,
            'embargo_active_turns': self.embargo_active_turns,
            # ITEM 2: Pre-computed threshold warnings for frontend display
            'threshold_warnings': self.get_threshold_warnings(),
            # ITEM 3: Military Strength
            'military_strength': getattr(self, 'military_strength', 20),
            # Session 4B: Election
            'election_turn': getattr(self, 'election_turn', 4),
            'election_fired': getattr(self, 'election_fired', False),
            'election_result': getattr(self, 'election_result', None),
            'election_warning_shown': getattr(self, 'election_warning_shown', False),
            'regime_democracy_locked': getattr(self, 'regime_democracy_locked', 0),
            'protests_pending': getattr(self, 'protests_pending', False),
            # Session 4C: Domestic Actions
            'action_media_taken': getattr(self, 'action_media_taken', False),
            'action_judiciary_captured': getattr(self, 'action_judiciary_captured', False),
            'action_press_suppressed': getattr(self, 'action_press_suppressed', False),
            'action_opposition_dissolved': getattr(self, 'action_opposition_dissolved', False),
            'action_journalists_liquidated': getattr(self, 'action_journalists_liquidated', False),
            'domestic_actions_enacted_turns': getattr(self, 'domestic_actions_enacted_turns', {}),
            'approval_floor': getattr(self, 'approval_floor', 0),
            'approval_ceiling': getattr(self, 'approval_ceiling', 100),
            'scandal_immune': getattr(self, 'scandal_immune', False),
            'coup_immune': getattr(self, 'coup_immune', False),
            'marsha_red_line_triggered': getattr(self, 'marsha_red_line_triggered', False),
            # Session 4D: Tech Level
            'tech_level': getattr(self, 'tech_level', 0.0),
            'tech_sources': getattr(self, 'tech_sources', []),
            'tech_gain_last_turn': getattr(self, 'tech_gain_last_turn', 0.0),
            'middle_power_transition': getattr(self, 'middle_power_transition', False),
            'tech_tier': self._compute_tech_tier(),
            'tech_tier_name': self._compute_tech_tier_name(),
            # Session 4D: Intelligence Budget
            'intel_budget': getattr(self, 'intel_budget', 0.0),
            'intel_budget_allocation': getattr(self, 'intel_budget_allocation', 'maintenance'),
            'intel_turns_unfunded': getattr(self, 'intel_turns_unfunded', 0),
            # Domestic Affairs: Budget Allocation
            'budget_allocation': getattr(self, 'budget_allocation', {
                "military": 20, "intelligence": 20, "public_services": 20,
                "infrastructure": 20, "diplomacy": 20,
            }),
            # Session 4D: Alternate endings
            'ending_triggered': getattr(self, 'ending_triggered', None),
            'martyrdom_triggered': getattr(self, 'martyrdom_triggered', False),
            'turns_no_suppression': getattr(self, 'turns_no_suppression', 0),
            # Session 5: Shadow Cabinet Five Axes
            'cabinet_axes': getattr(self, 'cabinet_axes', {'military': 0, 'intelligence': 0, 'resource_dev': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}),
            'cabinet_maintenance_paid': getattr(self, 'cabinet_maintenance_paid', 0.0),
            'extraction_injections_given': getattr(self, 'extraction_injections_given', []),
            # fixes_16 Fix C: Extraction milestones
            'extraction_l5_fired': getattr(self, 'extraction_l5_fired', False),
            'extraction_l7_fired': getattr(self, 'extraction_l7_fired', False),
            # Session 6: Military axis action state
            'defense_procurement_count': getattr(self, 'defense_procurement_count', 0),
            'defense_procurement_turn': getattr(self, 'defense_procurement_turn', -1),
            'force_projection_target': getattr(self, 'force_projection_target', None),
            'force_projection_cooldown': getattr(self, 'force_projection_cooldown', 0),
            'arms_export_this_turn': getattr(self, 'arms_export_this_turn', None),
            # Session 6: Intelligence axis action state
            'intel_sharing_target': getattr(self, 'intel_sharing_target', None),
            # Session 6: Media axis action state
            'scandal_suppressed_this_turn': getattr(self, 'scandal_suppressed_this_turn', False),
            'info_blackout_turns': getattr(self, 'info_blackout_turns', 0),
            # Session 6: Judicial axis action state
            'drop_investigation_this_turn': getattr(self, 'drop_investigation_this_turn', False),
            'lawfare_target': getattr(self, 'lawfare_target', None),
            'lawfare_turns': getattr(self, 'lawfare_turns', 0),
            # Session 6: Political axis action state
            'party_consolidation_turns': getattr(self, 'party_consolidation_turns', 0),
            'fourth_advisor_slot': getattr(self, 'fourth_advisor_slot', False),
            'constitutional_revision_active': getattr(self, 'constitutional_revision_active', False),
            # Session 6: Extraction axis action state
            'private_security_force': getattr(self, 'private_security_force', False),
            'private_security_strength': getattr(self, 'private_security_strength', 0),
            'offshore_transfer_this_turn': getattr(self, 'offshore_transfer_this_turn', False),
            # Session 6: Resource Development axis action state
            'export_contract_used': getattr(self, 'export_contract_used', False),
            'gdp_credibility_active': getattr(self, 'gdp_credibility_active', False),
            'sovereign_collateral_used': getattr(self, 'sovereign_collateral_used', False),
            'sovereign_collateral_repayment': getattr(self, 'sovereign_collateral_repayment', 0.0),
            'sovereign_collateral_turns': getattr(self, 'sovereign_collateral_turns', 0),
            'strategic_resource_partner': getattr(self, 'strategic_resource_partner', None),
            'resource_independence_active': getattr(self, 'resource_independence_active', False),
            # Session 6: NPC Conditional Leverage Demands
            'leverage_marsha_media_fired': getattr(self, 'leverage_marsha_media_fired', False),
            'leverage_bill_opposition_fired': getattr(self, 'leverage_bill_opposition_fired', False),
            'leverage_sadam_judicial_fired': getattr(self, 'leverage_sadam_judicial_fired', False),
            'leverage_jiwon_press_fired': getattr(self, 'leverage_jiwon_press_fired', False),
            # fixes_13: Bond financing + covert deals
            'bonds_issued_count': getattr(self, 'bonds_issued_count', 0),
            'small_bond_last_turn': getattr(self, 'small_bond_last_turn', -1),
            'large_bond_used': getattr(self, 'large_bond_used', False),
            'covert_deals': getattr(self, 'covert_deals', []),
            # fixes_13 Fix 26: Black Operations state
            'pressure_suspensions': getattr(self, 'pressure_suspensions', []),
            'blackmail_ops_used': getattr(self, 'blackmail_ops_used', []),
            # fixes_15 Fix F: Intel tier persists across turns for Blackmail
            'npc_intel_tiers': getattr(self, 'npc_intel_tiers', {}),
            'bilateral_damages': getattr(self, 'bilateral_damages', []),
            'cross_npc_penalty_reductions': getattr(self, 'cross_npc_penalty_reductions', []),
            # fixes_13 Fix 27: NPC 100 unlock state
            'relations_caps': getattr(self, 'relations_caps', {}),
            'dprg_coup_deterrence': getattr(self, 'dprg_coup_deterrence', False),
            # fixes_13 Fix 28: Emergency tax event
            'emergency_tax_event_fired': getattr(self, 'emergency_tax_event_fired', False),
            # 8A: Backward-compat legacy fields (read from relations dict)
            'russia_relations': self.relations.get('russia', 35.0),
            'china_relations': self.relations.get('china', 35.0),
            # Session 7D: Backchannel System
            'backchannel_history': getattr(self, 'backchannel_history', []),
            'active_backchannel_promises': getattr(self, 'active_backchannel_promises', []),
            'opsec_level': getattr(self, 'opsec_level', 0),
            # Session 7E: UN Summit System
            'summit_due': getattr(self, 'summit_due', False),
            'summit_history': getattr(self, 'summit_history', []),
            'active_summit_commitments': getattr(self, 'active_summit_commitments', []),
            'summit_credibility': getattr(self, 'summit_credibility', 100.0),
            # Advisor System (restored 9-archetype pool)
            'advisors': getattr(self, 'advisors', {}),
            'advisor_slots_available': getattr(self, 'advisor_slots_available', 2),
            'advisor_pool': getattr(self, 'advisor_pool', []),
            'advisors_eliminated': getattr(self, 'advisors_eliminated', []),
            'advisor_actions_log': getattr(self, 'advisor_actions_log', []),
            'advisor_distortions': self._compute_advisor_distortions(),
            'advisor_analyses': getattr(self, 'advisor_analyses', {}),
            'advisor_assigned_today': getattr(self, 'advisor_assigned_today', []),
            '_general_coup_boost_turns': getattr(self, '_general_coup_boost_turns', 0),
            '_general_elim_decay_turns': getattr(self, '_general_elim_decay_turns', 0),
            # Session 5: Economic Development Model
            'tax_rates': getattr(self, 'tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25}),
            'gdp_base': getattr(self, 'gdp_base', 100.0),
            'gdp_growth_rate': getattr(self, 'gdp_growth_rate', 0.02),
            'revenue_streams': getattr(self, 'revenue_streams', {}),
            'resource_endowment': getattr(self, 'resource_endowment', {'oil_reserves': 0.7, 'mineral_deposits': 0.3, 'arable_land': 0.4, 'rare_earths': 0.1, 'coastal_access': 0.6}),
            'soft_power': getattr(self, 'soft_power', 0),
            'diplomatic_capital': getattr(self, 'diplomatic_capital', 0),
            # Session 5: NPC-Initiated Contact
            'npc_contact_history': getattr(self, 'npc_contact_history', {}),
            'pending_npc_contacts': getattr(self, 'pending_npc_contacts', []),
            # Session 5: Brigade Operations
            'brigade_operations_this_turn': getattr(self, 'brigade_operations_this_turn', []),
            # 8B: Education System
            'education_level': getattr(self, 'education_level', 0),
            'education_allocation': getattr(self, 'education_allocation', 0.0),
            'education_decay_clock': getattr(self, 'education_decay_clock', 0),
            'education_gain_progress': getattr(self, 'education_gain_progress', 0.0),
            # 8C: Exile Sequence
            'in_exile': getattr(self, 'in_exile', False),
            'exile_trigger': getattr(self, 'exile_trigger', None),
            'exile_destination': getattr(self, 'exile_destination', None),
            'exile_day': getattr(self, 'exile_day', 0),
            'exile_backing': getattr(self, 'exile_backing', None),
            'exile_backing_committed': getattr(self, 'exile_backing_committed', False),
            'exile_wealth_at_collapse': getattr(self, 'exile_wealth_at_collapse', 0.0),
            'exile_apparatus_survived': getattr(self, 'exile_apparatus_survived', False),
            'exile_apparatus_detection_risk_modifier': getattr(self, 'exile_apparatus_detection_risk_modifier', 1.0),
            'successor_name': getattr(self, 'successor_name', None),
            'successor_disposition': getattr(self, 'successor_disposition', None),
            'successor_events_fired': getattr(self, 'successor_events_fired', []),
            'backing_doors_closed': getattr(self, 'backing_doors_closed', []),
            'exile_historian_note': getattr(self, 'exile_historian_note', None),
            # 9A: Comeback Mechanics
            'departure_heat': getattr(self, 'departure_heat', 0),
            'return_progress': getattr(self, 'return_progress', 0.0),
            'return_attempts': getattr(self, 'return_attempts', 0),
            'return_threshold': getattr(self, 'return_threshold', 100.0),
            'npc_assistance_tiers': getattr(self, 'npc_assistance_tiers', {}),
            'faction_contacts': getattr(self, 'faction_contacts', {}),
            'wealth_action_cooldowns': getattr(self, 'wealth_action_cooldowns', {}),
            'detection_events': getattr(self, 'detection_events', []),
            'restoration_active': getattr(self, 'restoration_active', False),
            'restoration_grace_days': getattr(self, 'restoration_grace_days', 0),
            'restoration_democratic_tally': getattr(self, 'restoration_democratic_tally', 0),
            'restoration_authoritarian_tally': getattr(self, 'restoration_authoritarian_tally', 0),
            'prior_regime_label': getattr(self, 'prior_regime_label', ''),
            'exile_entry_gdp': getattr(self, 'exile_entry_gdp', 0.0),
            'exile_entry_relations': getattr(self, 'exile_entry_relations', {}),
            'successor_archetype': getattr(self, 'successor_archetype', None),
            'successor_hostility': getattr(self, 'successor_hostility', 0),
            'exile_successor_log': getattr(self, 'exile_successor_log', []),
            'exile_actions_log': getattr(self, 'exile_actions_log', []),
            # 8D: The Leak
            'the_leak_fired': getattr(self, 'the_leak_fired', False),
            'the_leak_resolved': getattr(self, 'the_leak_resolved', False),
            'the_leak_choice': getattr(self, 'the_leak_choice', None),
            'the_leak_followup_fired': getattr(self, 'the_leak_followup_fired', False),
            'scapegoat_used': getattr(self, 'scapegoat_used', False),
            # 9.5A: Commitment Model
            'military_tier': getattr(self, 'military_tier', 1),
            'intelligence_tier': getattr(self, 'intelligence_tier', 1),
            'diplomatic_tier': getattr(self, 'diplomatic_tier', 0),
            'social_tier': getattr(self, 'social_tier', 1),
            'education_tier': getattr(self, 'education_tier', 0),
            'resource_tier': getattr(self, 'resource_tier', 0),
            'political_tier': getattr(self, 'political_tier', 0),
            'militia_tier': getattr(self, 'militia_tier', 0),
            'daily_military_cost': getattr(self, 'daily_military_cost', 0.0),
            'daily_intel_cost': getattr(self, 'daily_intel_cost', 0.0),
            'daily_diplomatic_cost': getattr(self, 'daily_diplomatic_cost', 0.0),
            'daily_social_cost': getattr(self, 'daily_social_cost', 0.0),
            'daily_education_cost': getattr(self, 'daily_education_cost', 0.0),
            'daily_resource_cost': getattr(self, 'daily_resource_cost', 0.0),
            'total_daily_commitment': getattr(self, 'total_daily_commitment', 0.0),
            'income_tax_rate': getattr(self, 'income_tax_rate', 0.25),
            'corporate_tax_rate': getattr(self, 'corporate_tax_rate', 0.20),
            'tax_structure': getattr(self, 'tax_structure', 'balanced'),
            'skim_rate': getattr(self, 'skim_rate', 0.0),
            'last_gross_revenue': getattr(self, 'last_gross_revenue', 0.0),
            'last_net_revenue': getattr(self, 'last_net_revenue', 0.0),
            'last_skim_amount': getattr(self, 'last_skim_amount', 0.0),
            'resource_policy': getattr(self, 'resource_policy', 'state_led'),
            'resource_policy_transition_days': getattr(self, 'resource_policy_transition_days', 0),
            'tier_upgrade_cooldowns': getattr(self, 'tier_upgrade_cooldowns', {}),
            'prerequisite_violations': getattr(self, 'prerequisite_violations', {}),
            'legitimacy_stability': getattr(self, 'legitimacy_stability', 0.0),
            'coercion_stability': getattr(self, 'coercion_stability', 0.0),
            # 9.5B: Two-component stability
            'sudden_collapse_risk': getattr(self, 'sudden_collapse_risk', False),
            'stability_resilient': getattr(self, 'stability_resilient', False),
            'external_stability': getattr(self, 'external_stability', 0.0),
            'prev_legitimacy_stability': getattr(self, 'prev_legitimacy_stability', 0.0),
            'coup_amplifier_active': getattr(self, 'coup_amplifier_active', False),
            'intel_politicized': getattr(self, 'intel_politicized', False),
            'eu_relations_ceiling': getattr(self, 'eu_relations_ceiling', 100),
            'commitment_deficit_days': getattr(self, 'commitment_deficit_days', 0),
            'loyal_generals_installed': getattr(self, 'loyal_generals_installed', False),
            'loyal_intel_chief_installed': getattr(self, 'loyal_intel_chief_installed', False),
            # 9.5C: Loyal leadership tracking
            'loyal_generals_cost_paid': getattr(self, 'loyal_generals_cost_paid', 0.0),
            'loyal_intel_chief_cost_paid': getattr(self, 'loyal_intel_chief_cost_paid', 0.0),
            'loyal_generals_install_day': getattr(self, 'loyal_generals_install_day', 0),
            'loyal_intel_chief_install_day': getattr(self, 'loyal_intel_chief_install_day', 0),
            'loyal_generals_reversing': getattr(self, 'loyal_generals_reversing', False),
            'loyal_intel_chief_reversing': getattr(self, 'loyal_intel_chief_reversing', False),
            'loyal_generals_reversal_day': getattr(self, 'loyal_generals_reversal_day', 0),
            'loyal_intel_chief_reversal_day': getattr(self, 'loyal_intel_chief_reversal_day', 0),
            'intel_distortion_active': getattr(self, 'intel_distortion_active', False),
            'coup_warnings_suppressed': getattr(self, 'coup_warnings_suppressed', False),
            'pending_briefing_items': getattr(self, 'pending_briefing_items', []),
            # 9.5A-Shadow: Shadow State
            'media_tier': getattr(self, 'media_tier', 0),
            'judicial_tier': getattr(self, 'judicial_tier', 0),
            'domestic_surveillance_tier': getattr(self, 'domestic_surveillance_tier', 0),
            'extraction_tier': getattr(self, 'extraction_tier', 0),
            'daily_media_cost': getattr(self, 'daily_media_cost', 0.0),
            'daily_judicial_cost': getattr(self, 'daily_judicial_cost', 0.0),
            'daily_surveillance_cost': getattr(self, 'daily_surveillance_cost', 0.0),
            'daily_extraction_cost': getattr(self, 'daily_extraction_cost', 0.0),
            'daily_militia_cost': getattr(self, 'daily_militia_cost', 0.0),
            'daily_extraction_revenue': getattr(self, 'daily_extraction_revenue', 0.0),
            'total_shadow_commitment': getattr(self, 'total_shadow_commitment', 0.0),
            'shadow_state_unlocked': getattr(self, 'shadow_state_unlocked', False),
            'militia_merged': getattr(self, 'militia_merged', False),
            'surveillance_merged': getattr(self, 'surveillance_merged', False),
            'shadow_tier_cooldowns': getattr(self, 'shadow_tier_cooldowns', {}),
            'advisor_elimination_count': getattr(self, 'advisor_elimination_count', 0),
            'advisor_elimination_last_day': getattr(self, 'advisor_elimination_last_day', 0),
            'advisors_with_fear_bonus': getattr(self, 'advisors_with_fear_bonus', []),
            'advisors_witnessed_elimination': getattr(self, 'advisors_witnessed_elimination', []),
            'advisors_chronically_fearful': getattr(self, 'advisors_chronically_fearful', []),
            # 10C: Operations System
            'ops_legitimate_this_turn': getattr(self, 'ops_legitimate_this_turn', 0),
            'ops_shadow_this_turn': getattr(self, 'ops_shadow_this_turn', 0),
            'arms_export_count': getattr(self, 'arms_export_count', 0),
            'modernization_tranche_1': getattr(self, 'modernization_tranche_1', False),
            'modernization_tranche_2': getattr(self, 'modernization_tranche_2', False),
            'modernization_tranche_3': getattr(self, 'modernization_tranche_3', False),
            'intel_sharing_agreements': getattr(self, 'intel_sharing_agreements', {}),
            'kompromat_holdings': getattr(self, 'kompromat_holdings', {}),
            'kompromat_collection_active': getattr(self, 'kompromat_collection_active', {}),
            'advisor_loyalty_ops': getattr(self, 'advisor_loyalty_ops', {}),
            'counter_intel_cooldown': getattr(self, 'counter_intel_cooldown', 0),
            'targeted_intercept_cooldown': getattr(self, 'targeted_intercept_cooldown', 0),
            'trade_mission_cooldown': getattr(self, 'trade_mission_cooldown', 0),
            'journalist_elimination_available': getattr(self, 'journalist_elimination_available', True),
            'journalist_elimination_day': getattr(self, 'journalist_elimination_day', 0),
            'journalist_elimination_discovery_day': getattr(self, 'journalist_elimination_discovery_day', 0),
            'operations_log': getattr(self, 'operations_log', []),
            'force_projection_modifiers': getattr(self, 'force_projection_modifiers', {}),
            # 10B-1: Daily Briefing System
            'daily_events': getattr(self, 'daily_events', []),
            'events_resolved_today': getattr(self, 'events_resolved_today', 0),
            'events_required_today': getattr(self, 'events_required_today', 3),
            'day_events_generated': getattr(self, 'day_events_generated', False),
            'communique_days_without_response': getattr(self, 'communique_days_without_response', {}),
            'morning_briefing_read': getattr(self, 'morning_briefing_read', False),
            'declarations_available': getattr(self, 'declarations_available', 0),
            'declaration_used_today': getattr(self, 'declaration_used_today', False),
            # 10B-2: Event dialogue, cables, declarations, intel
            'todays_declaration': getattr(self, 'todays_declaration', ''),
            'declaration_history': getattr(self, 'declaration_history', []),
            'event_dialogues': getattr(self, 'event_dialogues', {}),
            'diplomatic_cables': getattr(self, 'diplomatic_cables', {}),
            'cables_generated_today': getattr(self, 'cables_generated_today', False),
            'intel_ops_today': getattr(self, 'intel_ops_today', []),
            'deals_today': getattr(self, 'deals_today', []),
            'contact_requested': getattr(self, 'contact_requested', {}),
        }

    @classmethod
    def deserialize(cls, data):
        """Reconstruct a GameState from a dict (loaded from database)."""
        gs = cls()
        gs.budget = data['budget']
        gs.stability = data['stability']
        gs.oil_price = data['oil_price']
        gs.public_approval = data['public_approval']
        gs.personal_wealth = data['personal_wealth']
        gs.corruption_warned = data['corruption_warned']
        gs.current_turn = data['current_turn']
        gs.max_turns = data['max_turns']
        gs.current_day = data.get('current_day', data['current_turn'])  # fallback for pre-7A saves
        gs.current_era = data.get('current_era', 1)
        gs.era_start_day = data.get('era_start_day', 1)
        gs.era_transitions = data.get('era_transitions', [])
        gs.pending_era_transition = data.get('pending_era_transition', False)
        gs.last_threshold_event = data.get('last_threshold_event', None)
        gs.last_threshold_day = data.get('last_threshold_day', 0)
        gs.relations = data['relations']
        gs.times_sided_with = data['times_sided_with']
        gs.times_ignored = data['times_ignored']
        gs.consecutive_sides = data['consecutive_sides']
        gs.consecutive_ignores = data['consecutive_ignores']
        gs.action_history = data['action_history']
        gs.usa_sanctions_active = data['usa_sanctions_active']
        gs.arabia_embargo_active = data['arabia_embargo_active']
        gs.usa_sanctions_tier = data['usa_sanctions_tier']
        gs.arabia_embargo_tier = data['arabia_embargo_tier']
        gs.took_arabia_oil = data['took_arabia_oil']
        gs.took_usa_side_after_arabia_oil = data['took_usa_side_after_arabia_oil']
        gs.took_arabia_side_after_usa_alliance = data['took_arabia_side_after_usa_alliance']
        gs.blackmail_used = data['blackmail_used']
        gs.npc_relations = data.get('npc_relations', {
            'arabia_dprg': 45, 'arabia_eu': 25, 'arabia_usa': 30,
            'dprg_eu': 15, 'dprg_usa': 10, 'eu_usa': 75,
            'china_russia': 45, 'russia_usa': 15, 'china_usa': 25,
            'eu_russia': 20, 'china_eu': 50, 'arabia_russia': 40,
            'china_dprg': 35, 'arabia_china': 40, 'dprg_russia': 30,
        })
        gs.pressure_suspended = data.get('pressure_suspended', {})
        gs.approval_penalty_reduction = data.get('approval_penalty_reduction', 0.0)
        gs.current_event = data.get('current_event', None)
        gs.options_override = data.get('options_override', None)
        gs.oil_price_locked = data.get('oil_price_locked', False)
        gs.oil_price_lock_value = data.get('oil_price_lock_value', 0.0)
        gs.oil_price_lock_turns_remaining = data.get('oil_price_lock_turns_remaining', 0)
        gs.active_trade_commitments = data.get('active_trade_commitments', [])
        gs.active_installments = data.get('active_installments', [])
        # FIX D (session 6): Migrate inverted deal conditions from old parser bug.
        # EU deals with "DPRG above X" should be "DPRG below X" (Marsha demands DPRG distance).
        import re as _re_d
        for _inst in gs.active_installments:
            _ct = _inst.get('condition_type', '')
            if _ct and _ct not in ('relation_below', 'relation_above'):
                # Freeform condition — attempt to normalize
                _ct_lower = str(_ct).lower()
                if 'above' in _ct_lower or 'over' in _ct_lower:
                    _m = _re_d.search(r'(\d+)', _ct_lower)
                    if _m:
                        _thresh = int(_m.group(1))
                        # EU deals with "DPRG above X" are inverted — should be "below"
                        _inst_npc = (_inst.get('npc') or '').lower()
                        if _inst_npc in ('eu', 'marsha'):
                            _inst['condition_type'] = 'relation_below'
                            _inst['condition_npc'] = 'dprg'
                            _inst['condition_threshold'] = _thresh
                            print(f"  [game_state] FIX D MIGRATED: inverted EU deal condition -> relation_below dprg {_thresh}")
                        else:
                            _inst['condition_type'] = 'relation_above'
                            _npc_match = _re_d.search(r'(dprg|usa|eu|arabia)', _ct_lower)
                            if _npc_match:
                                _inst['condition_npc'] = _npc_match.group(1)
                            _inst['condition_threshold'] = _thresh
                            print(f"  [game_state] FIX D MIGRATED: normalized condition -> relation_above {_inst.get('condition_npc')} {_thresh}")
        gs.oil_price_modifiers = data.get('oil_price_modifiers', [])
        # Stage 5
        gs.state_identity = data.get('state_identity', {
            'regime_type': 'Managed Democracy',
            'power_base': 'Mass-Dependent',
        })
        gs.consecutive_large_skims = data.get('consecutive_large_skims', 0)
        gs.low_approval_turns = data.get('low_approval_turns', 0)
        gs.high_approval_turns = data.get('high_approval_turns', 0)
        gs.corruption_upgrades = data.get('corruption_upgrades', {
            'intelligence_apparatus': False,
            'sovereign_wealth_diversion': False,
            'loyalty_brigades': False,
            'debt_infrastructure_deal': False,
        })
        gs.historian_summary = data.get('historian_summary', None)  # fixes_12 Fix 4
        gs.pw_ledger = data.get('pw_ledger', [])
        gs.negotiate_costs_this_turn = data.get('negotiate_costs_this_turn', 0.0)
        gs.negotiate_sessions_this_turn = data.get('negotiate_sessions_this_turn', 0)
        # Session 2
        gs.brigades_deployed_last_turn = data.get('brigades_deployed_last_turn', False)
        gs.covert_security_unlocked = data.get('covert_security_unlocked', False)
        gs.intel = data.get('intel', {})
        gs.intel_activated_this_turn = data.get('intel_activated_this_turn', {})
        gs.deal_history = data.get('deal_history', [])
        gs.pending_gm_consequences = data.get('pending_gm_consequences', [])
        gs.ignored_communiques = data.get('ignored_communiques', {})
        gs.npcs_interacted_this_turn = data.get('npcs_interacted_this_turn', [])
        gs.budget_last_eot = data.get('budget_last_eot', None)
        gs.previous_oil_base = data.get('previous_oil_base', 75)
        gs.negotiation_log = data.get('negotiation_log', [])
        gs.total_aid_received = data.get('total_aid_received', {'usa': 0.0, 'arabia': 0.0, 'eu': 0.0, 'dprg': 0.0, 'russia': 0.0, 'china': 0.0})
        gs.current_rapport = data.get('current_rapport', {})
        gs.binding_promises = data.get('binding_promises', [])
        gs.detection_heat = data.get('detection_heat', 0)
        gs.scandals_triggered = data.get('scandals_triggered', 0)
        gs.last_scandal_turn = data.get('last_scandal_turn', 0)
        gs.leverage_events = data.get('leverage_events', {})
        gs.pressure_events_fired = data.get('pressure_events_fired', [])
        gs.relations_100_unlocks = data.get('relations_100_unlocks', {
            'usa': False, 'arabia': False, 'eu': False, 'dprg': False,
            'russia': False, 'china': False,
        })
        # Pre-Session 4: Legacy tracking
        gs.regime_history = data.get('regime_history', [])
        gs.total_skimmed = data.get('total_skimmed', 0.0)
        gs.peak_personal_wealth = data.get('peak_personal_wealth', 0.0)
        gs.relations_high = data.get('relations_high', dict(gs.relations))
        gs.relations_low = data.get('relations_low', dict(gs.relations))
        gs.corruption_events_fired = data.get('corruption_events_fired', [])
        gs.upgrades_purchased_log = data.get('upgrades_purchased_log', [])
        gs.sanctions_active_turns = data.get('sanctions_active_turns', 0)
        gs.embargo_active_turns = data.get('embargo_active_turns', 0)
        # ITEM 3: Military Strength
        gs.military_strength = data.get('military_strength', 20)
        # Session 4B: Election Mechanic (migration for old saves)
        gs.election_turn = data.get('election_turn', 4)
        gs.election_fired = data.get('election_fired', False)
        gs.election_result = data.get('election_result', None)
        gs.election_warning_shown = data.get('election_warning_shown', False)
        gs.regime_democracy_locked = data.get('regime_democracy_locked', 0)
        gs.protests_pending = data.get('protests_pending', False)
        if 'election_turn' not in data:
            print("  [game_state] ELECTION FIELDS MIGRATED: added defaults to old save")
        # Session 4C: Domestic Actions (migration for old saves)
        gs.action_media_taken = data.get('action_media_taken', False)
        gs.action_judiciary_captured = data.get('action_judiciary_captured', False)
        gs.action_press_suppressed = data.get('action_press_suppressed', False)
        gs.action_opposition_dissolved = data.get('action_opposition_dissolved', False)
        gs.action_journalists_liquidated = data.get('action_journalists_liquidated', False)
        gs.domestic_actions_enacted_turns = data.get('domestic_actions_enacted_turns', {})
        gs.approval_floor = data.get('approval_floor', 0)
        gs.approval_ceiling = data.get('approval_ceiling', 100)
        gs.scandal_immune = data.get('scandal_immune', False)
        gs.coup_immune = data.get('coup_immune', False)
        gs.marsha_red_line_triggered = data.get('marsha_red_line_triggered', False)
        if 'action_media_taken' not in data:
            print("  [game_state] DOMESTIC ACTION FIELDS MIGRATED: added defaults to old save")
        # Session 4D: Tech Level, Intel Budget, Alternate Endings (migration for old saves)
        gs.tech_level = float(data.get('tech_level', 0))
        gs.tech_sources = data.get('tech_sources', [])
        gs.tech_gain_last_turn = data.get('tech_gain_last_turn', 0.0)
        gs.middle_power_transition = data.get('middle_power_transition', False)
        gs.intel_budget = data.get('intel_budget', 0.0)
        gs.intel_budget_allocation = data.get('intel_budget_allocation', 'maintenance')
        gs.intel_turns_unfunded = data.get('intel_turns_unfunded', 0)
        gs.budget_allocation = data.get('budget_allocation', {
            "military": 20, "intelligence": 20, "public_services": 20,
            "infrastructure": 20, "diplomacy": 20,
        })
        gs.ending_triggered = data.get('ending_triggered', None)
        gs.martyrdom_triggered = data.get('martyrdom_triggered', False)
        gs.turns_no_suppression = data.get('turns_no_suppression', 0)
        if 'tech_level' not in data:
            print("  [game_state] SESSION 4D FIELDS MIGRATED: added defaults to old save")
        # Session 5: Shadow Cabinet Five Axes
        gs.cabinet_axes = data.get('cabinet_axes', {'military': 0, 'intelligence': 0, 'resource_dev': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0})
        gs.cabinet_maintenance_paid = data.get('cabinet_maintenance_paid', 0.0)
        gs.extraction_injections_given = data.get('extraction_injections_given', [])
        # fixes_16 Fix C: Extraction milestones
        gs.extraction_l5_fired = data.get('extraction_l5_fired', False)
        gs.extraction_l7_fired = data.get('extraction_l7_fired', False)
        # Session 6: Military axis action state
        gs.defense_procurement_count = data.get('defense_procurement_count', 0)
        gs.defense_procurement_turn = data.get('defense_procurement_turn', -1)
        gs.force_projection_target = data.get('force_projection_target', None)
        gs.force_projection_cooldown = data.get('force_projection_cooldown', 0)
        gs.arms_export_this_turn = data.get('arms_export_this_turn', None)
        # Session 6: Intelligence axis action state
        gs.intel_sharing_target = data.get('intel_sharing_target', None)
        # Session 6: Media axis action state
        gs.scandal_suppressed_this_turn = data.get('scandal_suppressed_this_turn', False)
        gs.info_blackout_turns = data.get('info_blackout_turns', 0)
        # Session 6: Judicial axis action state
        gs.drop_investigation_this_turn = data.get('drop_investigation_this_turn', False)
        gs.lawfare_target = data.get('lawfare_target', None)
        gs.lawfare_turns = data.get('lawfare_turns', 0)
        # Session 6: Political axis action state
        gs.party_consolidation_turns = data.get('party_consolidation_turns', 0)
        gs.fourth_advisor_slot = data.get('fourth_advisor_slot', False)
        gs.constitutional_revision_active = data.get('constitutional_revision_active', False)
        # Session 6: Extraction axis action state
        gs.private_security_force = data.get('private_security_force', False)
        gs.private_security_strength = data.get('private_security_strength', 0)
        gs.offshore_transfer_this_turn = data.get('offshore_transfer_this_turn', False)
        # Session 6: Resource Development axis action state
        gs.export_contract_used = data.get('export_contract_used', False)
        gs.gdp_credibility_active = data.get('gdp_credibility_active', False)
        gs.sovereign_collateral_used = data.get('sovereign_collateral_used', False)
        gs.sovereign_collateral_repayment = data.get('sovereign_collateral_repayment', 0.0)
        gs.sovereign_collateral_turns = data.get('sovereign_collateral_turns', 0)
        gs.strategic_resource_partner = data.get('strategic_resource_partner', None)
        gs.resource_independence_active = data.get('resource_independence_active', False)
        gs.leverage_marsha_media_fired = data.get('leverage_marsha_media_fired', False)
        gs.leverage_bill_opposition_fired = data.get('leverage_bill_opposition_fired', False)
        gs.leverage_sadam_judicial_fired = data.get('leverage_sadam_judicial_fired', False)
        gs.leverage_jiwon_press_fired = data.get('leverage_jiwon_press_fired', False)
        # fixes_13: Bond financing + covert deals
        gs.bonds_issued_count = data.get('bonds_issued_count', 0)
        gs.small_bond_last_turn = data.get('small_bond_last_turn', -1)
        gs.large_bond_used = data.get('large_bond_used', False)
        gs.covert_deals = data.get('covert_deals', [])
        # fixes_13 Fix 26: Black Operations state
        gs.pressure_suspensions = data.get('pressure_suspensions', [])
        gs.blackmail_ops_used = data.get('blackmail_ops_used', [])
        gs.npc_intel_tiers = data.get('npc_intel_tiers', {})
        gs.bilateral_damages = data.get('bilateral_damages', [])
        gs.cross_npc_penalty_reductions = data.get('cross_npc_penalty_reductions', [])
        # fixes_13 Fix 27: NPC 100 unlock state
        gs.relations_caps = data.get('relations_caps', {})
        gs.dprg_coup_deterrence = data.get('dprg_coup_deterrence', False)
        # fixes_13 Fix 28: Emergency tax event
        gs.emergency_tax_event_fired = data.get('emergency_tax_event_fired', False)
        # 8A: Russia/China migration — inject into relations dict from legacy fields
        if 'russia' not in gs.relations:
            gs.relations['russia'] = data.get('russia_relations', 35.0)
            print("  [game_state] MIGRATION: injected russia from legacy field")
        if 'china' not in gs.relations:
            gs.relations['china'] = data.get('china_relations', 35.0)
            print("  [game_state] MIGRATION: injected china from legacy field")
        # 8A: Ensure all tracking dicts have russia/china keys
        for _npc in ('russia', 'china'):
            gs.times_sided_with.setdefault(_npc, 0)
            gs.times_ignored.setdefault(_npc, 0)
            gs.consecutive_sides.setdefault(_npc, 0)
            gs.consecutive_ignores.setdefault(_npc, 0)
            gs.total_aid_received.setdefault(_npc, 0.0)
            gs.relations_high.setdefault(_npc, gs.relations.get(_npc, 35.0))
            gs.relations_low.setdefault(_npc, gs.relations.get(_npc, 35.0))
            gs.relations_100_unlocks.setdefault(_npc, False)
        # 8A: Ensure bilateral pairs exist
        _bilateral_defaults = {
            'china_russia': 45, 'russia_usa': 15, 'china_usa': 25,
            'eu_russia': 20, 'china_eu': 50, 'arabia_russia': 40,
            'china_dprg': 35, 'arabia_china': 40, 'dprg_russia': 30,
        }
        for _pair, _val in _bilateral_defaults.items():
            gs.npc_relations.setdefault(_pair, _val)
        # Session 7D: Backchannel System
        gs.backchannel_history = data.get('backchannel_history', [])
        gs.active_backchannel_promises = data.get('active_backchannel_promises', [])
        gs.opsec_level = data.get('opsec_level', 0)
        # Session 7E: UN Summit System
        gs.summit_due = data.get('summit_due', False)
        gs.summit_history = data.get('summit_history', [])
        gs.active_summit_commitments = data.get('active_summit_commitments', [])
        gs.summit_credibility = data.get('summit_credibility', 100.0)
        # Advisor System v2: full 9-archetype with gates
        _raw_advisors = data.get('advisors', {})
        # Migration: old formats -> v2 archetype dict
        _V1_ARCHETYPES = {'security_chief', 'diplomatic_aide', 'enforcer'}
        if isinstance(_raw_advisors, list):
            gs.advisors = {}  # old list format — start fresh
            print("  [game_state] ADVISOR MIGRATION: old list format -> v2")
        elif isinstance(_raw_advisors, dict):
            # Check for v1 archetypes or missing v2 fields
            _needs_migration = False
            for _k, _v in _raw_advisors.items():
                if isinstance(_v, dict):
                    if 'archetype' not in _v:
                        _needs_migration = True
                        break
                    if _v.get('archetype') in _V1_ARCHETYPES:
                        _needs_migration = True
                        break
                    if 'competence' not in _v:
                        _needs_migration = True
                        break
            if _needs_migration:
                gs.advisors = {}  # v1 format — start fresh for v2
                print("  [game_state] ADVISOR MIGRATION: v1 format -> v2 (fresh start)")
            else:
                gs.advisors = _raw_advisors
        else:
            gs.advisors = {}
        gs.advisor_slots_available = data.get('advisor_slots_available', 2)
        gs.advisor_pool = data.get('advisor_pool', [])
        # Migrate pool too — remove v1 archetypes from pool
        if gs.advisor_pool:
            gs.advisor_pool = [a for a in gs.advisor_pool
                               if isinstance(a, dict) and a.get('archetype') not in _V1_ARCHETYPES
                               and 'competence' in a]
        gs.advisors_eliminated = data.get('advisors_eliminated', [])
        gs.advisor_actions_log = data.get('advisor_actions_log', [])
        gs.advisor_distortions = data.get('advisor_distortions', {})
        gs.advisor_analyses = data.get('advisor_analyses', {})
        gs.advisor_assigned_today = data.get('advisor_assigned_today', [])
        gs._general_coup_boost_turns = data.get('_general_coup_boost_turns', 0)
        gs._general_elim_decay_turns = data.get('_general_elim_decay_turns', 0)
        # Session 5: Economic Development Model
        gs.tax_rates = data.get('tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
        gs.gdp_base = data.get('gdp_base', 100.0)
        gs.gdp_growth_rate = data.get('gdp_growth_rate', 0.02)
        gs.revenue_streams = data.get('revenue_streams', {
            'income_tax': 0.0, 'corporate_tax': 0.0, 'resource_tax': 0.0,
            'trade_tariffs': 0.0, 'foreign_aid': 0.0, 'tourism': 0.0,
            'arms_exports': 0.0, 'financial_sector': 0.0,
        })
        gs.resource_endowment = data.get('resource_endowment', {
            'oil_reserves': 0.7, 'mineral_deposits': 0.3, 'arable_land': 0.4,
            'rare_earths': 0.1, 'coastal_access': 0.6,
        })
        gs.soft_power = data.get('soft_power', 0)
        gs.diplomatic_capital = data.get('diplomatic_capital', 0)
        # Session 5: NPC-Initiated Contact
        gs.npc_contact_history = data.get('npc_contact_history', {})
        gs.pending_npc_contacts = data.get('pending_npc_contacts', [])
        # Session 5: Brigade Operations
        gs.brigade_operations_this_turn = data.get('brigade_operations_this_turn', [])
        # 8B: Education System (safe defaults for pre-8B saves)
        gs.education_level = data.get('education_level', 0)
        gs.education_allocation = data.get('education_allocation', 0.0)
        gs.education_decay_clock = data.get('education_decay_clock', 0)
        gs.education_gain_progress = data.get('education_gain_progress', 0.0)
        if 'education_level' not in data:
            print("  [game_state] 8B EDUCATION FIELDS MIGRATED: added defaults to old save")
        # 8C: Exile Sequence (safe defaults for pre-8C saves)
        gs.in_exile = data.get('in_exile', False)
        gs.exile_trigger = data.get('exile_trigger', None)
        gs.exile_destination = data.get('exile_destination', None)
        gs.exile_day = data.get('exile_day', 0)
        gs.exile_backing = data.get('exile_backing', None)
        gs.exile_backing_committed = data.get('exile_backing_committed', False)
        gs.exile_wealth_at_collapse = data.get('exile_wealth_at_collapse', 0.0)
        gs.exile_apparatus_survived = data.get('exile_apparatus_survived', False)
        gs.exile_apparatus_detection_risk_modifier = data.get('exile_apparatus_detection_risk_modifier', 1.0)
        gs.successor_name = data.get('successor_name', None)
        gs.successor_disposition = data.get('successor_disposition', None)
        gs.successor_events_fired = data.get('successor_events_fired', [])
        gs.backing_doors_closed = data.get('backing_doors_closed', [])
        gs.exile_historian_note = data.get('exile_historian_note', None)
        if 'in_exile' not in data:
            print("  [game_state] 8C EXILE FIELDS MIGRATED: added defaults to old save")
        # 9A: Comeback Mechanics (safe defaults for pre-9A saves)
        gs.departure_heat = data.get('departure_heat', 0)
        gs.return_progress = data.get('return_progress', 0.0)
        gs.return_attempts = data.get('return_attempts', 0)
        gs.return_threshold = data.get('return_threshold', 100.0)
        gs.npc_assistance_tiers = data.get('npc_assistance_tiers', {})
        gs.faction_contacts = data.get('faction_contacts', {})
        gs.wealth_action_cooldowns = data.get('wealth_action_cooldowns', {})
        gs.detection_events = data.get('detection_events', [])
        gs.restoration_active = data.get('restoration_active', False)
        gs.restoration_grace_days = data.get('restoration_grace_days', 0)
        gs.restoration_democratic_tally = data.get('restoration_democratic_tally', 0)
        gs.restoration_authoritarian_tally = data.get('restoration_authoritarian_tally', 0)
        gs.prior_regime_label = data.get('prior_regime_label', '')
        gs.exile_entry_gdp = data.get('exile_entry_gdp', 0.0)
        gs.exile_entry_relations = data.get('exile_entry_relations', {})
        gs.successor_archetype = data.get('successor_archetype', None)
        gs.successor_hostility = data.get('successor_hostility', 0)
        gs.exile_successor_log = data.get('exile_successor_log', [])
        gs.exile_actions_log = data.get('exile_actions_log', [])
        if 'departure_heat' not in data:
            print("  [game_state] 9A COMEBACK FIELDS MIGRATED: added defaults to old save")
        # 8D: The Leak (safe defaults for pre-8D saves)
        gs.the_leak_fired = data.get('the_leak_fired', False)
        gs.the_leak_resolved = data.get('the_leak_resolved', False)
        gs.the_leak_choice = data.get('the_leak_choice', None)
        gs.the_leak_followup_fired = data.get('the_leak_followup_fired', False)
        gs.scapegoat_used = data.get('scapegoat_used', False)
        if 'the_leak_fired' not in data:
            print("  [game_state] 8D LEAK FIELDS MIGRATED: added defaults to old save")
        # 9.5A: Commitment Model fields
        gs.military_tier = data.get('military_tier', 1)
        gs.intelligence_tier = data.get('intelligence_tier', 1)
        gs.diplomatic_tier = data.get('diplomatic_tier', 0)
        gs.social_tier = data.get('social_tier', 1)
        gs.education_tier = data.get('education_tier', gs.education_level)  # sync from education_level
        gs.resource_tier = data.get('resource_tier', 0)
        gs.political_tier = data.get('political_tier', 0)
        gs.militia_tier = data.get('militia_tier', 0)
        gs.daily_military_cost = data.get('daily_military_cost', 0.0)
        gs.daily_intel_cost = data.get('daily_intel_cost', 0.0)
        gs.daily_diplomatic_cost = data.get('daily_diplomatic_cost', 0.0)
        gs.daily_social_cost = data.get('daily_social_cost', 0.0)
        gs.daily_education_cost = data.get('daily_education_cost', 0.0)
        gs.daily_resource_cost = data.get('daily_resource_cost', 0.0)
        gs.total_daily_commitment = data.get('total_daily_commitment', 0.0)
        gs.income_tax_rate = data.get('income_tax_rate', 0.25)
        gs.corporate_tax_rate = data.get('corporate_tax_rate', 0.20)
        gs.tax_structure = data.get('tax_structure', 'balanced')
        gs.skim_rate = data.get('skim_rate', 0.0)
        gs.last_gross_revenue = data.get('last_gross_revenue', 0.0)
        gs.last_net_revenue = data.get('last_net_revenue', 0.0)
        gs.last_skim_amount = data.get('last_skim_amount', 0.0)
        gs.resource_policy = data.get('resource_policy', 'state_led')
        gs.resource_policy_transition_days = data.get('resource_policy_transition_days', 0)
        gs.tier_upgrade_cooldowns = data.get('tier_upgrade_cooldowns', {})
        gs.prerequisite_violations = data.get('prerequisite_violations', {})
        gs.legitimacy_stability = data.get('legitimacy_stability', gs.stability * 0.70)
        gs.coercion_stability = data.get('coercion_stability', gs.stability * 0.30)
        # 9.5B: Two-component stability
        gs.sudden_collapse_risk = data.get('sudden_collapse_risk', False)
        gs.stability_resilient = data.get('stability_resilient', False)
        gs.external_stability = data.get('external_stability', 0.0)
        gs.prev_legitimacy_stability = data.get('prev_legitimacy_stability', 0.0)
        gs.coup_amplifier_active = data.get('coup_amplifier_active', False)
        gs.intel_politicized = data.get('intel_politicized', False)
        gs.eu_relations_ceiling = data.get('eu_relations_ceiling', 100)
        gs.commitment_deficit_days = data.get('commitment_deficit_days', 0)
        gs.loyal_generals_installed = data.get('loyal_generals_installed', False)
        gs.loyal_intel_chief_installed = data.get('loyal_intel_chief_installed', False)
        # 9.5C: Loyal leadership tracking
        gs.loyal_generals_cost_paid = data.get('loyal_generals_cost_paid', 0.0)
        gs.loyal_intel_chief_cost_paid = data.get('loyal_intel_chief_cost_paid', 0.0)
        gs.loyal_generals_install_day = data.get('loyal_generals_install_day', 0)
        gs.loyal_intel_chief_install_day = data.get('loyal_intel_chief_install_day', 0)
        gs.loyal_generals_reversing = data.get('loyal_generals_reversing', False)
        gs.loyal_intel_chief_reversing = data.get('loyal_intel_chief_reversing', False)
        gs.loyal_generals_reversal_day = data.get('loyal_generals_reversal_day', 0)
        gs.loyal_intel_chief_reversal_day = data.get('loyal_intel_chief_reversal_day', 0)
        gs.intel_distortion_active = data.get('intel_distortion_active', False)
        gs.coup_warnings_suppressed = data.get('coup_warnings_suppressed', False)
        gs.pending_briefing_items = data.get('pending_briefing_items', [])
        # 9.5A-Shadow: Shadow State (safe defaults for pre-shadow saves)
        gs.media_tier = data.get('media_tier', 0)
        gs.judicial_tier = data.get('judicial_tier', 0)
        gs.domestic_surveillance_tier = data.get('domestic_surveillance_tier', 0)
        gs.extraction_tier = data.get('extraction_tier', 0)
        gs.daily_media_cost = data.get('daily_media_cost', 0.0)
        gs.daily_judicial_cost = data.get('daily_judicial_cost', 0.0)
        gs.daily_surveillance_cost = data.get('daily_surveillance_cost', 0.0)
        gs.daily_extraction_cost = data.get('daily_extraction_cost', 0.0)
        gs.daily_militia_cost = data.get('daily_militia_cost', 0.0)
        gs.daily_extraction_revenue = data.get('daily_extraction_revenue', 0.0)
        gs.total_shadow_commitment = data.get('total_shadow_commitment', 0.0)
        gs.shadow_state_unlocked = data.get('shadow_state_unlocked', False)
        gs.militia_merged = data.get('militia_merged', False)
        gs.surveillance_merged = data.get('surveillance_merged', False)
        gs.shadow_tier_cooldowns = data.get('shadow_tier_cooldowns', {})
        gs.advisor_elimination_count = data.get('advisor_elimination_count', 0)
        gs.advisor_elimination_last_day = data.get('advisor_elimination_last_day', 0)
        gs.advisors_with_fear_bonus = data.get('advisors_with_fear_bonus', [])
        gs.advisors_witnessed_elimination = data.get('advisors_witnessed_elimination', [])
        gs.advisors_chronically_fearful = data.get('advisors_chronically_fearful', [])
        # 10C: Operations System
        gs.ops_legitimate_this_turn = data.get('ops_legitimate_this_turn', 0)
        gs.ops_shadow_this_turn = data.get('ops_shadow_this_turn', 0)
        gs.arms_export_count = data.get('arms_export_count', 0)
        gs.modernization_tranche_1 = data.get('modernization_tranche_1', False)
        gs.modernization_tranche_2 = data.get('modernization_tranche_2', False)
        gs.modernization_tranche_3 = data.get('modernization_tranche_3', False)
        gs.intel_sharing_agreements = data.get('intel_sharing_agreements', {})
        gs.kompromat_holdings = data.get('kompromat_holdings', {})
        gs.kompromat_collection_active = data.get('kompromat_collection_active', {})
        gs.advisor_loyalty_ops = data.get('advisor_loyalty_ops', {})
        gs.counter_intel_cooldown = data.get('counter_intel_cooldown', 0)
        gs.targeted_intercept_cooldown = data.get('targeted_intercept_cooldown', 0)
        gs.trade_mission_cooldown = data.get('trade_mission_cooldown', 0)
        gs.journalist_elimination_available = data.get('journalist_elimination_available', True)
        gs.journalist_elimination_day = data.get('journalist_elimination_day', 0)
        gs.journalist_elimination_discovery_day = data.get('journalist_elimination_discovery_day', 0)
        gs.operations_log = data.get('operations_log', [])
        gs.force_projection_modifiers = data.get('force_projection_modifiers', {})
        # 10B-1: Daily Briefing System
        gs.daily_events = data.get('daily_events', [])
        gs.events_resolved_today = data.get('events_resolved_today', 0)
        gs.events_required_today = data.get('events_required_today', 3)
        gs.day_events_generated = data.get('day_events_generated', False)
        gs.communique_days_without_response = data.get('communique_days_without_response', {})
        gs.morning_briefing_read = data.get('morning_briefing_read', False)
        gs.declarations_available = data.get('declarations_available', 0)
        gs.declaration_used_today = data.get('declaration_used_today', False)
        # 10B-2: Event dialogue, cables, declarations, intel
        gs.todays_declaration = data.get('todays_declaration', '')
        gs.declaration_history = data.get('declaration_history', [])
        gs.event_dialogues = data.get('event_dialogues', {})
        gs.diplomatic_cables = data.get('diplomatic_cables', {})
        gs.cables_generated_today = data.get('cables_generated_today', False)
        gs.intel_ops_today = data.get('intel_ops_today', [])
        gs.deals_today = data.get('deals_today', [])
        gs.contact_requested = data.get('contact_requested', {})
        if 'daily_events' not in data:
            print("  [game_state] 10B-1 BRIEFING FIELDS MIGRATED: added defaults to old save")
        if 'ops_legitimate_this_turn' not in data:
            print("  [game_state] 10C OPERATIONS FIELDS MIGRATED: added defaults to old save")
        if 'media_tier' not in data:
            print("  [game_state] 9.5A-SHADOW FIELDS MIGRATED: added defaults to old save")
        # Sync resource_tier from cabinet_axes for old saves
        if 'resource_tier' not in data:
            gs.resource_tier = gs.cabinet_axes.get('resource_dev', 0)
        if 'military_tier' not in data:
            print("  [game_state] 9.5A COMMITMENT FIELDS MIGRATED: added defaults to old save")
        if 'cabinet_axes' not in data:
            print("  [game_state] SESSION 5 FIELDS MIGRATED: added defaults to old save")
            _migrate_to_axes(gs)
        # Session 6: Migrate old 'security' key to military + intelligence
        if 'security' in gs.cabinet_axes:
            _migrate_security_to_split(gs)
        # Ensure military/intelligence/resource_dev keys exist on old saves
        gs.cabinet_axes.setdefault('military', 0)
        gs.cabinet_axes.setdefault('intelligence', 0)
        gs.cabinet_axes.setdefault('resource_dev', 0)
        return gs
