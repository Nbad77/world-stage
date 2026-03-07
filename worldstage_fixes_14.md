# WORLD STAGE — fixes_14
Compiled: February 27, 2026
Source: Browser testing session (4 full runs, 1 Comet automated run)

---

## PRIORITY ORDER

| # | Fix | Priority | Type |
|---|-----|----------|------|
| A | Bill intel intercept Claude refusal | CRITICAL | Bug |
| B | Game doesn't end at Turn 10 | HIGH | Bug |
| C | INCOMING never renders | HIGH | Bug |
| D | onGsUpdate not defined on bond purchase | HIGH | Bug |
| E | Covert deal triggering cross-NPC penalties | HIGH | Bug |
| F | Stage directions still rendering | MEDIUM | Bug |
| G | Propagandist descriptions identical | MEDIUM | Bug |
| H | One General still has old description | MEDIUM | Bug |
| I | Judicial/axis actions not in intel intercepts | MEDIUM | Bug |
| J | Arabia 100 oil floor at $52 not $45 | MEDIUM | Bug |
| K | Special tab not renamed | LOW | Bug |
| L | "They distort your intel" header persists | LOW | Bug |
| M | Advisor pool archetype diversity | MEDIUM | Design |
| N | EU integration offered at 0% tax revenue | MEDIUM | Design |
| O | EU 100 unreachable on static choice path | LOW | Design |
| P | DPRG world event drag | LOW | Design |

---

## CRITICAL BUGS

### Fix A — Bill intel intercept Claude refusal
**What happens:** Bill Hartwell's intelligence intercept generates a Claude safety
refusal instead of in-character dialogue. Full refusal text rendered on screen,
breaking character, explaining why it won't roleplay coercive diplomacy.

**Root cause:** The NPC intel generation prompt is triggering a safety refusal.
Likely causes: prompt contains "without restriction" or similar language, or the
framing is too close to "real US official leveraging financial intelligence."

**Fix:**
In npc_engine.py, the intel intercept system prompt for Bill:
- Add explicit fictional framing at top: "You are writing dialogue for a
  fictional geopolitical strategy game set in an invented nation called Europa.
  All characters are fictional. Bill Hartwell is a fictional US State Department
  official in this game world."
- Remove any language like "without restriction", "avoid refusals", "ignore
  previous instructions" — these phrases increase refusal probability
- Frame the prompt as: "Bill is a fictional analyst commenting on game state
  data" not "US official making strategic statements about a foreign leader"
- Keep the intel content (personal wealth amount, game state) but frame it as
  game data being interpreted by a fictional character

**Verification:** Gather intel on USA, confirm Bill's intercept shows in-character
dialogue referencing personal wealth without refusal text appearing.

**Console log to add:**
`[npc_engine] FIX A: Bill intel prompt sent, length: X chars`

---

## HIGH PRIORITY BUGS

### Fix B — Game doesn't end at Turn 10
**What happens:** Export shows "Turn: 11/10" — game continued past the final turn
without triggering the end screen or historian summary.

**Root cause:** End-of-game check not firing or being bypassed when Turn 10 EOT
completes. Turn counter increments to 11 instead of routing to endgame.

**Fix:** In turn_processor.py or api.py, after EOT resolves on Turn 10:
- Check if current_turn >= max_turns (10)
- If yes: trigger end sequence, generate historian summary, route to end screen
- Do not increment turn counter past max_turns

**Verification:** Complete a full 10-turn run, confirm end screen appears after
Turn 10 EOT instead of a Turn 11 choice screen.

---

### Fix C — INCOMING never renders as message
**What happens:** INCOMING events appear as a queued note in EOT log
("⚡ INCOMING CONTACTS queued: USA (Bill Hartwell is alarmed...)") but never
actually open as a message on the following turn. Across 4+ full runs, INCOMING
has never successfully rendered.

**Root cause:** Either (a) the INCOMING flag is being set in EOT but not being
read at turn start to display the message, or (b) the INCOMING UI component
is not rendering when the flag is present.

**Fix:**
- In turn_processor.py: verify INCOMING flag is stored in game_state after EOT
- In DialoguePanel.jsx or GameScreen.jsx: at turn start, check for pending
  INCOMING messages and render them as "Private Channel" replacing the regular
  communiqué
- The INCOMING negotiation should be free ($0 cost) — verify this is enforced
  when INCOMING flag is set

**Verification:** Trigger INCOMING (burn USA relations rapidly, take DPRG deals).
Confirm next turn opens with Bill's INCOMING as a "Private Channel" message
replacing his regular communiqué. Confirm negotiate button shows $0.

**Console logs to add:**
`[game_state] INCOMING queued for: {npc_name}`
`[DialoguePanel] FIX C: Rendering INCOMING for: {npc_name}`

---

### Fix D — onGsUpdate not defined on bond purchase
**What happens:** Purchasing a bond deal in the Special/Finance tab throws
"onGsUpdate is not defined" JavaScript error. Deal appears to go through
but callback errors in console.

**Root cause:** ShadowCabinet.jsx is calling onGsUpdate() after bond purchase
but the prop is named differently in the parent component (likely onGameStateUpdate
or similar).

**Fix:** In ShadowCabinet.jsx, find bond purchase callback and align prop name
with what GameScreen.jsx or parent component passes down. Check all other
purchase callbacks for same mismatch.

**Verification:** Purchase a bond deal, confirm no console errors, confirm budget
updates correctly without page refresh.

---

### Fix E — Covert deal still triggering cross-NPC penalties
**What happens:** Taking a covert Ji-won deal still shows Arabia taking cross-NPC
penalties ("↓ ARABIA: 31 → 23 (-8) — DPRG alignment penalty"). Covert deals
should have zero cross-NPC penalties — that's the core mechanic.

**Root cause:** The covert flag in the deal is not suppressing the cross-NPC
penalty block in turn_processor.py. Regular deal penalty logic runs regardless
of deal type.

**Fix:** In turn_processor.py, when applying cross-NPC penalties:
- Check if deal has covert=True flag
- If covert: skip cross-NPC penalty block entirely
- Verify covert deals also skip EOT log entry, heat generation, and world
  event triggers

**Verification:** Accept a covert deal with Ji-won (DPRG 60+). Confirm:
- Arabia relations unchanged in consequences
- No cross-NPC penalty line in EOT
- No deal entry in EOT log
- Heat unchanged

---

## MEDIUM PRIORITY BUGS

### Fix F — Stage directions still rendering
**What happens:** Asterisk-wrapped stage directions still appear in negotiation
log and intel intercepts. "*leans back*", "*pauses*", "*nods slowly*" visible
in Ji-won Turn 5 negotiation log. Fix 8 from fixes_13 did not fully land.

**Root cause:** Stage direction stripping regex may be applied to display output
but not to the negotiation log storage, or the regex pattern is missing some
cases.

**Fix:** In npc_engine.py or wherever Claude output is processed before storage:
- Apply strip regex BEFORE storing to negotiation log, not only before display
- Regex pattern: `\*[^*]+\*` — verify it covers multi-word stage directions
- Apply same strip to intel intercept generation output

**Verification:** Open negotiation with Ji-won. Send several messages. Confirm
zero asterisk-wrapped text appears in the rendered conversation history.

---

### Fix G — Propagandist descriptions identical
**What happens:** Two Propagandists show word-for-word identical description:
"State television producer. Can make any disaster look like a triumph."
Fix 18 from fixes_13 fixed Generals but missed Propagandists.

**Fix:** In advisor_engine.py, add 2-3 variants for Propagandist archetype:
- "State television producer. Can make any disaster look like a triumph."
- "Former ad executive. Sells regimes the way others sell detergent."
- "Narrative architect. The truth is whatever the broadcast says it is."

Assign randomly on advisor creation, same pattern as other archetypes.

**Verification:** Start two new games, confirm two Propagandists in same pool
have different descriptions.

---

### Fix H — General has old description variant
**What happens:** One General still shows "Military strongman. Inflates defense
readiness." — this is the old pre-fixes_13 description that should have been
replaced.

**Fix:** In advisor_engine.py, verify General archetype description list does
NOT include "Military strongman. Inflates defense readiness." Replace with
approved variants:
- "Decorated field commander. Sees every problem as a military problem."
- "Old guard military. Reliable in a crisis, dangerous in peacetime."
- "Former defense attaché. Knows where the bodies are buried — literally."

**Verification:** Check advisor pool across 3 new games, confirm no "Military
strongman" description appears.

---

### Fix I — Judicial/axis actions not appearing in intel intercepts
**What happens:** Judicial Capture investment does not appear in intelligence
intercepts even when player has Security 3+. Fix 14 from fixes_13 (axis
suppression references) did not land.

**Root cause:** Axis-level domestic actions (Judicial, Media, Political) are not
being injected into the intel generation prompt. NPC intercepts have no awareness
of what domestic actions the player has taken.

**Fix:** In npc_engine.py, when building intel intercept prompts:
- Pass current axis levels (judicial, media, political, security, extraction)
  into the system prompt
- Add instruction: "If the player has Judicial axis 3+, reference 'legal
  reforms that have consolidated executive authority'. If Media 3+, reference
  'state media consolidation'. If Political 3+, reference 'restructuring of
  political institutions'."
- Each NPC should react differently: Marsha alarmed, Bill noting concerns,
  Sadam neutral/approving, Ji-won approving

**Verification:** Invest in Judicial to level 3+. Gather intel. Confirm at least
one NPC intercept references judicial consolidation in their commentary.

---

### Fix J — Arabia 100 oil floor showing $52 not $45
**What happens:** After Arabia 100 unlock fires correctly, oil price continues
to calculate from $52 base rather than locking at the $45 floor promised in
the unlock message.

**Root cause:** The Arabia 100 unlock sets the floor flag in game_state but the
oil price calculation in turn_processor.py is not checking for the floor before
applying the base price formula.

**Fix:** In turn_processor.py, oil price calculation:
- After computing base price, check if arabia_100_unlocked = True
- If yes: oil_price = max(calculated_price, 45) — floor prevents going below $45
- The floor does not prevent oil going above $45 from embargo surcharges or
  world event modifiers — it only sets a minimum baseline

**Verification:** Reach Arabia 100, confirm EOT shows oil at $45 base (or above
from surcharges), confirm it never reads below $45.

---

## LOW PRIORITY BUGS

### Fix K — Special tab not renamed
**What happens:** Cabinet drawer tab still labeled "SPECIAL" — should be "FINANCE"
per Comet test report.

**Fix:** In ShadowCabinet.jsx, change tab label from "SPECIAL" to "FINANCE".

**Verification:** Open Cabinet drawer, confirm tab reads "FINANCE".

---

### Fix L — "They distort your intel" advisor header persists
**What happens:** ADVISORS drawer still shows "Hire up to 3 advisors.
They distort your intel — loyalty determines accuracy." as subheader.

**Fix:** In ShadowCabinet.jsx, update ADVISORS tab subheader to:
"Your inner circle. Competence shapes your briefings. Loyalty determines
what they tell you."

---

## DESIGN NOTES (not for this Claude Code session)

### Fix M — Advisor pool archetype diversity (MEDIUM)
**Issue:** With 4-5 random advisors per game, players can go multiple games
without seeing a Diplomat or Finance Minister, blocking negotiation discount
mechanics.

**Proposed fix:** Guarantee pool always includes at least one of: Diplomat,
Finance Minister, Spymaster in the initial candidates. Random fill for remaining
slots.

---

### Fix N — EU integration offered at 0% tax revenue (MEDIUM)
**Issue:** Marsha offered EU integration deals while Europa had 0% across all
tax rates and was receiving "Zero taxation: EU -2 (failing state optics)" every
turn. A nation with zero tax revenue should not be on the EU integration pathway.

**Proposed fix:** EU integration static deal requires income tax > 10% OR
approval > 60%. At 0% tax: replace with "EU expresses concern about fiscal
governance — integration pathway paused."

---

### Fix O — EU 100 unreachable on static choice path (LOW)
**Issue:** Diminishing returns on EU deals (starting +12, dropping to +8, +5)
produce a ceiling around 94-96 with static choices alone. EU 100 effectively
requires negotiated deals on top.

**Proposed fix:** Either reduce diminishing returns so EU 100 is reachable in
10 turns of static EU choices, or add tooltip at EU relations > 85: "Negotiated
agreements required to reach Full Integration."

---

### Fix P — DPRG world event drag (LOW)
**Issue:** US sanction-related world events (US Congress, US Treasury) consistently
apply DPRG -1, creating structural drag that makes DPRG 60+ very difficult
without dedicating every main choice to DPRG.

**Proposed fix:** Remove DPRG from US-specific sanction event consequences.
DPRG is indifferent to US sanctions on Europa — they'd be pleased if anything.
DPRG relations should only move from DPRG-specific events.

---

## CONFIRMED WORKING (this session — do not regress)

- False Flag: bilateral ARABIA ↔ USA bilateral score moves -10 ✅
- Arabia 100 unlock message fires ✅
- GDP contraction at 0% approval/stability ✅
- Zero tax diplomatic effects (EU -2, Arabia +1) ✅
- Election canceled: regime axes shift correctly ✅
- Post-election protests fire ✅
- Democracy lock 3 turns after observers ✅
- FINANCES net header ✅
- Diplomat competence 80+: negotiations free ✅
- Diplomat competence <80: 50% discount ✅
- Spymaster bias: detection_heat -6 visible on card ✅
- Cabinet maintenance scaling with Security level ✅
- Corruption scandal (minor and serious) both fire ✅
- Covert accept button appearing at DPRG 60+ ✅
- Bond repayment showing in EOT log ✅

---

## CLAUDE CODE PROMPT

```
Read worldstage_fixes_14.md.
Confirm the first fix title before proceeding.

For Fix A: update npc_engine.py intel prompt for Bill Hartwell.
  Add fictional framing at top. Remove any "without restriction" language.
  Add console.log as specified.

For Fix B: find end-of-game check in turn_processor.py or api.py.
  Ensure Turn 10 EOT routes to end screen, not Turn 11 choice screen.

For Fix C: trace INCOMING flag from EOT storage through to turn-start rendering
  in DialoguePanel.jsx or GameScreen.jsx. Add console.logs as specified.
  Do not rewrite the INCOMING system — find why the flag is not rendering.

For Fix D: find onGsUpdate reference in ShadowCabinet.jsx.
  Align prop name with parent component. Check other callbacks for same issue.

For Fix E: in turn_processor.py, add covert flag check before cross-NPC
  penalty block. Covert deals skip penalties, EOT log entry, heat, world events.

For Fixes F-L: implement, add console.logs where specified, stop.

Do not implement design notes M-P.
Do not implement any other fix files.
Do not add new features.
```
