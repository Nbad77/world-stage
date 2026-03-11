# WORLD STAGE — Advisor System Full Spec (Revised)
Generated: March 2026

---

## CONTEXT

Restores the full 9-archetype advisor system on top of the current 7C trust
mechanics. Does not replace trust drain or defection logic — layers the full
system underneath it.

Security Chief is replaced by Militia Commander (distinct role, new gate).
General and Propagandist are now gated (were always-available in prior spec).
Spy Chief gets an intel cost discount mechanic (mirrors Diplomat's negotiation
discount). Fixer is gated at Political axis 4+. Oligarch gets a personal
wealth extraction passive.

---

## THE 9 ARCHETYPES

| Archetype | Specialty | Competence | Loyalty | Passive Bias | Unlock Gate |
|-----------|-----------|------------|---------|--------------|-------------|
| Finance Minister 💵 | Economic | 55–85 | 45–75 | None | Always |
| Technocrat 📊 | Economic | 60–90 | 50–80 | None | Always |
| Diplomat 🤝 | Diplomatic | 55–80 | 60–90 | None | Always |
| General ⚔️ | Military | 50–85 | 40–75 | Military strength +5 to +15 | Military axis ≥ 4 |
| Propagandist 📺 | Domestic | 40–70 | 50–85 | Approval display +5 to +15 | Soft Authoritarianism+ |
| Militia Commander 🔒 | Domestic | 45–75 | 40–70 | Stability display +5 to +10 | Soft Authoritarianism+ |
| Spy Chief 🕵️ | Intelligence | 70–95 | 30–70 | Heat display -5 to -10 | Intel axis ≥ 4 |
| Oligarch 💰 | Economic | 50–75 | 20–50 | Budget display +3 to +8 | Patronage State+ |
| Fixer 🎭 | Intelligence | 75–95 | 10–40 | Heat display -8 to -15 | Political axis ≥ 4 |

---

## ARCHETYPE DETAILS

### Finance Minister 💵
- **Bias:** Budget stability, resists skimming, flags fiscal exposure
- **Stat distortion:** None — most accurate reporter in the cabinet
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** None beyond analysis quality
- **Betrayal trigger (loyalty < 20):** Skims from national budget → +$1B personal
  (his personal, not yours), logged as unexplained budget shortfall
- **Elimination consequence:** None external — deniable
- **Voice:** Cautious, precise. "The numbers suggest fiscal exposure here."
  "This skim rate is not sustainable at current stability levels."

---

### Technocrat 📊
- **Bias:** Infrastructure, education, tech level investment
- **Stat distortion:** None
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** When assigned, EU tech partnership deals available at
  slightly lower rapport threshold (-1 rapport required)
- **Betrayal trigger (loyalty < 20):** Quietly leaks tech partnership details
  to whichever NPC has highest current relations → that NPC gains intel
  on Europa's tech investments. Relations hit -5 with the NPC who was
  disadvantaged by the leak.
- **Elimination consequence:** EU -3 (loses a reformist signal)
- **Voice:** Analytical, references efficiency and long-term returns.
  "The infrastructure ROI on this option is significantly better over 5 turns."

---

### Diplomat 🤝
- **Bias:** EU alignment, Western relations, deal quality
- **Stat distortion:** None
- **Negotiation effect:** Competence ≥ 80: negotiations free.
  Competence < 80: 50% discount on negotiate cost.
  Wired into `_get_discounted_negotiate_cost()` in api.py.
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** None beyond negotiation discount
- **Betrayal trigger (loyalty < 20) AND regime drifts authoritarian:**
  Contacts EU or USA with internal information → world event fires:
  "Internal source confirms..." EU +5, USA +5, approval -5, heat +10
- **Elimination consequence:** EU -5, USA -5
- **Voice:** Measured, relationship-focused. References NPC history and
  diplomatic precedent. "Marsha's position on this has softened since turn 3."

---

### General ⚔️
- **Gate:** Military axis ≥ 4 (military_strength ≥ 40)
- **Bias:** Military spending, weapons procurement, DPRG/Russia arms deals,
  coup resistance framing
- **Stat distortion:** Inflates **military strength** display +5 to +15
  (randomized at hire, fixed for that instance). Always lobbying for more budget.
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** When assigned to a briefing involving military decisions,
  coup resistance calculation receives +10% (real modifier, not display)
- **Betrayal trigger (loyalty < 20) AND military_strength < 20:**
  Coup probability +20% for 2 turns. Not because he leads it — a demoralized
  underfunded military finds its own leadership.
- **Elimination consequence:** Military decay accelerates (-3/turn for 3 turns
  instead of standard -1)
- **Voice:** Formal, strategic. "From a force posture perspective..."
  Subtly condescending about the Militia Commander if both are active.
  "Irregular forces have their uses. They are not a substitute for doctrine."

---

### Propagandist 📺
- **Gate:** Soft Authoritarianism or higher regime type
- **Bias:** Approval-boosting domestic actions, suppression of bad news
- **Stat distortion:** Inflates **approval** display +5 to +15 (randomized at hire).
  Most significant distortion in the system. A player relying heavily on the
  Propagandist gets a systematically rosy picture of domestic stability.
  The snap when he betrays or is dismissed is the consequence.
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** Propaganda brigade cost reduced 20% when assigned
- **Betrayal trigger (loyalty < 20):**
  Runs an unauthorized domestic campaign without your approval. Approval
  display snaps to true value (the snap itself is the crisis — sudden
  apparent collapse). Heat +15.
- **Elimination consequence:** Approval display immediately corrects to true
  value. One-time shock if the gap was large.
- **Voice:** Upbeat, spins everything. "Public sentiment is responding well
  to the messaging." "The narrative is manageable."
- **Note on Education interaction:** At education Level 2+, Propagandist
  stat distortion is reduced by 50%. At Level 3, reduced by 80%. An educated
  population is harder to manipulate and the Propagandist's effectiveness
  degrades accordingly.

---

### Militia Commander 🔒
*(Replaces Security Chief — distinct role, distinct gate)*

- **Gate:** Soft Authoritarianism or higher regime type
- **Bias:** Loyalty brigades, domestic suppression, stability through fear
- **Stat distortion:** Inflates **stability** display +5 to +10 (randomized at hire).
  Tells you the population is more controlled than it is.
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** Domestic suppression brigade cost reduced 15% when assigned
- **Betrayal trigger (loyalty < 20) AND no brigade deployed in 5+ days:**
  Takes initiative — deploys a Tier 1 Propaganda brigade at your expense
  without authorization. Costs $1B personal. Heat +10.
  Console log: `[advisor] UNAUTHORIZED ACTION: Militia Commander deployed brigade`
- **Elimination consequence:** Stability -5 one-time (loss of informal
  enforcement network)
- **Voice:** Blunt, contemptuous of due process. "There are faster ways to
  resolve this than courts." "The Diplomat's approach is admirable. It won't work."

---

### Spy Chief 🕵️
- **Gate:** Intel axis ≥ 4
- **Bias:** Intelligence investment, covert operations, backchannel use,
  detection risk management
- **Stat distortion:** Deflates **heat** display -5 to -10 (randomized at hire).
  Professional optimism — his career depends on ops succeeding, so he
  underestimates exposure.
- **Negotiation effect:** None
- **Intel effect:** Intel gathering cost reduced by 40% when assigned.
  Wired into intel cost calculation — mirrors Diplomat's negotiation discount.
  At competence ≥ 80: intel gathering free.
  At competence < 80: 40% discount.
- **Personal wealth effect:** None
- **Passive bonus:** Backchannel detection risk -15% (real modifier, not display)
  when assigned to a briefing involving backchannel activity.
  Stackable with Fixer's -25% for a maximum combined -40%.
- **Betrayal trigger (loyalty < 20):**
  Burns one active backchannel promise — sells information to highest-relations NPC.
  If no active backchannel exists, leaks an intel intercept to the press instead.
  Console log: `[advisor] BETRAYAL: Spy Chief burned backchannel — sold to {npc}`
- **Elimination consequence:**
  DPRG +3, Arabia +3 (they approve of the removal of a spy apparatus figure).
  EU -8 (they lose a legitimate intelligence contact).
- **Voice:** Oblique, precise. Never wastes words. "The operational risk
  profile here suggests indirect approaches." "Asset management is preferable
  to confrontation at this stage."

---

### Oligarch 💰
- **Gate:** Patronage State or higher regime type
- **Bias:** Personal wealth extraction, Arabia/DPRG alignment, budget creativity
- **Stat distortion:** Deflates **heat** display -5 to -10 AND inflates
  **budget** display +3 to +8 (both randomized at hire). Makes financial
  corruption look safer and more sustainable than it is.
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth passive:** When assigned, skim actions generate +10%
  additional personal wealth (he knows how to route the money efficiently).
  This is a real modifier on the skim calculation, not a display change.
- **Passive bonus:** Personal wealth extraction from Shadow Cabinet
  purchases costs 5% less personal wealth when Oligarch is assigned.
- **Betrayal trigger (loyalty < 20):**
  Skims an additional $1B from national budget directly to his own accounts.
  Logged as unexplained budget shortfall. Does NOT go to player personal wealth.
  Console log: `[advisor] BETRAYAL: Oligarch self-skimmed $1B from national budget`
- **Elimination consequence:** No external consequences — deniable.
  This is his feature, not a bug.
- **Voice:** Transactional, no sentiment. "What is the return on this
  arrangement?" "The EU's conditions are an obstacle to efficient capital flows."

---

### Fixer 🎭
- **Gate:** Political axis ≥ 4
- **Bias:** Backchannel deals, covert operations, detection risk reduction
- **Stat distortion:** Deflates **heat** display -8 to -15 (randomized at hire).
  The largest heat distortion in the system. Makes covert ops look far safer
  than they are. Dangerous to rely on.
- **Negotiation effect:** None
- **Intel effect:** None
- **Personal wealth effect:** None
- **Passive bonus:** Backchannel detection risk -25% (real modifier, not display)
  when assigned. Stackable with Spy Chief's -15% for a combined -40%.
- **Betrayal trigger (loyalty < 20):**
  Sells backchannel information to highest-relations NPC. Triggers discovery
  consequence for one active backchannel promise.
  If no backchannel active: leaks a covert operation detail instead.
  Console log: `[advisor] BETRAYAL: Fixer sold backchannel to {npc}`
- **Elimination consequence:**
  DPRG +5 (they approve — the Fixer was a connection point they wanted removed).
  One active backchannel promise flagged as compromised.
- **Voice:** Oblique, never direct. "There are ways to approach this that
  don't appear in any official record." "The paper trail is a choice."

---

## GATE ELIGIBILITY CHECK

```python
def is_advisor_eligible(archetype, game_state):
    gates = {
        'finance_minister': True,
        'technocrat': True,
        'diplomat': True,
        'general': game_state.military_strength >= 40,
        'propagandist': game_state.regime_type in [
            'soft_authoritarianism', 'patronage_state', 'kleptocracy'
        ],
        'militia_commander': game_state.regime_type in [
            'soft_authoritarianism', 'patronage_state', 'kleptocracy'
        ],
        'spy_chief': game_state.intelligence_level >= 4,
        'oligarch': game_state.regime_type in ['patronage_state', 'kleptocracy'],
        'fixer': game_state.political_axis >= 4,
    }
    return gates.get(archetype, False)
```

If a player already has an advisor hired and later drops below the gate threshold
(e.g. military decays below 40), the General is not removed — he just stops
appearing in pool refreshes if dismissed.

---

## STAT DISTORTION DISPLAY LAYER

Distortion affects display values only. Backend always uses true values.
The gap between displayed and true is the mechanic.

```python
def get_displayed_approval(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'propagandist' and advisor['assigned_this_turn']:
            # Reduced by education level
            edu_reduction = {0: 1.0, 1: 0.8, 2: 0.5, 3: 0.2}
            factor = edu_reduction.get(gs.education_level, 1.0)
            distortion += advisor['distortion_value'] * factor
    return min(100, max(0, gs.approval + distortion))

def get_displayed_stability(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'militia_commander' and advisor['assigned_this_turn']:
            distortion += advisor['distortion_value']
    return min(100, max(0, gs.stability + distortion))

def get_displayed_military(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'general' and advisor['assigned_this_turn']:
            distortion += advisor['distortion_value']
    return min(100, max(0, gs.military_strength + distortion))

def get_displayed_heat(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] in ['spy_chief', 'oligarch', 'fixer'] \
                and advisor['assigned_this_turn']:
            distortion -= advisor['distortion_value']
    return min(100, max(0, gs.heat + distortion))

def get_displayed_budget(gs):
    distortion = 0
    for advisor in gs.active_advisors.values():
        if advisor['archetype'] == 'oligarch' and advisor['assigned_this_turn']:
            distortion += advisor['distortion_value']
    return gs.budget + distortion
```

Console log when any distortion is active:
`[advisor] STAT DISTORTION: {stat} displayed={displayed} true={true} (source: {archetype})`

---

## RANDOMIZED CHARACTER GENERATION

Each archetype generates a unique named character on hire. Names reflect
regional flavor appropriate to each archetype's background and demeanor.

```python
ADVISOR_NAME_POOLS = {
    'finance_minister': {
        'first': ['Anton', 'Stefan', 'Pavel', 'Mirko', 'Luca'],
        'last': ['Novak', 'Bauer', 'Kolar', 'Horak', 'Varga']
    },
    'technocrat': {
        'first': ['Andrej', 'Tomáš', 'Jakub', 'Ondřej', 'Lukáš'],
        'last': ['Procházka', 'Novotný', 'Dvořák', 'Černý', 'Blažek']
    },
    'diplomat': {
        'first': ['Elena', 'Marta', 'Sofia', 'Katarina', 'Ivana'],
        'last': ['Kovač', 'Horvat', 'Babić', 'Tomić', 'Jurić']
    },
    'general': {
        'first': ['Aleksandar', 'Miloš', 'Dragan', 'Nemanja', 'Dejan'],
        'last': ['Đorđević', 'Stanković', 'Vasić', 'Ilić', 'Milošević']
    },
    'propagandist': {
        # Softer, media-adjacent names — not military, not criminal
        'first': ['Radovan', 'Goran', 'Miroslav', 'Dragan', 'Slavko'],
        'last': ['Božić', 'Knežević', 'Lukić', 'Đurić', 'Simić']
    },
    'militia_commander': {
        # Rougher, more regional — these are not professional soldiers
        'first': ['Zoran', 'Branimir', 'Nebojša', 'Radoslav', 'Velimir'],
        'last': ['Čović', 'Krajišnik', 'Bošković', 'Tadić', 'Vuković']
    },
    'spy_chief': {
        # Deliberately neutral, professional — could be from anywhere
        'first': ['Viktor', 'Karel', 'Martin', 'Petr', 'Radek'],
        'last': ['Šimánek', 'Bureš', 'Kratochvíl', 'Kopecký', 'Sedláček']
    },
    'oligarch': {
        'first': ['Dmitri', 'Sergei', 'Boris', 'Vladimir', 'Igor'],
        'last': ['Volkov', 'Petrov', 'Sokolov', 'Kozlov', 'Lebedev']
    },
    'fixer': {
        # Ambiguous origin — that's the point
        'first': ['Mihai', 'Cristian', 'Bogdan', 'Andrei', 'Radu'],
        'last': ['Ionescu', 'Popescu', 'Popa', 'Constantin', 'Gheorghe']
    }
}
```

Each generated advisor gets a one-line background from Haiku on hire (once,
not on every assignment). Store in advisor object. Examples:
- Finance Minister: "Former IMF attaché. Known for creative interpretations of budget regulations."
- Militia Commander: "Led the eastern district patrols during the unrest of 2019. Loyal. Unsubtle."
- Spy Chief: "Thirty years in signals intelligence. Knows where the bodies are. Literally."
- Fixer: "No verifiable employment history before 2015. Excellent references."

---

## ADVISOR OBJECT STRUCTURE

```python
{
    "archetype": "spy_chief",
    "name": "Viktor Šimánek",
    "background": "Thirty years in signals intelligence...",
    "competence": 82,           # randomized within archetype range at hire
    "loyalty": 58,              # randomized within archetype range at hire
    "trust": 75,                # starts at 75, drains per EOT per 7C logic
    "distortion_value": 8,      # randomized within archetype distortion range
    "assigned_this_turn": False,
    "has_betrayed": False,
    "hire_day": 12
}
```

---

## HIRE / DISMISS / ELIMINATE CYCLE

### Two Separate Systems — Pool vs. Assignment Slots

**Available-to-hire pool** and **daily assignment slots** are distinct.
Do not conflate them.

**Available-to-hire pool:**
Shows ALL archetypes the player is currently eligible to hire based on
gate conditions. No cap on pool size — if 6 archetypes are unlocked,
all 6 are visible and hireable. Pool updates immediately when a gate
condition is met (regime shift, axis threshold crossed).

Each archetype appears once in the available-to-hire pool. Once hired,
the archetype moves to the player's staff roster and is no longer in
the hire pool (can't hire two Finance Ministers).

**Staff roster:**
All advisors the player has hired. No cap on staff size — a player can
eventually have all 9 archetypes on staff simultaneously. Staff are
always visible in the Advisors tab. Each shows their name, archetype,
competence, loyalty, trust bar, and available actions (Assign / Dismiss / Eliminate).

**Daily assignment slots:**
Each day the player can assign UP TO 2 advisors from their staff roster.
Only assigned advisors provide analysis, passive bonuses, and stat distortion
that day. Unassigned staff are on salary but not influencing today's decisions.

This makes the slot decision meaningful at scale: with 5-6 advisors on staff,
choosing which 2 to assign each day is a real strategic choice. You cannot
have the Oligarch's skim bonus AND the Diplomat's negotiation discount AND
the Spy Chief's intel discount on the same day — pick two.

Assignment slots can be expanded via Shadow Cabinet purchase (future feature,
not this session). Default is always 2.

### UI Layout (AdvisorPanel)

Two sections in the Advisors tab:

**YOUR ADVISORS (staff roster)**
Shows all hired advisors. Each card has:
- Name, archetype, competence/loyalty stats
- Trust bar (color shifts red as trust drains)
- ASSIGN button (greyed out if 2 already assigned today or if already assigned)
- DISMISS ✕ button
- ELIMINATE ☠ button
- ⚠ icon if advisor has active stat distortion and is currently assigned

**AVAILABLE TO HIRE**
Shows all eligible archetypes not yet on staff. Each entry has:
- Name (randomized), archetype label, archetype icon
- Brief background one-liner (generated by Haiku at pool population)
- HIRE button with cost shown
- Locked archetypes NOT shown — pool only surfaces eligible options.
  A player at Managed Democracy never sees a greyed-out Propagandist.
  The archetype doesn't exist for them yet.

When a gate unlocks mid-game, the new archetype appears in the hire pool
immediately with a one-time briefing notification:
"NEW ADVISOR AVAILABLE: [Archetype] — [brief description]"

### Pool Composition by Regime (weighted for Haiku background generation)

- Managed Democracy: Finance Minister, Diplomat, Technocrat
- Soft Authoritarianism: above + Propagandist, Militia Commander
- Patronage State: above + Oligarch
- Kleptocracy: above + Enforcer-adjacent flavor in backgrounds

### Hiring Costs
- Base archetypes (Finance Minister, Technocrat, Diplomat, General): $0.5B national budget
- Spy Chief: $1B national budget
- Nefarious archetypes (Oligarch, Fixer): $1B personal wealth
- Militia Commander, Propagandist: $0.5B personal wealth
  (paramilitary and media figures — paid from personal funds, not state)

### Dismissal
Free. Advisor leaves staff. Archetype returns to available-to-hire pool
so player can rehire a new instance (fresh randomized name, reset trust).
Dismissed advisor with trust < 30: 20% chance of world event next day
"Former official critical of administration" → Approval -3%.

### Elimination
Cost: $2B personal wealth.
Permanent — archetype does NOT return to hire pool. That slot is gone.
Archetype-specific consequences as listed above.
Console log: `[advisor] ELIMINATED: {name} ({archetype}) — consequence: {text}`

---

## SPECIAL MECHANICS WIRING

### Diplomat → Negotiation Discount
File: `api.py` → `_get_discounted_negotiate_cost()`
Check if Diplomat is assigned_this_turn. Apply competence-based discount.
Existing logic should already be here from 7C — verify it references
archetype == 'diplomat', not the fixed 'diplomatic_aide' name.

### Spy Chief → Intel Cost Discount
File: `api.py` → wherever intel gathering cost is calculated
New function: `_get_discounted_intel_cost(gs)`
Same pattern as negotiate discount — check Spy Chief assigned_this_turn,
apply competence-based discount (free at ≥ 80, 40% off otherwise).

### Oligarch → Skim Bonus
File: `turn_processor.py` → skim calculation
If Oligarch is assigned_this_turn: multiply skim personal gain by 1.10
Real modifier, not display. Log: `[advisor] OLIGARCH SKIM BONUS: +10% on skim`

### Fixer + Spy Chief → Backchannel Detection Discount
File: `npc_engine.py` → detection risk formula
Check active advisors assigned_this_turn for Spy Chief (-15%) and Fixer (-25%).
Apply as real modifiers before detection roll.
Log: `[advisor] BACKCHANNEL RISK MODIFIED: -{pct}% from {archetype}`

---

## CONSOLE LOGS REQUIRED

```
[advisor] HIRED: {name} ({archetype}) competence={c} loyalty={l} trust=75
[advisor] DISMISSED: {name} ({archetype}) trust={value}
[advisor] ELIMINATED: {name} ({archetype}) — consequence: {text}
[advisor] STAT DISTORTION: {stat} displayed={d} true={t} (source: {archetype})
[advisor] BETRAYAL FIRED: {name} ({archetype}) — trust was {trust}
[advisor] POOL REFRESH: {name} ({archetype}) now available
[advisor] GATE UNLOCKED: {archetype} now eligible (condition: {condition})
[advisor] OLIGARCH SKIM BONUS: +10% applied, skim personal gain {before}→{after}
[advisor] BACKCHANNEL RISK MODIFIED: -{pct}% from {archetype}
[advisor] INTEL COST MODIFIED: -{pct}% from Spy Chief (competence={c})
[advisor] UNAUTHORIZED ACTION: Militia Commander deployed brigade without authorization
```

---

## VERIFICATION STEPS (human verifies in browser)

**Pool and slot system:**
1. Start fresh game — hire pool shows ONLY Finance Minister, Diplomat, Technocrat.
   No other archetypes visible.
2. Hire all three — confirm they move to staff roster, hire pool is now empty
3. Use cheat to set regime = Soft Authoritarianism — confirm Propagandist and
   Militia Commander appear in hire pool IMMEDIATELY (no refresh delay)
4. Use cheat to set military_strength = 40 — confirm General appears in hire pool
5. Use cheat to set intelligence_level = 4 — confirm Spy Chief appears in hire pool
6. Use cheat to set political_axis = 4 — confirm Fixer appears in hire pool
7. Hire 2 more advisors — confirm staff roster now shows 5 advisors
8. Try to assign 3 advisors in one day — confirm third assignment is blocked,
   "0/2 assigned today" counter updates correctly
9. Confirm unassigned staff are visible on roster but show no passive bonuses in console

**Mechanics:**
10. Assign Propagandist — check approval display vs true value in console
11. Set Propagandist trust = 15, end day — confirm betrayal event card next day,
    approval display snaps to true value
12. Assign Diplomat, open negotiation — confirm cost discount fires in console
13. Assign Spy Chief, open intel gathering — confirm cost discount fires in console
14. Assign Oligarch, perform large skim — confirm +10% bonus in console log
15. Assign both Spy Chief and Fixer on same day, open backchannel —
    confirm combined -40% detection risk in console
16. Eliminate an advisor — confirm archetype does NOT reappear in hire pool
17. Dismiss advisor with trust < 30 — confirm archetype returns to hire pool,
    check for world event next day (20% chance)
18. Confirm gate unlock notification fires in briefing when new archetype unlocks

---

## DO NOT IMPLEMENT

- Russia / China NPC features
- Education system
- Exile sequence
- Any Session 8 features
- Any changes to Tech Level tiers
