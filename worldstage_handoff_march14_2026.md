# WORLD STAGE — SESSION HANDOFF
Generated: March 14, 2026

---

## WHAT THE GAME IS

Geopolitical simulation. Player leads fictional nation of Europa.
Not win/lose — a narrative generator for political biographies.
Theme: loneliness of power. Players feel clever and compromised simultaneously.

**Stack:** FastAPI backend (Railway) + React frontend (Vercel).
**Deployed:** world-stage.vercel.app. GitHub auto-deploy.
**Auth:** Clerk dev instance. Auth optional — guests play without persistence.
**Cheat panel:** http://localhost:5173?cheat=true (TEST button bottom-right)

**Backend files:** npc_engine.py, turn_processor.py, game_state.py, api.py,
gm_engine.py, advisor_engine.py
**Frontend files:** GameScreen.jsx, DashboardLayout.jsx, LeftSidebar.jsx,
RightSidebar.jsx, NpcCard.jsx, AdvisorPanel.jsx, BriefingSummaryCard.jsx,
DomesticTab.jsx, PromiseTracker.jsx, SummitCommitmentTracker.jsx,
SummitModal.jsx, BackchannelModal.jsx, ShadowCabinet.jsx, ExileDashboard.jsx,
LeakCrisisModal.jsx

**NPCs:** Bill Hartwell (USA), Sadam (Arabia), Marsha (EU Commission),
Ji-won (DPRG), Nikolai Volkov (Russia), Wei Jianming (China).

---

## SESSIONS 1–8 COMPLETE

All core systems through Session 8 implemented and verified.

### Session 8 Status

| Sub-session | Feature | Status |
|-------------|---------|--------|
| 8A | Russia/China full NPC integration | ✅ Verified |
| 8B | Education system | ✅ Verified |
| 8C | Exile sequence | ✅ Verified |
| 8D | The Leak scripted crisis | ⚠️ Built, modal/endpoint verified, EOD trigger wiring unverified — fix during 9A when EOD loop is touched |
| 8E | UI improvements | ✅ Verified. Cleanup: remove empty Finance tab from ShadowCabinet.jsx |
| 8F | GM inference (Volkov + Wei) | ✅ Verified |

### Key Confirmed Working (post Session 8)
- Three-panel dashboard, day/era system, historian on demand ✅
- Advisor system (Finance Minister, Technocrat, Diplomat pool) ✅
- Russia/China passive cards with deal-based drift ✅
- Backchannel modal with detection risk ✅
- UN Summit group chat (6 NPCs, plain text, correct reaction types) ✅
- Education system (level display, decay warning, brain drain warning) ✅
- Exile sequence (dashboard, actions, NPC dialogue, destination routing) ✅
- GM inference layer (Volkov/Wei freeform proposals) ✅
- DEV panel accessible via ?cheat=true ✅
- Budget allocation dollar amounts on tags ✅
- Text inputs alongside spending sliders ✅

---

## KNOWN BUGS / PENDING ITEMS

**8D Leak trigger not firing:**
`_check_the_leak_trigger()` confirmed called at line 1959 in turn_processor.py
but `[leak] CHECK` log never appears. Function is wired but not producing output.
Likely a stale process or file save issue. Fix during 9A EOD loop work.

**Finance tab in Shadow Cabinet:**
Empty placeholder ("Intelligence network status."). Remove the tab entirely
from ShadowCabinet.jsx. Small cleanup, send to Claude Code before 9A.

**Backchannel conversation looping:**
Haiku loses thread after ~6 exchanges. Logged, not yet fixed.
File: npc_engine.py → generate_backchannel_response()

**FIX C Ledger Mismatch warning:**
`[api] ⚠️ FIX C LEDGER MISMATCH` appearing in some runs. Logged, not blocking.

---

## NEXT SESSION: SESSION 9

### 9A — Comeback Mechanics

Return from exile. The exile sequence ships in 8C; comeback arrives in 9A.

**Return conditions by collapse type:**
- Coup: need military faction support
- Revolution: need mass movement backing
- Debt crisis: need external creditor
- Voted-out: cleanest path, most viable return

**NPC return prices:**
- Bill: Western alignment commitment
- Sadam: energy partnership restored
- Marsha: reform commitments in writing
- Ji-won: isolation from West
- Volkov: energy exclusivity
- Wei: infrastructure partnership

**Restoration regime label:** Applied on return, persists until new identity
established through subsequent choices.

**Successor GM call:** Replace hardcoded stub events in 8C with live GM call
that generates successor government actions dynamically based on game state.

**Exile conversation depth:** Response depth scales with relationship strength:
- Backer NPC: full back-and-forth (invested in your return)
- High relations + no backing: one response, door open
- Low relations/hostile: silence or cold single response
- DPRG/Volkov at low relations: may not respond at all

**Other 9A items:**
- Comeback starts with reduced relations, depleted wealth, NPCs referencing
  previous regime
- "Comeback mechanics coming in Session 9" placeholder → replace with actual UI

### 9B — Narrative Engine

Full political biography generator.

**Biography sections:** Rise / Fall / Exile / Restoration / Legacy

**Reputation axes (hidden, revealed at end):**
- Statesman vs. Kleptocrat
- Reformer vs. Authoritarian
- Western vs. Eastern alignment

**Legacy scoring:**
- Economic stewardship
- Institutional integrity
- Geopolitical legacy
- Personal enrichment
- Longevity in power
- Quality of exile if applicable

**Historical verdict:** Claude in historian voice. References actual choices.
Acknowledges contradictions. One voice, not a summary.

**Regime Survival Index:** Consecutive turns across all eras. Leaderboard.

**Shareable biography cards:** Visual summary, shareable outside game.

---

## DESIGN WORK COMPLETED THIS SESSION (not yet implemented)

A major design conversation happened today covering systems for Sessions 9.5
and 10. Full spec in: `/mnt/user-data/outputs/worldstage_axes_redesign.md`

### Axes Redesign (Session 9.5 — after 9A and 9B)

**Core principle:** Axes = commitment-based spending tiers, not lump-sum
purchases. The tier you sustain IS your axis level.

**Tier counts (expanded from current):**
- Military: 0–10 (GDP gates at Tier 7+, Tier 9+)
- Intelligence (national): 0–9
- Diplomatic Corps: 0–10 (new axis)
- Education: 0–10 (expanded from 0–3)
- Social Infrastructure: 0–10 (expanded from 0–5)
- Resource Development: 0–10
- Political: 0–10 (actions-based, not spending)
- Tech Level: 0–100+ continuous (unchanged)
- Militia/Shadow Intel: 0–3 (personal wealth, Shadow Cabinet)

**GDP gates:** Upper tiers (7+) require GDP thresholds. Cannot build
world-class institutions without a world-class economy.

**Prerequisite webs (soft, not hard blocks):**
- Military Tier 5+ requires Tech Tier 2+, Education Level 1+
- Intel Tier 4+ requires Tech Tier 1+
- Diplomatic Tier 5+ requires Education Level 1+
- Max extraction requires Education Level 2+
- Judicial capture requires Political axis 3+ AND stability 40+

**Two-component stability:**
- Legitimacy stability: from approval, institutions, education, clean elections
- Coercion stability: from military, brigades, suppression, patronage
- Displayed number is sum; composition determines failure mode
- Coercion stability fails suddenly; legitimacy stability fails slowly
- Player sees hints in historian voice (not raw numbers)

**Military/Militia split:**
- Formal military (capability, potentially disloyal)
- Militia/Loyalty Brigades (loyal, less capable, personal wealth)
- Merger mechanic at Soft Authoritarianism+: integrate brigade into
  military command. Irreversible. Loses deniability, gains coup protection.

**Loyal Generals / Loyal Intel Chief:**
- Install loyal-but-incompetent leadership
- Coup probability drops; capability cap reduces; intercept quality degrades
- Reversible but costly

**Political axis as gate:** Regime type label becomes prescriptive for
certain purchases, not just descriptive.

### Diplomatic Effectiveness System (Session 9.5)

Three scores (not axes):

**Diplomatic Capacity** (spendable, 0–4 tiers, daily commitment):
- Tier 0: no corps; Tier 4: elite corps, kompromat surfaces
- Education reduces costs at higher tiers

**Soft Power** (derived, behavior-based, 0–100):
```
soft_power = (
  gdp_component × 0.28
  + education_component × 0.18
  + democratic_track_record × 0.15
  + dependency_network × 0.14
  + legitimacy_stability × 0.10
  + tech_level_normalized × 0.08
  + avg_diplomatic_standing × 0.04
  + avg_npc_relations × 0.03
)
```
GDP uses growth trajectory (gdp_normalized × 0.70 + gdp_trend × 0.30).

**Reliability Score** (derived, track-record-based, 0–100):
```
reliability_raw = (
  public_commitments_honored_pct × 0.40
  + backchannel_honored_pct × 0.30
  + summit_credibility_normalized × 0.20
  + recency_bonus × 0.10
)
```
Diplomatic capacity softens reliability penalties: each tier reduces
per-incident penalty by 4% (Tier 4 = 16% reduction max).
Reliability has a floor = diplomatic_capacity_tier × 3.

**Diplomatic Standing** (per-NPC, 0–100, moves slowly):
- Distinct from relation score
- Changes max ±5/day
- Hits zero → ambassador recall fires automatically
- At zero: diplomatic spending has no effect on that NPC

**Ambassador Recall mechanic:**
- Fires when standing drops below threshold or NPC chooses to escalate
- While recalled: backchannel unavailable, formal contact signals backing down
- Debrief quality scales with diplomatic capacity tier
- Options after debrief: send back, cold-call, wait, use intermediary, escalate

**Diplomatic power multipliers:**
- Military strength: reduces severity of pressure events from lower-tier NPCs
- GDP weight: reduces relation decay rate after incidents with EU/USA
- Dependency network: client states absorb bad behavior, lobby on your behalf
- Kompromat: active dependency, controlled anger, catastrophic if burned

**Diplomatic dampening formula:**
```
effective_fallout = base_fallout × (1 - diplomatic_dampening)

diplomatic_dampening = (
  standing_with_affected_NPC × 0.50
  + avg_standing_other_NPCs × 0.30
  + reliability_score_normalized × 0.20
) / 100

cap: 0.40 (diplomacy softens, never eliminates)
```
NPC-specific weights: Marsha/Bill respond more to reliability;
Sadam/Volkov respond more to direct standing; Ji-won responds to
capabilities, not reputation.

### Tax and Budget System (Session 9.5)

**Commitment model:** No allocation sliders. Each capability tier costs
a fixed $/day to maintain. Budget pie = read-out of commitments vs. revenue.

**Tax formula:**
```
daily_tax_revenue = income_revenue + corporate_revenue + resource_revenue

laffer_modifier: 0-25%=1.0, 25-45% decays, 45-60% decays faster, 60%+ severe

tax_approval_penalty × (approval/100)  ← diminishing at low approval
```

**Skim as visible slider:** Right there next to tax rate. Heat generation
nonlinear above 15%. Detection threshold drops at Education 2+, free press.

**Resource Policy toggle:** State-Led vs. Private Sector per tier.
State-Led: revenue to budget at resource_rate (gross).
Private Sector: revenue at profits only (×0.45), development speed ×1.4.

**Bond market — dynamic rates:**
```
bond_rate = 2.5% base
  + deficit_trend (0–3.0% capped at 10 days)
  + regime_label_premium (0–1.5%)
  + suppression_premium (0–0.6%)
  + election_premium (-0.2% to +0.4%)
  + debt_load (+0.15% per $10B)
  - access_modifier (market-dependent)
  - reliability_discount (-0.3% to +0.4%)

floor: 1.0%, ceiling: 12.0% (IMC intervenes at ceiling)
```
Market access tiers: International Markets (always), NPC bilateral
(supplementary, relationship-gated), IMC (institutional backstop).

**International lending at UN/Regional Council:**
- Player can table loan requests publicly
- NPCs lend in character (Marsha=reform conditions, Volkov=hidden conditions,
  Wei=dependency terms, Sadam=transactional, Bill=alignment conditions)
- Coalition lending: high usa_eu bilateral → joint package, both conditions
- Player can bail out other countries → client state mechanic born here

### The Powerful Authoritarian Path (Session 10)

Hardest path in the game. Requires maintaining international legitimacy
while being domestically authoritarian. Historical model: Saudi Arabia, UAE.

**International Legitimacy Score (hidden):**
Built by: strategic indispensability, stability as export, selective
international participation, strategic restraint, consistent summit presence.

**Failure mode:** Miscalculation. Mistakes tolerance for acceptance.
When calculus tips, it tips everywhere simultaneously.
Historian verdict: "He mistook tolerance for acceptance, and found out
the difference too late."

**Bill's role on this path:** Calculating whether you're manageable.
Transition from "strategic partner" to "problem to be solved" is
the most dangerous moment.

---

## OPEN QUESTIONS (carry to next design conversation)

1. **Diplomatic axis implementation timing:** Session 9.5 or Session 10?
2. **Militia as axis vs. renamed brigade:** Keep tier 1–3 discrete purchases
   or make it a continuous axis? Recommendation: keep discrete, add Militia
   stat that merger mechanic affects.
3. **Soft power/reliability visibility:** Hidden (inferred from NPC behavior)
   or shown as scores? Lean toward hidden.
4. **Kompromat acquisition mechanic:** Needs design — how is it obtained,
   how is it used, burn risk. Design before Session 9.5.
5. **The Leak trigger:** Fix EOD wiring during 9A.
6. **Finance tab removal:** Quick cleanup, send to Claude Code before 9A.

---

## HOW TO SUBMIT FIXES TO CLAUDE CODE

**Prompt structure that works:**
```
Read [fix doc or describe task].
Confirm the first fix/task title before proceeding.
Implement, add console.logs, stop.
Human will verify in browser.
Do not add new features.
Do not implement anything not listed.
```

**What works:** Specific function names and file locations, console.log
verification, pytest for algorithmic fixes.

**What doesn't work:** "Run the game", parse checks, not specifying files,
marking complete without verification.

**Stale process pitfall:** Kill uvicorn and clean restart if routes
aren't updating. Backend logs = Railway/uvicorn terminal. Frontend
logs = browser console. They are different.

**deal_total_value is canonical:** All consequence handlers must use
deal_total_value (upfront + installments), not deal_budget (upfront only).

---

## FILE REFERENCE

- worldstage_handoff_march2026.md — this file
- worldstage_axes_redesign.md — full axes/economy/diplomacy redesign spec
- worldstage_status_log.md — running bug/fix tracking
- worldstage_session7_design.md — Session 7 feature specs
- worldstage_techleveltiers.md — Tech Level tier spec (implemented)
- worldstage_8b_claude_code_prompt.md — Education system (implemented)
- WorldStage_Roadmap-2.docx — full roadmap Sessions 1–10

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
- Funding source IS the moral choice (national budget vs. personal skim
  for black ops signals democratic vs. authoritarian intent)
- The democratic path compounds outward; the authoritarian path compounds
  inward — both should feel coherent, neither obviously dominant
