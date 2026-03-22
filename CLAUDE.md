# CLAUDE.md — World Stage Project Instructions
# Claude Code reads this file at the start of every session.
# These instructions apply to ALL sessions unless explicitly overridden.

---

## GIT WORKFLOW — CRITICAL

**Never create new branches. Never use git worktrees.**

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

## TESTING PHILOSOPHY

- pytest: endings, math, state transitions, 3+ conditions simultaneously
- Comet: UI rendering, button visibility, modal open/close
- Manual: prose quality, NPC dialogue, game feel
- Any ending or complex condition → pytest first, never Comet
- Target baseline: 463 passing, 4 pre-existing failures (acceptable)
- Pre-existing failures: test_serialize_deserialize_advisors (x2),
  test_coup_fires_at_military_zero, test_no_contacts_when_conditions_not_met
- Pre-existing collection errors: test_advisors.py, test_session4d.py

---

## DO NOT TOUCH (unless the session explicitly targets these)

- The EOT flow and turn resolution sequence in GameScreen.jsx
- The double-confirm fix: `await _executeSkim(1)` in GameScreen.jsx
- The Anthropic client instantiation pattern in npc_engine.py
- Any ending condition logic unless explicitly in scope
- The exile system, biography system
- ShadowCabinet.jsx shadow axis tiers (already implemented)

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

---

## TEMP FILES

Do not create temporary files at the C: root or anywhere outside
the project directory. If you need temp files, use the project
directory. Clean up temp files before committing.

---

## CURRENT STATE (as of March 2026)

Sessions complete: 1-9C, 9.5A through 9.5G, 10A, 10C
Test count: 463 passing, 4 pre-existing failures
Last commit: e1b1a30

Key systems implemented:
- 10-tier commitment model (9.5A)
- Shadow State axes: Media, Judicial, Surveillance, Extraction, Militia (9.5A-Shadow)
- Two-component stability: legitimacy + coercion (9.5B)
- Loyal Generals / Loyal Intel Chief (9.5C)
- Diplomatic effectiveness: soft power, reliability, standing (9.5D)
- Resource policy, bond market, Volkov trap, client states (9.5E)
- Peacekeeping + intervention conditions (9.5F)
- Era system, historian on-demand, open world (10A)
- Operations redesign: 23 operations across 4 categories (10C)

Next session: 10B-1 (Daily Briefing Screen + GM World Events)
