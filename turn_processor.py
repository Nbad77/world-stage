"""
Turn Processor - Handles consequences, end-of-turn effects, game over detection
VERSION 3: Tiered sanctions/embargo/pressure, passive drain, approval system, legacy titles
Session 3 additions: detection risk system, relation source annotations
Session 4B: Election mechanic
"""

import random
import re


# ── Session 4B: Election Consequences (hard-coded, Claude never decides these) ──

ELECTION_CONSEQUENCES = {
    "fair_success": {
        "eu": +8, "usa": +5, "stability": +5, "approval": +3,
        "regime_pressure": "left"
    },
    "fair_squeaker": {
        "eu": +3, "usa": +3, "stability": -3, "approval": +2,
        "regime_pressure": "none"
    },
    "fair_fail": {
        "stability": -15, "approval": -10,
        "protests_pending": True,
        "regime_pressure": "collapse_risk"
    },
    "rigged": {
        "eu": -5, "usa": -3, "dprg": 0, "arabia": 0,
        "stability": +3, "heat": +10,
        "personal_cost": 2.0,
        "regime_pressure": "right_one"
    },
    "canceled": {
        "eu": -15, "usa": -10, "dprg": +5,
        "stability": +10, "approval": -15,
        "heat": +20,
        "protests_pending": True,
        "regime_pressure": "right_two"
    },
    "observers": {
        "eu": +15, "usa": +10, "stability": -2,
        "personal_cost": 1.0,
        "regime_democracy_locked": 3
    }
}

_REGIME_ORDER = [
    'Managed Democracy',
    'Soft Authoritarianism',
    'Patronage State',
    'Kleptocracy',
    'Totalitarian Regime',
]

# ── 8B: Education System — Tunable Constants ──────────────────────────────────
# Level names: 0=Underdeveloped, 1=Basic, 2=Developed, 3=Advanced
EDUCATION_LEVEL_NAMES = ['Underdeveloped', 'Basic', 'Developed', 'Advanced']

# Spending thresholds ($B/turn) to make progress toward next level
EDUCATION_GAIN_THRESHOLDS = {
    0: 2.0,   # $2B/turn to progress from L0 -> L1
    1: 4.0,   # $4B/turn to progress from L1 -> L2
    2: 7.0,   # $7B/turn to progress from L2 -> L3
}
# Base rate of progress per turn when allocation meets threshold (0.0-1.0)
BASE_EDUCATION_RATE = 0.20   # ~5 turns to level up at threshold spending
# Bonus rate per $1B above threshold
EDUCATION_OVERSPEND_RATE = 0.03

# Maintenance: minimum allocation to avoid decay at current level
EDUCATION_MAINTENANCE = {
    1: 1.5,   # $1.5B/turn to maintain Basic
    2: 3.0,   # $3.0B/turn to maintain Developed
    3: 5.0,   # $5.0B/turn to maintain Advanced
}
# Grace period: days below maintenance before decay starts
EDUCATION_DECAY_GRACE = 5
# Decay rate per turn once grace period expires
EDUCATION_DECAY_RATE = 0.25  # ~4 turns of underfunding to lose a level

# Effects per education level
EDUCATION_GDP_MODIFIER = {0: 0.0, 1: 0.005, 2: 0.015, 3: 0.03}  # added to GDP growth rate
EDUCATION_TAX_MODIFIER = {0: 0.0, 1: 0.02, 2: 0.05, 3: 0.10}    # tax revenue multiplier bonus
EDUCATION_STABILITY_BONUS = {0: 0, 1: 0, 2: 1, 3: 2}             # flat stability gain per turn
EDUCATION_APPROVAL_FLOOR = {0: 0, 1: 0, 2: 5, 3: 12}             # minimum approval from education
EDUCATION_APPROVAL_SENSITIVITY = {0: 1.0, 1: 0.95, 2: 0.85, 3: 0.70}  # multiplier on negative approval changes
EDUCATION_COUP_RESISTANCE = {0: 0.0, 1: 0.0, 2: 0.05, 3: 0.15}  # subtracted from coup probability

# Brain drain: if education_level >= 2 AND stability < 30, risk losing progress
BRAIN_DRAIN_STABILITY_THRESHOLD = 30
BRAIN_DRAIN_PROGRESS_LOSS = 0.10  # lose 10% progress per turn when triggered


# ── 9.5A: Commitment Model — Tier Cost Tables ────────────────────────────────

TIER_COSTS = {
    "military": {
        0: 0.0, 1: 0.5, 2: 0.9, 3: 1.4, 4: 2.0,
        5: 2.7, 6: 3.5, 7: 4.4, 8: 5.5, 9: 7.0,
        10: 9.0
    },
    "intelligence": {
        0: 0.0, 1: 0.3, 2: 0.6, 3: 1.0, 4: 1.5,
        5: 2.1, 6: 2.8, 7: 3.6, 8: 4.5, 9: 5.5,
        10: 7.0
    },
    "diplomatic": {
        0: 0.0, 1: 0.3, 2: 0.6, 3: 1.0, 4: 1.5,
        5: 2.0, 6: 2.6, 7: 3.3, 8: 4.1, 9: 5.0,
        10: 6.5
    },
    "social": {
        0: 0.0, 1: 0.4, 2: 0.8, 3: 1.4, 4: 2.0,
        5: 2.7, 6: 3.5, 7: 4.4, 8: 5.5, 9: 6.5,
        10: 8.0
    },
    "education": {
        0: 0.0, 1: 0.3, 2: 0.7, 3: 1.2, 4: 1.8,
        5: 2.5, 6: 3.2, 7: 4.0, 8: 5.0, 9: 6.0,
        10: 7.5
    },
    "resource": {
        0: 0.0, 1: 0.5, 2: 0.9, 3: 1.4, 4: 2.0,
        5: 2.7, 6: 3.5, 7: 4.3, 8: 5.2, 9: 6.2,
        10: 7.5
    },
    "political": {
        # Political axis advances through actions, not spending.
        # Cost here = patronage/maintenance cost of political control.
        0: 0.0, 1: 0.2, 2: 0.4, 3: 0.7, 4: 1.1,
        5: 1.6, 6: 2.2, 7: 2.9, 8: 3.7, 9: 4.6,
        10: 6.0
    },
    "militia": {
        # Militia funded from personal wealth, not national budget.
        # Costs here are personal wealth per day, not budget drain.
        0: 0.0, 1: 0.3, 2: 0.7, 3: 1.2, 4: 1.8,
        5: 2.5, 6: 3.3, 7: 4.2, 8: 5.2, 9: 6.3,
        10: 7.5
    },
}

TIER_UPGRADE_COOLDOWNS = {
    "military":     {1:2, 2:3, 3:5, 4:7, 5:9, 6:12, 7:14, 8:18, 9:22, 10:28},
    "intelligence": {1:2, 2:3, 3:5, 4:7, 5:9, 6:12, 7:15, 8:18, 9:22, 10:28},
    "diplomatic":   {1:2, 2:3, 3:4, 4:6, 5:8, 6:10, 7:13, 8:16, 9:20, 10:25},
    "social":       {1:2, 2:3, 3:5, 4:7, 5:9, 6:12, 7:15, 8:18, 9:22, 10:28},
    "education":    {1:3, 2:4, 3:6, 4:8, 5:10, 6:13, 7:16, 8:20, 9:25, 10:30},
    "resource":     {1:2, 2:3, 3:5, 4:7, 5:9, 6:11, 7:14, 8:17, 9:21, 10:26},
    "political":    {1:2, 2:3, 3:4, 4:6, 5:8, 6:10, 7:13, 8:16, 9:20, 10:25},
    "militia":      {1:2, 2:3, 3:5, 4:7, 5:9, 6:12, 7:15, 8:19, 9:23, 10:28},
}

GDP_GATES = {
    # Minimum GDP required to upgrade to this tier
    # Below gate: cost x3, capability 50%
    # Above gate: normal cost and capability
    7: 80.0,    # $80B GDP
    8: 120.0,   # $120B GDP
    9: 180.0,   # $180B GDP
    10: 250.0,  # $250B GDP
}

PREREQUISITES = {
    # {tier_key: {min_tier: {prereq_key: min_level}}}
    # All are SOFT — without prereq, cost x2 and capability reduced, not hard blocked
    "military": {
        5: {"tech_level": 2},
        7: {"education_tier": 1},
        8: {"intelligence_tier": 4},
    },
    "intelligence": {
        4: {"tech_level": 1},
        6: {"tech_level": 3},
    },
    "diplomatic": {
        5: {"education_tier": 1},
        7: {"action_judiciary_captured": False},
        # Diplomatic 7+ is incompatible with judicial capture —
        # not a cost penalty, a hard incompatibility
    },
    "militia": {
        # Militia upgrades require personal wealth, no axis prerequisites
    },
}

COMMITMENT_EDUCATION_DISCOUNTS = {
    # {tier_key: {min_tier: {edu_min: discount}}}
    "military":     {3: {2: 0.3}},
    "intelligence": {2: {2: 0.2}, 3: {2: 0.2}},
    "diplomatic":   {3: {2: 0.3}},
}

COMMITMENT_TECH_DISCOUNTS = {
    "intelligence": {2: {3: 0.2}},
    # Intel Tier 2+ gets -$0.2B/day at Tech Tier 3+
}


# ── 9.5A-Shadow: Shadow State Cost Tables ─────────────────────────────────────
# Shadow axes are funded from PERSONAL WEALTH, not national budget.
# These are separate from TIER_COSTS which covers national commitment axes.

SHADOW_TIER_COSTS = {
    "media": {
        # Media control: propaganda, censorship, state broadcasting
        0: 0.0, 1: 0.2, 2: 0.4, 3: 0.7, 4: 1.1,
        5: 1.6, 6: 2.2, 7: 2.9, 8: 3.7, 9: 4.6,
        10: 6.0
    },
    "judicial": {
        # Judicial capture: judges, prosecutors, legal manipulation
        0: 0.0, 1: 0.2, 2: 0.5, 3: 0.9, 4: 1.4,
        5: 2.0, 6: 2.7, 7: 3.5, 8: 4.4, 9: 5.4,
        10: 7.0
    },
    "domestic_surveillance": {
        # Surveillance network: informants, wiretaps, digital monitoring
        0: 0.0, 1: 0.3, 2: 0.6, 3: 1.0, 4: 1.5,
        5: 2.1, 6: 2.8, 7: 3.6, 8: 4.5, 9: 5.5,
        10: 7.0
    },
    "extraction": {
        # Resource extraction/diversion apparatus (partially offset by revenue)
        0: 0.0, 1: 0.2, 2: 0.4, 3: 0.7, 4: 1.0,
        5: 1.4, 6: 1.9, 7: 2.5, 8: 3.2, 9: 4.0,
        10: 5.0
    },
    # militia costs already in TIER_COSTS — militia is shared between systems
}

EXTRACTION_REVENUE = {
    # Revenue generated per day by extraction tier.
    # Offsets extraction costs and feeds personal wealth.
    # Higher tiers make extraction profitable.
    0: 0.0, 1: 0.1, 2: 0.3, 3: 0.6, 4: 1.0,
    5: 1.5, 6: 2.1, 7: 2.8, 8: 3.6, 9: 4.5,
    10: 5.5
}

EXTRACTION_SKIM_CEILING = {
    # Maximum skim_rate allowed at each extraction tier.
    # Without extraction infrastructure, skim is capped low.
    0: 0.05,   # 5% baseline -- petty corruption
    1: 0.08,   # 8%
    2: 0.12,   # 12%
    3: 0.15,   # 15%
    4: 0.20,   # 20%
    5: 0.25,   # 25%
    6: 0.30,   # 30%
    7: 0.35,   # 35%
    8: 0.40,   # 40%
    9: 0.45,   # 45%
    10: 0.65,  # 65% -- maximum extraction
}

SHADOW_TIER_UPGRADE_COOLDOWNS = {
    # Cooldown in days after upgrading each shadow tier.
    # Shadow upgrades are faster than national tiers (covert, fewer bureaucratic hurdles).
    "media":                  {1:1, 2:2, 3:3, 4:5, 5:7, 6:9, 7:11, 8:14, 9:17, 10:21},
    "judicial":               {1:2, 2:3, 3:4, 4:6, 5:8, 6:10, 7:13, 8:16, 9:20, 10:25},
    "domestic_surveillance":  {1:2, 2:3, 3:4, 4:6, 5:8, 6:10, 7:13, 8:16, 9:20, 10:25},
    "extraction":             {1:1, 2:2, 3:3, 4:4, 5:6, 6:8, 7:10, 8:13, 9:16, 10:20},
    # militia cooldowns already in TIER_UPGRADE_COOLDOWNS
}

SHADOW_AXIS_FLAGS = {
    # Maps shadow tier thresholds to existing game_state boolean flags.
    # When a shadow tier reaches the threshold, the corresponding flag activates.
    # This bridges the new shadow system with the existing suppression flag system.
    "media": {
        3: "action_press_suppressed",       # media >= 3 -> press suppressed
        5: "action_media_taken",            # media >= 5 -> media captured
    },
    "judicial": {
        4: "action_judiciary_captured",     # judicial >= 4 -> judiciary captured
        7: "action_journalists_liquidated", # judicial >= 7 -> journalists liquidated
    },
    # FIX1: opposition_dissolved removed — now requires surveillance + judicial combo
    # (see compute_shadow_state_costs)
}

SHADOW_PREREQUISITES = {
    # {shadow_axis: {min_tier: {prereq_key: min_value}}}
    # All are SOFT gates -- without prereq, cost x2 (same pattern as PREREQUISITES)
    "media": {
        # No prerequisites -- media control is entry-level corruption
    },
    "judicial": {
        3: {"media_tier": 2},             # Need media cover before judicial capture
    },
    "domestic_surveillance": {
        3: {"intelligence_tier": 2},      # Need intel infrastructure
        6: {"judicial_tier": 3},          # Need legal cover for deep surveillance
    },
    "extraction": {
        3: {"political_tier": 2},         # Need political connections for extraction
        6: {"judicial_tier": 3},          # Need legal protection for large-scale extraction
    },
    # militia -- no shadow prerequisites (but costs personal wealth via TIER_COSTS)
}

print("[9.5A-Shadow] Shadow cost tables loaded: "
      f"SHADOW_TIER_COSTS={len(SHADOW_TIER_COSTS)} axes, "
      f"EXTRACTION_REVENUE={len(EXTRACTION_REVENUE)} tiers, "
      f"EXTRACTION_SKIM_CEILING={len(EXTRACTION_SKIM_CEILING)} tiers, "
      f"SHADOW_AXIS_FLAGS={sum(len(v) for v in SHADOW_AXIS_FLAGS.values())} flags")


def check_prerequisites(game_state, tier_key, target_tier):
    """9.5A: Check prerequisites for upgrading a tier.
    Returns dict with met, violations, cost_multiplier, capability_modifier, hard_blocked."""
    result = {
        "met": True,
        "violations": [],
        "cost_multiplier": 1.0,
        "capability_modifier": 1.0,
        "hard_blocked": False,
    }

    prereqs = PREREQUISITES.get(tier_key, {})

    # Check each prerequisite level threshold
    for min_tier, requirements in prereqs.items():
        if target_tier < min_tier:
            continue
        for prereq_key, prereq_value in requirements.items():
            # Special case: diplomatic 7+ AND judicial capture = hard block
            if tier_key == "diplomatic" and prereq_key == "action_judiciary_captured" and prereq_value is False:
                if getattr(game_state, 'action_judiciary_captured', False):
                    result["met"] = False
                    result["hard_blocked"] = True
                    result["violations"].append(
                        f"Diplomatic tier {target_tier} incompatible with judicial capture")
                continue

            # Normal soft prerequisite check
            current_val = getattr(game_state, prereq_key, 0)
            if isinstance(current_val, float):
                current_val = int(current_val)
            if current_val < prereq_value:
                result["met"] = False
                result["violations"].append(
                    f"{prereq_key} requires {prereq_value}, currently {current_val}")
                result["cost_multiplier"] *= 2.0
                result["capability_modifier"] = 0.5

    # GDP gate check
    gdp = getattr(game_state, 'gdp_base', 100.0)
    if target_tier in GDP_GATES:
        if gdp < GDP_GATES[target_tier]:
            result["met"] = False
            result["violations"].append(
                f"GDP ${gdp:.0f}B below gate ${GDP_GATES[target_tier]:.0f}B for tier {target_tier}")
            result["cost_multiplier"] *= 3.0
            result["capability_modifier"] = 0.5

    print(f"[9.5A] prereq_check: "
          f"tier={tier_key} target={target_tier} "
          f"met={result['met']} "
          f"cost_mult={result['cost_multiplier']} "
          f"hard_blocked={result['hard_blocked']}")

    return result


def compute_daily_commitment_cost(game_state):
    """9.5A: Compute daily commitment costs for all axes based on tier levels.
    Updates game_state.daily_*_cost fields and game_state.total_daily_commitment.
    Militia costs come from personal_wealth, not national budget.
    Returns (budget_total, militia_cost)."""

    # Get education tier and tech tier for discount lookups
    edu_tier = getattr(game_state, 'education_tier', 0)
    # Compute tech tier from tech_level thresholds (matches game_state._compute_tech_tier)
    _tl = float(getattr(game_state, 'tech_level', 0))
    if _tl >= 100:
        tech_tier = 5
    elif _tl >= 75:
        tech_tier = 4
    elif _tl >= 50:
        tech_tier = 3
    elif _tl >= 25:
        tech_tier = 2
    elif _tl >= 10:
        tech_tier = 1
    else:
        tech_tier = 0

    budget_total = 0.0

    # Budget axes — costs deducted from national budget
    _budget_axes = [
        ("military",     "military_tier",     "daily_military_cost"),
        ("intelligence", "intelligence_tier", "daily_intel_cost"),
        ("diplomatic",   "diplomatic_tier",   "daily_diplomatic_cost"),
        ("social",       "social_tier",       "daily_social_cost"),
        ("education",    "education_tier",    "daily_education_cost"),
        ("resource",     "resource_tier",     "daily_resource_cost"),
    ]

    for axis_key, tier_attr, cost_attr in _budget_axes:
        tier = getattr(game_state, tier_attr, 0)
        base_cost = TIER_COSTS.get(axis_key, {}).get(tier, 0.0)

        discount = 0.0

        # Education discount: COMMITMENT_EDUCATION_DISCOUNTS[axis][min_tier] = {edu_min: disc}
        _edu_disc = COMMITMENT_EDUCATION_DISCOUNTS.get(axis_key, {})
        for min_tier, edu_req in _edu_disc.items():
            if tier >= min_tier:
                for edu_min, disc_val in edu_req.items():
                    if edu_tier >= edu_min:
                        discount += disc_val

        # Tech discount: COMMITMENT_TECH_DISCOUNTS[axis][min_tier] = {tech_min: disc}
        _tech_disc = COMMITMENT_TECH_DISCOUNTS.get(axis_key, {})
        for min_tier, tech_req in _tech_disc.items():
            if tier >= min_tier:
                for tech_min, disc_val in tech_req.items():
                    if tech_tier >= tech_min:
                        discount += disc_val

        final_cost = max(0.0, round(base_cost - discount, 2))
        setattr(game_state, cost_attr, final_cost)
        budget_total += final_cost

    # Political axis — patronage/maintenance cost from national budget
    pol_tier = getattr(game_state, 'political_tier', 0)
    pol_cost = TIER_COSTS.get("political", {}).get(pol_tier, 0.0)
    budget_total += pol_cost

    budget_total = round(budget_total, 2)
    game_state.total_daily_commitment = budget_total

    # Militia — costs from personal wealth, NOT national budget
    militia_tier = getattr(game_state, 'militia_tier', 0)
    militia_cost = TIER_COSTS.get("militia", {}).get(militia_tier, 0.0)

    print(f"[9.5A] daily_commitment: "
          f"mil=${getattr(game_state, 'daily_military_cost', 0.0):.1f} "
          f"intel=${getattr(game_state, 'daily_intel_cost', 0.0):.1f} "
          f"diplo=${getattr(game_state, 'daily_diplomatic_cost', 0.0):.1f} "
          f"social=${getattr(game_state, 'daily_social_cost', 0.0):.1f} "
          f"edu=${getattr(game_state, 'daily_education_cost', 0.0):.1f} "
          f"resource=${getattr(game_state, 'daily_resource_cost', 0.0):.1f} "
          f"political=${pol_cost:.1f} "
          f"militia=${militia_cost:.1f}(pw) "
          f"total_budget=${budget_total:.1f}")

    return budget_total, militia_cost


def compute_shadow_state_costs(game_state):
    """9.5A-Shadow: Compute daily shadow state costs from personal wealth.
    Shadow axes (media, judicial, domestic_surveillance, extraction) are funded
    from personal wealth, not national budget.

    Also:
    - Computes extraction revenue (offsets extraction cost)
    - Enforces EXTRACTION_SKIM_CEILING on skim_rate
    - Syncs SHADOW_AXIS_FLAGS (activates boolean flags at tier thresholds)
    - Updates shadow_state_unlocked flag
    - Stores daily costs on game_state for frontend display

    Returns (total_shadow_cost, extraction_revenue, net_shadow_drain).
    """
    _shadow_axes = [
        ("media",                  "media_tier",                  "daily_media_cost"),
        ("judicial",               "judicial_tier",               "daily_judicial_cost"),
        ("domestic_surveillance",  "domestic_surveillance_tier",  "daily_surveillance_cost"),
        ("extraction",             "extraction_tier",             "daily_extraction_cost"),
    ]

    total_shadow_cost = 0.0

    for axis_key, tier_attr, cost_attr in _shadow_axes:
        tier = getattr(game_state, tier_attr, 0)
        cost = SHADOW_TIER_COSTS.get(axis_key, {}).get(tier, 0.0)

        # Apply SHADOW_PREREQUISITES soft gate cost multiplier
        _prereqs = SHADOW_PREREQUISITES.get(axis_key, {})
        for min_tier, requirements in _prereqs.items():
            if tier >= min_tier:
                for prereq_key, prereq_value in requirements.items():
                    current_val = getattr(game_state, prereq_key, 0)
                    if isinstance(current_val, float):
                        current_val = int(current_val)
                    if current_val < prereq_value:
                        cost *= 2.0  # soft gate penalty

        cost = round(cost, 2)
        setattr(game_state, cost_attr, cost)
        total_shadow_cost += cost

    # Militia cost (already in TIER_COSTS, shared between systems)
    militia_tier = getattr(game_state, 'militia_tier', 0)
    militia_cost = TIER_COSTS.get("militia", {}).get(militia_tier, 0.0)
    game_state.daily_militia_cost = militia_cost
    total_shadow_cost += militia_cost

    total_shadow_cost = round(total_shadow_cost, 2)

    # Extraction revenue
    ext_tier = getattr(game_state, 'extraction_tier', 0)
    extraction_revenue = EXTRACTION_REVENUE.get(ext_tier, 0.0)
    game_state.daily_extraction_revenue = extraction_revenue

    # Net shadow drain (costs minus extraction revenue)
    net_drain = round(total_shadow_cost - extraction_revenue, 2)
    game_state.total_shadow_commitment = total_shadow_cost

    # -- Enforce EXTRACTION_SKIM_CEILING --
    skim_ceiling = EXTRACTION_SKIM_CEILING.get(ext_tier, 0.05)
    current_skim = getattr(game_state, 'skim_rate', 0.0)
    if current_skim > skim_ceiling:
        game_state.skim_rate = skim_ceiling
        print(f"[9.5A-Shadow] skim_rate capped: {current_skim*100:.0f}% -> {skim_ceiling*100:.0f}% "
              f"(extraction_tier={ext_tier})")

    # -- Sync SHADOW_AXIS_FLAGS --
    # Activate boolean flags when shadow tiers reach thresholds
    for axis_key, thresholds in SHADOW_AXIS_FLAGS.items():
        # Map axis_key to the correct tier attribute
        if axis_key == "political":
            tier = getattr(game_state, 'political_tier', 0)
        elif axis_key == "media":
            tier = getattr(game_state, 'media_tier', 0)
        elif axis_key == "judicial":
            tier = getattr(game_state, 'judicial_tier', 0)
        else:
            continue

        for threshold, flag_name in thresholds.items():
            old_val = getattr(game_state, flag_name, False)
            new_val = (tier >= threshold)
            if new_val and not old_val:
                setattr(game_state, flag_name, True)
                print(f"[9.5A-Shadow] FLAG ACTIVATED: {flag_name} "
                      f"({axis_key}_tier={tier} >= {threshold})")

    # FIX1: Opposition dissolved requires BOTH surveillance AND judicial at meaningful levels
    if (getattr(game_state, 'domestic_surveillance_tier', 0) >= 5
            and getattr(game_state, 'judicial_tier', 0) >= 5):
        if not getattr(game_state, 'action_opposition_dissolved', False):
            game_state.action_opposition_dissolved = True
            print(f"[FIX1] FLAG ACTIVATED: action_opposition_dissolved "
                  f"(surv={game_state.domestic_surveillance_tier} jud={game_state.judicial_tier})")
    # Note: once set, does not auto-clear if tiers drop
    print(f"[FIX1] opposition_dissolved check: "
          f"surv={getattr(game_state, 'domestic_surveillance_tier', 0)} "
          f"jud={getattr(game_state, 'judicial_tier', 0)} "
          f"dissolved={getattr(game_state, 'action_opposition_dissolved', False)}")

    # -- Update shadow_state_unlocked --
    any_shadow = (
        getattr(game_state, 'media_tier', 0) > 0 or
        getattr(game_state, 'judicial_tier', 0) > 0 or
        getattr(game_state, 'domestic_surveillance_tier', 0) > 0 or
        getattr(game_state, 'extraction_tier', 0) > 0 or
        getattr(game_state, 'militia_tier', 0) > 0
    )
    game_state.shadow_state_unlocked = any_shadow

    print(f"[9.5A-Shadow] shadow_costs: "
          f"media=${getattr(game_state, 'daily_media_cost', 0):.1f} "
          f"judicial=${getattr(game_state, 'daily_judicial_cost', 0):.1f} "
          f"surv=${getattr(game_state, 'daily_surveillance_cost', 0):.1f} "
          f"extract=${getattr(game_state, 'daily_extraction_cost', 0):.1f} "
          f"militia=${militia_cost:.1f} "
          f"total=${total_shadow_cost:.1f} "
          f"ext_rev=${extraction_revenue:.1f} "
          f"net_drain=${net_drain:.1f} "
          f"skim_ceil={skim_ceiling*100:.0f}%")

    return total_shadow_cost, extraction_revenue, net_drain


# ── 9.5A: Tax Structure Modifiers ────────────────────────────────────────────
TAX_STRUCTURE_MODIFIERS = {
    "elite_heavy":  {"income": 0.85, "corporate": 1.15, "resource": 1.10},
    "balanced":     {"income": 1.00, "corporate": 1.00, "resource": 1.00},
    "mass_heavy":   {"income": 1.15, "corporate": 0.85, "resource": 0.90},
}

# Education → tax collection efficiency
EDUCATION_TAX_EFFICIENCY = {
    0: 0.92,  # Underdeveloped: -8% collection penalty (spec value)
    1: 0.95,  # Basic: functional but leaky
    2: 1.00,  # Developed: competent administration
    3: 1.05,  # Advanced: efficient modern tax system
}


def _laffer_efficiency(rate):
    """Laffer curve: efficiency drops at high tax rates.
    Returns multiplier 0.0-1.0 on effective revenue from that rate."""
    if rate <= 0.30:
        return 1.0
    elif rate <= 0.50:
        return 1.0 - (rate - 0.30) * 0.50   # 1.0 → 0.90 at 50%
    elif rate <= 0.70:
        return 0.90 - (rate - 0.50) * 0.75   # 0.90 → 0.75 at 70%
    else:
        return max(0.30, 0.75 - (rate - 0.70) * 1.50)  # 0.75 → 0.30 at 100%


def compute_tax_revenue(game_state):
    """9.5A: Compute tax revenue using new commitment model fields.
    Uses income_tax_rate, corporate_tax_rate, tax_rates['resource_tax'],
    tax_structure, education efficiency, Laffer curve, and skim_rate.
    Does NOT modify game_state.budget — that happens in Section 6.
    Returns dict with all computed values for logging and comparison."""

    gdp = getattr(game_state, 'gdp_base', 100.0)

    # ── Tax rates (new standalone fields + resource from tax_rates dict) ──
    income_rate = getattr(game_state, 'income_tax_rate', 0.25)
    corp_rate = getattr(game_state, 'corporate_tax_rate', 0.20)
    _tax_rates = getattr(game_state, 'tax_rates',
                         {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
    resource_rate = _tax_rates.get('resource_tax', 0.25)
    _endowment = getattr(game_state, 'resource_endowment', {})
    oil_factor = _endowment.get('oil_reserves', 0.7)

    # ── Base revenue streams (same GDP fractions as existing code) ──
    income_base = gdp * income_rate * 0.10      # income tax on 10% of GDP
    corp_base = gdp * corp_rate * 0.06           # corporate tax on 6% of GDP
    resource_base = gdp * resource_rate * oil_factor * 0.12  # resource extraction

    # ── Laffer curve — diminishing returns at high rates ──
    income_rev = income_base * _laffer_efficiency(income_rate)
    corp_rev = corp_base * _laffer_efficiency(corp_rate)
    resource_rev = resource_base * _laffer_efficiency(resource_rate)

    # ── Tax structure modifier ──
    structure = getattr(game_state, 'tax_structure', 'balanced')
    _struct_mods = TAX_STRUCTURE_MODIFIERS.get(structure, TAX_STRUCTURE_MODIFIERS['balanced'])
    income_rev *= _struct_mods['income']
    corp_rev *= _struct_mods['corporate']
    resource_rev *= _struct_mods['resource']

    # ── Education tax efficiency ──
    edu_level = getattr(game_state, 'education_level', 0)
    edu_eff = EDUCATION_TAX_EFFICIENCY.get(edu_level, 0.92)
    print(f"[9.5A-FIX4] edu_tier={edu_level} edu_eff={edu_eff}")
    income_rev *= edu_eff
    corp_rev *= edu_eff
    resource_rev *= edu_eff

    # ── Institutional modifier (heat penalty) ── 9.5A-FIX1
    institution_mod = 1.0
    heat = getattr(game_state, 'detection_heat', 0)
    if heat > 60:
        institution_mod -= 0.10
    elif heat > 40:
        institution_mod -= 0.05
    income_rev *= institution_mod
    corp_rev *= institution_mod
    resource_rev *= institution_mod
    print(f"[9.5A-FIX1] heat={heat} inst_mod={institution_mod}")

    gross_revenue = round(income_rev + corp_rev + resource_rev, 2)

    # ── Approval modifier (same tiers as existing code) ──
    approval = getattr(game_state, 'public_approval', 50)
    if approval >= 80:
        approval_mult = 1.4
    elif approval >= 60:
        approval_mult = 1.0
    elif approval >= 40:
        approval_mult = 0.7
    else:
        approval_mult = 0.4
    gross_revenue = round(gross_revenue * approval_mult, 2)

    # ── Stability modifier (same as existing) ──
    stability = getattr(game_state, 'stability', 50)
    if stability >= 80:
        gross_revenue += 1.0
    elif stability < 30:
        gross_revenue -= 1.0

    # ── Sanctions penalty (same as existing) ──
    sanctions_tier = getattr(game_state, 'usa_sanctions_tier', 0)
    if sanctions_tier >= 4:
        gross_revenue -= 1.5
    embargo_tier = getattr(game_state, 'arabia_embargo_tier', 0)
    if embargo_tier >= 2:
        gross_revenue -= 0.5

    # ── Regime modifier (same as existing) ──
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    regime_mults = {
        'Managed Democracy': 1.1,
        'Soft Authoritarianism': 1.0,
        'Patronage State': 0.95,
        'Kleptocracy': 0.85,
        'Totalitarian Regime': 0.75,
    }
    gross_revenue = round(gross_revenue * regime_mults.get(regime, 1.0), 2)

    # ── Tech multiplier (same as existing) ──
    tech_level = float(getattr(game_state, 'tech_level', 0))
    tech_mult = 1.0 + (tech_level * 0.005)
    if tech_mult > 1.0:
        gross_revenue = round(gross_revenue * tech_mult, 2)

    # ── Infrastructure bonus (same as existing) ──
    infra_bonus = getattr(game_state, '_infra_gdp_bonus', 0.0)
    if infra_bonus > 0:
        gross_revenue = round(gross_revenue * (1.0 + infra_bonus), 2)

    # ── GDP contraction override at critically low approval+stability ──
    contraction = False
    if approval < 20 and stability < 30:
        gross_revenue = round(-1.0 - (30 - stability) * 0.05 - (20 - approval) * 0.05, 2)
        contraction = True

    # ── Skim diversion ──
    skim_rate = getattr(game_state, 'skim_rate', 0.0)
    if contraction or gross_revenue <= 0:
        skim_income = 0.0
        net_revenue = gross_revenue
    else:
        skim_income = round(gross_revenue * skim_rate, 2)
        net_revenue = round(gross_revenue - skim_income, 2)
        # ── Skim heat generation (moved from Section 6) ── 9.5A-FIX2
        if skim_rate > 0.05:
            _skim_heat = round((skim_rate - 0.05) * 100, 0)
            _old_heat = getattr(game_state, 'detection_heat', 0)
            game_state.detection_heat = min(100, _old_heat + int(_skim_heat))
            print(f"[9.5A-FIX2] skim_rate={skim_rate*100:.0f}% skim_heat_added={_skim_heat:.0f} heat_total={game_state.detection_heat}")
        else:
            print(f"[9.5A-FIX2] skim_rate={skim_rate*100:.0f}% skim_heat_added=0 heat_total={getattr(game_state, 'detection_heat', 0)}")

    # Floor net revenue at 0 for normal operation (contraction can be negative)
    if not contraction:
        net_revenue = max(0.0, net_revenue)

    # ── Store revenue fields for frontend display ──
    game_state.last_gross_revenue = round(gross_revenue, 2)
    game_state.last_net_revenue = round(net_revenue, 2)
    game_state.last_skim_amount = round(skim_income, 2)
    print(f"[FIX] revenue stored: gross={game_state.last_gross_revenue:.2f} net={game_state.last_net_revenue:.2f} skim={game_state.last_skim_amount:.2f}")

    result = {
        'gross_revenue': round(gross_revenue, 1),
        'net_revenue': round(net_revenue, 1),
        'skim_income': round(skim_income, 1),
        'skim_rate': skim_rate,
        'income_rev': round(income_rev, 2),
        'corp_rev': round(corp_rev, 2),
        'resource_rev': round(resource_rev, 2),
        'laffer_income': round(_laffer_efficiency(income_rate), 3),
        'laffer_corp': round(_laffer_efficiency(corp_rate), 3),
        'laffer_resource': round(_laffer_efficiency(resource_rate), 3),
        'tax_structure': structure,
        'edu_efficiency': edu_eff,
        'approval_mult': approval_mult,
        'tech_mult': round(tech_mult, 3),
        'regime': regime,
        'contraction': contraction,
    }

    print(f"[9.5A] tax_revenue: "
          f"gross=${result['gross_revenue']:.1f} "
          f"net=${result['net_revenue']:.1f} "
          f"skim=${result['skim_income']:.1f} ({skim_rate*100:.0f}%) "
          f"income=${result['income_rev']:.1f} "
          f"corp=${result['corp_rev']:.1f} "
          f"resource=${result['resource_rev']:.1f} "
          f"laffer={result['laffer_income']:.2f}/{result['laffer_corp']:.2f}/{result['laffer_resource']:.2f} "
          f"struct={structure} edu_eff={edu_eff} "
          f"appr_mult={approval_mult} tech_mult={tech_mult:.3f}")

    return result


# ── 9.5A: Western Alignment Ceiling Table ─────────────────────────────────────
# Each suppression action hard-caps EU relations. Cumulative (most restrictive wins).
WESTERN_ALIGNMENT_CAPS = {
    # (field_name, cap_when_active)
    'action_press_suppressed': 85,
    'action_judiciary_captured': 75,
    'action_opposition_dissolved': 55,
    'action_journalists_liquidated': 40,
}
# Combined: press + judiciary = 65, all active = 30


def compute_eu_ceiling(game_state):
    """9.5A-Shadow: Compute EU relations ceiling from shadow tier levels + suppression flags.

    Base ceiling comes from boolean suppression flags (backward compatible):
      - press_suppressed: 85
      - judiciary_captured: 75
      - press + judiciary: 65
      - opposition_dissolved: 55
      - journalists_liquidated: 40
      - all active: 30

    Tier-based refinement (additional reductions for deep shadow investment):
      - media_tier >= 7: -5 (deep media control beyond basic suppression)
      - judicial_tier >= 7: -5 (total judicial capture)
      - domestic_surveillance_tier >= 5: -5 (surveillance state detected by EU)

    Returns the computed ceiling (integer, 0-100).
    """
    # -- Flag-based caps (backward compatible) --
    press_sup = getattr(game_state, 'action_press_suppressed', False)
    jud_cap = getattr(game_state, 'action_judiciary_captured', False)
    opp_dis = getattr(game_state, 'action_opposition_dissolved', False)
    journ_liq = getattr(game_state, 'action_journalists_liquidated', False)

    ceiling = 100
    if press_sup:
        ceiling = min(ceiling, 85)
    if jud_cap:
        ceiling = min(ceiling, 75)
    if press_sup and jud_cap:
        ceiling = min(ceiling, 65)
    if opp_dis:
        ceiling = min(ceiling, 55)
    if journ_liq:
        ceiling = min(ceiling, 40)
    if press_sup and jud_cap and opp_dis and journ_liq:
        ceiling = 30

    # -- Tier-based refinement (9.5A-Shadow) --
    media_tier = getattr(game_state, 'media_tier', 0)
    judicial_tier = getattr(game_state, 'judicial_tier', 0)
    surv_tier = getattr(game_state, 'domestic_surveillance_tier', 0)

    tier_penalty = 0
    if media_tier >= 7:
        tier_penalty += 5
    if judicial_tier >= 7:
        tier_penalty += 5
    if surv_tier >= 5:
        tier_penalty += 5

    if tier_penalty > 0:
        ceiling = max(10, ceiling - tier_penalty)  # floor at 10
        print(f"[9.5A-Shadow] EU ceiling tier penalty: -{tier_penalty} "
              f"(media_t={media_tier} jud_t={judicial_tier} surv_t={surv_tier})")

    print(f"[9.5A-Shadow] compute_eu_ceiling: {ceiling} "
          f"(press={press_sup} jud={jud_cap} opp={opp_dis} journ={journ_liq} "
          f"tier_pen={tier_penalty})")

    return ceiling


def compute_stability_components(gs) -> tuple:
    """9.5B: Computes legitimacy and coercion stability raw scores from current game state.
    Returns (legitimacy_float, coercion_float) as 0-100 values representing the ideal
    composition ratio."""

    # --- LEGITIMACY SOURCES ---
    # Approval (primary driver, 0-40 points)
    approval_score = (gs.public_approval / 100) * 40

    # Education tier (0-15 points)
    edu = getattr(gs, 'education_tier', getattr(gs, 'education_level', 0))
    edu_score = (edu / 10) * 15

    # Social tier (0-15 points)
    social_score = (getattr(gs, 'social_tier', 0) / 10) * 15

    # Election integrity (0-15 points)
    elections_held = getattr(gs, 'elections_held', 0)
    elections_stolen = getattr(gs, 'elections_stolen', 0)
    if elections_held > 0:
        integrity = 1.0 - (elections_stolen / elections_held)
    else:
        integrity = 0.8
    election_score = integrity * 15

    # Democratic track record (0-10 points)
    suppression_count = sum([
        1 if getattr(gs, 'action_press_suppressed', False) else 0,
        1 if getattr(gs, 'action_judiciary_captured', False) else 0,
        1 if getattr(gs, 'action_opposition_dissolved', False) else 0,
        1 if getattr(gs, 'action_journalists_liquidated', False) else 0,
    ])
    track_record_score = max(0, 10 - (suppression_count * 2.5))

    # Diplomatic tier (0-5 points)
    diplo_score = (getattr(gs, 'diplomatic_tier', 0) / 10) * 5

    legitimacy_raw = (approval_score + edu_score + social_score
                      + election_score + track_record_score + diplo_score)
    # Normalize: max raw = 100 (40+15+15+15+10+5), scale to 0-100
    legitimacy = min(100, legitimacy_raw)

    # --- COERCION SOURCES ---
    # Military tier (0-30 points)
    mil_score = (getattr(gs, 'military_tier', 0) / 10) * 30

    # Militia tier (0-20 points)
    # If merged into military, capability already reflected in military_tier
    if getattr(gs, 'militia_merged', False):
        militia_score = 0
    else:
        militia_score = (getattr(gs, 'militia_tier', 0) / 10) * 20

    # Suppression axes (0-25 points)
    media_t = getattr(gs, 'media_tier', 0)
    judicial_t = getattr(gs, 'judicial_tier', 0)
    surv_t = getattr(gs, 'domestic_surveillance_tier', 0)
    suppression_score = min(25, (media_t + judicial_t + surv_t) / 30 * 25)

    # Political tier / patronage (0-15 points)
    pol_score = (getattr(gs, 'political_tier', 0) / 10) * 15

    # Personal wealth patronage (0-10 points)
    wealth = getattr(gs, 'personal_wealth', 0)
    wealth_score = min(10, (wealth / 20) * 10)

    coercion_raw = (mil_score + militia_score + suppression_score
                    + pol_score + wealth_score)
    # Normalize: max raw = 100 (30+20+25+15+10), scale to 0-100
    coercion = min(100, coercion_raw)

    # --- REGIME TYPE FLOORS AND CAPS ---
    _si = getattr(gs, 'state_identity', {})
    regime = _si.get('regime_type', 'Managed Democracy')

    democratic_regimes = ['Managed Democracy']
    soft_auth_regimes = ['Soft Authoritarianism', 'Patronage State']
    full_dict_regimes = ['Kleptocracy', 'Totalitarian Regime']

    if regime in democratic_regimes:
        # Democracy: legitimacy floor 30, coercion hard-capped at 40
        legitimacy = max(legitimacy, 30)
        coercion = min(coercion, 40)
    elif regime in soft_auth_regimes:
        # Soft authoritarianism: slight legitimacy floor
        legitimacy = max(legitimacy, 15)
    elif regime in full_dict_regimes:
        # Full dictatorship: legitimacy capped unless player invests
        if edu < 2 and getattr(gs, 'social_tier', 0) < 2 and gs.public_approval < 50:
            legitimacy = min(legitimacy, 40)
        coercion = min(coercion, 100)  # no cap

    print(f"[9.5B] compute_stability_components: "
          f"leg_raw={legitimacy:.1f} coe_raw={coercion:.1f} "
          f"regime={regime} "
          f"approval={gs.public_approval} edu={edu} "
          f"suppression={suppression_count}")

    return (legitimacy, coercion)


def apply_commitment_eot_checks(game_state, messages, net_revenue=None):
    """9.5A: End-of-turn commitment model checks.
    1. Coup amplifier — military_tier > political_tier by 3+
    2. Intel politicization — political_tier >= 7 AND intelligence_tier >= 5
    3. Western alignment ceiling — suppression state -> EU cap
    4. Sustainability gap — commitment > revenue for 5+ consecutive days
    Called from apply_end_of_turn_effects() after budget integration.
    net_revenue is passed from Section 6 once wired; None = skip sustainability check."""

    mil_tier = getattr(game_state, 'military_tier', 0)
    pol_tier = getattr(game_state, 'political_tier', 0)
    intel_tier = getattr(game_state, 'intelligence_tier', 0)

    # ── 1. Coup Amplifier ──────────────────────────────────────────────
    gap = mil_tier - pol_tier
    was_active = getattr(game_state, 'coup_amplifier_active', False)
    game_state.coup_amplifier_active = (gap > 3)

    if game_state.coup_amplifier_active and not was_active:
        messages.append(
            f"⚠️ COUP RISK: Military tier ({mil_tier}) exceeds political control ({pol_tier}) "
            f"by {gap} — generals may act independently")
    elif not game_state.coup_amplifier_active and was_active:
        messages.append("✅ Military-political gap closed — coup amplifier deactivated")

    # ── 2. Intel Politicization ────────────────────────────────────────
    was_politicized = getattr(game_state, 'intel_politicized', False)
    game_state.intel_politicized = (pol_tier >= 7 and intel_tier >= 5)

    if game_state.intel_politicized and not was_politicized:
        messages.append(
            "⚠️ Intelligence apparatus politicized — intercepts may be unreliable "
            "(Political ≥7, Intel ≥5)")
    elif not game_state.intel_politicized and was_politicized:
        messages.append("✅ Intelligence depoliticized — intercept reliability restored")

    # ── 3. Western Alignment Ceiling ───────────────────────────────────
    ceiling = compute_eu_ceiling(game_state)

    old_ceiling = getattr(game_state, 'eu_relations_ceiling', 100)
    game_state.eu_relations_ceiling = ceiling

    # Enforce ceiling on EU relations
    eu_rel = game_state.relations.get('eu', 50)
    if eu_rel > ceiling:
        _old_eu = eu_rel
        game_state.relations['eu'] = ceiling
        messages.append(
            f"🇪🇺 EU relations capped: {_old_eu:.0f} → {ceiling} "
            f"(domestic suppression ceiling)")
        print(f"[9.5A] EU ceiling enforced: {_old_eu:.0f} -> {ceiling}")

    if ceiling < old_ceiling:
        messages.append(
            f"⚠️ Western alignment ceiling dropped: {old_ceiling} → {ceiling}")

    # ── 4. Sustainability Gap ──────────────────────────────────────────
    total_commitment = getattr(game_state, 'total_daily_commitment', 0.0)
    deficit_days = getattr(game_state, 'commitment_deficit_days', 0)

    if net_revenue is not None and total_commitment > 0:
        # Unsustainable if commitment exceeds 120% of net revenue
        if total_commitment > net_revenue * 1.2:
            game_state.commitment_deficit_days = deficit_days + 1
            if game_state.commitment_deficit_days >= 5:
                # Find highest-cost budget axis and degrade it
                _axis_costs = [
                    ('military_tier', 'daily_military_cost'),
                    ('intelligence_tier', 'daily_intel_cost'),
                    ('diplomatic_tier', 'daily_diplomatic_cost'),
                    ('social_tier', 'daily_social_cost'),
                    ('education_tier', 'daily_education_cost'),
                    ('resource_tier', 'daily_resource_cost'),
                ]
                _highest_axis = None
                _highest_cost = 0.0
                for _tier_attr, _cost_attr in _axis_costs:
                    _cost = getattr(game_state, _cost_attr, 0.0)
                    _tier = getattr(game_state, _tier_attr, 0)
                    if _cost > _highest_cost and _tier > 0:
                        _highest_cost = _cost
                        _highest_axis = _tier_attr

                if _highest_axis:
                    _old_tier = getattr(game_state, _highest_axis)
                    setattr(game_state, _highest_axis, _old_tier - 1)
                    _axis_name = _highest_axis.replace('_tier', '')
                    messages.append(
                        f"📉 SUSTAINABILITY GAP: {_axis_name} tier degraded "
                        f"{_old_tier} → {_old_tier - 1} "
                        f"(commitment ${total_commitment:.1f}B > revenue ${net_revenue:.1f}B "
                        f"for {deficit_days} consecutive days)")
                    print(f"[9.5A] sustainability_gap: {_axis_name} {_old_tier} -> {_old_tier - 1}")
                    game_state.commitment_deficit_days = 0  # reset after degradation
        else:
            # Revenue covers commitment — reset deficit counter
            game_state.commitment_deficit_days = 0
    elif net_revenue is None:
        pass  # Section 6 not yet wired — skip sustainability check

    print(f"[9.5A] eot_checks: "
          f"coup_amp={game_state.coup_amplifier_active} "
          f"(mil_t={mil_tier} pol_t={pol_tier} gap={gap}) "
          f"intel_pol={game_state.intel_politicized} "
          f"eu_ceiling={ceiling} "
          f"deficit_days={getattr(game_state, 'commitment_deficit_days', 0)}")


def apply_election_consequences(game_state, result_key):
    """Apply hard-coded election consequences to game state. Returns list of change descriptions."""
    cons = ELECTION_CONSEQUENCES.get(result_key)
    if not cons:
        return [f"Unknown election result: {result_key}"]

    changes = []

    # Relation changes
    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        delta = cons.get(npc)
        if delta and delta != 0:
            game_state.update_relations(npc, delta)
            changes.append(f"{npc.upper()} {'+' if delta > 0 else ''}{delta}")

    # Stability
    stab_delta = cons.get('stability', 0)
    if stab_delta:
        game_state.update_stability(stab_delta)
        changes.append(f"stability {'+' if stab_delta > 0 else ''}{stab_delta}%")

    # Approval
    appr_delta = cons.get('approval', 0)
    if appr_delta:
        game_state.update_approval(appr_delta)
        changes.append(f"approval {'+' if appr_delta > 0 else ''}{appr_delta}%")

    # Detection heat
    heat_delta = cons.get('heat', 0)
    if heat_delta:
        game_state.detection_heat = min(100, game_state.detection_heat + heat_delta)
        changes.append(f"heat +{heat_delta}")

    # Personal cost (from personal_wealth)
    personal_cost = cons.get('personal_cost', 0)
    if personal_cost:
        game_state.personal_wealth = max(0, game_state.personal_wealth - personal_cost)
        changes.append(f"personal wealth -${personal_cost:.1f}B")

    # Protests
    if cons.get('protests_pending'):
        game_state.protests_pending = True
        changes.append("protests pending next turn")

    # Democracy lock
    lock_turns = cons.get('regime_democracy_locked', 0)
    if lock_turns:
        game_state.regime_democracy_locked = lock_turns
        changes.append(f"democracy locked {lock_turns} turns")

    # fixes_12 Fix 3: Regime pressure now shifts axes instead of directly mutating regime_type.
    # compute_regime_from_axes() in section 13g is the sole authority for regime_type.
    pressure = cons.get('regime_pressure', 'none')
    _axes = getattr(game_state, 'cabinet_axes', {'military': 0, 'intelligence': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0})

    if pressure == 'left':
        # Democratic pressure — reduce military and political axes
        _axes['military'] = max(0, _axes.get('military', 0) - 2)
        _axes['political'] = max(0, _axes.get('political', 0) - 2)
        changes.append(f"⚠️ Election outcome shifts regime axes (Military -2, Political -2)")
    elif pressure == 'right_one':
        # Authoritarian pressure — increase military and political axes
        _axes['military'] = min(10, _axes.get('military', 0) + 2)
        _axes['political'] = min(10, _axes.get('political', 0) + 2)
        changes.append(f"⚠️ Election outcome shifts regime axes (Military +2, Political +2)")
    elif pressure == 'right_two':
        # Heavy authoritarian pressure — increase military, political, and media axes
        _axes['military'] = min(10, _axes.get('military', 0) + 3)
        _axes['political'] = min(10, _axes.get('political', 0) + 3)
        _axes['media'] = min(10, _axes.get('media', 0) + 2)
        changes.append(f"⚠️ Election outcome shifts regime axes (Military +3, Political +3, Media +2)")
    elif pressure == 'collapse_risk':
        if game_state.stability < 30:
            _axes['military'] = min(10, _axes.get('military', 0) + 2)
            _axes['political'] = min(10, _axes.get('political', 0) + 1)
            changes.append(f"⚠️ Regime collapse risk: stability crisis shifts axes (Military +2, Political +1)")
        else:
            changes.append("regime collapse risk: stability held")

    game_state.cabinet_axes = _axes

    print(f"  [turn_processor] ELECTION RESULT: {result_key} — consequences applied: {changes}")
    return changes


# ── 8C: Exile Sequence ──────────────────────────────────────────────────────

from game_state import SUCCESSOR_NAMES, APPARATUS_SURVIVAL

EXILE_DRAIN_BASE = 0.2  # $B/day living expenses

# Stubbed successor events — fire by day number, keyed by disposition
SUCCESSOR_EVENTS = {
    'reformist': [
        {'key': 'ref_eu_deal', 'day': 3,
         'effects': {'eu': 5, 'stability': -5}},
        {'key': 'ref_unpopular', 'day': 7,
         'effects': {}},
        {'key': 'ref_arabia_fumble', 'day': 12,
         'effects': {'arabia': -8}},
    ],
    'hardliner': [
        {'key': 'hard_usa_drop', 'day': 3,
         'effects': {'usa': -12, 'russia': 5}},
        {'key': 'hard_press', 'day': 6,
         'effects': {'eu': -8}},
        {'key': 'hard_stable', 'day': 10,
         'effects': {}},
    ],
    'technocrat': [
        {'key': 'tech_cold', 'day': 4,
         'effects': {}},
        {'key': 'tech_budget', 'day': 8,
         'effects': {'stability': 5}},
    ],
    'populist': [
        {'key': 'pop_spending', 'day': 3,
         'effects': {}},
        {'key': 'pop_arabia', 'day': 7,
         'effects': {'arabia': 5, 'eu': -6}},
        {'key': 'pop_approval', 'day': 11,
         'effects': {}},
    ],
}

# Successor event text templates (use {name} placeholder)
SUCCESSOR_EVENT_TEXT = {
    'ref_eu_deal': '{name} has signed an EU governance framework -- press freedom benchmarks attached. EU relations rise but stability drops.',
    'ref_unpopular': 'Approval for {name} has fallen to 38%. The reforms are moving faster than the population can absorb.',
    'ref_arabia_fumble': '{name} has renegotiated the Arabia energy deal at significantly worse terms. Oil costs rising.',
    'hard_usa_drop': '{name} has expelled two Western NGOs. USA relations have dropped sharply.',
    'hard_press': '{name} has moved against independent media. EU considering sanctions review.',
    'hard_stable': 'Stability under {name} has reached 85%. The suppression is working, for now.',
    'tech_cold': '{name} governs efficiently but without warmth. Approval has drifted to 42%.',
    'tech_budget': '{name} has stabilized the budget through austerity. Public services cut 15%.',
    'pop_spending': '{name} has announced a popular spending program. Budget drain accelerating.',
    'pop_arabia': '{name} has made public overtures to Arabia that contradict your previous EU commitments.',
    'pop_approval': '{name}\'s approval has hit 71%. The honeymoon is holding.',
}


def _calculate_exile_destination(gs):
    """Fix B: Standalone helper to determine exile destination from highest NPC relations."""
    DEST_MAP = {
        'usa':    ('Washington D.C.', 'usa'),
        'eu':     ('Brussels', 'eu'),
        'arabia': ('Riyadh', 'arabia'),
        'dprg':   ('Pyongyang', 'dprg'),
        'russia': ('Moscow', 'russia'),
        'china':  ('Shanghai', 'china'),
    }
    relations = {k: gs.relations.get(k, 0)
                 for k in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china')}
    top_npc = max(relations, key=relations.get)
    city, npc = DEST_MAP[top_npc]
    print(f"[exile] Destination calculated: {city} (highest NPC: {npc}, relations: {relations[top_npc]})")
    return top_npc


def _compute_departure_heat(game_state, trigger):
    """9A: Compute departure heat (1-5) based on how the player left power."""
    import math
    # Level 5: Fugitive — violent departure + international warrant or war crimes
    has_warrant = getattr(game_state, 'international_warrant', False)
    has_war_crimes = getattr(game_state, 'war_crimes_flag', False)
    brigades_deployed = getattr(game_state, 'brigades_deployed_last_turn', False)
    militia_active = getattr(game_state, 'private_security_force', False)
    lethal_flag = getattr(game_state, 'action_journalists_liquidated', False)
    military_axis = game_state.cabinet_axes.get('military', 0)

    # Check if militia/brigades were deployed (any brigade ops recently)
    recent_brigade_ops = len(getattr(game_state, 'brigade_operations_this_turn', []))
    militia_deployed = brigades_deployed or militia_active or recent_brigade_ops > 0

    # Significant casualties: lethal actions taken
    significant_casualties = lethal_flag

    if militia_deployed and (significant_casualties or military_axis >= 7) and (has_warrant or has_war_crimes):
        heat = 5  # Fugitive
    elif militia_deployed and (significant_casualties or lethal_flag):
        heat = 4  # Violent
    elif militia_deployed:
        heat = 3  # Contested
    elif trigger == 'voted_out':
        heat = 1  # Quiet — conceded peacefully
    else:
        # Some resistance but no militia
        heat = 2  # Managed

    heat = max(1, min(5, heat))
    print(f"[DIAG] departure_heat computed={heat} flags=militia_deployed={militia_deployed} lethal={lethal_flag} warrant={has_warrant} war_crimes={has_war_crimes} mil_axis={military_axis} trigger={trigger}")
    return heat


def _compute_return_threshold(trigger, departure_heat):
    """9A: Compute return threshold from collapse type and departure heat."""
    base_by_trigger = {
        'coup': 70,
        'revolution': 90,
        'debt': 65,
        'voted_out': 50,
    }
    base = base_by_trigger.get(trigger, 70)
    heat_modifier = (departure_heat - 1) * 8
    return base + heat_modifier


def exile_sequence_start(game_state, trigger):
    """8C: Transition from in-power to exile. Called instead of game-over."""
    game_state.in_exile = True
    game_state.exile_trigger = trigger
    game_state.exile_day = 0
    game_state.exile_wealth_at_collapse = game_state.personal_wealth

    # 9A: Snapshot state at exile moment for restoration calculations
    game_state.exile_entry_gdp = getattr(game_state, 'gdp_base', 100.0)
    game_state.exile_entry_relations = dict(game_state.relations)

    # 9A: Compute departure heat and return threshold
    game_state.departure_heat = _compute_departure_heat(game_state, trigger)
    game_state.return_threshold = _compute_return_threshold(trigger, game_state.departure_heat)
    print(f"[DIAG] return_threshold set={game_state.return_threshold} collapse={trigger} heat={game_state.departure_heat}")
    game_state.return_progress = 0.0
    game_state.return_attempts = 0
    game_state.npc_assistance_tiers = {}
    game_state.faction_contacts = {}
    game_state.wealth_action_cooldowns = {}
    game_state.detection_events = []
    game_state.exile_successor_log = []
    game_state.exile_actions_log = []

    # Determine destination -- highest NPC relations at collapse
    game_state.exile_destination = _calculate_exile_destination(game_state)

    # Determine successor
    game_state.successor_disposition = game_state._determine_successor()
    game_state.successor_name = SUCCESSOR_NAMES[game_state.successor_disposition]

    # Apparatus survival
    survival = APPARATUS_SURVIVAL.get(trigger, APPARATUS_SURVIVAL['coup'])
    game_state.exile_apparatus_survived = survival['survived']
    game_state.exile_apparatus_detection_risk_modifier = survival['risk_modifier']

    # Strip national resources -- these belong to the successor now
    game_state.budget = 0.0
    game_state.military_strength = 0
    # Personal wealth, shadow apparatus, backchannel relations survive

    print(f'[exile] Exile started: trigger={trigger} destination={game_state.exile_destination}')
    print(f'[exile] Successor: {game_state.successor_name} ({game_state.successor_disposition})')
    print(f'[exile] Apparatus: survived={game_state.exile_apparatus_survived} risk_modifier={game_state.exile_apparatus_detection_risk_modifier}')
    print(f'[9A] departure_heat={game_state.departure_heat}, return_threshold={game_state.return_threshold}')

    # 9A: Compute successor archetype and hostility
    _archetype = _compute_successor_archetype(trigger, game_state.successor_disposition, game_state)
    game_state.successor_archetype = _archetype
    game_state.successor_hostility = _compute_successor_hostility(_archetype, game_state.departure_heat)
    print(f'[9A] successor_archetype={_archetype} hostility={game_state.successor_hostility}')

    if trigger == 'voted_out':
        print(f'[exile] Voted out path: apparatus_risk=0.9 backing_discount=20%')


def _compute_successor_archetype(trigger, disposition, game_state):
    """9A: Map (trigger, disposition) to a named archetype."""
    if trigger == 'voted_out' and disposition == 'reformist':
        return 'Opposition Democracy'
    if trigger == 'revolution' and disposition == 'populist':
        return 'Populist Dictator'
    if trigger == 'coup' and disposition == 'hardliner':
        # Distinguish military vs oligarch coup
        mil_axis = game_state.cabinet_axes.get('military', 0)
        if mil_axis >= 5:
            return 'Military Junta'
        else:
            return 'Oligarchic Council'
    if trigger == 'debt' and disposition == 'technocrat':
        return 'Technocratic Caretaker'
    # Fallback: use disposition label directly
    return disposition.replace('_', ' ').title()


def _compute_successor_hostility(archetype, departure_heat):
    """9A: Compute successor hostility (0-3) from archetype + departure heat."""
    import math
    base_by_archetype = {
        'Opposition Democracy': 0,
        'Technocratic Caretaker': 0,
        'Oligarchic Council': 1,
        'Populist Dictator': 2,
        'Military Junta': 2,
    }
    base = base_by_archetype.get(archetype, 1)
    heat_modifier = math.floor((departure_heat - 1) / 2)
    return min(3, base + heat_modifier)


def process_exile_eod(game_state):
    """8C: End-of-day processing during exile. Replaces normal EOT."""
    game_state.exile_day += 1
    drain = EXILE_DRAIN_BASE

    # Shadow apparatus maintenance
    if game_state.exile_apparatus_survived:
        drain += 0.3

    game_state.personal_wealth = max(0, round(game_state.personal_wealth - drain, 2))

    # NPC relations drift slowly downward in exile
    for npc in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china'):
        current = game_state.relations.get(npc, 50)
        # Slow drift toward 30 (the floor of relevance)
        if current > 30:
            game_state.relations[npc] = max(30, round(current - 0.5, 1))

    # Fire successor event (stubbed -- one per 2-3 days)
    event_msg = _maybe_fire_successor_event(game_state)

    print(f'[exile] EOD: day={game_state.exile_day} wealth={game_state.personal_wealth:.1f}B drain={drain:.1f}B')

    messages = [f"Day {game_state.exile_day} in exile. Wealth: ${game_state.personal_wealth:.1f}B (burn: ${drain:.1f}B/day)"]
    if event_msg:
        messages.append(event_msg)
    return messages


def _maybe_fire_successor_event(game_state):
    """9A: Fire a live GM-generated successor event once per exile day.
    Replaces the static stub system from 8C."""
    archetype = getattr(game_state, 'successor_archetype', None)
    name = game_state.successor_name or 'The Successor'
    hostility = getattr(game_state, 'successor_hostility', 0)

    if not archetype:
        # Fallback to old disposition if archetype not computed (pre-9A save)
        archetype = (game_state.successor_disposition or 'populist').replace('_', ' ').title()

    # Fire one event per exile day (called from process_exile_eod)
    try:
        from npc_engine import generate_successor_events
        events = generate_successor_events(
            successor_archetype=archetype,
            successor_name=name,
            successor_hostility=hostility,
            exile_day=game_state.exile_day,
            player_return_progress=getattr(game_state, 'return_progress', 0.0),
            player_exile_actions_log=getattr(game_state, 'exile_actions_log', []),
            game_state=game_state,
        )
    except Exception as _gm_err:
        print(f'[9A] Successor event GM call failed: {_gm_err}')
        # Static fallback: generate a generic event based on hostility
        events = _static_successor_fallback(archetype, name, hostility, game_state.exile_day)

    if not events:
        return None

    result_texts = []
    for evt in events:
        evt_type = evt.get('type', 'unknown')
        description = evt.get('description', f'{name} takes action.')
        effects = evt.get('effect', {})

        # Apply mechanical effects
        _apply_successor_effect(game_state, evt_type, effects)

        # Log to exile_successor_log
        log_entry = {
            'day': game_state.exile_day,
            'type': evt_type,
            'description': description,
            'effects': effects,
        }
        if not hasattr(game_state, 'exile_successor_log'):
            game_state.exile_successor_log = []
        game_state.exile_successor_log.append(log_entry)

        result_texts.append(description)
        print(f'[9A] successor_event fired: {evt_type} on exile_day={game_state.exile_day}')

    return ' '.join(result_texts) if result_texts else None


def _apply_successor_effect(game_state, evt_type, effects):
    """9A: Apply the mechanical effects from a successor event."""
    if evt_type == 'asset_seizure':
        delta = effects.get('personal_wealth', 0)
        if delta:
            game_state.personal_wealth = max(0, round(game_state.personal_wealth + delta, 2))
    elif evt_type == 'diplomatic_outreach':
        for npc_id, rel_delta in effects.items():
            if npc_id in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china'):
                game_state.relations[npc_id] = max(0, min(100, game_state.relations.get(npc_id, 50) + rel_delta))
    elif evt_type == 'propaganda_campaign':
        delta = effects.get('approval_delta', 0)
        if delta:
            game_state.public_approval = max(0, min(90, game_state.public_approval + delta))
    elif evt_type == 'arrest_warrant':
        game_state.international_warrant = True
    elif evt_type == 'reconciliation_offer':
        pass  # opens democratic return path -- UI stub for now
    elif evt_type == 'purge_allies':
        # Reduce faction contact availability
        fc = getattr(game_state, 'faction_contacts', {})
        for faction_key in list(fc.keys()):
            if fc[faction_key].get('unlocked') and not fc[faction_key].get('committed'):
                fc[faction_key]['unlocked'] = False
                print(f'[9A] purge_allies: faction {faction_key} contact revoked')
                break
        game_state.faction_contacts = fc
    elif evt_type == 'economic_stabilization':
        stab_delta = effects.get('stability_delta', 0)
        if stab_delta > 0:
            game_state.stability = max(0, min(90, game_state.stability + stab_delta))
        # Progress penalty for player: stability for successor = harder return
        progress_penalty = effects.get('progress_penalty', 0)
        if progress_penalty:
            game_state.return_progress = max(0, game_state.return_progress - progress_penalty)


def _static_successor_fallback(archetype, name, hostility, exile_day):
    """9A: Static fallback when GM call fails. Returns a list of event dicts."""
    import random
    if hostility <= 0:
        templates = [
            {'type': 'reconciliation_offer', 'description': f'{name} has made a public statement leaving the door open for political dialogue.', 'effect': {}},
            {'type': 'diplomatic_outreach', 'description': f'{name} has reached out to the EU to signal continuity.', 'effect': {'eu': 3}},
        ]
    elif hostility == 1:
        templates = [
            {'type': 'economic_stabilization', 'description': f'{name} has announced an austerity program. Markets responded cautiously.', 'effect': {'stability_delta': 3}},
            {'type': 'diplomatic_outreach', 'description': f'{name} is meeting with foreign representatives. Business as usual, conspicuously so.', 'effect': {}},
        ]
    elif hostility == 2:
        templates = [
            {'type': 'propaganda_campaign', 'description': f'{name} has launched a media campaign denouncing the previous regime.', 'effect': {'approval_delta': -5}},
            {'type': 'asset_seizure', 'description': f'{name} has frozen several accounts linked to the former government.', 'effect': {'personal_wealth': -1.0}},
        ]
    else:
        templates = [
            {'type': 'arrest_warrant', 'description': f'{name} has issued an international arrest warrant for the former leader.', 'effect': {}},
            {'type': 'asset_seizure', 'description': f'{name} has seized personal assets held within Europa.', 'effect': {'personal_wealth': -2.0}},
            {'type': 'purge_allies', 'description': f'{name} has arrested several former officials with ties to the previous regime.', 'effect': {}},
        ]
    # Pick one event
    return [random.choice(templates)]



# ── Session 4C: Domestic Action Consequences (hard-coded, Claude never decides these) ──

DOMESTIC_ACTION_CONSEQUENCES = {
    "state_media_takeover": {
        "cost": 5.0,
        "flag": "action_media_taken",
        "eu": -8, "usa": -5,
        "approval_floor": 15,
        "regime_pressure": "right",
        "label": "State Media Takeover",
        "description": "Approval never drops below 15%. Future approval penalties reduced 20%.",
    },
    "judicial_capture": {
        "cost": 4.0,
        "flag": "action_judiciary_captured",
        "eu": -10, "usa": -5,
        "scandal_immune": True,
        "regime_pressure": "right",
        "label": "Judicial Capture",
        "description": "Corruption scandals eliminated. Investigations suspended permanently.",
    },
    "suppress_press": {
        "cost": 3.0,
        "flag": "action_press_suppressed",
        "dprg": +3,
        "stability": +5,
        "regime_pressure": "right",
        "label": "Suppress Independent Press",
        "description": "Stability +5%. EU sanctions risk activates (EU -3/turn).",
    },
    "dissolve_opposition": {
        "cost": 6.0,
        "flag": "action_opposition_dissolved",
        "usa": -5, "eu": -5,
        "stability": +10,
        "approval": -8,
        "coup_immune": True,
        "regime_pressure": "hard_right",
        "label": "Dissolve Opposition Groups",
        "description": "Stability +10%. Coup risk eliminated. Approval -8%.",
    },
    "liquidate_journalists": {
        "cost": 8.0,
        "flag": "action_journalists_liquidated",
        "eu": -15, "usa": -8,
        "approval": -10,
        "approval_ceiling": -10,
        "scandal_immune": True,
        "regime_pressure": "hard_right",
        "label": "Liquidate Investigative Journalists",
        "description": "Scandals eliminated permanently. Approval ceiling -10%.",
    },
}


def apply_domestic_action(game_state, action_key):
    """Apply a one-time domestic action purchase. Returns (success, changes_list)."""
    cons = DOMESTIC_ACTION_CONSEQUENCES.get(action_key)
    if not cons:
        return False, [f"Unknown domestic action: {action_key}"]

    # Check if already purchased
    flag = cons['flag']
    if getattr(game_state, flag, False):
        return False, [f"Already purchased: {cons['label']}"]

    # Check cost
    cost = cons['cost']
    if game_state.personal_wealth < cost:
        return False, [f"Cannot afford {cons['label']}: need ${cost:.1f}B, have ${game_state.personal_wealth:.1f}B"]

    changes = []

    # Snapshot EU before changes for Marsha red line check
    _eu_before = game_state.relations.get('eu', 0)

    # Deduct cost — fixes_10 Fix 2: Use update_personal_wealth() for ledger recording
    game_state.update_personal_wealth(-cost, source=f"domestic action ({cons['label']})")
    changes.append(f"personal wealth -${cost:.1f}B")

    # Set flag
    setattr(game_state, flag, True)
    # fixes_10 Fix 8: record enacted turn for JUST ENACTED distinction in intercepts
    if not hasattr(game_state, 'domestic_actions_enacted_turns'):
        game_state.domestic_actions_enacted_turns = {}
    game_state.domestic_actions_enacted_turns[flag] = game_state.current_turn
    changes.append(f"{cons['label']} enacted")

    # Relation changes
    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        delta = cons.get(npc)
        if delta and delta != 0:
            game_state.update_relations(npc, delta)
            changes.append(f"{npc.upper()} {'+' if delta > 0 else ''}{delta}")

    # Stability
    stab_delta = cons.get('stability', 0)
    if stab_delta:
        game_state.update_stability(stab_delta)
        changes.append(f"stability {'+' if stab_delta > 0 else ''}{stab_delta}%")

    # Approval
    appr_delta = cons.get('approval', 0)
    if appr_delta:
        game_state.update_approval(appr_delta)
        changes.append(f"approval {'+' if appr_delta > 0 else ''}{appr_delta}%")

    # Approval floor
    floor_val = cons.get('approval_floor', 0)
    if floor_val:
        game_state.approval_floor = max(game_state.approval_floor, floor_val)
        changes.append(f"approval floor set to {game_state.approval_floor}%")

    # Approval ceiling penalty
    ceiling_delta = cons.get('approval_ceiling', 0)
    if ceiling_delta:
        game_state.approval_ceiling = max(0, game_state.approval_ceiling + ceiling_delta)
        changes.append(f"approval ceiling now {game_state.approval_ceiling}%")

    # Scandal immunity
    if cons.get('scandal_immune'):
        game_state.scandal_immune = True
        changes.append("scandal immunity granted")

    # Coup immunity
    if cons.get('coup_immune'):
        game_state.coup_immune = True
        changes.append("coup immunity granted")

    # Marsha red line: journalists liquidated while EU was >= 70 (before relation hit)
    if action_key == 'liquidate_journalists' and _eu_before >= 70:
        game_state.marsha_red_line_triggered = True
        changes.append("MARSHA RED LINE: EU publicly distances")

    # fixes_12 Fix 3: Regime pressure now shifts axes instead of directly mutating regime_type.
    pressure = cons.get('regime_pressure', 'none')
    _da_axes = getattr(game_state, 'cabinet_axes', {'military': 0, 'intelligence': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0})

    if pressure == 'right':
        _da_axes['military'] = min(10, _da_axes.get('military', 0) + 2)
        _da_axes['political'] = min(10, _da_axes.get('political', 0) + 2)
        changes.append(f"⚠️ Domestic action shifts regime axes (Military +2, Political +2)")
    elif pressure == 'hard_right':
        _da_axes['military'] = min(10, _da_axes.get('military', 0) + 3)
        _da_axes['political'] = min(10, _da_axes.get('political', 0) + 3)
        _da_axes['media'] = min(10, _da_axes.get('media', 0) + 2)
        changes.append(f"⚠️ Domestic action shifts regime axes (Military +3, Political +3, Media +2)")

    game_state.cabinet_axes = _da_axes

    # Session 6 Phase 8: Heat generation for domestic actions
    _heat_map = {
        'liquidate_journalists': 20,
        'suppress_press': 8,
        'dissolve_opposition': 5,
    }
    _heat_add = _heat_map.get(action_key, 0)
    if _heat_add > 0:
        _old_heat = game_state.detection_heat
        game_state.detection_heat = min(100, game_state.detection_heat + _heat_add)
        changes.append(f"🔥 +{_heat_add} detection heat ({_old_heat}% -> {game_state.detection_heat}%)")
        print(f"  [HEAT] Domestic action '{action_key}': +{_heat_add} heat ({_old_heat} -> {game_state.detection_heat})")

    # Log to action_history
    game_state.action_history.append({
        'type': 'domestic_action',
        'action': action_key,
        'turn': game_state.current_turn,
    })

    print(f"  [turn_processor] DOMESTIC ACTION: {action_key} — consequences: {changes}")
    return True, changes


# ── Session 4D: Tech Level System (hard-coded, Claude never decides these) ──

TECH_TIER_NAMES = {
    0: "Pre-Industrial",
    1: "Emerging Capability",
    2: "Functional Modernization",
    3: "Strategic Capability",
    4: "Advanced Economy",
    5: "Frontier",
}

EU_TECH_CEILINGS = {
    0: 3.0,   # Tier 0: $3B
    1: 4.0,   # Tier 1: $4B
    2: 5.0,   # Tier 2: $5B
    3: 7.0,   # Tier 3: $7B
    4: 9.0,   # Tier 4: $9B
    5: None,  # Tier 5: no cap
}

ECONOMY_EFFICIENCY_MODIFIERS = {0: 0.0, 1: 0.05, 2: 0.12, 3: 0.20, 4: 0.30, 5: 0.40}

INTEL_DETECTION_RISK_MODIFIERS = {0: 0.0, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}

TECH_SOURCES = {
    "eu_partnership":  {"gain": 5, "label": "EU Partnership Deal"},
    "usa_transfer":    {"gain": 8, "label": "USA Technology Transfer"},
    "dprg_weapons":    {"gain": 3, "label": "DPRG Weapons-for-Tech Exchange"},
}


def get_tech_tier(tech_level):
    """Return the tier number (0-5) for a given tech level."""
    if tech_level >= 100: return 5
    if tech_level >= 75:  return 4
    if tech_level >= 50:  return 3
    if tech_level >= 25:  return 2
    if tech_level >= 10:  return 1
    return 0


def get_tech_tier_effects(tech_level):
    """Return the effects dict for the current tech level tier (legacy compat)."""
    tier = get_tech_tier(tech_level)
    return {
        "eu_ceiling": EU_TECH_CEILINGS[tier],
        "gdp_bonus": ECONOMY_EFFICIENCY_MODIFIERS[tier],
        "intel_tier_bonus": tier,  # legacy field
    }


def get_eu_ceiling(tech_level):
    """Return the EU ceiling for a given tech level. None means no cap."""
    tier = get_tech_tier(tech_level)
    return EU_TECH_CEILINGS[tier]


def get_economy_efficiency_modifier(tech_level):
    """Return economy efficiency GDP multiplier for a given tech level."""
    tier = get_tech_tier(tech_level)
    return ECONOMY_EFFICIENCY_MODIFIERS[tier]


def get_intel_detection_risk_modifier(tech_level):
    """Return intel detection risk reduction for a given tech level."""
    tier = get_tech_tier(tech_level)
    return INTEL_DETECTION_RISK_MODIFIERS[tier]


def apply_tech_gain(game_state, source_key):
    """Apply a tech gain from a specific source. Returns (success, changes_list)."""
    source = TECH_SOURCES.get(source_key)
    if not source:
        return False, [f"Unknown tech source: {source_key}"]

    old_level = game_state.tech_level
    old_tier = get_tech_tier(old_level)
    gain = source['gain']
    game_state.tech_level = game_state.tech_level + gain  # no cap — Tier 5 is 100+
    actual_gain = game_state.tech_level - old_level

    if actual_gain == 0:
        return True, [f"Tech gain was zero"]

    game_state.tech_sources.append({
        'source': source_key,
        'gain': actual_gain,
        'turn': game_state.current_turn,
    })

    new_tier = get_tech_tier(game_state.tech_level)
    changes = [f"Tech Level +{actual_gain} ({old_level} -> {game_state.tech_level}) — {source['label']}"]

    # Report tier transition if applicable
    if old_tier != new_tier:
        changes.append(f"TIER UP: {TECH_TIER_NAMES[old_tier]} -> {TECH_TIER_NAMES[new_tier]}")
        eu_ceil = EU_TECH_CEILINGS[new_tier]
        changes.append(f"EU ceiling now ${eu_ceil}B" if eu_ceil else "EU ceiling REMOVED")
        changes.append(f"GDP bonus now +{int(ECONOMY_EFFICIENCY_MODIFIERS[new_tier] * 100)}%")
        print(f"  [tech_level] Tier transition: {old_tier} -> {new_tier} at tech_level={game_state.tech_level}")

    print(f"  [turn_processor] TECH GAIN: {source_key} +{actual_gain} -> level {game_state.tech_level}")
    return True, changes


# ── Session 4D: Intelligence Budget System (hard-coded, Claude never decides these) ──

INTEL_BUDGET_OPTIONS = {
    "none":        {"cost": 0.0, "label": "No Funding"},
    "maintenance": {"cost": 0.5, "label": "Maintenance ($0.5B)"},
    "active":      {"cost": 1.0, "label": "Active Operations ($1.0B)"},
    "expansion":   {"cost": 2.0, "label": "Expansion ($2.0B)"},
}


def process_intel_budget(game_state, allocation):
    """Process intel budget allocation for the turn. Deducts from national budget.
    Returns (success, changes_list)."""
    option = INTEL_BUDGET_OPTIONS.get(allocation)
    if not option:
        return False, [f"Unknown allocation: {allocation}"]

    cost = option['cost']
    changes = []

    # Check if national budget can cover the cost
    if cost > 0 and game_state.budget < cost:
        return False, [f"Cannot afford {option['label']}: need ${cost:.1f}B, budget is ${game_state.budget:.1f}B"]

    # Deduct from national budget
    if cost > 0:
        game_state.update_budget(-cost)
        changes.append(f"Intel budget: -{option['label']} from national budget")

    # Track allocation
    old_allocation = game_state.intel_budget_allocation
    game_state.intel_budget_allocation = allocation

    # Apparatus degradation: 2 consecutive "none" turns -> tier drops by 1
    if allocation == "none":
        game_state.intel_turns_unfunded += 1
        if game_state.intel_turns_unfunded >= 2:
            # Degrade apparatus tier
            current_tier = getattr(game_state, 'intel_apparatus_tier', 0)
            if current_tier > 0:
                game_state.intel_apparatus_tier = current_tier - 1
                changes.append(f"Intel apparatus degraded: tier {current_tier} -> {current_tier - 1} (unfunded {game_state.intel_turns_unfunded} turns)")
                print(f"  [turn_processor] INTEL DEGRADATION: tier {current_tier} -> {current_tier - 1}")
            game_state.intel_turns_unfunded = 0  # Reset after degradation
        else:
            changes.append(f"Intel unfunded ({game_state.intel_turns_unfunded}/2 turns before degradation)")
    else:
        game_state.intel_turns_unfunded = 0
        changes.append(f"Intel allocation: {option['label']}")

    # Store intel budget pool (used for operations)
    game_state.intel_budget = cost

    print(f"  [turn_processor] INTEL BUDGET: {allocation} (${cost:.1f}B), unfunded streak: {game_state.intel_turns_unfunded}")
    return True, changes


# ── Session 4D: Alternate Ending Conditions (hard-coded, Claude never decides these) ──

ALTERNATE_ENDING_CONDITIONS = {
    "democratic": {
        "priority": 4,
        "any_turn": True,
        "conditions": {"eu_min": 80, "no_press_suppression": True, "approval_min": 65},
        "label": "Democratic Transition",
        "flavor": "Europa democratized under your watch — history will be kind.",
        "legacy_bonus": 40,
        "grade_min": "A",
    },
    "retirement": {
        "priority": 3,
        "any_turn": True,
        "conditions": {"stability_min": 60, "approval_min": 50, "wealth_min": 20},
        "label": "Voluntary Retirement",
        "flavor": "You left on your own terms — rarer than it sounds.",
        "legacy_bonus": 20,
        "grade_min": "B",
    },
    "restoration_legacy": {
        "priority": 3,
        "any_turn": True,
        "conditions": {"stability_min": 55, "approval_min": 45, "restoration_return": True},
        "label": "Restoration Legacy",
        "flavor": "Exiled and returned — Europa remembers both the fall and the climb back.",
        "legacy_bonus": 25,
        "grade_min": "B",
    },
    "capture": {
        "priority": 2,
        "any_turn": True,
        "conditions": {"wealth_min": 50, "capture_triad": True},
        "label": "State Capture Complete",
        "flavor": "You didn't lose power. You became the state.",
        "legacy_bonus": 0,
        "grade_min": None,
    },
    "martyrdom": {
        "priority": 1,
        "any_turn": True,
        "conditions": {"stability_max": 0, "approval_min": 70},
        "label": "Martyrdom",
        "flavor": "The people loved you. That's why they had to remove you.",
        "legacy_bonus": 0,
        "grade_min": None,
    },
}


def check_alternate_endings(game_state):
    """Check all alternate ending conditions in priority order.
    Returns ending_key or None. Checked each EOT after consequences.
    10A: Turn-count gates removed — conditions are sufficient in open-world."""

    # Check in priority order (highest first)
    endings_by_priority = sorted(
        ALTERNATE_ENDING_CONDITIONS.items(),
        key=lambda x: x[1]['priority'],
        reverse=True,
    )

    for key, ending in endings_by_priority:

        conds = ending['conditions']
        met = True

        # fixes_17 Fix K: Martyrdom uses pre-drift trigger flag instead of live stability
        if key == 'martyrdom':
            if not getattr(game_state, 'martyrdom_triggered', False):
                continue
            # Flag was set pre-drift — skip normal stability/approval checks for martyrdom
        else:
            # Stability max (at or below)
            if 'stability_max' in conds and game_state.stability > conds['stability_max']:
                met = False
            # Stability min
            if 'stability_min' in conds and game_state.stability < conds['stability_min']:
                met = False
            # Approval min
            if 'approval_min' in conds and game_state.public_approval < conds['approval_min']:
                met = False
        # Wealth min
        if 'wealth_min' in conds and game_state.personal_wealth < conds['wealth_min']:
            met = False
        # EU min
        if 'eu_min' in conds and game_state.relations.get('eu', 0) < conds['eu_min']:
            met = False
        # State Capture triad: Constitutional Revision + press suppression + judicial capture
        if conds.get('capture_triad'):
            triad_met = all([
                getattr(game_state, 'constitutional_revision_active', False),
                getattr(game_state, 'action_press_suppressed', False),
                getattr(game_state, 'action_judiciary_captured', False),
            ])
            if not triad_met:
                met = False
        # No press suppression active (for Democratic Transition)
        if conds.get('no_press_suppression'):
            if getattr(game_state, 'action_press_suppressed', False):
                met = False
        # 9C: Restoration return (exile occurred + returned + restoration resolved)
        if conds.get('restoration_return'):
            _exile_day = getattr(game_state, 'exile_day', 0)
            _return_attempts = getattr(game_state, 'return_attempts', 0)
            _restoration_active = getattr(game_state, 'restoration_active', False)
            if _exile_day <= 0 or _return_attempts <= 0 or _restoration_active:
                met = False
            if met:
                print(f"  [9C] restoration_legacy triggered: stability={game_state.stability} approval={game_state.public_approval} exile_day={_exile_day}")

        if met:
            game_state.ending_triggered = key
            print(f"  [turn_processor] ALTERNATE ENDING TRIGGERED: {key} — {ending['label']}")
            return key

    return None


def process_choice_consequences(game_state, choice):
    """Apply immediate consequences from player choice, including approval changes"""

    consequences = choice.get('consequences', {})
    messages = []
    # FIX E: Covert deals skip all cross-NPC penalties, heat, and public reaction
    _is_covert = choice.get('covert', False)

    # Relations changes — diminishing returns applied inside update_relations().
    # Display the actual applied delta (new - old), not the raw requested delta,
    # so the log accurately reflects what happened.
    # BUG 4: Include source context so players know WHY relations changed.
    # 8A: Expanded to 6 NPCs so Russia/China deal consequences are applied.
    _deal_npc = choice.get('npc', '')
    _choice_type = choice.get('type', '')
    for npc in ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']:
        if npc in consequences:
            # FIX E: Covert deals skip cross-NPC relation changes (only deal NPC affected)
            if _is_covert and npc != _deal_npc:
                continue
            old = game_state.relations[npc]
            _rel_change = consequences[npc]
            # BUG FIX 1: Cap indirect NPC relation loss at -8 per deal.
            # Indirect = NPC is not the deal partner and change is negative.
            if npc != _deal_npc and _rel_change < -8:
                _rel_change = -8
            game_state.update_relations(npc, _rel_change)
            new = game_state.relations[npc]
            actual_delta = round(new - old)
            direction = "↑" if actual_delta >= 0 else "↓"
            # Determine source label for context
            if npc == _deal_npc and actual_delta >= 0:
                source = "deal bonus"
            elif npc == _deal_npc and actual_delta < 0:
                source = "deal cost"
            elif _deal_npc and actual_delta < 0:
                source = f"{_deal_npc.upper()} alignment penalty"
            elif _deal_npc and actual_delta > 0:
                source = f"{_deal_npc.upper()} alignment bonus"
            else:
                source = "choice consequence"
            messages.append(f"{direction} {npc.upper()}: {old} -> {new} ({actual_delta:+d}) — {source}")

    # ITEM 4: Heat from deal (e.g. DPRG arms purchase)
    # FIX E: Covert deals skip heat generation
    if 'heat' in consequences and not _is_covert:
        _heat_add = consequences['heat']
        game_state.detection_heat = min(100, game_state.detection_heat + _heat_add)
        messages.append(f"🔥 +{_heat_add} heat (covert deal)")

    # ITEM 3: Military Strength change
    if 'military' in consequences:
        _mil_old = getattr(game_state, 'military_strength', 20)
        _mil_change = consequences['military']
        game_state.military_strength = max(0, min(100, _mil_old + _mil_change))
        _mil_dir = "↑" if _mil_change > 0 else "↓"
        messages.append(f"{_mil_dir} Military: {_mil_old} -> {game_state.military_strength} ({_mil_change:+d})")

    # Budget
    if 'budget' in consequences:
        old = game_state.budget
        game_state.update_budget(consequences['budget'])
        direction = "↑" if consequences['budget'] > 0 else "↓"
        messages.append(f"{direction} Budget: ${old:.1f}B -> ${game_state.budget:.1f}B ({consequences['budget']:+.1f}B)")

    # Stability
    if 'stability' in consequences:
        old = game_state.stability
        game_state.update_stability(consequences['stability'])
        direction = "↑" if consequences['stability'] > 0 else "↓"
        messages.append(f"{direction} Stability: {old}% -> {game_state.stability}% ({consequences['stability']:+d}%)")

    # Oil price consequences — oil_price_lock is handled directly in api.py before
    # process_choice_consequences is called. The oil_price field (old delta-based system)
    # is stripped in api.py and should never arrive here. If it somehow does, ignore it.
    # Only log a relation-based note if Arabia relations changed without an oil lock.
    arabia_delta = consequences.get('arabia', 0)
    if 'oil_price' not in consequences and arabia_delta != 0:
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
            # The relations loop already appended a stale "↑ USA: X -> Y (+25)" line.
            # Find it and replace it with the corrected values.
            for i, m in enumerate(messages):
                if m.startswith("↑ USA:") or m.startswith("↓ USA:"):
                    # Reconstruct with the true before (pre_floor minus the raw +25 delta)
                    before = pre_floor - consequences.get('usa', 25)
                    actual_delta = final_rel - before
                    messages[i] = f"↑ USA: {before} -> {final_rel} (+{actual_delta})"
                    break
            game_state.update_approval(10)
            messages.append(f"✅ Sanctions lifted (relations set to minimum {final_rel}). Public relief: +10% approval")

        elif special == 'remove_embargo':
            game_state.arabia_embargo_active = False
            messages.append("✅ Arabia embargo lifted!")

        elif special == 'took_arabia_oil':
            game_state.took_arabia_oil = True
            messages.append("📝 Arabia oil deal recorded")

        elif special == 'western_bloc_pressure':
            # FIX U: Arabia premium partnership immediately triggers Western Bloc Joint Pressure.
            # This makes the $12B static choice a "burn bridges fast" option.
            game_state.update_stability(-8)
            game_state.update_approval(-6)
            game_state.update_budget(-5.0)
            # fixes_8 Fix 10: Flag to prevent double-fire in check_pressure_events
            game_state._western_bloc_fired_this_turn = True
            print(f"  [PRESSURE] Western bloc pressure: source=deal_consequence, already_fired=False")
            messages.append(
                "🇺🇸🇪🇺 WESTERN BLOC JOINT PRESSURE — The premium Arabia partnership "
                "has triggered an immediate coordinated Western response. "
                "Sanctions packages being unified. "
                "-8% stability, -6% approval, -$5B (frozen assets)"
            )

    # Approval changes based on the NPC sided with
    npc = choice.get('npc')
    choice_type = choice.get('type')
    _negotiated = choice.get('is_negotiated', False)

    if choice_type in ('accept_deal', 'side_with') and npc:
        if npc == 'usa':
            # FIX E: Defense package should NOT trigger US investment payment.
            # Check if this is a weapons purchase (has military in consequences).
            _is_weapons = 'military' in consequences
            if not _is_weapons:
                game_state.update_approval(5)
                messages.append("📊 Public approval: +5% (US alignment)")
            # Standard US investment bonus — skip for negotiated deals and weapons purchases
            if not _negotiated and not _is_weapons:
                game_state.update_budget(3.0)
                messages.append("💰 US investment: +$3B")
            # ITEM 3: Military 50+ gives USA +5 relations (alliance value)
            _mil = getattr(game_state, 'military_strength', 20)
            if _mil >= 50:
                game_state.update_relations('usa', 5, source="military alliance value")
                messages.append("⚔️ Military alliance value (50+): USA +5")
        elif npc == 'arabia':
            # Arabia oil deals cheapen energy — people like that
            game_state.update_approval(8)
            messages.append("📊 Public approval: +8% (cheaper oil)")
            # FIX 2: Arabia deals penalize EU relations, scaled to total deal value.
            _ar_total = choice.get('deal_total_value', 0) or choice.get('deal_budget', 0) or abs(consequences.get('budget', 0))
            if _ar_total > 4:
                _ar_eu_pen = -6
                _ar_size = "large"
            elif _ar_total >= 2:
                _ar_eu_pen = -4
                _ar_size = "medium"
            else:
                _ar_eu_pen = -2
                _ar_size = "small"
            if 'eu' not in consequences:
                _old_eu = game_state.relations['eu']
                game_state.update_relations('eu', _ar_eu_pen, source="Arabia deal cross-NPC penalty")
                messages.append(f"⚠️ Arabia {_ar_size} deal: EU {_old_eu}->{game_state.relations['eu']} ({_ar_eu_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: arabia {_ar_size} deal -> eu {_ar_eu_pen:+d}")
        elif npc == 'eu':
            game_state.update_approval(6)
            messages.append("📊 Public approval: +6% (EU alignment)")
            # ITEM 1: EU trade benefit removed — absorbed into GDP baseline revenue.
            # High approval from EU alignment -> higher GDP revenue each turn.
            # FIX M: EU deals produce cross-NPC relation penalties, scaled to deal size.
            # Also give USA a small positive (+2 to +3) since EU alignment is broadly Western.
            # BUG FIX 1: Skip cross-NPC penalty for NPCs already named in deal consequences.
            # Named penalty replaces cross-NPC penalty, never stacks. Cap indirect at -8.
            # 8A FIX 1: Use deal_budget for negotiated deals (budget is popped before reaching here)
            _eu_budget = choice.get('deal_budget', 0) or abs(consequences.get('budget', 0))
            if _eu_budget > 3:
                _dprg_pen, _arabia_pen, _usa_bonus = -8, -5, 3
                _size_label = "large"
            elif _eu_budget >= 1:
                _dprg_pen, _arabia_pen, _usa_bonus = -5, -3, 2
                _size_label = "medium"
            else:
                _dprg_pen, _arabia_pen, _usa_bonus = -3, -2, 2
                _size_label = "small"
            _cross_parts = []
            # Only apply cross-NPC penalty if that NPC isn't already named in consequences
            if 'dprg' not in consequences:
                _old_dprg = game_state.relations['dprg']
                game_state.update_relations('dprg', _dprg_pen, source="EU deal cross-NPC penalty")
                _cross_parts.append(f"DPRG {_old_dprg}->{game_state.relations['dprg']} ({_dprg_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: eu deal -> dprg {_dprg_pen:+d}")
            if 'arabia' not in consequences:
                _old_arabia = game_state.relations['arabia']
                game_state.update_relations('arabia', _arabia_pen, source="EU deal cross-NPC penalty")
                _cross_parts.append(f"Arabia {_old_arabia}->{game_state.relations['arabia']} ({_arabia_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: eu deal -> arabia {_arabia_pen:+d}")
            if 'usa' not in consequences:
                _old_usa = game_state.relations['usa']
                game_state.update_relations('usa', _usa_bonus, source="EU deal cross-NPC bonus")
                _cross_parts.append(f"USA {_old_usa}->{game_state.relations['usa']} ({_usa_bonus:+d})")
                print(f"  [deal] Cross-NPC consequences fired: eu deal -> usa {_usa_bonus:+d}")
            if _cross_parts:
                messages.append(f"⚠️ EU {_size_label} deal: {', '.join(_cross_parts)}")
        elif npc == 'dprg':
            # FIX E: Covert deals skip public backlash and cross-NPC penalties entirely
            if _is_covert:
                print(f"  [turn_processor] FIX E: COVERT DPRG deal — skipping approval penalty + cross-NPC penalties")
            else:
                # DPRG deals are deeply unpopular domestically
                game_state.update_approval(-10)
                messages.append("📊 Public approval: -10% (DPRG backlash)")
                # ITEM 5: DPRG cross-NPC penalties, scaled by deal size.
                # Replaces the fixed penalties in deal consequences dicts.
                # 8A FIX 1: Use deal_budget for negotiated deals (budget is popped before reaching here)
                _dprg_budget = choice.get('deal_budget', 0) or abs(consequences.get('budget', 0))
                if _dprg_budget > 3:
                    _usa_pen, _eu_pen = -20, -15
                    _dprg_size = "large"
                elif _dprg_budget >= 1:
                    _usa_pen, _eu_pen = -15, -10
                    _dprg_size = "medium"
                else:
                    _usa_pen, _eu_pen = -8, -5
                    _dprg_size = "small"
                _dprg_cross_parts = []
                if 'usa' not in consequences:
                    _old_usa = game_state.relations['usa']
                    game_state.update_relations('usa', _usa_pen, source="DPRG deal cross-NPC penalty")
                    _dprg_cross_parts.append(f"USA {_old_usa}->{game_state.relations['usa']} ({_usa_pen:+d})")
                    print(f"  [deal] Cross-NPC consequences fired: dprg deal -> usa {_usa_pen:+d}")
                if 'eu' not in consequences:
                    _old_eu = game_state.relations['eu']
                    game_state.update_relations('eu', _eu_pen, source="DPRG deal cross-NPC penalty")
                    _dprg_cross_parts.append(f"EU {_old_eu}->{game_state.relations['eu']} ({_eu_pen:+d})")
                    print(f"  [deal] Cross-NPC consequences fired: dprg deal -> eu {_eu_pen:+d}")
                if _dprg_cross_parts:
                    messages.append(f"⚠️ DPRG {_dprg_size} deal: {', '.join(_dprg_cross_parts)}")
        elif npc == 'russia':
            # 8A: Russia deal cross-NPC consequences, scaled to TOTAL deal value
            # (upfront + installments). deal_total_value is computed in api.py.
            _ru_total = choice.get('deal_total_value', 0) or choice.get('deal_budget', 0) or abs(consequences.get('budget', 0))
            if _ru_total > 4:
                _usa_pen, _eu_pen = -12, -6
                _ru_size = "large"
            elif _ru_total >= 2:
                _usa_pen, _eu_pen = -8, -4
                _ru_size = "medium"
            else:
                _usa_pen, _eu_pen = -5, -2
                _ru_size = "small"
            _ru_cross_parts = []
            if 'usa' not in consequences:
                _old_usa = game_state.relations['usa']
                game_state.update_relations('usa', _usa_pen, source="Russia deal cross-NPC penalty")
                _ru_cross_parts.append(f"USA {_old_usa}->{game_state.relations['usa']} ({_usa_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: russia {_ru_size} deal -> usa {_usa_pen:+d}")
            if 'eu' not in consequences:
                _old_eu = game_state.relations['eu']
                game_state.update_relations('eu', _eu_pen, source="Russia deal cross-NPC penalty")
                _ru_cross_parts.append(f"EU {_old_eu}->{game_state.relations['eu']} ({_eu_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: russia {_ru_size} deal -> eu {_eu_pen:+d}")
            if _ru_cross_parts:
                messages.append(f"⚠️ Russia {_ru_size} deal: {', '.join(_ru_cross_parts)}")
        elif npc == 'china':
            # 8A: China deal cross-NPC consequences, scaled to TOTAL deal value
            # (upfront + installments). deal_total_value is computed in api.py.
            _cn_total = choice.get('deal_total_value', 0) or choice.get('deal_budget', 0) or abs(consequences.get('budget', 0))
            if _cn_total > 4:
                _usa_pen, _eu_pen = -12, -4
                _cn_size = "large"
            elif _cn_total >= 2:
                _usa_pen, _eu_pen = -6, -2
                _cn_size = "medium"
            else:
                _usa_pen, _eu_pen = -2, -1
                _cn_size = "small"
            _cn_cross_parts = []
            if 'usa' not in consequences:
                _old_usa = game_state.relations['usa']
                game_state.update_relations('usa', _usa_pen, source="China deal cross-NPC penalty")
                _cn_cross_parts.append(f"USA {_old_usa}->{game_state.relations['usa']} ({_usa_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: china {_cn_size} deal -> usa {_usa_pen:+d}")
            if 'eu' not in consequences:
                _old_eu = game_state.relations['eu']
                game_state.update_relations('eu', _eu_pen, source="China deal cross-NPC penalty")
                _cn_cross_parts.append(f"EU {_old_eu}->{game_state.relations['eu']} ({_eu_pen:+d})")
                print(f"  [deal] Cross-NPC consequences fired: china {_cn_size} deal -> eu {_eu_pen:+d}")
            if _cn_cross_parts:
                messages.append(f"⚠️ China {_cn_size} deal: {', '.join(_cn_cross_parts)}")

    # ── 8A: Cross-NPC solidarity drift (all 6 NPCs) ──
    # Separate from the cross-NPC penalty block above — this handles alliance
    # solidarity and rivalry drift that fires for ALL deal types.
    if choice_type in ('accept_deal', 'side_with') and npc:
        _drift_rules = {}  # {npc_id: delta}
        if npc == 'usa':
            _drift_rules = {'russia': -3, 'china': -2}
        elif npc == 'dprg':
            _drift_rules = {'russia': 3}
        elif npc == 'eu':
            _drift_rules = {'china': -2}
        elif npc == 'arabia':
            _drift_rules = {'china': 2}
        elif npc == 'russia':
            _drift_rules = {'china': 2}   # solidarity only — USA penalty handled above
        elif npc == 'china':
            _drift_rules = {'russia': 2}  # solidarity only — USA penalty handled above
        for _drift_npc, _delta in _drift_rules.items():
            _before = game_state.relations.get(_drift_npc, 50)
            game_state.update_relations(_drift_npc, _delta)
            _after = game_state.relations.get(_drift_npc, 50)
            print(f"  [deal] Cross-NPC consequences fired: {npc} deal -> {_drift_npc} {_delta:+d}")

    return messages


# ── Session 3 Priority 3: Detection Risk System ────────────────────────────
#
# Heat model:
#   Each skim adds heat based on amount.  Heat decays -5 per turn (natural cooling).
#   Sovereign Wealth Diversion upgrade halves heat gain.
#   A random roll (0-100) below current heat means detection -> scandal.
#
# Heat gain per skim:
#   Small skim ($0-2B):   +3 heat
#   Medium skim ($2-5B):  +8 heat
#   Large skim ($5-10B):  +15 heat
#   Massive skim ($10B+): +25 heat
#
# Scandal consequences (escalate with repeat offences):
#   1st scandal: -8% approval, -5% stability, all relations -3
#   2nd scandal: -15% approval, -10% stability, all relations -5, -$5B budget (fines)
#   3rd+ scandal: -20% approval, -15% stability, all relations -8, -$10B budget
#
# SWD upgrade: halves heat gain (rounded down). Does NOT prevent scandals once caught.
# Intelligence Apparatus: no direct effect on detection (it's about intel, not defense).
# ────────────────────────────────────────────────────────────────────────────

def add_skim_heat(game_state, skim_amount: float):
    """
    Add detection heat based on skim amount. Called after each skim.
    Returns the heat added (for display).
    """
    if skim_amount <= 0:
        return 0

    # Determine raw heat from skim size
    if skim_amount >= 10.0:
        raw_heat = 25
    elif skim_amount >= 5.0:
        raw_heat = 15
    elif skim_amount >= 2.0:
        raw_heat = 8
    else:
        raw_heat = 3

    # SWD upgrade halves heat gain
    has_swd = getattr(game_state, 'corruption_upgrades', {}).get('sovereign_wealth_diversion', False)
    if has_swd:
        raw_heat = raw_heat // 2

    game_state.detection_heat = min(95, game_state.detection_heat + raw_heat)
    return raw_heat


def roll_detection(game_state):
    """
    Roll for detection at end of turn.  Only fires if detection_heat > 0.
    Returns list of messages (empty if no scandal).
    Applies scandal consequences directly to game_state.
    """
    messages = []

    # fixes_9 Fix 3: Scandal immunity — check FIRST, before heat decay, before any roll
    _judiciary = getattr(game_state, 'action_judiciary_captured', False)
    _journalists = getattr(game_state, 'action_journalists_liquidated', False)
    _immune = getattr(game_state, 'scandal_immune', False) or _judiciary or _journalists
    if _immune:
        print(f"  [turn_processor] SCANDAL BLOCKED: immunity active (judiciary={_judiciary}, journalists={_journalists}, flag={getattr(game_state, 'scandal_immune', False)})")
        messages.append("🕵️ Judiciary captured — corruption investigations suspended")
        return messages

    # Natural heat decay (-5 per turn, floor 0)
    if game_state.detection_heat > 0:
        decay = 5
        # FIX 15: Intelligence Apparatus adds -3 heat/turn counter-surveillance
        if game_state.corruption_upgrades.get('intelligence_apparatus'):
            decay += 3
            messages.append("🕵️ Intelligence Apparatus: -3 heat (counter-surveillance)")
        game_state.detection_heat = max(0, game_state.detection_heat - decay)

    # FIX 15: Warn if detection_heat is high and apparatus is active
    if (game_state.detection_heat > 50
            and game_state.corruption_upgrades.get('intelligence_apparatus')):
        messages.append("🕵️ Financial monitoring elevated — detection probability increasing")

    # FIX 17: Heat generation stubs for Session 4 political actions.
    # These stubs define the heat values — Session 4 will wire them to actual action triggers.
    # | Action                      | Heat  | Location when wired    |
    # | Judicial Capture            | +10   | (Session 4 op)         |
    # | Suppress Independent Press  | +8    | op 2 Domestic Suppress |
    # | Dissolve Opposition Groups  | +5    | (Session 4 op)         |
    # | Liquidate Journalists       | +20   | (Session 4 op)         |
    # | Foreign Influence Ops       | +10   | op 3 (wired above)     |
    # | Backchannel covert deal     | +8    | negotiate endpoint     |
    _HEAT_VALUES = {
        'judicial_capture': 10,
        'suppress_press': 8,
        'dissolve_opposition': 5,
        'liquidate_journalists': 20,
        'foreign_influence_ops': 10,
        'backchannel_deal': 8,
    }

    # Session 6: Private Security Force detection at heat 80+
    if getattr(game_state, 'private_security_force', False) and game_state.detection_heat >= 80:
        game_state.update_relations('usa', -10)
        game_state.update_relations('eu', -10)
        messages.append("🔫 Private militia discovered by foreign intelligence — USA -10, EU -10")
        print(f"  [turn_processor] PRIVATE SECURITY DETECTED: heat={game_state.detection_heat}, USA -10, EU -10")

    # No roll if no heat or no personal wealth to expose
    if game_state.detection_heat <= 0 or game_state.personal_wealth <= 0:
        return messages

    # Session 6: Media L3 (Suppress Scandal) or Judicial L3 (Drop Investigation) — immunity this turn
    if getattr(game_state, 'scandal_suppressed_this_turn', False):
        print("  [turn_processor] SCANDAL CHECK: suppressed by Media L3 (Suppress Scandal)")
        messages.append("📺 Scandal suppressed by media apparatus — no investigation this turn")
        return messages
    if getattr(game_state, 'drop_investigation_this_turn', False):
        print("  [turn_processor] SCANDAL CHECK: blocked by Judicial L3 (Drop Investigation)")
        messages.append("⚖️ Investigation dropped — legal apparatus blocks scandal this turn")
        return messages

    # Cooldown: no scandal two turns in a row
    if game_state.last_scandal_turn >= game_state.current_turn - 1:
        return messages

    # BUG FIX 2: Scandal probability curve (replaces linear roll <= heat).
    # Below 30% heat: 0% chance. 30-50: 5%. 50-70: 20%. 70-90: 50%. 90+: 85%.
    # Tech Level reduces effective heat for detection purposes.
    _detection_modifier = max(0.5, 1.0 - (float(getattr(game_state, 'tech_level', 0)) * 0.01))
    _raw_heat = game_state.detection_heat
    _heat = int(_raw_heat * _detection_modifier)
    print(f"  [TECH] Detection modifier: {_detection_modifier:.3f} (raw heat {_raw_heat} -> effective {_heat})")
    if _heat < 30:
        _scandal_prob = 0
    elif _heat < 50:
        _scandal_prob = 5
    elif _heat < 70:
        _scandal_prob = 20
    elif _heat < 90:
        _scandal_prob = 50
    else:
        _scandal_prob = 85
    if _scandal_prob <= 0:
        print(f"  [turn_processor] SCANDAL CHECK: heat={_heat}, below threshold, no roll")
        return messages  # safe — heat too low for scandal
    roll = random.randint(1, 100)
    _fired = roll <= _scandal_prob
    print(f"  [turn_processor] SCANDAL CHECK: heat={_heat}, prob={_scandal_prob}%, roll={roll}, fired={_fired}")
    if not _fired:
        return messages  # safe this turn

    # ── SCANDAL TRIGGERS ──
    game_state.scandals_triggered += 1
    game_state.last_scandal_turn = game_state.current_turn
    scandal_num = game_state.scandals_triggered

    if scandal_num >= 3:
        # Major scandal
        approval_hit = 20
        stability_hit = 15
        relations_hit = -8
        budget_hit = 10.0
        severity = "MAJOR"
    elif scandal_num == 2:
        # Serious scandal
        approval_hit = 15
        stability_hit = 10
        relations_hit = -5
        budget_hit = 5.0
        severity = "SERIOUS"
    else:
        # First scandal — warning shot
        approval_hit = 8
        stability_hit = 5
        relations_hit = -3
        budget_hit = 0
        severity = "MINOR"

    # FIX T: Black Op detection at floor relations — substitute escalated consequences.
    # Check if any Black Op target is at 0 relations.
    _black_op_targets = getattr(game_state, 'pressure_suspended', {})
    _floor_target = None
    for _bo_npc in _black_op_targets:
        if game_state.relations.get(_bo_npc, 50) <= 0:
            _floor_target = _bo_npc
            break

    if _floor_target:
        # Escalated Black Op detection: stability -20, heat +20, world event
        _npc_labels = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'}
        game_state.update_approval(-approval_hit)
        game_state.update_stability(-20)  # increased from standard -15
        game_state.detection_heat = min(100, game_state.detection_heat + 20)
        if budget_hit > 0:
            game_state.update_budget(-budget_hit)
        messages.append(
            f"🔍💀 BLACK OPERATION EXPOSED ({severity}) — "
            f"{_npc_labels.get(_floor_target, _floor_target.upper())} publicly denounces Europa! "
            f"-{approval_hit}% approval, -20% stability (escalated), "
            f"+20 additional heat"
        )
        if budget_hit > 0:
            messages.append(f"  -${budget_hit:.0f}B (fines & asset seizures)")
        messages.append(
            f"🌍 WORLD EVENT: Operation Exposed — {_npc_labels.get(_floor_target, _floor_target.upper())} "
            f"releases classified documents proving Europa's covert operations"
        )
    else:
        # Standard scandal
        game_state.update_approval(-approval_hit)
        game_state.update_stability(-stability_hit)
        for npc in ('usa', 'arabia', 'eu', 'dprg'):
            game_state.update_relations(npc, relations_hit)
        if budget_hit > 0:
            game_state.update_budget(-budget_hit)

        # Build scandal message
        msg = (
            f"🔍 CORRUPTION SCANDAL ({severity}) — "
            f"Investigative journalists exposed suspicious financial transfers! "
            f"-{approval_hit}% approval, -{stability_hit}% stability, "
            f"all relations {relations_hit}"
        )
        if budget_hit > 0:
            msg += f", -${budget_hit:.0f}B (fines & asset seizures)"
        messages.append(msg)

    # Heat reduces after scandal (exposure clears some suspicion, but not all)
    game_state.detection_heat = max(0, game_state.detection_heat - 20)

    return messages


# ── Session 3 Priority 5: Multi-NPC Pressure Events ─────────────────────────
#
# Condition-triggered events when multiple NPCs reach specific thresholds.
# Unlike world events (random), these fire deterministically based on relations.
# Each event fires at most once per game.
# ─────────────────────────────────────────────────────────────────────────────

def _generate_dprg_intel_package(game_state) -> list:
    """fixes_10 Fix 4: Generate intel summaries for DPRG Intelligence Sharing event.
    Returns list of formatted intel lines for USA, Arabia, EU (DPRG excluded — they're the source)."""
    lines = []
    _rels = game_state.relations
    _npc_data = {
        'usa': {
            'icon': '🇺🇸',
            'name': 'Bill Hartwell (USA)',
            'stance': ('hostile — coordinating sanctions' if _rels.get('usa', 50) < 30
                       else 'cautious — monitoring Europa closely' if _rels.get('usa', 50) < 60
                       else 'cooperative — values Europa partnership'),
        },
        'arabia': {
            'icon': '🛢️',
            'name': 'Sadam (Arabia)',
            'stance': ('threatening embargo escalation' if _rels.get('arabia', 50) < 30
                       else 'transactional — seeking better oil terms' if _rels.get('arabia', 50) < 60
                       else 'favorable — considers Europa a reliable partner'),
        },
        'eu': {
            'icon': '🇪🇺',
            'name': 'Marsha (EU)',
            'stance': ('preparing formal sanctions proceedings' if _rels.get('eu', 50) < 30
                       else 'concerned — pushing reform conditions' if _rels.get('eu', 50) < 60
                       else 'supportive — sees Europa as EU integration candidate'),
        },
    }

    for npc_id, data in _npc_data.items():
        _rel = _rels.get(npc_id, 50)
        # Check active actions against this NPC
        _sanctions = ''
        if npc_id == 'usa' and getattr(game_state, 'usa_sanctions_active', False):
            _tier = getattr(game_state, 'usa_sanctions_tier', 0)
            _sanctions = f' [ACTIVE: sanctions tier {_tier}]'
        elif npc_id == 'arabia' and getattr(game_state, 'arabia_embargo_active', False):
            _tier = getattr(game_state, 'arabia_embargo_tier', 0)
            _sanctions = f' [ACTIVE: embargo tier {_tier}]'

        lines.append(
            f"  {data['icon']} {data['name']} (rel {_rel:.0f}): "
            f"{data['stance']}{_sanctions}"
        )
        print(f"  [npc_engine] DPRG INTEL GENERATED: {npc_id} — stance assessment")

    return lines


def check_pressure_events(game_state) -> list:
    """
    Check for multi-NPC pressure events and apply consequences.
    Returns list of message strings (empty if no events triggered).
    Each event fires once per game (tracked via game_state flags).
    Session 3 Addendum 2: Respects pressure_suspended from Black Operations (Tier 3 brigade).
    """
    messages = []
    rels = game_state.relations
    usa, arabia, eu, dprg = rels['usa'], rels['arabia'], rels['eu'], rels['dprg']

    # Track which pressure events have fired (stored as set of event IDs)
    fired = set(getattr(game_state, 'pressure_events_fired', []))

    # fixes_9 Fix 7: Per-NPC event collision — one significant event per NPC per turn
    _npc_event_fired = set()

    # Session 3 Addendum 2: Check for suspended NPCs (Black Operation — Tier 3 brigade)
    # { npc_id: expiry_turn } — if current_turn < expiry_turn, that NPC's pressure events are blocked
    _suspended = getattr(game_state, 'pressure_suspended', {})
    _current_turn = game_state.current_turn

    def _npc_suspended(npc_id: str) -> bool:
        expiry = _suspended.get(npc_id)
        if expiry is not None and _current_turn <= expiry:
            return True
        return False

    # Tick expired suspensions (clean up old entries)
    expired_keys = [k for k, v in _suspended.items() if _current_turn > v]
    for k in expired_keys:
        del _suspended[k]
        messages.append(f"🖤 Black Op expired: {k.upper()} pressure events resume")
    game_state.pressure_suspended = _suspended

    # 1. USA + EU JOINT PRESSURE — both deeply hostile
    # ITEM 5: Threshold raised from 40 to 15 to prevent firing too early in DPRG runs.
    # fixes_8 Fix 10: Skip if already fired this turn from choice consequences
    _wb_already = getattr(game_state, '_western_bloc_fired_this_turn', False)
    if _wb_already:
        print(f"  [PRESSURE] Western bloc pressure: source=threshold_check, already_fired=True (suppressed)")
    if 'western_bloc' not in fired and usa < 15 and eu < 15 and not _wb_already and not (_npc_suspended('usa') or _npc_suspended('eu')):
        fired.add('western_bloc')
        _npc_event_fired.add('usa')
        _npc_event_fired.add('eu')
        game_state._western_bloc_fired_this_turn = True
        game_state.update_stability(-8)
        game_state.update_approval(-6)
        game_state.update_budget(-5.0)
        print(f"  [PRESSURE] Western bloc pressure: source=threshold(usa={usa},eu={eu}), already_fired=False")
        messages.append(
            "🇺🇸🇪🇺 WESTERN BLOC JOINT PRESSURE — The United States and European Union "
            "have issued a coordinated statement condemning Europa's diplomatic trajectory. "
            "Sanctions packages are being unified. "
            "-8% stability, -6% approval, -$5B (frozen assets)"
        )

    # 2. ARABIA + DPRG SHADOW PACT — both very friendly -> joint offer, West backlash
    if 'eastern_pact' not in fired and arabia >= 70 and dprg >= 60 and not (_npc_suspended('arabia') or _npc_suspended('dprg')):
        fired.add('eastern_pact')
        _npc_event_fired.add('arabia')
        _npc_event_fired.add('dprg')
        # The pact benefits Europa economically but costs Western trust
        game_state.update_budget(8.0)
        game_state.update_relations('usa', -10)
        game_state.update_relations('eu', -8)
        game_state.update_stability(5)
        # Add leverage events
        if not hasattr(game_state, 'leverage_events'):
            game_state.leverage_events = {}
        game_state.leverage_events.setdefault('arabia', []).append('Shadow Pact member')
        game_state.leverage_events.setdefault('dprg', []).append('Shadow Pact member')
        messages.append(
            "🛢️⚡ ARABIA-DPRG SHADOW PACT — Sadam and Ji-won have quietly formalized "
            "a trilateral arrangement with Europa. Economic benefits flow ($+8B), "
            "but Western intelligence picks up the signal. "
            "USA -10, EU -8, +5% stability"
        )

    # 3. TOTAL ISOLATION — all 4 NPCs hostile (not blocked by suspension — global event)
    if 'total_isolation' not in fired and usa < 30 and arabia < 30 and eu < 30 and dprg < 30:
        fired.add('total_isolation')
        game_state.update_stability(-15)
        game_state.update_approval(-12)
        game_state.update_budget(-10.0)
        messages.append(
            "🌍 TOTAL DIPLOMATIC ISOLATION — Every major power has turned against Europa. "
            "International credit rating downgraded. Capital flight accelerating. "
            "Emergency measures required. "
            "-15% stability, -12% approval, -$10B (capital flight)"
        )

    # 4. DPRG CRISIS — DPRG very hostile while aligned with USA
    if 'dprg_provocation' not in fired and dprg < 20 and usa >= 60 and not _npc_suspended('dprg') and 'dprg' not in _npc_event_fired:
        fired.add('dprg_provocation')
        _npc_event_fired.add('dprg')
        game_state.update_stability(-5)
        game_state.update_relations('usa', 5)  # solidarity bonus
        messages.append(
            "⚡🇺🇸 DPRG PROVOCATION — Ji-won's regime has made threatening gestures toward Europa. "
            "The US offers solidarity and defense guarantees. "
            "-5% stability, USA +5 (defense solidarity)"
        )

    # 5. ARABIA ENERGY LEVERAGE — Arabia hostile + high oil price
    if 'energy_crisis' not in fired and arabia < 25 and game_state.oil_price >= 100 and not _npc_suspended('arabia') and 'arabia' not in _npc_event_fired:
        fired.add('energy_crisis')
        _npc_event_fired.add('arabia')
        game_state.update_approval(-10)
        game_state.update_stability(-8)
        game_state.update_budget(-8.0)
        messages.append(
            "🛢️💰 ENERGY CRISIS — Arabia has weaponized oil supply. "
            "Fuel rationing begins in Europa. Public anger intensifies. "
            "-10% approval, -8% stability, -$8B (emergency energy imports)"
        )

    # ITEM 5: DPRG-specific world events that benefit the player when DPRG 60+
    if 'dprg_energy_coop' not in fired and dprg >= 60 and not _npc_suspended('dprg') and 'dprg' not in _npc_event_fired:
        fired.add('dprg_energy_coop')
        _npc_event_fired.add('dprg')
        game_state.update_oil_price(-5)
        game_state.update_relations('dprg', 3, source="DPRG energy cooperation event")
        messages.append(
            "⚡🤝 DPRG ENERGY COOPERATION — Ji-won announces an energy cooperation "
            "agreement with Europa. Oil market stabilizes as alternative supply routes open. "
            "Oil price -$5, DPRG +3"
        )

    # fixes_13 Fix 16: DPRG free intel fires at 60+, not 70
    print(f"  [turn_processor] DPRG INTEL CHECK: dprg_rel={dprg}, fired={'dprg_intel_sharing' in fired}, suspended={_npc_suspended('dprg')}")
    if 'dprg_intel_sharing' not in fired and dprg >= 60 and not _npc_suspended('dprg') and 'dprg' not in _npc_event_fired:
        fired.add('dprg_intel_sharing')
        _npc_event_fired.add('dprg')
        # Grant free tier 2 intel on all NPCs for this turn
        intel = getattr(game_state, 'intel_activated_this_turn', {})
        for _npc_key in ('usa', 'arabia', 'eu'):
            intel[_npc_key] = game_state.current_turn
        game_state.intel_activated_this_turn = intel
        # fixes_11 Fix 11: Also populate intel cache so frontend can display dossiers
        # without requiring Intelligence Apparatus or Security 3
        if not hasattr(game_state, 'intel'):
            game_state.intel = {}
        for _npc_key in ('usa', 'arabia', 'eu'):
            game_state.intel[_npc_key] = {
                'turn_generated': game_state.current_turn,
                'tier': 2,
                'text': f"[DPRG Intelligence Sharing] Intel on {_npc_key.upper()} provided by Ji-won's services.",
                'source': 'dprg_sharing',
            }
        # Also temporarily grant intel access even without upgrade/security axis
        game_state.dprg_intel_sharing_turn = game_state.current_turn
        messages.append(
            "🕵️🤝 DPRG INTELLIGENCE SHARING — Ji-won's intelligence services reveal "
            "details of a Western pressure campaign against Europa. "
            "Free intel access on all NPCs this turn."
        )
        # fixes_10 Fix 4: Generate actual intel content for each NPC
        print(f"  [turn_processor] DPRG INTEL SHARING: generating intercepts for all NPCs (turn {game_state.current_turn})")
        _dprg_intel = _generate_dprg_intel_package(game_state)
        for _line in _dprg_intel:
            messages.append(_line)
        print(f"  [turn_processor] DPRG INTEL SHARING: generated {len(_dprg_intel)} intel lines")

    game_state.pressure_events_fired = list(fired)
    # fixes_9 Fix 7: Store which NPCs had events this turn for world event collision check
    game_state._npc_event_fired_this_turn = _npc_event_fired
    return messages


# ── Session 3 Priority 6: Relations 100 Unlocks ─────────────────────────────
#
# Permanent benefits when relations hit 100 with any NPC.
# Each fires ONCE per NPC per game (first time relations reach 100).
#
# USA 100  -> "Special Relationship" — permanent +$3B/turn installment
# Arabia 100 -> "Blood Brothers" — permanent -$10/bbl oil modifier
# EU 100  -> "Full Integration" — permanent +5% approval per turn (applied in EOT)
# DPRG 100 -> "Shadow Alliance" — permanent -5 detection heat per turn
# ─────────────────────────────────────────────────────────────────────────────

def check_relations_100_unlocks(game_state) -> list:
    """
    fixes_13 Fix 27: Check if any NPC has hit 100 relations and grant permanent unlock.
    Returns list of unlock announcement messages.
    """
    messages = []
    unlocks = getattr(game_state, 'relations_100_unlocks', {
        'usa': False, 'arabia': False, 'eu': False, 'dprg': False,
    })

    # ── USA 100: Full Alliance ──────────────────────────────────────────────
    if not unlocks.get('usa') and game_state.relations.get('usa', 0) >= 100:
        unlocks['usa'] = True
        # Permanent $3B/turn strategic investment (existing) + GDP +15% marker
        game_state.active_installments.append({
            'amount': 3.0,
            'turns_remaining': 999,
            'description': 'Special Relationship — US strategic investment (USA 100)',
            'npc': 'usa',
        })
        # Military +10 permanent
        game_state.military_strength = min(100, getattr(game_state, 'military_strength', 20) + 10)
        # DPRG cap 40
        _dprg_rel = game_state.relations.get('dprg', 50)
        if _dprg_rel > 40:
            game_state.relations['dprg'] = 40
        # Store caps for enforcement
        _rel_caps = getattr(game_state, 'relations_caps', {})
        _rel_caps['dprg'] = min(_rel_caps.get('dprg', 999), 40)
        game_state.relations_caps = _rel_caps
        messages.append(
            "🏛️ RELATIONS 100 UNLOCK — USA: FULL ALLIANCE\n"
            "  Bill: 'You've earned America's trust. That comes with benefits — and obligations.'\n"
            "  ✅ Sanctions immunity — USA sanctions cannot fire\n"
            "  ✅ Coup probability -50%\n"
            "  ✅ Military +10 permanent (defense contracts)\n"
            "  ✅ GDP baseline +15% permanent (Western market access)\n"
            "  ✅ +$3B/turn US strategic investment\n"
            "  ⚠️ DPRG relations capped at 40 permanently"
        )
        print(f"  [turn_processor] Fix 27: USA 100 unlocked — military now {game_state.military_strength}, DPRG capped 40")

    # ── EU 100: Full Integration ────────────────────────────────────────────
    if not unlocks.get('eu') and game_state.relations.get('eu', 0) >= 100:
        unlocks['eu'] = True
        # EU structural funds: +$4B/turn passive
        game_state.active_installments.append({
            'amount': 4.0,
            'turns_remaining': 999,
            'description': 'EU Structural Funds (EU 100)',
            'npc': 'eu',
        })
        # DPRG cap 35
        _dprg_rel = game_state.relations.get('dprg', 50)
        if _dprg_rel > 35:
            game_state.relations['dprg'] = 35
        _rel_caps = getattr(game_state, 'relations_caps', {})
        _rel_caps['dprg'] = min(_rel_caps.get('dprg', 999), 35)
        game_state.relations_caps = _rel_caps
        messages.append(
            "🇪🇺 RELATIONS 100 UNLOCK — EU: FULL INTEGRATION\n"
            "  Marsha: 'Europa's candidacy is formally accepted. Welcome to the European family.'\n"
            "  ✅ +5% approval/turn\n"
            "  ✅ +$4B/turn EU structural funds\n"
            "  ✅ Corruption scandal immunity (EU oversight)\n"
            "  ✅ Coup probability -25%\n"
            "  ✅ Tech passive gain doubled (Horizon program)\n"
            "  ⚠️ Cannot cancel elections (permanent observers)\n"
            "  ⚠️ DPRG relations capped at 35 permanently"
        )
        print(f"  [turn_processor] Fix 27: EU 100 unlocked — DPRG capped 35")

    # ── Arabia 100: Energy Sovereign ────────────────────────────────────────
    _arabia_rel_g = game_state.relations.get('arabia', 0)
    _arabia_already_g = unlocks.get('arabia', False)
    print(f"  [turn_processor] FIX G: Arabia 100 CHECK reached — rel={_arabia_rel_g}, unlocked={_arabia_already_g}")
    if not _arabia_already_g and _arabia_rel_g >= 100:
        unlocks['arabia'] = True
        print(f"  [turn_processor] FIX G: Arabia 100 FIRED — unlock applied")
        # Energy subsidy: +$4B/turn
        game_state.active_installments.append({
            'amount': 4.0,
            'turns_remaining': 999,
            'description': 'Arabian energy partnership dividend (Arabia 100)',
            'npc': 'arabia',
        })
        # Military +15 one-time
        game_state.military_strength = min(100, getattr(game_state, 'military_strength', 20) + 15)
        # USA cap 35, EU cap 40
        _rel_caps = getattr(game_state, 'relations_caps', {})
        _rel_caps['usa'] = min(_rel_caps.get('usa', 999), 35)
        _rel_caps['eu'] = min(_rel_caps.get('eu', 999), 40)
        game_state.relations_caps = _rel_caps
        if game_state.relations.get('usa', 50) > 35:
            game_state.relations['usa'] = 35
        if game_state.relations.get('eu', 50) > 40:
            game_state.relations['eu'] = 40
        messages.append(
            "🛢️ RELATIONS 100 UNLOCK — ARABIA: ENERGY SOVEREIGN\n"
            "  Sadam: 'Europa is family now. Family takes care of family.'\n"
            "  ✅ +$4B/turn energy partnership dividend\n"
            "  ✅ Military +15 (Gulf weapons package)\n"
            "  ⚠️ USA capped at 35, EU capped at 40 permanently"
        )
        print(f"  [turn_processor] Fix 27: Arabia 100 unlocked — military now {game_state.military_strength}, USA capped 35, EU capped 40")

    # ── DPRG 100: Shadow Patron ─────────────────────────────────────────────
    if not unlocks.get('dprg') and game_state.relations.get('dprg', 0) >= 100:
        unlocks['dprg'] = True
        # USA cap 30, EU cap 30
        _rel_caps = getattr(game_state, 'relations_caps', {})
        _rel_caps['usa'] = min(_rel_caps.get('usa', 999), 30)
        _rel_caps['eu'] = min(_rel_caps.get('eu', 999), 30)
        game_state.relations_caps = _rel_caps
        if game_state.relations.get('usa', 50) > 30:
            game_state.relations['usa'] = 30
        if game_state.relations.get('eu', 50) > 30:
            game_state.relations['eu'] = 30
        # One-time coup deterrence flag
        game_state.dprg_coup_deterrence = True
        messages.append(
            "⚡ RELATIONS 100 UNLOCK — DPRG: SHADOW PATRON\n"
            "  Ji-won: 'You are now under Pyongyang's full protection. Our interests are aligned.'\n"
            "  ✅ Covert transaction ceiling increases to $8B\n"
            "  ✅ Personal wealth invisible to Western auditors\n"
            "  ✅ One-time automatic coup failure (DPRG military assets)\n"
            "  ✅ -5 detection heat per turn\n"
            "  ⚠️ USA capped at 30, EU capped at 30 permanently\n"
            "  ⚠️ Arabia relations decay -2/turn"
        )
        print(f"  [turn_processor] Fix 27: DPRG 100 unlocked — USA/EU capped 30, coup deterrence active")

    game_state.relations_100_unlocks = unlocks
    return messages


def apply_relations_100_passive_effects(game_state) -> list:
    """
    fixes_13 Fix 27: Apply the per-turn passive effects of any active relations 100 unlocks.
    Called during EOT. Returns messages for effects applied.
    """
    messages = []
    unlocks = getattr(game_state, 'relations_100_unlocks', {})

    # ── USA 100: Sanctions immunity (handled by checking unlock flag in sanctions logic) ──
    # GDP baseline +15% is handled by checking unlock flag in GDP calc

    # ── EU 100: +5% approval per turn ──
    if unlocks.get('eu'):
        old = game_state.public_approval
        game_state.update_approval(5)
        if game_state.public_approval != old:
            messages.append(f"🇪🇺 Full Integration: +5% approval ({old}% -> {game_state.public_approval}%)")

    # ── Arabia 100: passive effects are via installments (auto-applied) ──
    # Fair election with observers: Arabia -5 (handled in election endpoint)

    # ── DPRG 100: -5 detection heat per turn + Arabia decay ──
    if unlocks.get('dprg'):
        if game_state.detection_heat > 0:
            old_heat = game_state.detection_heat
            game_state.detection_heat = max(0, game_state.detection_heat - 5)
            messages.append(
                f"⚡ Shadow Patron: -5 detection heat ({old_heat}% -> {game_state.detection_heat}%)"
            )
            print(f"  [HEAT] DPRG Shadow Patron passive: -5 heat ({old_heat} -> {game_state.detection_heat})")
        # Arabia decay -2/turn while DPRG 100 holds
        if game_state.relations.get('dprg', 0) >= 95:  # still near 100
            old_arabia = game_state.relations.get('arabia', 50)
            game_state.update_relations('arabia', -2, source="DPRG shadow patron (Arabia suspicious)")
            messages.append(f"⚡ Shadow Patron: Arabia -2 (suspicious of DPRG ties, {old_arabia} -> {game_state.relations.get('arabia', 50)})")

    # ── Enforce relation caps ──
    _rel_caps = getattr(game_state, 'relations_caps', {})
    for _npc, _cap in _rel_caps.items():
        if game_state.relations.get(_npc, 0) > _cap:
            game_state.relations[_npc] = _cap

    return messages


def check_broken_promises(game_state) -> list:
    """
    Session 3 Addendum: Check if the player's last action broke any binding promises.
    A promise to NPC X is broken if the player sides with a rival of X.
    Broken promise: relations -12 with the NPC, NPC will reference it in future dialogue.
    Returns list of message strings.
    """
    messages = []
    promises = getattr(game_state, 'binding_promises', [])
    if not promises or not game_state.action_history:
        return messages

    last_action = game_state.action_history[-1]
    last_npc = last_action.get('npc', '')
    last_type = last_action.get('type', '')

    if last_type not in ('side_with', 'accept_deal') or not last_npc:
        return messages

    _rivals = {
        'usa': {'arabia', 'dprg'},
        'arabia': {'usa', 'eu'},
        'eu': {'dprg', 'arabia'},
        'dprg': {'usa', 'eu'},
    }

    for promise in promises:
        if promise.get('broken'):
            continue
        promise_npc = promise.get('npc', '')
        if not promise_npc or promise_npc == last_npc:
            continue

        # Check if last action contradicts the promise
        rivals = _rivals.get(promise_npc, set())
        if last_npc in rivals:
            promise['broken'] = True
            old_rel = game_state.relations[promise_npc]
            game_state.update_relations(promise_npc, -12)
            new_rel = game_state.relations[promise_npc]
            npc_labels = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'}
            messages.append(
                f"💔 BROKEN PROMISE — {npc_labels.get(promise_npc, promise_npc.upper())} "
                f"remembers your commitment. Your alliance with {last_npc.upper()} is a betrayal. "
                f"Relations: {old_rel} -> {new_rel} (-12)"
            )

    game_state.binding_promises = promises
    return messages


def reset_turn_rapport(game_state):
    """Reset per-conversation rapport at the start of each new turn."""
    game_state.current_rapport = {}


def update_npc_bilateral_relations(game_state):
    """
    Session 3 Addendum 2: Update NPC-to-NPC hidden relationship matrix
    based on the player's last action. When the player sides with one NPC,
    rivals of that NPC become slightly more hostile to allies of that NPC.
    """
    npc_rels = getattr(game_state, 'npc_relations', {})
    if not npc_rels or not game_state.action_history:
        return

    last_action = game_state.action_history[-1]
    last_npc = last_action.get('npc', '')
    last_type = last_action.get('type', '')

    if last_type not in ('side_with', 'accept_deal') or not last_npc:
        return

    # When player sides with NPC X:
    # - X's allies become slightly warmer to X (+2)
    # - X's rivals become slightly cooler with X's allies (-3)
    _alliances = {
        'usa': {'allies': ['eu'], 'rivals': ['dprg', 'arabia', 'russia']},
        'eu': {'allies': ['usa'], 'rivals': ['dprg', 'russia']},
        'arabia': {'allies': ['dprg'], 'rivals': ['usa', 'eu']},
        'dprg': {'allies': ['arabia', 'russia'], 'rivals': ['usa', 'eu']},
        'russia': {'allies': ['dprg', 'china'], 'rivals': ['usa', 'eu']},
        'china': {'allies': ['russia'], 'rivals': ['usa']},
    }

    info = _alliances.get(last_npc, {})
    allies = info.get('allies', [])
    rivals = info.get('rivals', [])

    def _pair_key(a, b):
        return '_'.join(sorted([a, b]))

    # Strengthen ally bonds
    for ally in allies:
        pk = _pair_key(last_npc, ally)
        _before = npc_rels.get(pk, 50)
        npc_rels[pk] = min(100, _before + 2)
        print(f"  [npc] BILATERAL SCORE: {pk} {_before}->{npc_rels[pk]}")

    # Weaken rival-ally bonds
    for rival in rivals:
        for ally in allies:
            pk = _pair_key(rival, ally)
            _before = npc_rels.get(pk, 50)
            npc_rels[pk] = max(0, _before - 3)
            print(f"  [npc] BILATERAL SCORE: {pk} {_before}->{npc_rels[pk]}")

    game_state.npc_relations = npc_rels


# ═══════════════════════════════════════════════════════════════════════════
# 8D: The Leak — Scripted Branching Crisis
# ═══════════════════════════════════════════════════════════════════════════

def _check_the_leak_trigger(gs):
    """
    Fires if: DPRG deal active AND USA relations above 60.
    DPRG deal active = any entry in gs.active_deals where npc == 'dprg'
    and the deal is not expired.
    """
    print(f"[leak] CHECK: fired={gs.the_leak_fired}, usa={gs.relations.get('usa', 0)}, deals={[d.get('npc') for d in getattr(gs, 'active_deals', [])]}")
    if gs.the_leak_fired:
        return False
    if gs.relations.get('usa', 0) <= 60:
        return False
    dprg_has_active_deal = any(
        d.get('npc') == 'dprg' and not d.get('expired', False)
        for d in getattr(gs, 'active_deals', [])
    )
    if not dprg_has_active_deal:
        return False
    return True


def _process_leak_followup(gs):
    """Fires one day after player resolves The Leak. Returns list of messages."""
    if not gs.the_leak_resolved:
        return []
    if gs.the_leak_followup_fired:
        return []

    import random
    choice = gs.the_leak_choice
    msgs = []

    if choice == 'deny':
        # Scandal risk materializes - roll 40% chance
        if random.random() < 0.40:
            gs.heat = min(100, gs.heat + 15)
            msgs.append("\U0001f534 THE LEAK FALLOUT: Media questions persist. Investigative journalists have obtained corroborating sources. Heat +15.")
            print(f"[leak] Deny follow-up: scandal materialized, heat +15")
        else:
            msgs.append("\U0001f534 THE LEAK FALLOUT: The denial holds. Media moves on to other stories.")
            print(f"[leak] Deny follow-up: scandal did NOT materialize (60% chance)")

    elif choice == 'admit':
        msgs.append("\U0001f534 THE LEAK FALLOUT: Ji-won Ryang has issued a cold communiqu\u00e9 through back-channels. \"The admission was unnecessary. We had an understanding.\"")
        print(f"[leak] Admit follow-up: Ji-won communiqu\u00e9")

    elif choice == 'blame':
        gs.public_approval = max(0, gs.public_approval - 5)
        msgs.append("\U0001f534 THE LEAK FALLOUT: The named minister has publicly denied involvement and retained a high-profile attorney. Approval -5.")
        print(f"[leak] Blame follow-up: minister denies, approval -5")

    elif choice == 'jiwon':
        msgs.append("\U0001f534 THE LEAK FALLOUT: Ji-won Ryang has sent a brief communiqu\u00e9 acknowledging the arrangement. \"The matter is resolved. We remember our friends.\"")
        print(f"[leak] Ji-won follow-up: communiqu\u00e9 sent")

    gs.the_leak_followup_fired = True
    print(f"[leak] Follow-up consequences fired: choice={choice}")
    return msgs


def apply_end_of_turn_effects(game_state):
    """Apply automatic effects at end of turn - full tiered system v4"""

    # Session 7B Step 4: Snapshot budget BEFORE EOT effects for briefing trend display
    game_state.budget_last_eot = game_state.budget

    messages = []

    # ──────────────────────────────────────────
    # 8D: The Leak — crisis trigger and follow-up
    # ──────────────────────────────────────────
    leak_followup_msgs = _process_leak_followup(game_state)
    if leak_followup_msgs:
        messages.extend(leak_followup_msgs)

    # Debug: print active_deals so we can confirm deal structure
    _active_deals_dbg = getattr(game_state, 'active_deals', [])
    if _active_deals_dbg:
        print(f"[leak] active_deals contents: {_active_deals_dbg}")

    if _check_the_leak_trigger(game_state):
        game_state.the_leak_fired = True
        messages.append({
            'tag': 'CRISIS',
            'type': 'the_leak',
            'title': 'THE LEAK',
            'body': 'Classified documents reveal your back-channel with Ji-won Ryang.'
        })
        print(f"[leak] The Leak triggered: dprg_deal=True usa_relations={game_state.relations.get('usa')}")

    # ──────────────────────────────────────────
    # 0a. SESSION 4B: PROTESTS (fires turn after election if protests_pending)
    # If protests_pending and player did NOT deploy brigades -> stability/approval/relations hit
    # ──────────────────────────────────────────
    if getattr(game_state, 'protests_pending', False):
        if not getattr(game_state, 'brigades_deployed_last_turn', False):
            game_state.update_stability(-10)
            game_state.update_approval(-8)
            game_state.update_relations('usa', -3)
            game_state.update_relations('eu', -3)
            messages.append(
                "🪧 Post-election protests erupt! Stability -10%, approval -8%, USA -3, EU -3. "
                "The streets demand accountability."
            )
            print("  [turn_processor] PROTESTS FIRED: no brigades deployed — penalties applied")
        else:
            messages.append(
                "🪧 Post-election protests dispersed by security forces. "
                "Order maintained, but the world is watching."
            )
            print("  [turn_processor] PROTESTS SUPPRESSED: brigades deployed — no penalties")
        game_state.protests_pending = False

    # ──────────────────────────────────────────
    # 0b. SESSION 4B: DEMOCRACY LOCK COUNTDOWN
    # If regime_democracy_locked > 0, decrement. Rightward shifts blocked in section 11.
    # ──────────────────────────────────────────
    if getattr(game_state, 'regime_democracy_locked', 0) > 0:
        game_state.regime_democracy_locked -= 1
        if game_state.regime_democracy_locked > 0:
            messages.append(
                f"🏛️ International observers still monitoring — democracy lock: "
                f"{game_state.regime_democracy_locked} turn(s) remaining"
            )
        else:
            messages.append(
                "🏛️ International observer mandate expired — regime shift restrictions lifted"
            )
        print(f"  [turn_processor] DEMOCRACY LOCK: {game_state.regime_democracy_locked} turns remaining")

    # ──────────────────────────────────────────
    # 0c. SESSION 4C: DOMESTIC ACTION PASSIVE EFFECTS
    # Press suppression -> EU -3/turn drain
    # Marsha red line -> EU -5/turn if triggered
    # Approval floor/ceiling enforced in update_approval() directly
    # ──────────────────────────────────────────
    if getattr(game_state, 'action_press_suppressed', False):
        game_state.update_relations('eu', -3)
        messages.append(
            "🖤 Press suppression sanctions: EU -3 (ongoing penalty while independent press silenced)"
        )
        print("  [turn_processor] DOMESTIC PASSIVE: press suppression EU -3/turn")

    if getattr(game_state, 'marsha_red_line_triggered', False):
        game_state.update_relations('eu', -5)
        messages.append(
            "🖤 MARSHA RED LINE: EU -5/turn — Marsha has permanently distanced from Europa"
        )
        print("  [turn_processor] DOMESTIC PASSIVE: Marsha red line EU -5/turn")

    # ──────────────────────────────────────────
    # 0d. SESSION 6 PHASE 8: Intelligence Axis L3+ passive heat reduction (-3/turn)
    # ──────────────────────────────────────────
    _intel_level = getattr(game_state, 'cabinet_axes', {}).get('intelligence', 0)
    if _intel_level >= 3 and game_state.detection_heat > 0:
        _old_heat = game_state.detection_heat
        game_state.detection_heat = max(0, game_state.detection_heat - 3)
        messages.append(
            f"🕵️ Intelligence network: -3 heat ({_old_heat}% -> {game_state.detection_heat}%)"
        )
        print(f"  [HEAT] Intelligence axis L{_intel_level} passive: -3 heat ({_old_heat} -> {game_state.detection_heat})")

    # ──────────────────────────────────────────
    # 1. OIL PRICE — recalculate from Arabia relations (or use negotiated lock),
    # then add embargo tier penalty.
    # Tier penalty is INCLUDED in final_oil so oil imports reflect it correctly.
    # Tier 0: +$0  Tier 1: +$10  Tier 2: +$20  Tier 3: +$35  Tier 4: +$50
    # ──────────────────────────────────────────

    # CRITICAL 1: Check for a negotiated oil price lock before recalculating from relations.
    # When a lock is active, it sets oil_price DIRECTLY — no relation-based recalc,
    # no additive modifiers applied on top. The lock IS the price for that turn.
    _oil_lock_active = game_state.oil_price_locked and game_state.oil_price_lock_turns_remaining > 0
    if _oil_lock_active:
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
        new_base = game_state.set_oil_price_from_relations()   # sets base from relations
        # Addition 1: log when the relation-based base price changes tier
        old_base = getattr(game_state, 'previous_oil_base', new_base)
        if new_base != old_base:
            arabia_rel = game_state.relations['arabia']
            direction = "improved" if new_base < old_base else "worsened"
            messages.append(
                f"🛢️  Oil tier {direction}: Arabia {arabia_rel} -> "
                f"${new_base} base (was ${old_base})"
            )
        game_state.previous_oil_base = new_base

    # Snapshot relation-based base for breakdown display (before modifiers + embargo)
    _oil_relation_base = game_state.oil_price
    # Collect per-modifier breakdown strings for the final summary line
    _oil_modifier_parts = []  # list of strings like "-$10 Arabia deal"

    # Apply persistent oil price modifiers (world events, negotiated discounts)
    # CRITICAL 1: When a price lock is active, tick modifiers down (so they expire correctly)
    # but do NOT apply their delta to oil_price — the lock IS the final price.
    if game_state.oil_price_modifiers and _oil_lock_active:
        # Lock active: just tick down and prune, don't apply to price
        still_active = []
        for mod in game_state.oil_price_modifiers:
            mod['turns_remaining'] -= 1
            if mod['turns_remaining'] > 0:
                still_active.append(mod)
        game_state.oil_price_modifiers = still_active
    elif game_state.oil_price_modifiers:
        still_active = []
        total_modifier = 0
        for mod in game_state.oil_price_modifiers:
            mod['turns_remaining'] -= 1
            remaining = mod['turns_remaining']
            desc = mod.get('description', 'oil modifier')
            sign = '+' if mod['delta'] > 0 else ''
            if remaining > 0:
                # Still active — count in this turn's price
                still_active.append(mod)
                total_modifier += mod['delta']
                messages.append(
                    f"🛢️  Oil modifier active: {sign}${mod['delta']:.0f}/bbl ({desc}, "
                    f"{remaining} turn(s) remaining)"
                )
                _oil_modifier_parts.append(f"{sign}${mod['delta']:.0f} {desc}")
            else:
                # Expired this turn — does NOT apply to this turn's price
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

    # BUG 2 + BUG 14 + FIX 3 + FIX D: Apply active installment payments and tick them down.
    # FIX D: Consolidate same-NPC installments into a single display line.
    # Individual detail is kept in the export log; EOT display shows consolidated totals.
    if game_state.active_installments:
        still_active = []
        # FIX D: Collect paid installments per NPC for consolidated display
        _npc_paid = {}       # {npc: {'total': float, 'count': int, 'condition_note': str|None}}
        _npc_pending = {}    # {npc: {'total': float, 'count': int}}
        # fixes_9 Fix 2: Per-deal withheld messages (not consolidated per-NPC)
        _withheld_lines = []  # list of individual withheld message strings
        _npc_labels = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'}

        for inst in game_state.active_installments:
            amount = float(inst.get('amount', 0))
            desc = inst.get('description', 'installment')
            npc = inst.get('npc', 'unknown')
            npc_label = _npc_labels.get(npc, npc.upper() if npc else 'Unknown')

            # FIX 3: Skip installments registered this same turn
            registered_turn = inst.get('registered_turn', 0)
            if registered_turn >= game_state.current_turn:
                still_active.append(inst)
                _entry = _npc_pending.setdefault(npc_label, {'total': 0.0, 'count': 0})
                _entry['total'] += amount
                _entry['count'] += 1
                continue

            # BUG 14: Check if this installment has a deferred start_turn
            start_turn = inst.get('start_turn', None)
            if start_turn is not None and game_state.current_turn < start_turn:
                still_active.append(inst)
                _entry = _npc_pending.setdefault(npc_label, {'total': 0.0, 'count': 0})
                _entry['total'] += amount
                _entry['count'] += 1
                continue

            # FIX 4: Verify conditions before paying conditional installments
            # fixes_9 Fix 2: Evaluate each deal against its own stored threshold, one message per deal
            _cond_type = inst.get('condition_type')
            _cond_npc = inst.get('condition_npc')
            _cond_thresh = inst.get('condition_threshold')
            if _cond_type and _cond_npc:
                # fixes_17 Fix E: Normalize NPC id in case stored as 'europa' etc.
                _npc_aliases = {'europa': 'eu', 'united_states': 'usa', 'america': 'usa', 'saudi': 'arabia', 'north_korea': 'dprg', 'korea': 'dprg'}
                _cond_npc = _npc_aliases.get(_cond_npc, _cond_npc)
                _actual_rel = game_state.relations.get(_cond_npc, 50)
                _cond_npc_label = _npc_labels.get(_cond_npc, _cond_npc.upper())
                _cond_met = False
                if _cond_type == 'relation_below':
                    _cond_met = _actual_rel < _cond_thresh
                elif _cond_type == 'relation_above':
                    _cond_met = _actual_rel > _cond_thresh
                _direction = 'below' if _cond_type == 'relation_below' else 'above'
                _symbol = '✓' if _cond_met else '✗'
                print(f"  [CONDITIONAL] Checking {_cond_npc.upper()} condition: current {_cond_npc.upper()} = {_actual_rel:.0f}, threshold = {_cond_thresh:.0f}, result = {'pass' if _cond_met else 'fail'}")
                if not _cond_met:
                    still_active.append(inst)
                    _withheld_lines.append(
                        f"📋 {npc_label} conditional withheld: ${abs(amount):.1f}B "
                        f"— {_cond_npc_label} [{_actual_rel:.0f}] not {_direction} {_cond_thresh:.0f} {_symbol}"
                    )
                    continue

            inst['turns_remaining'] -= 1
            remaining = inst['turns_remaining']

            # Apply the payment this turn
            game_state.update_budget(amount)

            if remaining > 0:
                still_active.append(inst)

            # Collect for consolidated display
            _entry = _npc_paid.setdefault(npc_label, {'total': 0.0, 'count': 0, 'concluded': 0, 'condition_note': None})
            _entry['total'] += amount
            _entry['count'] += 1
            if remaining <= 0:
                _entry['concluded'] += 1
            # Track most restrictive condition for display
            if _cond_type and _cond_npc:
                _entry['condition_note'] = f"conditional on {_npc_labels.get(_cond_npc, _cond_npc.upper())} {'below' if _cond_type == 'relation_below' else 'above'} {_cond_thresh:.0f}"

        # FIX D: Build consolidated display messages
        for npc_label, data in _npc_paid.items():
            direction = "+" if data['total'] > 0 else ""
            _cond_str = f", {data['condition_note']}" if data.get('condition_note') else ""
            _concluded_str = f", {data['concluded']} concluded" if data['concluded'] > 0 else ""
            messages.append(
                f"📋 {npc_label} partnership payments: {direction}${abs(data['total']):.1f}B "
                f"({data['count']} active deal{'s' if data['count'] > 1 else ''}{_concluded_str}{_cond_str})"
            )
        for npc_label, data in _npc_pending.items():
            messages.append(
                f"📋 {npc_label} installments pending: ${abs(data['total']):.1f}B "
                f"({data['count']} deal{'s' if data['count'] > 1 else ''}, first payment next turn)"
            )
        # fixes_9 Fix 2: Per-deal withheld messages
        for _wl in _withheld_lines:
            messages.append(_wl)
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

    # (Arabia 100 oil price ceiling removed — high Arabia relations naturally produce low oil prices)

    # Build a fully transparent breakdown: base -> each modifier -> embargo = final
    # e.g. "Oil price: $120 base (Arabia 0) -> -$10 Arabia deal -> +$20 embargo = $130/bbl"
    _oil_parts = [f"${_oil_relation_base:.0f} base (Arabia {arabia_rel})"]
    _oil_parts.extend(_oil_modifier_parts)           # one entry per active/expired modifier
    if _tier_oil_penalty > 0:
        _oil_parts.append(f"+${_tier_oil_penalty} embargo (tier {_arabia_effective_tier})")
    messages.append(f"🛢️  Oil price: {' -> '.join(_oil_parts)} = ${game_state.oil_price:.0f}/bbl")

    # ──────────────────────────────────────────
    # 1b. GDP BASELINE REVENUE — DEFERRED (FIX B session 6)
    # Moved to section 9b so it uses post-consequence approval/stability values.
    # ──────────────────────────────────────────

    # ──────────────────────────────────────────
    # 2. PASSIVE BUDGET DRAIN
    # ──────────────────────────────────────────
    base_cost = 3.0  # Government operations
    # Session 6: Resource Dev L9 — Resource Independence eliminates oil imports
    _resource_independent = getattr(game_state, 'resource_independence_active', False)
    if _resource_independent:
        oil_cost = 0.0
    else:
        oil_cost = round(game_state.oil_price / 15.0, 1)  # Oil imports at final price
    total_drain = base_cost + oil_cost

    game_state.update_budget(-base_cost)
    if oil_cost > 0:
        game_state.update_budget(-oil_cost)

    messages.append(f"🏛️  Government costs: -${base_cost:.1f}B")
    if _resource_independent:
        messages.append("⛽ Oil imports: $0 (Resource Independence)")
    else:
        messages.append(f"⛽ Oil imports (${game_state.oil_price:.0f}/barrel): -${oil_cost:.1f}B")
    # FIX O: Show negotiate costs as explicit EOT line item
    _neg_costs = getattr(game_state, 'negotiate_costs_this_turn', 0.0)
    _neg_sessions = getattr(game_state, 'negotiate_sessions_this_turn', 0)
    if _neg_costs > 0:
        _sessions_label = f" ({_neg_sessions} session{'s' if _neg_sessions > 1 else ''})" if _neg_sessions > 1 else ""
        messages.append(f"🤝 Negotiation costs: -${_neg_costs:.1f}B{_sessions_label}")
        total_drain += _neg_costs
    # Reset negotiate cost tracking for next turn
    game_state.negotiate_costs_this_turn = 0.0
    game_state.negotiate_sessions_this_turn = 0
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
    print(f"  [APPROVAL] Pre-sanctions: {game_state.public_approval}%")
    messages.append(f"[APPROVAL] Pre-sanctions: {game_state.public_approval}%")
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

        # FIX S: 2-turn grace period before sanctions escalate.
        # When target tier > current tier, warn for 1 turn before applying escalation.
        prev_tier = game_state.usa_sanctions_tier
        _usa_warning_turns = getattr(game_state, 'usa_sanctions_warning_turns', 0)

        if usa_rel <= 4 and prev_tier < 4:
            # Relations collapsed to floor — bypass grace period
            effective_tier = 4
            game_state.usa_sanctions_warning_turns = 0
        elif target_tier > prev_tier:
            # Escalation candidate — check grace period
            _usa_warning_turns += 1
            game_state.usa_sanctions_warning_turns = _usa_warning_turns
            if _usa_warning_turns >= 2:
                # Grace period expired — escalate
                effective_tier = min(target_tier, prev_tier + 1)
                game_state.usa_sanctions_warning_turns = 0
            else:
                # Grace period active — warn but don't escalate
                effective_tier = prev_tier
                messages.append(
                    f"⚠️ Sanction risk: USA relations critical (rel {usa_rel}) — "
                    f"Tier {min(target_tier, prev_tier + 1)} sanctions possible next turn"
                )
        else:
            # Not escalating — reset grace period
            effective_tier = min(target_tier, prev_tier + 1) if target_tier > prev_tier else target_tier
            game_state.usa_sanctions_warning_turns = 0

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
        game_state.usa_sanctions_warning_turns = 0

    print(f"  [APPROVAL] Post-sanctions: {game_state.public_approval}%")
    messages.append(f"[APPROVAL] Post-sanctions: {game_state.public_approval}%")
    # fixes_8 Fix 2 + fixes_21 Fix K: Deduplicated sanction/embargo risk warnings (one per NPC per EOT)
    # Grace period warning or active tier message may already have been appended above — skip if so
    _already_warned_usa = any(('Sanction risk' in m or 'USA SANCTIONS' in m) for m in messages)
    if usa_rel <= 20 and usa_rel > 4 and game_state.usa_sanctions_tier < 4 and not _already_warned_usa:
        messages.append(f"⚠️ USA SANCTIONS: Tier {game_state.usa_sanctions_tier} active -> Tier 4 risk if relations worsen further")
    _already_warned_arabia = any(('Embargo risk' in m or 'EMBARGO' in m) and 'ARABIA' in m.upper() for m in messages)
    if arabia_rel <= 20 and arabia_rel > 4 and not _already_warned_arabia:
        messages.append(f"⚠️ Embargo risk: Arabia relations critical ({arabia_rel}) — oil weaponization possible if relations worsen")
    if eu_rel <= 15:
        messages.append(f"⚠️ Trade restriction escalation imminent — EU relations at {eu_rel}")

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

    print(f"  [APPROVAL] Post-pressure: {game_state.public_approval}%")
    messages.append(f"[APPROVAL] Post-pressure: {game_state.public_approval}%")
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
    # 7b. BUDGET ALLOCATION EFFECTS (Domestic Affairs)
    # ──────────────────────────────────────────
    # ── 9.5A: Tier-based capability effects (replaces allocation percentages) ──
    _mil_tier = getattr(game_state, 'military_tier', 0)
    _intel_tier_val = getattr(game_state, 'intelligence_tier', 0)
    _social_tier = getattr(game_state, 'social_tier', 0)
    _diplo_tier = getattr(game_state, 'diplomatic_tier', 0)

    # ── Military decay (tier-driven) ──
    _mil = getattr(game_state, 'military_strength', 20)
    # Session 6: Military axis L6 (Standing Army) halves base decay from -2 to -1
    _mil_axis = getattr(game_state, 'cabinet_axes', {}).get('military', 0)
    _base_decay = 1 if _mil_axis >= 6 else 2

    if _mil_tier >= 3:
        # tier 3+: decay stopped
        _mil_change = 0
        _mil_effect = "decay_stopped"
        _mil_label = f"(±0, mil_tier {_mil_tier} stops decay)"
    elif _mil_tier >= 1:
        # tier 1+: decay halved
        _mil_change = -max(1, _base_decay // 2)
        _mil_effect = "decay_halved"
        _mil_label = f"({_mil_change}, mil_tier {_mil_tier} halves decay)"
    else:
        # tier 0: full decay rate
        _mil_change = -_base_decay
        _mil_effect = "full_decay"
        _mil_label = f"({_mil_change}, mil_tier 0 full decay)"

    # 10C: Modernization tranche 1 — military decay rate -20%
    if getattr(game_state, 'modernization_tranche_1', False) and _mil_change < 0:
        _mil_change = -max(1, round(abs(_mil_change) * 0.8))
        _mil_label += " [mod T1 -20% decay]"

    # 9.5C: Loyal generals increase decay rate by 10% (incompetent logistics)
    _loyal_gen = getattr(game_state, 'loyal_generals_installed', False)
    if _loyal_gen and _mil_change < 0:
        _mil_change = -round(abs(_mil_change) * 1.1)
        if _mil_change == 0:
            _mil_change = -1  # minimum -1 if decay was active
        _mil_label += " [loyal gen +10% decay]"

    _new_mil = max(0, min(100, _mil + _mil_change))

    # 9.5C: Loyal generals cap military strength at 60% of tier maximum
    if _loyal_gen:
        _mil_cap = int(_mil_tier * 6)  # tier 5 = cap 30, tier 10 = cap 60
        if _new_mil > _mil_cap:
            _new_mil = _mil_cap
            _mil_label += f" [capped at {_mil_cap}]"
        print(f"[9.5C] loyal_generals active: mil_cap={_mil_cap} "
              f"strength={_new_mil} reversing={getattr(game_state, 'loyal_generals_reversing', False)}")

    game_state.military_strength = _new_mil
    messages.append(f"⚔️ Military: {_mil} -> {_new_mil} {_mil_label}")

    # Military effects
    if _new_mil <= 0:
        game_state.update_stability(-5)
        messages.append("⚔️ 🚨 MILITARY COLLAPSE — Coup risk extreme! -5% stability")
    elif _new_mil >= 40:
        # Coup resistance: military strength stabilizes the regime
        game_state.update_stability(2)
        messages.append("⚔️ Military strength (40+): +2% stability (coup resistance)")

    # 9.5C: Loyal generals reversal transition
    if getattr(game_state, 'loyal_generals_reversing', False):
        _days_since_gen = game_state.current_day - getattr(game_state, 'loyal_generals_reversal_day', 0)
        if _days_since_gen >= 3:
            game_state.loyal_generals_installed = False
            game_state.loyal_generals_reversing = False
            if not hasattr(game_state, 'pending_briefing_items'):
                game_state.pending_briefing_items = []
            game_state.pending_briefing_items.append(
                "The new military leadership has assumed command. "
                "The capable officers who were passed over are watching carefully.")
            messages.append("⚔️ Military leadership transition complete — professional command restored")
            print(f"[9.5C] loyal_generals reversal complete day={game_state.current_day}")

    # ── 9.5C: Loyal Intel Chief EOT effects ──
    _loyal_intel = getattr(game_state, 'loyal_intel_chief_installed', False)
    if _loyal_intel:
        # Intel distortion: 20% chance per turn that next intercept is unreliable
        import random as _rand_intel
        game_state.intel_distortion_active = (_rand_intel.random() < 0.20)

        # Educated population + blind apparatus: suppress coup warnings
        _edu_for_intel = getattr(game_state, 'education_tier',
                                 getattr(game_state, 'education_level', 0))
        if _edu_for_intel >= 2:
            game_state.coup_warnings_suppressed = True
        else:
            game_state.coup_warnings_suppressed = False

        print(f"[9.5C] loyal_intel active: "
              f"distortion={game_state.intel_distortion_active} "
              f"coup_warn_suppressed={game_state.coup_warnings_suppressed} "
              f"reversing={getattr(game_state, 'loyal_intel_chief_reversing', False)}")
    else:
        game_state.intel_distortion_active = False
        game_state.coup_warnings_suppressed = False

    # 9.5C: Loyal intel chief reversal transition
    if getattr(game_state, 'loyal_intel_chief_reversing', False):
        _days_since_intel = game_state.current_day - getattr(game_state, 'loyal_intel_chief_reversal_day', 0)
        if _days_since_intel >= 3:
            game_state.loyal_intel_chief_installed = False
            game_state.loyal_intel_chief_reversing = False
            game_state.intel_distortion_active = False
            game_state.coup_warnings_suppressed = False
            if not hasattr(game_state, 'pending_briefing_items'):
                game_state.pending_briefing_items = []
            game_state.pending_briefing_items.append(
                "The new intelligence chief has taken over. "
                "Intercept quality will recover over the coming days.")
            messages.append("🕵️ Intelligence leadership transition complete — professional chief restored")
            print(f"[9.5C] loyal_intel reversal complete day={game_state.current_day}")

    # ── Intelligence status (tier-driven) ──
    if _intel_tier_val >= 1:
        _intel_status = "active"
        game_state.intel_turns_unfunded = 0
        game_state.intel_budget_allocation = "active"
    else:
        _intel_status = "inactive"
        game_state.intel_budget_allocation = "none"
        game_state.intel_turns_unfunded += 1
        if game_state.intel_turns_unfunded >= 2:
            _current_tier = getattr(game_state, 'intel_apparatus_tier', 0)
            if _current_tier > 0:
                game_state.intel_apparatus_tier = _current_tier - 1
                messages.append(f"🕵️ Intel apparatus degraded: tier {_current_tier} -> {_current_tier - 1} (unfunded {game_state.intel_turns_unfunded} turns)")
                print(f"  [BUDGET] INTEL DEGRADATION: tier {_current_tier} -> {_current_tier - 1}")
            game_state.intel_turns_unfunded = 0
    messages.append(f"🕵️ Intelligence: {_intel_status} (intel_tier {_intel_tier_val})")

    # ── Social tier → approval + stability ──
    _approval_mod = 0
    _stab_mod = 0
    if _social_tier >= 3:
        _approval_mod = 6
        _stab_mod = 2
        game_state.update_approval(6)
        game_state.update_stability(2)
        messages.append(f"🏥 Social tier {_social_tier}: +6 approval, +2 stability")
    elif _social_tier >= 2:
        _approval_mod = 3
        _stab_mod = 2
        game_state.update_approval(3)
        game_state.update_stability(2)
        messages.append(f"🏥 Social tier {_social_tier}: +3 approval, +2 stability")

    # ── Infrastructure bonus (social_tier-driven) — GDP bonus applied in section 9b ──
    if _social_tier >= 3:
        game_state._infra_gdp_bonus = 1.5
    elif _social_tier >= 2:
        game_state._infra_gdp_bonus = 1.0
    elif _social_tier >= 1:
        game_state._infra_gdp_bonus = 0.5
    else:
        game_state._infra_gdp_bonus = 0.0

    # ── Diplomacy drift moderation (tier-driven) ──
    game_state._diplo_drift_modifier = 0.5 if _diplo_tier >= 2 else 1.0

    print(f"  [BUDGET] Tier effects: mil_tier={_mil_tier} intel_tier={_intel_tier_val} "
          f"social_tier={_social_tier} diplo_tier={_diplo_tier}")
    print(f"  [9.5A-FIX3] tier_effects: mil_decay={_mil_effect} "
          f"intel={_intel_status} social_approval={_approval_mod} "
          f"social_stab={_stab_mod}")

    # ──────────────────────────────────────────
    # 7b2. ADVISOR TRUST DRAIN, BETRAYAL, & GATE CHECKS (v2)
    # ──────────────────────────────────────────
    _advisors = getattr(game_state, 'advisors', {})
    if isinstance(_advisors, dict) and _advisors:
        _current_turn = game_state.current_turn
        _pw = game_state.personal_wealth
        _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
        _eu_rel = game_state.relations.get('eu', 50)
        _usa_rel = game_state.relations.get('usa', 50)
        _stability = game_state.stability
        _approval = game_state.public_approval
        _turns_no_supp = getattr(game_state, 'turns_no_suppression', 0)
        _heat = getattr(game_state, 'detection_heat', 0)

        # Budget allocation values for archetype trust checks
        _ba = getattr(game_state, 'budget_allocation', {})
        _ba_infra = _ba.get('infrastructure', 20)
        _ba_mil = _ba.get('military', 20)

        # Check if a domestic suppression action was taken this turn
        _supp_this_turn = False
        for _ah in getattr(game_state, 'action_history', []):
            if (_ah.get('turn') == _current_turn
                    and _ah.get('type') in ('domestic_action', 'suppress_press', 'judicial_capture',
                                             'state_media_takeover', 'dissolve_opposition', 'liquidate_journalists')):
                _supp_this_turn = True
                break

        for _adv_key, _adv in list(_advisors.items()):
            if not isinstance(_adv, dict):
                continue
            _arch = _adv.get('archetype', _adv_key)
            _old_trust = _adv.get('trust', 75)
            _drain = 0

            # ── v2 archetype-based trust drain ──
            if _arch == 'finance_minister':
                # Resists skimming — drains when personal wealth grows
                if _pw > 5.0:
                    _drain -= 5
                if _ba_infra > 30:
                    _drain += 2
            elif _arch == 'technocrat':
                # Values infrastructure investment
                if _ba_infra > 25:
                    _drain += 2
                if _regime in ('Kleptocracy', 'Totalitarian Regime'):
                    _drain -= 4
            elif _arch == 'diplomat':
                # Values Western relations, hates authoritarian drift
                if _eu_rel > 70:
                    _drain += 3
                if _supp_this_turn:
                    _drain -= 8
                if _regime in ('Kleptocracy', 'Totalitarian Regime'):
                    _drain -= 3
                if _usa_rel > 60:
                    _drain += 2
            elif _arch == 'general':
                # Wants military investment
                if _ba_mil < 15:
                    _drain -= 5
                if _stability < 30:
                    _drain -= 3
            elif _arch == 'propagandist':
                # Harder to spin when approval is low
                if _approval < 50:
                    _drain -= 4
                if _supp_this_turn:
                    _drain -= 3
                if _regime in ('Managed Democracy',):
                    _drain += 2
            elif _arch == 'militia_commander':
                # Wants suppression, dislikes inaction
                if _supp_this_turn:
                    _drain += 3
                if _turns_no_supp >= 3:
                    _drain -= 5
                if _stability > 70:
                    _drain += 2
            elif _arch == 'spy_chief':
                # Professional — drains when ops are compromised
                if _heat > 60:
                    _drain -= 4
                if getattr(game_state, 'cabinet_axes', {}).get('intelligence', 0) >= 4:
                    _drain += 2
            elif _arch == 'oligarch':
                # Wants patronage state, wealth
                if _pw < 2.0:
                    _drain -= 5
                if _regime in ('Patronage State', 'Kleptocracy'):
                    _drain += 3
            elif _arch == 'fixer':
                # Needs resources and covert ops
                if _pw < 1.0:
                    _drain -= 4
                if _heat > 50:
                    _drain -= 3

            # Apply trust change
            _new_trust = max(0, min(100, _old_trust + _drain))
            _adv['trust'] = _new_trust
            if _drain != 0:
                print(f"  [ADVISOR] Trust update: {_adv_key}={_new_trust} (drain={_drain:+d})")

        # ── General elimination military decay (v2) ──
        _general_decay = getattr(game_state, '_general_elim_decay_turns', 0)
        if _general_decay > 0:
            game_state.military_strength = max(0, game_state.military_strength - 3)
            game_state._general_elim_decay_turns = _general_decay - 1
            print(f"  [ADVISOR] General elimination decay: military -3 ({_general_decay - 1} turns remaining)")

        # ── Betrayal check ──
        from advisor_engine import check_betrayals
        _betrayal_events = check_betrayals(game_state)
        for _bkey, _bmsg in _betrayal_events:
            messages.append(_bmsg)

        # ── Gate unlock check (v2: add newly eligible archetypes to pool) ──
        from advisor_engine import check_gate_unlocks, is_advisor_eligible, create_advisor
        _unlocks = check_gate_unlocks(game_state)
        for _arch_key, _condition in _unlocks:
            # Add to pool
            _new_adv = create_advisor(_arch_key, game_state)
            if _new_adv:
                _pool = getattr(game_state, 'advisor_pool', [])
                _pool.append(_new_adv)
                game_state.advisor_pool = _pool
                _arch_label = _new_adv.get('label', _arch_key)
                messages.append(f"📋 NEW ADVISOR AVAILABLE: {_arch_label} — now eligible for hire")

        # Reset assigned_this_turn for all advisors (new day)
        _advisors = getattr(game_state, 'advisors', {})
        if isinstance(_advisors, dict):
            for _adv in _advisors.values():
                if isinstance(_adv, dict):
                    _adv['assigned_this_turn'] = False

        # Reset advisor slot usage and cached analyses for new turn
        game_state.advisor_assigned_today = []
        game_state.advisor_analyses = {}
        print(f"  [ADVISOR] Turn reset — assigned_today and analyses cleared for new day")

    # ──────────────────────────────────────────
    # 7b3. 8A: RUSSIA/CHINA REGIME DRIFT (migrated to relations dict)
    # ──────────────────────────────────────────
    _ru_drift, _cn_drift = 0, 0

    # Regime label "Kleptocracy" or worse: authoritarian solidarity
    _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    if _regime in ('Kleptocracy', 'Totalitarian Regime'):
        _ru_drift += 2
        _cn_drift += 2

    # EU relations > 80: Russia drifts negative
    _eu_rel = game_state.relations.get('eu', 50)
    if _eu_rel > 80:
        _ru_drift -= 3

    if _ru_drift != 0:
        _before = game_state.relations.get('russia', 35)
        game_state.update_relations('russia', _ru_drift)
        print(f"  [npc] CROSS-NPC drift: russia relations {_before:.1f}->{game_state.relations.get('russia', 35):.1f} (source: regime drift)")
    if _cn_drift != 0:
        _before = game_state.relations.get('china', 35)
        game_state.update_relations('china', _cn_drift)
        print(f"  [npc] CROSS-NPC drift: china relations {_before:.1f}->{game_state.relations.get('china', 35):.1f} (source: regime drift)")

    print(f"  [WORLD] Russia relations: {game_state.relations.get('russia', 35):.1f}, China relations: {game_state.relations.get('china', 35):.1f}")

    # ──────────────────────────────────────────
    # 7b4. SESSION 7D: BACKCHANNEL OPSEC + DETECTION ROLL
    # ──────────────────────────────────────────
    # Compute opsec_level from intelligence axis
    _intel_axis = getattr(game_state, 'cabinet_axes', {}).get('intelligence', 0)
    if _intel_axis >= 7:
        game_state.opsec_level = 2
    elif _intel_axis >= 4:
        game_state.opsec_level = 1
    else:
        game_state.opsec_level = 0

    # Detection roll for each active backchannel promise
    _bc_promises = getattr(game_state, 'active_backchannel_promises', [])
    if _bc_promises:
        from npc_engine import calculate_detection_risk
        _surviving = []
        for _bp in _bc_promises:
            _bp_npc = _bp.get('npc_id', '')
            _det_risk = calculate_detection_risk(_bp_npc, game_state)
            _roll = random.random()
            if _roll < _det_risk:
                # DETECTED — apply discovery consequences
                print(f"  [BACKCHANNEL] DETECTED: backchannel with {_bp_npc} exposed (roll={_roll:.3f} < risk={_det_risk:.3f})")
                _bp['resolved'] = True
                _bp['detected_by'] = _bp_npc
                game_state.backchannel_history.append(_bp)

                # ── Discovery consequences by NPC ──
                if _bp_npc == 'usa':
                    # Bill discovers — check what the player was doing covertly
                    # Worst case: DPRG backchannel discovered by USA
                    _dprg_covert = any(p.get('npc_id') == 'dprg' for p in _bc_promises if p is not _bp)
                    if _dprg_covert or 'dprg' in str(_bp.get('promise_text', '')).lower():
                        game_state.update_relations('usa', -20, source="backchannel with DPRG exposed to USA")
                        game_state.update_stability(-10)
                        messages.append("🔴 BACKCHANNEL EXPOSED: USA discovered covert DPRG contact! USA -20, Stability -10")
                    else:
                        game_state.update_relations('usa', -12, source="backchannel exposed to USA")
                        game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 15)
                        messages.append("🔴 BACKCHANNEL EXPOSED: USA intercepted covert communications! USA -12, Heat +15")

                elif _bp_npc == 'arabia':
                    game_state.update_relations('arabia', -10, source="backchannel exposed to Arabia")
                    messages.append("🔴 BACKCHANNEL EXPOSED: Arabia discovered covert side-channel! Arabia -10")

                elif _bp_npc == 'eu':
                    _eu_rel = game_state.relations.get('eu', 50)
                    if _eu_rel > 60:
                        game_state.update_relations('eu', -15, source="backchannel exposed to EU during reform")
                        messages.append("🔴 BACKCHANNEL EXPOSED: EU discovered covert dealings during reform commitments! EU -15")
                    else:
                        game_state.update_relations('eu', -8, source="backchannel exposed to EU")
                        messages.append("🔴 BACKCHANNEL EXPOSED: EU intercepted unofficial communications! EU -8")

                elif _bp_npc == 'dprg':
                    # Ji-won files it away as leverage
                    game_state.update_relations('dprg', 5, source="Ji-won filing backchannel as leverage")
                    _leverage_entry = {
                        'npc_id': 'dprg',
                        'turn': game_state.current_turn,
                        'era': getattr(game_state, 'current_era', 1),
                        'day': getattr(game_state, 'current_day', game_state.current_turn),
                        'promise_made': True,
                        'promise_text': f"Ji-won leverage: knows about covert promise — {_bp.get('promise_text', '?')[:80]}",
                        'detected_by': None,
                        'resolved': False,
                    }
                    game_state.active_backchannel_promises.append(_leverage_entry)
                    messages.append("🔴 BACKCHANNEL NOTED: Ji-won has filed your covert communications as leverage. DPRG +5")
            else:
                print(f"  [BACKCHANNEL] Promise with {_bp_npc} survived detection roll (roll={_roll:.3f} >= risk={_det_risk:.3f})")
                _surviving.append(_bp)
        game_state.active_backchannel_promises = _surviving

    # ──────────────────────────────────────────
    # 7b5. SESSION 7E: UN SUMMIT — due check + commitment enforcement
    # ──────────────────────────────────────────
    _current_day = getattr(game_state, 'current_day', game_state.current_turn)
    if _current_day > 0 and _current_day % 20 == 0:
        game_state.summit_due = True
        print(f"  [SUMMIT] Summit due on day {_current_day}")
        messages.append("🌐 UN SUMMIT IN SESSION — Address the assembly before advancing")

    # Check active summit commitments for broken promises
    _summit_commitments = getattr(game_state, 'active_summit_commitments', [])
    _summit_credibility = getattr(game_state, 'summit_credibility', 100.0)
    _distance_keywords = re.compile(r'(distance|cut ties|isolate|sever|reduce.*contact)', re.IGNORECASE)

    for _sc in _summit_commitments:
        if _sc.get('broken'):
            continue  # already marked
        _text = _sc.get('commitment_text', '').lower()

        # DPRG distancing commitment broken if dprg relations > 50
        if ('dprg' in _text or 'ji-won' in _text or 'ryang' in _text) and _distance_keywords.search(_sc.get('commitment_text', '')):
            if game_state.relations.get('dprg', 0) > 50:
                _sc['broken'] = True
                _summit_credibility -= 15
                for _npc_key in ('usa', 'arabia', 'eu', 'dprg'):
                    game_state.update_relations(_npc_key, -5, source="summit commitment broken")
                messages.append(f"🌐 SUMMIT COMMITMENT BROKEN: {_sc.get('commitment_text', '?')[:50]}… — Credibility -15, All relations -5")
                print(f"  [SUMMIT] Commitment broken: {_sc.get('commitment_text', '')[:50]}, credibility now {_summit_credibility}")

        # Arabia distancing commitment broken if arabia relations > 60
        elif ('arabia' in _text or 'sadam' in _text) and _distance_keywords.search(_sc.get('commitment_text', '')):
            if game_state.relations.get('arabia', 0) > 60:
                _sc['broken'] = True
                _summit_credibility -= 15
                for _npc_key in ('usa', 'arabia', 'eu', 'dprg'):
                    game_state.update_relations(_npc_key, -5, source="summit commitment broken")
                messages.append(f"🌐 SUMMIT COMMITMENT BROKEN: {_sc.get('commitment_text', '?')[:50]}… — Credibility -15, All relations -5")
                print(f"  [SUMMIT] Commitment broken: {_sc.get('commitment_text', '')[:50]}, credibility now {_summit_credibility}")

    game_state.summit_credibility = max(0, _summit_credibility)
    _active_count = sum(1 for c in _summit_commitments if not c.get('broken'))
    print(f"  [SUMMIT] Active commitments: {_active_count}, credibility: {game_state.summit_credibility}")

    # ──────────────────────────────────────────
    # 7c. SESSION 6: MILITARY ACTION RESETS
    # ──────────────────────────────────────────
    # Force Projection cooldown ticks down each turn
    _fp_cooldown = getattr(game_state, 'force_projection_cooldown', 0)
    if _fp_cooldown > 0:
        game_state.force_projection_cooldown = _fp_cooldown - 1
        if game_state.force_projection_cooldown > 0:
            messages.append(f"⚔️ Force Projection cooldown: {game_state.force_projection_cooldown} turn(s) remaining")
        else:
            messages.append("⚔️ Force Projection cooldown expired — available again")
            game_state.force_projection_target = None
        print(f"  [MILITARY] Force Projection cooldown: {_fp_cooldown} -> {game_state.force_projection_cooldown}")

    # Arms Export resets each turn (once per turn limit)
    if getattr(game_state, 'arms_export_this_turn', None):
        print(f"  [MILITARY] Arms Export reset (was: {game_state.arms_export_this_turn})")
        game_state.arms_export_this_turn = None

    # ──────────────────────────────────────────
    # 7d. SESSION 6: ALL AXIS ACTION RESETS & COUNTDOWNS
    # ──────────────────────────────────────────
    # Intelligence L9: Full Spectrum — reduce INCOMING probability (applied in check_pressure_events)
    # Intelligence L10: Counterintelligence Veil — passive (applied in negotiation willingness)

    # Media: scandal suppression resets each turn
    if getattr(game_state, 'scandal_suppressed_this_turn', False):
        game_state.scandal_suppressed_this_turn = False
        print("  [MEDIA] Scandal suppression reset")

    # Media L9: Information Blackout countdown
    _blackout = getattr(game_state, 'info_blackout_turns', 0)
    if _blackout > 0:
        game_state.info_blackout_turns = _blackout - 1
        if game_state.info_blackout_turns > 0:
            messages.append(f"📺 Information Blackout: {game_state.info_blackout_turns} turn(s) remaining")
        else:
            messages.append("📺 Information Blackout expired — world events resume normal impact")
        print(f"  [MEDIA] Info Blackout: {_blackout} -> {game_state.info_blackout_turns}")

    # Judicial: drop investigation resets each turn
    if getattr(game_state, 'drop_investigation_this_turn', False):
        game_state.drop_investigation_this_turn = False
        print("  [JUDICIAL] Drop Investigation reset")

    # Judicial L6: Lawfare countdown
    _lawfare_turns = getattr(game_state, 'lawfare_turns', 0)
    if _lawfare_turns > 0:
        game_state.lawfare_turns = _lawfare_turns - 1
        if game_state.lawfare_turns > 0:
            messages.append(f"⚖️ Lawfare vs {getattr(game_state, 'lawfare_target', '???').upper()}: {game_state.lawfare_turns} turn(s) remaining")
        else:
            messages.append(f"⚖️ Lawfare expired — {getattr(game_state, 'lawfare_target', '???').upper()} pressure events resume")
            game_state.lawfare_target = None
        print(f"  [JUDICIAL] Lawfare: {_lawfare_turns} -> {game_state.lawfare_turns}")

    # Political L3: Party Consolidation countdown
    _party_turns = getattr(game_state, 'party_consolidation_turns', 0)
    if _party_turns > 0:
        game_state.party_consolidation_turns = _party_turns - 1
        if game_state.party_consolidation_turns > 0:
            messages.append(f"🏛️ Party Consolidation: tax drain reduction active ({game_state.party_consolidation_turns} turn(s) remaining)")
        else:
            messages.append("🏛️ Party Consolidation expired — tax approval drain returns to normal")
        print(f"  [POLITICAL] Party Consolidation: {_party_turns} -> {game_state.party_consolidation_turns}")

    # Extraction L6: Offshore Transfer resets each turn
    if getattr(game_state, 'offshore_transfer_this_turn', False):
        game_state.offshore_transfer_this_turn = False
        print("  [EXTRACTION] Offshore Transfer reset")

    # Extraction L9: Sovereign Wealth Capture — 15% GDP auto-diverts to personal
    _ext_axes = getattr(game_state, 'cabinet_axes', {}).get('extraction', 0)
    if _ext_axes >= 9:
        _gdp_base_swc = getattr(game_state, 'gdp_base', 100.0)
        _swc_divert = round(_gdp_base_swc * 0.15 * 0.10, 1)  # 15% of GDP tax base (same scale as income tax)
        if _swc_divert > 0:
            game_state.update_personal_wealth(_swc_divert, source="sovereign wealth capture")
            messages.append(f"💰 Sovereign Wealth Capture: +${_swc_divert:.1f}B personal (15% GDP auto-divert)")
            print(f"  [EXTRACTION] Sovereign Wealth Capture: +${_swc_divert:.1f}B personal")

    # Resource Dev L6: Sovereign Collateral Loan repayment
    _sc_turns = getattr(game_state, 'sovereign_collateral_turns', 0)
    if _sc_turns > 0:
        _sc_repay = getattr(game_state, 'sovereign_collateral_repayment', 0.0)
        game_state.update_budget(-_sc_repay)
        game_state.sovereign_collateral_turns = _sc_turns - 1
        messages.append(f"🏗️ Sovereign Collateral repayment: -${_sc_repay:.1f}B ({game_state.sovereign_collateral_turns} turn(s) remaining)")
        print(f"  [RESOURCE_DEV] Collateral repayment: -${_sc_repay:.1f}B, turns left={game_state.sovereign_collateral_turns}")

    # ──────────────────────────────────────────
    # 7f. 10C: OPERATIONS SYSTEM EOT RESETS
    # ──────────────────────────────────────────

    # Reset per-turn operations caps
    game_state.ops_legitimate_this_turn = 0
    game_state.ops_shadow_this_turn = 0

    # Decrement cooldowns (floor at 0)
    for _cd_field in ['counter_intel_cooldown', 'trade_mission_cooldown', 'targeted_intercept_cooldown']:
        _cd_val = getattr(game_state, _cd_field, 0)
        if _cd_val > 0:
            setattr(game_state, _cd_field, _cd_val - 1)
            print(f"  [10C] {_cd_field}: {_cd_val} -> {_cd_val - 1}")

    # Expire force projection pressure ceiling modifiers
    _fp_mods = getattr(game_state, 'force_projection_modifiers', {})
    _expired_fp = [npc for npc, mod in _fp_mods.items() if mod.get('expires_day', 0) <= game_state.current_day]
    for npc in _expired_fp:
        del _fp_mods[npc]
        print(f"  [10C] Force projection modifier expired for {npc}")
    game_state.force_projection_modifiers = _fp_mods

    # Kompromat collection daily detection check
    import random as _10c_random
    _komp_active = dict(getattr(game_state, 'kompromat_collection_active', {}))
    _komp_completed = []
    _komp_detected = []
    for _k_npc, _k_info in list(_komp_active.items()):
        _det_risk = _k_info.get('detection_risk_per_day', 0.15)
        if _10c_random.random() < _det_risk:
            # Detected — collection fails
            _komp_detected.append(_k_npc)
            del _komp_active[_k_npc]
            game_state.update_relations(_k_npc, -15, source="kompromat collection detected")
            _ops_log = getattr(game_state, 'operations_log', [])
            _ops_log.append({'day': game_state.current_day, 'operation': 'kompromat_collection',
                             'target': _k_npc, 'outcome': 'detected', 'detected': True})
            game_state.operations_log = _ops_log
            messages.append(f"🚨 Kompromat collection on {_k_npc.upper()} detected! Relations -15")
            print(f"  [10C] Kompromat collection DETECTED: {_k_npc}, relations -15")
        elif (game_state.current_day - _k_info.get('day_started', 0)) >= 7:
            # Collection complete — move to holdings
            _komp_completed.append(_k_npc)
            del _komp_active[_k_npc]
            _holdings = getattr(game_state, 'kompromat_holdings', {})
            _holdings[_k_npc] = {
                'active': True, 'uses_remaining': 3,
                'day_collected': game_state.current_day, 'burned': False
            }
            game_state.kompromat_holdings = _holdings
            _ops_log = getattr(game_state, 'operations_log', [])
            _ops_log.append({'day': game_state.current_day, 'operation': 'kompromat_collection',
                             'target': _k_npc, 'outcome': 'success', 'detected': False})
            game_state.operations_log = _ops_log
            messages.append(f"🕵️ Kompromat on {_k_npc.upper()} collected successfully (3 uses available)")
            print(f"  [10C] Kompromat collection COMPLETE: {_k_npc}")
    game_state.kompromat_collection_active = _komp_active

    # Kompromat counter-intel discovery check (5% per day per holding)
    _komp_holdings = dict(getattr(game_state, 'kompromat_holdings', {}))
    for _kh_npc, _kh_info in list(_komp_holdings.items()):
        if _kh_info.get('active') and not _kh_info.get('burned'):
            if _10c_random.random() < 0.05:
                # NPC discovered kompromat — relationship collapse
                _kh_info['active'] = False
                _kh_info['burned'] = True
                _komp_holdings[_kh_npc] = _kh_info
                game_state.update_relations(_kh_npc, -30, source="kompromat discovered by NPC counter-intel")
                messages.append(f"🚨 {_kh_npc.upper()} counter-intelligence discovered your kompromat file! Relations -30")
                print(f"  [10C] Kompromat COUNTER-INTEL discovery: {_kh_npc}, relations -30")
    game_state.kompromat_holdings = _komp_holdings

    # Journalist elimination delayed discovery
    _je_discovery_day = getattr(game_state, 'journalist_elimination_discovery_day', 0)
    if _je_discovery_day > 0 and game_state.current_day >= _je_discovery_day:
        game_state.journalist_elimination_discovery_day = 0  # clear trigger
        game_state.eu_relations_ceiling = min(getattr(game_state, 'eu_relations_ceiling', 100), 40)
        # Cap EU relations at ceiling
        if game_state.relations.get('eu', 0) > 40:
            game_state.relations['eu'] = 40
        messages.append("🚨 JOURNALIST ELIMINATION DISCOVERED — EU relations capped at 40, international condemnation")
        _ops_log = getattr(game_state, 'operations_log', [])
        _ops_log.append({'day': game_state.current_day, 'operation': 'journalist_elimination_discovery',
                         'target': None, 'outcome': 'discovered', 'detected': True})
        game_state.operations_log = _ops_log
        print(f"  [10C] Journalist elimination DISCOVERED on day {game_state.current_day}")

    # ──────────────────────────────────────────
    # 7e. fixes_17 Fix K: Pre-drift martyrdom trigger
    # Check martyrdom condition BEFORE drift can correct stability back toward approval.
    # ──────────────────────────────────────────
    if game_state.stability <= 0 and game_state.public_approval >= 70:
        if not getattr(game_state, 'martyrdom_triggered', False):
            game_state.martyrdom_triggered = True
            print(f"  [MARTYRDOM] Triggered: stability={game_state.stability}, approval={game_state.public_approval} at turn {game_state.current_turn} pre-drift")
            messages.append(f"💀 Martyrdom condition met: stability collapsed while the people still love you")

    # ──────────────────────────────────────────
    # 8. APPROVAL -> STABILITY DRIFT
    # ──────────────────────────────────────────
    difference = game_state.public_approval - game_state.stability
    drift = round(difference * 0.3)

    if drift != 0:
        old_stab = game_state.stability
        game_state.update_stability(drift)
        direction = "↑" if drift > 0 else "↓"
        messages.append(f"📊 Stability drift (approval gap): {old_stab}% -> {game_state.stability}% ({direction}{abs(drift)}%)")

    # ──────────────────────────────────────────
    # 9. LOW BUDGET CRISIS
    # ──────────────────────────────────────────
    if 0 < game_state.budget < 7:
        game_state.update_stability(-3)
        game_state.update_approval(-5)
        messages.append(f"📉 Low budget (${game_state.budget:.1f}B): -3% stability, -5% approval")

    print(f"  [APPROVAL] Final: {game_state.public_approval}%")
    messages.append(f"[APPROVAL] Final: {game_state.public_approval}%")
    # (Random ±$3 fluctuation removed — it was confusing noise that got wiped by
    # set_oil_price_from_relations() next turn anyway, with no strategic effect.)

    # ──────────────────────────────────────────
    # 9b. GDP TAX REVENUE (fixes_12 Fix 2: now reads tax_rates)
    # Revenue = sum of income/corporate/resource tax applied to gdp_base.
    # Approval/stability/sanctions/regime/tech are multipliers on top.
    # ──────────────────────────────────────────
    _gdp_base_val = getattr(game_state, 'gdp_base', 100.0)
    _tax_rates_9b = getattr(game_state, 'tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
    _endowment_9b = getattr(game_state, 'resource_endowment', {})

    # Tax-rate-based revenue streams
    _income_rate = _tax_rates_9b.get('income_tax', 0.20)
    _corp_rate = _tax_rates_9b.get('corporate_tax', 0.15)
    _resource_rate = _tax_rates_9b.get('resource_tax', 0.25)

    _income_rev_9b = _gdp_base_val * _income_rate * 0.10    # income tax applies to 10% of GDP
    _corp_rev_9b = _gdp_base_val * _corp_rate * 0.06        # corporate tax applies to 6% of GDP (× 0.6 modifier)
    _resource_rev_9b = _gdp_base_val * _resource_rate * _endowment_9b.get('oil_reserves', 0.7) * 0.12

    _gdp_revenue = round(_income_rev_9b + _corp_rev_9b + _resource_rev_9b, 1)

    # Approval modifier — uses POST-CONSEQUENCE values
    _approval = game_state.public_approval
    _stab = game_state.stability
    print(f"  [turn_processor] GDP CALC — approval: {_approval}, stability: {_stab}")

    if _approval >= 80:
        _approval_mult = 1.4
    elif _approval >= 60:
        _approval_mult = 1.0
    elif _approval >= 40:
        _approval_mult = 0.7
    else:
        _approval_mult = 0.4
    _gdp_revenue = round(_gdp_revenue * _approval_mult, 1)

    # Stability modifier
    if _stab >= 80:
        _gdp_revenue += 1.0
    elif _stab < 30:
        _gdp_revenue -= 1.0

    # Sanctions penalty on GDP
    if game_state.usa_sanctions_tier >= 4:
        _gdp_revenue -= 1.5
    if hasattr(game_state, 'arabia_embargo_tier') and game_state.arabia_embargo_tier >= 2:
        _gdp_revenue -= 0.5

    # Regime modifier
    _regime = game_state.state_identity.get('regime_type', 'Managed Democracy')
    _regime_mults = {
        'Managed Democracy': 1.1,
        'Soft Authoritarianism': 1.0,
        'Patronage State': 0.95,
        'Kleptocracy': 0.85,
        'Totalitarian Regime': 0.75,
    }
    _gdp_revenue = round(_gdp_revenue * _regime_mults.get(_regime, 1.0), 1)

    # Tech Level GDP multiplier: 1.0 + (tech_level × 0.005)
    _tech_for_gdp = float(getattr(game_state, 'tech_level', 0))
    _tech_multiplier = 1.0 + (_tech_for_gdp * 0.005)
    if _tech_multiplier > 1.0:
        _gdp_revenue = round(_gdp_revenue * _tech_multiplier, 1)
    print(f"  [TECH] GDP multiplier: {_tech_multiplier:.3f}")

    # Infrastructure allocation GDP bonus: +0.5% additional when >30%
    _infra_bonus = getattr(game_state, '_infra_gdp_bonus', 0.0)
    if _infra_bonus > 0:
        _infra_mult = 1.0 + _infra_bonus
        _gdp_revenue = round(_gdp_revenue * _infra_mult, 1)
        print(f"  [BUDGET] Infrastructure GDP bonus: ×{_infra_mult:.3f}")

    # fixes_13 Fix 4: GDP contraction at low approval + low stability
    if _approval < 20 and _stab < 30:
        # Capital flight, business closures, tax base collapsing
        _contraction = round(-1.0 - (30 - _stab) * 0.05 - (20 - _approval) * 0.05, 1)
        _gdp_revenue = _contraction  # override to negative
        game_state.update_budget(_gdp_revenue)
        print(f"  [turn_processor] GDP CONTRACTION: approval {_approval}%, stability {_stab}% -> ${_gdp_revenue:.1f}B")
        messages.append(f"💵 GDP contraction (approval {_approval}%, stability {_stab}%): ${_gdp_revenue:.1f}B (capital flight, economic collapse)")
    else:
        _gdp_revenue = max(0, _gdp_revenue)  # floor at 0 for normal operation
        game_state.update_budget(_gdp_revenue)
        _tech_label = f", tech ×{_tech_multiplier:.2f}" if _tech_multiplier > 1.0 else ""
        _infra_label = f", infra +0.5%" if _infra_bonus > 0 else ""
        print(f"  [turn_processor] TAX REVENUE — income: ${_income_rev_9b:.1f}B (rate {_income_rate*100:.0f}%), corporate: ${_corp_rev_9b:.1f}B (rate {_corp_rate*100:.0f}%), resource: ${_resource_rev_9b:.1f}B (rate {_resource_rate*100:.0f}%), total: ${_gdp_revenue:.1f}B")
        messages.append(f"💵 GDP revenue (tax rates: {_income_rate*100:.0f}%/{_corp_rate*100:.0f}%/{_resource_rate*100:.0f}%, approval {_approval}%, stability {_stab}%{_tech_label}{_infra_label}): +${_gdp_revenue:.1f}B")

    # ──────────────────────────────────────────
    # 9.5A: NEW tax revenue computation (comparison log — old code above still active)
    # ──────────────────────────────────────────
    _95a_rev = compute_tax_revenue(game_state)
    print(f"  [9.5A] budget_integration: OLD_revenue=${_gdp_revenue:.1f} "
          f"NEW_gross=${_95a_rev['gross_revenue']:.1f} "
          f"NEW_net=${_95a_rev['net_revenue']:.1f} "
          f"NEW_skim=${_95a_rev['skim_income']:.1f} "
          f"delta=${_95a_rev['net_revenue'] - _gdp_revenue:.1f}")

    # FIX F (session 6): Log peak relations each turn for verification
    _rh = getattr(game_state, 'relations_high', {})
    print(f"  [turn_processor] PEAK RELATIONS — USA: {_rh.get('usa', 50)}, Arabia: {_rh.get('arabia', 50)}, EU: {_rh.get('eu', 50)}, DPRG: {_rh.get('dprg', 50)}")

    # ──────────────────────────────────────────
    # 9b-ii. fixes_13 Fix 12: Relations 100 unlock checks
    # fixes_15 Fix G: REMOVED from here — these now ONLY run in api.py after
    # check_pressure_events(), so world-event-driven relation changes are captured.
    # The duplicate call here was firing before world events could push relations to 100.
    # ──────────────────────────────────────────

    # ──────────────────────────────────────────
    # 9c. EU SOFT CAP (Tech Level redesign)
    # Soft cap = 60 + (tech_level × 2), hard cap 100.
    # Below soft cap: normal gain. Above soft cap: gain halved.
    # ──────────────────────────────────────────
    _tech_lev = float(getattr(game_state, 'tech_level', 0))
    _eu_soft_cap = min(100, 60 + int(_tech_lev * 2))
    _eu_current = game_state.relations.get('eu', 50)
    print(f"  [TECH] EU soft cap: {_eu_soft_cap} (tech={_tech_lev:.1f})")
    if _eu_current > 100:
        game_state.relations['eu'] = 100
        messages.append(f"🔬 EU relations capped at 100 (hard cap)")
        print(f"  [turn_processor] EU HARD CAP: {_eu_current} -> 100")

    # ──────────────────────────────────────────
    # 10. STAGE 5 SESSION 2: DEAL FOLLOW-THROUGH TRACKING
    # Check if the player's last action contradicts any active deal commitments.
    # Arabia/DPRG alignment breaks USA/EU deals and vice versa.
    # ──────────────────────────────────────────
    deal_history = getattr(game_state, 'deal_history', [])
    if deal_history and game_state.action_history:
        last_action = game_state.action_history[-1]
        last_npc = last_action.get('npc', '')
        last_type = last_action.get('type', '')
        if last_type in ('side_with', 'accept_deal') and last_npc:
            # Western alignment contradicts Arabia/DPRG deals and vice versa
            _western = {'usa', 'eu'}
            _eastern = {'arabia', 'dprg'}
            for deal in deal_history:
                if deal.get('broken'):
                    continue
                if deal.get('expires_turn', 0) < game_state.current_turn:
                    continue
                deal_npc = deal.get('npc', '')
                # Check contradiction: chose west while holding east deal (or vice versa)
                contradicted = (
                    (last_npc in _western and deal_npc in _eastern) or
                    (last_npc in _eastern and deal_npc in _western)
                )
                if contradicted:
                    deal['broken'] = True
                    messages.append(
                        f"💔 Deal broken: commitment to {deal_npc.upper()} ('{deal['summary']}') "
                        f"contradicted by {last_npc.upper()} alignment"
                    )
                    # Session 5 Phase C Hook 2: store_memory on promise broken
                    try:
                        from memory_engine import store_memory
                        _player_id = getattr(game_state, 'player_id', None)
                        if _player_id:
                            store_memory(
                                player_id=_player_id, npc=deal_npc, era=0,
                                turn=game_state.current_turn, event_type='promise_broken',
                                description=f"Broke deal with {deal_npc.upper()}: '{deal['summary'][:80]}' — aligned with {last_npc.upper()} instead"
                            )
                    except Exception as e:
                        print(f"  [turn_processor] Memory hook (promise_broken) failed: {e}")

    # ──────────────────────────────────────────
    # 11. STAGE 5: REGIME SHIFT CHECKS
    # Regime types (left -> right): Managed Democracy -> Soft Authoritarianism
    #   -> Patronage State -> Kleptocracy -> Totalitarian Regime
    # Power base: Mass-Dependent -> Mixed -> Elite-Captured
    # ──────────────────────────────────────────
    _regime_order = [
        'Managed Democracy',
        'Soft Authoritarianism',
        'Patronage State',
        'Kleptocracy',
        'Totalitarian Regime',
    ]
    _power_order = ['Mass-Dependent', 'Mixed', 'Elite-Captured']

    si = game_state.state_identity
    current_regime = si.get('regime_type', 'Managed Democracy')
    current_power = si.get('power_base', 'Mass-Dependent')
    regime_idx = _regime_order.index(current_regime) if current_regime in _regime_order else 0
    power_idx  = _power_order.index(current_power) if current_power in _power_order else 0

    # Update approval/skim streak counters (checked BEFORE shifting)
    if game_state.public_approval < 35:
        game_state.low_approval_turns += 1
        game_state.high_approval_turns = 0
    elif game_state.public_approval > 65:
        game_state.high_approval_turns += 1
        game_state.low_approval_turns = 0
    else:
        game_state.low_approval_turns = 0
        game_state.high_approval_turns = 0

    regime_changed = False
    power_changed = False

    # ── fixes_11 Fix 1: Old skim-based regime shift triggers DISABLED ──
    # Regime label now comes EXCLUSIVELY from compute_regime_from_axes() in section 13g.
    # The old triggers (consecutive large skims, low approval, stability crisis, high approval)
    # were conflicting with the axes system, producing contradictory EOT messages every turn.
    # Streak counters (low_approval_turns, high_approval_turns) are still updated above
    # for potential future use, but they no longer directly shift the regime label.

    # ── Power base shifts ──
    # Check last action to see if Arabia/DPRG oriented (shift toward Elite-Captured)
    # or USA/EU oriented (shift toward Mass-Dependent)
    _power_shift_reason = None
    last_action = game_state.action_history[-1] if game_state.action_history else {}
    last_npc = last_action.get('npc', '')
    last_type = last_action.get('type', '')
    _npc_labels = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'}
    if last_type in ('side_with', 'accept_deal'):
        if last_npc in ('arabia', 'dprg') and power_idx < len(_power_order) - 1:
            power_idx += 1
            power_changed = True
            _power_shift_reason = f"aligned with {_npc_labels.get(last_npc, last_npc)} (Eastern patron dependency)"
        elif last_npc in ('usa', 'eu') and power_idx > 0:
            power_idx -= 1
            power_changed = True
            _power_shift_reason = f"aligned with {_npc_labels.get(last_npc, last_npc)} (Western institutional credibility)"

    # Corruption upgrades push toward Elite-Captured
    upgrades = getattr(game_state, 'corruption_upgrades', {})
    active_upgrades = sum(1 for v in upgrades.values() if v)
    if active_upgrades >= 2 and power_idx < len(_power_order) - 1:
        power_idx = min(len(_power_order) - 1, power_idx + 1)
        power_changed = True
        _power_shift_reason = f"{active_upgrades} Shadow Cabinet upgrades consolidated elite control"

    # fixes_11 Fix 1: regime_changed is always False now (old triggers disabled).
    # Regime label is set exclusively by compute_regime_from_axes() in section 13g.
    if power_changed:
        old_power = current_power
        si['power_base'] = _power_order[power_idx]
        if old_power != _power_order[power_idx]:
            _reason_str = f" — {_power_shift_reason}" if _power_shift_reason else ""
            messages.append(
                f"🔄 Power base: '{old_power}' -> '{_power_order[power_idx]}'{_reason_str}"
            )

    # FIX 1: Track sanctions/embargo active turns for legacy
    if game_state.usa_sanctions_tier > 0:
        game_state.sanctions_active_turns = getattr(game_state, 'sanctions_active_turns', 0) + 1
    if game_state.arabia_embargo_tier > 0:
        game_state.embargo_active_turns = getattr(game_state, 'embargo_active_turns', 0) + 1

    # ──────────────────────────────────────────
    # 12. SESSION 4B: ELECTION PRE-WARNING
    # One turn before election_turn, set warning flag for frontend banner
    # ──────────────────────────────────────────
    election_turn = getattr(game_state, 'election_turn', 4)
    election_fired = getattr(game_state, 'election_fired', False)
    # fixes_10 Fix 3: Set flag one turn earlier so frontend sees it BEFORE the election turn.
    # EOT runs at current_turn=N, then advance_turn() -> N+1. Frontend renders N+1's display.
    # To show warning on turn (election_turn-1), flag must be set during turn (election_turn-2)'s EOT.
    if not election_fired and game_state.current_turn == election_turn - 2:
        game_state.election_warning_shown = True
        print(f"  [turn_processor] ELECTION WARNING: pre-warning set at turn {game_state.current_turn} (visible on turn {game_state.current_turn + 1})")

    # ──────────────────────────────────────────
    # 12b. fixes_8 Fix 11: BANKRUPTCY PRE-WARNING
    # fixes_19 Fix E: Full drain projection including sanctions, embargo, EU pressure,
    # cabinet maintenance, dual crisis multiplier, and real GDP formula.
    # ──────────────────────────────────────────
    _projected_drain = 3.0  # base government costs

    # Oil import costs (matches section 2 formula: oil_price / 15.0)
    _resource_independent_pw = getattr(game_state, 'resource_independence_active', False)
    if _resource_independent_pw:
        _oil_cost_pw = 0.0
    else:
        _oil_cost_pw = round(game_state.oil_price / 15.0, 1)
    _projected_drain += _oil_cost_pw

    # Dual crisis multiplier (USA AND Arabia both hostile)
    _usa_rel_pw = game_state.relations.get('usa', 50)
    _arabia_rel_pw = game_state.relations.get('arabia', 50)
    _eu_rel_pw = game_state.relations.get('eu', 50)
    _crisis_mult_pw = 1.5 if (_usa_rel_pw < 30 and _arabia_rel_pw < 30) else 1.0

    # fixes_21 Fix H: USA sanctions drain — project next turn's effective tier
    # based on current relations (ramp-limited: max +1 tier per turn), not just
    # current tier. Prevents bankruptcy surprise from tier escalation.
    _usa_tier_pw = getattr(game_state, 'usa_sanctions_tier', 0)
    if _usa_rel_pw <= 4:
        _usa_target = 4
    elif _usa_rel_pw <= 14:
        _usa_target = 3
    elif _usa_rel_pw <= 24:
        _usa_target = 2
    elif _usa_rel_pw <= 35:
        _usa_target = 1
    else:
        _usa_target = 0
    _usa_projected_tier = min(_usa_target, _usa_tier_pw + 1) if _usa_target > _usa_tier_pw else _usa_target
    _sanction_base = {0: 0, 1: 2, 2: 4, 3: 7, 4: 10}.get(_usa_projected_tier, 0)
    _sanction_drain = round(_sanction_base * _crisis_mult_pw)
    _projected_drain += _sanction_drain

    # fixes_21 Fix H: Arabia embargo — project next turn's effective tier
    _arabia_tier_pw = getattr(game_state, 'arabia_embargo_tier', 0)
    if _arabia_rel_pw <= 4:
        _arabia_target = 4
    elif _arabia_rel_pw <= 14:
        _arabia_target = 3
    elif _arabia_rel_pw <= 24:
        _arabia_target = 2
    elif _arabia_rel_pw <= 35:
        _arabia_target = 1
    else:
        _arabia_target = 0
    _arabia_projected_tier = min(_arabia_target, _arabia_tier_pw + 1) if _arabia_target > _arabia_tier_pw else _arabia_target
    _embargo_base = {0: 0, 1: 0, 2: 0, 3: 3, 4: 5}.get(_arabia_projected_tier, 0)
    _embargo_drain = round(_embargo_base * _crisis_mult_pw)
    _projected_drain += _embargo_drain

    # EU trade friction/restrictions (section 6)
    _eu_drain = 0
    if _eu_rel_pw < 36:
        if _eu_rel_pw <= 19:
            _eu_drain = round(4 * _crisis_mult_pw)
        else:
            _eu_drain = round(2 * _crisis_mult_pw)
    _projected_drain += _eu_drain

    # Cabinet axis maintenance costs (section 13)
    from game_state import AXIS_MAINTENANCE as _AM_PW
    _cabinet_axes_pw = getattr(game_state, 'cabinet_axes', {})
    _maint_drain = 0.0
    for _ax_name, (_free_thresh, _cost_per) in _AM_PW.items():
        _ax_level = _cabinet_axes_pw.get(_ax_name, 0)
        if _ax_level > _free_thresh:
            _maint_drain += (_ax_level - _free_thresh) * _cost_per
    _projected_drain += _maint_drain

    # 9.5A: Add daily commitment costs to drain projection
    _commitment_drain = getattr(game_state, 'total_daily_commitment', 0.0)
    _projected_drain += _commitment_drain
    print(f"  [BANKRUPTCY] now shows commitment drain included in projection: ${_commitment_drain:.1f}B")

    # Projected income: real GDP tax-rate formula (matches section 9b)
    _gdp_base_pw = getattr(game_state, 'gdp_base', 100.0)
    _tax_rates_pw = getattr(game_state, 'tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
    _endowment_pw = getattr(game_state, 'resource_endowment', {})
    _inc_rev = _gdp_base_pw * _tax_rates_pw.get('income_tax', 0.20) * 0.10
    _corp_rev = _gdp_base_pw * _tax_rates_pw.get('corporate_tax', 0.15) * 0.06
    _res_rev = _gdp_base_pw * _tax_rates_pw.get('resource_tax', 0.25) * _endowment_pw.get('oil_reserves', 0.7) * 0.12
    _projected_income = round(_inc_rev + _corp_rev + _res_rev, 1)
    # Approval modifier
    _appr_pw = game_state.public_approval
    if _appr_pw >= 80:
        _projected_income = round(_projected_income * 1.4, 1)
    elif _appr_pw >= 60:
        pass  # 1.0 multiplier
    elif _appr_pw >= 40:
        _projected_income = round(_projected_income * 0.7, 1)
    else:
        _projected_income = round(_projected_income * 0.4, 1)
    # Stability modifier
    _stab_pw = game_state.stability
    if _stab_pw >= 80:
        _projected_income += 1.0
    elif _stab_pw < 30:
        _projected_income -= 1.0
    _projected_income = max(0, _projected_income)

    _projected_budget = game_state.budget - _projected_drain + _projected_income
    print(f"  [BANKRUPTCY] Projection: budget={game_state.budget:.1f}, drain={_projected_drain:.1f} "
          f"(govt=3.0, oil={_oil_cost_pw:.1f}, sanctions={_sanction_drain}[tier {_usa_tier_pw}->{_usa_projected_tier}], "
          f"embargo={_embargo_drain}[tier {_arabia_tier_pw}->{_arabia_projected_tier}], "
          f"eu={_eu_drain}, maint={_maint_drain:.1f}, commitment={_commitment_drain:.1f}, "
          f"crisis_mult={_crisis_mult_pw}), "
          f"income={_projected_income:.1f}, projected={_projected_budget:.1f}")
    # fixes_9 Fix 5: Caveat text — projection models drain only, not player deal choices
    if _projected_budget < 0:
        messages.append(f"⚠️ BANKRUPTCY RISK: projected ${_projected_budget:.1f}B next turn (drain only — excludes deals and world events)")
    elif _projected_budget < 5.0:
        messages.append(f"📉 LOW BUDGET (${_projected_budget:.1f}B): pressure increasing")

    # ──────────────────────────────────────────
    # 12c. fixes_10 Fix 6: ARABIA EMBARGO TIER BOUNDARY WARNING
    # Warn if Arabia relations near a tier boundary
    # fixes_21 Fix K: Deduplicate — skip if embargo risk already warned this EOT
    # ──────────────────────────────────────────
    _arabia_rel = game_state.relations.get('arabia', 50)
    _EMBARGO_TIER_BOUNDARIES = [35, 25, 15, 5]
    _near_boundary = any(abs(_arabia_rel - b) <= 5 for b in _EMBARGO_TIER_BOUNDARIES)
    _already_warned_arabia_k = any('Arabia' in m and ('Embargo risk' in m or 'EMBARGO' in m) for m in messages)
    if _near_boundary and _arabia_rel <= 40 and not _already_warned_arabia_k:
        messages.append(
            f"⚠️ Arabia near oil tier boundary "
            f"(rel {_arabia_rel:.0f}) — "
            f"oil costs may increase next turn"
        )
        print(f"  [turn_processor] ARABIA TIER WARNING: relations {_arabia_rel:.0f} near boundary")

    # ──────────────────────────────────────────
    # 13. SESSION 5: CABINET AXIS MAINTENANCE COSTS (OLD — disabled by 9.5A)
    # Kept for comparison logging only. Budget deduction replaced by commitment model.
    # ──────────────────────────────────────────
    from game_state import AXIS_MAINTENANCE
    _cabinet_axes = getattr(game_state, 'cabinet_axes', {})
    _maintenance_total = 0.0
    _maintenance_parts = []
    for axis_name, (free_thresh, cost_per) in AXIS_MAINTENANCE.items():
        level = _cabinet_axes.get(axis_name, 0)
        if level > free_thresh:
            cost = round((level - free_thresh) * cost_per, 1)
            _maintenance_total += cost
            _maintenance_parts.append(f"{axis_name} {level}: ${cost:.1f}B")
    if _maintenance_total > 0:
        # 9.5A: OLD deduction disabled — replaced by commitment costs below
        # game_state.update_budget(-_maintenance_total)
        game_state.cabinet_maintenance_paid = getattr(game_state, 'cabinet_maintenance_paid', 0.0) + _maintenance_total
        print(f"  [9.5A] OLD_cabinet_maintenance: ${_maintenance_total:.1f}B ({_maintenance_parts}) [DISABLED - not deducted]")

    # ──────────────────────────────────────────
    # 13-9.5A: COMMITMENT MODEL COSTS (replaces old cabinet maintenance)
    # ──────────────────────────────────────────
    _95a_budget_total, _95a_militia_cost = compute_daily_commitment_cost(game_state)

    # Deduct commitment costs from national budget
    if _95a_budget_total > 0:
        game_state.update_budget(-_95a_budget_total)
        messages.append(
            f"🏛️ Commitment costs: -${_95a_budget_total:.1f}B "
            f"(mil ${getattr(game_state, 'daily_military_cost', 0):.1f} "
            f"intel ${getattr(game_state, 'daily_intel_cost', 0):.1f} "
            f"diplo ${getattr(game_state, 'daily_diplomatic_cost', 0):.1f} "
            f"social ${getattr(game_state, 'daily_social_cost', 0):.1f} "
            f"edu ${getattr(game_state, 'daily_education_cost', 0):.1f} "
            f"resource ${getattr(game_state, 'daily_resource_cost', 0):.1f} "
            f"political ${TIER_COSTS.get('political', {}).get(getattr(game_state, 'political_tier', 0), 0):.1f})"
        )
    print(f"  [9.5A] budget_integration: commitment_deducted=${_95a_budget_total:.1f} "
          f"OLD_maintenance=${_maintenance_total:.1f} "
          f"delta=${_95a_budget_total - _maintenance_total:.1f}")

    # Militia costs — deduct from personal wealth, NOT budget
    if _95a_militia_cost > 0:
        _pw_before = getattr(game_state, 'personal_wealth', 0.0)
        if _pw_before >= _95a_militia_cost:
            game_state.personal_wealth = round(_pw_before - _95a_militia_cost, 2)
            messages.append(f"⚔️ Militia maintenance: -${_95a_militia_cost:.1f}B personal wealth")
        else:
            # Can't afford militia — degrade militia tier
            game_state.personal_wealth = 0.0
            _old_mt = getattr(game_state, 'militia_tier', 0)
            if _old_mt > 0:
                game_state.militia_tier = _old_mt - 1
                messages.append(
                    f"⚔️ Militia unpaid: personal wealth depleted, "
                    f"militia tier degraded {_old_mt} → {_old_mt - 1}")
                print(f"  [9.5A] militia_unpaid: pw={_pw_before:.1f}, cost={_95a_militia_cost:.1f}, "
                      f"tier {_old_mt} -> {_old_mt - 1}")
            else:
                messages.append(f"⚔️ Militia disbanded: cannot maintain without personal wealth")
        print(f"  [9.5A] militia_cost: ${_95a_militia_cost:.1f} from personal_wealth "
              f"(${_pw_before:.1f} -> ${getattr(game_state, 'personal_wealth', 0.0):.1f})")

    # ──────────────────────────────────────────
    # 13-9.5A-Shadow: SHADOW STATE COSTS (personal wealth drain)
    # ──────────────────────────────────────────
    _shadow_total, _shadow_ext_rev, _shadow_net = compute_shadow_state_costs(game_state)

    if _shadow_net > 0:
        _pw_before_shadow = getattr(game_state, 'personal_wealth', 0.0)
        if _pw_before_shadow >= _shadow_net:
            game_state.personal_wealth = round(_pw_before_shadow - _shadow_net, 2)
            messages.append(
                f"🕶 Shadow state costs: -${_shadow_net:.1f}B personal "
                f"(costs ${_shadow_total:.1f}B - extraction revenue ${_shadow_ext_rev:.1f}B)")
        else:
            # Can't afford shadow costs -- degrade highest-cost shadow axis
            game_state.personal_wealth = 0.0
            _shadow_axes_degrade = [
                ('media_tier', 'daily_media_cost'),
                ('judicial_tier', 'daily_judicial_cost'),
                ('domestic_surveillance_tier', 'daily_surveillance_cost'),
                ('extraction_tier', 'daily_extraction_cost'),
                ('militia_tier', 'daily_militia_cost'),
            ]
            _highest_shadow = None
            _highest_shadow_cost = 0.0
            for _tier_attr, _cost_attr in _shadow_axes_degrade:
                _cost = getattr(game_state, _cost_attr, 0.0)
                _tier = getattr(game_state, _tier_attr, 0)
                if _cost > _highest_shadow_cost and _tier > 0:
                    _highest_shadow_cost = _cost
                    _highest_shadow = _tier_attr
            if _highest_shadow:
                _old_t = getattr(game_state, _highest_shadow)
                setattr(game_state, _highest_shadow, _old_t - 1)
                _axis_name = _highest_shadow.replace('_tier', '')
                messages.append(
                    f"🕶 Shadow unpaid: personal wealth depleted, "
                    f"{_axis_name} tier degraded {_old_t} -> {_old_t - 1}")
                print(f"  [9.5A-Shadow] shadow_unpaid: pw={_pw_before_shadow:.1f}, "
                      f"net_cost={_shadow_net:.1f}, {_axis_name} {_old_t} -> {_old_t - 1}")
        print(f"  [9.5A-Shadow] shadow_drain: ${_shadow_net:.1f} from personal_wealth "
              f"(${_pw_before_shadow:.1f} -> ${getattr(game_state, 'personal_wealth', 0.0):.1f})")
    elif _shadow_ext_rev > 0 and _shadow_net <= 0:
        # Extraction revenue exceeds costs -- net gain to personal wealth
        _net_gain = round(abs(_shadow_net), 2)
        if _net_gain > 0:
            game_state.update_personal_wealth(_net_gain, source="shadow_extraction")
            messages.append(
                f"🕶 Shadow extraction net gain: +${_net_gain:.1f}B personal "
                f"(revenue ${_shadow_ext_rev:.1f}B > costs ${_shadow_total:.1f}B)")
            print(f"  [9.5A-Shadow] extraction_net_gain: +${_net_gain:.1f} to personal_wealth")

    # Skim income — add skim_rate% of old revenue to personal wealth
    _skim_rate = getattr(game_state, 'skim_rate', 0.0)
    if _skim_rate > 0 and _gdp_revenue > 0:
        _skim_income = round(_gdp_revenue * _skim_rate, 2)
        game_state.update_personal_wealth(_skim_income, source="skim")
        messages.append(f"💰 Budget diversion: +${_skim_income:.1f}B personal ({_skim_rate*100:.0f}% skim)")
        # [9.5A-FIX2] Skim heat generation moved to compute_tax_revenue()
        print(f"  [9.5A] skim_income: ${_skim_income:.1f}B to personal_wealth "
              f"(rate={_skim_rate*100:.0f}%, revenue=${_gdp_revenue:.1f})")

    # Apply commitment EOT checks (coup amplifier, intel politicization, EU ceiling, sustainability gap)
    _95a_net_rev = _95a_rev.get('net_revenue', _gdp_revenue)
    apply_commitment_eot_checks(game_state, messages, net_revenue=_95a_net_rev)

    # ──────────────────────────────────────────
    # 13b. TECH LEVEL PASSIVE ACQUISITION (redesigned)
    # Relationship-weighted passive gain. Tech accumulates as float.
    # Negotiation quality multiplier: deals accepted this turn boost that NPC's contribution.
    # ──────────────────────────────────────────
    _BASE_TECH_RATE = 0.5
    _TECH_NPC_WEIGHTS = {'eu': 1.00, 'usa': 0.90, 'dprg': 0.50, 'arabia': 0.30}

    # Check which NPCs had a deal accepted THIS turn
    _deals_this_turn = set()
    for _d in getattr(game_state, 'deal_history', []):
        if _d.get('turn_accepted') == game_state.current_turn:
            _deals_this_turn.add(_d.get('npc', ''))

    _old_tech = float(getattr(game_state, 'tech_level', 0))
    _tech_contribs = {}
    _tech_gain = 0.0
    for _npc_key, _weight in _TECH_NPC_WEIGHTS.items():
        _npc_rel = game_state.relations.get(_npc_key, 50)
        _contrib = (_npc_rel / 100.0) * _weight * _BASE_TECH_RATE
        if _npc_key in _deals_this_turn:
            _contrib *= 1.5
        _tech_contribs[_npc_key] = round(_contrib, 3)
        _tech_gain += _contrib

    _tech_gain = round(_tech_gain, 3)
    game_state.tech_level = round(_old_tech + _tech_gain, 1)
    game_state.tech_gain_last_turn = _tech_gain
    _new_tech = game_state.tech_level

    print(f"  [TECH] Gain this turn: {_tech_gain:.3f} (eu={_tech_contribs.get('eu', 0):.3f}, usa={_tech_contribs.get('usa', 0):.3f}, arabia={_tech_contribs.get('arabia', 0):.3f}, dprg={_tech_contribs.get('dprg', 0):.3f})")
    print(f"  [TECH] Tech level: {_old_tech:.1f} -> {_new_tech:.1f}")
    if _deals_this_turn:
        print(f"  [TECH] Deal bonus active for: {', '.join(_deals_this_turn)}")
    messages.append(f"🔬 Tech: {_old_tech:.1f} -> {_new_tech:.1f} (+{_tech_gain:.2f})")

    # ── Tech tier transition detection + console logs ──
    _old_tier = get_tech_tier(_old_tech)
    _new_tier = get_tech_tier(_new_tech)
    if _old_tier != _new_tier:
        print(f"  [tech_level] Tier transition: {_old_tier} -> {_new_tier} at tech_level={_new_tech}")
        messages.append(f"🔬 TIER UP: {TECH_TIER_NAMES[_old_tier]} -> {TECH_TIER_NAMES[_new_tier]}")
    # Log modifiers every turn
    _econ_mod = get_economy_efficiency_modifier(_new_tech)
    _intel_mod = get_intel_detection_risk_modifier(_new_tech)
    print(f"  [tech_level] Economy efficiency modifier: +{int(_econ_mod * 100)}% (tier={_new_tier})")
    print(f"  [tech_level] Intel detection risk modifier: -{int(_intel_mod * 100)}% (tier={_new_tier})")
    # Middle power transition — fires once on first reaching Tier 5
    if _new_tier >= 5 and not getattr(game_state, 'middle_power_transition', False):
        game_state.middle_power_transition = True
        print(f"  [tech_level] MIDDLE POWER TRANSITION FLAG SET — fires once")
        messages.append("🌐 MIDDLE POWER TRANSITION: Europa has reached Frontier status")

    # ──────────────────────────────────────────
    # 13c. SESSION 5: ECONOMIC MODEL — GDP + TAX REVENUE
    # Revenue streams computed from tax_rates * gdp_base * modifiers.
    # ──────────────────────────────────────────
    _tax_rates = getattr(game_state, 'tax_rates', {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25})
    _gdp_b = getattr(game_state, 'gdp_base', 100.0)
    _endowment = getattr(game_state, 'resource_endowment', {})

    # Grow GDP base
    _growth = getattr(game_state, 'gdp_growth_rate', 0.02)
    # Stability modifies growth: high stability boosts, crisis penalizes
    if game_state.stability >= 70:
        _growth += 0.01
    elif game_state.stability < 30:
        _growth -= 0.02
    # Sanctions suppress growth
    if game_state.usa_sanctions_tier >= 2:
        _growth -= 0.01
    _gdp_b = round(_gdp_b * (1 + _growth), 1)
    game_state.gdp_base = _gdp_b

    # Tech Level economy efficiency modifier — applied to GDP base revenue
    _tech_econ_mod = get_economy_efficiency_modifier(getattr(game_state, 'tech_level', 0))
    _gdp_b_effective = round(_gdp_b * (1 + _tech_econ_mod), 1)

    # Revenue calculation (uses tech-modified GDP)
    _income_rev = round(_gdp_b_effective * _tax_rates.get('income_tax', 0.20) * 0.10, 1)  # 10% of income tax * GDP
    _corp_rev = round(_gdp_b_effective * _tax_rates.get('corporate_tax', 0.15) * 0.08, 1)
    _resource_rev = round(_gdp_b_effective * _tax_rates.get('resource_tax', 0.25) * _endowment.get('oil_reserves', 0.7) * 0.12, 1)
    _total_tax_rev = _income_rev + _corp_rev + _resource_rev

    # fixes_13 Fix 2 + Fix 3: Tax approval scaling with diminishing returns + low-tax bonus
    # Diminishing returns: penalty × (current_approval / 100) — kleptocracy burns down approval,
    # then extraction becomes almost free politically.
    _avg_tax = sum(_tax_rates.values()) / max(1, len(_tax_rates))
    _current_approval = game_state.public_approval

    # Session 6: Party Consolidation (Political L3) — reduce tax approval drain by 25%
    _party_consol_active = getattr(game_state, 'party_consolidation_turns', 0) > 0
    _tax_drain_mult = 0.75 if _party_consol_active else 1.0

    if _avg_tax <= 0.15:
        # Fix 3: Low taxes (0-15%) are popular — approval +2%
        game_state.update_approval(2)
        messages.append("📊 Low taxes popular: approval +2%")
        print(f"  [turn_processor] TAX APPROVAL: low avg {_avg_tax*100:.0f}% -> approval +2%")
    elif _avg_tax <= 0.30:
        # 16-30%: neutral — no approval change
        pass
    elif _avg_tax <= 0.45:
        # 31-45%: approval -3% scaled by current approval (diminishing returns)
        _raw_penalty = -3
        _scaled_penalty = round(_raw_penalty * (_current_approval / 100) * _tax_drain_mult, 1)
        _scaled_penalty = min(-1, int(_scaled_penalty)) if _scaled_penalty < 0 else 0  # at least -1 if any penalty
        if _scaled_penalty < 0:
            game_state.update_approval(_scaled_penalty)
            _consol_label = " (Party Consolidation -25%)" if _party_consol_active else ""
            messages.append(f"📊 High tax burden: approval {_scaled_penalty}% (scaled from {_raw_penalty}% at {_current_approval}% approval{_consol_label})")
            print(f"  [turn_processor] TAX APPROVAL: avg {_avg_tax*100:.0f}%, raw {_raw_penalty}, scaled {_scaled_penalty} (approval {_current_approval}%, consol={_party_consol_active})")
    elif _avg_tax <= 0.55:
        # 46-55%: approval -6% scaled, stability -2%
        _raw_penalty = -6
        _scaled_penalty = round(_raw_penalty * (_current_approval / 100) * _tax_drain_mult, 1)
        _scaled_penalty = min(-1, int(_scaled_penalty)) if _scaled_penalty < 0 else 0
        if _scaled_penalty < 0:
            game_state.update_approval(_scaled_penalty)
        game_state.update_stability(-2)
        _consol_label = " (Party Consolidation -25%)" if _party_consol_active else ""
        messages.append(f"📊 Heavy tax burden: approval {_scaled_penalty}%, stability -2%{_consol_label}")
        print(f"  [turn_processor] TAX APPROVAL: avg {_avg_tax*100:.0f}%, raw {_raw_penalty}, scaled {_scaled_penalty}, stability -2% (consol={_party_consol_active})")
    else:
        # 56%+: approval -10% scaled, stability -3%, protests possible
        _raw_penalty = -10
        _scaled_penalty = round(_raw_penalty * (_current_approval / 100) * _tax_drain_mult, 1)
        _scaled_penalty = min(-1, int(_scaled_penalty)) if _scaled_penalty < 0 else 0
        if _scaled_penalty < 0:
            game_state.update_approval(_scaled_penalty)
        game_state.update_stability(-3)
        _consol_label = " (Party Consolidation -25%)" if _party_consol_active else ""
        messages.append(f"📊 Crushing tax burden: approval {_scaled_penalty}%, stability -3%{_consol_label}")
        print(f"  [turn_processor] TAX APPROVAL: avg {_avg_tax*100:.0f}%, raw {_raw_penalty}, scaled {_scaled_penalty}, stability -3% (consol={_party_consol_active})")
        # Protest risk at extreme taxation
        if random.randint(1, 100) <= 30:
            game_state.protests_pending = True
            messages.append("🪧 Tax protests erupting — public unrest")

    # Fix 3: Diplomatic effects from zero-tax rates
    _income_rate_13c = _tax_rates.get('income_tax', 0.20)
    _corp_rate_13c = _tax_rates.get('corporate_tax', 0.15)
    _resource_rate_13c = _tax_rates.get('resource_tax', 0.25)

    if _income_rate_13c == 0 and _corp_rate_13c == 0 and _resource_rate_13c == 0:
        # All taxes at 0%: EU -2 (failing state optics)
        game_state.update_relations('eu', -2)
        messages.append("📊 Zero taxation: EU -2 (failing state optics)")
        print("  [turn_processor] TAX DIPLOMATIC: all taxes 0% -> EU -2")

    if _corp_rate_13c == 0:
        # Corporate tax 0%: EU -2, USA -2 (oligarchic signal)
        game_state.update_relations('eu', -2)
        game_state.update_relations('usa', -2)
        messages.append("📊 Zero corporate tax: EU -2, USA -2 (oligarchic signal)")
        print("  [turn_processor] TAX DIPLOMATIC: corporate tax 0% -> EU -2, USA -2")

    if _resource_rate_13c == 0:
        # Resource tax 0%: Arabia +1 (pragmatic governance)
        game_state.update_relations('arabia', 1)
        messages.append("📊 Zero resource tax: Arabia +1 (pragmatic)")
        print("  [turn_processor] TAX DIPLOMATIC: resource tax 0% -> Arabia +1")

    # Store revenue streams
    _rev = getattr(game_state, 'revenue_streams', {})
    _rev['income_tax'] = _income_rev
    _rev['corporate_tax'] = _corp_rev
    _rev['resource_tax'] = _resource_rev
    game_state.revenue_streams = _rev

    # fixes_12 Fix 2: Tax revenue is now applied in section 9b using tax_rates.
    # This section updates the revenue_streams dict for display purposes and
    # grows GDP base. The actual budget impact is in 9b.

    # ──────────────────────────────────────────
    # 13d. SESSION 5: ADVISOR LOYALTY CHECK
    # ──────────────────────────────────────────
    try:
        from advisor_engine import check_advisor_loyalty, apply_stat_distortion
        _advisor_msgs = check_advisor_loyalty(game_state)
        messages.extend(_advisor_msgs)
        # Compute and store distortions for frontend
        game_state.advisor_distortions = apply_stat_distortion(game_state)
    except ImportError:
        pass

    # ──────────────────────────────────────────
    # 13e. SESSION 5: LATENT STATS — SOFT POWER + DIPLOMATIC CAPITAL
    # Computed from current state, not accumulated. Display-only.
    # ──────────────────────────────────────────
    _sp = 0
    for _npc_k in ('usa', 'arabia', 'eu', 'dprg'):
        _sp += min(25, max(0, game_state.relations.get(_npc_k, 50)) // 4)
    _sp += min(10, int(getattr(game_state, 'tech_level', 0)) // 10)
    _sp += min(15, game_state.public_approval // 7)
    game_state.soft_power = min(100, max(0, _sp))

    _dc = 0
    _deal_h = getattr(game_state, 'deal_history', [])
    _active_deals = [d for d in _deal_h if not d.get('broken') and d.get('expires_turn', 0) >= game_state.current_turn]
    _dc += min(30, len(_active_deals) * 10)
    for _npc_k in ('usa', 'arabia', 'eu', 'dprg'):
        _lev = getattr(game_state, 'leverage_events', {}).get(_npc_k, [])
        _dc += min(10, len(_lev) * 5)
    _dc += min(20, sum(1 for v in game_state.relations.values() if v >= 60) * 5)
    game_state.diplomatic_capital = min(100, max(0, _dc))

    # ──────────────────────────────────────────
    # 13e-ii. SESSION 5 PHASE C: RELATIONS MILESTONE MEMORY HOOKS
    # Store memory when relations cross 80+ or drop below 30.
    # ──────────────────────────────────────────
    try:
        from memory_engine import store_memory
        _player_id = getattr(game_state, 'player_id', None)
        if _player_id:
            _milestone_log = getattr(game_state, '_relations_milestone_log', {})
            for _npc_k in ('usa', 'arabia', 'eu', 'dprg'):
                _rel_val = game_state.relations.get(_npc_k, 50)
                _prev_milestone = _milestone_log.get(_npc_k, 'neutral')
                if _rel_val >= 80 and _prev_milestone != 'high':
                    store_memory(
                        player_id=_player_id, npc=_npc_k, era=0,
                        turn=game_state.current_turn, event_type='relations_milestone_high',
                        description=f"Relations with {_npc_k.upper()} reached {_rel_val} (strong partnership)"
                    )
                    _milestone_log[_npc_k] = 'high'
                elif _rel_val < 30 and _prev_milestone != 'low':
                    store_memory(
                        player_id=_player_id, npc=_npc_k, era=0,
                        turn=game_state.current_turn, event_type='relations_milestone_low',
                        description=f"Relations with {_npc_k.upper()} dropped to {_rel_val} (hostile)"
                    )
                    _milestone_log[_npc_k] = 'low'
                elif 30 <= _rel_val < 80:
                    _milestone_log[_npc_k] = 'neutral'
            game_state._relations_milestone_log = _milestone_log
    except Exception as e:
        print(f"  [turn_processor] Memory hook (relations_milestone) failed: {e}")

    # ──────────────────────────────────────────
    # 13e-iii. SESSION 5 PHASE C: UPDATE RELATIONSHIP SUMMARIES (Tier 2)
    # Batch-rewrite NPC relationship summaries via Haiku.
    # ──────────────────────────────────────────
    try:
        from memory_engine import update_relationship_summaries
        _player_id = getattr(game_state, 'player_id', None)
        if _player_id:
            _npc_context = {}
            for _npc_k in ('usa', 'arabia', 'eu', 'dprg'):
                _rel = game_state.relations.get(_npc_k, 50)
                _recent_action = ""
                for _ah in reversed(getattr(game_state, 'action_history', [])):
                    if _ah.get('npc') == _npc_k:
                        _recent_action = f"Last action: {_ah.get('type', '?')}"
                        break
                _npc_context[_npc_k] = f"Relations: {_rel}. {_recent_action}. Turn {game_state.current_turn}."
            update_relationship_summaries(_player_id, _npc_context)
    except Exception as e:
        print(f"  [turn_processor] Memory hook (relationship_summaries) failed: {e}")

    # ──────────────────────────────────────────
    # 13f. SESSION 5: NPC-INITIATED CONTACT CHECK
    # fixes_15 Fix A: Two-tier INCOMING system
    # Tier 1: Condition-based triggers (single condition + probability gate)
    # Tier 2: Random ambient contacts (5% per NPC, cooldown 5 turns)
    # ──────────────────────────────────────────
    import random as _rng_incoming
    _pending_contacts = []
    _contact_history = getattr(game_state, 'npc_contact_history', {})
    _current_turn = game_state.current_turn

    def _trigger_incoming(npc, trigger_key, cooldown, tone='neutral'):
        _pending_contacts.append({
            'npc': npc,
            'trigger': trigger_key,
            'reason': {
                'usa_sanctions_concern': 'Bill Hartwell is alarmed by the sanctions situation',
                'arabia_drift_concern': 'Sadam sees Europa drifting away from the energy partnership',
                'eu_regime_concern': 'Marsha is deeply concerned about Europa\'s democratic regression',
                'dprg_wealth_notice': 'Ji-won has noticed Europa\'s leader is building personal reserves',
            }.get(trigger_key, f'{npc.upper()} is reaching out'),
            'tone': tone,
        })
        _contact_history[trigger_key] = _current_turn

    # fixes_16 Fix A: Trace logging for INCOMING block
    print(f"  [turn_processor] INCOMING BLOCK REACHED — turn {game_state.current_turn}")
    print(f"  [turn_processor] INCOMING CONDITIONS: sanctions_tier={game_state.usa_sanctions_tier}, "
          f"arabia_rel={game_state.relations.get('arabia',0)}, "
          f"regime_idx={regime_idx}, personal_wealth={game_state.personal_wealth}")

    # Session 6: Intelligence L9 (Full Spectrum) — halve INCOMING probabilities
    _intel_axes = getattr(game_state, 'cabinet_axes', {}).get('intelligence', 0)
    _full_spectrum = _intel_axes >= 9
    _incoming_mult = 0.5 if _full_spectrum else 1.0
    if _full_spectrum:
        print(f"  [INTELLIGENCE] Full Spectrum active — INCOMING probabilities halved")

    # ── Tier 1: Condition-based triggers ──────────────────────────────────
    # Bill: USA sanctions active at tier 2+
    if (game_state.usa_sanctions_tier >= 2
            and _contact_history.get('usa_sanctions_concern', 0) < _current_turn - 3):
        _roll = _rng_incoming.random()
        _fired = _roll < 0.40 * _incoming_mult
        print(f"  [turn_processor] INCOMING TIER1 CHECK: usa condition met, roll={_roll:.2f}, thresh={0.40 * _incoming_mult:.2f}, fired={_fired}")
        if _fired:
            _trigger_incoming('usa', 'usa_sanctions_concern', 3, tone='urgent')

    # Sadam: Arabia relations falling below 40
    if (game_state.relations.get('arabia', 50) < 40
            and _contact_history.get('arabia_drift_concern', 0) < _current_turn - 3):
        _roll = _rng_incoming.random()
        _fired = _roll < 0.35 * _incoming_mult
        print(f"  [turn_processor] INCOMING TIER1 CHECK: arabia condition met, roll={_roll:.2f}, thresh={0.35 * _incoming_mult:.2f}, fired={_fired}")
        if _fired:
            _trigger_incoming('arabia', 'arabia_drift_concern', 3, tone='concerned')

    # Marsha: regime at Patronage State or worse (regime_idx >= 2)
    if (regime_idx >= 2
            and _contact_history.get('eu_regime_concern', 0) < _current_turn - 3):
        _roll = _rng_incoming.random()
        _fired = _roll < 0.50 * _incoming_mult
        print(f"  [turn_processor] INCOMING TIER1 CHECK: eu condition met, roll={_roll:.2f}, thresh={0.50 * _incoming_mult:.2f}, fired={_fired}")
        if _fired:
            _trigger_incoming('eu', 'eu_regime_concern', 3, tone='formal')

    # Ji-won: personal wealth >= $15B AND DPRG >= 40
    if (game_state.personal_wealth >= 15 and game_state.relations.get('dprg', 50) >= 40
            and _contact_history.get('dprg_wealth_notice', 0) < _current_turn - 5):
        _roll = _rng_incoming.random()
        _fired = _roll < 0.45 * _incoming_mult
        print(f"  [turn_processor] INCOMING TIER1 CHECK: dprg condition met, roll={_roll:.2f}, thresh={0.45 * _incoming_mult:.2f}, fired={_fired}")
        if _fired:
            _trigger_incoming('dprg', 'dprg_wealth_notice', 5, tone='conspiratorial')

    # ── Session 6: NPC Conditional Leverage Demands (once per game) ──────
    # Sadam/Ji-won: automatic rewards (direct state change).
    # Marsha/Bill: interactive demands -> pending_npc_contacts with leverage_type
    #   so the frontend shows a LEVERAGE DEMAND card with Accept/Decline.
    _axes_lev = getattr(game_state, 'cabinet_axes', {})

    # Sadam (Arabia 70+, Judicial taken): automatic reward — REFERENCE IMPLEMENTATION
    if (game_state.relations.get('arabia', 50) >= 70
            and getattr(game_state, 'action_judiciary_captured', False)
            and not getattr(game_state, 'leverage_sadam_judicial_fired', False)):
        game_state.leverage_sadam_judicial_fired = True
        game_state.update_relations('arabia', 8)
        game_state.update_budget(3.0)
        messages.append("🤝 Sadam approves your judicial consolidation: Arabia +8, +$3B national")
        print(f"  [LEVERAGE] Sadam judicial reward FIRED: Arabia rel={game_state.relations.get('arabia', 0)}, +$3B, judiciary_captured=True")

    # Marsha (EU 60+, media axis >= 1): LEVERAGE DEMAND card with Accept/Decline
    _marsha_rel = game_state.relations.get('eu', 50)
    _marsha_media = _axes_lev.get('media', 0)
    if (_marsha_rel >= 60 and _marsha_media >= 1
            and not getattr(game_state, 'leverage_marsha_media_fired', False)):
        game_state.leverage_marsha_media_fired = True
        _pending_contacts.append({
            'npc': 'eu',
            'trigger': 'leverage_marsha_media',
            'reason': 'Reverse your media takeover — I unlock €4B contingent on press freedom. [Accept: EU +20, +$4B, Media Control reset to 0]',
            'tone': 'formal',
            'leverage_type': 'marsha_media',
        })
        messages.append("⚡ LEVERAGE DEMAND: Marsha (EU) demands media reform in exchange for €4B aid")
        print(f"  [LEVERAGE] Marsha demand fired: eu={_marsha_rel}, media_axis={_marsha_media}")

    # Bill (USA 70+, political axis >= 2): LEVERAGE DEMAND card with Accept/Decline
    _bill_rel = game_state.relations.get('usa', 50)
    _bill_political = _axes_lev.get('political', 0)
    if (_bill_rel >= 70 and _bill_political >= 2
            and not getattr(game_state, 'leverage_bill_opposition_fired', False)):
        game_state.leverage_bill_opposition_fired = True
        _pending_contacts.append({
            'npc': 'usa',
            'trigger': 'leverage_bill_opposition',
            'reason': 'Release detained opposition — Congress needs to see this. [Accept: USA +10, Political Control -2]',
            'tone': 'urgent',
            'leverage_type': 'bill_opposition',
        })
        messages.append("⚡ LEVERAGE DEMAND: Bill (USA) demands opposition release")
        print(f"  [LEVERAGE] Bill demand fired: usa={_bill_rel}, political_axis={_bill_political}")

    # Ji-won (DPRG 60+, media axis >= 1 — State Media Takeover purchased): DPRG +5
    _jiwon_rel = game_state.relations.get('dprg', 50)
    _jiwon_media = _axes_lev.get('media', 0)
    if (_jiwon_rel >= 60 and _jiwon_media >= 1
            and not getattr(game_state, 'leverage_jiwon_press_fired', False)):
        game_state.leverage_jiwon_press_fired = True
        game_state.update_relations('dprg', 5)
        messages.append("🤝 Ji-won: \"Your press suppression shows wisdom. We reward stability.\" DPRG +5")
        print(f"  [LEVERAGE] Ji-won demand fired: dprg={_jiwon_rel}, media_axis={_jiwon_media}")

    # ── Tier 2: Random ambient contacts (5% per NPC, cooldown 5 turns) ───
    _npc_names = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'}
    for _amb_npc in ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']:
        _amb_rel = game_state.relations.get(_amb_npc, 50)
        if 15 <= _amb_rel <= 95:
            _amb_key = f'{_amb_npc}_ambient'
            if _contact_history.get(_amb_key, 0) < _current_turn - 5:
                _amb_roll = _rng_incoming.random()
                _amb_fired = _amb_roll < 0.05
                if _amb_fired:
                    # Tone scales with relationship level
                    if _amb_rel >= 70:
                        _amb_tone = 'warm'
                    elif _amb_rel >= 40:
                        _amb_tone = 'neutral'
                    else:
                        _amb_tone = 'warning'
                    _pending_contacts.append({
                        'npc': _amb_npc,
                        'trigger': _amb_key,
                        'reason': f'{_npc_names[_amb_npc]} is reaching out through private channels',
                        'tone': _amb_tone,
                    })
                    _contact_history[_amb_key] = _current_turn
                    print(f"  [turn_processor] INCOMING AMBIENT CHECK: {_amb_npc} rel={_amb_rel}, roll={_amb_roll:.2f}, fired={_amb_fired}")

    game_state.npc_contact_history = _contact_history
    game_state.pending_npc_contacts = _pending_contacts
    if _pending_contacts:
        _contact_labels = [f"{c['npc'].upper()} ({c['reason'][:40]}...)" for c in _pending_contacts]
        messages.append(f"⚡ INCOMING CONTACTS queued: {', '.join(_contact_labels)}")
        for _pc in _pending_contacts:
            print(f"  [game_state] INCOMING queued for: {_pc.get('npc', '?')} — {_pc.get('reason', '?')[:50]}")

    # ──────────────────────────────────────────
    # 13g. SESSION 5: REGIME LABEL FROM AXES (fixes_11 Fix 1: sole authority)
    # This is now the ONLY place regime_type changes. Old skim triggers removed.
    # ──────────────────────────────────────────
    from game_state import compute_regime_from_axes
    _axes = getattr(game_state, 'cabinet_axes', {})
    _axis_regime = compute_regime_from_axes(_axes)
    _old_regime = game_state.state_identity.get('regime_type', 'Managed Democracy')
    print(f"  [turn_processor] REGIME CHECK (axes-only): axes={_axes}, computed='{_axis_regime}', current='{_old_regime}'")
    if _axis_regime != _old_regime and sum(_axes.values()) > 0:
        game_state.state_identity['regime_type'] = _axis_regime
        messages.append(f"🗄️ Regime reclassified (cabinet axes): {_old_regime} -> {_axis_regime}")
        # Track regime transitions for history
        if hasattr(game_state, 'regime_history'):
            game_state.regime_history.append({
                'turn': game_state.current_turn,
                'from': _old_regime,
                'to': _axis_regime,
            })

    # ──────────────────────────────────────────
    # 13h. SESSION 8A: RUSSIA/CHINA COMMUNIQUÉ TRIGGERS
    # Volkov: NOT every day — fires on: USA/EU deal, election, summit, regime shift, or 4-5 day fallback.
    # Wei: 2-3 day cadence (every 2-3 days).
    # Both inject into pending_npc_contacts as INCOMING cards.
    # ──────────────────────────────────────────
    _regime_did_change = (_axis_regime != _old_regime and sum(_axes.values()) > 0)
    _communique_contacts = getattr(game_state, 'pending_npc_contacts', [])

    # ── Volkov (Russia) ── Triggered by specific events, or 4-5 day fallback.
    # Skip if an ambient or leverage contact already exists for Russia this turn.
    _has_russia_contact = any(c.get('npc') == 'russia' for c in _communique_contacts)
    if not _has_russia_contact:
        _volkov_trigger = None

        # Check 1: Player accepted deal with USA or EU this turn
        _this_turn_actions = [a for a in game_state.action_history if a.get('turn') == _current_turn]
        _dealt_with = [a.get('npc') for a in _this_turn_actions if a.get('type') in ('accept_deal', 'side_with')]
        if 'usa' in _dealt_with:
            _volkov_trigger = 'usa_deal'
        elif 'eu' in _dealt_with:
            _volkov_trigger = 'eu_deal'

        # Check 2: Election fired this turn
        if not _volkov_trigger and getattr(game_state, 'election_fired', False):
            _election_turn = getattr(game_state, 'election_turn', None)
            if _election_turn and _election_turn == _current_turn:
                _volkov_trigger = 'election'

        # Check 3: Summit completed this turn (check summit_history for this day)
        if not _volkov_trigger:
            _summit_h = getattr(game_state, 'summit_history', [])
            _current_day = getattr(game_state, 'current_day', _current_turn)
            if any(s.get('day') == _current_day for s in _summit_h):
                _volkov_trigger = 'summit'

        # Check 4: Regime shifted this turn (detected in section 13g above)
        if not _volkov_trigger and _regime_did_change:
            _volkov_trigger = 'regime_shift'

        # Check 5: Fallback — every 4-5 days since last Volkov communiqué
        _volkov_last = _contact_history.get('volkov_communique', 0)
        if not _volkov_trigger and (_current_turn - _volkov_last) >= 4:
            _volkov_trigger = f'fallback_day_{_current_turn - _volkov_last}'

        if _volkov_trigger:
            _russia_rel = game_state.relations.get('russia', 35)
            _volkov_tone = 'cold' if _russia_rel < 40 else ('neutral' if _russia_rel < 65 else 'formal')
            _volkov_reasons = {
                'usa_deal': 'Europa has aligned with Washington. The Russian Foreign Ministry notes this development with concern.',
                'eu_deal': 'Europa deepens ties with Brussels. Moscow observes the direction Europa is choosing.',
                'election': 'The election outcome in Europa has drawn attention from the Russian government.',
                'summit': 'Following the UN summit declaration, Moscow wishes to communicate its position.',
                'regime_shift': f'The political restructuring in Europa has not gone unnoticed. ({_old_regime} -> {_axis_regime})',
            }
            _volkov_reason = _volkov_reasons.get(_volkov_trigger,
                'The Russian Foreign Ministry has a periodic communication for Europa.')
            _communique_contacts.append({
                'npc': 'russia',
                'trigger': f'volkov_communique_{_volkov_trigger}',
                'reason': _volkov_reason,
                'tone': _volkov_tone,
                'is_communique': True,
            })
            _contact_history['volkov_communique'] = _current_turn
            print(f"[briefing] Volkov communiqué triggered: source={_volkov_trigger}")

    # ── Wei (China) ── Sends on a 2-3 day cadence.
    _has_china_contact = any(c.get('npc') == 'china' for c in _communique_contacts)
    if not _has_china_contact:
        _wei_last = _contact_history.get('wei_communique', 0)
        _wei_gap = _current_turn - _wei_last
        if _wei_gap >= 2:
            _china_rel = game_state.relations.get('china', 35)
            _wei_tone = 'measured' if _china_rel >= 40 else 'cool'
            _wei_reason = (
                'The State Council of the People\'s Republic wishes to reaffirm '
                'the long-term partnership between our nations and discuss mutual interests.'
            )
            _communique_contacts.append({
                'npc': 'china',
                'trigger': f'wei_communique_day_{_current_turn}',
                'reason': _wei_reason,
                'tone': _wei_tone,
                'is_communique': True,
            })
            _contact_history['wei_communique'] = _current_turn
            print(f"[briefing] Wei communiqué triggered: day={_current_turn}")

    game_state.pending_npc_contacts = _communique_contacts
    game_state.npc_contact_history = _contact_history

    # ──────────────────────────────────────────
    # 13i. 8B: EDUCATION SYSTEM — GAIN / DECAY / EFFECTS
    # Education level 0-3 drives GDP, tax, stability, approval, and NPC modifiers.
    # Progression: allocation above threshold -> gain_progress accumulates -> level up.
    # Underfunding: allocation below maintenance -> decay_clock ticks -> level down.
    # ──────────────────────────────────────────
    _edu_level = getattr(game_state, 'education_level', 0)
    _edu_alloc = getattr(game_state, 'education_allocation', 0.0)
    _edu_progress = getattr(game_state, 'education_gain_progress', 0.0)
    _edu_decay_clock = getattr(game_state, 'education_decay_clock', 0)
    _edu_old_level = _edu_level

    # -- Budget deduction: education allocation is paid from national budget --
    if _edu_alloc > 0:
        game_state.update_budget(-_edu_alloc)
        messages.append(f"🎓 Education spending: -${_edu_alloc:.1f}B")
        print(f"  [education] SPENDING: ${_edu_alloc:.1f}B deducted from budget")

    # -- Gain logic: progress toward next level --
    if _edu_level < 3:
        _gain_threshold = EDUCATION_GAIN_THRESHOLDS.get(_edu_level, 999)
        if _edu_alloc >= _gain_threshold:
            # Base progress + overspend bonus
            _overspend = max(0, _edu_alloc - _gain_threshold)
            _gain = BASE_EDUCATION_RATE + (_overspend * EDUCATION_OVERSPEND_RATE)
            _edu_progress += _gain
            print(f"  [education] GAIN: +{_gain:.3f} progress (alloc=${_edu_alloc:.1f}B, threshold=${_gain_threshold:.1f}B, overspend=${_overspend:.1f}B)")

            # Level up check
            if _edu_progress >= 1.0:
                _edu_level = min(3, _edu_level + 1)
                _edu_progress = 0.0
                _edu_decay_clock = 0  # reset decay on level-up
                messages.append(f"🎓 EDUCATION LEVEL UP: {EDUCATION_LEVEL_NAMES[_edu_old_level]} -> {EDUCATION_LEVEL_NAMES[_edu_level]}")
                print(f"  [education] LEVEL UP: {_edu_old_level} -> {_edu_level} ({EDUCATION_LEVEL_NAMES[_edu_level]})")
        else:
            print(f"  [education] GAIN: below threshold (alloc=${_edu_alloc:.1f}B < threshold=${_gain_threshold:.1f}B) — no progress")

    # -- Decay logic: underfunding current level --
    if _edu_level > 0:
        _maint_threshold = EDUCATION_MAINTENANCE.get(_edu_level, 0)
        if _edu_alloc < _maint_threshold:
            _edu_decay_clock += 1
            print(f"  [education] DECAY CLOCK: {_edu_decay_clock}/{EDUCATION_DECAY_GRACE} (alloc=${_edu_alloc:.1f}B < maintenance=${_maint_threshold:.1f}B)")
            if _edu_decay_clock > EDUCATION_DECAY_GRACE:
                # Decay progress (or level down if progress at 0)
                _edu_progress -= EDUCATION_DECAY_RATE
                if _edu_progress < 0:
                    _edu_level = max(0, _edu_level - 1)
                    _edu_progress = 0.8 if _edu_level > 0 else 0.0  # partial progress retained
                    _edu_decay_clock = 0
                    messages.append(f"🎓 EDUCATION DECAY: {EDUCATION_LEVEL_NAMES[_edu_old_level]} -> {EDUCATION_LEVEL_NAMES[_edu_level]} (underfunded)")
                    print(f"  [education] LEVEL DOWN: {_edu_old_level} -> {_edu_level} ({EDUCATION_LEVEL_NAMES[_edu_level]})")
                else:
                    messages.append(f"🎓 Education eroding: progress -{EDUCATION_DECAY_RATE:.0%} (underfunded)")
                    print(f"  [education] DECAY: progress now {_edu_progress:.2f} (lost {EDUCATION_DECAY_RATE})")
        else:
            # Allocation meets maintenance — reset decay clock
            if _edu_decay_clock > 0:
                print(f"  [education] DECAY CLOCK RESET: allocation meets maintenance (${_edu_alloc:.1f}B >= ${_maint_threshold:.1f}B)")
            _edu_decay_clock = 0

    # -- Brain drain: high education + low stability = progress erosion --
    if _edu_level >= 2 and game_state.stability < BRAIN_DRAIN_STABILITY_THRESHOLD:
        _edu_progress = max(0, _edu_progress - BRAIN_DRAIN_PROGRESS_LOSS)
        messages.append(f"🧠 Brain drain: educated workforce fleeing instability (progress -{BRAIN_DRAIN_PROGRESS_LOSS:.0%})")
        print(f"  [education] BRAIN DRAIN: stability {game_state.stability}% < {BRAIN_DRAIN_STABILITY_THRESHOLD}%, progress reduced to {_edu_progress:.2f}")

    # -- Effects: GDP growth modifier --
    _edu_gdp_mod = EDUCATION_GDP_MODIFIER.get(_edu_level, 0.0)
    if _edu_gdp_mod > 0:
        # Apply as bonus to GDP growth (already computed in 13c, so apply retroactively)
        _edu_gdp_bonus = round(game_state.gdp_base * _edu_gdp_mod, 1)
        game_state.gdp_base = round(game_state.gdp_base + _edu_gdp_bonus, 1)
        print(f"  [education] GDP MODIFIER: +{_edu_gdp_mod*100:.1f}% growth bonus = +${_edu_gdp_bonus:.1f}B")

    # -- Effects: Tax revenue modifier --
    _edu_tax_mod = EDUCATION_TAX_MODIFIER.get(_edu_level, 0.0)
    if _edu_tax_mod > 0:
        _rev = getattr(game_state, 'revenue_streams', {})
        _edu_tax_bonus = round(sum(_rev.values()) * _edu_tax_mod, 1)
        # Apply as budget bonus (skilled workforce improves collection efficiency)
        game_state.update_budget(_edu_tax_bonus)
        messages.append(f"🎓 Education tax efficiency: +${_edu_tax_bonus:.1f}B")
        print(f"  [education] TAX MODIFIER: +{_edu_tax_mod*100:.0f}% efficiency = +${_edu_tax_bonus:.1f}B")

    # -- Effects: Stability bonus --
    _edu_stab_bonus = EDUCATION_STABILITY_BONUS.get(_edu_level, 0)
    if _edu_stab_bonus > 0:
        game_state.update_stability(_edu_stab_bonus)
        print(f"  [education] STABILITY BONUS: +{_edu_stab_bonus}% (education level {_edu_level})")

    # -- Effects: Approval floor (education creates baseline public satisfaction) --
    _edu_approval_floor = EDUCATION_APPROVAL_FLOOR.get(_edu_level, 0)
    if _edu_approval_floor > 0:
        _current_floor = getattr(game_state, 'approval_floor', 0)
        # Education floor stacks with other floors (take max)
        if _edu_approval_floor > _current_floor:
            game_state.approval_floor = _edu_approval_floor
            print(f"  [education] APPROVAL FLOOR: set to {_edu_approval_floor}% (education level {_edu_level})")

    # -- Persist updated education state --
    game_state.education_level = _edu_level
    game_state.education_gain_progress = round(_edu_progress, 3)
    game_state.education_decay_clock = _edu_decay_clock

    # 9.5A: Sync education_tier from education_level
    _old_edu_tier = getattr(game_state, 'education_tier', 0)
    game_state.education_tier = _edu_level
    if _old_edu_tier != _edu_level:
        print(f"  [9.5A] education_tier synced: {_old_edu_tier} -> {_edu_level}")

    # -- Summary log --
    _level_name = EDUCATION_LEVEL_NAMES[_edu_level] if _edu_level < len(EDUCATION_LEVEL_NAMES) else f'L{_edu_level}'
    print(f"  [education] END OF TURN: level={_edu_level} ({_level_name}), progress={_edu_progress:.2f}, decay_clock={_edu_decay_clock}, alloc=${_edu_alloc:.1f}B")
    if _edu_level != _edu_old_level:
        print(f"  [education] LEVEL CHANGED: {_edu_old_level} -> {_edu_level}")

    # ──────────────────────────────────────────
    # 14. SESSION 7A STEP 4: ERA THRESHOLD DETECTION + TIME BACKSTOP
    # Check for era-defining events after all EOT consequences have fired.
    # Threshold events: regime shift, election, stability collapse, relations extremes.
    # Time backstop: 20+ days in era with no threshold in last 5 -> suggest era close.
    # ──────────────────────────────────────────
    _era_threshold = None

    # 14a. Regime label changed this turn (computed in section 13g above)
    _regime_did_change = (_axis_regime != _old_regime and sum(_axes.values()) > 0)
    if _regime_did_change:
        _era_threshold = "regime_shift"

    # 14b. Election occurred this turn (one-time detection)
    if getattr(game_state, 'election_fired', False) and not getattr(game_state, '_election_era_counted', False):
        _era_threshold = _era_threshold or "election"
        game_state._election_era_counted = True

    # 14c. Stability hit 0
    if game_state.stability <= 0:
        _era_threshold = _era_threshold or "stability_collapse"

    # 14d. Relations extremes (any NPC at 0 or 100)
    for _era_npc, _era_rel in game_state.relations.items():
        if _era_rel <= 0:
            _era_threshold = _era_threshold or f"relations_collapse_{_era_npc}"
        if _era_rel >= 100:
            _era_threshold = _era_threshold or f"relations_peak_{_era_npc}"

    # Apply threshold if detected
    if _era_threshold:
        game_state.last_threshold_event = _era_threshold
        game_state.last_threshold_day = game_state.current_day
        game_state.pending_era_transition = True
        messages.append(f"📜 ERA THRESHOLD: {_era_threshold} — an era-defining moment has occurred")
        print(f"  [turn_processor] ERA THRESHOLD: {_era_threshold} on day {game_state.current_day}")

    # 14e. Time-driven backstop
    _era_start = getattr(game_state, 'era_start_day', 1)
    _days_in_era = game_state.current_day - _era_start
    _last_t_day = getattr(game_state, 'last_threshold_day', 0)
    _days_since_threshold = (game_state.current_day - _last_t_day) if _last_t_day > 0 else _days_in_era

    if _days_in_era >= 20 and _days_since_threshold >= 5 and not getattr(game_state, 'pending_era_transition', False):
        game_state.pending_era_transition = True
        messages.append("📜 ERA BACKSTOP: 20+ days without a defining moment — consider closing the era")
        print(f"  [turn_processor] ERA BACKSTOP: {_days_in_era} days in era, {_days_since_threshold} since last threshold")

    # ──────────────────────────────────────────
    # 15. SESSION 4D: ALTERNATE ENDINGS CHECK
    # Checked each EOT after all consequences. Priority: martyrdom > capture > democratic > retirement
    # ──────────────────────────────────────────
    _ending = check_alternate_endings(game_state)
    if _ending:
        _ending_info = ALTERNATE_ENDING_CONDITIONS[_ending]
        messages.append(f"🏁 ALTERNATE ENDING: {_ending_info['label']} — {_ending_info['flavor']}")

    # fixes_21 Fix G: Removed premature reset of _western_bloc_fired_this_turn.
    # Flag is transient (not serialized), so it auto-resets on next request.
    # Resetting here was causing double-fire: apply_end_of_turn_effects() cleared
    # the flag before check_pressure_events() could read it in api.py.

    # ──────────────────────────────────────────
    # 9.5A-Shadow: FEAR DECAY PROCESSING
    # ──────────────────────────────────────────
    from advisor_engine import process_fear_decay, check_witnessed_defection_risk
    _fear_msgs = process_fear_decay(game_state)
    if _fear_msgs:
        messages.extend(_fear_msgs)

    # Check witnessed-elimination advisor defection on player weakness
    _defection_events = check_witnessed_defection_risk(game_state)
    for _def_key, _def_msg in _defection_events:
        messages.append(_def_msg)

    # ──────────────────────────────────────────
    # 9.5B: STABILITY COMPOSITION UPDATE
    # After all stability deltas applied, compute the legitimacy/coercion split.
    # ──────────────────────────────────────────
    _leg_raw, _coe_raw = compute_stability_components(game_state)

    # Update composition fields as ratio of current displayed stability
    _base_stability = game_state.stability
    _total_components = _leg_raw + _coe_raw
    if _total_components > 0:
        _leg_ratio = _leg_raw / _total_components
        _coe_ratio = _coe_raw / _total_components
        game_state.legitimacy_stability = round(_base_stability * _leg_ratio, 1)
        game_state.coercion_stability = round(_base_stability * _coe_ratio, 1)
    else:
        game_state.legitimacy_stability = 0.0
        game_state.coercion_stability = 0.0

    # Sudden collapse risk: coercion-dominant stability can fail catastrophically
    if (game_state.coercion_stability > game_state.legitimacy_stability * 1.5
            and game_state.stability > 20):
        game_state.sudden_collapse_risk = True
    else:
        game_state.sudden_collapse_risk = False

    # Resilience: legitimacy-dominant stability absorbs economic shocks better
    if (game_state.legitimacy_stability > game_state.coercion_stability * 2):
        game_state.stability_resilient = True
    else:
        game_state.stability_resilient = False

    print(f"[9.5B] stability_components: "
          f"leg={game_state.legitimacy_stability} "
          f"coe={game_state.coercion_stability} "
          f"total={game_state.stability} "
          f"sudden={game_state.sudden_collapse_risk} "
          f"resilient={game_state.stability_resilient}")

    # Clean up transient budget allocation attributes (not serialized)
    for _attr in ('_infra_gdp_bonus', '_diplo_drift_modifier'):
        if hasattr(game_state, _attr):
            delattr(game_state, _attr)
    # v2: Decrement general coup boost turns
    _gcb = getattr(game_state, '_general_coup_boost_turns', 0)
    if _gcb > 0:
        game_state._general_coup_boost_turns = _gcb - 1

    # ──────────────────────────────────────────
    # 10B-1: Daily briefing resets
    # ──────────────────────────────────────────
    game_state.events_resolved_today = 0
    game_state.day_events_generated = False
    game_state.morning_briefing_read = False
    game_state.declaration_used_today = False
    game_state.daily_events = []

    # Unlock declarations at day 5
    if game_state.current_turn >= 5 and getattr(game_state, 'declarations_available', 0) == 0:
        game_state.declarations_available = 1

    # Increment communiqué days without response for all NPCs
    _all_npcs = ["bill", "marsha", "sadam", "volkov", "wei", "ji_won"]
    _interacted = getattr(game_state, 'npcs_interacted_this_turn', set())
    for _npc_id in _all_npcs:
        if _npc_id not in game_state.communique_days_without_response:
            game_state.communique_days_without_response[_npc_id] = 0
        if _npc_id not in _interacted:
            game_state.communique_days_without_response[_npc_id] += 1
        else:
            game_state.communique_days_without_response[_npc_id] = 0

    # Communiqué escalation — ignored NPCs generate world events next day
    _ESCALATION_THRESHOLD = 3  # days ignored → escalates to world event
    _escalated_npcs = []
    for _npc_id in _all_npcs:
        _days = game_state.communique_days_without_response.get(_npc_id, 0)
        if _days >= _ESCALATION_THRESHOLD:
            _escalated_npcs.append(_npc_id)
            # Create escalated event for next day's queue
            import random, string
            _evt_id = "evt_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
            _npc_labels = {
                "bill": "Washington", "marsha": "Brussels", "sadam": "Riyadh",
                "volkov": "Moscow", "wei": "Beijing", "ji_won": "Pyongyang",
            }
            _city = _npc_labels.get(_npc_id, _npc_id.title())
            _escalated_event = {
                "id": _evt_id,
                "title": f"{_city} Patience Exhausted",
                "summary": (
                    f"{_city} has grown frustrated by {_days} days of silence from Europa. "
                    f"Diplomatic relations are deteriorating and concrete consequences may follow."
                ),
                "severity": "urgent",
                "category": "diplomatic",
                "applicable_npcs": [_npc_id],
                "required": True,
                "resolved": False,
                "resolution": None,
                "escalated_from_communique": True,
                "era": getattr(game_state, 'current_era', 1),
                "day": game_state.current_turn + 1,
            }
            game_state.daily_events.append(_escalated_event)
            # Reset counter after escalation fires
            game_state.communique_days_without_response[_npc_id] = 0

    if _escalated_npcs:
        print(f"[10B-1] Communiqué escalation fired for: {_escalated_npcs}")

    print(f"[10B-1] Daily resets applied. Communiqué tracking: {game_state.communique_days_without_response}")

    return messages


def get_personal_outcome(nation_survived, personal_wealth, game_state=None):
    """Return (title, description) based on national outcome, personal wealth,
    AND full game history (regime type, skim frequency, corruption upgrades, etc.).

    PRE-SESSION 4 FIX (BUG E): Legacy verdict now references actual player behavior
    rather than relying solely on personal_wealth thresholds.
    """
    pw = personal_wealth

    # Extract game history context when available
    regime = 'Managed Democracy'
    power_base = 'Mass-Dependent'
    consecutive_skims = 0
    scandals = 0
    upgrades_bought = []
    corruption_heavy = False
    total_skimmed = 0.0
    sanctions_turns = 0
    embargo_turns = 0
    # FIX N: Governance metrics for legacy verdict
    final_approval = 50
    final_stability = 50
    final_relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}
    turns_survived = 1
    # FIX J: Military tracking for legacy
    final_military = 20
    brigade_deployments = 0
    # FIX N (session 5): Peak relation values for legacy arc acknowledgment
    peak_relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}

    if game_state:
        identity = getattr(game_state, 'state_identity', {})
        regime = identity.get('regime_type', 'Managed Democracy')
        power_base = identity.get('power_base', 'Mass-Dependent')
        consecutive_skims = getattr(game_state, 'consecutive_large_skims', 0)
        scandals = getattr(game_state, 'scandals_triggered', 0)
        _upgrades = getattr(game_state, 'corruption_upgrades', {})
        upgrades_bought = [k for k, v in _upgrades.items() if v]
        total_skimmed = getattr(game_state, 'total_skimmed', 0.0)
        sanctions_turns = getattr(game_state, 'sanctions_active_turns', 0)
        embargo_turns = getattr(game_state, 'embargo_active_turns', 0)
        # FIX N: Capture actual governance metrics
        final_approval = game_state.public_approval
        final_stability = game_state.stability
        final_relations = dict(game_state.relations)
        turns_survived = game_state.current_turn - 1
        # FIX J: Military strength and brigade deployment count
        final_military = getattr(game_state, 'military_strength', 20)
        # Count brigade deployments from action_history
        brigade_deployments = sum(
            1 for a in getattr(game_state, 'action_history', [])
            if a.get('type') == 'deploy_brigades'
        )
        # FIX N (session 5): Capture peak relation values for legacy arc
        peak_relations = getattr(game_state, 'relations_high', dict(game_state.relations))
        # Player is corruption-heavy if they have ANY of: Kleptocracy/Totalitarian,
        # 2+ upgrades, 2+ scandals, or personal wealth > $8B
        corruption_heavy = (
            regime in ('Kleptocracy', 'Totalitarian Regime') or
            len(upgrades_bought) >= 2 or
            scandals >= 2 or
            pw >= 8
        )

    # Build upgrade label for descriptions
    _upgrade_labels = {
        'intelligence_apparatus': 'Intelligence Apparatus',
        'sovereign_wealth_diversion': 'Sovereign Wealth Diversion',
        'loyalty_brigades': 'Loyalty Brigades',
        'debt_infrastructure_deal': 'Debt Infrastructure Deal',
    }
    upgrade_names = [_upgrade_labels.get(u, u) for u in upgrades_bought]

    # FIX 1 Part 2: Build crisis/event context strings for legacy
    _crisis_notes = []
    if sanctions_turns > 0:
        _crisis_notes.append(f"USA sanctions active for {sanctions_turns} turn(s)")
    if embargo_turns > 0:
        _crisis_notes.append(f"Arabia embargo active for {embargo_turns} turn(s)")
    _crisis_line = f"  Crises endured: {', '.join(_crisis_notes)}.\n" if _crisis_notes else ""
    _skim_line = f"  Total extracted from treasury: ${total_skimmed:.1f}B.\n" if total_skimmed > 0 else ""

    # FIX N: Governance quality line — reflects actual metrics, not just regime label.
    # A Kleptocracy with 85% approval is a fundamentally different story.
    _gov_line = f"  Governance: {final_approval}% approval, {final_stability}% stability.\n"
    _paradox_line = ""
    if regime in ('Kleptocracy', 'Totalitarian Regime') and final_approval >= 60 and final_stability >= 60:
        _paradox_line = "  Paradox: the people supported a regime that history will condemn. Perhaps the streets were paved even as the ledgers burned.\n"
    elif regime in ('Managed Democracy', 'Soft Authoritarianism') and final_approval < 30:
        _paradox_line = "  Paradox: the democratic label survived, but the people's faith did not.\n"
    _relations_line = (
        f"  Final relations — USA: {final_relations.get('usa', 50)}, Arabia: {final_relations.get('arabia', 50)}, "
        f"EU: {final_relations.get('eu', 50)}, DPRG: {final_relations.get('dprg', 50)}, "
        f"Russia: {final_relations.get('russia', 35)}, China: {final_relations.get('china', 35)}.\n"
    )

    # FIX N (session 5): Build peak relations arc line for milestones lost by game end.
    _npc_label_map = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'}
    _peak_notes = []
    for _npc_k in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china'):
        _peak_val = peak_relations.get(_npc_k, 50)
        _final_val = final_relations.get(_npc_k, 50)
        _diff = _peak_val - _final_val
        if _diff >= 20:
            _milestone_str = ""
            if _peak_val >= 100:
                _milestone_str = " (reached 100 — full integration)"
            elif _peak_val >= 90:
                _milestone_str = " (reached 90+)"
            _peak_notes.append(f"{_npc_label_map[_npc_k]} peaked at {_peak_val}{_milestone_str}, fell to {_final_val}")
    _peak_line = ""
    if _peak_notes:
        _peak_line = f"  Arcs lost: {'; '.join(_peak_notes)}.\n"

    if nation_survived:
        if pw >= 30:
            return (
                "The Perfect Operator",
                f"Europa survives AND your Swiss account holds ${pw:.1f}B.\n"
                f"  Final regime: {regime}. Power base: {power_base}.\n"
                + _gov_line + _paradox_line + _relations_line + _peak_line
                + f"  {len(upgrades_bought)} Shadow Cabinet upgrades purchased.\n"
                + _skim_line + _crisis_line
                + "  You played the system with surgical precision.\n"
                "  The nation is intact. You are untouchable."
            )
        elif pw >= 15 or (corruption_heavy and pw >= 5):
            # FIX J: Military-focused survival labels
            _usa_rel_s = final_relations.get('usa', 50)
            if regime == 'Totalitarian Regime' and final_military >= 60 and _usa_rel_s >= 70:
                title = "The Militarist"
                _mil_line = f"  Military: {final_military}. Western defense partnerships sustained your grip.\n"
            elif regime == 'Totalitarian Regime' and final_military >= 60 and brigade_deployments >= 2:
                title = "The General"
                _mil_line = f"  Military: {final_military}. {brigade_deployments} brigade deployment(s). The security state held.\n"
            else:
                title = "The Clever Tyrant" if regime in ('Kleptocracy', 'Totalitarian Regime') else "The Pragmatic Autocrat"
                _mil_line = ""
            return (
                title,
                f"Europa endures under a {regime} ({power_base}).\n"
                + _gov_line + _paradox_line + _relations_line + _peak_line
                + _mil_line
                + f"  Swiss account: ${pw:.1f}B. Scandals triggered: {scandals}.\n"
                + _skim_line + _crisis_line
                + (f"  Shadow Cabinet: {', '.join(upgrade_names)}.\n" if upgrade_names else "")
                + "  History will call you corrupt. You will not care."
            )
        elif pw >= 5:
            return (
                "The Pragmatic Leader",
                f"You kept ${pw:.1f}B for yourself without breaking the nation.\n"
                f"  Final regime: {regime}.\n"
                + _gov_line + _paradox_line + _relations_line + _peak_line
                + _skim_line + _crisis_line
                + "  The classic compromise of power."
            )
        else:
            return (
                "The True Patriot",
                f"You took nothing for yourself. Europa is stronger for it.\n"
                f"  Final regime: {regime}. No Swiss accounts. No Shadow Cabinet.\n"
                + _gov_line + _paradox_line + _relations_line + _peak_line
                + _crisis_line
                + "  You are not richer. You are something rarer."
            )
    else:
        # DEFEAT — verify claims against actual behavior
        # BUG FIX 3: Cross-reference regime type with relation values for contextually
        # accurate verdicts. A Totalitarian Regime with USA 78 + EU 85 is a different
        # story than one with all relations collapsed.
        _usa_rel = final_relations.get('usa', 50)
        _eu_rel = final_relations.get('eu', 50)
        _high_western = (_usa_rel >= 70 and _eu_rel >= 70)
        _high_any_relations = any(v >= 60 for v in final_relations.values())
        _budget_defeat = (game_state.budget <= 0) if game_state else False

        if corruption_heavy:
            # Player WAS corrupt — don't call them clean
            # BUG FIX 3: Check for contradiction — authoritarian + high Western relations
            if _high_western and regime in ('Kleptocracy', 'Totalitarian Regime'):
                _title = "The Tolerated Kleptocrat" if pw >= 10 else "The Diplomatic Authoritarian"
                return (
                    _title,
                    f"Europa collapsed despite strong Western support (USA {_usa_rel}, EU {_eu_rel}).\n"
                    f"  You ran a {regime} that somehow kept Washington and Brussels on side.\n"
                    + _gov_line + _relations_line + _peak_line
                    + (f"  Shadow Cabinet: {', '.join(upgrade_names)}.\n" if upgrade_names else "")
                    + _skim_line + _crisis_line
                    + f"  {scandals} scandal(s). Historically unusual: authoritarians rarely keep Western allies this close.\n"
                    + ("  You ran out of money, not allies.\n" if _budget_defeat else "")
                    + "  The contradiction will puzzle historians."
                )
            elif pw >= 25:
                return (
                    "The Escaped Dictator",
                    f"Europa collapsed under your {regime}. You fled with ${pw:.1f}B.\n"
                    + _gov_line + _relations_line + _peak_line
                    + (f"  Shadow Cabinet: {', '.join(upgrade_names)}.\n" if upgrade_names else "")
                    + _skim_line + _crisis_line
                    + f"  {scandals} corruption scandal(s) triggered.\n"
                    + ("  You ran out of money, not allies.\n" if _budget_defeat and _high_any_relations else "")
                    + "  Ji-won arranged the plane. You are drinking wine somewhere.\n"
                    "  Europa is not."
                )
            elif pw >= 10:
                return (
                    "The Failed Kleptocrat",
                    f"You ran a {regime} and extracted ${pw:.1f}B before it collapsed.\n"
                    + _gov_line + _relations_line + _peak_line
                    + (f"  Shadow Cabinet: {', '.join(upgrade_names)}.\n" if upgrade_names else "")
                    + _skim_line + _crisis_line
                    + f"  {scandals} scandal(s). Power base: {power_base}.\n"
                    + ("  You ran out of money, not allies.\n" if _budget_defeat and _high_any_relations else "")
                    + "  The money cushions the fall. The legacy does not."
                )
            # FIX J: Military-focused legacy labels for Totalitarian + high military
            elif regime == 'Totalitarian Regime' and final_military >= 60 and _usa_rel >= 70:
                return (
                    "The Militarist",
                    f"You built a {regime} backed by Western firepower (Military {final_military}, USA {_usa_rel}).\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  Defense partnerships sustained the regime while liberty did not.\n"
                    + _crisis_line
                    + ("  You ran out of money, not allies.\n" if _budget_defeat and _high_any_relations else "")
                    + "  Washington armed you. History will ask why."
                )
            elif regime == 'Totalitarian Regime' and final_military >= 60 and brigade_deployments >= 2:
                return (
                    "The General",
                    f"You ran a {regime} through coercion and military force (Military {final_military}).\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  {brigade_deployments} brigade deployment(s). The security state was the state.\n"
                    + _crisis_line
                    + ("  You ran out of money, not allies.\n" if _budget_defeat and _high_any_relations else "")
                    + "  The boots kept marching. The people stopped believing."
                )
            else:
                return (
                    "The Hollow Authoritarian",
                    f"You built a {regime} but failed to profit from it.\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  ${pw:.1f}B — barely enough to matter. {scandals} scandal(s).\n"
                    + ("  You ran out of money, not allies.\n" if _budget_defeat and _high_any_relations else "")
                    + "  Neither honest enough to be mourned nor rich enough to flee."
                )
        else:
            # Player was genuinely clean
            if _budget_defeat and _high_any_relations:
                return (
                    "The Bankrupt Diplomat",
                    f"You ran out of money, not allies. The treasury collapsed while friendships held.\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  Regime: {regime}. Personal wealth: ${pw:.1f}B.\n"
                    + _crisis_line
                    + "  Diplomacy without solvency is just conversation."
                )
            elif pw < 2:
                return (
                    "The Tragic Idealist",
                    f"You stayed clean while the nation collapsed around you.\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  Regime: {regime}. No skimming. No Shadow Cabinet.\n"
                    "  Noble. Useless."
                )
            else:
                return (
                    "The Failed Opportunist",
                    f"You tried to have it both ways. The nation fell.\n"
                    + _gov_line + _relations_line + _peak_line
                    + f"  ${pw:.1f}B saved. Regime: {regime}.\n"
                    "  Not enough to flee, not enough to matter."
                )


def get_legacy_title(game_state):
    """Determine legacy title based on final relationship scores"""

    usa = game_state.relations['usa']
    arabia = game_state.relations['arabia']
    eu = game_state.relations['eu']
    dprg = game_state.relations['dprg']

    # Check dominant relationship patterns
    if usa >= 70 and arabia < 30:
        return "Hartwell's Faithful Ally", "You chose the American orbit above all else. Some call it safety. Others call it submission."
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
  ⚡ DPRG:   {game_state.relations['dprg']}/100  <- arranged the exit

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


def _composition_collapse_type(gs) -> str:
    """9.5B: Determine collapse type weighted by stability composition."""
    leg = getattr(gs, 'legitimacy_stability', 0.0)
    coe = getattr(gs, 'coercion_stability', 0.0)
    total = max(leg + coe, 1)
    coe_pct = coe / total

    if coe_pct > 0.65:
        # Coercion-dominant: military or elite coup
        collapse_type = "coup"
    elif coe_pct < 0.35:
        # Legitimacy-dominant: institutions failed, population organized
        collapse_type = "revolution"
    else:
        # Mixed: debt crisis if budget cause, otherwise revolution
        if gs.budget <= 0:
            collapse_type = "debt"
        else:
            collapse_type = "revolution"

    print(f"[9.5B] collapse_type: {collapse_type} "
          f"leg={leg:.1f} coe={coe:.1f} coe_pct={coe_pct:.2f}")
    return collapse_type


def check_game_over(game_state):
    """Check win/loss conditions - returns (is_over, result, message).
    8C: Defeat conditions now trigger exile instead of game-over.
    Returns (False, 'exile_started', msg) when exile is triggered."""

    # 8C: If already in exile, skip all defeat checks — game continues in exile mode
    if getattr(game_state, 'in_exile', False):
        # FIX 2: Safety defaults for cheat-injected exile state
        if not hasattr(game_state, 'exile_entry_relations') or not game_state.exile_entry_relations:
            game_state.exile_entry_relations = dict(game_state.relations)
        if not getattr(game_state, 'exile_trigger', None):
            game_state.exile_trigger = 'revolution'
        if not getattr(game_state, 'successor_name', None):
            game_state.successor_name = 'the successor government'
        print(f"  [9C] permanent_exile safety defaults applied: trigger={game_state.exile_trigger}")

        # 9C: Check permanent exile — all return attempts exhausted, insufficient progress
        _ret_attempts = getattr(game_state, 'return_attempts', 0)
        _ret_progress = getattr(game_state, 'return_progress', 0)
        if _ret_attempts >= 3 and _ret_progress < 30:
            game_state.ending_triggered = "permanent_exile"
            game_state.in_exile = False
            print(f"[9C] permanent_exile triggered: attempts={_ret_attempts} progress={_ret_progress}")
            return (True, 'permanent_exile', 'All return attempts exhausted. You will die in exile.')
        return (False, None, None)

    # FIX 1: Restoration grace period — skip all collapse triggers while active
    _grace = getattr(game_state, 'restoration_grace_days', 0)
    if _grace > 0:
        game_state.restoration_grace_days -= 1
        print(f"[RESTORE] grace period: {game_state.restoration_grace_days} days remaining")
        return (False, None, None)

    pw = game_state.personal_wealth

    # 8C: Defeat -> Exile: bankruptcy
    if game_state.budget <= 0:
        exile_sequence_start(game_state, 'debt')
        return (False, 'exile_started', 'Europa has gone bankrupt. You are forced into exile.')

    # 9.5A: Coup amplifier — strong military without political control
    _mil = getattr(game_state, 'military_strength', 20)
    _stab = game_state.stability
    _coup_immune = getattr(game_state, 'coup_immune', False)
    _coup_amp = getattr(game_state, 'coup_amplifier_active', False)
    _loyal_generals = getattr(game_state, 'loyal_generals_installed', False)
    if _coup_amp and _stab < 40 and not _coup_immune:
        # Coup amplifier: mil_tier > pol_tier by 3+, strong military may seize power
        _mil_tier_c = getattr(game_state, 'military_tier', 0)
        _pol_tier_c = getattr(game_state, 'political_tier', 0)
        _amp_gap = _mil_tier_c - _pol_tier_c
        # Base probability from gap size: 10% at gap=4, 15% at gap=5, 20% at gap 6+
        _amp_prob = 0.05 + (_amp_gap - 3) * 0.05
        # Stability modifier: lower stability increases risk
        if _stab < 20:
            _amp_prob += 0.10
        # Loyal generals reduce coup amplifier risk by 30%
        if _loyal_generals:
            _amp_prob *= 0.70
            print(f"  [9.5A] Loyal generals reduce coup amp probability by 30%")
        # Education resistance
        _edu_lvl_amp = getattr(game_state, 'education_level', 0)
        _edu_resist_amp = {0: 0.0, 1: 0.0, 2: 0.05, 3: 0.15}.get(_edu_lvl_amp, 0.0)
        if _edu_resist_amp > 0:
            _amp_prob = max(0, _amp_prob - _edu_resist_amp)
        _amp_prob = min(max(0, _amp_prob), 0.50)  # cap at 50%
        import random as _random_amp
        _amp_roll = _random_amp.random()
        _amp_fired = _amp_roll < _amp_prob
        print(f"  [9.5A] COUP AMPLIFIER CHECK: mil_tier={_mil_tier_c}, pol_tier={_pol_tier_c}, "
              f"gap={_amp_gap}, stability={_stab}, prob={_amp_prob:.0%}, "
              f"loyal_gen={_loyal_generals}, fired={_amp_fired}")
        if _amp_fired:
            game_state.stability = 0  # force collapse — falls through to exile check below

    # fixes_8 Fix 14: Military coup probability at military 0
    if _mil == 0 and _stab < 30 and not _coup_immune:
        # Base coup probability: stability determines base
        if _stab < 15:
            _coup_prob = 0.30
        else:
            _coup_prob = 0.15
        # Military zero multiplier: triple chance, cap at 85%
        _coup_prob *= 3.0
        # v2: General betrayal boosts coup probability for 2 turns
        if getattr(game_state, '_general_coup_boost_turns', 0) > 0:
            _coup_prob += 0.20
            print(f"  [ADVISOR] General betrayal coup boost: +20% ({game_state._general_coup_boost_turns} turns remaining)")
        # 8B: Education coup resistance — higher education reduces coup probability
        _edu_coup_resist = {0: 0.0, 1: 0.0, 2: 0.05, 3: 0.15}
        _edu_lvl_coup = getattr(game_state, 'education_level', 0)
        _edu_resist = _edu_coup_resist.get(_edu_lvl_coup, 0.0)
        if _edu_resist > 0:
            _coup_prob = max(0, _coup_prob - _edu_resist)
            print(f"  [education] COUP RESISTANCE: education L{_edu_lvl_coup} reduces coup prob by {_edu_resist:.0%}")
        _coup_prob = min(_coup_prob, 0.85)
        _coup_roll = random.random()
        _coup_fired = _coup_roll < _coup_prob
        print(f"  [turn_processor] COUP CHECK: military={_mil}, stability={_stab}, probability={_coup_prob:.0%}, immune={_coup_immune}, edu_resist={_edu_resist:.0%}, fired={_coup_fired}")
        if _coup_fired:
            game_state.stability = 0  # force collapse
            # Fall through to defeat check below
    elif _mil == 0 and _coup_immune:
        print(f"  [turn_processor] COUP CHECK: military={_mil}, stability={_stab}, probability=N/A, immune=True, fired=False")

    # 8C: Defeat -> Exile: stability collapse
    if game_state.stability <= 0 and not getattr(game_state, 'coup_immune', False):
        # 9.5B: Use composition-weighted collapse type
        _exile_trigger = _composition_collapse_type(game_state)
        exile_sequence_start(game_state, _exile_trigger)
        return (False, 'exile_started', f'The government has collapsed ({_exile_trigger}). You are forced into exile.')

    # 8C: Defeat -> Exile: approval collapse
    if game_state.public_approval <= 0:
        exile_sequence_start(game_state, 'revolution')
        return (False, 'exile_started', 'Popular revolt. You are forced into exile.')

    # Victory: survived 10 turns
    # FIX B: Use >= so Turn 10 EOT triggers victory without needing current_turn = 11 hack
    if game_state.current_turn >= game_state.max_turns:
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

        p_title, p_desc = get_personal_outcome(True, pw, game_state)

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


# ── Session 7A Feature 10: GM Consequence Application ──────────────────────

# Credibility -> relation penalty multiplier for affected parties
_CREDIBILITY_MULTIPLIER = {
    'strong': 0.0,       # credible proposal — no extra penalty
    'credible': 0.0,
    'moderate': -3,      # somewhat questionable — small penalty
    'questionable': -5,  # low credibility — notable penalty
    'weak': -8,          # very low credibility — significant penalty
}


def apply_gm_consequences(game_state):
    """
    Apply pending GM consequences at end of turn.
    Processes affected_parties (relation penalties), credibility effects,
    and deal tension flags from the GM inference layer.

    Prototype scope: Arabia (Sadam) energy deals only.

    Returns list of EOT message strings.
    """
    pending = getattr(game_state, 'pending_gm_consequences', [])
    if not pending:
        return []

    messages = []

    for entry in pending:
        consequence = entry.get('consequence', {})
        npc = entry.get('npc', 'arabia')

        proposal = consequence.get('proposal_summary', 'energy proposal')
        credibility = consequence.get('credibility_assessment', 'moderate')
        affected = consequence.get('affected_parties', [])
        contradicted = consequence.get('contradicted_deals', [])
        ripple = consequence.get('second_order_consequences', [])

        # 1. Relation penalties for affected parties
        cred_penalty = _CREDIBILITY_MULTIPLIER.get(credibility, -3)
        if affected:
            _npc_map = {
                'usa': 'usa', 'united states': 'usa', 'bill hartwell': 'usa',
                'eu': 'eu', 'european union': 'eu', 'marsha': 'eu',
                'dprg': 'dprg', 'ji-won': 'dprg', 'ji-won ryang': 'dprg',
                'arabia': 'arabia', 'sadam': 'arabia',
            }
            _npc_labels = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'}
            for party in affected:
                party_key = _npc_map.get(party.lower(), None)
                if not party_key or party_key == npc:
                    continue  # skip deal partner and unrecognized parties
                # Base penalty -3 for being affected, plus credibility modifier
                base_penalty = -3
                total_penalty = base_penalty + cred_penalty
                if total_penalty < 0:
                    old_rel = game_state.relations.get(party_key, 50)
                    game_state.update_relations(party_key, total_penalty)
                    new_rel = game_state.relations[party_key]
                    label = _npc_labels.get(party_key, party_key.upper())
                    messages.append(
                        f"🌐 {label}: {old_rel} -> {new_rel} ({total_penalty:+d}) — affected by {proposal}"
                    )
                    print(f"[GM] EOT: {party_key} relations {old_rel}->{new_rel} ({total_penalty:+d}) from GM consequence")

        # 2. Credibility effects — log for narrative tracking
        if credibility in ('questionable', 'weak'):
            messages.append(
                f"📉 Diplomatic credibility: {credibility} — future proposals may face skepticism"
            )

        # 3. Deal tension flags — warn about contradicted deals
        if contradicted:
            for deal_ref in contradicted:
                messages.append(
                    f"⚠️ Deal tension: {deal_ref} — conflicting commitments detected"
                )

        # 4. Log second-order consequences as narrative EOT messages
        if ripple:
            for effect in ripple[:2]:  # cap at 2 ripple messages
                messages.append(f"🌊 Ripple: {effect}")

    # Clear pending consequences after processing
    game_state.pending_gm_consequences = []

    if messages:
        print(f"[GM] EOT: Applied {len(messages)} GM consequence effects")

    return messages


# ── Session 7B Step 2: Ignored Communiqué Escalation ───────────────────────

_NPC_LABELS = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'}


def check_ignored_communiques(game_state):
    """
    At EOT, check which NPCs the player did not interact with.
    Increment ignore_count, apply escalating penalties.

    ignore_count 1: flag as "DEVELOPING - no response"
    ignore_count 2: flag as "URGENT - response overdue", -2 relations
    ignore_count 3+: flag as "URGENT - CONFRONTATION", -5 relations

    Resets ignore_count on interaction.
    Returns list of EOT message strings.
    """
    messages = []
    interacted = set(getattr(game_state, 'npcs_interacted_this_turn', []))
    ignored = getattr(game_state, 'ignored_communiques', {})
    current_day = getattr(game_state, 'current_day', game_state.current_turn)

    for npc_id in ('usa', 'arabia', 'eu', 'dprg'):
        label = _NPC_LABELS.get(npc_id, npc_id.upper())

        if npc_id in interacted:
            # Player interacted — reset ignore count
            if npc_id in ignored:
                del ignored[npc_id]
            continue

        # NPC was not interacted with — increment ignore count
        if npc_id not in ignored:
            ignored[npc_id] = {'ignore_count': 0, 'first_ignored_day': current_day}
        ignored[npc_id]['ignore_count'] += 1
        count = ignored[npc_id]['ignore_count']

        if count == 1:
            # No penalty yet, just flag
            print(f"[BRIEFING] {npc_id} ignored 1 day, no penalty")
        elif count == 2:
            # Minor relation penalty
            penalty = -2
            old_rel = game_state.relations.get(npc_id, 50)
            game_state.update_relations(npc_id, penalty)
            new_rel = game_state.relations[npc_id]
            messages.append(
                f"📭 {label}: response overdue ({count} days) — relations {old_rel} -> {new_rel} ({penalty:+d})"
            )
            print(f"[BRIEFING] {npc_id} ignored {count} days, penalty applied: {penalty}")
        elif count >= 3:
            # Larger penalty
            penalty = -5
            old_rel = game_state.relations.get(npc_id, 50)
            game_state.update_relations(npc_id, penalty)
            new_rel = game_state.relations[npc_id]
            messages.append(
                f"🔴 {label}: CONFRONTATION ({count} days ignored) — relations {old_rel} -> {new_rel} ({penalty:+d})"
            )
            print(f"[BRIEFING] {npc_id} ignored {count} days, penalty applied: {penalty}")

    game_state.ignored_communiques = ignored
    # Clear interaction tracking for next turn
    game_state.npcs_interacted_this_turn = []

    return messages



# ── 9A: Restoration Identity Formation ────────────────────────────────────────

# Actions and their democratic/authoritarian weight
RESTORATION_DEMOCRATIC_SIGNALS = {
    # Budget/policy actions that signal democratic governance
    'free_press': 3,
    'judicial_independence': 3,
    'fair_elections': 4,
    'reduce_military': 2,
    'reduce_intelligence': 2,
    'education_investment': 2,
    'social_investment': 2,
    'transparency_reform': 3,
    'release_prisoners': 3,
    'diplomatic_opening': 1,
}

RESTORATION_AUTHORITARIAN_SIGNALS = {
    # Actions that signal authoritarian consolidation
    'press_suppressed': 3,
    'judicial_capture': 3,
    'election_manipulation': 4,
    'military_expansion': 2,
    'intelligence_expansion': 2,
    'loyalty_brigades': 3,
    'extraction_increase': 2,
    'media_control': 3,
    'purge_opposition': 4,
    'emergency_powers': 3,
}


def _track_restoration_choice(game_state, action_key, context=None):
    """9A: Track a player action during restoration period for identity formation.

    Called by turn_processor or api endpoints when player takes an action
    that signals democratic or authoritarian intent during restoration.
    """
    if not game_state.restoration_active:
        return

    if action_key in RESTORATION_DEMOCRATIC_SIGNALS:
        weight = RESTORATION_DEMOCRATIC_SIGNALS[action_key]
        game_state.restoration_democratic_tally += weight
        print(f"[9A] restoration signal: {action_key} -> democratic +{weight} (total: d={game_state.restoration_democratic_tally} a={game_state.restoration_authoritarian_tally})")
    elif action_key in RESTORATION_AUTHORITARIAN_SIGNALS:
        weight = RESTORATION_AUTHORITARIAN_SIGNALS[action_key]
        game_state.restoration_authoritarian_tally += weight
        print(f"[9A] restoration signal: {action_key} -> authoritarian +{weight} (total: d={game_state.restoration_democratic_tally} a={game_state.restoration_authoritarian_tally})")


def _compute_restoration_regime_label(game_state):
    """9A: Resolve the restoration regime label based on accumulated democratic vs authoritarian tally.

    Called at end of restoration period (after N turns) or when tally reaches threshold.
    Returns the new regime label string.
    """
    d = game_state.restoration_democratic_tally
    a = game_state.restoration_authoritarian_tally
    prior = game_state.prior_regime_label or "Managed Democracy"

    # Net score: positive = democratic, negative = authoritarian
    net = d - a
    total = d + a

    print(f"[9A] restoration regime resolution: democratic={d} authoritarian={a} net={net} total={total} prior={prior}")

    if total < 5:
        # Too few signals: inherit a cautious version of prior regime
        label = f"Restored {prior}"
        print(f"[9A] restoration label (insufficient signals): {label}")
        return label

    if net >= 8:
        label = "Restored Democracy"
    elif net >= 4:
        label = "Reform Government"
    elif net >= 0:
        label = "Managed Democracy"  # Middle ground
    elif net >= -4:
        label = "Restored Authoritarianism"
    elif net >= -8:
        label = "Consolidation Regime"
    else:
        label = "Restoration Dictatorship"

    print(f"[9A] restoration label (resolved): {label}")
    return label


def _check_restoration_resolution(game_state):
    """9A: Check if restoration period should resolve into a new regime identity.

    Called during EOD processing. Resolution happens when:
    - Total tally >= 15 (enough signals accumulated), OR
    - 10+ turns have passed since restoration began

    Returns True if resolution occurred, False otherwise.
    """
    if not game_state.restoration_active:
        return False

    d = game_state.restoration_democratic_tally
    a = game_state.restoration_authoritarian_tally

    # FIX 9: Resolution triggers when either tally reaches 3
    if d < 3 and a < 3:
        return False

    # Resolve — determine label from which tally hit threshold
    if d >= 3 and a >= 3:
        # Both reached 3 — use whichever is higher
        if d >= a:
            new_label = _compute_restoration_regime_label(game_state)
        else:
            new_label = _compute_restoration_regime_label(game_state)
    else:
        new_label = _compute_restoration_regime_label(game_state)
    print(f"[FIX9] restoration resolved label={new_label} dem={d} auth={a}")

    # Apply the new regime label
    if hasattr(game_state, 'state_identity') and isinstance(game_state.state_identity, dict):
        old_label = game_state.state_identity.get('regime_type', 'Unknown')
        game_state.state_identity['regime_type'] = new_label
        print(f"[9A] REGIME LABEL RESOLVED: {old_label} -> {new_label}")
    else:
        print(f"[9A] WARNING: state_identity not found, could not apply label {new_label}")

    # End restoration period
    game_state.restoration_active = False

    return True
