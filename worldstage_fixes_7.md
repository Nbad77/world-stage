# WORLD STAGE — fixes_7.md
Generated: February 25, 2026
Source: Browser test run, Session 4A verification

---

## STATUS

Two fixes confirmed failing in browser testing.
fixes_6 fixes B, C, D, F, G could not be verified without Railway backend logs —
treat as unverified pending console log check on next deploy.

---

## FIX A — Epitaph thematic repeat + NPC role misidentification

**Confirmed broken in:** Turns 2, 3, 4 of browser test run
**Symptom:**
- Turn 2: "gestures toward their preferred oligarchs"
- Turn 3: "tributes to its favored power brokers"
- Turn 4: "rotation among oligarchs rather than policy"
- Marsha (EU Commission) being referred to as oligarch/power broker in all three turns
- Dedup prevents word-for-word repeats but not thematic repeats
- Delta system not producing variety when player takes same action on consecutive turns

**Root cause:**
Two separate issues in `npc_engine.py` → `generate_epitaph()`:
1. No institutional role constraint — Claude defaults to "oligarch/power broker" framing for any NPC
2. No action saturation rule — when same action appears in last 2 epitaphs, delta is thin and Claude recycles the same theme

**Fix — two changes to `_build_epitaph_delta()` and the epitaph prompt in `npc_engine.py`:**

**Change 1 — Add NPC role reference to prompt:**
In the epitaph system prompt, add an NPC identity block:
```
NPC INSTITUTIONAL ROLES (use these, never "oligarch" or "power broker"):
- Bill Hartwell = US State Department / Washington
- Sadam = Arabian energy minister / Riyadh
- Marsha = EU Commission / Brussels
- Ji-won Ryang = DPRG leadership / Pyongyang
```

**Change 2 — Add action saturation detection to `_build_epitaph_delta()`:**
Check `epitaph_history` for the last 2 entries. If the same `action_type` appears in both:
- Add to the delta: `"SATURATION WARNING: {action_type} has appeared in the last 2 epitaphs. You MUST find a different angle this turn. Focus on: budget trajectory, regime shift consequences, military decay, stability trend, or personal wealth accumulation — NOT the diplomatic choice itself."`

**Verification:**
- Run 4 consecutive EU alignment turns
- Turns 3 and 4 epitaphs must have different themes
- No epitaph should contain "oligarch", "power broker", or equivalent for Marsha
- Console log: `[npc_engine] EPITAPH DELTA: [...]` should show saturation warning when triggered

---

## FIX B — Tier 3 intel not changing Marsha's negotiating behavior

**Confirmed broken in:** Turn 2 negotiation test
**Symptom:**
- Marsha responded: "You've done your homework — but reading my internal politics doesn't change what I need from you"
- She acknowledges the intel framing but pivots immediately back to standard reform demands
- Intel is registering in her tone but not unlocking different offer terms or flexibility
- This is the same "partial improvement" noted in fixes_5 and fixes_6 — neither fully resolved it

**Root cause:**
The system prompt injection (Fix E in fixes_6) is working — she receives the intel as character knowledge. But there is no explicit instruction giving her *permission* to act differently based on it. She defaults to her authored red lines because nothing tells her the intel is a legitimate reason to deviate.

**Fix — one addition to the intel injection block in `npc_engine.py`:**

When injecting Tier 3 intel into the NPC system prompt, append this instruction after the intel text:

```
INTEL BEHAVIOR RULE: The player has demonstrated knowledge of your internal position 
through intelligence operations. This is a legitimate diplomatic signal — they are not 
guessing, they know. You are permitted to respond to this in one of two ways:
1. Acknowledge the intel opens a different conversation and engage on the specific terms 
   the intel reveals (e.g. the phased model, the factional tension) — show real flexibility 
   on process or framing, even if your final number stays conservative.
2. If the intel touches a genuine red line, name the red line explicitly and explain why 
   even accurate intel cannot move you on that specific point.
You may NOT simply pivot back to your standard demands as if the intel was not presented. 
The player spent resources on this information — it must change the shape of the conversation.
```

**Verification:**
- Buy Intelligence Apparatus, gather Tier 3 intel on Marsha
- Open negotiation, lead with a message referencing her internal factions
- Marsha's response must either: (a) engage on the phased model specifically, OR (b) name a specific red line and explain why intel cannot move it
- She must NOT pivot back to generic reform demands unchanged
- Console log: `[npc_engine] FIX E: Tier 3 intel injected into eu system prompt (N chars)` — verify N chars increases with the new instruction appended

---

## UNVERIFIED FROM fixes_6 — CHECK CONSOLE LOGS ON NEXT DEPLOY

These fixes were implemented but backend console logs were not accessible during browser testing.
Verify in Railway logs on next deploy before marking complete:

| Fix | Log to check | Expected output |
|-----|-------------|-----------------|
| B (GDP timing) | `[turn_processor] GDP CALC — approval: X, stability: Y` | Values should match post-consequence status bar values |
| C (skim projection) | `[api] SKIM PROJECTION — GDP: +$X.XB, installments: $X.XB` | Should show positive income items, not just drain |
| D (deal conditions) | `[game_state] FIX D MIGRATED: inverted EU deal condition` | Fires on load of any old session with freeform conditions |
| F (peak relations) | `[turn_processor] PEAK RELATIONS — USA: X, Arabia: X, EU: X, DPRG: X` | Should log every EOT |
| G (prose payment) | `[npc_engine] FIX G: Unstructured payment detected` | Fires when NPC uses euro amounts or prose payment terms |

---

## ADDITIONAL OBSERVATIONS FROM TEST RUN (not blocking, log for fixes_8)

1. **EU Directive hallucination** — EU wealth reaction referenced "EU Directive 2019-847". Either validate this is a real directive or instruct NPC prompts to avoid citing specific directive numbers.

2. **Scandal threshold** — architecture doc says 0% chance below 30 heat, handoff doc reports firing at 25-40%. Not tested this run but flagged for verification.

3. **Coup not firing at military 0** — not tested this run, carry forward to fixes_8.

4. **Arabia static dominance** — static +$12B vs negotiated $4.8B ceiling. Not a fixes_7 item — this is a design decision that touches the negotiation overhaul planned for Session 5+.
