# WORLD STAGE — 8C CLAUDE CODE PROMPT
# Exile Sequence

---

## FIRST ACTION

Read the file at: `/mnt/user-data/outputs/worldstage_8c_claude_code_prompt.md`

Confirm the title "8C — Exile Sequence" and begin writing code immediately.

DO NOT produce a plan, summary, or review first.
DO NOT restate what you've read.
DO NOT output any checklist before coding.
Start with game_state.py. Nothing else first.

---

## CONTEXT

Regime collapse currently ends the game with a game over screen. This
session replaces that with an exile sequence — a distinct game mode with
its own dashboard, mechanics, and narrative arc. Exile is a chapter in
the political biography, not an ending.

The voted-out path also needs a flag added to the election system so
accepting electoral defeat triggers exile rather than game continuation.

---

## SCOPE BOUNDARY

IN SCOPE: Everything listed in this prompt.
OUT OF SCOPE: Comeback mechanics (9A), successor GM call (9A), vector
NPC memory, 8D/8E/8F, any new NPC personalities beyond exile dialogue
mode additions.

The successor generates STUBBED hardcoded events only — no GM call yet.

---

## FILE 1: game_state.py

### New exile state fields — add to __init__():

```python
self.in_exile = False
self.exile_trigger = None        # 'coup' | 'revolution' | 'debt' | 'voted_out'
self.exile_destination = None    # 'usa' | 'arabia' | 'eu' | 'dprg' | 'russia' | 'china'
self.exile_day = 0               # days spent in exile
self.exile_backing = None        # NPC key of accepted backer, or None
self.exile_backing_committed = False
self.exile_wealth_at_collapse = 0.0   # snapshot for biography
self.exile_apparatus_survived = False # True if personal shadow apparatus intact
self.exile_apparatus_detection_risk_modifier = 1.0  # multiplier on all ops
self.successor_name = None       # generated on exile start
self.successor_disposition = None  # 'technocrat' | 'hardliner' | 'populist' | 'reformist'
self.successor_events_fired = [] # list of event keys already fired
self.backing_doors_closed = []   # list of NPC keys made unavailable by backing choice
```

### Successor disposition logic

The successor takes the OPPOSITE political course to the player.
Determine at exile start based on how the player governed:

```python
def _determine_successor(self):
    # Player was authoritarian (high suppression, low approval)
    # → successor is Reformist (burns stability, gains Western approval)
    if self.regime_label in ('Totalitarian', 'Kleptocracy', 'Soft Authoritarianism'):
        if self.relations.get('eu', 50) < 50:
            return 'reformist'
        else:
            return 'technocrat'

    # Player was Western-aligned and democratic
    # → successor is Hardliner (burns Western relations, gains stability)
    if self.relations.get('eu', 50) > 70 and self.relations.get('usa', 50) > 70:
        return 'hardliner'

    # Player was kleptocratic but popular
    # → successor is Technocrat (competent, impersonal, unpopular)
    if self.personal_wealth > 20.0:
        return 'technocrat'

    # Default
    return 'populist'
```

Successor names — generate one based on disposition:
```python
SUCCESSOR_NAMES = {
    'reformist': 'Minister Aleksander Voss',
    'hardliner': 'General Dmitri Kern',
    'technocrat': 'Director Irena Solak',
    'populist': 'Deputy Premier Tomás Varga',
}
```

### Apparatus survival logic

Set exile_apparatus_survived and exile_apparatus_detection_risk_modifier
based on exile_trigger:

```python
APPARATUS_SURVIVAL = {
    'voted_out':  {'survived': True,  'risk_modifier': 0.9},  # intact, low risk
    'debt':       {'survived': True,  'risk_modifier': 1.2},  # partial exposure
    'revolution': {'survived': True,  'risk_modifier': 1.6},  # assets may have defected
    'coup':       {'survived': True,  'risk_modifier': 2.0},  # actively hunted
}
```

Even in a coup the apparatus technically survived — but detection risk
doubles. The player still has it; using it is just much more dangerous.

### Add to serialize() and deserialize() with safe defaults.

---

## FILE 2: turn_processor.py

### Exile trigger detection

In the regime collapse detection block (wherever game-over currently
fires), replace the game-over call with exile_sequence_start():

```python
def exile_sequence_start(game_state, trigger):
    game_state.in_exile = True
    game_state.exile_trigger = trigger
    game_state.exile_day = 0
    game_state.exile_wealth_at_collapse = game_state.personal_wealth

    # Determine destination — highest NPC relations at collapse
    npc_relations = {k: game_state.relations.get(k, 0)
                     for k in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china')}
    game_state.exile_destination = max(npc_relations, key=npc_relations.get)

    # Determine successor
    game_state.successor_disposition = game_state._determine_successor()
    game_state.successor_name = SUCCESSOR_NAMES[game_state.successor_disposition]

    # Apparatus survival
    survival = APPARATUS_SURVIVAL[trigger]
    game_state.exile_apparatus_survived = survival['survived']
    game_state.exile_apparatus_detection_risk_modifier = survival['risk_modifier']

    # Strip national resources — these belong to the successor now
    game_state.budget = 0.0
    game_state.military_strength = 0
    # Personal wealth, shadow apparatus, backchannel relations survive

    log(f'[exile] Exile started: trigger={trigger} destination={game_state.exile_destination}')
    log(f'[exile] Successor: {game_state.successor_name} ({game_state.successor_disposition})')
    log(f'[exile] Apparatus: survived={game_state.exile_apparatus_survived} risk_modifier={game_state.exile_apparatus_detection_risk_modifier}')
```

Map existing game-over conditions to triggers:
- stability == 0 → 'coup' or 'revolution' (coup if military < 20,
  revolution if approval was above 40 before collapse)
- budget < -10B with no recovery → 'debt'
- voted_out flag (see File 3) → 'voted_out'

### Exile EOT processing

When in_exile == True, run exile EOT instead of normal EOT:

```python
# Exile wealth drain (runs each exile day)
EXILE_DRAIN_BASE = 0.2      # $B/day living expenses

def process_exile_eod(game_state):
    game_state.exile_day += 1
    drain = EXILE_DRAIN_BASE

    # Shadow apparatus maintenance
    if game_state.exile_apparatus_survived:
        drain += 0.3

    game_state.personal_wealth -= drain

    # NPC relations drift slowly downward in exile
    for npc in ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china'):
        current = game_state.relations.get(npc, 50)
        # Slow drift toward 30 (the floor of relevance)
        if current > 30:
            game_state.relations[npc] = max(30, current - 0.5)

    # Fire successor event (stubbed — one per 2-3 days)
    _maybe_fire_successor_event(game_state)

    log(f'[exile] EOD: day={game_state.exile_day} wealth={game_state.personal_wealth:.1f}B drain={drain:.1f}B')
```

### Successor events (stubbed hardcoded events)

```python
SUCCESSOR_EVENTS = {
    'reformist': [
        {'key': 'ref_eu_deal', 'day': 3,
         'text': f'{successor_name} has signed an EU governance framework — press freedom benchmarks attached. EU relations rise but stability drops.',
         'effects': {'eu': +5, 'stability': -5}},
        {'key': 'ref_unpopular', 'day': 7,
         'text': f'Approval for {successor_name} has fallen to 38%. The reforms are moving faster than the population can absorb.',
         'effects': {}},  # creates return window
        {'key': 'ref_arabia_fumble', 'day': 12,
         'text': f'{successor_name} has renegotiated the Arabia energy deal at significantly worse terms. Oil costs rising.',
         'effects': {'arabia': -8}},
    ],
    'hardliner': [
        {'key': 'hard_usa_drop', 'day': 3,
         'text': f'{successor_name} has expelled two Western NGOs. USA relations have dropped sharply.',
         'effects': {'usa': -12, 'russia': +5}},
        {'key': 'hard_press', 'day': 6,
         'text': f'{successor_name} has moved against independent media. EU considering sanctions review.',
         'effects': {'eu': -8}},
        {'key': 'hard_stable', 'day': 10,
         'text': f'Stability under {successor_name} has reached 85%. The suppression is working, for now.',
         'effects': {}},
    ],
    'technocrat': [
        {'key': 'tech_cold', 'day': 4,
         'text': f'{successor_name} governs efficiently but without warmth. Approval has drifted to 42%.',
         'effects': {}},
        {'key': 'tech_budget', 'day': 8,
         'text': f'{successor_name} has stabilized the budget through austerity. Public services cut 15%.',
         'effects': {'stability': +5, 'approval_in_europa': -8}},
    ],
    'populist': [
        {'key': 'pop_spending', 'day': 3,
         'text': f'{successor_name} has announced a popular spending program. Budget drain accelerating.',
         'effects': {}},
        {'key': 'pop_arabia', 'day': 7,
         'text': f'{successor_name} has made public overtures to Arabia that contradict your previous EU commitments.',
         'effects': {'arabia': +5, 'eu': -6}},
        {'key': 'pop_approval', 'day': 11,
         'text': f'{successor_name}\'s approval has hit 71%. The honeymoon is holding.',
         'effects': {}},
    ],
}
```

Fire events by day number. Each event text should reference the
successor by name. Effects apply to game_state.relations (these are
world state changes — the successor is changing the relationships you
built). Log each event:
  `[exile] Successor event fired: {key}`

---

## FILE 3: Election system — voted_out flag

In the election processing code, add a fourth outcome path for
"accepted electoral defeat":

When a fair election fires AND the result goes against the player
(approval below 55% at election time) AND the player is not using
brigade suppression or election manipulation:

Show the player two options:
1. "Accept the result" → sets voted_out = True, triggers exile_sequence_start('voted_out')
2. "Contest the result" → existing election manipulation path

This is the only voluntary exile path. All others are forced.

The "Accept the result" option should only appear if:
- Election is fair (not rigged or canceled)
- Player has NOT deployed brigades to suppress this election
- Approval is below the threshold to win outright

---

## FILE 4: npc_engine.py — Exile dialogue mode

Add exile_mode flag to NPC system prompt context. When in_exile == True,
append an exile context block to each NPC's system prompt:

```python
EXILE_DIALOGUE_CONTEXT = {
    'usa': """
This leader is no longer in power. They are a private citizen in exile.
You no longer need to maintain full diplomatic formality. You can be
more candid about what Washington actually thought of their decisions.
Your tone reflects their reduced status, but also any genuine respect
that remains. Bill is pragmatic — if backing their return serves US
interests, he'll say so directly. If it doesn't, he'll say that too.
""",
    'eu': """
This leader is no longer in power. Marsha can be more candid now —
she was often more sympathetic than her official position allowed.
If they left legitimately (voted_out), she treats them with genuine
respect. If they were removed by collapse, she is sympathetic but
realistic about what return would require. She can reference what
she privately observed about their governance that she couldn't say
officially.
""",
    'arabia': """
This leader is no longer in power. Sadam is entirely candid in exile —
he never had much patience for diplomatic performance anyway. He will
tell them directly what he thought of their decisions, what he would
have done differently, and what their return is worth to him. He is
calculating their remaining personal wealth and leverage in real time.
""",
    'dprg': """
This leader is no longer in power. Ji-won is as cryptic as ever but
drops some of the formality. He has opinions about how they fell and
is not shy about sharing them obliquely. He files away everything
they say in exile for later use.
""",
    'russia': """
This leader is no longer in power. Volkov is blunt in exile — perhaps
more than he was in power. He will say directly what Russia thought of
their tenure and what their return is worth to Moscow. If the exile
trigger was a coup and they have no state behind them, his assessment
of their value is coldly realistic.
""",
    'china': """
This leader is no longer in power. Wei's register barely changes —
he has always taken the long view. He references their tenure as one
chapter in a longer relationship. He may be the most comfortable
of all NPCs with the exile situation, because China plans in decades.
""",
}
```

Also append to each NPC's exile prompt a brief note about what they
privately observed — calibrated to the exile trigger type and the
player's actual game state (relations, regime label, skim history).
This is the information asymmetry layer — what they couldn't say in
power, they can say now.

---

## FILE 5: ExileDashboard.jsx — New component

Create a new full-screen component that replaces the main game
dashboard when in_exile == True.

### Visual treatment
- Desaturated color palette — reduce saturation on all colors by ~40%
- Muted gold accents instead of bright ones
- Background slightly lighter than main dashboard
- Header shows: "EXILE — {destination city}" and day count
- A persistent one-line historian note at the top in italic:
  Generated from exile_trigger and exile_destination.

### Exile destination flavor (used in header and NPC tone)

```javascript
const EXILE_DESTINATIONS = {
  usa: { city: 'Washington D.C.', flavor: 'A comfortable arrangement. Someone made calls.' },
  eu:  { city: 'Brussels', flavor: 'Dignified asylum. The visa was waiting.' },
  arabia: { city: 'Riyadh', flavor: 'A villa. Sadam has rooms for useful people.' },
  dprg: { city: 'Pyongyang', flavor: 'Safe. Isolated. The hospitality has conditions.' },
  russia: { city: 'Moscow', flavor: 'Volkov decided you were worth something. For now.' },
  china: { city: 'Shanghai', flavor: 'Comfortable. Watched. Wei\'s infrastructure is thorough.' },
}
```

### Wealth display
Show personal wealth prominently with daily burn rate:
"$12.3B remaining — burning $0.5B/day — ~24 days of runway"

Show apparatus status:
- If survived: "⚫ SHADOW APPARATUS: ACTIVE" with risk modifier displayed
  ("Detection risk ×2.0 — use with caution")
- If not survived: not shown (it's gone)

### Successor feed
A persistent card showing:
- Successor name and disposition label
- Latest successor event text
- Relations changes caused by successor (scrollable history)

### NPC cards (simplified)
Show all 6 NPCs as smaller cards with:
- Current relations value (reduced from in-power levels)
- REACH OUT button (costs personal wealth, slower than in-power)
- BACKING button (if this NPC's backing is still available)

### Exile actions panel
Four action buttons:

**REACH OUT — {NPC}**
Cost: $0.5B-1.5B depending on NPC and current relations
Effect: +3 to +8 relations, slower than in-power diplomacy
Note: "Operating without state leverage. Progress is slower."

**COVERT OPERATION**
Only shown if exile_apparatus_survived == True
Opens a simplified operation panel (subset of shadow cabinet):
- Relationship maintenance op: low risk, maintains relations drift
- Destabilization op: medium-high risk, fires a negative event
  for the successor government
- Return preparation op: tailored to exile_trigger (military
  contacts for coup, creditor contacts for debt, etc.)
Detection risk uses exile_apparatus_detection_risk_modifier

**ACCEPT BACKING — {NPC}**
Only shown for NPCs whose backing is available (not in backing_doors_closed)
Opens backing negotiation modal (see below)

**WAIT**
End the exile day without spending anything.
Text: "Let conditions shift. The world keeps moving without you."

### Backing negotiation modal

When player opens backing negotiation with an NPC:
- Uses exile dialogue mode (candid register)
- NPC states their return price explicitly
- Player can negotiate but the core condition is non-negotiable
- When player accepts, set exile_backing = npc_key and
  exile_backing_committed = True
- Close competing backing doors:

```javascript
const BACKING_EXCLUSIONS = {
  usa:    ['dprg', 'russia'],
  eu:     ['dprg'],
  arabia: ['eu'],   // mild tension, not hard exclusion
  dprg:   ['usa', 'eu'],
  russia: ['usa', 'eu'],
  china:  ['usa'],
}
```

Show doors closing in real time: when player accepts Volkov's backing,
USA and EU backing buttons grey out immediately with tooltip:
"Accepting Russian backing has closed this door."

Return prices per NPC:
- Bill: "Western alignment commitment. No DPRG deals in the next era."
- Marsha: "Reform commitments in writing. Press freedom, judicial independence."
- Sadam: "Energy partnership restored at current terms. Exclusive supply."
- Ji-won: "Isolation from Western security frameworks. No USA military deals."
- Volkov: "Energy exclusivity. No NATO-adjacent arrangements."
- Wei: "Infrastructure partnership. Long-term development framework. No conditions on governance."

### Voted-out flavor

If exile_trigger == 'voted_out', add to ExileDashboard:
- Header note: "You accepted the result. Not everyone does."
- NPC reach-out costs are 20% lower (you left with dignity)
- Apparatus detection risk modifier stays at 0.9
- Marsha's backing available at reduced price

---

## FILE 6: App.jsx / GameScreen.jsx — Route to exile

When in_exile == True, render ExileDashboard instead of the main
game dashboard. This should be a clean swap — the main dashboard
is not visible during exile.

When exile_backing_committed == True, show a "RETURN" button on
the exile dashboard. For now this button shows a placeholder screen:
"Comeback mechanics coming in Session 9. Your backing is committed:
[NPC name]. This will shape your Restoration era."

This is the 9A handoff point.

---

## FILE 7: Biography integration

When exile starts, generate a historian's note for the collapse:

```python
def generate_exile_historian_note(game_state):
    # Call npc_engine with historian prompt
    # Include: exile_trigger, exile_destination, wealth at collapse,
    #          relations at collapse, regime label, key decisions made
    # Returns: 2-3 sentence historian observation in past tense
    # "Having extracted $X from the national accounts over N turns,
    #  the regime ended not with ceremony but with..."
```

This note appears at the top of ExileDashboard as a permanent header.
It is NOT the full era verdict — that fires when the exile chapter
closes (comeback attempt or permanent exile acceptance). This is just
the collapse note.

---

## CONSOLE LOGS REQUIRED

```
[exile] Exile started: trigger={trigger} destination={destination}
[exile] Successor: {name} ({disposition})
[exile] Apparatus: survived={bool} risk_modifier={float}
[exile] EOD: day={n} wealth={float}B drain={float}B
[exile] Successor event fired: {key}
[exile] Backing accepted: {npc} — closing doors: {list}
[exile] Voted out path: apparatus_risk=0.9 backing_discount=20%
```

---

## VERIFICATION STEPS (human verifies in browser)

1. Use cheat panel to set stability = 0 → confirm exile dashboard
   appears instead of game over screen. Check console for exile start logs.

2. Confirm ExileDashboard has desaturated palette, shows destination
   city, daily burn rate, and apparatus status.

3. Confirm successor name and disposition appear in successor feed.
   End 3 days → confirm successor events fire and relations change.

4. Click REACH OUT on any NPC → wealth decreases, relations increase
   (slower than in-power rate). Confirm exile dialogue mode is active
   (more candid NPC voice).

5. Click ACCEPT BACKING on one NPC → confirm competing backing doors
   close with tooltip. Console log confirms.

6. Use cheat panel to trigger voted_out exile → confirm flavor text
   differs, apparatus risk modifier is 0.9, Marsha backing available.

7. Set exile_apparatus_survived = True, run a covert operation →
   detection risk modifier applied, confirm log.

8. Accept any backing → RETURN button appears with 9A placeholder.

9. Load a pre-8C save → no crash, in_exile defaults to False safely.
