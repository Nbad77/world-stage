# WORLD STAGE — SESSION HANDOFF
Generated: March 9, 2026

---

## WHAT THE GAME IS

Geopolitical simulation. Player leads fictional nation of Europa across 10 turns.
Not win/lose — a narrative generator for political biographies.
Theme: loneliness of power. Players feel clever and compromised simultaneously.

**Stack:** FastAPI backend (Railway) + React frontend (Vercel).
**Deployed:** world-stage.vercel.app. GitHub auto-deploy.
**Auth:** Clerk dev instance. Auth optional — guests play without persistence.

**Backend files:** npc_engine.py, turn_processor.py, game_state.py, api.py,
gm_engine.py, advisor_engine.py
**Frontend files:** GameScreen.jsx, DashboardLayout.jsx, LeftSidebar.jsx,
RightSidebar.jsx, NpcCard.jsx, AdvisorPanel.jsx, BriefingSummaryCard.jsx,
DomesticTab.jsx, PromiseTracker.jsx, SummitCommitmentTracker.jsx,
SummitModal.jsx, BackchannelModal.jsx, ShadowCabinet.jsx

**NPCs:** Bill Hartwell (USA), Sadam (Arabia), Marsha (EU Commission), Ji-won (DPRG).
Russia and China: passive world actors (no direct negotiation yet).

---

## CURRENT DEVELOPMENT STATUS

**Sessions 1–6 complete.** All core systems from original roadmap implemented.
**Session 7 complete (7A–7E).** Full living world infrastructure shipped.
**fixes_21 complete.** All high/medium/low priority bugs resolved.

### Session 7 Systems — All Complete

**7A — Dashboard Rebuild + Day/Era System**
- Three-panel desktop layout (left sidebar / center / right sidebar)
- Mobile card feed layout via Tailwind responsive breakpoints
- Turns → Days, "End Turn" → "End Day"
- Ambient mode vs Event mode header indicator
- Era system: threshold-driven + time-driven (20-day backstop) transitions
- Historian write-up button (on-demand + automatic on era close)
- GM Inference Layer prototype (Sadam + energy proposals only)

**7B — Daily Briefing System**
- Briefing item tags: URGENT / INCOMING / INTELLIGENCE / DEVELOPING
- Urgency escalation: Day 1 ignore = no penalty, Day 2 = -2 relations,
  Day 3+ = -5 relations URGENT CONFRONTATION
- Player-initiated contact (CONTACT button on NPC cards)
- BriefingSummaryCard at top of each day

**7C — Advisor System + Russia/China Passive Integration**
- Three fixed advisors: Finance Minister, Security Chief, Diplomatic Aide
- 2 slots per day, assign/unassign toggle
- Claude Haiku-generated analysis on assignment (distinct voices per advisor)
- Trust drain per EOT, defection at trust < 20
- Russia and China cards in right sidebar (passive, no Contact button)
- Deal-based and regime-based drift for Russia/China relations
- Russia/China context injected into world event generation

**7D — Backchannel System**
- BACKCHANNEL button on each active NPC card with risk tier (LOW/MODERATE/HIGH/CRITICAL)
- BackchannelModal: dark UI, detection risk meter, conversation history
- Detection risk formula: base by NPC × opsec modifier × NPC intel modifier
- EOT detection rolls for active promises
- Discovery consequences hardcoded per scenario
- PromiseTracker: COVERT COMMITMENTS in center panel
- Backchannel history log expandable in PromiseTracker
- Ji-won leverage filing mechanic

**7E — UN Summit**
- Triggers every 20 days (summit_due flag), blocks End Day until addressed
- SummitModal: full-screen group chat UI, sidebars remain visible
- All 6 NPCs respond in parallel (ThreadPoolExecutor)
- Ji-won 30% silence chance
- Russia and China with OBSERVER badges, muted treatment
- Auto-position feature: generates holding statement, player can edit
- SummitCommitmentTracker: public commitments in center panel (blue tint)
- Summit credibility score (starts 100, -15 per broken commitment)
- UN Standing section in left sidebar
- Summit stats on ending screen

---

## FIXES_21 — ALL COMPLETE ✅

| Fix | Issue | Status |
|-----|-------|--------|
| A | Summit markdown headers leaking | ✅ Plain text instruction all 6 NPC prompts |
| B | Summit reaction type inference wrong | ✅ Challenge-first keyword order |
| C | Marsha summit response cut off | ✅ Token limit 150→400 |
| D | Re-render loop spam | ✅ Already fixed in prior session |
| E | Mobile modal regression | ✅ "Private Channel"→"Negotiation", mobile circles confirmed calling onBackchannel |
| F | Resume Game / Continue Game regression | ✅ Catch handler only clears localStorage on 404, tri-state loading state |
| G | Pre-action deal conflict warning | ✅ Amber warning modal before confirming conflicting choice |
| H | Bankruptcy pre-warning missing sanctions drain | ✅ Projects next turn's effective tier |
| I | StatusBar double render | ✅ Already in useEffect |
| J | Election countdown not shown | ✅ "ELECTION T-{N}" in LeftSidebar |
| K | Sanction risk double-log | ✅ Dedup checks for USA + Arabia |
| L | Tech Level hidden at 0 | ✅ Shows "0" at 0.4 opacity always |
| M | Intel budget no persistent display | ✅ Compact 5-tag allocation in ShadowCabinet header |
| N | Cabinet button buried in corner | ✅ Moved above ERA/DAY, gold border, renamed "SHADOW CABINET" |

---

## CONFIRMED WORKING (post fixes_21)

- Three-panel dashboard layout ✅
- Day/era system with historian on demand ✅
- Advisor analysis (Finance Minister, Diplomatic Aide, Security Chief) ✅
- Russia/China passive cards with deal-based drift ✅
- Backchannel modal with detection risk meter ✅
- Promise tracking (PromiseTracker, history log) ✅
- UN Summit group chat (all 6 NPCs, plain text, correct reaction types) ✅
- Ji-won silence mechanic ✅
- Auto-position feature (plain text) ✅
- Summit credibility tracking ✅
- Urgency escalation system ✅
- Player-initiated contact ✅
- Domestic affairs tab ✅
- Tech Level passive gain formula ✅
- GM Inference Layer (Sadam / energy proposals) ✅
- Resume Game / Continue Game after refresh ✅
- Deal conflict warning before action ✅
- Shadow Cabinet button prominent ✅

---

## ADVISOR SYSTEM REGRESSION — LOGGED FOR DEDICATED SESSION

The current advisor system (3 fixed advisors, trust mechanics) replaced a richer
prior system. What was lost:

- 7 base archetypes + 2 nefarious archetypes (Spy Chief, General, Diplomat,
  Propagandist, Oligarch, Finance Minister, Technocrat + Enforcer, Fixer)
- Randomized characters with unique names generated from archetype templates
- Stat distortion bias — unreliable narrator mechanic (Propagandist inflates
  approval display, backend uses true values)
- Loyalty-based betrayal events (skim budget, leak intel, sabotage relations)
- Hire/dismiss/eliminate cycle with regenerating pool ($2B personal to eliminate)
- Regime-gated progression (Oligarch unlocks at Patronage State+)
- Archetype-specific elimination consequences
- Negotiation cost discount wired to Diplomat archetype competence

**Restoration plan:** Dedicated session. Restore 9-archetype pool with randomized
characters and stat distortion on top of current trust mechanics. Keep current
three-advisor names as possible archetype instances, not replacements.

---

## SESSION 7 REMAINING GAPS

These were deferred during Session 7 — design needed before implementation:

**Tech Level tier thresholds**
Passive gain formula is implemented but specific breakpoints and what each
tier unlocks exactly was listed as "needs design before implementation."
Design conversation needed before Claude Code touches this.

**GM inference layer expansion**
Session 7 scope was prototype only (Sadam + energy proposals).
Full architecture (all NPCs, all proposal categories) is Session 8 scope.

**Education system**
Currently a stub/placeholder acting as absorption rate multiplier only.
Full design deferred to Session 8.

**Summit → NPC memory**
NPCs don't yet reference summit declarations in subsequent communiqués.
Deferred to Session 8 when vector stores are added.

---

## NEXT SESSION PRIORITIES

**Design conversation first (this Project):**
1. Tech Level tier thresholds — design breakpoints and specific unlocks
2. Session 8 scope planning — Russia/China full NPC integration,
   regime transitions, scripted branching crises (The Leak)
3. Advisor system restoration planning

**Session 8 implementation:**
- Russia and China full NPC integration (authored personality containers,
  rapport system, negotiation panels)
- Regime transitions: exile sequence, comeback mechanics, leader transitions
- Scripted branching crises (The Leak framework + first implementation)
- Tech Level tier implementation (after design)
- Vector stores for NPC long-term memory (Pinecone/ChromaDB)

---

## HOW TO SUBMIT FIXES TO CLAUDE CODE

**Prompt structure that works:**
```
Read [fix doc].
Confirm the first fix title before proceeding.
For each fix: implement, add console.logs, stop.
Human will verify in browser.
Do not implement any other fix files.
Do not add new features.
```

**What works:** Specific function names and file locations, console.log
verification requirements, pytest for algorithmic fixes.

**What doesn't work:** "Run the game", parse checks as verification,
not specifying file locations, marking complete without verification.

**Stale process pitfall:** Kill all uvicorn processes and clean restart
if routes aren't updating.

---

## FILE REFERENCE

- worldstage_handoff_march2026.md — this file (current)
- worldstage_session7_design.md — full Session 7 feature specs
- WorldStage_Roadmap-2.docx — full roadmap Sessions 1–10
- Snapshots: /snapshots/turn_1_clean.json, turn_8_high_axes.json,
  sanctions_active.json

---

## DESIGN PRINCIPLES TO PRESERVE

- Hard-code consequences, author personalities, seed starting conditions,
  let Claude generate everything in between
- Sophie's choice principle: best crises force binary where both options hurt
- Mechanics create dependency loops — solving immediate problems deepens
  structural vulnerabilities
- Players should feel clever and compromised simultaneously
- Never let Claude decide consequences — it narrates them
- The game is a narrative generator, not a conventional strategy game
- Success measured by quality of emergent stories, not win/lose conditions
- The player never has to grow — staying small is a legitimate playstyle
- Static choices should never dominate negotiation
