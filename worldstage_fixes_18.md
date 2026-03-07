# WORLD STAGE — fixes_18.md
Generated: March 3, 2026

5 fixes. All carried forward from fixes_17 verification or discovered during testing.

---

## Fix A — Counter-offer drops narrative condition from structured panel

**Issue:** When Marsha negotiates a counter-offer with dual conditions (one numeric + one narrative), only the numeric condition appears in the structured deal panel. The narrative condition — e.g. "press freedom law passage" — is silently dropped. Dialogue text is correct but the panel shows only the Arabia threshold.

**Example:** Full condition was "press freedom law passage AND Arabia relations ≤65". Panel showed only "Arabia below 65". The press freedom condition was lost from the structured output.

**Root cause:** Counter-offer condition parsing in npc_engine.py likely splits on AND and only stores the first parseable numeric condition. Narrative/qualitative conditions are not being serialized into the deal object.

**Fix:**
- In npc_engine.py, when parsing counter-offer conditions, store ALL conditions — both numeric and narrative — in the deal object
- Numeric conditions: store as `{type: "numeric", variable: "arabia_relations", operator: "below", threshold: 65}`
- Narrative conditions: store as `{type: "narrative", description: "press freedom law passage"}`
- In DialoguePanel.jsx, render both types in the structured panel: numeric conditions as before, narrative conditions as plain text description

**Console log to add:**
```
[npc_engine] COUNTER-OFFER CONDITIONS: {numeric: X, narrative: Y, raw: "..."}
```

**Verification:** Negotiate with Marsha until she produces a counter-offer with a reform condition. Confirm the structured panel shows both the Arabia threshold AND the narrative condition text.

---

## Fix B — Historian verdict reads wrong wealth variable

**Issue:** Historian verdict references a much lower personal wealth figure than the player's actual balance. Observed twice: "$29B" when actual was $177B, and "$41B in diverted wealth" when actual was $223B. The number appears to be total-skimmed-this-game or some intermediate calculation rather than the current personal wealth balance.

**Fix:**
- In the function that constructs the historian Claude call (api.py or turn_processor.py), add a console.log immediately before the API call:
```
[HISTORIAN] Personal wealth passed to prompt: $X.XB
[HISTORIAN] Actual game state personal_wealth: $X.XB
```
- Verify both values match. If they don't, find where the disconnect is and pass `game_state.personal_wealth` directly.
- If "diverted wealth" is a separate tracked variable, it should be used as flavor context only — the historian's stat summary must use the actual current balance.

**Verification:** Run to Turn 10 with known personal wealth (use dev panel to set a round number like $100B). Confirm historian verdict references $100B, not a different figure.

---

## Fix C — Approval trace logs not appearing in console

**Issue:** Four `[APPROVAL]` trace logs were added in fixes_17 to track the approval calculation sequence during EOT, but they never appear in the browser console — even in runs with active USA Tier 4 sanctions and approval collapsing to 0.

**Root cause:** Likely one of: (1) logs were added to a different code path than the one actually executing, (2) the function is being called but the logs are inside a conditional branch that isn't reached, or (3) the logs are in backend Python but the frontend console only shows frontend logs.

**Fix:**
- Locate `apply_end_of_turn_effects()` in turn_processor.py and confirm the four logs are present at the correct sequence points
- If they're in Python/backend: pipe them to the frontend EOT response object and render them as `console.log` calls in the React EOT handler, the same way other EOT logs surface
- The four required trace points:
  1. `[APPROVAL] Pre-sanctions: X%` (before USA sanctions block)
  2. `[APPROVAL] Post-sanctions: X%` (after USA sanctions)
  3. `[APPROVAL] Post-pressure: X%` (after Arabia embargo + EU pressure)
  4. `[APPROVAL] Final: X%` (after all passive changes)

**Verification:** Run a turn with USA relations below 20 (Tier 4 sanctions active). All four approval trace logs must appear in browser console during EOT.

---

## Fix D — Bill breaks character in intelligence intercepts

**Issue:** The first USA intelligence intercept produced a Claude refusal to roleplay as "the U.S. President" instead of Bill Hartwell's reaction. The NPC system prompt for intercept generation is incorrectly naming Bill as "the U.S. President" or a similar real-world title rather than his fictional character name.

**Root cause:** The intercept generation prompt in npc_engine.py or api.py is passing the wrong character descriptor for the USA NPC. Bill Hartwell is a fictional State Department official, not a real political figure.

**Fix:**
- In the intercept generation prompt, replace any reference to "U.S. President", "American President", or similar real-world political titles with "Bill Hartwell, US State Department Senior Advisor"
- Audit all four NPC intercept prompts to confirm none reference real-world political figures or titles
- The fictional framing (Europa, Europa's leader, Bill Hartwell) must be consistent throughout

**Console log to add:**
```
[INTERCEPT] Generating intercept for: {npc} as {character_name}
```

**Verification:** Trigger a USA intel intercept. Bill responds in character as Bill Hartwell without any refusal or meta-commentary.

---

## Fix E — Intelligence intercepts firing 3x per NPC per turn

**Issue:** Each NPC appears three times in the intel intercept block per turn. Every intercept should fire once per NPC per turn maximum.

**Root cause:** The intercept generation loop in turn_processor.py or api.py is likely iterating over a list (deals, events, or NPCs with some multiplier) and generating an intercept call per iteration rather than once per NPC.

**Fix:**
- Find the intercept generation loop
- Add a seen-NPCs set: once an NPC has had an intercept generated this turn, skip subsequent iterations for that NPC
- Or restructure to iterate over `unique_npcs` rather than `deals` or `events`

**Console log to add:**
```
[INTERCEPT] Turn X: generating intercepts for NPCs: [usa, arabia, eu, dprg]
[INTERCEPT] {npc} intercept generated (skipping duplicates)
```

**Verification:** Complete a turn with Intelligence L3+. Each NPC produces exactly one intercept card in the briefing, not three.

---

## FIXES_18 SUBMISSION PROMPT

```
Read worldstage_fixes_18.md.
Confirm the title "fixes_18" before proceeding.

Fix A: Counter-offer drops narrative condition from structured panel.
Fix B: Historian verdict reads wrong wealth variable.
Fix C: Approval trace logs not appearing in console.
Fix D: Bill breaks character in intel intercepts.
Fix E: Intel intercepts firing 3x per NPC per turn.

For Fix B: add the console.logs first, stop. Human will run a test 
to identify the exact wrong variable before you implement the correction.

For Fixes A, C, D, E: implement, add console.logs, stop.

Do not implement any other fix files.
Do not add new features.
Specify the exact file and function modified for each fix.
```

---

## VERIFICATION CHECKLIST

| Fix | Test | Pass condition |
|-----|------|----------------|
| A | Marsha negotiation to counter-offer | Structured panel shows both Arabia threshold AND narrative condition |
| B | Console log check before Turn 10 | `[HISTORIAN]` log shows correct personal_wealth value |
| C | Turn with USA Tier 4 sanctions | All 4 approval trace logs appear in browser console |
| D | Trigger USA intel intercept | Bill responds in character, no refusal |
| E | Turn with Intelligence L3+ | Each NPC produces exactly 1 intercept card |
