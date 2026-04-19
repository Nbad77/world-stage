# CLAUDE.md — World Stage Project Instructions
# Claude Code reads this file at the start of every session.
# These instructions apply to ALL sessions unless explicitly overridden.

---

## GIT WORKFLOW — CRITICAL

**Never create new branches. Never use git worktrees.**

Never run `git reset --hard` when uncommitted changes
exist in the working tree. Always run `git status` first.
Uncommitted changes are silently and permanently lost.

Always commit directly to main:
```
git add -A
git commit -m "descriptive message"
git push origin HEAD:main
```

`git push origin HEAD:main` works correctly from any branch or
worktree — always use this form, never `git push origin main`.

At the start of every session, confirm you are on main:
```
git status
git log --oneline -3
```

At the end of every session, after all verification passes:
```
git add -A
git commit -m "Session X complete — N passing tests"
git push origin HEAD:main
```

Report the commit hash. Never end a session without pushing.

---

## PROJECT OVERVIEW

World Stage is a geopolitical narrative simulation game.
Player leads the fictional nation of Europa.
Not win/lose — a narrative generator for political biographies.
Theme: loneliness of power.

**Stack:**
- Backend: FastAPI (Python) on Railway
- Frontend: React on Vercel (world-stage.vercel.app)
- Database: PostgreSQL (Railway)
- AI: Claude Haiku for NPC dialogue
- Local dev: `python -m uvicorn api:app --reload --port 8000`
- Frontend: double-click START_WEB.bat (do not use npm run dev in PowerShell)

---

## PERFORMANCE — NEVER REVERT THESE

**Anthropic client (npc_engine.py):**
Single module-level instance. NEVER revert to per-function instantiation.
Per-function instantiation caused 70-second turns.
```python
_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=30.0,
    max_retries=0
)
```

**Parallel NPC calls:**
generate_dialogue() uses ThreadPoolExecutor for parallel Haiku calls.
_token_log writes protected by _token_log_lock.
Do NOT add shared gs writes to _call_npc() without lock protection.

**Skim flow:**
The pre-EOT skim prompt is REMOVED. Skim is a persistent slider
in the Shadow Cabinet. The /skim endpoint is called automatically
with choice 1 — no per-turn prompt. Never restore the skim prompt.

**The missing await is always the bug.**
Check all fire-and-forget async calls before reporting complete.
`await _executeSkim(1)` not `_executeSkim(1)`.

---

## ARCHITECTURE RULES

- Shadow upgrades: POST /shadow/upgrade (NOT /cabinet_invest)
- Shadow parameter: shadow_key (NOT tier_key)
- deal_total_value is canonical (NOT deal_budget)
- POWER BASE reads from gs.media_tier etc. (NOT gs.cabinet_axes)
- game_over field does NOT exist — use ending_triggered (str or None)
- Endings fire on state conditions only — no turn count gates
- max_turns is deprecated (set to 9999) — game_over flag drives endings

---

## ADDITIONAL ARCHITECTURE INVARIANTS

**NPC ID key convention (critical):**
All dicts keyed by npc_id use character-name
keys: bill, eu, sadam, dprg, volkov, wei.
Relations keys (usa, arabia, russia, china)
are different. Mixing causes silent fallthrough.
See WorldStage_ClaudeCode_Reference.md for
the full mapping table.

**cabinet_axes vs display tiers:**
cabinet_axes['military'] gates advisor unlocks
and regime calculations.
military_tier / mil_tier is the display/decay
stat shown in the UI.
These are completely separate fields.
Never conflate them.

**Fence stripping — required before json.loads():**
ALL Haiku JSON responses must be stripped
before parsing. Canonical pattern:
  cleaned = raw.strip()
  if cleaned.startswith('```'):
      cleaned = cleaned.split('\n', 1)[-1]
  if cleaned.endswith('```'):
      cleaned = cleaned.rsplit('```', 1)[0]
  cleaned = cleaned.strip()
  result = json.loads(cleaned)
Never call json.loads() directly on a raw
Haiku response.

**diplomatic_standing is ABSENT:**
Confirmed absent by grep. Do not assume
this field exists. Do not write code that
references it without first confirming it
has been implemented.

**Advisory council state lives in GameScreen:**
chiefOfStaff, advisorBriefings, briefingFetchedDay,
advisorProfileCache, poolProfileCache,
availableAdvisors, morningBriefingLoading
are all lifted to GameScreen and passed as
props to BriefingScreen. Do not re-add local
useState declarations for these in BriefingScreen.

**Stable advisor pool:**
generate_advisor_pool() reuses existing pool
entries by archetype. Only creates new advisor
objects when an archetype first becomes eligible.
Do not revert to always-create pattern.

**Reload-and-patch pattern:**
Always reload gs_fresh before saving.
Only write fields the endpoint owns.
Never save a full gs if another endpoint
writes it concurrently.

**eot_data try/except:**
EOT data construction is wrapped in try/except
with silent null fallback. Do not remove.

**Budget sign convention:**
Negative = Europa pays. Positive = Europa receives.
Applies to all budget_delta fields.

---

## TESTING PHILOSOPHY

- pytest: endings, math, state transitions, 3+ conditions simultaneously
- Comet: UI rendering, button visibility, modal open/close
- Manual: prose quality, NPC dialogue, game feel
- Any ending or complex condition → pytest first, never Comet
- Target baseline: confirm current count with
  pytest before each session. Pre-existing
  failures are acceptable if present before
  your changes.

---

## DO NOT TOUCH (unless the session explicitly targets these)

- The EOT flow and turn resolution sequence in GameScreen.jsx
- The double-confirm fix: `await _executeSkim(1)` in GameScreen.jsx
- The Anthropic client instantiation pattern in npc_engine.py
- Any ending condition logic unless explicitly in scope
- The exile system, biography system
- ShadowCabinet.jsx shadow axis tiers (already implemented)
- Advisory council state lift in GameScreen.jsx
  (chiefOfStaff, advisorBriefings, and related
  lifted state — do not move back to BriefingScreen)
- lastDayRef, poolFetchedDayRef, morningBriefingInFlight
  ref initialization patterns in BriefingScreen.jsx
- generate_deal_consequences_and_reactions()
  combined call — existing separate functions
  are fallbacks only
- turn_dialogues cache in game_state — cached
  per {npc_id}_{turn}, never bypass

---

## DIAGNOSTIC DISCIPLINE

Before fixing anything:
1. Read the relevant files in full
2. Run pytest and report the summary line
3. Report the specific lines that need changing
4. Wait for go-ahead before making changes

Never fix what you don't understand.
Never fix things outside the stated scope.
If you find a bug while reading, note it — do not fix it.

Before marking any task complete,
cross-reference your changes against
the Architecture Notes and Console Log
Contracts in the session's handoff
document. Flag any field name, key
format, or ordering constraint that
your implementation might violate.

---

## TEMP FILES

Do not create temporary files at the C: root or anywhere outside
the project directory. If you need temp files, use the project
directory. Clean up temp files before committing.

