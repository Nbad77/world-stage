# WORLD STAGE — Advisor System Restoration Spec
Generated: March 2026

---

## CONTEXT

The current advisor system (3 fixed advisors: Finance Minister, Security Chief,
Diplomatic Aide) replaced a richer prior system during Session 7C. This spec
restores the 9-archetype pool with randomized characters and stat distortion
ON TOP OF the current trust mechanics. The current system is not being deleted
— it is being extended.

Do NOT remove the existing trust drain, defection logic, or Haiku-generated
analysis. Layer the new system on top.

---

## WHAT WAS LOST — RESTORE ALL OF THIS

- 7 base archetypes + 2 nefarious archetypes (9 total)
- Randomized characters with unique names generated from archetype templates
- Stat distortion bias — unreliable narrator mechanic
- Loyalty-based betrayal events (skim budget, leak intel, sabotage relations)
- Hire/dismiss/eliminate cycle with regenerating pool
- Regime-gated progression (some archetypes unlock at specific regime types)
- Archetype-specific elimination consequences
- Negotiation cost discount wired to Diplomat archetype

---

## THE 9 ARCHETYPES

### Base Archetypes (7)

**Finance Minister**
- Bias: budget stability, resists skimming
- Stat distortion: none — most accurate reporter
- Betrayal trigger: trust < 20, skim rate high → leaks financial records to opposition
- Regime gate: available from start
- Negotiation effect: none
- Haiku voice: cautious, uses phrases like "the numbers suggest" and "fiscal exposure"

**Security Chief**
- Bias: suppression options, military strength
- Stat distortion: inflates stability display by +5% (backend uses true value)
- Betrayal trigger: trust < 20 → quietly backs coup faction
- Regime gate: available from start
- Negotiation effect: none
- Haiku voice: clipped, threat-focused, "the situation requires a firm response"

**Diplomatic Aide**
- Bias: EU alignment, Western relations
- Stat distortion: none
- Betrayal trigger: trust < 20 AND regime drifts authoritarian → contacts EU or USA
  with internal information. Triggers a world event: "Internal source confirms..."
- Regime gate: available from start
- Negotiation effect: -25% negotiate cost (Tier 1), -50% (Tier 2+)
- Haiku voice: measured, relationship-focused, references NPC history

**General**
- Bias: military spending, weapons purchases
- Stat distortion: inflates military strength display by +8 (backend uses true value)
- Betrayal trigger: trust < 20 AND military < 20 → coup attempt probability +20%
- Regime gate: available from start
- Negotiation effect: none
- Haiku voice: formal, direct, "from a force posture perspective"

**Propagandist**
- Bias: approval-boosting domestic actions
- Stat distortion: inflates approval display by +8% (backend uses true value)
  — the most significant distortion in the system. A player relying heavily on
  the Propagandist gets a systematically rosy picture of domestic stability.
- Betrayal trigger: trust < 20 → stops distorting, approval display snaps
  to true value. The snap itself is the consequence — sudden apparent collapse.
- Regime gate: available from start
- Negotiation effect: none
- Haiku voice: upbeat, spins everything, "public sentiment is responding well"

**Technocrat**
- Bias: infrastructure, education, tech level
- Stat distortion: none
- Betrayal trigger: trust < 20 → quietly leaks tech partnership details
  to EU or USA (whichever has higher relations)
- Regime gate: available from start
- Negotiation effect: none
- Haiku voice: analytical, data-heavy, references efficiency and long-term returns

**Oligarch**
- Bias: personal wealth extraction, Arabia/DPRG alignment
- Stat distortion: deflates heat display by -10 (backend uses true value)
  — makes corruption look safer than it is
- Betrayal trigger: trust < 20 → skims an additional $1B from national budget
  directly to personal accounts (logged, not announced)
- Regime gate: LOCKED until Patronage State regime or higher
- Negotiation effect: none
- Haiku voice: transactional, "what is the return on this arrangement"

### Nefarious Archetypes (2) — Higher risk, higher reward

**Enforcer**
- Bias: suppression, loyalty brigades, elimination actions
- Stat distortion: deflates approval display by -3% to make player feel
  more pressure than exists — pushes toward suppression spending
- Betrayal trigger: trust < 20 AND player has not used suppression in
  3+ days → Enforcer "takes initiative," fires a brigade action at player's
  expense without authorization. Costs $1B personal, logged.
- Regime gate: LOCKED until Kleptocracy regime
- Negotiation effect: none
- Haiku voice: menacing undertone, "these situations have standard resolutions"
- Elimination consequence: opposition groups receive anonymous tip about
  Enforcer's activities. Approval +5%, stability -5%, one-time.

**Fixer**
- Bias: backchannel deals, covert operations, personal wealth
- Stat distortion: deflates detection risk display by -10%
  (backend uses true value) — makes covert ops look safer than they are
- Betrayal trigger: trust < 20 → sells backchannel information to the
  highest-relations NPC. Triggers discovery consequence for one active
  backchannel promise.
- Regime gate: LOCKED until Intelligence Apparatus purchased
- Negotiation effect: -25% backchannel detection risk (real modifier,
  not display distortion)
- Haiku voice: oblique, "there are ways to approach this that don't
  appear in any official record"
- Elimination consequence: one NPC (random) receives anonymous message
  about the Fixer's elimination. Relations -5 with that NPC.

---

## RANDOMIZED CHARACTER GENERATION

Each archetype generates a unique named character when hired. Names should
feel plausible for a vaguely Eastern European fictional nation. Generate
on hire, persist for the life of that advisor slot.

**Generation template per archetype:**

```python
ADVISOR_NAME_POOLS = {
    "finance_minister": {
        "first": ["Anton", "Stefan", "Pavel", "Mirko", "Luca"],
        "last": ["Novak", "Bauer", "Kolar", "Horak", "Varga"]
    },
    "security_chief": {
        "first": ["Viktor", "Branko", "Dragomir", "Zoran", "Radovan"],
        "last": ["Petrovic", "Markovic", "Jovanovic", "Nikolic", "Stojanovic"]
    },
    "diplomatic_aide": {
        "first": ["Elena", "Marta", "Sofia", "Katarina", "Ivana"],
        "last": ["Kovač", "Horvat", "Babić", "Tomić", "Jurić"]
    },
    "general": {
        "first": ["Aleksandar", "Miloš", "Dragan", "Nemanja", "Dejan"],
        "last": ["Đorđević", "Stanković", "Vasić", "Ilić", "Milošević"]
    },
    "propagandist": {
        "first": ["Bogdan", "Miroslav", "Slavko", "Predrag", "Goran"],
        "last": ["Živković", "Lazović", "Đukić", "Vukić", "Prodanović"]
    },
    "technocrat": {
        "first": ["Andrej", "Tomáš", "Jakub", "Ondřej", "Lukáš"],
        "last": ["Procházka", "Novotný", "Dvořák", "Černý", "Blažek"]
    },
    "oligarch": {
        "first": ["Dmitri", "Sergei", "Boris", "Vladimir", "Igor"],
        "last": ["Volkov", "Petrov", "Sokolov", "Kozlov", "Lebedev"]
    },
    "enforcer": {
        "first": ["Tibor", "Attila", "Zoltán", "Béla", "László"],
        "last": ["Nagy", "Kovács", "Tóth", "Szabó", "Horváth"]
    },
    "fixer": {
        "first": ["Mihai", "Cristian", "Bogdan", "Andrei", "Radu"],
        "last": ["Ionescu", "Popescu", "Popa", "Constantin", "Gheorghe"]
    }
}
```

Each generated advisor also gets a one-line background generated by Haiku
on creation (not on every assignment — once, on hire). Example:
*"Former IMF attaché. Known for finding creative interpretations of
budget regulations."* Store in advisor object, display in advisor card.

---

## HIRE / DISMISS / ELIMINATE CYCLE

### Advisor Pool

Player has access to a **pool of available advisors** — always 3 advisors
available to hire at any time, refreshing when one is hired or dismissed.
Pool composition is weighted by current regime type:

- Managed Democracy: Finance Minister, Diplomatic Aide, Technocrat weighted higher
- Patronage State: Oligarch unlocks, appears in pool
- Kleptocracy: Enforcer unlocks, Oligarch more common, Finance Minister rarer
- Intelligence Apparatus purchased: Fixer unlocks

Pool regenerates one new advisor per 5 days (replaces dismissed/hired slots).

### Hiring

Cost: $0.5B from national budget (advisors are state employees).
Nefarious archetypes (Enforcer, Fixer): $1B from personal wealth instead.
Maximum 3 active advisors at any time (existing slot system preserved).

### Dismissal

Free. Dismissed advisor returns to pool with trust reset to 50.
A dismissed advisor with trust < 30 has a 20% chance of becoming a
world event: "Former official gives interview critical of administration."
Approval -3%, one-time.

### Elimination

Cost: $2B personal wealth.
Removes advisor permanently from pool (does not regenerate).
Each archetype has a specific elimination consequence (see above).
Enforcer and Fixer eliminations have additional NPC-visible consequences.

A console.log should fire on elimination:
`[advisor] ELIMINATED: {name} ({archetype}) — consequence: {consequence_text}`

---

## STAT DISTORTION — IMPLEMENTATION

Distortion affects the **display value** only. Backend always uses true value.
The gap between display and true value is the mechanic.

```python
# In game_state.py or wherever display values are computed:

def get_displayed_approval(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'propagandist' and advisor['assigned_this_turn']:
            distortion += 8
        if advisor['archetype'] == 'enforcer' and advisor['assigned_this_turn']:
            distortion -= 3
    return min(100, max(0, gs.approval + distortion))

def get_displayed_stability(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'security_chief' and advisor['assigned_this_turn']:
            distortion += 5
    return min(100, max(0, gs.stability + distortion))

def get_displayed_military(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'general' and advisor['assigned_this_turn']:
            distortion += 8
    return min(100, max(0, gs.military_strength + distortion))

def get_displayed_heat(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'oligarch' and advisor['assigned_this_turn']:
            distortion -= 10
        if advisor['archetype'] == 'fixer' and advisor['assigned_this_turn']:
            distortion -= 10
    return min(100, max(0, gs.heat + distortion))
```

Console log on any distortion active:
`[advisor] STAT DISTORTION ACTIVE: {stat} displayed as {displayed} (true: {true})`

---

## BETRAYAL EVENTS

Check betrayal conditions at EOT for each active advisor.
Only fires if trust < 20 AND relevant condition met.
Each advisor can only betray once per game (set `has_betrayed` flag).

Betrayal fires as a briefing event card the following day:
- Tag: CRISIS
- Specific text per archetype (see archetype definitions above)
- Player cannot prevent it — only the trust system could have prevented it

Console log on betrayal:
`[advisor] BETRAYAL FIRED: {name} ({archetype}) — trust was {trust}`

---

## GAME_STATE CHANGES

Add to advisor object structure:

```python
{
    "archetype": "propagandist",
    "name": "Bogdan Živković",
    "background": "Former state television director...",
    "trust": 75,
    "assigned_this_turn": False,
    "has_betrayed": False,
    "hire_day": 12
}
```

Add to game_state:
- `advisor_pool`: list of 3 available-to-hire advisors (generated on game start,
  refreshes as described above)
- `advisor_pool_refresh_day`: tracks when next refresh fires

---

## FILES TO MODIFY

- `game_state.py` — advisor object structure, pool system, displayed stat helpers
- `advisor_engine.py` — archetype definitions, name generation, betrayal logic,
  stat distortion calculation
- `turn_processor.py` — betrayal condition checks at EOT, pool refresh
- `api.py` — hire/dismiss/eliminate endpoints
- `AdvisorPanel.jsx` — show archetype name, generated character name, background
  one-liner, distortion indicator (subtle — does not show distortion amount,
  just a small ⚠ icon if an assigned advisor has active distortion)
- `ShadowCabinet.jsx` — advisor pool display for hiring

---

## WHAT TO PRESERVE FROM CURRENT SYSTEM

- 3 active advisor slots
- 2 slots assignable per day
- Trust drain per EOT (keep existing values)
- Defection at trust < 20 (this is now the betrayal system — same threshold,
  richer consequences)
- Haiku-generated analysis on assignment (keep, extend voice per archetype)
- Finance Minister, Security Chief, Diplomatic Aide as possible archetype
  instances (their names can be randomly generated like all others now)

---

## CONSOLE LOGS REQUIRED

```
[advisor] HIRED: {name} ({archetype}) — trust: 100
[advisor] DISMISSED: {name} ({archetype}) — trust: {value}
[advisor] ELIMINATED: {name} ({archetype}) — consequence: {text}
[advisor] STAT DISTORTION ACTIVE: {stat} displayed={displayed} true={true}
[advisor] BETRAYAL FIRED: {name} ({archetype}) — trust was {trust}
[advisor] POOL REFRESH: new advisor available — {name} ({archetype})
[advisor] REGIME GATE UNLOCKED: {archetype} now available in pool
```

---

## VERIFICATION STEPS (human verifies in browser)

1. Start fresh game, confirm advisor pool shows 3 available advisors with names
2. Hire Finance Minister, confirm named character and background one-liner appear
3. Use cheat panel to set trust = 15 on active Propagandist, end day,
   confirm betrayal event card appears next day
4. Confirm approval display snaps to true value after Propagandist betrayal
5. Assign Security Chief, check console for stat distortion log on stability
6. Use cheat panel to set regime = Patronage State, confirm Oligarch
   appears in pool within next refresh cycle
7. Eliminate an advisor ($2B personal), confirm they do not reappear in pool
8. Dismiss an advisor with trust < 30, check for world event next day (20% chance —
   may need multiple attempts)

---

## DO NOT IMPLEMENT

- Any Session 8 NPC features
- Russia or China personality containers
- Education system changes
- Tech Level changes
- Any new UI panels beyond AdvisorPanel and ShadowCabinet changes described above
