# WORLD STAGE — fixes_13
Generated: February 27, 2026
Source: Local testing after fixes_12 deploy

Status: PENDING — implement after Railway deploy of fixes_12

---

## PRIORITY ORDER

1. Deal amount unit parsing regression check (CRITICAL)
2. Tax approval scaling — diminishing returns at low approval (HIGH)
3. Tax approval scaling — 0-15% rates should give approval bonus (HIGH)
4. GDP goes negative at low approval + low stability (HIGH)
5. Democracy lock not enforcing — only tracking, not blocking (HIGH)
6. Regime label conflict on election trigger — regression (HIGH)
7. INCOMING stacking on top of regular communiqué (MEDIUM)
8. Stage directions rendering in all Claude output (MEDIUM)
9. Dismissed advisor duplicating in pool (MEDIUM)
10. INCOMING negotiation should be free (MEDIUM)
11. Counter-offer panel persisting after player declines (LOW)
12. Arabia 100 unlock not firing (MEDIUM)
13. Media/Political axis not affecting intel intercepts (MEDIUM)
14. NPC intercepts should reference axis-level suppression (MEDIUM)
15. FINANCES header showing passive drain only, not net (MEDIUM)
16. Ji-won free intel still not firing at DPRG 60+ (MEDIUM)
17. Debt Infrastructure Deal still showing in Special drawer (BUG)
18. Dismissed advisor duplicates in pool (MEDIUM)
19. Advisor descriptions identical within same archetype (LOW)
20. Advisor elimination consequences (MEDIUM)

---

## FEATURES FOR THIS SESSION

21. Bond financing in Finance drawer (MEDIUM)
22. Diplomat advisor makes negotiations discounted/free (MEDIUM)
23. Political axis level 5+ reduces negotiation cost (MEDIUM)
24. Covert transaction mechanic for Ji-won (MEDIUM)
25. Operations drawer state/personal budget split labeling (SESSION 6 PREP)
26. Black Operations suite expansion at Security 6 (MEDIUM)
27. All four NPC relations 100 unlocks — fully detailed (MEDIUM)
28. Tax rate caps unlocked by Judicial/Political axes (MEDIUM)
29. Domestic spending allocation panel (SESSION 6 CENTERPIECE)
30. GDP growth equation with tech/education factors (DESIGN NOTE)
31. Axis level 10 unlocks — all five axes (DESIGN NOTE)
32. NPC-to-NPC bilateral scores player-facing layer (SESSION 6-7)
33. Special drawer renamed to Finance/Treasury (LOW)

---

## BUG DETAILS

### Fix 1 — Deal amount unit parsing regression check (CRITICAL)

**Context:**
Fix 1 from fixes_12 addressed the $400M → $400B bug.
Verify in this session that the fix held and no
similar unit parsing issues exist for other amounts.

**Test:**
Negotiate a deal where Ji-won or Bill offers an amount
in millions explicitly ("$500 million", "800M").
Verify it registers as $0.5B or $0.8B not $500B/$800B.

If still broken, update NPC counter-offer prompt to
always express amounts in billions with explicit "B"
suffix, eliminating ambiguity at the source.

**Files:** api.py (counter-offer parsing),
  npc_engine.py (counter-offer prompt)

---

### Fix 2 — Tax approval scaling — diminishing returns (HIGH)

**Current behavior:**
"High tax burden: approval -3%" fires as flat
penalty regardless of current approval level.

**Intended behavior:**
Tax approval impact should be diminishing at
low approval — when people are already miserable,
additional extraction doesn't proportionally
increase their anger.

Formula:
  tax_approval_penalty × (current_approval / 100)

At 80% approval: max taxes hit full penalty
At 30% approval: same rate hits ~37% of penalty
At 10% approval: taxes barely register

Makes kleptocracy mechanically distinct — once
approval is burned down, extraction becomes
almost free politically.

**Files:** turn_processor.py (tax burden calc)

---

### Fix 3 — Tax approval at 0-15% rates (HIGH)

**Intended behavior:**
- 0-15% all rates: approval +2% (low taxes popular)
- 16-30%: neutral
- 31-45%: approval -3% (scaled by current approval)
- 46-55%: approval -6%, stability -2%
- 56%+: approval -10%, stability -3%, protests possible

**Additional diplomatic effects:**
All taxes at 0%: EU -2 (failing state optics),
  Bill comments on inability to fund governance
Corporate tax 0%: EU -2, USA -2 (oligarchic signal)
Resource tax 0%: Arabia +1 (pragmatic governance)

**Files:** turn_processor.py (tax burden calc)

---

### Fix 4 — GDP goes negative at low approval + stability (HIGH)

**Intended behavior:**
When approval < 20% AND stability < 30%:
GDP goes negative — capital flight, business
closures, tax base collapsing.

Display as:
  "💵 GDP contraction (approval 0%, stability 0%):
   -$2.1B (capital flight, economic collapse)"

**Files:** turn_processor.py (GDP calc section 13c)

---

### Fix 5 — Democracy lock not enforcing (HIGH)

**Symptom:**
Democracy lock tracks correctly but does not
block any actions during the lock window.

**Intended behavior:**
- Block election rigging and cancellation for
  locked turns (hard block, not advisory)
- If player attempts to cancel election while
  locked: "International observers are present —
  this action is not possible this turn"

**Files:** api.py (election endpoint + choice
  validation), turn_processor.py

---

### Fix 6 — Regime label conflict on election trigger (HIGH)

**Symptom:**
Election consequences block still contains
hardcoded regime_label mutation that fires
before compute_regime_from_axes().

**Fix:**
Remove ALL direct regime_label assignments
from election consequence handler.
Election outcomes affect axes values only.
Search entire codebase for direct
regime_label = "X" assignments and remove
all except the axes computation function.

**Files:** api.py (election endpoint),
  turn_processor.py

---

### Fix 7 — INCOMING stacking on regular communiqué (MEDIUM)

**Intended behavior:**
INCOMING replaces regular communiqué for that
NPC that turn. Style as direct leader-to-leader
private channel, not diplomatic department cable.

Display distinction:
- Regular: "[NPC] — [Department]"
- INCOMING: "[NPC] ⚡ INCOMING — Private Channel"

**Files:** DialoguePanel.jsx or GameScreen.jsx

---

### Fix 8 — Stage directions rendering everywhere (MEDIUM)

**Symptom:**
Asterisk stage directions rendering literally in
INCOMING messages, negotiation dialogue, and
intel intercepts.

**Fix:**
Strip all content matching \*[^*]+\* before
rendering any Claude-generated text.
Apply globally to all display components.

**Files:** DialoguePanel.jsx and all text
  display components

---

### Fix 9 — Dismissed advisor duplicating in pool (MEDIUM)

**Fix:**
dismiss_advisor(): find existing pool record by
advisor ID, update status to "dismissed",
set previously_served = True.
Do not create a new record.

**Files:** advisor_engine.py, api.py

---

### Fix 10 — INCOMING negotiation should be free (MEDIUM)

**Fix:**
When NPC has pending INCOMING contact, set
negotiation_cost = 0 for that NPC that turn.
Display as "Negotiate — Free" with no cost shown.

**Files:** api.py (negotiation cost calc),
  DialoguePanel.jsx

---

### Fix 11 — Counter-offer panel persists after decline (LOW)

**Fix:**
When NPC response contains no new counter-offer
AND player has explicitly declined, close the
counter-offer panel automatically.

**Files:** DialoguePanel.jsx, api.py

---

### Fix 12 — Arabia 100 unlock not firing (MEDIUM)

See Fix 27 for full Arabia 100 unlock details.
The unlock check needs to be added to
turn_processor.py relations milestone detection.

**Files:** turn_processor.py, game_state.py

---

### Fix 13 — Media/Political axis not affecting intel (MEDIUM)

**Intended behavior:**
Media axis obscures financial intelligence:
- Media 0-3: exact figures ("$27B offshore")
- Media 4-6: approximate ("approximately $20-30B")
- Media 7-9: vague ("significant personal holdings")
- Media 10: no financial intel from this source

Political axis obscures regime intel:
- Political 0-3: accurate characterization
- Political 4-6: "opacity around governance"
- Political 7+: Western intel openly frustrated

**Files:** npc_engine.py (intel generation prompt),
  turn_processor.py (intel context injection)

---

### Fix 14 — NPC intercepts not referencing axis suppression (MEDIUM)

**Intended behavior:**
Media axis >= 4: Bill and Marsha reference press
  freedom concerns in intercepts
Political axis >= 4: references to opposition
  suppression, democratic backsliding
Judicial axis >= 4: rule of law deterioration

**Files:** npc_engine.py (intel generation prompt)

---

### Fix 15 — FINANCES header showing passive drain only (MEDIUM)

**Fix:**
FINANCES header should show true net budget change:
  net = -passive_drain + GDP_revenue
        - cabinet_maintenance - sanctions
        - eu_friction + installments

If net positive: "FINANCES +$2.1B"
If net negative: "FINANCES -$3.2B"

**Files:** GameScreen.jsx

---

### Fix 16 — Ji-won free intel not firing at DPRG 60+ (MEDIUM)

**Fix:**
Add console log to find string mismatch:
  "[turn_processor] DPRG INTEL CHECK:
   event_type={x}, dprg_rel={y}"

Align event type string check with actual value.

**Files:** turn_processor.py

---

### Fix 17 — Debt Infrastructure Deal still in Special drawer (BUG)

**Fix:**
Remove Debt Infrastructure Deal card entirely.
Verify Extraction axis level 5 fires one-time
budget injection automatically when first reached.

**Files:** ShadowCabinet.jsx, api.py

---

### Fix 18 — Advisor descriptions identical within archetype (LOW)

**Fix:**
Generate 2-3 description variants per archetype.
Assign randomly on advisor creation.

Example Technocrat variants:
- "Data-driven and methodical. Sees politics
  as an obstacle to optimization."
- "Former IMF consultant. Numbers don't lie,
  but she knows how to make them mislead."
- "Brilliant with spreadsheets. Dangerously
  naive about loyalty."

**Files:** advisor_engine.py

---

### Fix 19 — Advisor names too region-specific (LOW)

**Fix:**
Replace Eastern European-only name pool with
mixed international pool. Europa is fictional —
advisors can plausibly be from anywhere.
Include names from: Eastern European, Western
European, Middle Eastern, East Asian, South Asian,
African, and Latin American pools.

**Files:** advisor_engine.py (name generator)

---

### Fix 20 — Advisor elimination consequences (MEDIUM)

**Intended behavior:**
Eliminating an advisor is a significant act with
real consequences, escalating with each elimination.

First elimination:
- Stability -5%
- Heat +10
- If advisor served 3+ turns: approval -3%
- If advisor had loyalty 70+: world event risk 40%
  "Senior official disappears under mysterious
  circumstances" — EU -5, USA -5, approval -5%

Each subsequent elimination same game (escalating):
- Stability -8%
- Heat +15
- World event risk increases +15% per elimination

Special cases:
- Spymaster eliminated: DPRG +3, Arabia +3, EU -8
- Finance Minister eliminated: EU demands explanation,
  Bill references it next negotiation
- Eliminate while observers present: automatic
  scandal, stability -10%, approval -8%

Flavor text on elimination:
  "The matter was handled discreetly.
   Some matters require discretion."

Historian summary should reference eliminations:
  "Three senior officials were eliminated during
   the regime's tenure."

**Files:** advisor_engine.py, api.py
  (/advisor_action endpoint),
  npc_engine.py (historian summary prompt)

---

## FEATURES

### Fix 21 — Bond financing in Finance drawer (MEDIUM)

**Mechanics:**
Issue $5B bonds: +$5B now, -$2B/turn × 3 turns
Issue $10B bonds: +$10B now, -$4B/turn × 3 turns
EU +2, USA +2 (legitimate financing)
Heat: 0
One issue per game — second issuance: relations -5 all

Display under "DEBT INSTRUMENTS" in Finance drawer.

**Files:** api.py (/issue_bonds), ShadowCabinet.jsx

---

### Fix 22 — Diplomat advisor discounts negotiations (MEDIUM)

**Mechanics:**
- Diplomat at any competence: 50% cost discount
- Diplomat at competence 80+: negotiations free
- Diplomat at loyalty < 40: secretly reports
  negotiating positions to one NPC (random,
  player never told which)

Display: "Negotiate — $0.25B (Diplomat discount)"
or "Negotiate — Free (Diplomat)"

**Files:** api.py, npc_engine.py, DialoguePanel.jsx

---

### Fix 23 — Political axis 5+ reduces negotiation cost (MEDIUM)

**Mechanics:**
- Political 0-4: full cost
- Political 5-7: 25% discount
- Political 8+: 50% discount

Stacks multiplicatively with Diplomat advisor.

**Files:** api.py (negotiation cost calc)

---

### Fix 24 — Ji-won covert transaction mechanic (MEDIUM)

**Unlocks at DPRG 60+**

Covert transactions:
- Zero diplomatic footprint
- No relations changes for any NPC
- No heat generated
- No visible EOT log entry
- No world event trigger
- No cross-NPC penalty

Player gives Ji-won in return: weapons transit
rights, intelligence sharing, or safe passage
for DPRG assets through Europa.

New deal type: COVERT
- Does not appear in EOT log
- Does appear in export/debug log
- Stored in memory for future Ji-won reference
- Breaking a covert deal: Ji-won references it
  in future dialogue, takes no public action

**Files:** api.py, turn_processor.py, game_state.py

---

### Fix 25 — Operations drawer state/personal split labeling (SESSION 6 PREP)

Label each operation as STATE or PERSONAL:
- Propaganda Campaign → STATE
- Domestic Suppression → STATE
- Foreign Influence Op → PERSONAL
- Covert Security → PERSONAL
- Black Operations suite → PERSONAL

No mechanics change — visual prep for Session 6 split.

**Files:** ShadowCabinet.jsx

---

### Fix 26 — Black Operations suite at Security 6 (MEDIUM)

**Replace current weak Black Operation with full suite:**

🖤 Fabricate Crisis ($4B personal)
Target one NPC. Manufacture domestic incident.
Their pressure events suspended 2 turns.
Detection risk 35%.

🖤 Reputation Laundering ($3B personal)
Hire Western PR firm through intermediaries.
Heat -15. One NPC's negative perception softens
next negotiation. No detection risk (technically legal).

🖤 Blackmail Operation ($5B personal)
Extract one-time concession from NPC.
Requires Tier 3 intel on target.
NPC relations -5 permanently (they know).
Detection risk 40%.
One use per NPC per game.

Per-NPC blackmail concessions:
- Bill: sanctions suspended 2 turns
  Flavor: "The photographs from Geneva remain
  private. For now."
- Marsha: conditionality review dropped 2 turns
  Flavor: "The Luxembourg arrangements stay
  between us."
- Sadam: oil price locked at current floor 3 turns
  Flavor: "Riyadh's Tehran communications
  stay unshared."
- Ji-won: reveals one other NPC's actual
  negotiating floor
  Flavor: "Pyongyang's Singapore accounts
  stay off Western radar."

🖤 False Flag ($6B personal)
Blame hostile action on another NPC.
Damages their bilateral NPC-to-NPC score -10.
Detection risk 50%.
If detected: both targeted NPCs -20 relations.

🖤 Political Sabotage ($3B personal)
Manufacture domestic scandal in target NPC's country.
Their pressure events suspended 1 turn.
Their cross-NPC penalty on you reduced 50% next turn.
Requires Tier 2 intel on target.
Detection risk 25%.

All operations:
- One per turn limit (shared)
- Detection fires OPSEC consequence not heat
- DPRG and Arabia approve if detected (+2 each)
- USA and EU condemn if detected (-15 each)

**Files:** api.py, ShadowCabinet.jsx,
  turn_processor.py

---

### Fix 27 — All four NPC 100 unlocks (MEDIUM)

---

#### USA 100 — Full Alliance

**Benefits:**
- Sanctions immunity — USA sanctions cannot fire
- Bill stops making demands, starts offering
- Coup probability -50%
- Military: +10 permanent, no decay
  (American defense contracts + embedded advisors)
- Western market access: GDP baseline +15% permanent
- IMF emergency credit line: one-time $15B
  (repay $18B over 4 turns, no heat, EU approves)
- Intelligence sharing: Bill provides Tier 2 intel
  on any NPC once per turn
- Bill as Marsha backchannel: once per game, ask
  Bill to soften EU conditionality, EU floor +10
  temporarily

**Costs:**
- DPRG relations cap 40 permanently
- Arabia deals trigger automatic congressional
  review warning each turn
- You are now a Western client — the alliance
  has obligations both ways

**One-time message from Bill acknowledging milestone.**

---

#### EU 100 — Full Integration

**Benefits:**
- +5% approval/turn ✅ already implemented
- EU structural funds: +$4B/turn passive income
- Corruption scandal immunity — EU oversight
  protects against domestic scandal exposure
- Marsha as democratic shield: USA sanctions
  capped at Tier 2 maximum while EU 100 holds
- Tech passive gain doubles — Horizon program
  access, full technology transfer
- EU defense umbrella: coup probability -25%
  (half of USA's -50%)
- CIA blackmail events fire at 30% reduced
  probability — observer scrutiny cuts both ways
- European Stability Mechanism credit line:
  one-time $8B (repay $9.5B over 3 turns,
  lighter strings than IMF)

**Costs:**
- Cannot cancel elections while at EU 100 —
  observers are now permanent
- DPRG relations cap 35 permanently
- Arabia premium partnership triggers automatic
  EU conditionality review

**One-time message from Marsha acknowledging milestone.**

---

#### Arabia 100 — Energy Sovereign

**Benefits:**
- Oil locked at $45/bbl floor regardless of
  world events or relations changes
- OPEC insider status — oil spike world events
  don't affect your price (inside the cartel)
- Energy subsidy: +$3B/turn passive income
  "Arabian energy partnership dividend"
- Strategic Reserve Access static option:
  +$8B, no relation penalties
- Military equipment: one-time +15 Military
  (Gulf weapons package, no political strings,
  no ongoing maintenance support)
- Sadam as financial facilitator: $6B/turn
  ceiling on clean Gulf banking transactions
  (not fully invisible like Ji-won but
  harder for West to pierce without court order)

**Costs:**
- USA relations cap 35 permanently
- EU relations cap 40 permanently
- Any fair election with observers: Arabia -5
  (Sadam invested in a stable authoritarian,
  not a reformer)
- If Sadam is ever blackmailed: entire 100
  unlock collapses, relations drop to 60,
  floor price disappears immediately

**Flavor:**
Arabia 100 is the most financially rewarding
patron but the most politically isolating.
Rich, cheap oil, equipped military — no Western
allies, population knows you sold to Riyadh,
entire financial system runs through Gulf
networks Sadam can close at will.
The dependency loop just changed direction.

**One-time message from Sadam acknowledging milestone.**

---

#### DPRG 100 — Shadow Patron

Note: Ji-won as intelligence broker unlocks
at DPRG 80+, not 100. Exile escape route
is already available via INCOMING dialogue.
DPRG 100 is distinctly more powerful.

**Benefits:**
- Covert transaction ceiling increases to $8B
- Personal wealth hosted in DPRG sovereign
  accounts — completely invisible to Western
  auditors, not just hard to trace
- One-time coup deterrence: if coup fires while
  at DPRG 100, it fails automatically once
  (DPRG deploys military assets)
- Double agent mechanic: Ji-won feeds you
  disinformation to pass to Bill and Marsha.
  USA and EU relations don't decay naturally
  for 3 turns — they think you're their asset.
  If discovered: both relations -25, DPRG +10

**Costs:**
- USA relations cap 30 permanently
- EU relations cap 30 permanently
- Arabia grows suspicious: Arabia relations
  decay -2/turn while DPRG 100 holds
- You are fully in the Eastern orbit

**One-time message from Ji-won acknowledging milestone.**
  (Characteristically understated and menacing)

---

### Fix 28 — Tax rate caps unlocked by axes (MEDIUM)

**Base caps (always available):**
- Income: 0-50%
- Corporate: 0-40%
- Resource: 0-60%

**Judicial 5+ unlocks:**
- Resource cap rises to 75%
- 61-75% resource: stability -3%/turn additional,
  protests possible

**Political 7+ unlocks:**
- Income cap rises to 65%
- 51-65% income: approval -5%/turn additional,
  capital flight warning in EOT

**Judicial 8+ AND Political 8+ together unlock:**
- All caps rise to 85%
- "Emergency economic measures" world event fires
- EU -10, USA -8, Arabia +2
- Stability -5% immediate

**85-100% permanently locked** — that range is
outright confiscation/nationalization territory,
a different mechanic entirely for Session 7+.

**Files:** api.py (/set_tax_rates validation),
  ShadowCabinet.jsx (slider max values),
  turn_processor.py (cap enforcement)

---

## DESIGN NOTES — SESSION 6 SCOPE

**Domestic spending allocation panel**
Session 6 centerpiece. Player directs national
budget across categories each turn:
  Public services → mass approval +, stability +
  Military spending → military strength +
  Infrastructure → economy efficiency +, slow burn
  Intelligence apparatus → tier maintenance
  Education → GDP growth rate + (long term)

Tax rates = revenue side.
Spending allocation = expenditure side.
Together they form a real fiscal management loop.

**GDP growth equation**
  GDP growth = base_rate
    + tech_level × 0.3%
    + education_spending × 0.2%
    + infrastructure_investment × 0.15%
    - tax_burden_modifier
    - sanctions_drag
    - stability_penalty
    - extraction_rate_penalty

High Extraction axis hollows out GDP growth
over time — the structural vulnerability loop.

**Axis level 10 unlocks**
Security 10: full coup immunity, passive Tier 3 intel
Media 10: total info control, approval floor 25%, EU cap 40
Judicial 10: corruption scandals impossible, USA cap 50
Political 10: elections ceremonial, stability floor 20%
Extraction 10: sovereign wealth fund, GDP permanently reduced

Pattern: high axis levels unlock power but
permanently cap certain NPC relationships.

**NPC-to-NPC bilateral player layer**
6 bilateral scores already tracked silently.
Session 6: intel hints reveal tensions.
Session 7: GM inference uses bilaterals.
Foreign Influence Ops move bilateral scores.
Summit mode makes tensions visible in real time.

**Special drawer rename**
Rename to FINANCE or TREASURY throughout.
"Special" was always a placeholder.

---

## CONFIRMED WORKING — from latest test runs

- Historian summary on game over ✅
  ("Ji-won arranged the plane. You are drinking
  wine somewhere. Europa is not.")
- CIA blackmail at high personal wealth ✅
- Democracy lock tracking ✅ (enforcement missing)
- Tax revenue calculating with rates ✅
- INCOMING from Ji-won with real generated dialogue ✅
- Intel intercepts showing NPC reactions to wealth ✅
- NPC cross-awareness (Ji-won knows Sadam's offer) ✅
- Election watchers firing correctly ✅
- Western Bloc Joint Pressure cascade ✅
- CIA blackmail bringing stability to 0 ✅
- Arabia 100 reached (unlock missing but milestone hit ✅)
- Negotiation quality high across all four NPCs ✅
