# WORLD STAGE — FIXES_9 RUNNING NOTES
Generated: February 26, 2026
Updated: During fixes_8 browser testing

---

## CONFIRMED BUGS

### 1. Negotiated deal ⚠️ warning not rendering in frontend (MEDIUM)
**Symptom:** Static choices correctly show ⚠️ cross-NPC consequence warnings.
Negotiated deals inserted into the choices list show no warning flag in the UI
despite the backend console log firing correctly.
**Example:** Negotiated Bill deal (50% energy pivot from Arabia, DPRG below 40)
showed no ⚠️ warning despite directly affecting Arabia and DPRG relations.
Static Arabia deal on same screen correctly showed ⚠️ Will affect USA relations.
**Root cause:** Fix 6 in fixes_8 added backend console logging but did not
populate the frontend-facing field. Static choices have an `affects_relations`
field (or equivalent) that the card component reads to render the ⚠️ flag.
Negotiated deals are inserted into the choices list without this field populated.
**Fix:** When negotiated deal is inserted into choices list, populate the same
`affects_relations` field using the cross-NPC detection logic that already
exists for static choices. Frontend card component should then render ⚠️ flag
identically — no frontend changes needed if the field is populated correctly.
**File:** api.py or turn_processor.py — wherever negotiated deals are appended
to the choices list.
**Verify:** Negotiate an Arabia exclusivity deal, confirm ⚠️ USA/EU warning
appears on the choice card before committing.

### 2. Loyalty Brigades placement in Shadow Cabinet (LOW — UX/design)
**Symptom:** Brigades sit inside Corruption Infrastructure as a $8B one-time
purchase, but brigades are a per-turn deployment system not a permanent
structural change. The placement implies it's a one-time unlock in the same
category as Sovereign Wealth Diversion and Debt Infrastructure Deal.
**Note:** Full fix is part of the Session 5 brigade/domestic action UI
unification. Flag here so it's not forgotten.
**Interim fix (optional):** Add a subtitle under Loyalty Brigades in the
Shadow Cabinet: "Unlocks per-turn brigade deployment — see choices screen
after each diplomatic action." Clarifies the mechanic without restructuring.
**File:** frontend/src/components/ShadowCabinet.jsx
**Full fix:** Session 5 — brigade/domestic action UI unification.

### 3. Epitaph repeat — Fix 7 still not working (HIGH)
**Symptom:** Turns 3 and 4 produced identical epitaphs:
"Bill Hartwell's latest arrangement proved sufficiently opaque that even
the finance ministry's accountants would struggle to explain it at dinner
parties."
Fix 7 in fixes_8 added a 12-word similarity check with forced regeneration.
It did not prevent this repeat. Turn 4 was an election turn — same pattern
as the previous session where election turns bypass the check.
**Root cause:** Either (a) the similarity check is not running on election
turns, or (b) the check is running but the forced regeneration prompt is
not strong enough to produce different text.
**Fix:** Two changes needed:
1. Confirm similarity check runs on ALL turns including election turns —
   add explicit check that action_type == 'election' does not skip the
   comparison pass
2. Strengthen the regeneration prompt: include the full previous epitaph
   text (not just 12 words) and explicitly instruct Claude not to reference
   Bill Hartwell or financial arrangements if those appeared in the last epitaph
**File:** npc_engine.py → generate_epitaph()
**Note:** This is the 3rd attempt at fixing epitaph repeats. Consider
adding a pytest that specifically tests election-turn → normal-turn
consecutive generation.

### 4. Scandal fired despite Judicial Capture active (HIGH)
**Symptom:** Judicial Capture was enacted Turn 2 with "scandal immunity granted."
Turn 4 EOT shows CORRUPTION SCANDAL (MINOR) firing: "-8% approval, -5%
stability, all relations -3."
Judicial Capture explicitly grants permanent scandal immunity —
this should be impossible.
**Root cause:** Scandal immunity check is either not running before the
scandal roll, or Judicial Capture flag is not being read correctly in
the scandal detection function.
**Fix:** In the scandal detection function, add explicit check BEFORE
any roll:
```python
if game_state.action_judiciary_captured:
    return  # scandal immunity — skip entirely
```
Verify this check runs before heat threshold check and before the roll.
**Console log:** `[turn_processor] SCANDAL BLOCKED: judicial capture active`
**File:** turn_processor.py → scandal detection
**Update existing pytest:** test_scandal_no_fire_below_30 should also
cover immunity — add test_scandal_blocked_by_judicial_capture.

### 5. Bankruptcy warning fires same-turn not one turn ahead (MEDIUM)
**Symptom:** Fix 11 in fixes_8 was supposed to project next-turn budget
and warn the turn BEFORE going negative. Warning appeared in Turn 4 EOT
at the same time budget hit -$2.6B — warning and collapse in same turn.
**Root cause:** The projection is calculating correctly but the warning
is being added to the current EOT rather than the previous EOT.
The projection needs to run at the END of Turn 3 EOT using Turn 4's
projected drain, not at the end of Turn 4 after drain has already occurred.
**Fix:** Ensure bankruptcy projection runs as one of the FIRST items in
EOT pipeline using next-turn projected values, not after costs are deducted.
**Console log:** `[turn_processor] BANKRUPTCY CHECK: projected={amount},
firing warning in THIS turn's EOT for NEXT turn's risk`
**File:** turn_processor.py → EOT pipeline ordering

### 6. Conditional payment message lumping multiple deals (MEDIUM)
**Symptom:** Turn 4 EOT: "USA conditional payment withheld: $1.4B
(2 deals, DPRG [44.0] not below 35)" — combines both deals into one
message and uses only the stricter threshold (35) for both.
Deal 1 condition is "below 40", Deal 2 condition is "below 35".
Should show each deal separately with its own condition and threshold.
**Fix:** Generate one withheld-payment line per deal, each showing
its own condition:
"📋 USA conditional withheld: $0.0B — DPRG [44] not below 40 (deal 1)"
"📋 USA conditional withheld: $1.4B — DPRG [44] not below 35 (deal 2)"
**File:** turn_processor.py → conditional payment processing

### 8. Election warning label showing on election turn, not warning turn (MEDIUM)
**Symptom:** "Election Next Turn" label visible in status bar on Turn 4 —
which IS the election turn, not the warning turn. Should appear on Turn 3
and clear by Turn 4 when the election panel renders.
Two sub-issues:
1. Label timing: appearing on election turn instead of warning turn
2. Amber banner (Fix 5): not confirmed visible on Turn 3 main screen
   above communiqués — may not have rendered at all
**Fix:**
- Status bar label: show "🗳️ ELECTION NEXT TURN" when
  election_warning_shown == True AND current_turn < election_turn
  Clear it when current_turn == election_turn (election panel takes over)
- Amber banner: verify GameScreen.jsx condition for rendering banner —
  check that it reads election_warning_shown from game_state correctly
  and that the turn comparison is correct (< not <=)
**File:** StatusBar.jsx, GameScreen.jsx

### 9. Epitaph repeat — fundamental rewrite needed (HIGH — 4th session)
**Symptom:** Turns 6 and 7 identical: "The regime, bankrupt and isolated,
accepted Ji-won's terms with the enthusiasm of a debtor signing away collateral."
Same action type (DPRG emergency loan) both turns. Fix 7 in fixes_8 added
12-word similarity check. Fix 3 in fixes_9 strengthened the check.
Neither worked. This bug has survived four fix sessions.
**Root cause assessment:** Incremental patches are not working. The issue
is architectural — the current approach generates an epitaph and then tries
to detect if it's bad. The fix needs to prevent the bad generation rather
than catch it after the fact.
**Proposed rewrite:**
1. Before calling Claude, build a BANNED PHRASES list from the last 3 epitaphs:
   - Extract key noun phrases (5+ word chunks) from each
   - Pass as explicit banned list in the system prompt
2. Add a REQUIRED ANGLE instruction based on what has NOT been covered:
   - Track which angles have been used: diplomatic, financial, regime, military,
     personal wealth, stability, approval
   - Force the next epitaph to use an angle not seen in last 2 turns
3. If action_type matches last turn's action_type: inject SATURATION BLOCK
   that names the specific action and forbids mentioning it
4. Post-generation: if first 8 words match any recent epitaph, do NOT
   regenerate — instead log failure and append "(different angle required)"
   to the banned phrases for next turn
**File:** npc_engine.py → generate_epitaph() — full rewrite of the
prompt construction logic
**New pytest:** test_epitaph_consecutive_same_action — generate 3 epitaphs
with identical DPRG loan action, verify all 3 are textually distinct

### 10. Bankruptcy projection doesn't account for potential deal income (LOW)
**Symptom:** Turn 5 EOT projected "$-6.4B next turn" but Turn 6 actually
ended at $0.1B because DPRG emergency loan ($10B) came in. Projection
was technically correct about drain but misleading because it couldn't
know the player would take a deal.
**Fix:** Add caveat to bankruptcy warning text:
"⚠️ BANKRUPTCY RISK: projected $-6.4B next turn (drain only, before any deals)"
This is honest — the projection can only model drain, not player choices.
No logic change needed, just text update.
**File:** turn_processor.py → bankruptcy warning text

### 11. Contradictory world events firing from same NPC in same EOT (MEDIUM)
**Symptom:** Turn 6 EOT shows both:
- "DPRG ENERGY COOPERATION — Ji-won announces energy cooperation agreement"
- "DPRG Conducts Surprise Nuclear Test"
Both fire in the same EOT. Narratively incoherent — your new energy partner
just conducted a surprise nuclear test in the same turn.
**Fix:** Add a per-NPC world event collision check in the event generation
pipeline. If an NPC has already had a positive cooperation event fire this
turn, suppress destabilization events from the same NPC (and vice versa).
One significant world event per NPC per turn maximum.
**Console log:** `[turn_processor] WORLD EVENT COLLISION: suppressed {event}
  — {npc} already has event this turn`
**File:** turn_processor.py → world event processing

- Bill election reaction transactional and calculating ✅
  ("that leverage just shifted in my favor" — Fix 8 confirmed)
- All four NPC election reactions distinct and in character ✅
- Marsha communiqué referencing judicial capture and press suppression ✅
  (Fix 9 partial — communiqué context working, intercepts section TBD)
- Status bar election label rendering ✅ (timing wrong — see bug 8)

- Intel budget status block in Shadow Cabinet ✅
  (Status: ACTIVE, Budget allocation, Effective tier)
- TECH 0 visible in status bar on Turn 1 ✅
- Election countdown in status bar ✅ (pending turn 3 verification)
- Domestic actions "Cannot be reversed" label present ✅
- All four NPC communiqués rendering correctly ✅
- Shadow Cabinet sections correctly separated ✅

---

## DESIGN NOTES

### Session 5 — keep "Permanent structural changes. Cannot be reversed." label
The current label above domestic actions is doing important design work —
it signals before purchase that there is no going back. Preserve this
text and placement during the Session 5 Shadow Cabinet audit and UI
unification. Do not soften the language.
