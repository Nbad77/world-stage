# CLAUDE CODE PROMPT — fixes_10
Generated: February 26, 2026
Source: worldstage_fixes_10_notes.md — server log analysis + browser testing

---

## BEFORE YOU WRITE A SINGLE LINE OF CODE

Read these files in this order:
1. worldstage_fixes_10_notes.md — full bug list with confirmed root causes
2. ARCHITECTURE.md — codebase reference
3. STATUS.md — current build state

After reading all three, respond with:
"I have read all three files. fixes_10 contains N actionable items.
Files I will modify: [list every file]
Files I will NOT modify: [list adjacent files out of scope]"

Do not proceed until confirmed.

---

## SCOPE

9 fixes. Implement in order as listed.

NOT in scope:
- Session 5 features (vector memory, advisor system, etc.)
- GM inference layer (Session 7)
- Structured negotiation templates (Session 6)
- Any new features

---

## FIX 1 — Epitaph angle history resets after elections (HIGH)

**Root cause confirmed via server logs:**
Both test runs show `(recent angles: [])` after election
processing. The angle tracking array is being cleared during
election handling, causing the rotation system to default
to the same angle on consecutive turns.

Run 1:
```
Turn 4 (fair_squeaker): required=diplomatic (recent angles: [])
Turn 5 (defense purchase): required=diplomatic (recent angles: [])
```

This is a state persistence bug, NOT a prompt engineering problem.

**Investigation required before fixing:**
Find every place in the codebase where election processing
occurs. Look for any line that clears, resets, or reinitializes:
- `epitaph_history`
- `epitaph_angles_used`
- Any list used for angle tracking
Post your findings before implementing.

**Fix:**
1. Store angle history as a dedicated persistent field:
   `game_state.epitaph_angles_used` — list of strings,
   initialized at game start, NEVER cleared.

2. In generate_epitaph(), read from and write to
   `game_state.epitaph_angles_used` exclusively.
   Never derive angle history from epitaph_history text.

3. Add defensive reset detection:
```python
if len(game_state.epitaph_angles_used) == 0 and game_state.current_turn > 1:
    log(f"[npc_engine] EPITAPH ANGLE HISTORY RESET DETECTED — turn {game_state.current_turn}")
    # Reconstruct from last known angles if possible
```

4. Add fallback template as safety net (not primary fix):
```python
def get_fallback_epitaph(game_state, template_index: int) -> str:
    templates = [
        f"Turn {game_state.current_turn}: ${game_state.personal_wealth:.1f}B "
        f"accumulated personally while the national budget stood at "
        f"${game_state.budget:.1f}B.",
        
        f"The {game_state.regime_label} entered its {game_state.current_turn}"
        f"{'th' if game_state.current_turn > 3 else ['st','nd','rd'][game_state.current_turn-1]} "
        f"quarter with {game_state.stability:.0f}% stability.",
        
        f"Relations with {get_highest_npc(game_state)} stood at "
        f"{get_highest_relations(game_state)} as "
        f"{get_lowest_npc(game_state)} receded to "
        f"{get_lowest_relations(game_state)}.",
        
        f"Stability at {game_state.stability:.0f}%, approval at "
        f"{game_state.approval:.0f}% — the arithmetic of survival "
        f"growing {'more' if game_state.stability < 50 else 'less'} favorable.",
        
        f"The national accounts recorded ${abs(game_state.budget):.1f}B "
        f"{'deficit' if game_state.budget < 0 else 'surplus'} "
        f"as personal reserves reached ${game_state.personal_wealth:.1f}B.",
    ]
    return templates[template_index % len(templates)]

# In generate_epitaph(), after generation:
if shares_6_words_with_recent(generated, game_state.epitaph_history[-3:]):
    fallback_index = game_state.current_turn % 5
    generated = get_fallback_epitaph(game_state, fallback_index)
    log(f"[npc_engine] EPITAPH FALLBACK USED — turn {game_state.current_turn}")
```

**Console logs required:**
- `[npc_engine] EPITAPH ANGLE HISTORY RESET DETECTED — turn {n}`
  (should never appear after fix)
- `[npc_engine] EPITAPH FALLBACK USED — turn {n}`
  (safety net — rare)
- After election, should show:
  `(recent angles: ['financial', 'diplomatic'])` not `(recent angles: [])`

**Update tests/test_epitaph.py:**
Add test_epitaph_angles_persist_through_election:
- Process 2 turns, then process election turn, then turn 5
- Verify `epitaph_angles_used` contains all 3+ angles after turn 5
- Verify no `RESET DETECTED` log fires

All 8 epitaph tests must still pass.

**Files:** npc_engine.py, game_state.py, turn_processor.py
  (find and fix the reset location)

---

## FIX 2 — Fix C Ledger Mismatch — domestic actions not recorded

**Root cause confirmed via server logs:**
Every turn shows consistent gap matching domestic action costs:
```
[api] ⚠️ FIX C LEDGER MISMATCH: gap=-4.00  (Judicial Capture = $4B)
[api] ⚠️ FIX C LEDGER MISMATCH: gap=-3.00  (Suppress Press = $3B)
```

Domestic action personal wealth deductions apply to
`game_state.personal_wealth` but are NOT written to the
personal wealth ledger.

**Investigation required:**
Find the domestic action handler. Find where it deducts
personal wealth. Find where the personal wealth ledger
is written to for other transactions (skim, upgrades).
Post your findings before implementing.

**Fix:**
In the domestic action handler, after deducting personal wealth,
write a corresponding ledger entry using the same pattern
as skim and upgrade ledger entries:

```python
# After: game_state.personal_wealth -= action_cost
ledger_entry = {
    "turn": game_state.current_turn,
    "type": "domestic_action",
    "action": action_name,
    "amount": -action_cost,
    "description": f"{action_label} enacted"
}
game_state.personal_wealth_ledger.append(ledger_entry)
log(f"[api] LEDGER ENTRY: domestic_action {action_name} -${action_cost}B")
```

**Console log required:**
`[api] LEDGER ENTRY: domestic_action {action_name} -${cost}B
  (ledger now: ${ledger_sum}B)`

After fix, `FIX C LEDGER MISMATCH` warning should never appear.

**Write pytest in tests/test_ledger.py (NEW FILE):**
- test_domestic_action_recorded_in_ledger: enact judicial_capture,
  verify ledger contains entry with amount=-4.0 and
  type="domestic_action"
- test_ledger_sum_matches_personal_wealth: after domestic action,
  ledger sum equals game_state.personal_wealth
- test_all_action_types_recorded: test each of the 5 domestic
  actions records correctly

**Files:** api.py or turn_processor.py → domestic action handler

---

## FIX 3 — Election warning frontend not reading backend flag

**Root cause confirmed via server logs:**
Backend fires correctly:
`[turn_processor] ELECTION WARNING: pre-warning shown at turn 3`
in both test runs. Problem is entirely frontend — StatusBar.jsx
and GameScreen.jsx are not reading `election_warning_shown`
from the game state response.

**Investigation required:**
Before fixing, add this console.log to StatusBar.jsx temporarily:
```javascript
console.log('[StatusBar] DEBUG:', {
  election_warning_shown: gameState?.election_warning_shown,
  election_fired: gameState?.election_fired,
  current_turn: gameState?.current_turn,
  election_turn: gameState?.election_turn,
})
```
Tell me what values appear in the browser console on Turn 3.
This will confirm whether the field is missing from the API
response or just being read incorrectly.

**Likely fixes (implement after investigation):**

Option A — field missing from API response:
Add `election_warning_shown` explicitly to the game state
serialization in api.py. Check if boolean False values are
being dropped by the JSON serializer.

Option B — field name mismatch:
Frontend reads `gameState.electionWarningShown` (camelCase)
but backend sends `election_warning_shown` (snake_case).
Align the field names.

Option C — wrong condition:
StatusBar condition uses wrong comparison. Should be:
```javascript
const showElectionWarning =
  gameState.election_warning_shown === true &&
  gameState.election_fired !== true;
```

**Console log to add permanently:**
```javascript
// In StatusBar.jsx when election warning renders:
console.log('[StatusBar] ELECTION BANNER: rendering on turn',
  gameState.current_turn)
```

**Verify:**
Turn 3 main screen: amber banner ABOVE communiqués
Turn 3 status bar: "🗳️ ELECTION NEXT TURN" visible
Turn 4: both gone, election panel takes over

**Files:** StatusBar.jsx, GameScreen.jsx, api.py (if Option A)

---

## FIX 4 — DPRG Intelligence Sharing delivers no intel

**Symptom:** World event fires with message:
"🕵️🤝 DPRG INTELLIGENCE SHARING — Free intel access on all NPCs
this turn."
Player receives no actual intelligence.

**Fix:**
When DPRG Intelligence Sharing world event fires in
turn_processor.py, trigger intel generation for all 4 NPCs:

```python
if event_type == "dprg_intelligence_sharing":
    # Generate intel intercepts for all NPCs
    intel_content = generate_dprg_intel_package(game_state)
    game_state.pending_intel_reveal = intel_content
    game_state.intel_reveal_source = "DPRG Intelligence Sharing"
    log("[turn_processor] DPRG INTEL SHARING: generating intercepts for all NPCs")
```

Intel content should reflect the Western pressure campaign framing —
Bill and Marsha discussing Europa's DPRG alignment, sanctions
coordination, potential responses. Pass current relations and
recent actions as context.

In the EOT display, change the message from static text to
include a [VIEW INTEL] action that opens the existing intel
intercept panel populated with this content.

If a full intel modal is too complex for this fix session,
minimum viable: add the 4 NPC intel summaries as additional
lines in the EOT event display under the DPRG sharing message.

**Console logs required:**
`[turn_processor] DPRG INTEL SHARING: generating intercepts for all NPCs`
`[npc_engine] DPRG INTEL GENERATED: {npc} — {word_count} words`

**Files:** turn_processor.py, npc_engine.py, EotPanel.jsx or
  GameScreen.jsx (display)

---

## FIX 5 — Budget projection text — add world events caveat

**File:** turn_processor.py → bankruptcy warning text

**Fix:** Text update only, no logic change:
```python
# Change from:
f"⚠️ BANKRUPTCY RISK: projected ${amount}B next turn (drain only, before any deals)"

# Change to:
f"⚠️ BANKRUPTCY RISK: projected ${amount}B next turn (drain only — excludes deals and world events)"
```

**Verify:** Export log shows updated caveat text.

---

## FIX 6 — Arabia embargo tier boundary warning

**File:** turn_processor.py

**Fix:** In the bankruptcy projection calculation, after
computing projected budget, check whether Arabia relations
are near a tier boundary:

```python
EMBARGO_TIER_BOUNDARIES = [35, 25, 15]

def is_near_embargo_boundary(arabia_relations: float,
                              threshold: int = 5) -> bool:
    return any(
        abs(arabia_relations - boundary) <= threshold
        for boundary in EMBARGO_TIER_BOUNDARIES
    )

# In EOT, after bankruptcy warning:
if is_near_embargo_boundary(game_state.arabia_relations):
    eot_messages.append(
        f"⚠️ Arabia near oil tier boundary "
        f"(rel {game_state.arabia_relations:.0f}) — "
        f"oil costs may increase next turn"
    )
```

**Console log:**
`[turn_processor] ARABIA TIER WARNING: relations {n} near boundary`

**Write pytest in tests/test_arabia.py (NEW or add to existing):**
- test_near_boundary_warning_fires: arabia_relations=27 → warning fires
- test_far_from_boundary_no_warning: arabia_relations=50 → no warning

---

## FIX 7 — Debug panel for manual NPC relation adjustment

**Purpose:** Dev/testing tool. Allows manual adjustment of
NPC relations, budget, stability, approval without playing
through multiple turns to reach a specific game state.
Hidden from normal players — activated by key combination.

**Implementation:**

Backend — new endpoint:
```python
# api.py
@app.post("/game/{game_id}/debug/set_state")
async def debug_set_state(game_id: str, overrides: dict):
    """
    Dev tool: directly set any game state values.
    Example body: {"usa_relations": 80, "budget": 40.0}
    """
    game = get_game(game_id)
    for field, value in overrides.items():
        if hasattr(game, field):
            setattr(game, field, value)
    return {"status": "ok", "applied": overrides}
```

Frontend — debug panel component:
```javascript
// DebugPanel.jsx — new component
// Activated by: Ctrl+Shift+D (or similar)
// Shows sliders/inputs for:
// - USA relations (0-100)
// - Arabia relations (0-100)
// - EU relations (0-100)
// - DPRG relations (0-100)
// - Budget ($B)
// - Personal wealth ($B)
// - Stability (%)
// - Approval (%)
// - Heat (0-100)
// "Apply" button calls /debug/set_state
// Panel closes after apply
```

Style: minimal, clearly marked "DEBUG MODE" in red.
Does NOT appear in production build if NODE_ENV=production.

**Files:** api.py (new endpoint), 
  frontend/src/components/DebugPanel.jsx (new),
  GameScreen.jsx (keyboard listener + conditional render)

---

## FIX 8 — Intel intercept domestic context — JUST ENACTED flag

**Assessment from server logs:**
`[npc_engine] INTERCEPT CONTEXT: domestic actions=['Judicial Capture']`
IS firing correctly — just on the following turn, not immediately.
One-turn delay is acceptable (realistic — foreign intel takes time).

**Small improvement only:**
Add "JUST ENACTED" distinction for actions taken this turn:

```python
current_turn_actions = [a for a in active_actions
                        if a["enacted_turn"] == game_state.current_turn - 1]
ongoing_actions = [a for a in active_actions
                   if a["enacted_turn"] < game_state.current_turn - 1]

if current_turn_actions:
    prompt += f"RECENTLY ENACTED (this turn — foreign intel processing now): "
              f"{[a['label'] for a in current_turn_actions]}\n"
if ongoing_actions:
    prompt += f"ESTABLISHED ACTIONS (ongoing): "
              f"{[a['label'] for a in ongoing_actions]}\n"
```

**Files:** npc_engine.py → intercept generation

---

## FIX 9 — Negotiated deal cross-NPC warning — DEFER

**Status:** Partial fix from fixes_9 is acceptable for now.
Warning shows for explicitly mentioned NPCs (DPRG warning on
USA deals that mention DPRG). Arabia silent hits are a
consequence of the pre-set cross-NPC penalty matrix, not
the negotiation content.

Full fix requires Session 7 GM inference layer — the layer
that reads actual deal content and determines which NPCs
are affected and how much. Pushing a better warning system
now means building logic that will be replaced in two sessions.

**Action:** No code changes. Add to ARCHITECTURE.md notes:
"Negotiated deal cross-NPC warnings are partial until Session 7
GM inference layer. Static matrix penalties may not match
negotiated deal content — full consequence matching deferred."

---

## STEP — TESTS

After all fixes implemented, run full test suite.

Expected test files:
- tests/test_epitaph.py — 8 tests + 1 new (angle persistence)
- tests/test_ledger.py — NEW, 3 tests
- tests/test_arabia.py — 2 new tests
- tests/test_scandal.py — 3 tests (existing, unchanged)
- tests/test_conditional_payments.py — 3 tests (existing)
- tests/test_election.py — 6 tests (existing)
- tests/test_domestic_actions.py — 11 tests (existing)
- tests/test_session4d.py — 12 tests (existing)
- tests/test_coup.py — 2 tests (existing)

Target: 50+ tests passing.
Paste full pytest output. ALL tests must pass before docs.

---

## STEP — DOCUMENTATION

Only after all tests pass.

**ARCHITECTURE.md:**
- Section 11 (Epitaph): update to note angle history persistence fix,
  fallback template system, reset detection
- Section 19 (Console Logs): add all new logs from fixes_10
- Add note on negotiated deal warning deferral (Fix 9)
- Update "Last updated" line

**STATUS.md:**

```
## Current Build — fixes_10

IMPLEMENTED:
- Epitaph angle history persists through elections (root cause fixed)
- Epitaph fallback template system (safety net)
- Domestic action costs recorded in personal wealth ledger
- Election warning frontend reads backend flag correctly
- DPRG Intelligence Sharing delivers actual intel content
- Budget projection caveat includes world events
- Arabia embargo tier boundary warning
- Debug panel for manual stat adjustment (dev tool, hidden in prod)
- Intel intercept JUST ENACTED distinction

DEFERRED:
- Negotiated deal cross-NPC warnings (full fix Session 7 GM layer)

FILES MODIFIED:
- npc_engine.py (epitaph reset fix, fallback templates, DPRG intel,
  intercept JUST ENACTED)
- game_state.py (epitaph_angles_used persistent field)
- turn_processor.py (find and fix election reset, Arabia warning,
  projection text, DPRG intel trigger)
- api.py (ledger entries, debug endpoint, Option A election if needed)
- StatusBar.jsx (election warning frontend fix)
- GameScreen.jsx (amber banner fix, debug panel keyboard listener)
- frontend/src/components/DebugPanel.jsx (NEW)
- tests/test_epitaph.py (1 new test)
- tests/test_ledger.py (NEW — 3 tests)
- tests/test_arabia.py (2 new tests)
- ARCHITECTURE.md
- STATUS.md

UNRESOLVED (carry to fixes_11 if needed):
- Fix D (fixes_6): deal condition migration — needs old save file
- Fix G (fixes_6): prose payment panel — needs specific scenario

## Previous — fixes_9: 9 fixes, 45/45 tests
## Previous — fixes_8: 14 fixes, 40/40 tests
## Archive: Sessions 4A-4D, fixes_1 through fixes_7, 110+ cumulative
```

---

## CONSTRAINTS

**MAY touch:**
- npc_engine.py
- game_state.py
- turn_processor.py
- api.py
- StatusBar.jsx
- GameScreen.jsx
- EotPanel.jsx (DPRG intel display only)
- frontend/src/components/DebugPanel.jsx (NEW)
- tests/test_epitaph.py (add 1 test)
- tests/test_ledger.py (NEW)
- tests/test_arabia.py (new or add to existing)
- ARCHITECTURE.md
- STATUS.md

**MAY NOT touch:**
- ElectionPanel.jsx
- ShadowCabinet.jsx
- OffersPanel.jsx
- SkimPanel.jsx
- IntelAllocationPanel.jsx
- EndingPanel.jsx
- DialoguePanel.jsx
- Any test file not listed above

**Do NOT:**
- Add vector database or memory system (Session 5)
- Add advisor system (Session 5)
- Implement structured negotiation templates (Session 6)
- Implement GM inference layer (Session 7)
- Add new npm packages or Python dependencies
- Mark complete without running full test suite and pasting output

---

## VERIFICATION CHECKLIST

Before posting "done":

Backend:
- [ ] After election, `(recent angles:)` log shows populated list,
      not empty list
- [ ] `EPITAPH ANGLE HISTORY RESET DETECTED` log never fires
- [ ] `FIX C LEDGER MISMATCH` log never fires after domestic actions
- [ ] DPRG Intelligence Sharing: intel content visible in EOT
- [ ] Arabia at relations 27: tier boundary warning fires in EOT
- [ ] Bankruptcy projection text includes "world events"
- [ ] 50+ tests passing — paste full output

Frontend:
- [ ] Turn 3: amber banner visible ABOVE communiqués
- [ ] Turn 3: "🗳️ ELECTION NEXT TURN" in status bar
- [ ] Turn 4: election panel renders, both indicators gone
- [ ] Ctrl+Shift+D opens debug panel
- [ ] Debug panel: changing USA relations to 80 and clicking
      Apply updates the NPC card immediately
- [ ] Debug panel: NOT visible if NODE_ENV=production

Flag anything unverifiable through code/tests as
"UNVERIFIED — needs browser test".
