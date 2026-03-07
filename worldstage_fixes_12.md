# WORLD STAGE — fixes_12
Generated: February 26, 2026
Source: Local testing after fixes_11 deploy

Status: PENDING — implement after Railway deploy of fixes_11

---

## PRIORITY ORDER

1. Deal amount unit parsing — 400M reading as $400B (CRITICAL)
2. Tax levers not affecting GDP revenue (HIGH)
3. Regime label conflict on election trigger (HIGH)
4. Replace per-turn epitaph with end-game historian summary (HIGH)
5. Cabinet drawer too narrow (MEDIUM)
6. Dismiss vs eliminate — dismissed advisors gone permanently (MEDIUM)
7. Advisor pool missing archetypes at Managed Democracy (MEDIUM)
8. Intel button locked state (LOW)
9. Intel gathering deducting from personal wealth (LOW)

---

## BUG DETAILS

### Fix 1 — Deal amount unit parsing (CRITICAL)

**Symptom:**
Ji-won counter-offer: "four hundred million, channelled
through intermediary accounts, structured across the
next two turns"

Deal registered as $400B total, paying $200B/turn.
Budget jumped from $35B to $218B in one turn.

**Root cause:**
The counter-offer mechanics parser extracts the numeric
amount from NPC text but does not correctly apply
the M/B multiplier. "400M" or "400 million" is being
stored as 400 (billions) instead of 0.4 (billions).

**Fix:**
In wherever deal amounts are parsed from NPC
counter-offer structured output:
- If amount unit is "M", "million", or "mil" →
  divide by 1000 to convert to billions
- If amount unit is "B", "billion" → use as-is
- If unit is ambiguous → default to billions
  (NPCs should always specify)

Additionally add a sanity cap as a safety net:
- Single deal payment cannot exceed $20B
- Installment payment cannot exceed $10B per turn
- If parsed amount exceeds cap, return validation
  error and log: "[api] DEAL AMOUNT CAP EXCEEDED:
  raw={x}, parsed={y} — rejecting"
- NPC should be prompted to re-offer within range

Also update NPC counter-offer prompt to always
express amounts in billions with explicit "B"
suffix to reduce ambiguity. Example:
"$0.4B over two turns" not "400 million".

**Files:** api.py (counter-offer parsing),
  npc_engine.py (counter-offer prompt instructions)

---

### Fix 2 — Tax levers not affecting GDP revenue (HIGH)

**Symptom:**
Run with income 50%, corporate 40%, resource 60%
set on Turn 1. GDP revenue line shows $4.4B on
Turn 1, $4.4B on Turn 2. No change despite
maximum tax rates.

Run with all taxes at 0%: GDP revenue still
shows same values.

Tax burden approval penalty fires correctly
("High tax burden: approval -3%") but the
revenue calculation ignores tax rates entirely.

**Root cause:**
GDP revenue formula in turn_processor.py section
13c is likely using hardcoded revenue values or
not reading tax_rates from game state. The tax
levers in the Special drawer write to
game_state.tax_rates correctly (upgrade log
confirms "Tax rates set: income 50%...") but
the revenue calculation is not consuming them.

**Fix:**
In turn_processor.py GDP revenue calculation:
- Read game_state.tax_rates for income, corporate,
  resource rates
- Apply as multipliers to their respective
  revenue base values:
  - Income tax revenue = gdp_base × income_rate
  - Corporate tax revenue = gdp_base × corp_rate × 0.6
  - Resource tax revenue = resource_base × resource_rate
- Total tax revenue replaces the current flat
  GDP revenue figure
- Add console log:
  "[turn_processor] TAX REVENUE — income: $XB
  (rate X%), corporate: $XB (rate X%),
  resource: $XB (rate X%), total: $XB"

This should create meaningful tradeoffs —
maxing all taxes generates more revenue but
tanks approval, while cutting taxes is popular
but starves the budget.

**Files:** turn_processor.py (section 13c GDP calc),
  verify game_state.py tax_rates field is
  persisting correctly across turns

---

### Fix 3 — Regime label conflict on election trigger (HIGH)

**Symptom:**
fixes_11 Fix 1 disabled the skim-based regime
shift triggers. But election consequences still
contain their own regime shift logic:

Turn 4 [ELECTION] rigged consequences:
  "regime shift right: Soft Authoritarianism
   → Patronage State"

EOT then shows:
  "Regime reclassified (cabinet axes):
   Patronage State → Soft Authoritarianism"

Same dual conflict as before — different code path.
The election consequence block has its own hardcoded
regime shift that bypasses compute_regime_from_axes().

**Root cause:**
Election consequence handler in api.py or
turn_processor.py directly mutates
game_state.regime_label based on election type,
separate from the axes-based computation.

**Fix:**
Remove direct regime_label mutation from election
consequence handler. Election outcomes should
instead affect axes values (canceled election →
Security axis +2, Political axis +2) and let
compute_regime_from_axes() determine the label
at EOT as it does for everything else.

The election consequence log line should read:
  "⚠️ Election outcome shifts regime axes
   (Security +2, Political +2)"
Not a direct regime label change.

**Verify:**
No hardcoded regime_label = "X" assignments
anywhere except compute_regime_from_axes().
Search codebase for direct regime_label
assignments and remove all except the
axes computation.

**Files:** api.py (election endpoint),
  turn_processor.py (election consequence block)

---

### Fix 4 — Replace per-turn epitaph with end-game historian summary (HIGH)

**Symptom:**
Per-turn epitaph repeats on consecutive turns
with similar game state. Has survived 8 fix
sessions without resolution. Fundamental
architecture problem — single-turn context
is insufficient for varied output when
game state doesn't change much.

**Decision:**
Remove per-turn epitaph entirely.
Replace with single historian summary
generated at game end.

**Remove:**
- Per-turn epitaph generation call in npc_engine.py
- Epitaph display at bottom of turn results UI
- Angle rotation system
- Similarity check and fallback template system
- All related game_state fields (recent_epitaphs,
  last_epitaph_angle, etc.)

**Add:**
End-game historian summary generated when
game status flips to any terminal state
(bankruptcy, collapse, completed, exile).

The summary has access to full turn history
and should cover:
- How the regime began and what the opening
  choices revealed about the leader's character
- The key turning point — the moment the
  player's strategic identity became clear
- How it ended and what that says about
  the whole arc
- One-sentence verdict in textbook style

Display on the ending/legacy screen, styled
in the same historian voice, after the
mechanical legacy verdict.

Prompt structure for generation:
- Pass full turn history array
- Pass final game state (relations, wealth,
  regime label, stability, approval)
- Pass all deals made and broken
- Pass election choices made
- Pass domestic actions taken
- Instruct: write 3-4 sentences in the voice
  of a historian writing 20 years after
  these events. Do not summarize mechanically.
  Find the through-line. End with a verdict.

**Files:** npc_engine.py (remove epitaph generation,
  add generate_historian_summary()),
  turn_processor.py (remove epitaph call from EOT),
  GameScreen.jsx or EndingScreen.jsx (remove
  per-turn display, add to ending screen),
  game_state.py (remove epitaph-related fields)

---

### Fix 5 — Cabinet drawer too narrow (MEDIUM)

**Symptom:**
Cabinet drawer requires horizontal scrolling
to see axis track bars, investment controls,
and content in the Infrastructure and
Operations drawers. Content is wider than
the drawer panel.

**Fix:**
Increase Cabinet drawer width. Target:
- Desktop: minimum 480px, preferred 520px
- The axis track bars (10 segments) need
  enough width to be readable without
  squishing
- Investment buttons (+Invest / -Defund)
  should sit comfortably on one line with
  the cost label
- No horizontal scroll on any drawer tab
- If viewport is narrow, drawer can overlay
  the main content area rather than
  sitting beside it

Also verify the drawer doesn't cause
layout reflow on the main communiqués
panel when it opens.

**Files:** index.css (Cabinet drawer width,
  axis track sizing), ShadowCabinet.jsx

---

### Fix 6 — Dismiss vs eliminate — dismissed advisors gone permanently (MEDIUM)

**Symptom:**
Dismissed an advisor — they disappeared from
the pool entirely. No way to rehire.
Dismiss and eliminate are behaving identically.

**Intended behavior:**
- Dismiss: advisor returns to hiring pool,
  marked "Previously served", rehirable
  next turn. No cost.
- Eliminate: permanent removal, never
  returns to pool. Costs personal wealth.
  Used for dangerously disloyal advisors.

**Fix:**
In advisor_engine.py:
- dismiss_advisor(): set advisor.status =
  "dismissed", return to pool with
  previously_served = True flag
- eliminate_advisor(): set advisor.status =
  "eliminated", remove from pool permanently,
  deduct wealth cost

In AdvisorPanel.jsx:
- Show dismissed advisors in pool with
  "Previously served" badge
- Separate "Dismiss" and "Eliminate" buttons
  with distinct visual treatment — Eliminate
  should be red and require confirmation

**Files:** advisor_engine.py, api.py
  (dismiss/eliminate endpoints),
  AdvisorPanel.jsx

---

### Fix 7 — Advisor pool missing archetypes at Managed Democracy (MEDIUM)

**Symptom:**
Only 4 advisor options visible at Managed
Democracy regime level. Design specifies
5+ available archetypes at starting conditions.

Intelligence Chief notably absent — this is
the most important advisor archetype and
should be available from the start, gated
by Security axis level not regime type.

**Fix:**
Audit advisor_engine.py capacity gates:
- List all 7 base archetypes and their
  current unlock conditions
- Intelligence Chief: change gate from
  regime threshold to Security axis >= 3
- Identify which 5th archetype is missing
  at Managed Democracy and fix its gate
- Pool should always show minimum 5
  candidates at any regime level

Add console log on pool generation:
  "[advisor_engine] POOL: {n} candidates
  generated for regime {regime},
  security {level}"

**Files:** advisor_engine.py

---

### Fix 8 — Intel button locked state (LOW)

**Symptom:**
Get Intel button is hidden entirely until
Security axis reaches level 3. New players
don't know the feature exists or what
unlocks it.

**Fix:**
Show Get Intel button on all NPC communiqué
cards from turn 1, grayed out with lock
icon if Security axis < 3.

Locked state display:
  🔒 Get Intel
  Requires Security level 3
  (Cabinet → Infrastructure → Security)

Clicking locked button shows same message
rather than doing nothing.

At Security >= 3 button becomes active
as currently implemented.

**Files:** DialoguePanel.jsx or GameScreen.jsx
  (wherever intel button renders)

---

### Fix 9 — Intel gathering deducting from personal wealth (LOW)

**Symptom:**
Get Intel deducts from personal wealth
(corruption budget) instead of national budget.

**Intended behavior per roadmap:**
National intelligence is a legitimate state
function funded from national budget.
Cost tiers by relation level:
  Relations 60+: $0.5B from national budget
  Relations 30-59: $1.0B from national budget
  Relations 0-29: $1.5B from national budget

Personal wealth funds covert operations
(Tier 3 shadow apparatus) — not standard
NPC intelligence gathering.

**Fix:**
In api.py /get_intel endpoint:
- Change deduction from game_state.personal_wealth
  to game_state.budget
- Verify cost tier calculation uses relation
  level correctly
- Update skim panel / budget display to
  show intel cost as national expense

**Files:** api.py (/get_intel endpoint)

---

## DESIGN NOTES (not bugs — Session 6 scope)

**High-level axis rewards**
Levels 7-10 on each axis have unlock indicators
but limited visible mechanical payoff currently.
These are intended to unlock the domestic action
suite (State Media Takeover, Judicial Capture,
Suppress Independent Press, etc.) which are
Session 6 features. No fix needed — just needs
Session 6 implementation to make the higher
levels feel meaningful.

**Arabia static choice dominance**
Arabia static deal (+$12B) remains vastly
superior to negotiated Sadam ceiling (~$4.8B).
Players have no reason to negotiate when static
is obviously better. Carried forward from
fixes_11 open items. Session 7 GM inference
layer is the full fix — Sadam should be able
to offer larger negotiated deals that reflect
his actual willingness formula.

---

## CONFIRMED WORKING — from latest test runs

- Western Bloc Joint Pressure cascade ✅
- USA Sanctions Tier 4 full penalty stack ✅
- Arabia oil tier improvements with relations ✅
- Cabinet maintenance costs ✅
- Election consequences (stability, approval,
  relations effects) ✅
- INCOMING contacts queuing ✅
- Deal broken detection ✅
- Cross-NPC penalties ✅
- Tax burden approval penalty ✅
- Tech passive acquisition ✅
- Skim panel EOT projection ✅
- One operation per turn limit ✅
