# THE WORLD STAGE — STATUS

## Current Build State

- **Tests:** 101 passing, 0 failing
- **Frontend:** Vite production build clean
- **Backend:** All Python modules parse cleanly
- **All fixes through fixes_16** plus individual single fixes implemented
- **Total sessions completed:** 5 (plus extensive post-session bug fixing)

### Known Non-Functional

- **Covert Security operation** (brigade op 4): Does not correctly deduct cost or apply effects. Deferred to Session 6 Operations redesign.
- **Fabricate Crisis suspension vs OPSEC failure interaction:** Design question unresolved — deferred to Session 6.

### Session 6 Scope (Not Yet Implemented)

- **Axis redesign:** Security splits into Military and Intelligence as separate axes
- **Resource Development:** New national budget axis added
- **Action suites:** Each axis gets its own action suite
- **Operations redesign:** Full audit and restructure of brigade/black ops system
- **Advisor pool:** Updated to match new axis structure

---

## Post-Session 5 Fixes (fixes_11 through fixes_16 + individual fixes)

All fixes through fixes_16 have been implemented. Key areas addressed:

- **fixes_11:** Brigade operations gating (one-per-turn), advisor dedup, regime derivation sole authority
- **fixes_12:** Historian summary redesign, personal wealth ledger
- **fixes_13:** Bond financing ($5B routine/$10B emergency), covert deals, Black Operations suite (5 black ops), NPC 100 unlocks (USA/Arabia/EU/DPRG), cross-NPC penalty matrix
- **fixes_14:** Browser testing residuals — Bill intel refusal, end-of-game check, INCOMING rendering, stage direction stripping, Arabia 100 floor
- **fixes_15:** INCOMING two-tier redesign (condition + probability gates), bond financing split, infrastructure budget source split (national vs personal), intel tier persistence (`npc_intel_tiers`), Arabia 100 floor enforcement
- **fixes_16:** INCOMING trace logging, blackmail intel read path fix, extraction milestones ($7B injection at L5), advisor pool axis gating, extraction budget source correction, skim projection restructure (simulates EOT approval/stability pipeline before GDP)

### Individual Fixes (post fixes_16)
- Arabia 100 unlock: dividend increased $3B to $4B/turn, oil price ceiling removed
- Skim projection deep audit: GDP now uses projected post-penalty approval/stability, sanctions floor-collapse bypass handled
- Communique text injection into NPC chat history on negotiation open

---

## Session 5: 7 Deliverables (5 Phases A-E)

### Session 5 Summary

7 major deliverables implemented across 5 phases:

1. **Vector Memory System** (3-tier NPC memory with Voyage AI embeddings + pgvector)
2. **NPC-Initiated Contact** (rule-based triggers for 4 NPCs, cooldown enforcement)
3. **Daily Briefing UI Spec** (design document only, no implementation — `docs/briefing_spec.md`)
4. **Tech Level Passive Acquisition** (EU/USA/DPRG weighted fractional accumulation per turn)
5. **Advisor System** (7 base + 2 nefarious archetypes, hire/dismiss/eliminate, stat distortion, betrayal)
6. **Shadow Cabinet Redesign** (five-axis system replacing binary upgrades, three-drawer UI)
7. **Economic Development Model** (GDP growth, 3 tax sliders, revenue streams, stability/sanctions modifiers)

### Phase A — Foundation

**game_state.py:**
- 5 axis constants: `AXIS_COST_PER_LEVEL`, `AXIS_MAINTENANCE`, `AXIS_PERMANENT_FLOORS`
- `compute_regime_from_axes()` — derives regime_type from sum of 5 axes
- `_migrate_to_axes()` — one-time migration from binary upgrades to five axes
- ~30 new fields: cabinet_axes, advisors, advisor_pool, tax_rates, gdp_base, revenue_streams, soft_power, diplomatic_capital, tech_level_fractional, pending_npc_contacts, brigade_operations_this_turn, etc.
- All new fields in `serialize()` and `deserialize()` with safe defaults

**db.py:**
- `player_id` column added to GameSession
- 3 new models: `NpcMemory`, `NpcRelationshipSummary`, `EraSummary`
- pgvector graceful import with `HAS_PGVECTOR` flag

**requirements.txt:**
- Added `voyageai>=0.3.0` and `pgvector>=0.3.0`

### Phase B — Backend Systems

**memory_engine.py (NEW):**
- Full 3-tier memory system (episodic, relationship summaries, era summaries)
- Voyage AI embeddings (voyage-3-lite, 512-dim) with graceful degradation
- `store_memory()`, `retrieve_memories()`, `build_memory_context()`, `update_relationship_summaries()`, `create_era_summary()`, `cleanup_expired_memories()`

**advisor_engine.py (NEW):**
- 7 base archetypes: technocrat, spymaster, general, diplomat, propagandist, oligarch, ideologue
- 2 nefarious archetypes: enforcer (Security >= 6), fixer (Security >= 3)
- `generate_advisor_pool()`, `hire_advisor()`, `dismiss_advisor()`, `eliminate_advisor()`
- `apply_stat_distortion()` — loyalty-gated stat bias for frontend
- `check_advisor_loyalty()` — betrayal events by specialty (skim, leak, sabotage, etc.)

**turn_processor.py (7 new EOT sections):**
- 13: Cabinet axis maintenance costs
- 13b: Tech passive acquisition (EU 60%, USA 25%, DPRG 15% weighted, regime modifier)
- 13c: GDP + tax revenue model (growth, revenue streams, approval impact)
- 13d: Advisor loyalty check
- 13e: Latent stats (soft_power, diplomatic_capital)
- 13f: NPC-initiated contact check (4 rules: USA/Arabia/EU/DPRG)
- 13g: Regime label override from axes

**api.py:**
- 3 new request models: `CabinetInvestRequest`, `AdvisorActionRequest`, `TaxRateRequest`
- 5 new endpoints: `/cabinet_invest`, `/advisor_action`, `/advisor_pool`, `/set_tax_rates`, `/brigade_operation`

### Phase C — Memory Integration (9 Hook Points)

1. Deal accepted (api.py /action, after deal_history.append)
2. Promise broken (turn_processor.py section 10)
3. Domestic action (api.py /domestic_action)
4. Election outcome (api.py /election)
5. Large skim >$5B (api.py /skim)
6. Regime collapse + create_era_summary (api.py /skim)
7. Relations milestone (turn_processor.py EOT 13e-ii)
8. Relationship summaries update (turn_processor.py EOT 13e-iii)
9. Cleanup expired memories (api.py /game/new)

### Phase D — Frontend

**ShadowCabinet.jsx (COMPLETE REWRITE):**
- Three-drawer architecture: INFRASTRUCTURE (5 axis tracks), OPERATIONS (5 brigade types), SPECIAL (taxes/intel/purchases)
- Axis tracks with pip bars, invest/defund buttons, maintenance costs, permanent floors
- Brigade operations gated by Security >= 3 with NPC target selector
- Tax sliders, revenue streams grid, GDP display

**AdvisorPanel.jsx (NEW):**
- Active advisors with competence/loyalty stats, bias info
- Dismiss/eliminate actions with confirmation flow
- Hiring pool with auto-fetch

**StatusBar.jsx:**
- Soft Power and Diplomatic Capital display
- NPC-initiated contact indicator (pulse animation)

**DialoguePanel.jsx:**
- Incoming contact display with red border and reason banner

**GameScreen.jsx:**
- AdvisorPanel wired after DialoguePanel

**api.js:**
- 5 new methods: `cabinetInvest`, `advisorAction`, `getAdvisorPool`, `setTaxRates`, `brigadeOperation`

**index.css:**
- ~400 lines new CSS for drawer tabs, axis tracks, operations cards, advisor panel, NPC contacts

### Phase E — Spec + Tests

**docs/briefing_spec.md (NEW):**
- Daily Briefing system design document (no implementation)
- Covers structure, generation pipeline, caching, advisor distortion, token budget

### New Tests (66 new, 117 total)

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_memory.py` | 8 (NEW) | Embedding graceful degradation, store/retrieve failure tolerance, build_memory_context assembly |
| `tests/test_advisors.py` | 13 (NEW) | Capacity gates, pool generation, hire/dismiss/eliminate, stat distortion, loyalty betrayal, archetype exclusion |
| `tests/test_cabinet_axes.py` | 14 (NEW) | 7 regime derivation tests, cost tables, maintenance calc, permanent floors, migration, 3 serialization round-trips |
| `tests/test_tech_passive.py` | 4 (NEW) | Weighted formula, regime modifier, tech level advancement, zero-relations edge case |
| `tests/test_npc_contact.py` | 5 (NEW) | USA/DPRG/Arabia trigger conditions, cooldown enforcement, no-contact baseline |
| `tests/test_economic.py` | 6 (NEW) | GDP growth, stability/sanctions modifiers, revenue streams population, serialization |
| `tests/test_tax_effects.py` | 5 (NEW) | High/low/normal tax approval effects, revenue scaling, default rates |

### Existing Test Fixes (Session 5)

| File | Fix |
|------|-----|
| `tests/test_arabia.py` | Fixed Unicode encoding errors in print statements (Windows cp1252 emoji) |
| `tests/test_scandal.py` | Fixed Unicode encoding errors in print statements (Windows cp1252 emoji) |

### Files Modified (Session 5)

| File | Changes |
|------|---------|
| `game_state.py` | 5 axis constants, `compute_regime_from_axes()`, `_migrate_to_axes()`, ~30 new fields, serialize/deserialize |
| `turn_processor.py` | 7 new EOT sections (13-13g), Phase C hooks 2/7/8 |
| `npc_engine.py` | Memory context injection into `_build_context()`, incoming contact context |
| `api.py` | 5 new endpoints, 3 request models, Phase C hooks 1/3/4/5/6/9 |
| `db.py` | `player_id` column, 3 new models (NpcMemory, NpcRelationshipSummary, EraSummary), pgvector support |
| `memory_engine.py` | NEW — full 3-tier NPC memory system |
| `advisor_engine.py` | NEW — 9 archetypes, hire/dismiss/eliminate, distortion, betrayal |
| `requirements.txt` | Added voyageai, pgvector |
| `frontend/src/api.js` | 5 new API client methods |
| `frontend/src/components/ShadowCabinet.jsx` | COMPLETE REWRITE — three-drawer UI |
| `frontend/src/components/AdvisorPanel.jsx` | NEW — advisor management panel |
| `frontend/src/components/StatusBar.jsx` | Soft Power, Diplomatic Capital, incoming contacts |
| `frontend/src/components/DialoguePanel.jsx` | NPC-initiated contact display |
| `frontend/src/components/GameScreen.jsx` | AdvisorPanel wire-in |
| `frontend/src/index.css` | ~400 lines new CSS |
| `docs/briefing_spec.md` | NEW — Daily Briefing design spec |
| `tests/test_memory.py` | NEW — 8 tests |
| `tests/test_advisors.py` | NEW — 13 tests |
| `tests/test_cabinet_axes.py` | NEW — 14 tests |
| `tests/test_tech_passive.py` | NEW — 4 tests |
| `tests/test_npc_contact.py` | NEW — 5 tests |
| `tests/test_economic.py` | NEW — 6 tests |
| `tests/test_tax_effects.py` | NEW — 5 tests |
| `tests/test_arabia.py` | Unicode print fix |
| `tests/test_scandal.py` | Unicode print fix |

### Current Build State

- Backend: All Python modules parse cleanly
- Tests: **117 total passing** across 16 files (66 new + 51 existing)
- Frontend: Builds clean (vite build)
- New dependencies: voyageai, pgvector (graceful degradation if unavailable)
- Total features/fixes implemented across all sessions: **117** (110 prior + 7 Session 5 deliverables)

---

## Previous — fixes_10: 9 Fixes (from fixes_9 server log analysis + browser testing)

### Fix 1 — Epitaph angle history persists through elections (HIGH)
- `game_state.py`: Added `epitaph_angles_used` persistent field — list of angle strings, initialized at game start, NEVER cleared. Serialized/deserialized with game state.
- `npc_engine.py`: `_select_required_angle()` reads from `epitaph_angles_used` exclusively (not text classification). Reset detection fallback if field empty on turn > 1. `generate_epitaph()` records angle on all return paths (success, 8-word fallback, exception).
- `npc_engine.py`: Added `_get_fallback_epitaph()` — 5 per-turn-unique templates as 8-word match safety net.

### Fix 2 — Domestic action costs recorded in personal wealth ledger
- `turn_processor.py`: Changed direct `personal_wealth -= cost` to `update_personal_wealth(-cost, source=...)` in `apply_domestic_action()`. FIX C ledger mismatch warning should no longer fire.

### Fix 3 — Election warning frontend timing fix
- `turn_processor.py`: Changed election warning flag from `election_turn - 1` to `election_turn - 2`. Flag now set during turn (election_turn-2)'s EOT, visible to frontend on turn (election_turn-1) before `current_turn < election_turn` guard evaluates.
- `StatusBar.jsx`: Added emoji to election warning text.

### Fix 4 — DPRG Intelligence Sharing delivers actual intel content
- `turn_processor.py`: Added `_generate_dprg_intel_package()` — generates per-NPC stance summaries (USA, Arabia, EU) with relation values, sanctions status, and strategic context. Appended as EOT message lines when DPRG Intelligence Sharing event fires.

### Fix 5 — Budget projection caveat text
- `turn_processor.py`: Changed "(drain only, before any deals)" to "(drain only — excludes deals and world events)".

### Fix 6 — Arabia embargo tier boundary warning
- `turn_processor.py`: Added EOT section 12c — checks if Arabia relations within 5 of tier boundaries (35, 25, 15, 5) AND below 40. Warning message appended to EOT messages.

### Fix 7 — Debug panel for manual stat adjustment (dev tool)
- `api.py`: New `POST /game/{id}/debug/set_state` endpoint — accepts `{ overrides: { field: value } }`. Supports relations, budget, personal_wealth, stability, approval, heat, military, tech_level.
- `frontend/src/components/DebugPanel.jsx`: NEW component — sliders/inputs for all adjustable stats. Red "DEBUG MODE" header. Hidden in production builds.
- `GameScreen.jsx`: Ctrl+Shift+D keyboard listener toggles debug panel. Not visible when `import.meta.env.PROD`.
- `api.js`: Added `debugSetState()` method.
- `index.css`: Debug panel overlay styles.

### Fix 8 — Intel intercept JUST ENACTED distinction
- `game_state.py`: Added `domestic_actions_enacted_turns` dict — maps flag name to turn number.
- `turn_processor.py`: Records enacted turn in `apply_domestic_action()`.
- `npc_engine.py`: `generate_intercept_comments()` splits active domestic actions into RECENTLY ENACTED (current_turn - 1) vs ESTABLISHED (older). Priority instruction added for recently enacted actions.

### Fix 9 — Negotiated deal cross-NPC warnings — DEFERRED
- No code changes. Deferred to Session 7 GM inference layer. Note added to ARCHITECTURE.md section 24.

### New Tests (6 new, 51 total)

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_epitaph.py` | +1 (9 total) | `test_epitaph_angles_persist_through_election` — angles survive serialize/deserialize round-trip through election |
| `tests/test_ledger.py` | 3 (NEW) | Domestic action ledger entry, ledger sum matches wealth, all 5 action types recorded |
| `tests/test_arabia.py` | 2 (NEW) | Near-boundary warning fires at rel=27, no warning at rel=50 |

### Files Modified (fixes_10)

| File | Changes |
|------|---------|
| `game_state.py` | `epitaph_angles_used` field, `domestic_actions_enacted_turns` field, serialize/deserialize |
| `turn_processor.py` | Ledger fix, election warning timing, DPRG intel package, bankruptcy text, Arabia boundary, enacted turn tracking |
| `npc_engine.py` | Epitaph angle persistence, fallback templates, intercept JUST ENACTED split |
| `api.py` | `DebugSetStateRequest` model, `/debug/set_state` endpoint |
| `StatusBar.jsx` | Election warning emoji |
| `GameScreen.jsx` | Debug panel import, state, Ctrl+Shift+D listener, conditional render |
| `DebugPanel.jsx` | NEW — dev-only stat override panel |
| `api.js` | `debugSetState()` method |
| `index.css` | Debug panel styles |
| `tests/test_epitaph.py` | +1 angle persistence test, updated Tests 3/6 for Fix 1 changes |
| `tests/test_ledger.py` | NEW — 3 tests |
| `tests/test_arabia.py` | NEW — 2 tests |
| `ARCHITECTURE.md` | Sections 3/11/19/24 updated, deferred items section |

---

## Previous — fixes_9: 9 Bug Fixes (from fixes_8 browser verification)

### Fix 1 — Negotiated deal ⚠️ warning not rendering
- `api.py`: Added `relation_warning` field population in `post_negotiate()` when counter-offer first returned (not at acceptance time). Checks consequences for negative NPC relations AND installment conditions involving other NPCs.

### Fix 2 — Conditional payment per-deal evaluation
- `turn_processor.py`: Changed withheld tracking from per-NPC consolidation to per-deal list. Each deal now evaluated against its own stored `condition_threshold`. Separate withheld message per deal showing threshold, current value, and ✓/✗ status.

### Fix 3 — Judicial Capture not blocking scandals
- `turn_processor.py`: Moved scandal immunity check to FIRST line of `roll_detection()`, before heat decay. Checks `action_judiciary_captured`, `action_journalists_liquidated`, AND `scandal_immune`. Returns immediately with immunity message.

### Fix 4 — Epitaph repeat full rewrite
- `npc_engine.py`: Complete rewrite of epitaph prompt construction. 9 angle categories with keyword classification. Angle rotation (avoids last 2 used angles). Banned phrases (5-word chunks from last 3 epitaphs). Saturation block (if same action repeated). Single Claude call (no retry loops). Post-generation 8-word match falls back to delta template.

### Fix 5 — Bankruptcy projection caveat text
- `turn_processor.py`: Updated warning text to include "(drain only, before any deals)" caveat. Changed critical format to "📉 LOW BUDGET".

### Fix 6 — Election warning timing (3 sub-fixes)
- Fix 6a — `StatusBar.jsx`: Added `current_turn < election_turn` guard to election countdown label
- Fix 6b — `GameScreen.jsx`: Already correct (no change needed)
- Fix 6c — `turn_processor.py`: Removed election warning from EOT messages entirely (kept flag-setting). Amber banner in GameScreen handles display.

### Fix 7 — Contradictory world events from same NPC
- `turn_processor.py`: Added `_npc_event_fired` set in `check_pressure_events()`. Each event adds NPC to set; later events check before firing.
- `api.py`: Added collision check in skim/inject endpoints — suppresses world events from NPCs that already had pressure events this turn.

### Fix 9 — Intel intercepts domestic action context
- `npc_engine.py`: Strengthened domestic action block in `generate_intercept_comments()`. Added regime type context. MANDATORY instruction to reference specific domestic actions by name. Per-NPC reaction patterns for each domestic action type.

### Fix 10 — Loyalty Brigades subtitle in Shadow Cabinet
- `ShadowCabinet.jsx`: Added `subtitle` field to Loyalty Brigades card: "Unlocks per-turn brigade deployment — see choices screen after each diplomatic action."

### New Tests (12 new, 45 total)

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_epitaph.py` | 8 (FULL REWRITE) | Angle classification, banned phrases, angle rotation, delta variation, system prompt check, 8-word fallback, saturation block, consecutive same-action |
| `tests/test_scandal.py` | +1 (3 total) | `test_scandal_blocked_by_judicial_capture` — judicial capture blocks scandal at max heat |
| `tests/test_conditional_payments.py` | 3 (NEW) | Per-deal withheld messages, stored threshold usage, condition-met payout |

### Files Modified (fixes_9)

| File | Changes |
|------|------------|
| `api.py` | Counter-offer relation_warning field, world event NPC collision check |
| `turn_processor.py` | Per-deal conditional eval, scandal immunity ordering, bankruptcy caveat, election warning removal, pressure event collision tracking |
| `npc_engine.py` | Epitaph full rewrite (angles, banned phrases, saturation), intercept domestic context strengthened |
| `StatusBar.jsx` | Election countdown turn guard |
| `ShadowCabinet.jsx` | Loyalty Brigades subtitle |
| `tests/test_epitaph.py` | FULL REWRITE — 8 new tests replacing 7 old |
| `tests/test_scandal.py` | +1 judicial capture immunity test |
| `tests/test_conditional_payments.py` | NEW — 3 tests |
| `ARCHITECTURE.md` | Sections 10/11/19/22 updated |

---

## Previous — fixes_8: 14 Polish / Mechanical / Bug Fixes

### Category 1 — Quick Polish (Frontend)

**Fix 1 — StatusBar double render**
- `StatusBar.jsx`: Wrapped `console.log` in `useEffect` with `[approval, stability]` dependencies — prevents double-fire per state update

**Fix 2 — Sanction risk logged twice per EOT**
- `turn_processor.py`: Added deduplication flags (`_already_warned_usa`, `_already_warned_arabia`) scanning existing messages before adding new sanction/embargo warnings

**Fix 3 — Election countdown missing from status bar**
- `StatusBar.jsx`: Added "| Election Next Turn" amber text in state-identity-row when `election_warning_shown && !election_fired`

**Fix 4 — Tech Level hidden at 0**
- `StatusBar.jsx`: Tech Level always visible, `opacity: 0.4` when value is 0

### Category 2 — Mechanical Fixes

**Fix 5 — Election warning in EOT instead of turn start**
- `EotPanel.jsx`: Election warning lines filtered out of EOT display
- `GameScreen.jsx`: Election warning banner restyled amber (#ffb74d), text updated to "Elections next turn — your choices this turn will shape the outcome."

**Fix 6 — Negotiated deal warning console log**
- `api.py`: Added `print(f"  [api] NEGOTIATED DEAL WARNING: ...")` after existing relation_warning assignment (logic was already implemented in FIX G from fixes_6)

**Fix 7 — Epitaph text similarity check**
- `npc_engine.py`: Added second-pass 12-word similarity check in `generate_epitaph()` after 8-word overlap passes. Compares first 12 words of new draft against last 2 in history. Forces regeneration with stronger instruction on match.

**Fix 8 — Bill election reaction too generic**
- `npc_engine.py`: Added Bill Hartwell transactional voice guidance block to `generate_election_reactions()` system prompt with per-outcome reaction patterns

**Fix 9 — Intelligence intercepts ignore domestic actions**
- `npc_engine.py`: Added domestic action flag detection in `generate_intercept_comments()`. Lists active actions (State Media Takeover, Judicial Capture, etc.) with per-NPC reaction guidance.

**Fix 10 — Western Bloc double-fire prevention**
- `turn_processor.py`: Added `_western_bloc_fired_this_turn` flag in `process_choice_consequences()` when Western Bloc fires from choice consequences. `check_pressure_events()` checks flag before threshold trigger, suppresses with console log.

**Fix 11 — Budget bankruptcy pre-warning**
- `turn_processor.py`: Added section 12b projecting next-turn budget from govt costs ($3B), oil imports, sanctions, embargo vs projected GDP income ($4B base). Warning message added to EOT if projected budget ≤ $3B.

**Fix 12 — Intel budget persistent display in Shadow Cabinet**
- `ShadowCabinet.jsx`: Added Intel Apparatus Status block below Intelligence Apparatus upgrade showing: status, budget allocation, effective tier, tech bonus, unfunded warning.

### Category 3 — Investigated Bugs

**Fix 13 — Scandal threshold floor enforcement**
- `turn_processor.py`: Added console logs to scandal check: `SCANDAL CHECK: heat=X, prob=X%, roll=X, fired=T/F`. Verified heat < 30 floor was already correctly enforced.

**Fix 14 — Coup multiplier at military 0**
- `turn_processor.py`: Added military coup probability check in `check_game_over()` before stability collapse. Military=0 + stability<30 → base prob 15-30% × 3 (capped 85%). `coup_immune=True` blocks entirely. On fire, sets stability=0 triggering collapse.

### New Tests (5 new, 40 total)

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_epitaph.py` | +1 (7 total) | `test_epitaph_text_similarity_check` — mocks two Claude calls, verifies regeneration on 12-word match |
| `tests/test_scandal.py` | 2 (NEW) | `test_scandal_no_fire_below_30` — heat=25 never fires; `test_scandal_fires_above_85` — heat=95 (decays to 90) fires frequently |
| `tests/test_coup.py` | 2 (NEW) | `test_coup_fires_at_military_zero` — military=0 fires in majority; `test_coup_blocked_by_immunity` — coup_immune=True never fires |

### Files Modified (fixes_8)

| File | Changes |
|------|---------|
| `StatusBar.jsx` | useEffect wrap, election countdown, tech always visible |
| `EotPanel.jsx` | Election lines filtered from EOT |
| `GameScreen.jsx` | Election warning banner amber restyle |
| `ShadowCabinet.jsx` | Intel Apparatus Status block |
| `turn_processor.py` | Sanction dedup, Western Bloc flag, bankruptcy pre-warning, scandal log, coup multiplier |
| `npc_engine.py` | Epitaph similarity, Bill voice, intercept domestic flags |
| `api.py` | Negotiated deal warning console log |
| `tests/test_epitaph.py` | +1 similarity test |
| `tests/test_scandal.py` | NEW — 2 tests |
| `tests/test_coup.py` | NEW — 2 tests |
| `ARCHITECTURE.md` | Sections 3/11/12/19/22 updated |

### Design Decisions Deferred
- No changes to `game_state.py`, `ElectionPanel.jsx`, `OffersPanel.jsx`, `SkimPanel.jsx`, `IntelAllocationPanel.jsx`, `EndingPanel.jsx`, NPC personality files, `index.css`, or existing test files (except `test_epitaph.py`)

---

## Previous — Session 4D: Tech Level, Intel Budget, Alternate Endings

### Tech Level Resource (0-100, permanent, no decay)

| Tier | Tech Range | EU Ceiling | GDP Bonus | Intel Tier Bonus |
|------|-----------|------------|-----------|-----------------|
| 1 | 0-20 | 100 (default) | 0% | 0 |
| 2 | 21-40 | 110 | +5% | 0 |
| 3 | 41-60 | 120 | +10% | +1 |
| 4 | 61-80 | 130 | +15% | +1 |
| 5 | 81-100 | 140 | +20% | +2 |

**Sources:** EU partnership +5, USA transfer +8, DPRG weapons-for-tech +3

### Intelligence Budget Allocation

| Option | Cost | Effect |
|--------|------|--------|
| None | $0 | Apparatus degrades after 2 consecutive unfunded turns |
| Maintenance | $0.5B | Keep apparatus at current level |
| Active | $1.0B | Full operational capability |
| Expansion | $2.0B | Maximum investment |

Deducted from national budget (not personal wealth). Shown before skim screen each turn.

### Alternate Endings (4 endings, checked each EOT)

| Ending | Priority | Turn | Conditions |
|--------|----------|------|------------|
| Martyrdom | 4 (highest) | Any | Stability <= 0, approval >= 70 |
| State Capture | 3 | Any | Wealth >= $50B, all 5 domestic actions taken |
| Democratic Transition | 2 | Turn 10 | EU >= 80, approval >= 65, no domestic actions |
| Voluntary Retirement | 1 | Turn 10 | Stability >= 60, approval >= 50, wealth >= $20B |

**GameState changes (`game_state.py`):**
- 7 new fields: `tech_level`, `tech_sources`, `intel_budget`, `intel_budget_allocation`, `intel_turns_unfunded`, `ending_triggered`, `turns_no_suppression`
- `update_relations()` now uses dynamic EU ceiling from tech level (inline tier lookup)
- Migration log: `[game_state] SESSION 4D FIELDS MIGRATED: added defaults to old save`

**Turn processor (`turn_processor.py`):**
- `TECH_TIER_EFFECTS` dict — 5 tier ranges with eu_ceiling, gdp_bonus, intel_tier_bonus
- `TECH_SOURCES` dict — 3 sources (eu_partnership +5, usa_transfer +8, dprg_weapons +3)
- `get_tech_tier_effects(tech_level)` — returns effects dict for current tier
- `apply_tech_gain(game_state, source_key)` — applies gain, logs to tech_sources, reports tier transitions
- `INTEL_BUDGET_OPTIONS` dict — 4 allocation options with costs
- `process_intel_budget(game_state, allocation)` — deducts from national budget, tracks unfunded streak, degrades apparatus
- `ALTERNATE_ENDING_CONDITIONS` dict — 4 endings with priority, conditions, flavor text
- `check_alternate_endings(game_state)` — checks in priority order, sets ending_triggered
- EOT section 9b: GDP bonus multiplied by (1 + tech_gdp_bonus)
- EOT section 9c: EU ceiling enforcement from tech tier
- EOT section 13: Alternate endings check after all consequences

**API (`api.py`):**
- `POST /game/{id}/intel_allocation` — validates allocation, calls `process_intel_budget`, returns success/changes/game_state
- `IntelAllocationRequest` model, imports `process_intel_budget`, `INTEL_BUDGET_OPTIONS`, `apply_tech_gain`, `TECH_SOURCES`

**Frontend:**
- `EndingPanel.jsx` (NEW) — 4 alternate ending displays with unique icons, colors, flavor text, final stats
- `IntelAllocationPanel.jsx` (NEW) — 4 allocation buttons, budget display, unfunded warning, shown before skim
- `StatusBar.jsx` — Tech Level stat (hidden at 0, shown when > 0)
- `GameScreen.jsx` — EndingPanel + IntelAllocationPanel imports, `handleIntelAllocate()`, intel allocation state, skim disabled until intel allocated, alternate ending detection in ENDED phase
- `api.js` — `intelAllocation(id, allocation)` method

**Tests (`tests/test_session4d.py`) — 12/12 passing:**
1. `test_tech_tier_effects_all_tiers` — all 5 tiers verified
2. `test_apply_tech_gain_eu_partnership` — EU partnership +5
3. `test_apply_tech_gain_tier_transition` — USA transfer tier transition reporting
4. `test_tech_gdp_bonus_in_eot` — tech GDP bonus increases revenue
5. `test_eu_ceiling_from_tech` — EU relations exceed 100 with tech
6. `test_intel_budget_deducts_from_national` — active costs $1B from national budget
7. `test_intel_apparatus_degradation` — 2 unfunded turns degrades tier
8. `test_ending_martyrdom` — stability 0 + approval 70+
9. `test_ending_retirement` — turn 10 + stability/approval/wealth thresholds
10. `test_ending_democratic` — turn 10 + EU 80+ + no domestic actions
11. `test_ending_capture` — wealth 50+ + all 5 domestic actions
12. `test_ending_priority_martyrdom_over_capture` — priority ordering verified

### Files Modified (Session 4D)

| File | Changes |
|------|---------|
| `game_state.py` | 7 Session 4D fields, `update_relations()` dynamic EU ceiling, serialize/deserialize with migration |
| `turn_processor.py` | TECH_TIER_EFFECTS, TECH_SOURCES, INTEL_BUDGET_OPTIONS, ALTERNATE_ENDING_CONDITIONS dicts + 4 functions, EOT sections 9b/9c/13 |
| `api.py` | `POST /game/{id}/intel_allocation` endpoint, `IntelAllocationRequest` model, new imports |
| `StatusBar.jsx` | Tech Level stat display (hidden at 0) |
| `GameScreen.jsx` | EndingPanel + IntelAllocationPanel wire-in, intel allocation state + handler |
| `api.js` | `intelAllocation()` method |
| `EndingPanel.jsx` | NEW — alternate ending display |
| `IntelAllocationPanel.jsx` | NEW — intel budget allocation panel |
| `tests/test_session4d.py` | NEW — 12 tests |
| `ARCHITECTURE.md` | Sections 3/5/6/8 updated for Session 4D |

---

## Previous — Session 4C: Domestic Actions + EOT Fixes

### 3 Bug Fixes

**FIX 1 — Election banner suppression on election turn**
- `GameScreen.jsx`: Banner now checks `current_turn < election_turn` — suppressed on the actual election turn

**FIX 2 — fair_squeaker approval +2**
- `turn_processor.py`: Added `"approval": +2` to `ELECTION_CONSEQUENCES["fair_squeaker"]`
- `tests/test_election.py`: New sub-test verifying approval goes from 50 to 52

**FIX 3 — EOT panel split into Finance/World Events sections**
- `EotPanel.jsx`: Complete rewrite — 4-bucket categorization (election/worldEvents/regime/finances)
- FINANCES collapsed by default, WORLD EVENTS expanded, election lines as standalone highlights

### Domestic Actions — 5 permanent Shadow Cabinet purchases

| Action | Cost | Key Effect | Regime Pressure |
|--------|------|------------|-----------------|
| State Media Takeover | $5B | Approval floor 15%, penalties -20% | Right |
| Judicial Capture | $4B | Scandal immunity | Right |
| Suppress Press | $3B | Stability +5%, EU -3/turn drain | Right |
| Dissolve Opposition | $6B | Coup immunity, stability +10% | Hard right |
| Liquidate Journalists | $8B | Scandal immunity, ceiling -10% | Hard right |

---

## Previous — Session 4B: Election Mechanic

### Election feature — full implementation

**What it is:** Elections fire once per game at turn 4 (configurable). Player chooses how to handle it: fair election, rig it, cancel it, or invite international observers.

---

## Previous — fixes_7 (2 fixes A-B)

**FIX A** — Epitaph thematic repeat + NPC role misidentification
**FIX B** — Tier 3 intel not changing Marsha's negotiating behavior

---

## Previous — fixes_6 (7 fixes A-G)

**FIX A** — Duplicate epitaph (6th attempt, delta-based)
**FIX B** — GDP revenue wrong approval/stability values
**FIX C** — Skim screen projection missing income items
**FIX D** — Old deal conditions not retroactively corrected
**FIX E** — Tier 3 intel not affecting NPC behavior
**FIX F** — Legacy verdict ignoring peak relation values
**FIX G** — NPC prose payment terms not generating deal panel

---

## Archive

- **fixes_5:** 16 fixes A-P
- **Session 4A:** 3 bug fixes + 5 features
- **fixes_4:** 13 fixes
- **fixes_3:** 6 fixes
- **fixes_2:** 5 fixes
- **fixes_1:** 17 fixes

### Current Build State

- Backend: All Python modules parse cleanly
- Tests: **101 total passing, 0 failing** across 16 test files
- Frontend: Builds clean (vite build)
- `ARCHITECTURE.md` updated through post-fixes_16
- `STATUS.md` updated through post-fixes_16
