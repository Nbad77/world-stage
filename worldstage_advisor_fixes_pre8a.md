# WORLD STAGE — Advisor Fixes (Pre-8A)
Generated: March 2026

---

## CONTEXT

Small fixes to the advisor system before Session 8A begins.
Do not implement any Session 8 features.
Verify each fix in browser before proceeding to 8A.

---

## FIX 1 — Technocrat Haiku Prompt Voice

**Problem:** Technocrat analysis reads like a second Diplomat — referencing
diplomatic posture, NPC relations, and negotiating flexibility. Should be
focused on infrastructure, tech investment, education, and economic efficiency.

**Fix:** Update Technocrat system prompt in `npc_engine.py` →
`_ADVISOR_SYSTEM_PROMPTS['technocrat']`

The Technocrat should:
- Lead with infrastructure, tech level, education investment observations
- Frame everything through efficiency, ROI, and long-term economic returns
- Reference GDP multipliers, tech tier, spending allocation
- Be indifferent to diplomatic relationships except where they affect
  tech transfer or EU partnership access
- Never sound like he's assessing the geopolitical situation

Example voice: "Tech is at Tier 2 — the EU ceiling has opened to $5B but
we're leaving efficiency gains on the table without education investment.
Infrastructure allocation is underfunded relative to the GDP multiplier
it would unlock."

---

## FIX 2 — Militia Commander Haiku Prompt Voice

**Problem:** Militia Commander analysis references EU relations and diplomatic
concerns. Should be entirely focused on internal control, domestic threat
assessment, and suppression readiness. Explicitly indifferent to Western
relations — that's not his problem.

**Fix:** Update Militia Commander system prompt in `npc_engine.py` →
`_ADVISOR_SYSTEM_PROMPTS['militia_commander']`

The Militia Commander should:
- Lead with stability, approval gap, protest probability, brigade readiness
- Frame everything as an internal security assessment
- Be explicitly dismissive of diplomatic concerns
  ("The EU's opinion of our methods is not a tactical consideration")
- Reference heat level, suppression options, loyalty brigade status
- Never mention Western relations, EU deals, or diplomatic posture

Example voice: "Stability at 54 with approval at 63 — the gap is manageable
but the heat is climbing. One more ignored DPRG provocation and we're looking
at protest probability above threshold. Brigade is ready if you need it."

---

## FIX 3 — Cabinet Button Rename + Drawer Direction

**Problem A:** Button is labeled "SHADOW CABINET" — rename to "CABINET".
The shadow is implied by the dark aesthetic. Cleaner label.

**Problem B:** Cabinet drawer opens from the right side of the screen
but the button is on the left. Disorienting UX.

**Fix:** 
- Rename button label from "SHADOW CABINET" to "CABINET" in
  `LeftSidebar.jsx` or wherever the button renders
- Change drawer animation from slide-in-right to **slide-up from bottom**
  This matches the original roadmap spec ("slides up as a tray from the bottom"),
  works correctly on both desktop and mobile, and doesn't occlude NPC cards
  or the briefing panel
- On mobile this should use a bottom sheet pattern (already standard
  in the mobile layout per roadmap)

Files: `ShadowCabinet.jsx`, `LeftSidebar.jsx`, relevant CSS/transition classes

---

## FIX 4 — Advisor Hire and Assign Interaction Finickiness

**Problem:** Hiring and selecting advisors is reported as finicky —
likely a combination of small click target issues, state not updating
cleanly after hire, and assign/unassign toggle behaving unexpectedly.

**Investigate and fix:**

A) **Hire button state after hiring:**
After clicking HIRE, the advisor should immediately appear in the staff
roster and disappear from the hire pool without requiring a page refresh
or manual reload. If there's a stale state issue, ensure the pool
regenerates and roster updates in the same state update after hire.

B) **Assign toggle clarity:**
ASSIGN button should clearly show current state — if already assigned,
button should read "ASSIGNED" (or show a checkmark) and be clickable
to unassign. The current "ASSIGN" label doesn't communicate whether
the advisor is currently active today. Add visual distinction between
assigned and unassigned states.

C) **Slot counter update:**
"0/2 assigned today" counter should update immediately and correctly
when advisors are assigned or unassigned. If it's lagging behind state,
move it to derive directly from the assigned advisor count rather than
separate state.

D) **Click target size:**
ASSIGN, DISMISS (✕), and ELIMINATE (☠) buttons are small and close
together. If misclicks are happening between them, increase spacing or
add a confirmation step specifically for ELIMINATE (irreversible, $2B cost)
— confirm modal: "Eliminate {name}? This costs $2B and cannot be undone."

E) **Scroll behavior in hire pool:**
If the hire pool has 5+ eligible advisors, confirm the pool section
scrolls correctly and all advisors are reachable.

Console logs to add for debugging interaction issues:
```
[advisor] HIRE CLICKED: {archetype} — pool count before: {n}
[advisor] HIRE COMPLETE: {name} added to roster — pool count after: {n}
[advisor] ASSIGN TOGGLED: {name} ({archetype}) — now assigned={bool}
[advisor] SLOT COUNT: {n}/2 assigned today
```

---

## VERIFICATION STEPS

1. Assign Technocrat — confirm analysis references tech tier, infrastructure,
   GDP efficiency. No diplomatic language.
2. Assign Militia Commander — confirm analysis references stability, approval
   gap, brigade readiness, heat. No EU/Western relations language.
3. Rename confirmed: button shows "CABINET" not "SHADOW CABINET"
4. Open Cabinet — drawer slides up from bottom, not from right
5. Hire an advisor — confirm they appear in roster immediately without refresh,
   disappear from hire pool immediately
6. Assign an advisor — confirm ASSIGN button changes state visually,
   slot counter updates to 1/2 immediately
7. Assign a second advisor — slot counter updates to 2/2, third ASSIGN
   button is greyed out
8. Click ELIMINATE — confirm modal appears asking for confirmation before
   proceeding
9. With 5+ eligible advisors unlocked via cheat panel, confirm hire pool
   scrolls and all are accessible

---

## DO NOT IMPLEMENT

- Session 8A (Russia/China NPCs)
- Education system
- Exile sequence
- Any other Session 8 features
