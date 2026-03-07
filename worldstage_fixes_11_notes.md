# WORLD STAGE — fixes_11 NOTES
Generated: February 26, 2026
Source: Session 5 browser testing — two full runs

Status: PENDING — implement after Session 5 push to Railway

---

## PRIORITY ORDER

1. Regime label dual system conflict (HIGH — fires every turn)
2. Brigade spam no per-turn limit (HIGH — game-breaking)
3. Advisor panel not accessible (HIGH — major feature invisible)
4. Epitaph repeat on consecutive same-context turns (HIGH)
5. ⚡ INCOMING not generating contact dialogue (MEDIUM)
6. Deal history empty despite accepted deals (MEDIUM)
7. Security axis level 3 missing intel unlock (MEDIUM)
8. Skim panel missing full EOT projection (MEDIUM-HIGH)
9. Verbose upgrade log (MEDIUM)
10. Shadow Cabinet rename + always accessible (MEDIUM)
11. DPRG intel sharing not generating intel (MEDIUM)
12. Bill negotiation posture ignoring canceled election (MEDIUM)

---

## BUG DETAILS

### 1. Regime label dual system conflict (HIGH)

**Symptom:**
Every turn shows two contradicting regime shift lines:
  "⚠️ Regime shift: 'Managed Democracy' → 'Soft Authoritarianism'
   — Trigger: 2 consecutive large skims"
  "🗄️ Regime reclassified (cabinet axes): Soft Authoritarianism
   → Managed Democracy"

The old skim-based trigger and the new axes-based calculation
fight each other every single turn. The axes system wins
(correct) but the old trigger fires first and logs a false
regime shift message before being overridden.

**Root cause:**
Two separate regime calculation paths still active:
- Old: turn_processor.py skim threshold triggers
- New: compute_regime_from_axes() in EOT section 13+

**Fix:**
Disable the old skim-based regime shift triggers entirely.
Regime label must come exclusively from compute_regime_from_axes().
The skim thresholds can still affect axes values (they do),
but the regime label itself should only change when
compute_regime_from_axes() returns a different value.

Search turn_processor.py for "Regime shift" log lines from
the old system and remove or disable them.

**Verify:**
No "⚠️ Regime shift" line in EOT. Only
"🗄️ Regime reclassified" if axes actually changed label.
If axes haven't changed, no regime line at all.

**File:** turn_processor.py

---

### 2. Brigade spam — no per-turn limit (HIGH)

**Symptom:**
Turn 4 export shows 6 consecutive Foreign Influence Ops
targeting USA in a single turn:
  "🕵️ Foreign influence op targeting USA: +5 relations, -$1.5B"
  (repeated 6 times)

No per-turn limit enforced. Player can deploy unlimited
operations in a single turn draining personal wealth
and stacking relation bonuses indefinitely.

**Root cause:**
The Operations drawer has no deployment counter or
cooldown check. brigade_operations_this_turn field
was added to game_state in Session 5 but the gating
logic was not implemented in the endpoint.

**Fix:**
In the /brigade_operation endpoint (api.py):
- Check game_state.brigade_operations_this_turn
- If already >= 1 for any operation type, return 400
  "Only one operation can be deployed per turn"
- Reset brigade_operations_this_turn to {} at start
  of each new turn (in turn_processor.py turn advance)

In ShadowCabinet.jsx Operations drawer:
- After any deployment, disable all Deploy buttons
  for the rest of that turn
- Show "Operation deployed this turn" message

**Files:** api.py, turn_processor.py, ShadowCabinet.jsx

---

### 3. Advisor panel not accessible (HIGH)

**Symptom:**
AdvisorPanel.jsx was created and wired into GameScreen.jsx
but there is no visible button or entry point to open it
in the UI. Two full runs completed with no advisor hired.

**Root cause:**
The panel likely renders but has no trigger button, or
the button is hidden behind another element. The
Shadow Cabinet doesn't have an Advisors section
linking to it.

**Fix:**
Add ADVISORS as a fourth drawer tab in the Shadow Cabinet
alongside INFRASTRUCTURE, OPERATIONS, SPECIAL.
Advisors are part of state management — this is the
cleanest UX placement.

Also verify the /advisor/pool endpoint returns candidates
correctly and the hire flow works end-to-end.

**Files:** ShadowCabinet.jsx, AdvisorPanel.jsx, GameScreen.jsx

---

### 4. Epitaph repeat on consecutive same-context turns (HIGH)

**Symptom:**
Run 1: Turns 4 and 5 identical.
Run 2: Turns 5 and 6 identical.

**Context:**
Fix 1 in fixes_10 resolved election-based resets.
The issue now appears to be that when game state barely
changes between turns (same choice type, same alignment,
same trajectory), Claude generates the same thematic
angle even with the rotation system active.

**Investigation required:**
Check server logs for (recent angles:) on repeated turns.
If the angle IS rotating but output still repeats, the
similarity check threshold needs tightening.
If the angle is NOT rotating, a reset is still occurring
in a different code path.

**Fix:**
Check whether the post-generation similarity check is
running. The fallback template system should catch
repeats — if generated epitaph shares 6+ words with
recent epitaphs, use a template instead. May need to
reduce threshold to 4 words.

**Files:** npc_engine.py

---

### 5. INCOMING not generating contact dialogue (MEDIUM)

**Symptom:**
INCOMING contacts queue correctly in EOT but render
as a single italic context hint line above the NPC's
regular communiqué rather than a distinct generated
dialogue card.

**Root cause:**
generate_npc_contact_dialogue() either not being called
or its output not stored in contact.dialogue.
Frontend may be rendering contact.context_hint directly
instead of contact.dialogue.

**Fix:**
1. Verify generate_npc_contact_dialogue() is called
   for each pending contact at turn start
2. Verify generated dialogue stored in
   pending_npc_contacts[n].dialogue not context_hint
3. In DialoguePanel.jsx render contact.dialogue
   not contact.context_hint

The INCOMING badge is correct — just the dialogue
content needs to be the generated response.

**Files:** api.py, npc_engine.py, DialoguePanel.jsx

---

### 6. Deal history empty despite accepted deal (MEDIUM)

**Symptom:**
Run 2 Turn 4: Bill's $2B deal accepted in negotiation.
Deal History section: "(no deals recorded)"

**Root cause:**
accept_counter endpoint likely updates game state but
does not append to game_state.deal_history. Memory
hook writes to memory but not to deal_history.

**Fix:**
In /accept_counter endpoint (api.py), after applying
deal consequences, append to game_state.deal_history
with same structure as static choice deals.

**Files:** api.py (accept_counter endpoint)

---

### 7. Security axis level 3 missing intel unlock (MEDIUM)

**Symptom:**
Security axis at level 3+ does not unlock the Get Intel
button on NPC cards. Operations drawer correctly
unlocks at Security 3 but intel access does not.

**Root cause:**
Frontend and backend gating still checks old binary flag:
  corruption_upgrades['intelligence_apparatus']
instead of:
  cabinet_axes['security'] >= 3

**Fix:**
Update gating in both:
- Frontend: intel button visibility condition
- Backend: /get_intel endpoint validation

One-line fix in each location.

**Files:** api.py, relevant frontend component

---

### 8. Skim panel missing full EOT projection (MEDIUM-HIGH)

**Symptom:**
Skim panel shows projected budget after skim but before
EOT costs. Players cannot see whether skimming will
cause bankruptcy after all costs apply.

**Fix:**
Build full EOT projection matching the bankruptcy check:
  projected = budget - skim - govt_costs - oil_imports
            - sanctions - eu_friction + GDP + installments

Display as:
  "PROJECTED AFTER SKIM: -$2.1B (includes all EOT costs)
   ⚠️ Skim will cause bankruptcy this turn"

World events still excluded — caveat text covers this.

**Files:** api.py or turn_processor.py, SkimPanel.jsx

---

### 9. Verbose upgrade log (MEDIUM)

**Symptom:**
Turn history shows every slider tick and every axis
investment step individually rather than summaries.

**Fix:**
At EOT, collapse multiple same-type entries:
  "Tax rates set: income 35%, corporate 20%, resource 30%"
  "Security axis: 0 → 3 (total cost: $4B)"

**Files:** api.py (/set_tax_rates, /cabinet_invest)

---

### 10. Shadow Cabinet rename + always accessible (MEDIUM)

**Fix:**
A) Rename to "CABINET" — covers both governance and
   covert operations without implying only the latter.

B) Status bar button accessible at ALL game phases,
   not just during skim flow.

**Files:** StatusBar.jsx, ShadowCabinet.jsx, GameScreen.jsx

---

### 11. DPRG intel sharing not generating intel (MEDIUM)

**Symptom:**
DPRG sharing world event fires message but delivers
no actual intel content.

**Investigation:**
Add console log to find event type string mismatch.
If [turn_processor] DPRG INTEL SHARING: generating
never appears, it's the string mismatch.

**Files:** turn_processor.py

---

### 12. Bill negotiation posture ignoring canceled election (MEDIUM)

**Session 5 note:**
Vector memory is the full fix. Reassess after confirming
memory writes are working in production. If memory
confirmed working and Bill still ignores canceled
election, implement interim context injection fix.

**Files:** npc_engine.py

---

## ITEMS TO VERIFY IN PRODUCTION BEFORE FIXES_11

1. Memory writes happening — check Railway logs for
   [memory_engine] entries after deals/elections

2. Extraction axis level 5 budget injection — Run 1
   Turn 4 hit Extraction 5 but no one-time injection
   appeared in EOT

3. Relationship summary rewrite — Tier 2 Haiku call
   should fire each EOT. No log seen in any test run.

---

## CONFIRMED WORKING — Session 5

- Cabinet maintenance costs ✅
- Tech passive acquisition every turn ✅
- Tax revenue in GDP calculation ✅
- Tax effects on approval ✅
- INCOMING CONTACTS queuing in EOT ✅
- INCOMING badge on NPC card ✅
- Arabia tier boundary warnings ✅
- Three-drawer Shadow Cabinet structure ✅
- Axis invest/defund controls ✅
- Soft Power stat visible ✅
- Diplomatic Capital stat visible ✅
- Bill referencing Arabia alignment in negotiation ✅

---

## DEFERRED BY DESIGN

- Negotiated deal cross-NPC consequence warnings — Session 7 GM layer
- Daily briefing UI — Session 6
- Resource development mechanics — Session 7
- Financial sector income — Session 6+
- Foreign Intel Network full UI — Session 6
