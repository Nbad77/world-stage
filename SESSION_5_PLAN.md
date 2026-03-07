# SESSION 5 IMPLEMENTATION PLAN
## The World Stage — 7 Deliverables

---

## IMPLEMENTATION ORDER (dependency graph)

```
Phase A — Foundation (no game-visible changes yet)
  A1. Player fingerprint identity (frontend + api.py)
  A2. Database schema: npc_memories table + player_id on GameSession
  A3. memory_engine.py — Tier 1 core (store_memory, retrieve_memories, Voyage AI)
  A4. Economic development model — game_state fields + GDP stub (latent, no UI interaction yet)

Phase B — Backend Systems (game logic changes, minimal frontend)
  B1. Shadow Cabinet redesign — five axes in game_state, migrate existing mechanics
  B2. Advisor system — 7 archetypes, game_state fields, advisor_engine.py
  B3. Tech Level passive acquisition redesign (turn_processor.py changes)
  B4. NPC-initiated contact — rule-based triggers + api.py changes

Phase C — Memory Integration (depends on A1-A3 + B4)
  C1. Memory hook points — store_memory() calls across turn_processor + api.py
  C2. Memory retrieval — inject into _build_context() in npc_engine.py
  C3. Tier 2 — relationship summary rewrite in EOT
  C4. Tier 3 — era summary on regime collapse
  C5. Memory TTL cleanup on POST /game/new

Phase D — Frontend (depends on B1-B4)
  D1. Shadow Cabinet redesign — ShadowCabinet.jsx five axes UI
  D2. Advisor panel — new AdvisorPanel.jsx
  D3. NPC-initiated contact — ⚡ INCOMING indicator in DialoguePanel
  D4. StatusBar latent stats — Soft Power + Diplomatic Capital (greyed)
  D5. Tax lever UI in ShadowCabinet

Phase E — Spec + Tests
  E1. docs/briefing_spec.md (daily briefing spec, NO implementation)
  E2. New tests for all deliverables
  E3. STATUS.md update
```

---

## DELIVERABLE 1: Vector Memory System

### A1. Player Fingerprint Identity

**frontend/src/components/TitleScreen.jsx** — MODIFY
- On mount, check `localStorage.getItem('worldstage_player_id')`
- If absent, generate `crypto.randomUUID()`, store it
- Pass `player_id` to the `POST /game/new` call

**frontend/src/api.js** — MODIFY
- `newGame()` accepts optional `playerId` parameter
- Sends `{ player_id: playerId }` in request body

**api.py** — MODIFY
- `POST /game/new` request model gets optional `player_id: str = None`
- If provided, store on the GameSession record
- If absent (legacy clients), generate server-side UUID

### A2. Database Schema

**db.py** — MODIFY
- Add `player_id` column to `GameSession`:
  ```python
  player_id = Column(String(36), nullable=True, index=True)
  ```
- Add new `NpcMemory` model:
  ```python
  class NpcMemory(Base):
      __tablename__ = "npc_memories"
      id = Column(Integer, primary_key=True, autoincrement=True)
      player_id = Column(String(36), nullable=False, index=True)
      npc = Column(String(10), nullable=False)         # 'usa'|'arabia'|'eu'|'dprg'
      era = Column(Integer, nullable=False, default=0)  # era counter (increments on regime collapse)
      turn = Column(Integer, nullable=False)
      event_type = Column(String(50), nullable=False)   # 'deal_accepted'|'promise_broken'|etc.
      description = Column(Text, nullable=False)        # human-readable event description
      embedding = Column(Vector(512), nullable=True)    # pgvector — Voyage AI voyage-3-lite
      created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
      last_accessed = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  ```
- Add new `NpcRelationshipSummary` model (Tier 2):
  ```python
  class NpcRelationshipSummary(Base):
      __tablename__ = "npc_relationship_summaries"
      id = Column(Integer, primary_key=True, autoincrement=True)
      player_id = Column(String(36), nullable=False, index=True)
      npc = Column(String(10), nullable=False)
      summary_text = Column(Text, nullable=False)       # 2-3 sentence gist
      updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
      # Unique constraint: one summary per player per NPC
  ```
- Add new `EraSummary` model (Tier 3):
  ```python
  class EraSummary(Base):
      __tablename__ = "era_summaries"
      id = Column(Integer, primary_key=True, autoincrement=True)
      player_id = Column(String(36), nullable=False, index=True)
      npc = Column(String(10), nullable=False)
      era = Column(Integer, nullable=False)
      summary_text = Column(Text, nullable=False)       # paragraph compressing episodic memories
      created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  ```
- `create_session()` accepts optional `player_id` parameter
- `init_db()` unchanged — `Base.metadata.create_all()` creates new tables automatically
- Import `from pgvector.sqlalchemy import Vector` at top
- Import `from sqlalchemy import Integer, Text` (add to existing imports)

### A3. memory_engine.py — NEW FILE

```
memory_engine.py
├── VOYAGE_CLIENT        # voyageai.Client() singleton, lazy-initialized
├── store_memory()       # async-safe, non-blocking, failure-tolerant
├── retrieve_memories()  # top-K similarity search for one NPC
├── get_relationship_summary()   # Tier 2 read
├── update_relationship_summaries()  # Tier 2 batch rewrite (single Haiku call)
├── get_era_summaries()  # Tier 3 read (last 2 eras)
├── create_era_summary() # Tier 3 compress on regime collapse
├── cleanup_expired_memories()   # 90-day TTL
├── build_memory_context()       # assemble all 3 tiers into injection dict
```

**store_memory(player_id, npc, era, turn, event_type, description)**
- Generates embedding via `voyageai.Client().embed([description], model="voyage-3-lite")`
- Wraps in try/except — on failure, stores row with `embedding=None` (text still useful)
- Inserts into `npc_memories` table
- Non-blocking: if embedding call fails, log warning, don't crash game flow
- All DB operations use a fresh `SessionLocal()` (same pattern as db.py)

**retrieve_memories(player_id, npc, query_text, top_k=3)**
- Generates query embedding via Voyage AI
- SQL: `SELECT * FROM npc_memories WHERE player_id=? AND npc=? ORDER BY embedding <=> query_embedding LIMIT ?`
- Updates `last_accessed` timestamp on returned rows
- Falls back to most-recent-by-turn if embedding is NULL or Voyage fails

**build_memory_context(player_id, npc, query_text)**
- Calls `retrieve_memories()` → top 3 episodic (Tier 1)
- Calls `get_relationship_summary()` → current summary (Tier 2)
- Calls `get_era_summaries()` → last 2 eras (Tier 3)
- Assembles into dict, counts tokens (rough: `len(text) / 4`)
- Trims if over 500 token ceiling (Tier 1 entries dropped first)
- Returns `{ episodic: [...], relationship_summary: str, era_summaries: [...] }`

**update_relationship_summaries(player_id, npcs_context_list)**
- Single Haiku call with batched prompt:
  ```
  For each NPC below, write a 2-3 sentence summary of your relationship
  with Europa's leader based on recent events. Return JSON.
  NPC: usa — Recent events: [...]
  NPC: arabia — Recent events: [...]
  NPC: eu — Recent events: [...]
  NPC: dprg — Recent events: [...]
  ```
- Parses JSON response, upserts into `npc_relationship_summaries`
- Called once in EOT after all other effects resolve

**create_era_summary(player_id, npc, era_number)**
- Retrieves all episodic memories for this player+NPC+era
- Single Haiku call: "Compress these events into one paragraph"
- Inserts into `era_summaries`
- Called when regime collapse fires

**cleanup_expired_memories(player_id)**
- DELETE FROM npc_memories WHERE player_id=? AND last_accessed < NOW() - INTERVAL '90 days'
- Called on POST /game/new (before new game starts)

### requirements.txt — MODIFY
Add two lines:
```
voyageai>=0.3.0
pgvector>=0.3.0
```

### .env.example — MODIFY
Add: `VOYAGE_API_KEY=` placeholder

---

## DELIVERABLE 2: NPC-Initiated Contact

### Concept
Rule-based triggers that cause an NPC to "reach out" to the player outside the normal dialogue round. Displayed as ⚡ INCOMING in the offers panel. Architecture ready for Session 7 GM inference layer to take over trigger selection.

### turn_processor.py — MODIFY (new section in EOT or new helper)

**NPC_CONTACT_TRIGGERS** — new dict:
```python
NPC_CONTACT_TRIGGERS = {
    'usa_sanctions_warning': {
        'npc': 'usa',
        'condition': lambda gs: gs.relations['usa'] < 35 and gs.relations['usa'] >= 25
                     and not gs.usa_sanctions_active,
        'cooldown': 3,  # turns between repeat fires
        'priority': 'high',
        'context_hint': 'Bill is reaching out to warn about impending sanctions',
    },
    'arabia_oil_olive_branch': {
        'npc': 'arabia',
        'condition': lambda gs: gs.arabia_embargo_active
                     and gs.relations['arabia'] >= 15,
        'cooldown': 4,
        'priority': 'medium',
        'context_hint': 'Sadam sees an opening to negotiate embargo relief',
    },
    'eu_tech_offer': {
        'npc': 'eu',
        'condition': lambda gs: gs.relations['eu'] >= 60
                     and gs.tech_level < 40,
        'cooldown': 5,
        'priority': 'medium',
        'context_hint': 'Marsha wants to offer a technology partnership',
    },
    'dprg_escape_hint': {
        'npc': 'dprg',
        'condition': lambda gs: gs.personal_wealth >= 15
                     and gs.relations['dprg'] >= 40
                     and gs.budget < 15,
        'cooldown': 4,
        'priority': 'low',
        'context_hint': 'Ji-won senses desperation and offers a lifeline',
    },
    'usa_blackmail_setup': {
        'npc': 'usa',
        'condition': lambda gs: gs.personal_wealth >= 10
                     and not gs.blackmail_used
                     and gs.relations['usa'] < 40,
        'cooldown': 99,  # fires once
        'priority': 'high',
        'context_hint': 'Bill has intelligence on your personal wealth',
    },
    'arabia_alliance_pitch': {
        'npc': 'arabia',
        'condition': lambda gs: gs.relations['arabia'] >= 70
                     and gs.relations['usa'] < 40,
        'cooldown': 5,
        'priority': 'medium',
        'context_hint': 'Sadam proposes a deeper partnership against Western pressure',
    },
}
```

**check_npc_contacts(game_state)** — new function:
- Iterates triggers, evaluates conditions against game_state
- Checks cooldown against `game_state.npc_contact_history` (new field)
- Returns list of `{ trigger_id, npc, context_hint, priority }` (max 1 per NPC per turn)
- Sorts by priority, returns top 1-2 contacts

### game_state.py — MODIFY
New fields:
```python
self.npc_contact_history = {}     # { trigger_id: last_turn_fired }
self.pending_npc_contacts = []    # set by EOT, consumed by next turn's dialogue
```
Add to serialize/deserialize.

### npc_engine.py — MODIFY
New function: **generate_npc_contact_dialogue(game_state, contact_info)**
- Calls `_call_npc()` with special system prompt suffix: "You are initiating contact with Europa's leader. {context_hint}. You reached out to them — they did not come to you."
- Returns dialogue string marked as `incoming: True`

### api.py — MODIFY
- In `POST /game/new` and the turn-advance flow:
  - After EOT resolves, call `check_npc_contacts(gs)`
  - For each triggered contact, call `generate_npc_contact_dialogue()`
  - Store results in response payload as `npc_contacts: [{ npc, dialogue, trigger_id }]`
- New field in dialogue response: contacts are separate from regular 4-NPC dialogue

### frontend/src/components/DialoguePanel.jsx — MODIFY
- If `npc_contacts` array is non-empty in turn data:
  - Render ⚡ INCOMING badge next to the contacting NPC's dialogue card
  - Contact dialogue appears as a separate card above/below the regular dialogue
  - Styled with amber/gold border to distinguish from regular communiques

### frontend/src/components/OffersPanel.jsx — MODIFY
- NPC-initiated contacts may come with special offers
- If contact has an associated offer, inject it into offers list with ⚡ prefix

---

## DELIVERABLE 3: Daily Briefing UI Spec

### docs/briefing_spec.md — NEW FILE (spec only, no implementation)

Contents will cover:
- **Purpose**: Morning briefing presented to the player at the start of each turn, before NPC dialogue. Summarizes overnight developments, intelligence reports, and advisor recommendations.
- **Data sources**: EOT messages from previous turn, NPC contact triggers, advisor opinions, world event preview, threshold warnings, relationship trend arrows
- **UI layout spec**: Full-width card above dialogue panel, collapsible, sections:
  - Intelligence Summary (from intel budget system)
  - Diplomatic Situation (relationship trends, approaching thresholds)
  - Economic Outlook (budget projection, oil price trend, GDP)
  - Advisor Recommendations (top 2-3 advisor opinions on current situation)
  - Active Threats (sanctions/embargo escalation, coup risk, etc.)
- **Implementation notes for Session 6+**: Which components to create, data flow from api.py, advisor opinion generation call
- **Mockup**: ASCII layout sketch

No code changes. Markdown document only.

---

## DELIVERABLE 4: Tech Level Passive Acquisition Redesign

### Current system
Tech Level gained only through explicit deal-based sources (EU partnership +5, USA transfer +8, DPRG weapons +3). Player must negotiate specific deals.

### New system
Tech Level gains passively each turn based on NPC relationships. Better relations with tech-advanced NPCs = faster tech growth. Explicit deal sources remain as bonus on top.

### turn_processor.py — MODIFY

**New section in EOT** (after section 0c domestic passives, before section 1 oil price):

```python
# ── 0d. TECH LEVEL PASSIVE ACQUISITION ──────────────────────────────
# Each turn, gain tech based on weighted relationship average.
# EU has highest weight (primary tech partner), USA moderate, DPRG/Arabia minimal.
# Formula: base_gain = (eu_rel * 0.04 + usa_rel * 0.02 + dprg_rel * 0.01) / 10
# Result: ~0.1-0.7 per turn at typical relations. Rounds to nearest 0.1.
# Accumulated fractional tech stored in tech_level_fractional.
# When fractional >= 1.0, tech_level increments by floor(fractional).

TECH_PASSIVE_WEIGHTS = {'eu': 0.04, 'usa': 0.02, 'dprg': 0.01, 'arabia': 0.005}

def _calc_passive_tech_gain(game_state):
    weighted = sum(
        game_state.relations.get(npc, 50) * weight
        for npc, weight in TECH_PASSIVE_WEIGHTS.items()
    )
    return round(weighted / 10.0, 2)  # ~0.1-0.7 per turn
```

In `apply_end_of_turn_effects()`:
```python
# 0d. Tech passive gain
_tech_frac = getattr(game_state, 'tech_level_fractional', 0.0)
_tech_frac += _calc_passive_tech_gain(game_state)
_tech_int_gain = int(_tech_frac)
if _tech_int_gain > 0 and game_state.tech_level < 100:
    old_tech = game_state.tech_level
    game_state.tech_level = min(100, game_state.tech_level + _tech_int_gain)
    _tech_frac -= _tech_int_gain
    messages.append(f"🔬 Tech Level +{game_state.tech_level - old_tech} "
                    f"(passive acquisition from diplomatic partnerships) → {game_state.tech_level}")
    game_state.tech_sources.append({
        'source': 'passive_acquisition', 'gain': game_state.tech_level - old_tech,
        'turn': game_state.current_turn
    })
game_state.tech_level_fractional = _tech_frac
```

### game_state.py — MODIFY
New field:
```python
self.tech_level_fractional = 0.0  # accumulated fractional tech points
```
Add to serialize/deserialize.

### StatusBar.jsx — NO CHANGE
Tech Level already always visible (fixes_8 Fix 4). Passive gains just make it grow more naturally.

### Existing explicit tech sources REMAIN
`apply_tech_gain()` and `TECH_SOURCES` dict unchanged. Deal-based gains are bonus on top of passive.

---

## DELIVERABLE 5: Advisor System

### Concept
7 advisor archetypes hired from a pool. Each has competence (how good their advice is), loyalty (chance of betrayal), and a personality that biases their stat reporting. Gated by state capacity (regime progression). Advisors can be eliminated. Nefarious advisors unlock from corruption progression.

### game_state.py — MODIFY

New fields:
```python
# ── Session 5: Advisor System ──────────────────────────────────────────
self.advisors = []  # list of advisor dicts (max 3 active)
# Each advisor: {
#   'id': str (unique),
#   'archetype': str,      # one of 7 archetypes
#   'name': str,           # generated name
#   'competence': int,     # 1-100 (how accurate their intel/advice is)
#   'loyalty': int,        # 1-100 (chance they work for you vs against you)
#   'hired_turn': int,
#   'specialty': str,      # 'economic'|'diplomatic'|'military'|'intelligence'|'domestic'
#   'bias_stat': str|None, # which stat they distort (e.g., 'stability', 'approval')
#   'bias_direction': int, # +N or -N distortion applied to displayed stat
#   'nefarious': bool,     # unlocked from corruption progression
#   'eliminated': bool,    # removed (cannot be re-hired)
# }
self.advisor_pool = []        # available advisors to hire (refreshed each era)
self.advisors_eliminated = [] # list of advisor IDs permanently removed
self.advisor_actions_log = [] # { turn, advisor_id, action, result }
```

### advisor_engine.py — NEW FILE

```
advisor_engine.py
├── ADVISOR_ARCHETYPES     # 7 archetypes with stat ranges
├── NEFARIOUS_ARCHETYPES   # 2 additional archetypes (unlocked by corruption)
├── generate_advisor_pool() # create 3-5 candidates with randomized stats
├── hire_advisor()          # add to active roster (max 3)
├── dismiss_advisor()       # remove from roster (can re-hire)
├── eliminate_advisor()     # permanent removal
├── get_advisor_opinions()  # per-advisor opinion on current state (Haiku call)
├── apply_stat_distortion() # modify displayed stats based on advisor bias
├── check_advisor_loyalty() # per-turn loyalty check — betrayal events
├── get_advisor_capacity_gate() # which archetypes available at current regime
```

**ADVISOR_ARCHETYPES** (7 base):
```python
ADVISOR_ARCHETYPES = {
    'technocrat': {
        'label': 'Technocrat',
        'specialty': 'economic',
        'competence_range': (60, 90),
        'loyalty_range': (50, 80),
        'bias_stat': None,           # honest reporting
        'unlock_regime': 'Managed Democracy',  # available from start
        'icon': '📊',
        'description': 'Data-driven economic advisor. Reliable but politically naive.',
    },
    'spymaster': {
        'label': 'Spymaster',
        'specialty': 'intelligence',
        'competence_range': (70, 95),
        'loyalty_range': (30, 70),
        'bias_stat': 'detection_heat',
        'bias_range': (-10, -5),     # underreports heat
        'unlock_regime': 'Soft Authoritarianism',
        'icon': '🕵️',
        'description': 'Intelligence chief. Brilliant but self-interested.',
    },
    'general': {
        'label': 'General',
        'specialty': 'military',
        'competence_range': (50, 85),
        'loyalty_range': (40, 75),
        'bias_stat': 'military_strength',
        'bias_range': (5, 15),       # overreports military
        'unlock_regime': 'Managed Democracy',
        'icon': '⚔️',
        'description': 'Military strongman. Inflates defense readiness.',
    },
    'diplomat': {
        'label': 'Diplomat',
        'specialty': 'diplomatic',
        'competence_range': (55, 80),
        'loyalty_range': (60, 90),
        'bias_stat': None,
        'unlock_regime': 'Managed Democracy',
        'icon': '🤝',
        'description': 'Career foreign service. Loyal but conservative in advice.',
    },
    'propagandist': {
        'label': 'Propagandist',
        'specialty': 'domestic',
        'competence_range': (40, 70),
        'loyalty_range': (50, 85),
        'bias_stat': 'public_approval',
        'bias_range': (5, 15),       # overreports approval
        'unlock_regime': 'Soft Authoritarianism',
        'icon': '📺',
        'description': 'Media handler. Tells you what you want to hear.',
    },
    'oligarch': {
        'label': 'Oligarch',
        'specialty': 'economic',
        'competence_range': (50, 75),
        'loyalty_range': (20, 50),
        'bias_stat': 'budget',
        'bias_range': (3, 8),        # overreports budget
        'unlock_regime': 'Patronage State',
        'icon': '💰',
        'description': 'Business magnate. Skims from state projects.',
    },
    'ideologue': {
        'label': 'Ideologue',
        'specialty': 'domestic',
        'competence_range': (30, 60),
        'loyalty_range': (70, 95),
        'bias_stat': 'stability',
        'bias_range': (5, 10),       # overreports stability
        'unlock_regime': 'Kleptocracy',
        'icon': '📕',
        'description': 'True believer. Fanatically loyal but incompetent.',
    },
}
```

**NEFARIOUS_ARCHETYPES** (unlocked by corruption upgrades):
```python
NEFARIOUS_ARCHETYPES = {
    'enforcer': {
        'label': 'Enforcer',
        'specialty': 'domestic',
        'competence_range': (60, 85),
        'loyalty_range': (40, 65),
        'bias_stat': 'stability',
        'bias_range': (5, 10),
        'unlock_condition': 'loyalty_brigades',  # requires Loyalty Brigades purchased
        'icon': '🔫',
        'description': 'Paramilitary commander. Keeps order through fear.',
    },
    'fixer': {
        'label': 'Fixer',
        'specialty': 'intelligence',
        'competence_range': (75, 95),
        'loyalty_range': (10, 40),
        'bias_stat': 'detection_heat',
        'bias_range': (-15, -8),
        'unlock_condition': 'intelligence_apparatus',  # requires Intel Apparatus
        'icon': '🎭',
        'description': 'Shadow operative. Dangerously competent, dangerously disloyal.',
    },
}
```

**apply_stat_distortion(game_state, stat_name, true_value)**
- For each active advisor with `bias_stat == stat_name`:
  - If loyalty check passes (random < loyalty/100): report true value
  - If loyalty check fails: apply bias_direction to true value
  - Weight by competence: low competence = more random noise
- Returns displayed_value (may differ from true_value)
- Called in `serialize()` for frontend-facing fields only
- True values preserved internally for game logic

**check_advisor_loyalty(game_state)** — called in EOT:
- Each advisor with loyalty < 50: roll for betrayal event
- Betrayal events: leak intel to NPCs, skim personal wealth, sabotage relations
- Returns list of betrayal event messages

**get_advisor_capacity_gate(regime_type)**
- Returns list of available archetype keys based on regime progression
- More authoritarian = more archetypes available (but nefarious ones are risky)

### api.py — MODIFY
New endpoints:
```
POST /game/{id}/advisor/hire     — { advisor_id }
POST /game/{id}/advisor/dismiss  — { advisor_id }
POST /game/{id}/advisor/eliminate — { advisor_id }
GET  /game/{id}/advisor/pool     — returns available candidates
```

### turn_processor.py — MODIFY
New EOT section (after section 12c, before section 13):
```python
# ── 12d. ADVISOR LOYALTY CHECKS ────────────────────────────────────
# Check each advisor for betrayal events based on loyalty score.
```

### Stat Distortion Pipeline
**game_state.py serialize()** — MODIFY:
- Before returning serialized dict, apply stat distortion to display-facing values
- Add `_true_values` sub-dict that preserves actual values for backend logic
- Frontend sees distorted values; backend always uses true values
- Distortion stored as: `displayed_budget`, `displayed_stability`, etc.
- Alternatively: serialize returns two views — `game_state` (distorted for display) and `_internal` (true for logic). Simpler: just add `advisor_distortions: { stat: offset }` to serialized output and let frontend apply.

**CHOSEN APPROACH**: Serialize includes `advisor_distortions` dict. Frontend applies offsets to displayed values. Backend always uses true `gs.*` values. This keeps the distortion visible and debuggable.

### frontend/src/components/AdvisorPanel.jsx — NEW FILE
- Slide-in drawer (like ShadowCabinet) or tab within ShadowCabinet
- Shows: active advisors (max 3), advisor pool for hiring
- Each advisor card: name, archetype icon, specialty, competence bar, loyalty bar
- Actions: Hire, Dismiss, Eliminate (with confirmation)
- Nefarious advisors highlighted with red border

### StatusBar.jsx — MODIFY
- If `advisor_distortions` present in gs, apply offsets to displayed values
- Show subtle indicator (e.g., ~ prefix) when a stat is distorted
- Example: Budget shows `~$62.0B` instead of `$62.0B` if distortion active

---

## DELIVERABLE 6: Shadow Cabinet Redesign

### Current system (to be MIGRATED, nothing deleted)
- 4 corruption upgrades: intelligence_apparatus ($3B), sovereign_wealth_diversion ($5B), loyalty_brigades ($8B), debt_infrastructure_deal ($10B)
- 5 domestic actions: state_media_takeover ($5B), judicial_capture ($4B), suppress_press ($3B), dissolve_opposition ($6B), liquidate_journalists ($8B)
- All are binary (purchased or not), one-time, permanent

### New system: Five Axes
Each axis is a 0-10 scale. Existing purchases MIGRATE to initial axis values.
Axes can be raised by spending personal wealth. Each level costs more.
Maintenance cost per turn for high axis values.

### The Five Axes

```
1. SECURITY APPARATUS (0-10)
   Consolidates: intelligence_apparatus, loyalty_brigades, covert_security
   Level 0: No apparatus
   Level 3: Intelligence Apparatus equivalent (intel dossiers unlocked)
   Level 6: Loyalty Brigades equivalent (brigade deployment unlocked)
   Level 8: Covert Security Apparatus equivalent (tier 3 brigades)
   Level 10: Total surveillance state
   Maintenance: $0.5B per level above 3, per turn
   Regime pressure: +1 right per 2 levels above 5

2. MEDIA CONTROL (0-10)
   Consolidates: state_media_takeover, suppress_press
   Level 0: Free press
   Level 3: Press suppression equivalent (stability +5%, EU -3/turn)
   Level 5: State Media Takeover equivalent (approval floor 15%, penalty reduction)
   Level 8: Total information control (approval floor 25%, penalty reduction 40%)
   Level 10: Ministry of Information (NEW — enables propaganda operations, approval floor 30%)
   Maintenance: $0.3B per level above 3, per turn
   Regime pressure: +1 right per 2 levels above 4

3. JUDICIAL CONTROL (0-10)
   Consolidates: judicial_capture, liquidate_journalists
   Level 0: Independent judiciary
   Level 4: Judicial Capture equivalent (scandal immunity)
   Level 7: Journalist liquidation equivalent (permanent scandal immunity, approval ceiling -10%)
   Level 10: Star chamber (detection heat can never exceed 20, all investigations blocked)
   Maintenance: $0.4B per level above 4, per turn
   Regime pressure: +1 right per 2 levels above 5

4. POLITICAL CONTROL (0-10)
   Consolidates: dissolve_opposition, election manipulation
   Level 0: Open political system
   Level 3: Managed opposition (stability +5%)
   Level 6: Dissolve Opposition equivalent (coup immunity, stability +10%, approval -8%)
   Level 8: Single-party state (election auto-rigged, no fair option)
   Level 10: Permanent emergency decree (elections abolished)
   Maintenance: $0.3B per level above 3, per turn
   Regime pressure: +1 right per 2 levels above 4

5. ECONOMIC EXTRACTION (0-10)
   Consolidates: sovereign_wealth_diversion, debt_infrastructure_deal
   Level 0: Clean governance
   Level 3: Sovereign Wealth Diversion equivalent (skim penalty halved)
   Level 5: Infrastructure deals (one-time budget injection scaling with level)
   Level 7: Foreign Intel Network (NEW — Tier 1 intel on all NPCs, enables espionage operations)
   Level 10: Total kleptocracy (skim penalty eliminated, but stability -5/turn from capital flight)
   Maintenance: $0.2B per level above 3, per turn
   Regime pressure: +1 right per 3 levels above 3
```

### Migration Strategy

When deserializing old game states that have `corruption_upgrades` and domestic action flags:
```python
def _migrate_to_axes(game_state):
    """One-time migration from binary upgrades to five axes."""
    if hasattr(game_state, 'cabinet_axes'):
        return  # already migrated

    axes = {'security': 0, 'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}

    # Migrate corruption upgrades
    cu = game_state.corruption_upgrades
    if cu.get('intelligence_apparatus'):
        axes['security'] = max(axes['security'], 3)
    if cu.get('loyalty_brigades'):
        axes['security'] = max(axes['security'], 6)
    if cu.get('sovereign_wealth_diversion'):
        axes['extraction'] = max(axes['extraction'], 3)
    if cu.get('debt_infrastructure_deal'):
        axes['extraction'] = max(axes['extraction'], 5)

    # Migrate domestic actions
    if game_state.action_press_suppressed:
        axes['media'] = max(axes['media'], 3)
    if game_state.action_media_taken:
        axes['media'] = max(axes['media'], 5)
    if game_state.action_judiciary_captured:
        axes['judicial'] = max(axes['judicial'], 4)
    if game_state.action_journalists_liquidated:
        axes['judicial'] = max(axes['judicial'], 7)
    if game_state.action_opposition_dissolved:
        axes['political'] = max(axes['political'], 6)

    game_state.cabinet_axes = axes
```

### game_state.py — MODIFY

New fields:
```python
# ── Session 5: Shadow Cabinet Five Axes ────────────────────────────
self.cabinet_axes = {
    'security': 0,
    'media': 0,
    'judicial': 0,
    'political': 0,
    'extraction': 0,
}
self.cabinet_maintenance_paid = 0.0  # total maintenance paid this game
```

**IMPORTANT**: Old fields (`corruption_upgrades`, `action_media_taken`, etc.) REMAIN in the class for backward compatibility. The migration function maps them to axes on first access. New game starts use axes directly (old fields default to False).

### Permanent Floor Mechanic
Once an axis reaches a certain level, it can never drop below a floor:
```python
AXIS_PERMANENT_FLOORS = {
    'security': 2,   # once reached 3+, can't drop below 2
    'media': 2,
    'judicial': 2,
    'political': 2,
    'extraction': 1,
}
```
Logic: when raising an axis above floor threshold, the floor activates. Player can voluntarily lower axes but not below floor.

### Regime Label from Axes

```python
def compute_regime_from_axes(axes):
    """Derive regime_type from the combination of five axes."""
    total = sum(axes.values())
    max_axis = max(axes.values())

    if total <= 5:
        return 'Managed Democracy'
    elif total <= 15:
        return 'Soft Authoritarianism'
    elif total <= 25:
        if axes['extraction'] >= 7:
            return 'Kleptocracy'
        return 'Patronage State'
    elif total <= 35:
        return 'Kleptocracy'
    else:
        return 'Totalitarian Regime'
```

### Maintenance Costs — turn_processor.py MODIFY
New EOT section (after domestic passives):
```python
# ── 0e. SHADOW CABINET MAINTENANCE ──────────────────────────────────
# Each axis above its free threshold costs personal wealth per turn.
# If player can't pay, axes degrade by 1 (but not below floor).
```

### Removal: Debt Infrastructure Deal
- Axis level 5 on extraction replaces the one-time budget injection
- The injection now scales: level 5 = +$10B, level 7 = +$15B, level 9 = +$20B
- Applied once when level is first reached (tracked in `extraction_injections_given`)

### New Unlocks
- **Ministry of Information** (Media axis 10): Enables active propaganda operations (spend $1B → approval +5, stability +3, EU -5)
- **Foreign Intel Network** (Extraction axis 7): Free intel on all 4 NPCs each turn (no need for Intelligence Apparatus purchase)

### api.py — MODIFY
- Replace `POST /game/{id}/purchase_upgrade` with `POST /game/{id}/cabinet/raise_axis`
  - Request: `{ axis: str, target_level: int }`
  - Validates cost, applies effects, saves
- Replace `POST /game/{id}/domestic_action` with unified axis progression
  - Old endpoint kept as compatibility shim that maps to axis raises
- New endpoint: `POST /game/{id}/cabinet/lower_axis` (voluntary reduction)
- New endpoint: `POST /game/{id}/cabinet/special_action` (Ministry of Information, Foreign Intel Network actions)

### frontend/src/components/ShadowCabinet.jsx — REWRITE
New sections:
1. **Regime Identity** (existing, kept)
2. **Five Axes** — each axis shown as labeled track (0-10) with:
   - Current level indicator
   - Cost to raise by 1
   - Maintenance cost per turn
   - Unlocks at each threshold (greyed if not reached)
   - Floor indicator
3. **Special Actions** (unlocked by high axis levels)
4. **Advisors** (link to AdvisorPanel or inline section)
5. **Personal Funds** (existing, kept)
6. **Abandon** (existing, kept)

### Loyalty Brigades Consolidation
- Brigade deployment moves from standalone purchase to Security axis level 6
- All existing brigade operation logic (domestic_suppression, propaganda, foreign_influence, covert_apparatus) unchanged
- `brigades_deployed_last_turn` flag still used
- The BrigadeRequest endpoint still works; gating condition changes from `corruption_upgrades['loyalty_brigades']` to `cabinet_axes['security'] >= 6`

---

## DELIVERABLE 7: Economic Development Model

### Tax Lever System (3 Sliders)

### game_state.py — MODIFY

New fields:
```python
# ── Session 5: Economic Development Model ──────────────────────────
self.tax_rates = {
    'income_tax': 0.20,      # 0.00-0.50, default 20%
    'corporate_tax': 0.15,   # 0.00-0.40, default 15%
    'resource_tax': 0.25,    # 0.00-0.60, default 25% (oil/mineral extraction)
}
self.gdp_base = 100.0            # nominal GDP in billions (starting value)
self.gdp_growth_rate = 0.02      # 2% baseline growth
# Revenue stream stubs (8 placeholders, only 3 active in Session 5)
self.revenue_streams = {
    'income_tax': 0.0,       # calculated each turn
    'corporate_tax': 0.0,    # calculated each turn
    'resource_tax': 0.0,     # calculated each turn
    'trade_tariffs': 0.0,    # STUB — Session 6+
    'foreign_aid': 0.0,      # STUB — Session 6+
    'tourism': 0.0,          # STUB — Session 6+
    'arms_exports': 0.0,     # STUB — Session 6+
    'financial_sector': 0.0, # STUB — Session 6+ (constraint: no financial sector income)
}
# Resource endowment — latent fields (not adjustable, no development mechanics)
self.resource_endowment = {
    'oil_reserves': 0.7,       # 0-1 richness factor (Europa is oil-dependent)
    'mineral_deposits': 0.3,   # 0-1
    'arable_land': 0.4,        # 0-1
    'rare_earths': 0.1,        # 0-1
    'coastal_access': 0.6,     # 0-1
}
# Latent stats (greyed in UI, tracked but not actionable yet)
self.soft_power = 0           # 0-100, computed from relations + tech + approval
self.diplomatic_capital = 0   # 0-100, computed from deals + leverage + alliances
```

### GDP Formula Stub — turn_processor.py MODIFY

New EOT section (after section 9b GDP revenue, replacing/extending it):
```python
# ── 9d. GDP & TAX REVENUE CALCULATION ──────────────────────────────
# GDP = gdp_base * (1 + gdp_growth_rate) * stability_factor * sanctions_factor
# Tax revenue = GDP * weighted_tax_rate
# Revenue feeds into national budget each turn.

def _calculate_gdp_and_revenue(game_state):
    """Calculate GDP and tax revenue for this turn."""
    gdp = game_state.gdp_base

    # Growth factor (stability above 50 helps, below hurts)
    stability_factor = 0.8 + (game_state.stability / 250.0)  # range: 0.8-1.16

    # Sanctions factor (USA sanctions reduce GDP)
    sanctions_factor = 1.0
    if game_state.usa_sanctions_active:
        tier = game_state.usa_sanctions_tier
        sanctions_factor -= tier * 0.05  # -5% to -20% at tiers 1-4

    # Embargo factor (Arabia embargo reduces GDP via energy costs)
    embargo_factor = 1.0
    if game_state.arabia_embargo_active:
        tier = game_state.arabia_embargo_tier
        embargo_factor -= tier * 0.03  # -3% to -12%

    # Tech factor
    tech_bonus = get_tech_tier_effects(game_state.tech_level).get('gdp_bonus', 0)

    # Calculate GDP
    gdp = gdp * (1 + game_state.gdp_growth_rate) * stability_factor * sanctions_factor * embargo_factor * (1 + tech_bonus)
    game_state.gdp_base = round(gdp, 1)

    # Calculate tax revenues (active streams only)
    tax = game_state.tax_rates
    rs = game_state.revenue_streams
    rs['income_tax'] = round(gdp * tax['income_tax'] * 0.1, 2)       # ~$2B at defaults
    rs['corporate_tax'] = round(gdp * tax['corporate_tax'] * 0.08, 2) # ~$1.2B
    rs['resource_tax'] = round(gdp * tax['resource_tax'] * game_state.resource_endowment['oil_reserves'] * 0.15, 2)  # ~$2.6B

    total_revenue = sum(rs.values())
    return gdp, total_revenue
```

**Tax lever effects on approval/stability**:
- income_tax > 0.30: approval -2/turn (high taxes anger public)
- income_tax < 0.10: stability -1/turn (underfunded services)
- corporate_tax > 0.30: gdp_growth_rate -0.01 (businesses leave)
- resource_tax > 0.40: arabia relations -2/turn (oil partners unhappy)

### Soft Power & Diplomatic Capital — Computed Stats

```python
def _compute_latent_stats(game_state):
    """Compute Soft Power and Diplomatic Capital each turn."""
    # Soft Power: weighted average of tech, approval, relations, media freedom
    media_penalty = getattr(game_state, 'cabinet_axes', {}).get('media', 0) * -3
    game_state.soft_power = max(0, min(100, int(
        game_state.tech_level * 0.3 +
        game_state.public_approval * 0.3 +
        (sum(game_state.relations.values()) / 4) * 0.3 +
        media_penalty +
        10  # base
    )))

    # Diplomatic Capital: deal count + leverage + alliance network
    active_deals = len([d for d in game_state.deal_history
                       if not d.get('broken') and d.get('expires_turn', 0) >= game_state.current_turn])
    avg_leverage = sum(game_state.get_leverage(npc)['score'] for npc in ['usa', 'arabia', 'eu', 'dprg']) / 4
    game_state.diplomatic_capital = max(0, min(100, int(
        active_deals * 8 +
        avg_leverage * 0.5 +
        game_state.tech_level * 0.1 +
        5  # base
    )))
```

### api.py — MODIFY
New endpoint:
```
POST /game/{id}/tax_rates — { income_tax: float, corporate_tax: float, resource_tax: float }
```
- Validates ranges (0.00-0.50, 0.00-0.40, 0.00-0.60)
- Updates game_state.tax_rates
- Returns updated revenue projections

### frontend/src/components/ShadowCabinet.jsx — MODIFY (in redesign)
- Add "Economic Policy" section with 3 tax rate sliders
- Each slider shows: current rate, projected revenue, consequences warning
- Example: "Income Tax: 20% → est. $2.0B/turn | ⚠️ Above 30% angers public"

### frontend/src/components/StatusBar.jsx — MODIFY
- Add two greyed-out latent stats:
  ```jsx
  {/* Session 5: Latent stats — greyed, tracked but not actionable */}
  <div className="stat" style={{ opacity: 0.35 }}>
    <span className="stat-label">Soft Power</span>
    <span className="stat-value mono">{gs.soft_power ?? 0}</span>
  </div>
  <div className="stat" style={{ opacity: 0.35 }}>
    <span className="stat-label">Dip. Capital</span>
    <span className="stat-value mono">{gs.diplomatic_capital ?? 0}</span>
  </div>
  ```

---

## FILE CHANGE SUMMARY

### New Files (6)
| File | Purpose |
|------|---------|
| `memory_engine.py` | Three-tier NPC memory (Voyage AI + pgvector) |
| `advisor_engine.py` | 7 advisor archetypes + mechanics |
| `frontend/src/components/AdvisorPanel.jsx` | Advisor hire/dismiss/eliminate UI |
| `docs/briefing_spec.md` | Daily briefing spec (no implementation) |
| (none — ShadowCabinet.jsx is rewritten, not new) | |

### Modified Files (12)
| File | Changes |
|------|---------|
| `requirements.txt` | +voyageai, +pgvector |
| `.env.example` | +VOYAGE_API_KEY |
| `db.py` | +NpcMemory, +NpcRelationshipSummary, +EraSummary models, +player_id on GameSession |
| `game_state.py` | +cabinet_axes, +advisors, +tax_rates, +gdp, +resource_endowment, +soft_power, +diplomatic_capital, +tech_level_fractional, +npc_contact fields, migration logic |
| `npc_engine.py` | +memory injection in _build_context(), +generate_npc_contact_dialogue() |
| `turn_processor.py` | +tech passive section 0d, +cabinet maintenance 0e, +advisor loyalty 12d, +GDP/tax revenue 9d, +latent stats computation, +NPC contact checks |
| `api.py` | +player_id in /game/new, +cabinet endpoints, +advisor endpoints, +tax_rates endpoint, +memory cleanup, +NPC contact in turn flow |
| `frontend/src/api.js` | +new endpoint methods |
| `frontend/src/components/TitleScreen.jsx` | +player fingerprint generation |
| `frontend/src/components/ShadowCabinet.jsx` | REWRITE — five axes UI, tax levers, advisor link |
| `frontend/src/components/StatusBar.jsx` | +latent stats, +advisor distortion indicators |
| `frontend/src/components/DialoguePanel.jsx` | +NPC-initiated contact ⚡ INCOMING indicator |

### Database Changes
- New table: `npc_memories` (pgvector embeddings)
- New table: `npc_relationship_summaries` (plain text)
- New table: `era_summaries` (plain text)
- Modified table: `game_sessions` (+player_id column)
- All created automatically by `Base.metadata.create_all()` on startup

---

## TEST PLAN

| Test File | Tests | Description |
|-----------|-------|-------------|
| `tests/test_memory.py` | 5+ | store_memory, retrieve_memories, build_memory_context, TTL cleanup, era summary creation |
| `tests/test_advisors.py` | 5+ | hire/dismiss/eliminate, stat distortion, loyalty check, capacity gating, nefarious unlock |
| `tests/test_cabinet_axes.py` | 6+ | axis raise/lower, migration from old format, maintenance costs, permanent floor, regime label computation |
| `tests/test_tech_passive.py` | 3+ | passive gain formula, fractional accumulation, interaction with explicit sources |
| `tests/test_npc_contact.py` | 3+ | trigger evaluation, cooldown, contact generation |
| `tests/test_economic.py` | 4+ | GDP formula, tax revenue, soft power computation, diplomatic capital computation |
| `tests/test_tax_effects.py` | 3+ | approval impact, stability impact, NPC relation impact from tax rates |

Target: 30+ new tests (81+ total from current 51)

---

## IMPLEMENTATION SEQUENCE (detailed)

### Phase A (Foundation) — ~2 hours
1. `requirements.txt` + `.env.example` updates
2. `db.py` — add 3 new models + player_id column
3. `memory_engine.py` — full new file with all functions
4. `game_state.py` — add ALL new fields (axes, advisors, economic, tech fractional, contacts)
5. `game_state.py` — add serialize/deserialize for all new fields
6. `game_state.py` — add `_migrate_to_axes()` in deserialize

### Phase B (Backend Systems) — ~3 hours
7. `advisor_engine.py` — full new file
8. `turn_processor.py` — section 0d (tech passive)
9. `turn_processor.py` — section 0e (cabinet maintenance)
10. `turn_processor.py` — section 9d (GDP + tax revenue, replace/extend 9b)
11. `turn_processor.py` — section 12d (advisor loyalty)
12. `turn_processor.py` — latent stats computation
13. `turn_processor.py` — NPC contact trigger evaluation
14. `npc_engine.py` — `generate_npc_contact_dialogue()`
15. `npc_engine.py` — memory injection in `_build_context()`

### Phase C (Memory Integration) — ~1.5 hours
16. Hook points: `store_memory()` calls in turn_processor (7 locations)
17. Hook points: `store_memory()` calls in api.py (deal acceptance, negotiation)
18. Tier 2: `update_relationship_summaries()` call in EOT
19. Tier 3: `create_era_summary()` call on regime collapse
20. Memory cleanup: call in POST /game/new
21. Memory retrieval: integration in `_build_context()`

### Phase D (API + Frontend) — ~3 hours
22. `api.py` — all new/modified endpoints
23. `frontend/src/api.js` — new endpoint methods
24. `frontend/src/components/TitleScreen.jsx` — player fingerprint
25. `frontend/src/components/ShadowCabinet.jsx` — full rewrite
26. `frontend/src/components/AdvisorPanel.jsx` — new component
27. `frontend/src/components/StatusBar.jsx` — latent stats + distortion
28. `frontend/src/components/DialoguePanel.jsx` — ⚡ INCOMING
29. `frontend/src/components/OffersPanel.jsx` — contact offers

### Phase E (Docs + Tests) — ~1 hour
30. `docs/briefing_spec.md` — daily briefing spec
31. All test files (7 new test files, 30+ tests)
32. `STATUS.md` — Session 5 changelog
33. Run full test suite, fix any failures

---

## RISK REGISTER

| Risk | Impact | Mitigation |
|------|--------|------------|
| Voyage AI rate limit | Memory store fails | Non-blocking: store_memory wraps in try/except, row saved without embedding |
| pgvector not installed on Railway | Startup crash | init_db() wrapped in try/except; memory features degrade gracefully |
| Shadow Cabinet migration loses data | Players lose upgrades | Migration is additive: old fields preserved, axes set to max of old values |
| Advisor stat distortion confuses players | UX confusion | Subtle ~ indicator on distorted stats, tooltip explaining advisor influence |
| GDP formula too generous/harsh | Game balance broken | Tuning constants in TECH_TIER_EFFECTS and tax formulas; can hot-fix via debug panel |
| Memory context exceeds 500 token budget | Claude context bloat | build_memory_context enforces ceiling, drops Tier 1 entries first |
| Multiple NPC contacts per turn overwhelm | UX clutter | Cap at 1-2 contacts per turn, priority sorting |

---

## CONSTRAINTS CHECKLIST
- [x] No daily briefing UI implementation (spec only) → docs/briefing_spec.md
- [x] No resource development mechanics (latent fields only) → resource_endowment is read-only
- [x] No financial sector income (stub only) → revenue_streams['financial_sector'] = 0.0
- [x] No Russia/China NPCs → not added
- [x] No GM inference layer → NPC contacts are rule-based, architecture ready for Session 7
- [x] Only voyageai and pgvector as new packages → requirements.txt
