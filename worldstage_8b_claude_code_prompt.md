# WORLD STAGE — 8B CLAUDE CODE PROMPT
# Education System

---

## FIRST ACTION

Read the file at: `/mnt/user-data/outputs/worldstage_8b_claude_code_prompt.md`

Confirm the title "8B — Education System" and begin writing code immediately.

DO NOT produce a plan, summary, or review first.
DO NOT restate what you've read.
DO NOT output any checklist before coding.
Start with game_state.py. Nothing else first.

---

## CONTEXT

Education is a new long-term investment axis. It lives in the Domestic
Affairs tab as a budget line item. Higher allocation = faster progression
toward the next level. Underfunding triggers decay. Effects compound across
GDP, tech absorption, stability, approval dynamics, and NPC behavior.

This is a tunable system — the gain rate is a named constant, not a magic
number buried in logic.

---

## SCOPE BOUNDARY

IN SCOPE: Everything listed in this prompt.
OUT OF SCOPE: 8C (Exile), 8D (The Leak), 8E (UI), 8F (GM Inference),
any new NPC personalities, any changes to Russia/China systems.

---

## FILE 1: game_state.py

Add these fields to GameState.__init__():

```python
self.education_level = 0          # 0-3 (Underdeveloped/Basic/Developed/Advanced)
self.education_allocation = 0.0   # $B/turn allocated from national budget
self.education_decay_clock = 0    # days below maintenance threshold (max 5 before decay)
self.education_gain_progress = 0.0  # fractional progress toward next level (resets on level-up)
```

Add to serialize() and deserialize() with appropriate defaults on
deserialize (all 0 if missing — safe for pre-8B saves).

---

## FILE 2: turn_processor.py

### Constants (define at top of file, clearly labeled as tunable)

```python
# EDUCATION SYSTEM — tunable constants
# Target: EU-aligned heavy investor reaches Level 2 in 2-3 eras, Level 3 in 5-6 eras
BASE_EDUCATION_RATE = 0.15

EDUCATION_MAINTENANCE = {1: 0.5, 2: 1.0, 3: 1.5}  # $B/turn minimum per level
EDUCATION_DECAY_GRACE = 5   # days below maintenance before level drops
EDUCATION_LEVEL_NAMES = {
    0: 'Underdeveloped',
    1: 'Basic',
    2: 'Developed',
    3: 'Advanced'
}
```

### Education gain/decay logic (runs each EOD in the education processing block)

**Gain logic:**
- If education_allocation >= maintenance threshold for current level (or level 0):
  - gain = education_allocation × BASE_EDUCATION_RATE
  - education_gain_progress += gain
  - Reset education_decay_clock to 0
  - If education_gain_progress >= 1.0 AND education_level < 3:
    - education_level += 1
    - education_gain_progress = 0.0
    - Log: `[education] Level up: {old} → {new} (Level {level})`

**Decay logic:**
- If education_allocation < EDUCATION_MAINTENANCE.get(education_level, 0):
  - education_decay_clock += 1
  - Log: `[education] Decay clock: {clock}/{EDUCATION_DECAY_GRACE} days`
  - If education_decay_clock >= EDUCATION_DECAY_GRACE AND education_level > 0:
    - education_level -= 1
    - education_decay_clock = 0
    - education_gain_progress = 0.0
    - Log: `[education] Level decay: dropped to Level {education_level}`

### GDP modifier from education (apply in section 9b alongside tech modifier)

```python
EDUCATION_GDP_MODIFIERS = {0: 0.0, 1: 0.05, 2: 0.12, 3: 0.20}

education_gdp_modifier = EDUCATION_GDP_MODIFIERS[gs.education_level]
# Apply to GDP baseline revenue alongside existing tech modifier
```

Log: `[education] GDP modifier: +{pct}% (Level {level})`

### Tax base modifier

```python
EDUCATION_TAX_MODIFIERS = {0: 0.0, 1: 0.03, 2: 0.08, 3: 0.15}
```

Apply as multiplier to national budget revenue.

### Stability modifier

```python
EDUCATION_STABILITY_MODIFIERS = {0: 0, 1: 3, 2: 7, 3: 10}
```

Add as flat bonus to stability calculation (same section as other
stability modifiers).

### Approval floor

```python
EDUCATION_APPROVAL_FLOORS = {0: 0, 1: 2, 2: 5, 3: 8}
```

Apply as minimum floor — approval cannot drop below this value
purely from education (other mechanics can still push it lower
via suppression, scandals, etc.).

### Approval sensitivity (Level 2 and 3 only)

Level 2: negative approval events (suppression, scandal, election
manipulation) hit approval × 1.15 instead of × 1.0

Level 3: negative approval events hit × 1.25. Suppression actions
cost +5% additional approval loss. Corruption scandals hit +10%
harder.

### Coup resistance bonus

```python
EDUCATION_COUP_RESISTANCE = {0: 0, 1: 0, 2: 10, 3: 20}
```

Apply as percentage reduction to coup probability calculation.

### Brain drain check (Level 3 only, runs each EOD)

If education_level == 3 AND approval < 30:
  - GDP modifier degrades by additional -5% (stacks with base modifier,
    so effective modifier at Level 3 with brain drain = +15% not +20%)
  - Log: `[education] BRAIN DRAIN ACTIVE: approval {approval}% below 30 threshold`
  - Add flag to EOD summary so player sees it in briefing

Brain drain recovers automatically when approval returns to 30+.

### Propagandist distortion reduction

When calculating Propagandist advisor stat distortion, apply:
  Level 0-1: full distortion (no change)
  Level 2: distortion × 0.5
  Level 3: distortion × 0.2

This should be applied wherever Propagandist distortion is calculated
in advisor_engine.py or turn_processor.py.

Log: `[education] Propagandist distortion reduced: level={level} multiplier={mult}`

---

## FILE 3: npc_engine.py

Inject education_level into system prompt context for Marsha, Bill,
and Wei. Use it to conditionally modify their behavior:

**Marsha:**
- Level 0 at EU relations 60+: append to her system prompt:
  "You are adding human capital development benchmarks as conditions
  on any deals this turn."
- Level 1+: EU education partnership deal is available in her pool
  (EU funds education investment — creates EU framework dependency).
  Add this as a deal option in her negotiation context.
- Level 2+: append to system prompt: "Europa's social investment record
  gives you something to defend to EU member states. Your tone is
  slightly warmer."
- Level 3: EU ceiling +$1B on top of tech tier ceiling.
  Marsha references education in communiqués explicitly.

**Bill:**
- Level 2+: passive rapport +1 per era (add to era-start rapport bonus).
- Level 0 + suppression actions active: append to Bill's system prompt:
  "You have flagged Europa's education underdevelopment alongside its
  suppression record as a long-term instability signal."

**Wei:**
- Level 0-1: education infrastructure deal available in his pool
  (universities, technical schools — Belt and Road framing).
- Level 2+: remove education infrastructure deal from his pool.
  Append to Wei's system prompt: "You have closed the education
  partnership door — Europa no longer needs your help here. Your
  deal focus shifts to tech and market access."
- Level 3: append to Wei's system prompt: "An educated population
  is more resistant to external cultural influence. Your communiqués
  are marginally more formal."

**Volkov:**
- Does not respond to education level.
- If education_allocation is being funded by an EU partnership deal:
  append to Volkov's system prompt: "You have noted that Europa's
  education programs have European funding. This is a mild irritant
  you may reference obliquely."

---

## FILE 4: DomesticTab.jsx

Add education as a spending row in the Domestic Affairs tab. It should
appear after existing spending categories and before the social contract
section.

Row structure:
- Label: "Education" with current level name in muted text
  (e.g., "Education — Developed")
- Allocation slider: same style as other domestic spending sliders
- Dollar amount input field alongside slider (same as other categories)
- Level progress indicator: small progress bar showing fractional
  progress toward next level (0.0–1.0)
- Decay warning: if allocation < maintenance threshold, show:
  "⚠ Below maintenance — decay in {5 - decay_clock} days"
  in amber text

Level names displayed in the row header:
  0 → "Underdeveloped"
  1 → "Basic"
  2 → "Developed"
  3 → "Advanced"

Brain drain indicator: if Level 3 and approval < 30, show a red
warning: "⚠ Brain drain active — approval below 30%"

---

## FILE 5: LeftSidebar.jsx

Add a compact education level indicator near the tech tier display.
Format: "EDU: Basic" or "EDU: Level 2" — whatever reads cleanest
alongside the existing tech display. Use muted text at Level 0,
normal text at Level 1-2, highlighted text at Level 3.

---

## CONSOLE LOGS REQUIRED

```
[education] Level up: {old_name} → {new_name} (Level {level})
[education] Decay clock: {clock}/{grace} days (level={level})
[education] Level decay: dropped to Level {level}
[education] GDP modifier: +{pct}% (Level {level})
[education] Propagandist distortion reduced: level={level} multiplier={mult}
[education] BRAIN DRAIN ACTIVE: approval {pct}% below 30 threshold
```

---

## VERIFICATION STEPS (human verifies in browser)

1. Open Domestic Affairs tab → Education row appears with "Underdeveloped"
   label, slider at 0, no decay warning

2. Set education allocation to $1.0B/day via cheat panel or slider →
   confirm gain progress ticks each day in console

3. Use cheat panel to set education_level = 1 → confirm "Basic" label
   appears in Domestic tab and LeftSidebar, GDP modifier log shows +5%

4. Set education_level = 2 → confirm "Developed", GDP +12%, Propagandist
   distortion log shows 0.5× multiplier

5. Set education_level = 3 → confirm "Advanced", GDP +20%, brain drain
   warning fires when approval set below 30 via cheat panel

6. Set allocation below maintenance threshold → decay warning appears
   in Domestic tab, decay clock increments each day in console,
   level drops after 5 days

7. Negotiate with Marsha at education_level = 0, EU 65+ → confirm her
   communiqué references education benchmarks

8. Negotiate with Wei at education_level = 0 → confirm education
   infrastructure deal appears in his pool

9. Set education_level = 2 then open Wei negotiation → confirm
   education deal is gone from his pool

10. Load a pre-8B save → no crash, all education fields initialize
    to 0 safely
