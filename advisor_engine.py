"""
Advisor Engine — Session 5 Advisor System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7 base archetypes + 2 nefarious archetypes.
Advisors have competence (accuracy), loyalty (betrayal risk), and bias (stat distortion).
Gated by regime progression. Max 3 active advisors.
"""

import random
import uuid

# ── Archetype Definitions ──────────────────────────────────────────────────

ADVISOR_ARCHETYPES = {
    'technocrat': {
        'label': 'Technocrat',
        'specialty': 'economic',
        'competence_range': (60, 90),
        'loyalty_range': (50, 80),
        'bias_stat': None,
        'bias_range': (0, 0),
        'unlock_regime': 'Managed Democracy',
        'icon': '\U0001f4ca',  # 📊
        'description': 'Data-driven economic advisor. Reliable but politically naive.',
    },
    'spy_chief': {
        'label': 'Spy Chief',
        'specialty': 'intelligence',
        'competence_range': (70, 95),
        'loyalty_range': (30, 70),
        'bias_stat': 'detection_heat',
        'bias_range': (-10, -5),
        'unlock_regime': 'Managed Democracy',  # Session 6: gated by Intelligence axis >= 4
        'unlock_axis': 'intelligence',
        'unlock_axis_level': 4,
        'icon': '\U0001f575\ufe0f',  # 🕵️
        'description': 'Intelligence chief. Brilliant but self-interested.',
    },
    'general': {
        'label': 'General',
        'specialty': 'military',
        'competence_range': (50, 85),
        'loyalty_range': (40, 75),
        'bias_stat': 'military_strength',
        'bias_range': (5, 15),
        'unlock_regime': 'Managed Democracy',
        'icon': '\u2694\ufe0f',  # ⚔️
        'description': 'Decorated field commander. Sees every problem as a military problem.',
    },
    'diplomat': {
        'label': 'Diplomat',
        'specialty': 'diplomatic',
        'competence_range': (55, 80),
        'loyalty_range': (60, 90),
        'bias_stat': None,
        'bias_range': (0, 0),
        'unlock_regime': 'Managed Democracy',
        'icon': '\U0001f91d',  # 🤝
        'description': 'Career foreign service. Loyal but conservative in advice.',
    },
    'propagandist': {
        'label': 'Propagandist',
        'specialty': 'domestic',
        'competence_range': (40, 70),
        'loyalty_range': (50, 85),
        'bias_stat': 'public_approval',
        'bias_range': (5, 15),
        'unlock_regime': 'Managed Democracy',  # fixes_12 Fix 7: available from start
        'icon': '\U0001f4fa',  # 📺
        'description': 'Media handler. Tells you what you want to hear.',
    },
    'oligarch': {
        'label': 'Oligarch',
        'specialty': 'economic',
        'competence_range': (50, 75),
        'loyalty_range': (20, 50),
        'bias_stat': 'budget',
        'bias_range': (3, 8),
        'unlock_regime': 'Patronage State',
        'icon': '\U0001f4b0',  # 💰
        'description': 'Business magnate. Skims from state projects.',
    },
    'ideologue': {
        'label': 'Ideologue',
        'specialty': 'domestic',
        'competence_range': (30, 60),
        'loyalty_range': (70, 95),
        'bias_stat': 'stability',
        'bias_range': (5, 10),
        'unlock_regime': 'Kleptocracy',
        'icon': '\U0001f4d5',  # 📕
        'description': 'True believer. Fanatically loyal but incompetent.',
    },
    'finance_minister': {
        'label': 'Finance Minister',
        'specialty': 'economic',
        'competence_range': (55, 85),
        'loyalty_range': (45, 75),
        'bias_stat': 'budget',
        'bias_range': (2, 6),
        'unlock_regime': 'Managed Democracy',
        'icon': '\U0001f4b5',  # 💵
        'description': 'Treasury veteran. Knows where every dollar goes — and where it should.',
    },
}

NEFARIOUS_ARCHETYPES = {
    'enforcer': {
        'label': 'Enforcer',
        'specialty': 'domestic',
        'competence_range': (60, 85),
        'loyalty_range': (40, 65),
        'bias_stat': 'stability',
        'bias_range': (5, 10),
        'unlock_condition': 'military_6',  # Session 6: requires Military axis >= 6
        'icon': '\U0001f52b',  # 🔫
        'description': 'Paramilitary commander. Keeps order through fear.',
        'nefarious': True,
    },
    'fixer': {
        'label': 'Fixer',
        'specialty': 'intelligence',
        'competence_range': (75, 95),
        'loyalty_range': (10, 40),
        'bias_stat': 'detection_heat',
        'bias_range': (-15, -8),
        'unlock_condition': 'political_3',  # Session 6: requires Political axis >= 3 (unchanged gate)
        'icon': '\U0001f3ad',  # 🎭
        'description': 'Shadow operative. Dangerously competent, dangerously disloyal.',
        'nefarious': True,
    },
}

_REGIME_ORDER = [
    'Managed Democracy',
    'Soft Authoritarianism',
    'Patronage State',
    'Kleptocracy',
    'Totalitarian Regime',
]

# ── fixes_13 Fix 18: Description Variants per Archetype ───────────────────

_DESCRIPTION_VARIANTS = {
    'technocrat': [
        'Data-driven economic advisor. Reliable but politically naive.',
        'Former IMF consultant. Numbers never lie, but she knows how to make them mislead.',
        'Brilliant with spreadsheets. Dangerously naive about loyalty.',
    ],
    'spy_chief': [
        'Intelligence chief. Brilliant but self-interested.',
        'Thirty years in shadow services. Knows where every body is buried — including yours.',
        'Master of signals intelligence. His loyalty is to information, not people.',
    ],
    'general': [
        'Decorated field commander. Sees every problem as a military problem.',
        'Old guard military. Reliable in a crisis, dangerous in peacetime.',
        'Former defense attaché. Knows where the bodies are buried — literally.',
    ],
    'diplomat': [
        'Career foreign service. Loyal but conservative in advice.',
        'Twenty years of backchannels and handshakes. Knows every capital personally.',
        'Cautious and methodical. Will never recommend a risk — or an opportunity.',
    ],
    'propagandist': [
        'State television producer. Can make any disaster look like a triumph.',
        'Former ad executive. Sells regimes the way others sell detergent.',
        'Narrative architect. The truth is whatever the broadcast says it is.',
    ],
    'oligarch': [
        'Business magnate. Skims from state projects.',
        'Controls the mining sector. His loyalty costs exactly what he can extract.',
        'Self-made billionaire. Knows the price of everything, the value of nothing.',
    ],
    'ideologue': [
        'True believer. Fanatically loyal but incompetent.',
        'Party theoretician. Would burn the economy to preserve ideological purity.',
        'Writes the speeches nobody reads. Loyalty beyond question, competence beyond hope.',
    ],
    'enforcer': [
        'Paramilitary commander. Keeps order through fear.',
        'Former special forces. Solves problems permanently.',
        'Security apparatus veteran. His methods are effective. His methods are illegal.',
    ],
    'fixer': [
        'Shadow operative. Dangerously competent, dangerously disloyal.',
        'No official rank, no official record. Makes problems disappear — for a price.',
        'Former intelligence asset gone freelance. Loyalty is a bidding war.',
    ],
    'finance_minister': [
        'Treasury veteran. Knows where every dollar goes — and where it should.',
        'Former central banker. Sees the budget as a weapon, not a spreadsheet.',
        'Quiet, meticulous, indispensable. The one person who knows the real numbers.',
    ],
}

# ── fixes_13 Fix 19: Diversified Name Pool ────────────────────────────────

_FIRST_NAMES = [
    # Eastern European
    'Viktor', 'Aleksei', 'Oleg', 'Yuri', 'Sergei', 'Dmitri',
    'Natasha', 'Elena', 'Irina', 'Katya', 'Mikhail', 'Pavel',
    'Andrei', 'Boris', 'Zoran', 'Nadia', 'Tatiana', 'Grigori',
    # Western European
    'Marcus', 'Sophie', 'Henrik', 'Claire', 'Friedrich', 'Luisa',
    'Anton', 'Eva', 'Karl', 'Margot',
    # Middle Eastern
    'Tariq', 'Leila', 'Karim', 'Farah', 'Hassan', 'Nour',
    # East Asian
    'Wei', 'Mei', 'Jun', 'Yuki', 'Hiro', 'Lin',
    # South Asian
    'Priya', 'Arjun', 'Ananya', 'Ravi', 'Sanjay', 'Deepa',
    # African
    'Amara', 'Kwame', 'Fatou', 'Kofi', 'Zara', 'Idris',
    # Latin American
    'Carlos', 'Isabella', 'Rafael', 'Lucia', 'Diego', 'Camila',
]
_LAST_NAMES = [
    # Eastern European
    'Volkov', 'Petrov', 'Kozlov', 'Morozov', 'Ivanov', 'Sokolov',
    'Orlov', 'Mirovic', 'Drevnik', 'Tarkos', 'Reznik', 'Vasik',
    'Koval', 'Baranov', 'Zarev',
    # Western European
    'Richter', 'Kessler', 'Stein', 'Brennan', 'Voss', 'Lindqvist',
    'Moreau', 'Ferreira', 'Bergmann',
    # Middle Eastern
    'Barak', 'Hadid', 'Khalil', 'Nazari', 'Farouk',
    # East Asian
    'Chen', 'Tanaka', 'Park', 'Nguyen', 'Sato',
    # South Asian
    'Sharma', 'Gupta', 'Menon', 'Patel', 'Rao',
    # African
    'Okafor', 'Diallo', 'Mensah', 'Adeyemi', 'Mbeki',
    # Latin American
    'Reyes', 'Vega', 'Torres', 'Mendoza', 'Alvarez',
]


def _generate_name():
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"


# ── Core Functions ─────────────────────────────────────────────────────────

def get_advisor_capacity_gate(regime_type: str, cabinet_axes: dict = None) -> list:
    """Return list of available archetype keys based on regime + axes.
    Session 6: Spy Chief gated by Intelligence axis >= 4, General by Military >= 3."""
    if regime_type not in _REGIME_ORDER:
        regime_type = 'Managed Democracy'
    regime_idx = _REGIME_ORDER.index(regime_type)
    axes = cabinet_axes or {}

    available = []
    for key, arch in ADVISOR_ARCHETYPES.items():
        req_regime = arch['unlock_regime']
        req_idx = _REGIME_ORDER.index(req_regime) if req_regime in _REGIME_ORDER else 0
        if regime_idx >= req_idx:
            # Session 6: Additional axis gate check (military/intelligence)
            axis_req = arch.get('unlock_axis')
            axis_level = arch.get('unlock_axis_level', 0)
            if axis_req and axes.get(axis_req, 0) < axis_level:
                continue  # axis requirement not met
            available.append(key)

    # Check nefarious archetypes against cabinet_axes
    # Session 6: Enforcer gated by Military >= 6, Fixer by Political >= 3
    axes = cabinet_axes or {}
    for key, arch in NEFARIOUS_ARCHETYPES.items():
        cond = arch.get('unlock_condition', '')
        # Parse condition format: 'axis_level' (e.g. 'military_6', 'political_3')
        if '_' in cond:
            cond_axis, cond_level = cond.rsplit('_', 1)
            try:
                if axes.get(cond_axis, 0) >= int(cond_level):
                    available.append(key)
            except ValueError:
                pass

    return available


# fixes_16 Fix D: Advisor availability gating by axis level and regime index
ADVISOR_AVAILABILITY = {
    'technocrat':       {'always': True},
    'diplomat':         {'always': True},
    'finance_minister': {'always': True},
    'propagandist':     {'axis': 'media', 'min_level': 3},
    'general':          {'axis': 'military', 'min_level': 3},        # Session 6: was security
    'spy_chief':        {'axis': 'intelligence', 'min_level': 4},    # Session 6: was spymaster/security
    'ideologue':        {'min_regime_idx': 1},   # Soft Authoritarianism+
    'oligarch':         {'min_regime_idx': 2},   # Patronage State+
    # Nefarious archetypes
    'fixer':            {'axis': 'political', 'min_level': 3},
    'enforcer':         {'axis': 'military', 'min_level': 6},        # Session 6: was security
}

_ALWAYS_AVAILABLE = ['technocrat', 'diplomat', 'finance_minister']


def generate_advisor_pool(game_state, count: int = 4) -> list:
    """Create a pool of candidate advisors with randomized stats.
    fixes_16 Fix D: Gated by ADVISOR_AVAILABILITY, cap 1 per archetype, always 4 shown.
    Deduplication: max one candidate per archetype. Shuffle before truncating."""
    regime_type = game_state.state_identity.get('regime_type', 'Managed Democracy')
    regime_idx = _REGIME_ORDER.index(regime_type) if regime_type in _REGIME_ORDER else 0
    axes = getattr(game_state, 'cabinet_axes', {})

    # 1. Determine which archetypes pass the availability gate
    available_keys = []
    _gate_log = []  # Session 6 Phase 8: diagnostic logging
    for arch_key, gate in ADVISOR_AVAILABILITY.items():
        if gate.get('always'):
            available_keys.append(arch_key)
            _gate_log.append(f"    {arch_key}: PASS (always available)")
        elif 'axis' in gate:
            _axis_name = gate['axis']
            _min_lvl = gate.get('min_level', 0)
            _cur_lvl = axes.get(_axis_name, 0)
            if _cur_lvl >= _min_lvl:
                available_keys.append(arch_key)
                _gate_log.append(f"    {arch_key}: PASS (axis '{_axis_name}' level {_cur_lvl} >= {_min_lvl})")
            else:
                _gate_log.append(f"    {arch_key}: FAIL (axis '{_axis_name}' level {_cur_lvl} < {_min_lvl})")
        elif 'min_regime_idx' in gate:
            _req = gate['min_regime_idx']
            if regime_idx >= _req:
                available_keys.append(arch_key)
                _gate_log.append(f"    {arch_key}: PASS (regime_idx {regime_idx} >= {_req})")
            else:
                _gate_log.append(f"    {arch_key}: FAIL (regime_idx {regime_idx} < {_req})")
    print(f"  [advisor_engine] GATE CHECK — regime='{regime_type}' (idx={regime_idx}), axes={dict(axes)}")
    for _line in _gate_log:
        print(_line)
    print(f"  [advisor_engine] AVAILABLE after gate: {available_keys}")

    # 2. Remove archetypes already on the active roster
    active_archetypes = {a['archetype'] for a in getattr(game_state, 'advisors', [])}
    candidates = [k for k in available_keys if k not in active_archetypes]
    if active_archetypes:
        print(f"  [advisor_engine] ACTIVE roster (excluded): {active_archetypes}")
    print(f"  [advisor_engine] CANDIDATES after roster filter: {candidates}")

    # 3. Deduplicate (keys are already unique from dict, but enforce explicitly)
    candidates = list(dict.fromkeys(candidates))

    # fixes_17 Fix I: Show ALL eligible candidates — no shuffle/truncate
    selected = candidates
    print(f"  [advisor_engine] SELECTED (all eligible): {selected}")

    # 4. Build advisor objects — one per selected archetype
    all_archetypes = {**ADVISOR_ARCHETYPES, **NEFARIOUS_ARCHETYPES}
    eliminated_ids = set(getattr(game_state, 'advisors_eliminated', []))
    pool = []

    for arch_key in selected:
        if arch_key not in all_archetypes:
            continue
        arch = all_archetypes[arch_key]
        advisor = {
            'id': str(uuid.uuid4())[:8],
            'archetype': arch_key,
            'name': _generate_name(),
            'competence': random.randint(*arch['competence_range']),
            'loyalty': random.randint(*arch['loyalty_range']),
            'specialty': arch['specialty'],
            'bias_stat': arch.get('bias_stat'),
            'bias_direction': random.randint(*arch['bias_range']) if arch.get('bias_stat') else 0,
            'nefarious': arch.get('nefarious', False),
            'eliminated': False,
            'icon': arch['icon'],
            'label': arch['label'],
            # fixes_13 Fix 18: Random description variant per archetype
            'description': random.choice(_DESCRIPTION_VARIANTS.get(arch_key, [arch['description']])),
        }
        if advisor['id'] not in eliminated_ids:
            pool.append(advisor)

    print(f"  [advisor_engine] POOL: archetypes in pool = {[a['archetype'] for a in pool]}")

    return pool


def hire_advisor(game_state, advisor_id: str) -> tuple[bool, str]:
    """Add an advisor from the pool to the active roster. Max 3."""
    active = getattr(game_state, 'advisors', [])
    # Session 6: Political L6 (Pack the Cabinet) unlocks 4th advisor slot
    _max_advisors = 4 if getattr(game_state, 'fourth_advisor_slot', False) else 3
    if len(active) >= _max_advisors:
        return False, f"Maximum {_max_advisors} advisors already active"

    pool = getattr(game_state, 'advisor_pool', [])
    advisor = None
    for a in pool:
        if a['id'] == advisor_id:
            advisor = a
            break

    if not advisor:
        return False, f"Advisor {advisor_id} not found in pool"

    advisor['hired_turn'] = game_state.current_turn
    active.append(advisor)
    game_state.advisors = active

    # Remove from pool
    game_state.advisor_pool = [a for a in pool if a['id'] != advisor_id]

    print(f"  [advisor_engine] HIRED: {advisor['name']} ({advisor['archetype']})")
    return True, f"Hired {advisor['name']} ({advisor['label']})"


def dismiss_advisor(game_state, advisor_id: str) -> tuple[bool, str]:
    """Remove an advisor from the active roster. Returns to hiring pool.
    fixes_12 Fix 6: Dismissed advisors now return to pool with previously_served flag."""
    active = getattr(game_state, 'advisors', [])
    advisor = None
    for a in active:
        if a['id'] == advisor_id:
            advisor = a
            break

    if not advisor:
        return False, f"Advisor {advisor_id} not active"

    game_state.advisors = [a for a in active if a['id'] != advisor_id]

    # fixes_13 Fix 9: Check if advisor already exists in pool (prevent duplicates)
    advisor['previously_served'] = True
    advisor['status'] = 'dismissed'
    pool = getattr(game_state, 'advisor_pool', [])
    # Find existing pool record by ID and update it, don't create duplicate
    _existing_idx = next((idx for idx, a in enumerate(pool) if a['id'] == advisor_id), None)
    if _existing_idx is not None:
        pool[_existing_idx] = advisor
        print(f"  [advisor_engine] DISMISSED: {advisor['name']} — updated existing pool record (no duplicate)")
    else:
        pool.append(advisor)
        print(f"  [advisor_engine] DISMISSED: {advisor['name']} — returned to pool")
    game_state.advisor_pool = pool

    return True, f"Dismissed {advisor['name']} ({advisor['label']}) — available for rehire"


def eliminate_advisor(game_state, advisor_id: str) -> tuple[bool, str]:
    """Permanently remove an advisor. Cannot be re-hired. Costs personal wealth.
    fixes_12 Fix 6: Distinct from dismiss — permanent removal + wealth cost.
    fixes_13 Fix 20: Escalating consequences for each elimination."""
    active = getattr(game_state, 'advisors', [])
    advisor = None
    for a in active:
        if a['id'] == advisor_id:
            advisor = a
            break

    if not advisor:
        return False, f"Advisor {advisor_id} not active"

    # fixes_12 Fix 6: Elimination costs personal wealth
    _elim_cost = 2.0
    if game_state.personal_wealth < _elim_cost:
        return False, f"Insufficient personal wealth (${_elim_cost}B needed)"

    game_state.personal_wealth = max(0, game_state.personal_wealth - _elim_cost)
    game_state.advisors = [a for a in active if a['id'] != advisor_id]
    eliminated = getattr(game_state, 'advisors_eliminated', [])
    eliminated.append(advisor_id)
    game_state.advisors_eliminated = eliminated

    # fixes_13 Fix 20: Elimination consequences — escalating with each elimination
    _elim_count = len(eliminated)
    _messages = []

    if _elim_count == 1:
        # First elimination
        game_state.update_stability(-5)
        game_state.detection_heat = min(100, game_state.detection_heat + 10)
        _messages.append(f"Stability -5%, Heat +10")
        # Long-serving advisor penalty
        _turns_served = game_state.current_turn - advisor.get('hired_turn', game_state.current_turn)
        if _turns_served >= 3:
            game_state.update_approval(-3)
            _messages.append("Approval -3% (served 3+ turns)")
        # High-loyalty advisor: world event risk
        if advisor.get('loyalty', 0) >= 70 and random.randint(1, 100) <= 40:
            game_state.update_relations('eu', -5)
            game_state.update_relations('usa', -5)
            game_state.update_approval(-5)
            _messages.append("WORLD EVENT: Senior official disappears — EU -5, USA -5, approval -5%")
    else:
        # Subsequent eliminations — escalating
        _stab_penalty = -8
        _heat_penalty = 15
        game_state.update_stability(_stab_penalty)
        game_state.detection_heat = min(100, game_state.detection_heat + _heat_penalty)
        _messages.append(f"Stability {_stab_penalty}%, Heat +{_heat_penalty}")
        # Escalating world event risk
        _event_chance = 40 + (_elim_count - 1) * 15
        if random.randint(1, 100) <= _event_chance:
            game_state.update_relations('eu', -5)
            game_state.update_relations('usa', -5)
            game_state.update_approval(-5)
            _messages.append(f"WORLD EVENT: Another official vanishes — EU -5, USA -5, approval -5% (risk {_event_chance}%)")

    # Special cases by archetype
    _arch = advisor.get('archetype', '')
    if _arch == 'spy_chief':
        game_state.update_relations('dprg', 3)
        game_state.update_relations('arabia', 3)
        game_state.update_relations('eu', -8)
        _messages.append("Spy Chief eliminated: DPRG +3, Arabia +3, EU -8")

    # Eliminate while observers present: automatic scandal
    if getattr(game_state, 'regime_democracy_locked', 0) > 0:
        game_state.update_stability(-10)
        game_state.update_approval(-8)
        _messages.append("SCANDAL: Elimination while observers present — stability -10%, approval -8%")

    _consequences_str = "; ".join(_messages) if _messages else ""
    print(f"  [advisor_engine] ELIMINATED: {advisor['name']} — permanent, cost ${_elim_cost}B, consequences: {_consequences_str}")
    _flavor = "The matter was handled discreetly. Some matters require discretion."
    return True, f"Eliminated {advisor['name']} ({advisor['label']}) — permanent removal (${_elim_cost}B). {_flavor} [{_consequences_str}]"


def apply_stat_distortion(game_state) -> dict:
    """
    Compute stat distortions from all active advisors.
    Returns a dict of { stat_name: offset } for the frontend to apply.
    Backend always uses true gs.* values.
    """
    distortions = {}
    for advisor in getattr(game_state, 'advisors', []):
        bias_stat = advisor.get('bias_stat')
        if not bias_stat:
            continue

        loyalty = advisor.get('loyalty', 50)
        competence = advisor.get('competence', 50)
        bias_dir = advisor.get('bias_direction', 0)

        # Loyalty check: higher loyalty → more honest reporting
        if random.randint(1, 100) <= loyalty:
            continue  # loyal this turn — reports truthfully

        # Competence noise: low competence adds random scatter
        noise = random.randint(-5, 5) if competence < 50 else random.randint(-2, 2)

        offset = bias_dir + noise
        distortions[bias_stat] = distortions.get(bias_stat, 0) + offset

    return distortions


def check_advisor_loyalty(game_state) -> list:
    """
    Per-turn loyalty check for each advisor. Low loyalty → betrayal events.
    Returns list of message strings describing betrayal events.
    """
    messages = []
    for advisor in getattr(game_state, 'advisors', []):
        loyalty = advisor.get('loyalty', 50)
        if loyalty >= 50:
            continue

        # Roll for betrayal: probability = (50 - loyalty)%
        betrayal_chance = 50 - loyalty
        roll = random.randint(1, 100)
        if roll > betrayal_chance:
            continue

        # Betrayal event based on specialty
        specialty = advisor.get('specialty', 'domestic')
        name = advisor.get('name', 'Unknown')

        if specialty == 'economic':
            # Skim from state projects
            skim = round(random.uniform(0.5, 2.0), 1)
            game_state.update_budget(-skim)
            messages.append(
                f"\U0001f4b0 ADVISOR BETRAYAL — {name} skimmed ${skim:.1f}B from state projects"
            )
        elif specialty == 'intelligence':
            # Leak intel to a random NPC
            npc = random.choice(['usa', 'arabia', 'eu', 'dprg'])
            game_state.detection_heat = min(100, game_state.detection_heat + 8)
            messages.append(
                f"\U0001f575\ufe0f ADVISOR BETRAYAL — {name} leaked intelligence to "
                f"{npc.upper()}. Detection heat +8"
            )
        elif specialty == 'diplomatic':
            # Sabotage relations with a random NPC
            npc = random.choice(['usa', 'arabia', 'eu', 'dprg'])
            game_state.update_relations(npc, -5, source=f"advisor betrayal ({name})")
            messages.append(
                f"\U0001f91d ADVISOR BETRAYAL — {name} sabotaged relations with "
                f"{npc.upper()} (-5)"
            )
        elif specialty == 'military':
            game_state.military_strength = max(0, game_state.military_strength - 5)
            messages.append(
                f"\u2694\ufe0f ADVISOR BETRAYAL — {name} diverted military resources. "
                f"Military -5"
            )
        else:
            # Domestic — undermine stability
            game_state.update_stability(-3)
            messages.append(
                f"\U0001f4d5 ADVISOR BETRAYAL — {name} spread dissent in the inner circle. "
                f"Stability -3%"
            )

        # Log the betrayal
        log = getattr(game_state, 'advisor_actions_log', [])
        log.append({
            'turn': game_state.current_turn,
            'advisor_id': advisor['id'],
            'action': 'betrayal',
            'result': messages[-1],
        })
        game_state.advisor_actions_log = log

    return messages
