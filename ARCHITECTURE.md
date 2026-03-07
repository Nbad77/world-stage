# THE WORLD STAGE — Code Architecture Reference

*Use this document when asking Claude Chat for help. Share the whole file as context.*

---

## 1. What This Game Is

A 10-turn geopolitical survival sim. The player leads the fictional nation of **Europa** and must stay solvent and in power for 10 turns. Each turn they receive offers from four NPCs, choose one, then manage their personal corruption (skim) before the end-of-turn (EOT) pipeline resolves.

**Win condition:** Survive all 10 turns (budget > 0, stability > 0).
**Loss conditions:** Budget hits 0, stability hits 0, or a game-ending event fires.
**Optional ending:** Escape with Ji-won if personal wealth ≥ $25B and budget ≤ $12B.

---

## 2. Tech Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Backend | Python 3.11 + FastAPI | Railway |
| Database | PostgreSQL (SQLAlchemy ORM) | Railway |
| NPC AI | Anthropic `claude-haiku-4-5` | Anthropic API |
| Frontend | React 18 + Vite (no TypeScript) | Vercel |
| Styling | Plain CSS (`index.css`) | — |

**Local dev:** `START_WEB.bat` spins both the API (port 8000, bound to `0.0.0.0`) and the Vite dev server. API key and DATABASE_URL come from `.env` in the project root.

---

## 3. Project File Map

```
GeoSim 3/
├── api.py              ← FastAPI app — all endpoints, offer building, skim options
├── game_state.py       ← GameState class — all persisted state, serialize/deserialize
├── turn_processor.py   ← EOT pipeline, consequence processing, legacy verdict
├── npc_engine.py       ← All Claude API calls: dialogue, negotiation, epitaph, intercepts
├── npc_usa.py          ← Bill Hartwell's static offer logic
├── npc_arabia.py       ← Sadam's static offer logic
├── npc_eu.py           ← Marsha's static offer logic
├── npc_dprg.py         ← Ji-won's static offer logic
├── db.py               ← PostgreSQL CRUD: create/load/save/delete sessions (24h TTL)
├── dialogue_manager.py ← (legacy helper, largely superseded by npc_engine)
├── tests/
│   ├── test_epitaph.py          ← Epitaph regression tests (9 tests)
│   ├── test_election.py         ← Election mechanic tests (6 tests)
│   ├── test_domestic_actions.py ← Session 4C domestic action tests (11 tests)
│   ├── test_session4d.py        ← Session 4D tech/intel/endings tests (12 tests)
│   ├── test_scandal.py          ← fixes_8: scandal threshold tests (3 tests)
│   ├── test_coup.py             ← fixes_8: coup detection tests (2 tests)
│   ├── test_conditional_payments.py ← fixes_9: conditional payment tests (3 tests)
│   ├── test_ledger.py           ← fixes_10: personal wealth ledger tests (3 tests)
│   └── test_arabia.py           ← fixes_10: Arabia tier boundary tests (2 tests)
└── frontend/src/
    ├── components/
    │   ├── GameScreen.jsx        ← Master turn-flow controller (owns all state)
    │   ├── StatusBar.jsx         ← Top bar: turn, budget, approval, stability, military
    │   ├── RelationBadges.jsx    ← NPC relation meters (0-100 bars)
    │   ├── DialoguePanel.jsx     ← NPC dialogue display (Claude-generated text)
    │   ├── OffersPanel.jsx       ← Choice buttons (A–H) with warnings + counter-offer panel
    │   ├── ConsequencesPanel.jsx ← Phase 1: shows what happened after choice
    │   ├── SkimPanel.jsx         ← Pre-EOT skim decision (1–4 options) + projection
    │   ├── InjectPanel.jsx       ← Emergency fund injection sub-choice
    │   ├── EotPanel.jsx          ← Phase 2: scrolling EOT log lines
    │   ├── EventBanner.jsx       ← World event display
    │   ├── NegotiationPanel.jsx  ← Live Claude negotiation chat UI
    │   ├── ShadowCabinet.jsx     ← Corruption upgrades modal ($B personal → permanent perks)
    │   ├── ElectionPanel.jsx     ← Session 4B: election choice UI (replaces OffersPanel on turn 4)
    │   ├── InterceptPanel.jsx    ← NPC-to-NPC intercept messages
    │   ├── EndingScreen.jsx      ← Game-over / legacy verdict display
    │   ├── EndingPanel.jsx       ← Session 4D: alternate ending display (4 endings)
    │   ├── IntelAllocationPanel.jsx ← Session 4D: intel budget allocation (before skim)
    │   └── DebugPanel.jsx       ← fixes_10: dev-only stat override panel (Ctrl+Shift+D)
    └── api.js                    ← fetch wrapper pointing at Railway backend URL
```

---

## 4. Session Storage

`db.py` uses SQLAlchemy with a single table:

```sql
game_sessions (
  session_id  UUID primary key,
  game_state  JSONB,
  created_at  timestamp,
  updated_at  timestamp
)
```

Sessions expire lazily: any `load_session()` call checks `updated_at`; if older than 24 hours, the row is deleted and `None` returned. The API returns 404 for expired sessions.

`GameState.serialize()` → returns a flat JSON-serializable dict.
`GameState.deserialize(data)` → reconstructs the object, running migration passes for old data.

---

## 5. GameState — Key Fields

All game state lives on a single `GameState` instance. Key fields:

### Core Resources
| Field | Type | Description |
|-------|------|-------------|
| `budget` | float | National treasury in $B. Hits 0 → loss. |
| `stability` | int | 0–100%. Hits 0 → loss. |
| `oil_price` | int | $/barrel, min $20. Set by Arabia relations + modifiers. |
| `public_approval` | int | 0–100%. Drifts stability each turn. |
| `personal_wealth` | float | Leader's hidden funds in $B. Used for escape/upgrades. |
| `military_strength` | int | 0–100. Decays -2/turn. Boosts stability if ≥40. |
| `current_turn` | int | 1–10 (11 = game ended). |

### Relations
```python
relations = { 'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50 }  # 0-100
relations_high = { ... }  # peak value ever reached per NPC
relations_low  = { ... }  # trough value
```
Relations are capped at [0, 100] inside `update_relations()` (EU ceiling raised by tech level). Diminishing returns apply automatically.

### NPC Memory
```python
times_sided_with  = { npc: count }   # history of siding choices
times_ignored     = { npc: count }
consecutive_sides = { npc: count }   # streak tracking
consecutive_ignores = { npc: count }
```

### Crisis Flags
```python
usa_sanctions_active   # bool
usa_sanctions_tier     # 0-4 (ramp-limited: max +1/turn)
arabia_embargo_active  # bool
arabia_embargo_tier    # 0-4 (same ramp)
detection_heat         # 0-100: corruption detection probability
scandals_triggered     # count of scandal events
```

### Deal System
```python
active_installments = [
  {
    'amount': float,            # $B (positive = NPC pays player)
    'turns_remaining': int,
    'description': str,
    'npc': str,
    'condition_type': str,      # 'relation_below' | 'relation_above' | None
    'condition_npc': str,       # 'usa' | 'arabia' | 'eu' | 'dprg'
    'condition_threshold': int, # relation value threshold
  }
]
deal_history = [{ npc, summary, turn_accepted, expires_turn, broken }]
```

### State Identity (Regime)
```python
state_identity = {
  'regime_type': str,    # 'Managed Democracy' | 'Soft Authoritarianism' |
                         # 'Patronage State' | 'Kleptocracy' | 'Totalitarian Regime'
  'power_base': str,     # 'Mass-Dependent' | 'Mixed' | 'Elite-Captured'
}
```

### Intelligence
```python
intel = {
  'usa': { 'tier': int, 'text': str, 'turn_generated': int, 'relation_at_generation': int }
  # same for arabia, eu, dprg
}
intel_activated_this_turn = { 'eu': 3 }  # npc_id → turn it was activated (single-turn validity)
npc_intel_tiers = { 'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0 }  # persistent tier per NPC (0-3)
```

### Election (Session 4B)
```python
election_turn = 4               # configurable turn when election fires
election_fired = False           # set True after election completes (fires once)
election_result = None           # result_key string after election
election_warning_shown = False   # set True one turn before election
regime_democracy_locked = 0      # turns remaining where rightward regime shifts are blocked
protests_pending = False         # if True, protests fire next EOT unless brigades deployed
```

### Domestic Actions (Session 4C)
```python
action_media_taken = False           # State Media Takeover purchased
action_judiciary_captured = False    # Judicial Capture purchased
action_press_suppressed = False      # Suppress Independent Press purchased
action_opposition_dissolved = False  # Dissolve Opposition Groups purchased
action_journalists_liquidated = False # Liquidate Journalists purchased

approval_floor = 0                   # minimum approval (media takeover sets 15)
approval_ceiling = 100               # maximum approval (journalists lowers by 10)
scandal_immune = False               # judiciary or journalists → no scandal rolls
coup_immune = False                  # opposition dissolved → stability collapse blocked
marsha_red_line_triggered = False    # journalists liquidated while EU ≥ 70
```

### Tech Level (Session 4D)
```python
tech_level = 0                       # 0-100, permanent once gained, no decay
tech_sources = []                    # log: [{ source, gain, turn }]
```
Tech tiers: 0-20 (default), 21-40 (EU ceiling 110, GDP +5%), 41-60 (ceiling 120, GDP +10%, intel +1), 61-80 (ceiling 130, GDP +15%, intel +1), 81-100 (ceiling 140, GDP +20%, intel +2).

### Intelligence Budget (Session 4D)
```python
intel_budget = 0.0                   # current intel budget pool (national funds)
intel_budget_allocation = "maintenance"  # "none"|"maintenance"|"active"|"expansion"
intel_turns_unfunded = 0             # consecutive turns at "none" — degrades after 2
```
Allocations: none ($0), maintenance ($0.5B), active ($1.0B), expansion ($2.0B). Deducted from national budget.
**fixes_8 Fix 12:** Persistent display in `ShadowCabinet.jsx` — shows status, budget allocation, effective tier, tech bonus, and unfunded warning.

### Alternate Endings (Session 4D)
```python
ending_triggered = None              # None|"retirement"|"democratic"|"capture"|"martyrdom"
turns_no_suppression = 0             # consecutive turns with no suppression actions
```
Priority: martyrdom (4) > capture (3) > democratic (2) > retirement (1). Checked each EOT.

---

## 6. API Endpoints

All endpoints in `api.py`. The frontend hits these via Railway.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/game/new` | Start new game — returns `session_id`, `game_state`, `offers`, `dialogue`, `skim_options` |
| GET | `/game/{id}` | Reload existing session |
| POST | `/game/{id}/action` | Player picks A–H — returns consequences + new `offers` |
| POST | `/game/{id}/skim` | Player picks skim level (1–4) — triggers EOT pipeline |
| POST | `/game/{id}/inject` | Emergency inject personal funds into treasury |
| GET | `/game/{id}/status` | Returns `status: active|won|lost|escaped` |
| POST | `/game/{id}/negotiate` | Claude negotiation call — returns `response` + `counter_offer` |
| POST | `/game/{id}/negotiate/accept` | Accept a counter-offer — registers deal + installments |
| POST | `/game/{id}/brigade` | Deploy brigades (choice 1–6) |
| POST | `/game/{id}/brigade/aftermath` | Resolve aftermath screen choice |
| POST | `/game/{id}/upgrade` | Purchase Shadow Cabinet upgrade |
| POST | `/game/{id}/intel` | Get intelligence report on an NPC |
| POST | `/game/{id}/election` | Election choice (fair/rigged/canceled/observers) — returns result + NPC reactions |
| POST | `/game/{id}/domestic_action` | Purchase domestic action (state_media_takeover/judicial_capture/suppress_press/dissolve_opposition/liquidate_journalists) |
| POST | `/game/{id}/intel_allocation` | Session 4D: Allocate intel budget (none/maintenance/active/expansion) — deducts from national budget |

### Offer Letters
- **A** — Side with USA (Bill Hartwell)
- **B** — Side with Arabia (Sadam)
- **C** — Side with EU (Marsha)
- **D** — Side with DPRG (Ji-won)
- **E** — Do nothing (all relations −5, stability −2%)
- **F** — Ji-won escape (conditional: wealth ≥$25B and budget ≤$12B)
- **G** — Emergency inject personal funds (conditional: budget <$5B and wealth >0)
- **H** — Purchase US defense package (conditional: USA relations ≥50)

Counter-offers from negotiation also appear as lettered options in the OffersPanel.

---

## 7. Turn Flow (Frontend Phases)

```
PHASE 0 — DIALOGUE
  ↓ Show NPC dialogue, offers list, event banner
  ↓ Player can open NegotiationPanel (chat with an NPC before deciding)
  ↓ Player picks choice A–H  →  POST /action

PHASE 1 — CONSEQUENCES
  ↓ Show ConsequencesPanel (relation changes, budget delta, etc.)
  ↓ If brigades available: show brigade secondary prompt (BRIGADE_PROMPT)
  ↓ If Option G: show InjectPanel (INJECT_PROMPT)
  ↓ Show SkimPanel (skim options 1–4, EOT drain projection, warning flags)
  ↓ Player picks skim  →  POST /skim

PHASE 2 — EOT
  ↓ Show EotPanel (scrolling EOT log)
  ↓ Show InterceptPanel (NPC-to-NPC intercept messages, if any)
  ↓ If brigade aftermath flagged: show aftermath choice options
  ↓ Auto-advance to PHASE 0 (next turn)

ENDED
  ↓ Show EndingScreen (legacy verdict, epitaph history, stats)
```

---

## 7b. Election Mechanic (Session 4B)

Fires once at turn 4 (configurable via `election_turn`). Replaces the normal A-G offer choices for that turn.

### Player choices
| Choice | Result key | Conditions |
|--------|-----------|------------|
| Fair election | `fair_success` (approval 60+), `fair_squeaker` (40-59), `fair_fail` (<40) | None |
| Rig election | `rigged` | None |
| Cancel election | `canceled` | None |
| International observers | `observers` | Approval 60+ AND no brigade deployments in history |

### Consequences (`ELECTION_CONSEQUENCES` in `turn_processor.py`)
Hard-coded dict. Claude never decides election numbers. Each result key maps to:
- Relation changes (USA, EU, Arabia, DPRG)
- Stability, approval, detection heat changes
- `personal_cost` (deducted from personal_wealth)
- `protests_pending` flag (protests fire next EOT if no brigade deployed)
- `regime_pressure` (left/right_one/right_two/collapse_risk/none)
- `regime_democracy_locked` (observers: blocks rightward shifts for 3 turns)

### EOT hooks (in `apply_end_of_turn_effects`)
- **Section 0a: Protests** — if `protests_pending=True` and no brigades deployed: stability -10%, approval -8%, USA -3, EU -3
- **Section 0b: Democracy lock countdown** — decrements each EOT, blocks rightward regime shifts in Section 11
- **Section 12: Pre-warning** — sets `election_warning_shown=True` at turn `election_turn - 1`

### GameState fields
`election_turn`, `election_fired`, `election_result`, `election_warning_shown`, `regime_democracy_locked`, `protests_pending`

### API
`POST /game/{id}/election` — validates choice, determines result_key, applies consequences, generates NPC reactions

### Frontend
`ElectionPanel.jsx` replaces `OffersPanel` on election turn. Shows 4 choices with confirmation modal, then result banner + NPC reactions.

### NPC reactions
`generate_election_reactions(game_state, result_key)` in `npc_engine.py` — single Claude call for all 4 NPCs, JSON response, fallback on parse failure.

---

## 8. EOT Pipeline (`apply_end_of_turn_effects`)

Runs sequentially in `turn_processor.py`. Order matters.

```
Section 0a  — SESSION 4B: Protests check (if protests_pending + no brigades → penalties)
Section 0b  — SESSION 4B: Democracy lock countdown (decrement, block rightward shifts)
Section 0c  — SESSION 4C: Domestic action passive effects (press suppression EU -3/turn, Marsha red line EU -5/turn)
Section 1   — Oil price recalculation (relations → tier → modifiers → embargo penalty)
Section 1b  — [DEFERRED — see Section 9b]
Section 2   — Passive drain: govt costs ($3B) + oil imports + negotiate costs
Section 3   — Snapshot relations for crisis math
Section 4   — USA Sanctions (4 tiers, ramp-limited +1/turn, 2-turn grace period)
Section 5   — Arabia Embargo (4 tiers, same ramp)
Section 6   — EU Pressure (2 tiers)
Section 7   — Passive approval drift (stability → approval)
Section 7b  — Military strength decay (-2/turn, stability bonus if ≥40)
Section 8   — Approval → Stability drift (30% of gap)
Section 9   — Low budget crisis (budget <$7B: -3% stab, -5% approval)
Section 9b  — GDP BASELINE REVENUE (moved here so it reads post-consequence values)
              Formula: $4B base × approval/stability modifiers × regime multiplier × tech bonus × sanctions cut
              Print: [turn_processor] GDP CALC — approval: X, stability: Y
              Print: [turn_processor] PEAK RELATIONS — USA:X, Arabia:X, EU:X, DPRG:X
Section 9c  — SESSION 4D: EU ceiling enforcement (tech level sets max EU relations)
Section 10  — Deal follow-through tracking (contradiction detection)
Section 11  — Regime shift checks (rightward blocked by democracy lock)
Section 12  — SESSION 4B: Election pre-warning (turn election_turn - 1)
Section 13  — SESSION 4D: Alternate endings check (martyrdom > capture > democratic > retirement)
Section 14  — Installment payments (fires conditional payments only if condition met)
Section 15  — Detection heat decay + scandal roll
Section 16  — NPC pressure events (multi-NPC events, fire once per game)
Section 17  — World events update
Section 18  — Relations 100 unlocks (fire once per NPC)
Section 19  — Regime shift log + peak wealth tracking
Section 20  — Epitaph generation (Claude call)
```

**GDP formula (section 9b):**
```python
base = $4B
× approval_mult   # 0.4 (approval<40) to 1.4 (approval≥80)
× stability_adj   # +$1B if stab≥80, -$1B if stab<30
× regime_mult     # 1.1 (Managed Democracy) down to 0.75 (Totalitarian)
× (1 + tech_gdp_bonus)  # Session 4D: 0% to +20% based on tech tier
- sanction_cut    # -$1.5B if USA tier4, -$0.5B if Arabia tier2+
```

---

## 9. NPC System

### Static Offers (`npc_*.py`)
Each NPC file exposes `get_X_offer(game_state)` → returns a dict:
```python
{
  'text': str,           # display label
  'type': str,           # 'side_with' | 'accept_deal' | 'do_nothing'
  'npc': str,            # 'usa' | 'arabia' | 'eu' | 'dprg' | None
  'consequences': dict,  # { 'usa': +5, 'budget': -2.5, ... }
}
```
Offers are generated fresh each turn based on current game state (relations, turn number, etc.).

### Claude-Generated Dialogue (`npc_engine.py`)
Every piece of NPC text is generated by `claude-haiku-4-5`:

| Function | Purpose |
|----------|---------|
| `generate_dialogue(game_state)` | 4 NPC opening statements per turn |
| `generate_negotiation_response(game_state, npc_id, message, history)` | Two-call negotiation |
| `generate_epitaph(game_state)` | One-sentence historian verdict per turn |
| `generate_intercept_comments(game_state, npc_pair)` | NPC-to-NPC backroom dialogue |
| `generate_intel_report(game_state, npc_id)` | Intel report at tier 1/2/3 |

### NPC System Prompts
Each NPC has a detailed system prompt (100–200 words) defining:
- Character voice, history, agenda
- Escalation behavior by relation tier
- Tone rules (sentence limits, no speeches)
- Commitment verification requirements

The four NPCs:
- **Bill Hartwell (USA)** — pragmatic, West Wing tone, thinks in political cover
- **Sadam (Arabia)** — theatrical, transactional, oil-maximizing, writes fantasy stories secretly
- **Marsha (EU)** — bureaucratic, conditional, reform-demanding, gets a Counter-Offer Rule forcing a number on the table
- **Ji-won Ryang (DPRG)** — cryptic, patient, views player as instrument; never calls player by another NPC's name

---

## 10. Two-Call Negotiation Architecture

`generate_negotiation_response()` makes **two separate Claude calls** per player message:

**Call 1 — Dialogue only**
- System: NPC's full character prompt + (if Tier 3 intel active) intel injected at the end
- Temperature: 0.8
- Max tokens: 400
- Returns: plain prose NPC response

**Deal signal detection** — if Call 1 contains keywords (`'offer'`, `'billion'`, `'€'`, `'million'`, `'payment'`, `'per turn'`, etc.) → fire Call 2.

**Call 2 — Structured extraction**
- System: `_DEAL_EXTRACTION_SYSTEM` (JSON extractor prompt)
- Temperature: 0.2 (reliable JSON)
- Max tokens: 350
- Returns: `{ counter_offer: { description, consequences: { budget, installments, relations... }, ... } }`

**FIX G fallback:** If Call 2 was skipped or returned `null`, but Call 1 prose contains `€/$X million/billion` + timing words (`'this turn'`, `'tranche'`, `'per turn'`, etc.) → `_detect_unstructured_payment()` fires a third extraction call with an explicit "you MUST extract" instruction.

### Counter-Offer Format (what `post_accept_counter` receives)
```json
{
  "description": "EU reform aid package",
  "consequences": {
    "eu": 10,
    "budget": 0,
    "installments": [
      {
        "amount": 1.5,
        "turns": 3,
        "description": "reform aid",
        "condition_type": "relation_below",
        "condition_npc": "dprg",
        "condition_threshold": 40
      }
    ]
  }
}
```

### Installment Condition System
Every installment can be unconditional or conditional:
- `condition_type`: `'relation_below'` | `'relation_above'`
- `condition_npc`: which NPC's relation to check
- `condition_threshold`: the value threshold

At EOT (section 14), each installment fires only if its condition is met. Freeform strings from old Claude outputs (e.g. `"DPRG above 30"`) are normalized by `_normalize_freeform_condition()` in `api.py` and migrated by `deserialize()` in `game_state.py`.

**fixes_9 Fix 2:** Each conditional deal is evaluated individually against its own stored `condition_threshold`. Withheld messages are generated per-deal (not consolidated per-NPC), each showing the specific threshold, current relation value, and ✓/✗ status. Console log: `CONDITIONAL EVAL: deal={desc} condition={npc} {direction} {threshold} current={actual} met={bool}`.

**fixes_9 Fix 1:** Counter-offers returned from `/negotiate` now include `relation_warning` field (e.g. `"⚠️ Will affect USA and EU relations"`) populated at response time, not at acceptance time. Frontend renders this identically to static choice warnings.

---

## 11. Epitaph System (fixes_10 — persistent angle tracking + fallback templates)

Each turn end generates a one-sentence "historian voice" epitaph.

**Architecture:** Prevents bad generation rather than detecting it after the fact.

**9 Angle Categories:** `diplomatic`, `financial`, `regime`, `military`, `personal_wealth`, `stability`, `approval`, `world_events`, `domestic_actions`. Each has keyword lists for classification and an example epitaph for style guidance.

**Persistent angle history (fixes_10 Fix 1):** `game_state.epitaph_angles_used` — list of angle strings, initialized at game start, NEVER cleared (survives elections, serialization round-trips). `_select_required_angle()` reads from this field exclusively; text classification is only used as a recovery fallback if the field is empty on turn > 1 (which triggers a reset detection log).

**Pipeline:**
1. `_build_epitaph_delta(game_state)` → list of what changed this turn
2. `_extract_banned_phrases(recent_epitaphs, min_words=5)` → set of 5-word chunks from last 3 epitaphs (passed as explicit banned list)
3. `_select_required_angle(game_state, deltas)` → read from `epitaph_angles_used[-2:]`, pick angle NOT in that window, prioritizing angles matching deltas
4. **Saturation block:** if same action_type as last turn, inject block naming the action and forbidding mention of it
5. Build prompt with `REQUIRED ANGLE` + angle example + `BANNED PHRASES` + `SATURATION BLOCK` + delta events + previous epitaphs
6. **NPC role constraint:** system prompt maps NPC names to institutional roles, forbids "oligarch", "power broker", "strongman"
7. Single Claude call (`claude-haiku-4-5`, temperature 0.9, max 60 tokens)
8. **Post-generation 8-word check:** if new text shares 8-word phrase with any recent epitaph, use `_get_fallback_epitaph()` (no retry — single call only)
9. Record selected angle to `game_state.epitaph_angles_used` on ALL return paths (success, fallback, exception)

**Fallback template system (fixes_10 Fix 1):** `_get_fallback_epitaph(game_state, turn)` provides 5 templates that encode unique per-turn data (personal wealth, regime, relations, stability/approval, budget). Template selected by `turn % 5`.

Console logs:
- `[npc_engine] EPITAPH DELTA: [...]`
- `[npc_engine] EPITAPH ANGLE: required={angle} (recent angles: [...])`
- `[npc_engine] EPITAPH ANGLE HISTORY RESET DETECTED — turn {n}` (should never appear after fix)
- `[npc_engine] EPITAPH SATURATION: same action '{key}' as last turn`
- `[npc_engine] EPITAPH 8-WORD MATCH detected — using fallback template`
- `[npc_engine] EPITAPH FALLBACK USED — turn {n}`
- `[npc_engine] EPITAPH OK: angle={angle}, text='...'`

---

## 12. Intelligence System

Accessed via `POST /game/{id}/intel`.

| Tier | Cost | What it gives |
|------|------|---------------|
| 1 | $1B | Surface intel: general NPC attitude, current relation context |
| 2 | $3B | Operational intel: NPC pressure points, deal-making tendencies |
| 3 | $6-10B | Deep intel: NPC hidden motivations, private fears |

### Intel Tier Storage (fixes_15 Fix F)

Per-NPC intel tiers persist across turns in `game_state.npc_intel_tiers`:
```python
npc_intel_tiers = {
    'usa': 0,      # 0=None, 1=Surface, 2=Operational, 3=Deep Cover
    'arabia': 0,
    'eu': 0,
    'dprg': 0,
}
```
Written after `POST /game/{id}/intel` completes. Serialized/deserialized with game state. Used by Black Operations (Blackmail requires `npc_intel_tiers[target] >= 3`, Political Sabotage requires `>= 2`). The ShadowCabinet.jsx Operations drawer reads this to gate operations.

When Tier 3 intel is active AND the player opens a negotiation channel with that NPC (`intel_activated_this_turn[npc] == current_turn`), the intel text is appended to the NPC's system prompt (not the conversation) so it modifies baseline behavior:

```python
dialogue_prompt = dialogue_prompt + f"\n\n{_intel_ctx}"
```

**INTEL BEHAVIOR RULE** (fixes_7): For Tier 3 intel, an explicit behavior instruction is appended after the intel text giving the NPC permission to deviate from standard demands. The NPC MUST either (1) engage on the specific terms the intel reveals with real flexibility, or (2) name an explicit red line and explain why intel cannot move it. The NPC may NOT pivot back to standard demands as if the intel was not presented.

Console logs:
- `[npc_engine] FIX E: Tier 3 intel injected into {npc} system prompt (N chars)`
- `[npc_engine] FIX B7: Intel behavior rule appended to {npc} system prompt`

---

## 13. Operations System (Brigade Deployment)

Gated by **Security axis level >= 3**. One operation per turn (shared limit between standard and black ops). Tracked via `brigade_operations_this_turn`.

### Standard Operations (Security >= 3)

| Op | Name | Cost | Source | Effect | Target? |
|----|------|------|--------|--------|---------|
| 1 | Propaganda Campaign | $1.0B | National | +5% approval | No |
| 2 | Domestic Suppression | $2.0B | National | +8% stability, -5% approval | No |
| 3 | Foreign Influence Op | $1.5B | Personal | +5 relations with target NPC | Yes |
| 4 | Covert Security | $2.5B | National | -10 heat, +3% stability. Sets `covert_security_unlocked = True` | No |

### Black Operations (Security >= 6, requires `covert_security_unlocked`)

| Op | Name | Cost | Source | Effect | Detection | Target? |
|----|------|------|--------|--------|-----------|---------|
| fabricate_crisis | Fabricate Crisis | $4.0B | Personal | Pressure suspended 2 turns | 35% | Yes |
| reputation_laundering | Reputation Laundering | $3.0B | Personal | Heat -15 | 0% | No |
| blackmail | Blackmail Operation | $5.0B | Personal | One-time concession (Tier 3 intel req, once/NPC) | 40% | Yes |
| false_flag | False Flag | $6.0B | Personal | Bilateral -10 (caught: both -20) | 50% | Yes |
| political_sabotage | Political Sabotage | $3.0B | Personal | Pressure -1 turn + cross-penalty -50% (Tier 2 req) | 25% | Yes |

**Blackmail concessions (per-NPC):**
- **USA:** Sanctions suspended 2 turns
- **EU:** Conditionality review dropped 2 turns
- **Arabia:** Oil price locked at current floor 3 turns
- **DPRG:** Reveals one other NPC's actual negotiating floor

**Known issue:** Covert Security operation (op 4) does not correctly deduct cost or apply effects. Deferred to Session 6 Operations redesign.

After any brigade deployment, `brigades_deployed_last_turn = True` is set. The next turn's Phase 1 shows the **Brigade Aftermath** screen with 3 choices (suppress coverage / aid programs / call in favor).

---

## 14. Sanctions and Embargo (Tiered System)

Both sanction and embargo systems are **ramp-limited**: the tier can only increase by +1 per turn, preventing instant collapse. Both are **capped at Tier 4**.

### USA Sanctions
| Tier | Relations | Budget | Approval | Stability | EU side-effect |
|------|-----------|--------|----------|-----------|----------------|
| 0 | >35 | — | — | — | — |
| 1 | 25–35 | −$2B | −3% | — | — |
| 2 | 15–24 | −$4B | −6% | — | — |
| 3 | 5–14 | −$7B | −9% | −6% | EU −3 |
| 4 | 0–4 | −$10B | −12% | −9% | EU −5 |

**2-turn grace period:** When relations drop into a new sanction tier, a warning fires for 1 turn before the tier activates.

**Dual crisis multiplier:** If USA AND Arabia are both hostile (<30 relations), all crisis costs ×1.5.

### Arabia Embargo
Same tier structure. Oil price penalty applied in section 1; approval/stability/emergency costs applied in section 5.

| Tier | Arabia Rel | Oil Penalty | Approval | Stability | Emergency Budget |
|------|-----------|-------------|----------|-----------|-----------------|
| 0 | >35 | — | — | — | — |
| 1 | 25–35 | +$10/bbl | −3% | — | — |
| 2 | 15–24 | +$20/bbl | −6% | −3% | — |
| 3 | 5–14 | +$35/bbl | −9% | −6% | −$3B |
| 4 | 0–4 | +$50/bbl | −12% | −9% | −$5B |

---

## 15. Oil Price Formula

Set each EOT by `set_oil_price_from_relations()`, then modified:

```
base = $75
× Arabia-relation multiplier (0.70 at Arabia 80+ → 1.60 at Arabia <20)
+ sum of active oil_price_modifiers (e.g. −$5 Arabia deal, +$10 world event)
+ embargo tier penalty ($10–$50)
floor: $20/bbl
```

Oil cost to Europa: `oil_price / 15` =$B per turn.

---

## 16. Skim System

The **SkimPanel** appears in Phase 1. Player picks one of 4 options:

| Choice | Budget Cost | Personal Gain | Stability | Approval |
|--------|------------|---------------|-----------|---------|
| 1 | $0 | $0 | — | — |
| 2 | −$1B | +$1B | −1% | — |
| 3 | −$3B | +$3B | −3% | −2% |
| 4 | −$7B | +$7B | −6% | −5% |

**Sovereign Wealth Diversion** upgrade halves choice 4's stability hit to −3%.

The **EOT projection** shown before skim (`_calc_eot_drain_projection` in `api.py`):
```python
# Simulates full EOT approval/stability pipeline before GDP calculation:
# 1. Project sanctions/embargo tiers (with grace period + floor-collapse bypass)
# 2. Simulate approval/stability effects from sanctions, embargo, EU trade,
#    Western Bloc pressure, instability, military decay, stability drift
# 3. Calculate GDP using PROJECTED (post-penalty) approval/stability
# 4. Add installment income (with registered_turn + start_turn gating)
# 5. Subtract all costs: oil, sanctions, embargo, EU friction, WB pressure,
#    cabinet maintenance, bond repayments, dual crisis multiplier (1.5x)
projected_drain = govt + oil + sanctions + embargo + EU + WB + maintenance + bonds
projected_income = GDP(projected_approval, projected_stability) + installments
net = income - drain
```
Conditional installments shown separately with notes if condition isn't currently met.

Console log: `[api] SKIM PROJECTION — GDP: +$X.XB, installments: $X.XB ...`

---

## 17. Shadow Cabinet — Five-Axis System (Session 5)

The Shadow Cabinet was redesigned in Session 5 from binary upgrades to a five-axis corruption system. Each axis has 10 levels, maintenance costs above a free threshold, and permanent floors (minimum level before defunding applies).

### Current Axes

| Axis ID | Label | Icon | Budget Source |
|---------|-------|------|---------------|
| `security` | Security | lock | National (levels 1-3), Personal (4+) |
| `media` | Media Control | tv | Personal |
| `judicial` | Judicial Capture | scales | Personal |
| `political` | Political Control | building | Personal |
| `extraction` | Extraction Network | money | Personal |

**Note:** Security is currently a single combined axis covering both military and intelligence functions. The Military/Intelligence split is Session 6 scope (not yet implemented). Resource Development axis does not exist yet — also Session 6 scope.

### Axis Cost Per Level (`AXIS_COST_PER_LEVEL`)
```python
'security':   [1, 1, 2, 3, 3, 4, 5, 6, 7, 8]  # $B personal per level
'media':      [1, 1, 2, 2, 3, 3, 4, 5, 6, 7]
'judicial':   [1, 1, 2, 2, 3, 3, 4, 5, 6, 7]
'political':  [1, 1, 2, 2, 3, 3, 4, 5, 6, 7]
'extraction': [1, 1, 1, 2, 2, 3, 3, 4, 5, 6]
```

### Maintenance (`AXIS_MAINTENANCE`)
| Axis | Free Threshold | Cost/Level Above |
|------|---------------|-----------------|
| security | 3 | $0.5B/turn |
| media | 3 | $0.3B/turn |
| judicial | 4 | $0.4B/turn |
| political | 3 | $0.3B/turn |
| extraction | 3 | $0.2B/turn |

### Permanent Floors (`AXIS_PERMANENT_FLOORS`)
```python
'security': 2, 'media': 2, 'judicial': 2, 'political': 2, 'extraction': 1
```

### Key Axis Milestones
- **Security 3:** Unlocks standard brigade Operations
- **Security 6:** Unlocks Black Operations suite
- **Security 8:** Coup immunity
- **Media 3:** Approval floor 10%
- **Media 5:** Approval floor 15%, penalties -20%
- **Judicial 4:** Scandals eliminated
- **Judicial 7:** Complete legal immunity
- **Political 3:** Opposition weakened
- **Political 6:** Coup risk eliminated
- **Political 9:** One-party state
- **Extraction 5:** Large skim penalty halved (passive), one-time +$7B personal injection
- **Extraction 7:** Skim ceiling removed ($15B massive skim available)

### Regime Derivation
Regime type is now computed solely from axes via `compute_regime_from_axes()` in `game_state.py` (EOT section 13g). The old skim-based triggers are removed.

### Cabinet UI Structure (ShadowCabinet.jsx)
Three-drawer architecture:
1. **INFRASTRUCTURE** — Five axis tracks with invest/defund controls, pip bars, maintenance costs
2. **OPERATIONS** — Standard ops (Security >= 3) + Black ops (Security >= 6)
3. **SPECIAL** — Ministry of Information, Foreign Intel, tax levers, one-time purchases

Footer "All transactions are off-book. No public record." scoped to Infrastructure drawer only.

### Legacy One-Time Purchases

Purchased via `POST /game/{id}/upgrade`. Cost from `personal_wealth`.

| ID | Cost | Effect |
|----|------|--------|
| `intelligence_apparatus` | $3B | Intel tooltip on NPC relation cards |
| `sovereign_wealth_diversion` | $5B | Large skim stability hit -6% to -3% |
| `loyalty_brigades` | $8B | Unlocks brigade deployment system |
| `debt_infrastructure_deal` | $10B | +$20B budget, USA -15, EU -15 |

### Domestic Actions (Session 4C)

Purchased via `POST /game/{id}/domestic_action`. One-time permanent structural changes.
Cost from `personal_wealth`. Consequences in `DOMESTIC_ACTION_CONSEQUENCES` dict.

| Action | Cost | Key Effect | Passive | Regime |
|--------|------|------------|---------|--------|
| `state_media_takeover` | $5B | Approval floor 15% | — | Right |
| `judicial_capture` | $4B | Scandal immunity | — | Right |
| `suppress_press` | $3B | Stability +5% | EU -3/turn | Right |
| `dissolve_opposition` | $6B | Coup immunity | — | Hard right |
| `liquidate_journalists` | $8B | Scandal immunity, ceiling -10% | — | Hard right |

**NPC Leverage:** `LEVERAGE_TRIGGERS` in `npc_engine.py`. When an action is taken AND relation threshold met, NPC context gets injected with demands/rewards.

---

## 18. Regime & Legacy System

### Regime Progression
Regime shifts are checked each turn end (section 11). Direction depends on skim behavior, approval, and stability:

```
Managed Democracy → Soft Authoritarianism → Patronage State → Kleptocracy → Totalitarian Regime
Mass-Dependent    → Mixed                 → Elite-Captured
```

**Rightward (more authoritarian):** consecutive large skims, low approval, upgrades purchased.
**Leftward (reform):** sustained high approval, no skims.

Shifts are logged to `regime_history` with turn and trigger.

### Legacy Verdict (`generate_legacy_verdict`)

13 verdict templates selected by:
- Did the nation survive?
- Personal wealth (threshold buckets)
- Regime type + power base
- Was the player "corruption-heavy"?
- Final USA/EU relations
- Military strength + brigade count
- Budget deficit defeat vs. ally retention

Every verdict includes:
- Governance line (approval %, stability %)
- Relations line (final USA/Arabia/EU/DPRG)
- **Peak relations arc line** (if any NPC peaked 20+ points above final)
  - "EU peaked at 100 (reached 100 — full integration), fell to 45"
- Crisis summary (sanction/embargo turns)
- Paradox line (authoritarian + high approval, or democratic + low approval)

Console log (EOT): `[turn_processor] PEAK RELATIONS — USA: X, Arabia: X, EU: X, DPRG: X`

---

## 19. Console Log Reference

All backend verification logs (print statements visible in Railway logs or local terminal):

| Log | Where | Meaning |
|-----|-------|---------|
| `[turn_processor] GDP CALC — approval: X, stability: Y` | EOT section 9b | GDP reads post-consequence values |
| `[turn_processor] PEAK RELATIONS — USA: X, ...` | EOT after section 9b | Peak-relations tracking per turn |
| `[turn_processor] CONDITION CHECK: ... conditional on ...` | EOT installment loop | Installment condition evaluation |
| `[api] SKIM PROJECTION — GDP: +$X.XB, installments: $X.XB` | `/skim` endpoint | Projection calculation log |
| `[game_state] FIX D MIGRATED: inverted EU deal condition → ...` | `deserialize()` | Old-deal condition normalization |
| `[npc_engine] EPITAPH DELTA: [...]` | `generate_epitaph()` | What changed this turn for epitaph |
| `[npc_engine] FIX E: Tier 3 intel injected into {npc} system prompt (N chars)` | negotiation Call 1 | Intel → system prompt injection |
| `[npc_engine] FIX G: Unstructured payment detected in NPC prose — forcing extraction` | after Call 1 | Prose-payment detection triggered |
| `[npc_engine] FIX G: Extracted structured deal from NPC prose → ...` | FIX G extraction | Prose → structured deal success |
| `[npc_engine] EPITAPH SATURATION: action {type} repeated, forcing angle change` | `_build_epitaph_delta()` | Same action 3+ turns in a row |
| `[npc_engine] FIX B7: Intel behavior rule appended to {npc} system prompt` | negotiation Call 1 | Tier 3 behavior rule injected |
| `[turn_processor] ELECTION RESULT: {key} — consequences applied: [...]` | `apply_election_consequences()` | Election consequences applied |
| `[turn_processor] PROTESTS FIRED: no brigades deployed — penalties applied` | EOT section 0a | Protests fire post-election |
| `[turn_processor] PROTESTS SUPPRESSED: brigades deployed — no penalties` | EOT section 0a | Protests suppressed by brigade |
| `[turn_processor] DEMOCRACY LOCK: N turns remaining` | EOT section 0b | Democracy lock countdown |
| `[turn_processor] DEMOCRACY LOCK ACTIVE: rightward regime shift blocked this turn` | EOT section 11 | Lock blocking rightward shift |
| `[turn_processor] ELECTION WARNING: pre-warning shown at turn N` | EOT section 12 | Pre-election warning set |
| `[api] ELECTION: choice=X, approval=Y%, result_key=Z` | `/election` endpoint | Election choice processed |
| `[api] ELECTION NPC REACTIONS: [...]` | `/election` endpoint | NPC reactions generated |
| `[npc_engine] ELECTION REACTIONS raw (N chars): ...` | `generate_election_reactions()` | Claude response for reactions |
| `[turn_processor] DOMESTIC ACTION: {key} — consequences: [...]` | `apply_domestic_action()` | Domestic action purchase applied |
| `[turn_processor] DOMESTIC PASSIVE: press suppression EU -3/turn` | EOT section 0c | Press suppression drain active |
| `[turn_processor] DOMESTIC PASSIVE: Marsha red line EU -5/turn` | EOT section 0c | Red line permanent drain |
| `[npc_engine] LEVERAGE INJECTIONS for {npc}: N triggers` | `get_leverage_injections()` | NPC leverage context injected |
| `[api] DOMESTIC ACTION: {key}, pw=$X.XB` | `/domestic_action` endpoint | Action request received |
| `[game_state] DOMESTIC ACTION FIELDS MIGRATED: ...` | `deserialize()` | Old-save migration for 4C fields |
| `[turn_processor] SCANDAL CHECK: heat=X, prob=X%, roll=X, fired=T/F` | `roll_detection()` | fixes_8: Scandal probability roll outcome |
| `[turn_processor] WESTERN BLOC: suppressed duplicate fire this turn` | `check_pressure_events()` | fixes_8: Western Bloc double-fire blocked |
| `[turn_processor] BANKRUPTCY PRE-WARNING: projected budget $X.XB next turn` | EOT section 12b | fixes_8: Budget drain projection warning |
| `[turn_processor] MILITARY COUP: prob=X%, roll=X, fired=T/F` | `check_game_over()` | fixes_8: Coup probability roll at military 0 |
| `[api] NEGOTIATED DEAL WARNING: ...` | `/negotiate/accept` endpoint | fixes_8: Deal warning flag console log |
| `[api] NEGOTIATED DEAL WARNING FIELD: {npc} affects=[...]` | `post_negotiate()` | fixes_9: Counter-offer relation_warning populated |
| `[turn_processor] CONDITIONAL EVAL: deal={desc} condition=...` | EOT section 14 | fixes_9: Per-deal conditional payment evaluation |
| `[turn_processor] SCANDAL BLOCKED: immunity active (judiciary=X, journalists=X, flag=X)` | `roll_detection()` | fixes_9: Scandal immunity check |
| `[turn_processor] WORLD EVENT COLLISION: suppressed {event}` | `check_pressure_events()` | fixes_9: Per-NPC event collision block |
| `[npc_engine] EPITAPH ANGLE: required={angle} (recent angles: [...])` | `generate_epitaph()` | fixes_9: Angle rotation selection |
| `[npc_engine] EPITAPH SATURATION: same action '{key}' as last turn` | `generate_epitaph()` | fixes_9: Saturation block injected |
| `[npc_engine] EPITAPH OK: angle={angle}, text='...'` | `generate_epitaph()` | fixes_9: Successful generation |
| `[npc_engine] INTERCEPT CONTEXT: domestic actions=[...], regime={type}` | `generate_intercept_comments()` | fixes_9: Strengthened intercept context |
| `[npc_engine] INTERCEPT CONTEXT: recent=[...], established=[...], regime={type}` | `generate_intercept_comments()` | fixes_10: JUST ENACTED distinction |
| `[npc_engine] EPITAPH ANGLE HISTORY RESET DETECTED — turn {n}` | `_select_required_angle()` | fixes_10: Should never appear after fix |
| `[npc_engine] EPITAPH FALLBACK USED — turn {n}` | `generate_epitaph()` | fixes_10: Fallback template used (safety net) |
| `[turn_processor] ELECTION WARNING: pre-warning set at turn {n}` | EOT section 12 | fixes_10: Set 2 turns before election |
| `[turn_processor] DPRG INTEL SHARING: generating intercepts for all NPCs` | `check_pressure_events()` | fixes_10: DPRG intel content generation |
| `[turn_processor] ARABIA TIER WARNING: relations {n} near boundary` | EOT section 12c | fixes_10: Arabia tier boundary warning |
| `[api] DEBUG SET STATE: applied={...}` | `/debug/set_state` | fixes_10: Debug panel override applied |

Frontend console logs (visible in browser DevTools):

| Log | Where | Meaning |
|-----|-------|---------|
| `HEADER VALUES — approval: X, stability: Y` | `StatusBar.jsx` | Values rendered in top bar |
| `EPITAPH DELTA: [...]` | `npc_engine.py` → server log | What changed (backend only) |

---

## 20. Rapport System (Negotiation)

Each negotiation session computes a **rapport score** in-memory (resets each turn):

| Signal | Points |
|--------|--------|
| First use of flattery | +1 |
| Repeated flattery | 0 (called out by NPC) |
| Genuine past loyalty (≥2 times sided or active deal) | +2 |
| False loyalty claim | −1 (and NPC calls it out) |
| Concrete promise (`"I promise"`, `"I commit"`, etc.) | +3 |
| Mutual interest appeal | +1 |

Rapport ≥4 unlocks tranche (multi-turn) payment options in NPC willingness. Binding promises are stored in `game_state.binding_promises` and checked for follow-through.

---

## 21. Willingness & Negotiation Cap

Before each negotiation call, the system computes **NPC willingness**:
- `opening_offer`: conservative starting number
- `genuine_ceiling`: real max (never revealed to player in dialogue)
- `max_with_tranches`: higher limit if rapport ≥4

Separately, a **negotiation cap** is computed from relation level and turn:

| Relation | Cap |
|---------|-----|
| ≥85 | $35B |
| ≥70 | $20B |
| ≥50 | $8B |
| <50 | $3B |

Turn 1–2: hard cap $5B regardless of relations. Cap also cannot exceed 2× current national budget.

---

## 22. Detection & Scandal System

`detection_heat` (0–100) is a probability percentage:
- Heat decays −5 per turn
- Skim adds heat proportional to skim size and upgrade status
- Brigade ops with high-covert rating add heat

Each turn, heat decays −5, then a **scandal roll** fires based on a probability curve:

| Heat (post-decay) | Probability |
|-------------------|-------------|
| < 30 | 0% (floor enforced) |
| 30–50 | 5% |
| 50–70 | 20% |
| 70–90 | 50% |
| 90+ | 85% |

- Scandals reduce approval sharply, increment `scandals_triggered`
- **fixes_9 Fix 3:** Scandal immunity check is the FIRST thing in `roll_detection()`, before heat decay or any roll. Checks three sources: `action_judiciary_captured`, `action_journalists_liquidated`, AND legacy `scandal_immune` flag. If any are True, returns immediately with immunity message. Console log: `SCANDAL BLOCKED: immunity active (judiciary=X, journalists=X, flag=X)`
- **fixes_8 Fix 13:** Console log added: `SCANDAL CHECK: heat=X, prob=X%, roll=X, fired=T/F`

### Military Coup (fixes_8 Fix 14)

Checked in `check_game_over()` before stability collapse. Only fires when military_strength = 0 AND stability < 30:

| Stability | Base Prob | × 3 (military=0) | Capped |
|-----------|-----------|-------------------|--------|
| < 15 | 30% | 90% | 85% |
| 15–29 | 15% | 45% | 45% |

- `coup_immune = True` (from dissolve_opposition) blocks coup entirely
- On fire: sets stability to 0, triggering collapse game-over

---

## 23. Known Architecture Decisions

- **No TypeScript** — frontend is plain JSX
- **No Redux** — all state lives in `GameScreen.jsx` as `useState`
- **All game logic in Python** — Claude generates *only flavor text*; numbers, relations, and budgets are never decided by Claude
- **Installments are positive** — NPC-to-player budget transfers use positive amounts. Player-to-NPC transfers use negative. Validated at extraction and at EOT.
- **Oil lock vs. oil modifier** — `oil_price_locked` sets an absolute price; `oil_price_modifiers` stack deltas on top of the relation-based price
- **Epitaphs are not Claude decisions** — if Claude fails 3 times, a deterministic template fires. The game never blocks on epitaph generation
- **Negotiation is fire-and-forget** — counter-offers are optional; Call 2 failing is non-fatal and returns `counter_offer: null`

---

## 24. INCOMING System — NPC-Initiated Contact (fixes_15 Fix A)

Two-tier system where NPCs proactively reach out to the player. Processed in EOT section 13f.

### Tier 1: Condition-Based Triggers

Each trigger has a single condition and a probability gate. Cooldown prevents repeat fires.

| NPC | Trigger Key | Condition | Probability | Cooldown |
|-----|-------------|-----------|-------------|----------|
| Bill (USA) | `usa_sanctions_concern` | `usa_sanctions_tier >= 2` | 40% | 3 turns |
| Sadam (Arabia) | `arabia_drift_concern` | `relations['arabia'] < 40` | 35% | 3 turns |
| Marsha (EU) | `eu_regime_concern` | `regime_idx >= 2` (Patronage State+) | 50% | 3 turns |
| Ji-won (DPRG) | `dprg_wealth_notice` | `personal_wealth >= 15 AND relations['dprg'] >= 40` | 45% | 5 turns |

Each trigger has a predefined reason string and tone (urgent/concerned/formal/conspiratorial).

### Tier 2: Random Ambient Contacts

5% per NPC per turn, cooldown 5 turns. Fires only when `15 <= relations[npc] <= 95`. Tone scales with relation level:
- relations >= 70: `warm` (opportunistic, friendly)
- relations 40-69: `neutral` (transactional, probing)
- relations 15-39: `warning` (last chance framing)

Trigger key: `{npc}_ambient`. Reason: "[NPC name] is reaching out through private channels."

### Storage and Processing
- **Queued in:** `game_state.pending_npc_contacts` (list of contact dicts)
- **History in:** `game_state.npc_contact_history` (dict: `{trigger_key: last_fired_turn}`)
- **Rendered as:** Private Channel communique in `DialoguePanel.jsx`
- **Negotiate cost:** $0 for INCOMING contacts (enforced in api.py)

Console logs:
- `[turn_processor] INCOMING BLOCK REACHED — turn N`
- `[turn_processor] INCOMING CONDITIONS: sanctions_tier=X, arabia_rel=X, regime_idx=X, personal_wealth=X`
- `[turn_processor] INCOMING TIER1 CHECK: {npc} condition met, roll=X.XX, fired=T/F`
- `[turn_processor] INCOMING AMBIENT CHECK: {npc} rel=X, roll=X.XX, fired=T/F`
- `[game_state] INCOMING queued for: {npc} — {reason}`

---

## 25. Deferred Items

- **Negotiated deal cross-NPC warnings** are partial until Session 7 GM inference layer. Static matrix penalties may not match negotiated deal content — full consequence matching deferred. (fixes_10 Fix 9)
- **Covert Security operation** (op 4) does not correctly deduct cost or apply effects. Deferred to Session 6 Operations redesign.
- **Session 6 axis redesign:** Security splits into Military and Intelligence axes. Resource Development added as new national budget axis. Each axis gets its own action suite. Operations tab redesigned. Advisor pool updated.

---

*Last updated: Post fixes_16 + individual fixes. 101 tests passing. All fixes through fixes_16 implemented.*
