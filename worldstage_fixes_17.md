# WORLD STAGE — FIXES 17
## Session 6 Testing Bugs
Generated: March 2026

---

## PRIORITY ORDER

| Fix | Issue | Type |
|-----|-------|------|
| A | Propaganda/Domestic Suppression wrong budget source | Bug |
| B | Defense Procurement unlimited per turn | Bug |
| C | Arms Export arbitrage with Defense Procurement | Bug |
| D | Counter-offer conditional renders "EU above null" | Bug |
| E | Conditional withheld checks wrong variable | Bug |
| F | Historian verdict wrong personal wealth value | Bug |
| G | Historian verdict truncates mid-sentence | Bug |
| H | Approval spike to 100% then instant collapse | Bug |
| I | Show all eligible advisors in pool | Design fix |
| J | Sadam repeats specifics demand | Prompt fix |
| K | Martyrdom blocked by stability drift | Design fix |

---

## FIX A — Propaganda/Domestic Suppression wrong budget source

**Issue:** Both Tier 1 brigade operations deduct from national
budget but should deduct from personal wealth.

**Files:** api.py (brigade_operation endpoint), ShadowCabinet.jsx

**Instructions:**
In api.py, find brigade_operation handler for ops 1 and 2:
- Change budget source from gs.budget to gs.personal_wealth
- Update deduction and affordability check accordingly

In ShadowCabinet.jsx, find OPERATIONS array entries for these
two ops:
- Change budgetType from 'national' to 'personal'
- Update badge label to show PERSONAL not STATE

Add console.log:
[BRIGADE] Propaganda Campaign: -$1B personal
[BRIGADE] Domestic Suppression: -$2B personal

Verify frontend canAfford check uses personal_wealth
for these two ops.

Do not change any other operation logic.

**Verify:** Deploy Propaganda Campaign — should deduct from
personal wealth, not national budget.

---

## FIX B — Defense Procurement unlimited per turn

**Issue:** Defense Procurement (+5 military, -$3B national)
has no per-turn limit. Player can spam it multiple times
in the same turn for unlimited military gain.

**Files:** api.py or ShadowCabinet.jsx (wherever action
cooldown is tracked)

**Instructions:**
Add a used_this_turn flag to Defense Procurement that resets
each turn. If already used this turn, button should show
as disabled with "Used this turn" label.

Add console.log:
[MILITARY] Defense Procurement: blocked — already used
this turn

Do not change any other operation logic.

**Verify:** Use Defense Procurement once, confirm button
disables. End turn, confirm button re-enables.

---

## FIX C — Arms Export arbitrage

**Issue:** Arms Export (-5 military, +$4B national, +8
relations) can fire same turn as Defense Procurement
(+5 military, -$3B national), creating net +$1B and +8
relations with no military cost. Unintended.

**Files:** api.py or ShadowCabinet.jsx

**Instructions:**
Arms Export should be once per turn AND cannot fire the
same turn as Defense Procurement. If Defense Procurement
was used this turn, Arms Export button shows disabled
with "Cannot combine with Defense Procurement this turn."

Alternatively, simpler: Arms Export is once per turn
regardless, same used_this_turn flag as Fix B.

Do not change Arms Export mechanics otherwise.

**Verify:** Use Defense Procurement, confirm Arms Export
is blocked. Use Arms Export without Defense Procurement,
confirm it works normally.

---

## FIX D — Counter-offer conditional renders "EU above null"

**Issue:** Counter-offer second tranche condition renders
as "conditional: EU above null" in the deal panel instead
of the actual negotiated condition. Dialogue text is correct
but structured panel shows null.

**Files:** npc_engine.py (counter-offer generation),
DialoguePanel.jsx (panel rendering)

**Instructions:**
Check counter-offer generation in npc_engine.py. The
conditional field for installment deals is not being
stored correctly when the condition is narrative
(e.g. "merit-based judicial appointments") rather
than numeric. The condition string needs to be extracted
and stored in the structured counter-offer object.

Check DialoguePanel.jsx rendering of the conditional
field — confirm it displays whatever string is stored,
not a null fallback.

Add console.log:
[NPC] Counter-offer conditional: {condition_string}

**Verify:** Negotiate a two-tranche deal with Marsha.
Confirm second tranche shows actual condition text,
not "EU above null."

---

## FIX E — Conditional withheld checks wrong variable

**Issue:** EOT conditional withheld message shows
"EUROPA [50] not above 80" when EU relations are 100.
Wrong variable being checked in conditional verification.

Seen in export: "EU conditional withheld: $1.5B —
EUROPA [50] not above 80 ✗"

**Files:** turn_processor.py (conditional payment
verification pipeline)

**Instructions:**
In the conditional payment verification, find where
EUROPA [50] is being read. This appears to be reading
a wrong variable — likely a snapshot value or a
different field entirely — instead of current EU
relations. Fix to read gs.relations['eu'] or
equivalent current-turn EU value.

Add console.log:
[CONDITIONAL] Checking EU condition: current EU = X,
threshold = Y, result = pass/fail

Do not change any other conditional payment logic.

**Verify:** Negotiate conditional deal with EU threshold.
Confirm EOT message reflects actual current EU value.

---

## FIX F — Historian verdict wrong personal wealth value

**Issue:** Historian verdict references wrong personal
wealth figure. Run ended with $177.3B personal but
historian said "$29 billion."

**Files:** turn_processor.py or api.py (wherever
end-game historian Claude call is constructed)

**Instructions:**
Check what value is being passed to the historian
Claude call as personal_wealth. It may be reading
a snapshot from earlier in the turn before EOT
calculations complete, or reading the wrong field.

Confirm the historian prompt receives the final
post-EOT personal_wealth value.

Add console.log:
[HISTORIAN] Personal wealth passed to prompt: $X.XB

**Verify:** End a run with known personal wealth.
Confirm historian references the correct figure.

---

## FIX G — Historian verdict truncates mid-sentence

**Issue:** Historian verdict cuts off mid-sentence in
multiple ending types across multiple runs. Appears
to be a token limit issue.

**Files:** Wherever the historian Claude API call is made
(turn_processor.py or api.py)

**Instructions:**
Increase max_tokens on the historian Claude call from
current value to 1000. Also check if there is a
character limit applied to the verdict string before
display in the frontend — if so, increase or remove it.

Add console.log:
[HISTORIAN] Verdict length: X chars, tokens: ~Y

**Verify:** Run to Turn 10. Confirm historian verdict
ends with a complete sentence and a period.

---

## FIX H — Approval spikes to 100% then collapses

**Issue:** In one run, approval showed 100% at Turn 5
then immediately collapsed to 68% in the same EOT block.
Likely a calculation ordering issue — approval is being
read before sanctions/pressure penalties apply.

**Files:** turn_processor.py (EOT approval calculation
ordering)

**Instructions:**
Add console.log at each step of approval calculation
in EOT to trace the sequence:
[APPROVAL] Pre-sanctions: X%
[APPROVAL] Post-sanctions: X%
[APPROVAL] Post-pressure: X%
[APPROVAL] Final: X%

If approval is being displayed or snapshotted before
sanctions penalties apply, move the display to after
all penalties resolve.

**Verify:** Replicate conditions from Martyrdom run
(USA Tier 4 sanctions active, Western Bloc pressure).
Confirm no 100% spike appears in EOT log.

---

## FIX I — Show all eligible advisors in pool

**Issue:** Advisor pool randomly selects 4 from all
eligible archetypes. Spy Chief has ~50-57% chance of
appearing per pool generation, missing in 3 consecutive
runs. Players should see all eligible options.

**Files:** advisor_engine.py, ShadowCabinet.jsx

**Instructions:**
In generate_advisor_pool(): remove the random.shuffle
and truncate-to-4 step entirely. Return all archetypes
that pass the gate check and roster filter.

In ShadowCabinet.jsx: update the Advisors tab to render
however many advisors are in the pool — if 7 cards,
show 7 cards. No fixed grid size.

Keep the max_advisors hire limit (3, or 4 with Pack
the Cabinet) — player still can only HIRE a limited
number, they just see all available options.

Remove SHUFFLE CUT diagnostic log. Keep GATE CHECK,
PASS/FAIL, AVAILABLE, and CANDIDATES logs.

**Verify:** Invest Intelligence to L4. Confirm Spy Chief
appears in advisor pool alongside all other eligible
archetypes.

---

## FIX J — Sadam repeats specifics demand

**Issue:** In negotiation, Sadam re-asks for the same
specifics (refinery names, years, consequences) up to
four times even after player has partially answered.
Feels like a broken record.

**Files:** npc_engine.py (Sadam system prompt)

**Instructions:**
Add to Sadam's system prompt:

"Do not repeat the same request for specifics more
than once. If the player has provided partial answers
— named some locations, given a timeframe, named a
consequence — treat those as sufficient and move the
negotiation forward to your counter-offer or next
demand. Pressing for the same detail more than once
makes the negotiation feel circular and unrealistic.
Accept imprecision and advance."

Do not change any other NPC prompts.
Do not change counter-offer generation logic.

**Verify:** Open Sadam negotiation. Give a partial
answer (e.g. "half my refineries"). Confirm he
accepts the partial answer and moves forward rather
than re-asking for specifics.

---

## FIX K — Martyrdom blocked by stability drift

**Issue:** Martyrdom ending (stability 0, approval 70%+)
is nearly impossible to trigger because stability drift
pulls stability back toward approval every EOT. When
approval is high, stability 0 is self-correcting within
one turn. The higher the approval, the faster it bounces.

**Files:** turn_processor.py (Martyrdom check,
stability drift calculation)

**Instructions:**
Check for Martyrdom as a trigger event when stability
first hits 0 mid-turn during consequence processing,
BEFORE drift applies. Specifically:

After applying all choice consequences and pressure
events in turn_processor, before running drift
calculation:
- If stability <= 0 AND approval >= 70: set a
  martyrdom_triggered flag on game state
- At Turn 10 (or on collapse), if martyrdom_triggered
  is True: fire Martyrdom ending instead of
  standard collapse

This means drift can still apply (stability bounces
back) but the Martyrdom condition was met at the
moment it mattered.

Add console.log:
[MARTYRDOM] Triggered: stability={X}, approval={Y}
at turn {N} pre-drift

Do not change drift calculation.
Do not change other ending checks.

**Verify:** Set up conditions where Arabia premium
deals crash stability to 0 while approval stays
above 70. Confirm martyrdom_triggered flag is set.
Run to Turn 10 and confirm Martyrdom ending fires.

---

## ALREADY SUBMITTED (do not resubmit)

- Dev panel for localhost testing (submitted this session)
- Cabinet description labels for last four axes
  (submitted this session)

---

## NOTES FOR CLAUDE CODE

- Confirm each fix title before starting
- Add console.log for every fix as specified
- Do not implement any features not listed here
- Do not modify any other files not specified
- Human will verify all fixes in browser

Recommended order: A, B, C first (operations bugs,
straightforward). Then D+E together (same pipeline).
Then F+G together (same historian call). Then H, I,
J, K separately.
