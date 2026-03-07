# WORLD STAGE — SESSION HANDOFF
Generated: March 4, 2026

---

## WHAT THE GAME IS

Geopolitical simulation. Player leads fictional nation of Europa across 10 turns.
Not win/lose — a narrative generator for political biographies.
Theme: loneliness of power. Players feel clever and compromised simultaneously.

**Stack:** FastAPI backend (Railway) + React frontend (Vercel).
**Deployed:** world-stage.vercel.app. GitHub auto-deploy.
**Files:** Backend — npc_engine.py, turn_processor.py, game_state.py, api.py.
Frontend — DialoguePanel.jsx, StatusBar.jsx, GameScreen.jsx, ShadowCabinet.jsx, EndingPanel.jsx.

**NPCs:** Bill Hartwell (USA), Sadam (Arabia), Marsha (EU Commission), Ji-won (DPRG).

---

## CURRENT DEVELOPMENT STATUS

**Stages 1–5 complete.** All core systems implemented including:
- Core game loop, budget/stability/approval/relations
- Oil pricing, sanctions, skimming, heat system
- Four NPC personalities with Claude-powered dialogue
- Two-call negotiation architecture with rapport system
- Dynamic willingness formula
- Intelligence system Tiers 1–3
- Four corruption upgrades, Shadow Cabinet UI
- Loyalty Brigade system (partially — see below)
- State Identity progression + Power Base axis
- Per-turn epitaphs in historian voice
- Military Strength resource
- Election mechanic (all four outcomes)
- Domestic action suite (Media, Judicial, Political, Extraction — purchaseable)
- NPC leverage demands (Sadam $2B reward for Judicial Capture confirmed working)
- Alternate endings: Voluntary Retirement, Democratic Transition, State Capture,
  Martyrdom — all implemented
- Intel budget allocation panel
- Tech Level (scaffolding only — redesign deferred to Session 5)
- Resource Development axis
- Regime type labeling

**Session 6 architectural changes completed (104 tests passing):**
- Security axis split into Military + Intelligence
- Resource Development added (7 axes total)
- Comprehensive action suites across all axes
- NPC conditional leverage demands
- Alternate endings

---

## FIXES_18 STATUS — CURRENT BATCH

| Fix | Issue | Status |
|-----|-------|--------|
| A | Counter-offer dual conditions rendering | ✅ Confirmed |
| B | Historian wealth diagnostic logs | ⚠️ UNVERIFIED — logs not appearing in console |
| C | Approval trace logs (4-bucket) | ✅ Confirmed |
| D | Bill character regression (was refusing in-character) | ✅ Confirmed |
| E | Intelligence intercepts firing 3x per NPC per turn | ✅ Confirmed |

**Fix B detail:** The three `[HISTORIAN]` diagnostic console.logs were supposed
to appear at Turn 10 when the historian verdict generates. They are not showing
up in the browser console. Two possible causes:
1. Logs are firing in Python backend but not piped to frontend console
2. Logs were placed in the wrong code path in api.py or npc_engine.py

The historian verdict IS generating successfully (confirmed in game export).
The fix itself may be working — the diagnostic logs just aren't visible.

**To verify Fix B in next session:**
Ask Claude Code: "In npc_engine.py, find the historian verdict generation
function. Confirm these three console.logs exist and are in the correct path:
`[HISTORIAN] Personal wealth passed to prompt: $X.XB`
`[HISTORIAN] Actual game state personal_wealth: $X.XB`
`[HISTORIAN] Total skimmed in prompt: $X.XB`
If they are Python print() calls, they will only appear in Railway logs,
not browser console. If that's the case, the fix is implemented correctly —
just check Railway logs instead."

---

## KNOWN BUGS — VERIFIED IN PLAY (not yet in any fix doc)

These are bugs confirmed across multiple test runs, documented in
worldstage_running_notes.md in outputs/. Listed in priority order.

### HIGH PRIORITY

**Re-render loop spam (PERFORMANCE)**
Three diagnostic logs fire on every React state update instead of once per turn:
- `[DialoguePanel] FIX A: pending_npc_contacts at turn start`
- `[DialoguePanel] Fix 22+23: usa negotiate cost...`
- `[DialoguePanel] FIX C: Rendering INCOMING for: usa`

They are inside render paths, not useEffect hooks. Creates massive console noise
that buries real diagnostic logs (this is what hid the Fix B historian logs).
Fix: Move all three into useEffect(() => { ... }, [turnNumber]) so they fire
once per turn, not on every state update.
File: DialoguePanel.jsx lines ~330, ~354, ~386

**Epitaph text similarity not checked (MEDIUM)**
Saturation rule prevents same-action-type repeats but doesn't check if the
generated TEXT is similar to recent epitaphs. Turns 4+5 in a test run produced
word-for-word identical text despite different action types.
Fix: After generating, compare first N words against last 2 epitaphs. If too
similar, regenerate with instruction to take a different angle.
File: npc_engine.py → generate_epitaph()

**Western Bloc Joint Pressure double-fire (MEDIUM)**
Two pressure triggers can fire in the same turn — deal-based trigger (Arabia
premium deal) and threshold-based trigger (USA/EU both critically low).
Player hit -8% stability and -6% approval twice from overlapping systems.
Fix: Add western_bloc_pressure_fired_this_turn flag, reset each EOT.
File: turn_processor.py

**Budget negative without bankruptcy warning (MEDIUM)**
Bankruptcy pre-warning not catching sanctions-drain path. Player hit -$5.3B
budget with no warning. Warning checks skim overage but not cumulative
sanctions + oil + government costs combination.
Fix: Pre-warning should project next turn budget from ALL drain sources.
File: turn_processor.py → pre-warning system

### MEDIUM PRIORITY

**Election turn epitaph produces "nothing notable" (MEDIUM)**
On election turns, _build_epitaph_delta() returns generic stagnation text
because there's no diplomatic choice to build the delta from.
Fix: Detect action_type == 'election', inject election result context.
File: npc_engine.py → _build_epitaph_delta()

**Election warning fires at wrong point in turn (MEDIUM)**
Warning appears at END of Turn N EOT, after player already made all choices.
Should appear at TOP of Turn N BEFORE communiqués and choices.
Fix: Move from EOT output to top of GameScreen above communiqués.
File: GameScreen.jsx + EotPanel.jsx

**Intel intercepts not referencing domestic actions (MEDIUM)**
Intercepts only react to personal wealth. Judicial capture, press suppression
etc. are not mentioned even though other nations would know.
Fix: Add domestic action flags to intercept generation prompt context.
Each NPC reacts in character (Bill alarmed, Marsha formal, Sadam approving,
Ji-won encouraging).
File: npc_engine.py → intercept generation

**Scandal threshold not enforcing floor (MEDIUM)**
Scandals reported firing at 25–40% heat; floor should be 30%. Carry from
earlier sessions. Not retested recently.
Fix: Verify `if heat < 30: skip scandal roll` in turn_processor.py.

**Coup not firing at military 0 (MEDIUM)**
Military hit 0 in a test run, coup warning appeared but coup didn't trigger.
Fix: At military == 0 AND stability below threshold, coup probability
should be 40–60%. Verify military_zero multiplier in coup logic.
File: turn_processor.py

### LOW PRIORITY

**StatusBar double render**
HEADER VALUES console log fires twice per state update.
Fix: Wrap in useEffect with approval/stability dependencies.
File: StatusBar.jsx

**Election countdown not shown in status bar**
Status bar has empty space next to regime label during election warning turn.
Fix: Show "🗳️ ELECTION T-1" indicator when election_warning_shown == True.
File: StatusBar.jsx

**Sanction risk logged twice in same EOT**
Two separate warnings for same condition. Consolidate into one line.
File: turn_processor.py

**Intel budget state has no persistent display**
After confirming allocation, player has no way to see current intel budget
status between allocation screens.
Fix: Add indicator in Shadow Cabinet drawer.
File: ShadowCabinet.jsx

**Tech Level hidden at 0**
Tech display hidden when tech_level == 0. Player has no way to know stat exists.
Fix: Show greyed-out "TECH 0" always.
File: StatusBar.jsx

### DESIGN/BALANCE ISSUES (not pure bugs)

**Arabia static deal dominates negotiated ceiling**
Arabia static choice (+$12B) is objectively better than negotiated ceiling
(~$4.8B). No rational reason to negotiate. Needs design discussion.
Options: cap static below negotiated ceiling, or make immediate cross-NPC
consequences visible on confirmation screen.

**Marsha relation scaling flat**
EU 93 produces same tone/flexibility as EU 50. High relations should unlock
larger offers and warmer tone. Not fixed.

**Named NPC penalty + cross-NPC penalty stacking**
Arabia takes double hit from some EU deals (-2 cross-NPC + -10 named = -12).
Should cap at -8 or named should replace cross-NPC.

---

## CONFIRMED WORKING (tested in multiple full playthroughs)

- GDP baseline revenue all turns ✅
- Military Strength + decay (-2/turn) ✅
- Military tier effects (50+ gives USA +5/turn) ✅
- Weapons purchase mechanic ✅
- Deal broken detection ✅
- Conditional payment withheld + verified release when condition met ✅
  (EU deal: $0.2B/turn conditional on Arabia < 80 — withheld turns 8–9,
  released turn 10 when Arabia dropped to 27. End-to-end working.)
- Pre-warning system (Arabia 25/35, bankruptcy) ✅
- Diplomatic Crisis screen ✅
- Cross-NPC penalties all directions ✅
- Relations 100 unlock (EU full integration) ✅
- Marsha negotiation voice and specificity demands ✅
- NPC leverage demands (Sadam $2B reward for Judicial Capture) ✅
- Domestic actions purchaseable from Shadow Cabinet ✅
- Election mechanic end-to-end (all four outcomes) ✅
- Voluntary Retirement ending ✅ (confirmed: Stability 60+, Approval 50+, Personal $20B+)
- Approval trace logs (4-bucket) working correctly ✅
- Fix 22+23: negotiate cost discount from Political axis ✅
  (Tier 1: -25%, Tier 2+: -50%)
- Counter-offer dual conditions rendering ✅
- Intelligence intercept single-fire per NPC ✅
- Bill character voice ✅

---

## NEXT SESSION PRIORITIES

**Immediate (fixes_19):**
1. Fix re-render loop spam in DialoguePanel.jsx (moves three logs to useEffect)
2. Verify/locate Fix B historian logs — check if they're Python print() in
   Railway logs vs browser console
3. Election turn epitaph delta fix
4. Western Bloc double-fire flag
5. Bankruptcy pre-warning drain coverage

**Session 4 features (after fixes_19 verified):**
Per roadmap, these are the remaining unimplemented Session 4 items:
- Ji-won expanded role (currently underutilized)
- Leverage system deepened (allies who helped hold implicit power in dialogue)
- NPC conditional leverage demands — Marsha/Bill/Ji-won variants
  (only Sadam confirmed working; Marsha/Bill/Ji-won unverified)
- Tech Level redesign (passive relationship-weighted gain — see Design Notes)

**Session 5 on horizon:**
- Vector database for persistent NPC memory (Pinecone/ChromaDB)
- Advisor system (Finance Minister, Security Chief, Diplomatic Aide)
- Brigade/Domestic Action UI unification (two-drawer Shadow Cabinet)
- Full domestic action audit (reversals, costs, NPC reaction depth)
- Tech Level passive gain implementation

---

## HOW TO SUBMIT FIXES TO CLAUDE CODE

**Prompt structure that works:**
```
Read worldstage_fixes_18.md (or whichever is current).
Confirm the first fix title before proceeding.
For each fix: implement, add console.logs, stop.
Human will verify in browser.
Do not implement any other fix files.
Do not add new features.
```

**What works:**
- Specific function names and file locations
- Console.log verification requirements
- pytest for algorithmic fixes
- Asking it to confirm fix title before starting

**What doesn't work:**
- Asking it to "run the game" — it can't run interactive sessions
- Parse checks as verification — confirms syntax not behavior
- Not specifying file locations — it guesses wrong
- Marking complete without verification — it will always say done

**Stale process pitfall:**
FastAPI/uvicorn route registration failures from stale processes not reloading.
Kill all processes and do a clean restart if routes aren't updating.

---

## DESIGN PRINCIPLES TO PRESERVE

- Hard-code consequences, author personalities, seed starting conditions,
  let Claude generate everything in between
- Sophie's choice principle: best crises force binary where both options hurt
- Mechanics create dependency loops — solving immediate problems deepens
  structural vulnerabilities
- Players should feel clever and compromised simultaneously
- Never let Claude decide consequences — it narrates them
- Static choices should never dominate negotiation (currently violated for Arabia)
- The game is a narrative generator, not a conventional strategy game
- Success measured by quality of emergent stories, not win/lose conditions

---

## FILE REFERENCE

- worldstage_running_notes.md — full bug list with root causes
- worldstage_fixes_18.md — current fix batch (4/5 verified)
- worldstage_session_handoff.md (in project files) — older session context
- WorldStage_Roadmap-2.docx (in project files) — full roadmap Sessions 1–10
- worldstage_session5_design.md — Session 5 design spec
- worldstage_alternate_endings_guide.md — all four endings, conditions, text
