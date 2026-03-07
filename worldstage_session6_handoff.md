# WORLD STAGE — SESSION 7 HANDOFF
Generated: March 1, 2026

---

## WHAT THE GAME IS

A geopolitical simulation where you manage the fictional nation of Europa
across 10 turns. Not a win/lose game — a narrative generator for political
biographies. Core theme: the loneliness of power. Players feel clever and
compromised simultaneously.

Four NPC relationships: Bill Hartwell (USA), Sadam (Arabia), Marsha (EU
Commission), Ji-won (DPRG). Each has authored personality, motivations,
red lines. Claude generates dialogue within authored containers.

**Stack:** FastAPI backend (Railway) + React frontend (Vercel). Claude API
throughout. Deployed at world-stage.vercel.app. GitHub auto-deploy.

**Design pillars:**
- Authored scenario seeds (starting conditions)
- Authored NPC personalities (Claude executes, doesn't invent)
- Authored consequence frameworks (Claude narrates, never decides)

---

## CURRENT DEVELOPMENT STATUS

**Completed:** Stages 1-6 fully implemented plus extensive bug fixing
through fixes_13 to fixes_16 and individual single fixes. Session 6
completed all 8 phases: axis redesign, operations audit, leverage demands,
alternate endings, and heat system additions.

**Tests:** 104 passing, 0 failing. Clean production build.

---

## CONFIRMED WORKING

### Core Loop
- Turn-based decisions, budget/stability/approval/relations ✅
- GDP baseline revenue with real tax-rate formula ✅
- GDP contraction at low approval/stability ✅
- Government costs, oil imports, cabinet maintenance ✅
- Military decay -2/turn ✅
- Military tier effects (40+ gives stability bonus, 50+ gives USA +5/turn) ✅
- Stability drift (approval gap) ✅
- Tech level progression ✅
- Bond financing ($5B routine / $10B emergency, once per game) ✅
- Bankruptcy risk warnings ✅
- Pre-warning system (Arabia 25/35, bankruptcy) ✅
- Game ends at Turn 10 with historian summary ✅

### Diplomatic System
- Four NPC personalities with Claude-powered dialogue ✅
- Two-call negotiation architecture with rapport system ✅
- Dynamic willingness formula ✅
- Static deal selection ✅
- Negotiated deal acceptance ✅
- Cross-NPC penalty matrix (all directions) ✅
- Cross-NPC penalties suppressed for covert deals ✅
- Deal broken detection and diplomatic crisis screen ✅
- Conditional payment verification pipeline ✅
- Diplomat advisor negotiation discount ✅
- NPC ceiling bonuses: GDP Credibility +20%, Strategic Resource Partner
  +50% (one NPC), Force Projection +25% (targeted NPC while cooldown
  active) ✅

### NPC 100 Unlocks
- USA 100: Full Alliance (sanctions immunity, coup -50%, military +10,
  GDP +15%, +$3B/turn) ✅
- Arabia 100: Energy Sovereign ($4B/turn dividend, military +15, USA/EU
  caps at 35/40) ✅
- EU 100: Full Integration (+5% approval/turn) ✅
- DPRG 100: Shadow Alliance (-5 heat/turn) ✅

### Relations 100 Caps (when other NPC hits 100)
- Arabia 100: USA capped at 35, EU capped at 40 permanently ✅
- USA 100: DPRG capped at 40 permanently ✅

### Pressure and Sanctions
- USA sanctions tiers 1-4 ✅
- Arabia embargo tiers 1-3 ✅
- EU trade friction and trade restrictions ✅
- Western Bloc joint pressure ✅

### INCOMING System
- Bill: sanctions tier 2+, 40% chance, 3-turn cooldown ✅
- Sadam: Arabia relations < 40, 35% chance ✅
- Marsha: regime_idx >= 2, 50% chance ✅
- Ji-won: personal wealth >= $15B AND DPRG >= 40, 45% chance ✅
- Tier 2 ambient contacts (5% per NPC per turn, relation-scaled tone) ✅
- INCOMING renders as Private Channel in communiqué area ✅
- Negotiate button shows $0 for INCOMING ✅

### NPC Conditional Leverage Demands (Session 6)
- Marsha (EU 60+, media taken): demands media reform, Accept gives
  EU +20, media axis reset, +$4B national; Decline keeps status quo ✅
- Bill (USA 70+, opposition dissolved): demands opposition release,
  Accept gives USA +10, political axis -2; Decline keeps status quo ✅
- Sadam (Arabia 70+, judicial captured): automatic reward, +8 relations,
  +$3B national ✅
- Ji-won (DPRG 60+, press suppressed): automatic reward, +8 relations,
  +3% stability ✅
- Leverage contacts render with ⚡ LEVERAGE DEMAND badge and
  Accept/Decline buttons in DialoguePanel ✅

### Election Mechanic
- Fair election, observers, finger on scale, canceled — all variants ✅
- Election and negotiated deal both record as separate turn history
  entries on same turn ✅
- Diplomatic choice available after election resolves ✅
- Negotiation only accessible after election result shown ✅
- Democracy lock enforces after observer elections ✅
- Constitutional Revision blocks elections permanently ✅

### Intelligence System
- Tier 1/2/3 intercepts ✅
- Intel tier written to npc_intel_tiers[target] after Get Intel ✅
- Blackmail reads from npc_intel_tiers[selectedTarget] correctly ✅
- Bill refuses intel targeting USA (in-character) ✅

### Shadow Cabinet — Axes (Session 6)
- Seven axes: Military, Intelligence, Resource Dev, Media, Judicial,
  Political, Extraction ✅
- Budget source split: Military/Resource Dev = national; Intelligence
  L1-3 = national, L4+ = personal; all others = personal ✅
- Axis investment and defund with permanent floors ✅
- Advisor gating by axis level and regime ✅
- Advisor pool: deduplication enforced (max one per archetype) ✅
- Finance Minister always in pool ✅
- Stage directions stripped from all NPC dialogue ✅

### Military Axis (Session 6)
- L3: Defense Procurement — weapons purchases, +5 military per buy ✅
- L6: Standing Army — military decay -2/turn → -1/turn ✅
- L9: Force Projection — NPC ceilings +25% on targeted NPC, target -8
  relations, 3-turn cooldown ✅
- L10: Arms Export — sell weapons to one NPC per turn, +$4B national,
  +8 relations with buyer, military -5 per sale ✅
- Arms Export uses dedicated inline NPC selector (independent from
  global target selector) ✅

### Intelligence Axis (Session 6)
- L3: State Intelligence Bureau — Tier 1/2 intercepts, Spy Chief
  unlocks, gates brigade operations 3-4 ✅
- L5: Intelligence Sharing — offer to one NPC per game, +12 relations ✅
- L6: Shadow Apparatus — Tier 3 intercepts, covert ops ✅
- L9: Full Spectrum — neutralize NPC covert actions ✅
- L10: Counterintelligence Veil — UI note "Active — NPC intelligence
  degraded" (mechanical effect deferred) ✅
- Intelligence L3+ passive: -3 heat/turn at EOT ✅

### Media Control Axis (Session 6)
- L3: Suppress a Scandal — $1B personal, kill incoming scandal ✅
- L6: Narrative Campaign — $2B personal, +8% approval, NPC credibility
  hit ✅
- L9: Information Blackout — $4B personal, world events muted 2 turns ✅

### Judicial Capture Axis (Session 6)
- L3: Drop Investigation — scandal immunity, free, once per turn ✅
- L6: Lawfare — $3B personal, suspend NPC pressure event 2 turns ✅
- L9: Asset Seizure — $5B personal, +$3B national, stability +5%,
  approval -8% ✅

### Political Control Axis (Session 6)
- L3: Party Consolidation — $1B personal, approval drain from heavy
  taxes -25% for 3 turns ✅
- L6: Pack the Cabinet — $3B personal, fourth advisor slot permanently ✅
- L9: Constitutional Revision — $6B personal, removes elections, regime
  shifts hard right, EU -15 ✅

### Extraction Network Axis (Session 6)
- L3: Shell Company — heat -5 immediately, $1B personal ✅
- L5: Large Skim Penalty Halved — permanent passive ✅
- L5 milestone: +$7B personal injection (one-time) ✅
- L6: Offshore Transfer — move up to $10B national → personal, no skim
  heat, EU intel notices ✅
- L7: Private Security Force — $5B personal, personal militia 15
  military, coup immunity ✅
- L7 milestone: skim ceiling removed ($15B massive skim) ✅
- L9: Sovereign Wealth Capture — 15% GDP auto-diverts to personal, plus
  inject any amount personal → national ✅

### Resource Development Axis (Session 6 — NEW)
- L3: Export Contract — one-time +$8B national, no NPC penalties ✅
- L5: GDP Credibility — NPC negotiation ceilings +20% permanently ✅
- L6: Sovereign Collateral Loan — $10B, 15% interest, zero NPC
  penalties, once per game ✅
- L8: Strategic Resource Partner — choose one NPC, their ceiling +50%
  permanently ✅
- L9: Resource Independence — oil imports eliminated permanently, EU +5 ✅
- L10: Better Bond Terms — reduced interest rates on bonds ✅

### Operations Tab (Session 6 — Redesigned)
- Section order: Standard Ops → Military → Intelligence → Black Ops →
  Media → Judicial → Political → Extraction → Resource Dev ✅
- All 28 operations audited and verified working ✅
- Per-operation gate checking: ops 1-2 gate on Military ≥ 3,
  ops 3-4 gate on Intelligence ≥ 3 ✅
- Covert Security deducts from personal wealth (not national) ✅
- Frontend affordability check matches budget source per operation ✅

### Alternate Endings (Session 6)
- Democratic Transition (priority 4, highest): EU 80+, no press
  suppression, approval 65%+, Turn 10 only ✅
- Voluntary Retirement (priority 3): stability 60+, approval 50+,
  personal wealth $20B+, Turn 10 only ✅
- State Capture Complete (priority 2): personal wealth $50B+, capture
  triad (Constitutional Revision + press suppression + judicial capture),
  Turn 10 only ✅
- Martyrdom (priority 1, lowest): stability 0, approval 70%+,
  any turn ✅
- EndingPanel shows distinct icon, color, title, flavor per type ✅
- Historian summary includes ending-type-specific framing ✅
- EndingPanel displays historian verdict with color-coded border ✅

### Heat System (Session 6 — Additions)
- Domestic action heat: Liquidate Journalists +20, Suppress Press +8,
  Dissolve Opposition +5 ✅
- Judicial axis L3 reached: +10 heat ✅
- Foreign Influence Ops (brigade op 3): +10 heat ✅
- Intelligence axis L3+ passive: -3 heat/turn at EOT ✅
- DPRG Shadow Alliance: -5 heat/turn (balanced from initial -10) ✅
- Intelligence Apparatus upgrade: -3 heat/turn in detection roll ✅
- Console.log prints ([HEAT]) for all heat additions and reductions ✅

### World Events
- Dynamic world event generation ✅
- Events affect relations, oil, stability, approval correctly ✅

### Skim System
- Small, medium, large, massive (L7+) skim tiers ✅
- Skim projection includes real tax-rate GDP formula ✅
- Skim projection includes sanctions costs, EU friction, active deal
  income, Arabia dividend ✅

### Regime and Power Base
- State Identity progression labels ✅
- Power Base axis (Mass-Dependent → Elite-Captured) ✅
- Per-turn epitaph in historian voice ✅
- Legacy verdict at Turn 10 ✅

---

## KNOWN ISSUES — DEFERRED TO SESSION 7

### Private Security Force Detection Fires Every Turn
Private Security Force detection at heat 80+ fires every turn heat stays
at 80+, applying USA -10 and EU -10 repeatedly. Should fire once and set
a `militia_discovered` flag. The repeated -10/-10 per turn is too punishing.

### Constitutional Revision Regime Shift Unlocks Unpaid Axes
Constitutional Revision shifts regime hard right, which increases axis
values (Military +3, Political +3, Media +2). This may unlock action
suites the player hasn't invested in — axis levels increase without
paying the per-level cost.

### Counterintelligence Veil Mechanical Effect Deferred
Intelligence L10 Counterintelligence Veil shows "Active — NPC intelligence
degraded" as a UI note only. The NPC willingness system has not been
modified to actually degrade NPC intelligence gathering or miscalibrate
their offers/pressure events.

### Standing Army Decay Ordering Issue
Standing Army (Military L6) reduces military decay from -2/turn to -1/turn.
However, if an election fires on the same turn that reduces the military
axis, the decay calculation may use the post-election axis value instead of
the start-of-turn value. Decay should use the start-of-turn axis value to
avoid the election axis reduction masking the Standing Army benefit.

### Arms Export Inline Selector Verification Needed
Before Phase 4, Arms Export auto-targeted the NPC with lowest relations.
Phase 4 replaced this with an inline NPC button selector independent from
the global target. Verify in playtesting that the inline selector works
correctly and targets the intended NPC.

---

## CONFIRMED WORKING — DO NOT REGRESS

Critical mechanics that have been fixed multiple times and must be
preserved through future architectural changes:

- Arabia 100 fires after check_pressure_events() only (not pre-world-events)
- INCOMING conditions are single-condition probability gates (not AND logic)
- Intel tier written to npc_intel_tiers[target] after Get Intel
- Advisor pool deduplication enforced (max one per archetype)
- Finance Minister in always-available list
- Election records separately from diplomatic choice in turn history
- Diplomatic choice available after election resolves
- Skim projection uses real tax-rate formula matching EOT section 9b
- Cross-NPC penalties suppressed for covert deals
- Game ends at Turn 10 with historian summary
- Constitutional Revision blocks elections (guard in api.py + UI) ✅
- Leverage demands fire once per game (flag-gated) ✅
- Alternate endings check in priority order (highest first) ✅
- Budget source split: national vs personal per axis ✅
- Operations gate on correct axis (Military vs Intelligence) ✅
- Heat generation wired for domestic actions + judicial L3 + foreign influence ✅

---

## HOW TO SUBMIT FIXES TO CLAUDE CODE

**What works:**
- Specific function names and file locations
- Console.log verification requirements
- One fix at a time with single verification step
- Asking it to confirm fix title before starting

**What doesn't work:**
- Asking Claude Code to "run the game" — it can't run interactive sessions
- Parse checks as verification — confirms syntax not behavior
- Not specifying file locations — it guesses wrong
- Marking complete without verification

**Best prompt structure for single fixes:**
```
In [specific file], [specific function], fix [specific problem].

Add one console.log: [specific log format]

Do not change any other logic.
Do not implement any other fixes.
Do not add new features.
```

---

## FILE LOCATIONS

- Backend: FastAPI — npc_engine.py, turn_processor.py, game_state.py, api.py
- Frontend: React — DialoguePanel.jsx, StatusBar.jsx, ShadowCabinet.jsx,
  GameScreen.jsx, EndingPanel.jsx, EndingScreen.jsx
- Tests: tests/test_epitaph.py, tests/test_session4d.py
- Roadmap: WorldStage_Roadmap.docx (in project files)

---

## DESIGN PRINCIPLES TO PRESERVE

- Hard-code consequences, author personalities, seed starting conditions,
  let Claude generate everything in between
- Sophie's choice principle: best crises force binary where both options hurt
- Mechanics create dependency loops — solving immediate problems deepens
  structural vulnerabilities
- Players should feel clever and compromised simultaneously
- Never let Claude decide consequences — it narrates them
- Static choices should never dominate negotiation
- Features should feel authored rather than mechanical
