"""
Advisor Engine — Full 9-Archetype System (Revised v2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layered on top of Session 7C trust mechanics.
9 archetypes with stat distortion, competence/loyalty stats,
betrayal events, hire/dismiss/eliminate cycle, and gate-based pool.

v2 changes from v1:
  - Security Chief → Militia Commander (distinct role, Soft Auth+ gate)
  - Enforcer → Spy Chief (intel discount mechanic)
  - diplomatic_aide → diplomat (renamed, competence-based discount)
  - General, Propagandist now gated
  - Pool is dynamic (shows all eligible archetypes not on staff)
  - No staff cap (can hire all 9)
  - Trust starts at 75
  - Competence/loyalty/distortion_value randomized per archetype range
  - Budget distortion added for Oligarch
  - Education interaction with Propagandist distortion
"""

import random
import uuid

# ── Archetype Definitions (v2 spec-matching) ─────────────────────────────────

ADVISOR_ARCHETYPES = {
    'finance_minister': {
        'label': 'Finance Minister',
        'icon': '💵',
        'specialty': 'Economic',
        'competence_range': (55, 85),
        'loyalty_range': (45, 75),
        'distortion_stat': None,
        'distortion_range': None,
        'gate': None,  # always available
        'hire_cost_type': 'national',  # $0.5B national
        'hire_cost': 0.5,
        'haiku_voice': 'cautious, precise, "the numbers suggest fiscal exposure here", "this skim rate is not sustainable at current stability levels"',
    },
    'technocrat': {
        'label': 'Technocrat',
        'icon': '📊',
        'specialty': 'Economic',
        'competence_range': (60, 90),
        'loyalty_range': (50, 80),
        'distortion_stat': None,
        'distortion_range': None,
        'gate': None,
        'hire_cost_type': 'national',
        'hire_cost': 0.5,
        'haiku_voice': 'analytical, references efficiency and long-term returns, "the infrastructure ROI on this option is significantly better over 5 turns"',
    },
    'diplomat': {
        'label': 'Diplomat',
        'icon': '🤝',
        'specialty': 'Diplomatic',
        'competence_range': (55, 80),
        'loyalty_range': (60, 90),
        'distortion_stat': None,
        'distortion_range': None,
        'gate': None,
        'hire_cost_type': 'national',
        'hire_cost': 0.5,
        'haiku_voice': 'measured, relationship-focused, references NPC history and diplomatic precedent, "Marsha\'s position on this has softened since turn 3"',
    },
    'general': {
        'label': 'General',
        'icon': '⚔️',
        'specialty': 'Military',
        'competence_range': (50, 85),
        'loyalty_range': (40, 75),
        'distortion_stat': 'military_strength',
        'distortion_range': (5, 15),
        'gate': 'military_axis_4',
        'hire_cost_type': 'national',
        'hire_cost': 0.5,
        'haiku_voice': 'formal, strategic, "from a force posture perspective", subtly condescending about militia if both active, "irregular forces have their uses — they are not a substitute for doctrine"',
    },
    'propagandist': {
        'label': 'Propagandist',
        'icon': '📺',
        'specialty': 'Domestic',
        'competence_range': (40, 70),
        'loyalty_range': (50, 85),
        'distortion_stat': 'approval',
        'distortion_range': (5, 15),
        'gate': 'soft_authoritarianism',
        'hire_cost_type': 'personal',
        'hire_cost': 0.5,
        'haiku_voice': 'upbeat, spins everything, "public sentiment is responding well to the messaging", "the narrative is manageable"',
    },
    'militia_commander': {
        'label': 'Militia Commander',
        'icon': '🔒',
        'specialty': 'Domestic',
        'competence_range': (45, 75),
        'loyalty_range': (40, 70),
        'distortion_stat': 'stability',
        'distortion_range': (5, 10),
        'gate': 'soft_authoritarianism',
        'hire_cost_type': 'personal',
        'hire_cost': 0.5,
        'haiku_voice': 'blunt, contemptuous of due process, "there are faster ways to resolve this than courts", "the diplomat\'s approach is admirable — it won\'t work"',
    },
    'spy_chief': {
        'label': 'Spy Chief',
        'icon': '🕵️',
        'specialty': 'Intelligence',
        'competence_range': (70, 95),
        'loyalty_range': (30, 70),
        'distortion_stat': 'heat',
        'distortion_range': (5, 10),
        'gate': 'intel_axis_4',
        'hire_cost_type': 'national',
        'hire_cost': 1.0,
        'haiku_voice': 'oblique, precise, never wastes words, "the operational risk profile here suggests indirect approaches", "asset management is preferable to confrontation at this stage"',
    },
    'oligarch': {
        'label': 'Oligarch',
        'icon': '💰',
        'specialty': 'Economic',
        'competence_range': (50, 75),
        'loyalty_range': (20, 50),
        'distortion_stat': 'heat_and_budget',  # special: two distortions
        'distortion_range': (5, 10),  # heat reduction
        'budget_distortion_range': (3, 8),  # budget inflation
        'gate': 'patronage_state',
        'hire_cost_type': 'personal',
        'hire_cost': 1.0,
        'haiku_voice': 'transactional, no sentiment, "what is the return on this arrangement", "the EU\'s conditions are an obstacle to efficient capital flows"',
    },
    'fixer': {
        'label': 'Fixer',
        'icon': '🎭',
        'specialty': 'Intelligence',
        'competence_range': (75, 95),
        'loyalty_range': (10, 40),
        'distortion_stat': 'heat',
        'distortion_range': (8, 15),
        'gate': 'political_axis_4',
        'hire_cost_type': 'personal',
        'hire_cost': 1.0,
        'haiku_voice': 'oblique, never direct, "there are ways to approach this that don\'t appear in any official record", "the paper trail is a choice"',
    },
}

_REGIME_ORDER = [
    'Managed Democracy',
    'Soft Authoritarianism',
    'Patronage State',
    'Kleptocracy',
    'Totalitarian Regime',
]

# ── Name Pools per Archetype (v2 spec-matching) ──────────────────────────────

ADVISOR_NAME_POOLS = {
    'finance_minister': {
        'first': ['Anton', 'Stefan', 'Pavel', 'Mirko', 'Luca'],
        'last': ['Novak', 'Bauer', 'Kolar', 'Horak', 'Varga']
    },
    'technocrat': {
        'first': ['Andrej', 'Tomáš', 'Jakub', 'Ondřej', 'Lukáš'],
        'last': ['Procházka', 'Novotný', 'Dvořák', 'Černý', 'Blažek']
    },
    'diplomat': {
        'first': ['Elena', 'Marta', 'Sofia', 'Katarina', 'Ivana'],
        'last': ['Kovač', 'Horvat', 'Babić', 'Tomić', 'Jurić']
    },
    'general': {
        'first': ['Aleksandar', 'Miloš', 'Dragan', 'Nemanja', 'Dejan'],
        'last': ['Đorđević', 'Stanković', 'Vasić', 'Ilić', 'Milošević']
    },
    'propagandist': {
        'first': ['Radovan', 'Goran', 'Miroslav', 'Dragan', 'Slavko'],
        'last': ['Božić', 'Knežević', 'Lukić', 'Đurić', 'Simić']
    },
    'militia_commander': {
        'first': ['Zoran', 'Branimir', 'Nebojša', 'Radoslav', 'Velimir'],
        'last': ['Čović', 'Krajišnik', 'Bošković', 'Tadić', 'Vuković']
    },
    'spy_chief': {
        'first': ['Viktor', 'Karel', 'Martin', 'Petr', 'Radek'],
        'last': ['Šimánek', 'Bureš', 'Kratochvíl', 'Kopecký', 'Sedláček']
    },
    'oligarch': {
        'first': ['Dmitri', 'Sergei', 'Boris', 'Vladimir', 'Igor'],
        'last': ['Volkov', 'Petrov', 'Sokolov', 'Kozlov', 'Lebedev']
    },
    'fixer': {
        'first': ['Mihai', 'Cristian', 'Bogdan', 'Andrei', 'Radu'],
        'last': ['Ionescu', 'Popescu', 'Popa', 'Constantin', 'Gheorghe']
    },
}


def _generate_name(archetype_key):
    """Generate a name from the archetype-specific pool."""
    pool = ADVISOR_NAME_POOLS.get(archetype_key)
    if pool:
        return f"{random.choice(pool['first'])} {random.choice(pool['last'])}"
    return f"Advisor {str(uuid.uuid4())[:4]}"


# ── Gate Eligibility ─────────────────────────────────────────────────────────

def is_advisor_eligible(archetype_key, game_state):
    """Check if an archetype is eligible given current game state.
    Returns (eligible: bool, condition_desc: str)."""
    arch = ADVISOR_ARCHETYPES.get(archetype_key)
    if not arch:
        return False, "unknown archetype"

    gate = arch.get('gate')
    if gate is None:
        return True, "always available"

    regime = game_state.state_identity.get('regime_type', 'Managed Democracy')

    if gate == 'military_axis_4':
        axes = getattr(game_state, 'cabinet_axes', {})
        mil_axis = axes.get('military', 0)
        eligible = mil_axis >= 4
        print(f"  [advisor] GATE CHECK: general — military_axis={mil_axis}")
        return eligible, "military axis >= 4"

    if gate == 'soft_authoritarianism':
        if regime not in _REGIME_ORDER:
            return False, "Soft Authoritarianism+"
        idx = _REGIME_ORDER.index(regime)
        gate_idx = _REGIME_ORDER.index('Soft Authoritarianism')
        return idx >= gate_idx, "Soft Authoritarianism+"

    if gate == 'intel_axis_4':
        axes = getattr(game_state, 'cabinet_axes', {})
        eligible = axes.get('intelligence', 0) >= 4
        return eligible, "intelligence axis >= 4"

    if gate == 'patronage_state':
        if regime not in _REGIME_ORDER:
            return False, "Patronage State+"
        idx = _REGIME_ORDER.index(regime)
        gate_idx = _REGIME_ORDER.index('Patronage State')
        return idx >= gate_idx, "Patronage State+"

    if gate == 'political_axis_4':
        axes = getattr(game_state, 'cabinet_axes', {})
        eligible = axes.get('political', 0) >= 4
        return eligible, "political axis >= 4"

    return False, "unknown gate"


# ── Advisor Object Creation ──────────────────────────────────────────────────

def create_advisor(archetype_key, game_state=None):
    """Create a new advisor object for the given archetype.
    Randomizes competence, loyalty, and distortion_value within archetype ranges."""
    arch = ADVISOR_ARCHETYPES.get(archetype_key)
    if not arch:
        return None

    name = _generate_name(archetype_key)
    comp_range = arch.get('competence_range', (50, 80))
    loy_range = arch.get('loyalty_range', (40, 70))
    competence = random.randint(comp_range[0], comp_range[1])
    loyalty = random.randint(loy_range[0], loy_range[1])

    # Distortion value
    distortion_value = 0
    budget_distortion_value = 0
    dist_range = arch.get('distortion_range')
    if dist_range:
        distortion_value = random.randint(dist_range[0], dist_range[1])
    # Oligarch has separate budget distortion
    budget_dist_range = arch.get('budget_distortion_range')
    if budget_dist_range:
        budget_distortion_value = random.randint(budget_dist_range[0], budget_dist_range[1])

    advisor = {
        'id': str(uuid.uuid4())[:8],
        'archetype': archetype_key,
        'name': name,
        'background': '',  # filled by Haiku on hire
        'competence': competence,
        'loyalty': loyalty,
        'trust': 75,  # v2: starts at 75
        'distortion_value': distortion_value,
        'budget_distortion_value': budget_distortion_value,
        'assigned_this_turn': False,
        'has_betrayed': False,
        'hire_day': getattr(game_state, 'current_day', 1) if game_state else 1,
        'icon': arch['icon'],
        'label': arch['label'],
    }
    print(f"  [advisor] Created: {name} ({archetype_key}) competence={competence} loyalty={loyalty}")
    return advisor


# ── Pool Generation (v2: dynamic, shows all eligible archetypes) ─────────────

def generate_advisor_pool(game_state):
    """Generate advisor pool. Reuse existing pool entries where possible —
    only create new advisor objects when an archetype becomes newly eligible."""
    hired = set()
    _advisors = getattr(game_state, 'advisors', {})
    if isinstance(_advisors, dict):
        for adv in _advisors.values():
            if isinstance(adv, dict) and 'archetype' in adv:
                hired.add(adv['archetype'])

    eliminated = set(getattr(game_state, 'advisors_eliminated', []))

    # Build lookup of existing pool by archetype
    existing_pool = {}
    for a in (getattr(game_state, 'advisor_pool', None) or []):
        if isinstance(a, dict) and a.get('archetype'):
            existing_pool[a['archetype']] = a

    new_pool = []
    reused = 0
    created = 0
    for arch_key in ADVISOR_ARCHETYPES:
        if arch_key in hired:
            continue
        if arch_key in eliminated:
            continue

        eligible, condition = is_advisor_eligible(arch_key, game_state)
        if not eligible:
            continue

        # Reuse existing pool entry if present
        if arch_key in existing_pool:
            new_pool.append(existing_pool[arch_key])
            reused += 1
        else:
            # Only create new advisor when archetype is newly eligible
            advisor = create_advisor(arch_key, game_state)
            if advisor:
                new_pool.append(advisor)
                created += 1
                print(f"  [advisor] POOL NEW: {advisor['name']} ({arch_key}) now available")

    print(f"  [ADVISOR_POOL] stable pool: {len(new_pool)} eligible, {reused} reused, {created} new")
    return new_pool


def check_gate_unlocks(game_state):
    """Check if any new archetypes have become eligible.
    Returns list of (archetype_key, condition) tuples for notification."""
    unlocked = []
    active_archetypes = set()
    _advisors = getattr(game_state, 'advisors', {})
    if isinstance(_advisors, dict):
        for adv in _advisors.values():
            if isinstance(adv, dict) and 'archetype' in adv:
                active_archetypes.add(adv['archetype'])

    eliminated = set(getattr(game_state, 'advisors_eliminated', []))
    pool_archetypes = set()
    for a in getattr(game_state, 'advisor_pool', []):
        if isinstance(a, dict) and 'archetype' in a:
            pool_archetypes.add(a['archetype'])

    for arch_key, arch in ADVISOR_ARCHETYPES.items():
        if arch_key in active_archetypes or arch_key in eliminated:
            continue
        if arch_key in pool_archetypes:
            continue
        if arch.get('gate') is None:
            continue  # always-available don't need unlock notification

        eligible, condition = is_advisor_eligible(arch_key, game_state)
        if eligible:
            unlocked.append((arch_key, condition))
            print(f"  [advisor] GATE UNLOCKED: {arch_key} now eligible (condition: {condition})")

    return unlocked


# ── Hire / Dismiss / Eliminate ───────────────────────────────────────────────

def hire_advisor(game_state, advisor_id):
    """Hire an advisor from the pool into staff roster.
    v2: No staff cap. Costs vary by archetype."""
    pool = getattr(game_state, 'advisor_pool', [])
    advisor = None
    for a in pool:
        if a['id'] == advisor_id:
            advisor = a
            break
    if not advisor:
        return False, "Advisor not found in pool"

    arch_key = advisor['archetype']
    arch = ADVISOR_ARCHETYPES.get(arch_key, {})
    cost_type = arch.get('hire_cost_type', 'national')
    cost = arch.get('hire_cost', 0.5)

    # Cost check
    if cost_type == 'personal':
        if game_state.personal_wealth < cost:
            return False, f"Need ${cost}B personal wealth to hire {arch.get('label', arch_key)}"
        game_state.personal_wealth = round(game_state.personal_wealth - cost, 1)
    else:
        if game_state.budget < cost:
            return False, f"Need ${cost}B national budget to hire {arch.get('label', arch_key)}"
        game_state.budget = round(game_state.budget - cost, 1)

    # Set hire fields
    advisor['trust'] = 75
    advisor['hire_day'] = getattr(game_state, 'current_day', 1)
    advisor['assigned_this_turn'] = False
    advisor['has_betrayed'] = False

    # Add to staff roster (keyed by archetype)
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        _advisors = {}
    _advisors[arch_key] = advisor
    game_state.advisors = _advisors

    # Remove from pool
    game_state.advisor_pool = [a for a in pool if a['id'] != advisor_id]

    cost_str = f"${cost}B {'personal' if cost_type == 'personal' else 'national'}"
    print(f"  [advisor] HIRED: {advisor['name']} ({arch_key}) competence={advisor['competence']} loyalty={advisor['loyalty']} trust=75")
    return True, f"Hired {advisor['name']} ({advisor['label']}) — {cost_str}"


def dismiss_advisor(game_state, advisor_key):
    """Dismiss an active advisor. Free. Archetype returns to hire pool
    with a fresh randomized character. Low-trust dismissal (trust < 30)
    has 20% chance of world event."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict) or advisor_key not in _advisors:
        return False, "Advisor not found"

    advisor = _advisors[advisor_key]
    old_trust = advisor.get('trust', 75)
    name = advisor.get('name', advisor_key)
    messages = []

    # Low-trust dismissal world event (20% chance)
    if old_trust < 30 and random.randint(1, 100) <= 20:
        game_state.update_approval(-3)
        messages.append("WORLD EVENT: Former official gives interview critical of administration. Approval -3%")

    # Remove from staff
    del _advisors[advisor_key]
    game_state.advisors = _advisors

    # Return archetype to pool with fresh randomized character
    new_advisor = create_advisor(advisor_key, game_state)
    if new_advisor:
        pool = getattr(game_state, 'advisor_pool', [])
        # Remove any existing instance of this archetype from pool
        pool = [a for a in pool if a.get('archetype') != advisor_key]
        pool.append(new_advisor)
        game_state.advisor_pool = pool

    event_str = f" — {messages[0]}" if messages else ""
    print(f"  [advisor] DISMISSED: {name} ({advisor_key}) trust={old_trust}")
    return True, f"Dismissed {name} ({advisor.get('label', advisor_key)}){event_str}"


def eliminate_advisor(game_state, advisor_key):
    """Permanently remove an advisor. Costs $2B personal wealth.
    Archetype does NOT return to pool — slot is gone forever.
    Archetype-specific consequences apply."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict) or advisor_key not in _advisors:
        return False, "Advisor not found"

    advisor = _advisors[advisor_key]

    # Cost check
    if game_state.personal_wealth < 2.0:
        return False, "Need $2B personal wealth to eliminate an advisor"
    game_state.personal_wealth = round(game_state.personal_wealth - 2.0, 1)

    # Remove from staff
    del _advisors[advisor_key]
    game_state.advisors = _advisors

    # Mark archetype as permanently eliminated (by archetype key)
    eliminated = getattr(game_state, 'advisors_eliminated', [])
    eliminated.append(advisor_key)
    game_state.advisors_eliminated = eliminated

    # Remove from pool too
    game_state.advisor_pool = [a for a in getattr(game_state, 'advisor_pool', []) if a.get('archetype') != advisor_key]

    # Archetype-specific consequences
    consequence = _apply_elimination_consequence(game_state, advisor)

    print(f"  [advisor] ELIMINATED: {advisor['name']} ({advisor_key}) — consequence: {consequence}")

    # Log
    log = getattr(game_state, 'advisor_actions_log', [])
    log.append({
        'day': getattr(game_state, 'current_day', 0),
        'advisor': advisor.get('name', advisor_key),
        'archetype': advisor_key,
        'action': 'elimination',
        'result': consequence,
    })
    game_state.advisor_actions_log = log

    # ── 9.5A-Shadow: Fear Effect on remaining advisors ──────────────────
    _current_day = getattr(game_state, 'current_day', 0)
    _old_elim_count = getattr(game_state, 'advisor_elimination_count', 0)
    _last_elim_day = getattr(game_state, 'advisor_elimination_last_day', 0)
    _days_since_last = _current_day - _last_elim_day if _last_elim_day > 0 else 999

    # Determine fear intensity based on repeat eliminations
    _is_repeat_2 = (_old_elim_count >= 1 and _days_since_last <= 10)
    _is_repeat_3 = (_old_elim_count >= 2 and _days_since_last <= 20)

    _loyalty_boost = 15
    _fear_window = 5
    if _is_repeat_2 or _is_repeat_3:
        _loyalty_boost = 25
        _fear_window = 7

    # Update elimination tracking
    game_state.advisor_elimination_count = _old_elim_count + 1
    game_state.advisor_elimination_last_day = _current_day

    # Apply fear to all remaining advisors
    _remaining = getattr(game_state, 'advisors', {})
    _fear_list = list(getattr(game_state, 'advisors_with_fear_bonus', []))
    _witnessed_list = list(getattr(game_state, 'advisors_witnessed_elimination', []))
    _chronic_list = list(getattr(game_state, 'advisors_chronically_fearful', []))

    for _rkey, _radv in _remaining.items():
        if not isinstance(_radv, dict):
            continue
        # Loyalty boost
        _old_loyalty = _radv.get('trust', 75)
        _radv['trust'] = min(100, _old_loyalty + _loyalty_boost)

        # Set fear bonus on advisor dict
        _radv['fear_bonus_active'] = True
        _radv['fear_start_day'] = _current_day
        _radv['fear_window'] = _fear_window

        # Track in lists
        if _rkey not in _fear_list:
            _fear_list.append(_rkey)
        if _rkey not in _witnessed_list:
            _witnessed_list.append(_rkey)

        # Chronically fearful for 2nd+ elimination within window
        if _is_repeat_2 and _rkey not in _chronic_list:
            _chronic_list.append(_rkey)
            # Competence degradation for chronically fearful (-10 permanent)
            _old_comp = _radv.get('competence', 60)
            _radv['competence'] = max(0, _old_comp - 10)
            print(f"  [9.5A-Shadow] {_rkey} now CHRONICALLY FEARFUL "
                  f"(competence {_old_comp} -> {_radv['competence']})")

        print(f"  [9.5A-Shadow] fear_effect: {_rkey} loyalty {_old_loyalty} -> {_radv['trust']}, "
              f"fear_window={_fear_window}d")

    game_state.advisors_with_fear_bonus = _fear_list
    game_state.advisors_witnessed_elimination = _witnessed_list
    game_state.advisors_chronically_fearful = _chronic_list
    game_state.advisors = _remaining

    _fear_msg = f"Fear effect: +{_loyalty_boost} loyalty, {_fear_window}d window"
    if _is_repeat_3:
        _fear_msg += " (3rd+ elimination — deeply unreliable)"
    elif _is_repeat_2:
        _fear_msg += " (repeat elimination — chronically fearful)"

    print(f"  [9.5A-Shadow] elimination #{_old_elim_count + 1}: "
          f"repeat_2={_is_repeat_2} repeat_3={_is_repeat_3} "
          f"remaining={len(_remaining)} fear_list={_fear_list}")

    return True, f"Eliminated {advisor['name']} ({advisor.get('label', advisor_key)}) — {consequence}. {_fear_msg}"


def _apply_elimination_consequence(game_state, advisor):
    """Apply archetype-specific elimination consequences. Returns description."""
    arch = advisor.get('archetype', '')

    if arch == 'technocrat':
        # EU -3
        game_state.update_relations('eu', -3, flat=True, source="technocrat elimination")
        return "EU -3 relations (loss of reformist signal)"

    if arch == 'diplomat':
        # EU -5, USA -5
        game_state.update_relations('eu', -5, flat=True, source="diplomat elimination")
        game_state.update_relations('usa', -5, flat=True, source="diplomat elimination")
        return "EU -5, USA -5 relations"

    if arch == 'general':
        # Military decay accelerates (-3/turn for 3 turns)
        game_state._general_elim_decay_turns = 3
        return "Military decay accelerates (-3/turn for 3 turns)"

    if arch == 'propagandist':
        # Approval display corrects to true value — one-time shock
        return "Approval display corrected to true value. Media credibility damaged."

    if arch == 'militia_commander':
        # Stability -5 one-time
        game_state.update_stability(-5)
        return "Stability -5 (loss of informal enforcement network)"

    if arch == 'spy_chief':
        # DPRG +3, Arabia +3, EU -8
        game_state.update_relations('dprg', 3, flat=True, source="spy chief elimination")
        game_state.update_relations('arabia', 3, flat=True, source="spy chief elimination")
        game_state.update_relations('eu', -8, flat=True, source="spy chief elimination")
        return "DPRG +3, Arabia +3, EU -8"

    if arch == 'oligarch':
        # No external consequences — deniable
        return "No external consequences — deniable"

    if arch == 'fixer':
        # DPRG +5, one active backchannel promise compromised
        game_state.update_relations('dprg', 5, flat=True, source="fixer elimination")
        _promises = getattr(game_state, 'active_promises', [])
        if _promises:
            return "DPRG +5. One active backchannel promise flagged as compromised."
        return "DPRG +5."

    if arch == 'finance_minister':
        # No external consequences — deniable
        return "No external consequences — deniable"

    # Default
    return "Inner circle instability."


# ── Stat Distortion (v2: randomized per advisor, education interaction) ──────

def get_displayed_approval(gs):
    """Get displayed approval with Propagandist distortion.
    Education level reduces Propagandist effectiveness."""
    distortion = 0
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return gs.public_approval
    for adv in _advisors.values():
        if not isinstance(adv, dict):
            continue
        if not adv.get('assigned_this_turn', False):
            continue
        arch = adv.get('archetype', '')
        if arch == 'propagandist':
            # Education reduces Propagandist effectiveness
            edu_level = getattr(gs, 'education_level', 0)
            edu_reduction = {0: 1.0, 1: 0.8, 2: 0.5, 3: 0.2}
            factor = edu_reduction.get(edu_level, 1.0)
            raw_dist = adv.get('distortion_value', 0)
            effective_dist = round(raw_dist * factor)
            # 9.5A-Shadow: fear reduces distortion by 50%
            if adv.get('fear_bonus_active', False):
                effective_dist = round(effective_dist * 0.5)
            distortion += effective_dist
    displayed = min(100, max(0, gs.public_approval + distortion))
    if distortion != 0:
        print(f"  [advisor] STAT DISTORTION: approval displayed={displayed} true={gs.public_approval} (source: propagandist)")
    return displayed


def get_displayed_stability(gs):
    """Get displayed stability with Militia Commander distortion."""
    distortion = 0
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return gs.stability
    for adv in _advisors.values():
        if not isinstance(adv, dict):
            continue
        if not adv.get('assigned_this_turn', False):
            continue
        if adv.get('archetype') == 'militia_commander':
            _dv = adv.get('distortion_value', 0)
            # 9.5A-Shadow: fear reduces distortion by 50%
            if adv.get('fear_bonus_active', False):
                _dv = round(_dv * 0.5)
            distortion += _dv
    displayed = min(100, max(0, gs.stability + distortion))
    if distortion != 0:
        print(f"  [advisor] STAT DISTORTION: stability displayed={displayed} true={gs.stability} (source: militia_commander)")
    return displayed


def get_displayed_military(gs):
    """Get displayed military strength with General distortion."""
    distortion = 0
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return getattr(gs, 'military_strength', 20)
    for adv in _advisors.values():
        if not isinstance(adv, dict):
            continue
        if not adv.get('assigned_this_turn', False):
            continue
        if adv.get('archetype') == 'general':
            _dv = adv.get('distortion_value', 0)
            # 9.5A-Shadow: fear reduces distortion by 50%
            if adv.get('fear_bonus_active', False):
                _dv = round(_dv * 0.5)
            distortion += _dv
    true_val = getattr(gs, 'military_strength', 20)
    displayed = min(100, max(0, true_val + distortion))
    if distortion != 0:
        print(f"  [advisor] STAT DISTORTION: military displayed={displayed} true={true_val} (source: general)")
    return displayed


def get_displayed_heat(gs):
    """Get displayed detection heat with Spy Chief / Oligarch / Fixer distortion.
    All three deflate heat (negative distortion)."""
    distortion = 0
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return getattr(gs, 'detection_heat', 0)
    for adv in _advisors.values():
        if not isinstance(adv, dict):
            continue
        if not adv.get('assigned_this_turn', False):
            continue
        arch = adv.get('archetype', '')
        if arch in ('spy_chief', 'oligarch', 'fixer'):
            _dv = adv.get('distortion_value', 0)
            # 9.5A-Shadow: fear reduces distortion by 50%
            if adv.get('fear_bonus_active', False):
                _dv = round(_dv * 0.5)
            distortion -= _dv
    true_val = getattr(gs, 'detection_heat', 0)
    displayed = min(100, max(0, true_val + distortion))
    if distortion != 0:
        sources = []
        for adv in _advisors.values():
            if isinstance(adv, dict) and adv.get('assigned_this_turn') and adv.get('archetype') in ('spy_chief', 'oligarch', 'fixer'):
                sources.append(adv['archetype'])
        print(f"  [advisor] STAT DISTORTION: heat displayed={displayed} true={true_val} (source: {', '.join(sources)})")
    return displayed


def get_displayed_budget(gs):
    """Get displayed budget with Oligarch distortion (inflates budget display)."""
    distortion = 0
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return gs.budget
    for adv in _advisors.values():
        if not isinstance(adv, dict):
            continue
        if not adv.get('assigned_this_turn', False):
            continue
        if adv.get('archetype') == 'oligarch':
            _dv = adv.get('budget_distortion_value', 0)
            # 9.5A-Shadow: fear reduces distortion by 50%
            if adv.get('fear_bonus_active', False):
                _dv = round(_dv * 0.5)
            distortion += _dv
    displayed = gs.budget + distortion
    if distortion != 0:
        print(f"  [advisor] STAT DISTORTION: budget displayed={displayed:.1f} true={gs.budget:.1f} (source: oligarch)")
    return displayed


def compute_all_distortions(gs):
    """Compute all stat distortions and return a dict for frontend serialization."""
    distortions = {}
    _advisors = getattr(gs, 'advisors', {})
    if not isinstance(_advisors, dict):
        return distortions

    for adv in _advisors.values():
        if not isinstance(adv, dict) or not adv.get('assigned_this_turn', False):
            continue
        arch = adv.get('archetype', '')
        dv = adv.get('distortion_value', 0)
        # 9.5A-Shadow: fear reduces distortion by 50%
        _fear_active = adv.get('fear_bonus_active', False)
        if _fear_active:
            dv = round(dv * 0.5)

        if arch == 'propagandist' and dv:
            edu_level = getattr(gs, 'education_level', 0)
            edu_reduction = {0: 1.0, 1: 0.8, 2: 0.5, 3: 0.2}
            factor = edu_reduction.get(edu_level, 1.0)
            effective = round(dv * factor)
            if effective:
                distortions['approval'] = distortions.get('approval', 0) + effective

        elif arch == 'militia_commander' and dv:
            distortions['stability'] = distortions.get('stability', 0) + dv

        elif arch == 'general' and dv:
            distortions['military_strength'] = distortions.get('military_strength', 0) + dv

        elif arch in ('spy_chief', 'fixer') and dv:
            distortions['detection_heat'] = distortions.get('detection_heat', 0) - dv

        elif arch == 'oligarch':
            if dv:
                distortions['detection_heat'] = distortions.get('detection_heat', 0) - dv
            bdv = adv.get('budget_distortion_value', 0)
            if _fear_active:
                bdv = round(bdv * 0.5)
            if bdv:
                distortions['budget'] = distortions.get('budget', 0) + bdv

    return distortions


# ── Betrayal Logic (v2: updated archetypes, conditions) ──────────────────────

def check_betrayals(game_state):
    """Check betrayal conditions at EOT for each staff advisor.
    Only fires if loyalty < 20 (uses loyalty field, not trust).
    Each advisor can only betray once per game.
    Returns list of (archetype_key, message) tuples for briefing events."""
    events = []
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return events

    for key, adv in list(_advisors.items()):
        if not isinstance(adv, dict):
            continue
        trust = adv.get('trust', 75)
        if trust >= 20:
            continue
        if adv.get('has_betrayed', False):
            continue

        arch = adv.get('archetype', key)
        name = adv.get('name', arch)
        betrayed = False
        msg = ""

        if arch == 'finance_minister':
            # Skims from national budget → +$1B his personal (not player's)
            game_state.budget = max(0, game_state.budget - 1.0)
            msg = f"🔴 BETRAYAL: {name} skimmed $1B from national budget (unexplained shortfall)"
            betrayed = True

        elif arch == 'technocrat':
            # Leaks tech partnership details to highest-relations NPC
            rels = game_state.relations
            target_npc = max(['eu', 'usa'], key=lambda n: rels.get(n, 0))
            other_npc = 'usa' if target_npc == 'eu' else 'eu'
            game_state.update_relations(other_npc, -5, flat=True, source="technocrat leak")
            msg = f"🔴 BETRAYAL: {name} leaked tech partnership details to {target_npc.upper()}! Relations -5 with {other_npc.upper()}"
            betrayed = True

        elif arch == 'diplomat':
            # Contacts EU or USA — requires authoritarian regime drift
            _regime = game_state.state_identity.get('regime_type', 'Managed Democracy')
            if _regime in ('Kleptocracy', 'Totalitarian Regime', 'Patronage State', 'Soft Authoritarianism'):
                game_state.update_relations('eu', 5, flat=True, source="diplomat betrayal")
                game_state.update_relations('usa', 5, flat=True, source="diplomat betrayal")
                game_state.update_approval(-5)
                game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 10)
                msg = f"🔴 BETRAYAL: {name} leaked internal info to EU and USA! EU +5, USA +5, Approval -5, Heat +10"
                betrayed = True

        elif arch == 'general':
            # Coup probability +20% for 2 turns (military_strength < 20 condition)
            mil = getattr(game_state, 'military_strength', 20)
            if mil < 20:
                game_state._general_coup_boost_turns = 2
                msg = f"🔴 BETRAYAL: {name} — demoralized military finds its own leadership! Coup probability +20% for 2 turns"
                betrayed = True

        elif arch == 'propagandist':
            # Unauthorized campaign — approval display snaps to true, heat +15
            game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 15)
            msg = f"🔴 BETRAYAL: {name} ran unauthorized domestic campaign! Approval display reveals true values. Heat +15"
            betrayed = True

        elif arch == 'militia_commander':
            # Unauthorized brigade deployment — $1B personal, heat +10
            _days_no_brigade = getattr(game_state, 'days_since_suppression', 0)
            if _days_no_brigade >= 5:
                if game_state.personal_wealth >= 1.0:
                    game_state.personal_wealth = round(game_state.personal_wealth - 1.0, 1)
                game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 10)
                print(f"  [advisor] UNAUTHORIZED ACTION: Militia Commander deployed brigade without authorization")
                msg = f"🔴 BETRAYAL: {name} deployed a Tier 1 Propaganda brigade without authorization! $1B personal, Heat +10"
                betrayed = True

        elif arch == 'spy_chief':
            # Burns one active backchannel promise
            _promises = getattr(game_state, 'active_promises', [])
            rels = game_state.relations
            target_npc = max(['usa', 'arabia', 'eu', 'dprg'], key=lambda n: rels.get(n, 0))
            if _promises:
                print(f"  [advisor] BETRAYAL: Spy Chief burned backchannel — sold to {target_npc.upper()}")
                msg = f"🔴 BETRAYAL: {name} burned backchannel — sold information to {target_npc.upper()}! Covert promise exposed"
            else:
                game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 15)
                print(f"  [advisor] BETRAYAL: Spy Chief burned backchannel — sold to {target_npc.upper()}")
                msg = f"🔴 BETRAYAL: {name} leaked intel intercept to the press! Heat +15"
            betrayed = True

        elif arch == 'oligarch':
            # Skims additional $1B from national budget (not to player)
            game_state.budget = max(0, game_state.budget - 1.0)
            print(f"  [advisor] BETRAYAL: Oligarch self-skimmed $1B from national budget")
            msg = f"🔴 BETRAYAL: {name} skimmed $1B from national budget to personal accounts! Budget -$1B"
            betrayed = True

        elif arch == 'fixer':
            # Sells backchannel info to highest-relations NPC
            rels = game_state.relations
            target_npc = max(['usa', 'arabia', 'eu', 'dprg'], key=lambda n: rels.get(n, 0))
            _promises = getattr(game_state, 'active_promises', [])
            if _promises:
                print(f"  [advisor] BETRAYAL: Fixer sold backchannel to {target_npc.upper()}")
                msg = f"🔴 BETRAYAL: {name} sold backchannel information to {target_npc.upper()}! Covert promise exposed"
            else:
                game_state.detection_heat = min(100, getattr(game_state, 'detection_heat', 0) + 15)
                print(f"  [advisor] BETRAYAL: Fixer sold backchannel to {target_npc.upper()}")
                msg = f"🔴 BETRAYAL: {name} leaked covert operation details! Heat +15"
            betrayed = True

        if betrayed:
            adv['has_betrayed'] = True
            adv['trust'] = 50  # reset to prevent immediate re-trigger
            events.append((key, msg))
            print(f"  [advisor] BETRAYAL FIRED: {name} ({arch}) — trust was {trust}")

            # Log
            log = getattr(game_state, 'advisor_actions_log', [])
            log.append({
                'day': getattr(game_state, 'current_day', 0),
                'advisor': name,
                'archetype': arch,
                'action': 'betrayal',
                'result': msg,
            })
            game_state.advisor_actions_log = log

    return events


# ── Diplomat Negotiation Discount (v2: competence-based) ─────────────────────

def get_diplomat_discount(game_state):
    """Return negotiation cost multiplier if Diplomat is assigned this turn.
    Competence >= 80: free (multiplier 0.0).
    Competence < 80: 50% discount (multiplier 0.5)."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return 1.0  # no discount
    adv = _advisors.get('diplomat', {})
    if not isinstance(adv, dict):
        return 1.0
    if not adv.get('assigned_this_turn', False):
        return 1.0
    comp = adv.get('competence', 60)
    if comp >= 80:
        return 0.0  # free
    return 0.5  # 50% discount


# ── Spy Chief Intel Cost Discount (v2: new mechanic) ─────────────────────────

def get_spy_chief_intel_discount(game_state):
    """Return intel gathering cost multiplier if Spy Chief is assigned this turn.
    Competence >= 80: free (multiplier 0.0).
    Competence < 80: 40% discount (multiplier 0.6)."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return 1.0
    adv = _advisors.get('spy_chief', {})
    if not isinstance(adv, dict):
        return 1.0
    if not adv.get('assigned_this_turn', False):
        return 1.0
    comp = adv.get('competence', 70)
    if comp >= 80:
        print(f"  [advisor] INTEL COST MODIFIED: -100% from Spy Chief (competence={comp})")
        return 0.0
    print(f"  [advisor] INTEL COST MODIFIED: -40% from Spy Chief (competence={comp})")
    return 0.6


# ── Backchannel Detection Discount (v2: Spy Chief + Fixer stackable) ────────

def get_backchannel_detection_modifier(game_state):
    """Return combined backchannel detection risk modifier.
    Spy Chief assigned: -15%. Fixer assigned: -25%. Combined max: -40%.
    Returns the modifier as a fraction (e.g., 0.60 means 40% reduction)."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return 1.0

    modifier = 1.0
    for adv in _advisors.values():
        if not isinstance(adv, dict) or not adv.get('assigned_this_turn', False):
            continue
        arch = adv.get('archetype', '')
        if arch == 'spy_chief':
            modifier -= 0.15
            print(f"  [advisor] BACKCHANNEL RISK MODIFIED: -15% from spy_chief")
        elif arch == 'fixer':
            modifier -= 0.25
            print(f"  [advisor] BACKCHANNEL RISK MODIFIED: -25% from fixer")

    return max(0.0, modifier)


# ── Oligarch Skim Bonus (v2: new mechanic) ───────────────────────────────────

def get_oligarch_skim_bonus(game_state):
    """Return skim bonus multiplier if Oligarch is assigned this turn.
    +10% additional personal wealth on skim actions."""
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return 1.0
    adv = _advisors.get('oligarch', {})
    if not isinstance(adv, dict):
        return 1.0
    if not adv.get('assigned_this_turn', False):
        return 1.0
    return 1.10  # +10% bonus


# ── 9.5A-Shadow: Fear Decay Processing ───────────────────────────────────────────

def process_fear_decay(game_state):
    """9.5A-Shadow: Process fear bonus decay for advisors.
    Called from EOT processing. Removes fear_bonus_active when window expires.
    Applies loyalty decay toward baseline after fear expires.
    Returns list of messages for briefing."""
    current_day = getattr(game_state, 'current_day', 0)
    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return []

    fear_list = list(getattr(game_state, 'advisors_with_fear_bonus', []))
    messages = []
    expired = []

    for key, adv in _advisors.items():
        if not isinstance(adv, dict):
            continue
        if not adv.get('fear_bonus_active', False):
            continue

        start = adv.get('fear_start_day', 0)
        window = adv.get('fear_window', 5)

        if current_day >= start + window:
            # Fear expired
            adv['fear_bonus_active'] = False
            expired.append(key)

            # Loyalty decays toward baseline (-10 from the boost)
            old_trust = adv.get('trust', 75)
            decay = 10
            adv['trust'] = max(20, old_trust - decay)
            print(f"  [9.5A-Shadow] fear_expired: {key} loyalty {old_trust} -> {adv['trust']}")

    # Update fear list
    for key in expired:
        if key in fear_list:
            fear_list.remove(key)

    if expired:
        messages.append(
            f"\U0001f576 Fear effect faded for {len(expired)} advisor(s) "
            f"\u2014 loyalty returning to baseline")
        print(f"  [9.5A-Shadow] fear_decay: {len(expired)} expired, "
              f"remaining_fear={fear_list}")

    game_state.advisors_with_fear_bonus = fear_list
    game_state.advisors = _advisors
    return messages


def check_witnessed_defection_risk(game_state):
    """9.5A-Shadow: Check if witnessed-elimination advisors defect on player weakness.
    Called from EOT when approval < 30 or other weakness triggers.
    Returns list of (advisor_key, message) for defection events."""
    events = []
    approval = getattr(game_state, 'public_approval', 50)
    in_exile = getattr(game_state, 'in_exile', False)

    # Only trigger on weakness
    if approval >= 30 and not in_exile:
        return events

    _advisors = getattr(game_state, 'advisors', {})
    if not isinstance(_advisors, dict):
        return events

    witnessed = getattr(game_state, 'advisors_witnessed_elimination', [])
    chronic = getattr(game_state, 'advisors_chronically_fearful', [])

    for key, adv in list(_advisors.items()):
        if not isinstance(adv, dict):
            continue
        if key not in witnessed:
            continue
        # Skip advisors currently under fear effect (too scared to defect NOW)
        if adv.get('fear_bonus_active', False):
            continue

        # Defection chance: 15% base, +10% if chronically fearful
        defect_chance = 0.15
        if key in chronic:
            defect_chance += 0.10

        import random
        if random.random() < defect_chance:
            name = adv.get('name', key)
            # Defection: trust drops drastically
            old_trust = adv.get('trust', 75)
            adv['trust'] = max(0, old_trust - 40)
            events.append((key, f"\U0001f576 {name} (witnessed elimination) "
                          f"has turned against you! Loyalty plummeted."))
            print(f"  [9.5A-Shadow] witnessed_defection: {key} trust "
                  f"{old_trust} -> {adv['trust']} (approval={approval})")

    return events
