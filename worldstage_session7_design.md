# WORLD STAGE — Session 7 Design Document
Generated: March 2026

---

## SESSION 7 THEME: THE LIVING WORLD

Session 7 is the transition point from structured 10-turn arcs toward
open-ended persistent simulation. The fixed loop dissolves. Eras replace
turns as narrative containers. The full political biography assembles
from era chapters over time. The GM becomes an active participant in
world generation rather than a consequence narrator.

---

## PRE-SESSION 7 INFRASTRUCTURE (Required Before Session 7 Begins)

### Player Accounts

Every Session 7 feature that requires persistence — NPC memory, era
biography, leaderboards, shareable cards — needs a player identity
to attach to. Accounts must exist before the dashboard rebuild ships.

**Implementation:** Supabase Auth (email + password). Supabase has a
local development CLI so the local dev workflow is unchanged — run
Supabase locally alongside uvicorn, same code connects to hosted
Supabase in production. Railway and Vercel remain the deployment
targets.

**What accounts unlock:**
- Game states stored against user ID, not just game ID
- NPC vector memory keyed to user ID per NPC (Session 5 prerequisite)
- Multi-era biography assembly across sessions
- Leaderboard and Regime Survival Index
- Shareable biography cards
- Save/resume across sessions

### Test Account System

A `is_test` flag on any account unlocks:
- One-click full game state reset without losing account credentials
- Cheat panel (locked to test accounts only, never visible in production)
- Direct game state editor: set any value (relations, axis levels,
  turn number, personal wealth) without playing to that point
- Seeded snapshots: saved game states at specific conditions
  (e.g. "Turn 8, all axes at 10, EU 94, Arabia sanctions active")
  restorable instantly without cheat panel engineering
- Multiple simultaneous game states under one account for path testing

**Local testing:** Full local dev workflow preserved. Supabase CLI runs
the auth and database stack locally. No requirement to switch to
Railway/Vercel for testing until accounts + dashboard ship together.

---

## FEATURE 1: TURN STRUCTURE REDESIGN

### The Core Change

Turns become days. The 10-turn loop dissolves into open-ended play
structured around eras. Two modes run simultaneously:

**Ambient mode (between events):**
Budget ticks, relations drift, world moves. Player chooses what to
engage with or ignore. No forced structure or clock. The dashboard
is the ambient state — incoming briefings, world events, the daily
rhythm of governing.

**Event mode (inside an active event):**
Compressed structure with stakes and a clock. Beginning, exchanges,
resolution. The existing negotiation architecture is the model. Events
follow the same pattern, then return to ambient. "Turns" activate
contextually during events rather than running as a uniform clock
across the whole game.

### Day Advancement

Player-controlled. When done with the day's agenda, the player hits
"Next Day" manually. Natural pressure to advance comes from urgency
escalation — items ignored over multiple days get more urgent, eventually
becoming confrontations rather than invitations. No forced pace, but
no consequence-free stalling either.

### End of Day Processing

The existing EOT system maps directly onto day-end. Budget ticks,
sanctions drain, approval/stability shifts, world events resolve, NPC
relations drift — all fire when the player advances the day.

Results appear as a persistent summary card in the dashboard. Not a
blocking screen — a reference document that sits alongside the next
day's briefing items. Player can pull it up and review at any point
during the following day.

---

## FEATURE 2: ERA SYSTEM

### What an Era Is

A narrative container with a dramatic thesis. "The Reform Era."
"The Consolidation." "The Exile." Each era closes with a historian
verdict. The full political biography assembles from era chapters.
This is the architecture that makes open-ended play feel structured
without being artificial about it.

### Era Transition Triggers — Two Parallel Systems

**Event-driven (primary):**
Certain threshold events force an era boundary because the story has
genuinely changed. These include:
- Regime label crossing a line (Managed Democracy → Patronage State)
- Election outcome (especially canceled or stolen)
- Coup attempt (success or failure)
- Exile sequence triggered
- Relations hitting a meaningful floor or ceiling (EU 100, Arabia 0)
- Stability hitting 0

**Time-driven backstop (secondary):**
For long stable runs where nothing dramatic forces the issue, a
turn-count trigger runs in parallel. Approximately 20 ambient days
without a threshold event triggers a GM era-close suggestion. Player
can accept or defer. This prevents eras from running indefinitely
without compression.

**GM-initiated suggestion vs. forced transition:**
The GM proposes era transitions rather than forcing them. Player can
accept the proposal or defer. Only regime collapse and exile force
a transition regardless of player preference.

### Historian Write-Up Triggers

**Automatic:** Every era transition generates a historian verdict as
part of the closing sequence, whether player-initiated or GM-initiated.

**On demand:** A button in the left sidebar near the State Identity
label. Available at any time during ambient play. The on-demand version
uses provisional language — "As things stand..." or "Should the current
trajectory hold..." — distinct from the definitive past-tense voice
of a closed era verdict. Player can call for a mid-era reflection
whenever they want to take stock.

---

## FEATURE 3: DASHBOARD REBUILD

### The Core Change

The current single-column scaffold is replaced with a proper two-layout
system. Same components, same data, arranged differently based on
screen width via Tailwind responsive breakpoints. One build, both
targets.

### Desktop Layout — Three Panel

**Left sidebar (vital signs):**
- Budget with trend arrow
- Stability bar
- Approval bar
- Personal wealth
- Oil price with embargo tier indicator
- State Identity label — most visually prominent element on screen,
  color shifts gray → amber → deep red as regime drifts. Constant
  mirror.
- Power Base axis as horizontal slider
- Military strength and tech level as numeric indicators
- Historian write-up button (sits beneath State Identity label)
- Era number and day count

**Center panel (context-sensitive action space):**
- Default: presidential briefing with incoming items as cards,
  EOT summary card persistent at top if day just ended
- Event mode: event header, stakes summary, options, consequence
  previews. Sidebars remain visible — player sees their stability
  bleeding while deciding whether to deny the leak.
- Negotiation mode: NPC portrait forward, conversation history,
  rapport meter, current offer. Everything else fades slightly.
- Shadow Cabinet: slides up as a tray from the bottom without
  replacing the sidebars.
- Backchannel: visually distinct dark treatment, no record in
  official diplomatic log.

**Right sidebar (the world):**
Built for 6 NPCs from the start (original four + Russia + China).
- NPC cards with portrait, name, relations bar (green to red),
  one-line status note
- Russia and China cards present from Session 7 launch (passive
  initially, full dialogue in Session 8)
- Tier 2 nations below the main six — smaller, no portrait, name
  and relations number only
- Intelligence intercept notification badge at top — pulsing when
  intercept available
- Backchannel button on each NPC card (risk level indicator)

**Visual tone:** Dark background (deep navy or slate). Muted golds
and blues for UI chrome. NPC card border color reflects relationship
health. Cross between a classified briefing room and a Bloomberg
terminal.

### Mobile Layout — Card Feed

Three-panel collapses into a card feed.
- NPC relationship strip: horizontal scroll row of portrait circles
  at top with colored rings (Instagram stories visual language)
- Stats: single line, only danger-zone numbers highlighted
- Shadow Cabinet: bottom sheet, swipe up from persistent tab
- Intel intercepts: banner dropping from top of screen
- EOT summary: persistent card at top of feed after day ends

### Domestic Affairs Tab

Secondary tab on the dashboard, not a full separate page. 30-second
check-in each day: tax burden distribution, spending priorities,
social contract status in historian voice. Sets constraints for
foreign affairs without being a separate game.

---

## FEATURE 4: THE DAILY BRIEFING SYSTEM

### Structure

Each day opens with 3-5 briefing items at varying urgency levels.
Items come from:
- Major NPC-initiated events (Bill wants you to join Arabia sanctions)
- Regional issues and council updates
- Intelligence intercepts
- Player-initiated events (proactive decisions)
- World events (commodity shifts, elections in other nations)
- UN Summit (mandatory, recurring every 20-30 days)

### Item Architecture

Each briefing item the player opens becomes its own contained arc.
The existing negotiation/static choice architecture is the engine,
but GM-generated rather than fully pre-authored. Each item has:

1. **Opening message** — NPC or event card establishing the situation
2. **Exploration phase** — player can talk to other NPCs, gather
   intelligence, deploy operations, open backchannels. Multiple NPCs
   are aware of the situation and have positions.
3. **Decision point** — GM generates static options based on what
   the player did in the exploration phase. Options reflect actual
   commitments made, intelligence gathered, alliances tested.
4. **Consequences** — fire at day-end. Follow-up items may appear
   in subsequent briefings.

### The Arabia Sanctions Arc (Reference Example)

Day 1: Bill's message arrives. Arabia sends a counter-message.
Player can open backchannels to Russia or China to read their
position quietly. Assign Diplomatic Aide for relationship context.

Day 2: Active negotiation phase. Talking to multiple NPCs, deploying
intelligence, making preliminary commitments. Backchannel to Arabia
carries detection risk — if Bill's intelligence apparatus picks it
up, the arc escalates.

Day 3: Decision crystallizes. GM generates static options based on
days 1-2 actions. Consequences fire. Follow-up arrives in next
briefing.

### Player-Initiated Events

Player can kick off events proactively from the dashboard:
- Confront a country on an issue
- Cut off resources to another country
- Make a public declaration
- Initiate a trade negotiation
- Deploy a covert operation
- Open a backchannel

These generate their own arcs the same way incoming events do, with
the GM determining the other side's response. This is where the
"being the antagonist" mechanic lives — provoking, threatening,
exploiting tensions before they form against you.

### Urgency Escalation

Items ignored over multiple days escalate in language and consequence
severity:
- Ignored once: more urgent framing next day
- Ignored twice: situation worsens mechanically
- Ignored three times: no longer an invitation, now a confrontation

Intelligence apparatus reveals which slow burns are genuinely slow
and which are about to become fires.

---

## FEATURE 5: ADVISOR SYSTEM

### The Three Advisors

**Finance Minister:** Prioritizes budget stability. Gives economic
impact analysis on any briefing item. Resists skimming. May flag
when personal wealth extraction is compromising national accounts.

**Security Chief:** Pushes for suppression options. Loyal to personal
wealth. Gives military and intelligence framing on events. Hidden
loyalty threshold — can defect if trust too low.

**Diplomatic Aide:** EU-aligned. Gives relationship context and
diplomatic framing. Whistleblower risk if regime drifts authoritarian
while aide is assigned to sensitive items.

### Advisor Slot System

Player starts with 2 advisor slots per day. More slots unlock as
game progresses (Shadow Cabinet purchase or axis threshold). Choosing
which advisors to bring into which situations is a strategic layer —
an advisor not assigned is unavailable that day.

Each advisor assigned to a briefing item provides a distinct lens:
- Finance Minister on sanctions arc: budget impact, cost projections
- Security Chief on sanctions arc: military options, covert responses
- Diplomatic Aide on sanctions arc: NPC relationship context,
  what each party privately wants

### Advisor Trust and Defection

Each advisor has a hidden trust rating. Actions that conflict with
their agenda drain trust. Below a threshold:
- Finance Minister leaks skim data to opposition
- Security Chief may back a coup faction quietly
- Diplomatic Aide may contact EU or USA with internal information

Advisors can be leveraged against each other — Security Chief
approves of Diplomatic Aide's removal if trust with Security Chief
is high enough.

---

## FEATURE 6: BACKCHANNEL SYSTEM

### What It Is

A separate covert diplomatic track running parallel to official
diplomacy. Accessible via backchannel button on NPC cards or from
Shadow Cabinet. Visually distinct — dark UI treatment, no record
in the official diplomatic log.

### Detection Risk Factors

- Intelligence level (higher = better OPSEC)
- Other party's intelligence level (sophisticated NPC = harder to hide from)
- Number of intermediaries (Ji-won as broker means three parties know)
- Which apparatus used (personal shadow network = higher risk than
  state apparatus)

### Discovery Consequences

Consequences vary by who discovers the backchannel:
- Bill discovers DPRG backchannel: existential diplomatic crisis
- Sadam discovers quiet EU energy conversation: relations hit
- Ji-won discovers almost anything: leverage he files away for later
- Marsha discovers Arabia backchannel during reform commitments:
  conditional EU funds suspended

### Backchannel Promises

Promises made in backchannels carry their own leverage. If Sadam
agreed to something covertly and you don't deliver, he doesn't go
public — he just remembers. More dangerous long-term than broken
public commitments because there's no diplomatic resolution path.

---

## FEATURE 7: UN SUMMIT

### Structure

Recurring mandatory briefing item every 20-30 days. Player cannot
advance the day until the Summit item is engaged. All NPCs present
simultaneously, reacting to each other's positions in real time.

Declarations are heard by everyone. Breaking a UN commitment hits
credibility with all parties at once. NPCs contradict each other
publicly — player navigates competing demands in front of all.

### Auto-Position Feature

Claude reads current relations and recent declarations, generates
a holding statement that keeps positions consistent without committing
to anything new. Player can approve as-is, edit, or write their own.
Prevents the Summit from being a mandatory time sink on quiet days
while preserving stakes on consequential ones.

### Group Chat UI

Running thread where multiple NPCs post reactions in real time as
player makes declarations. Sadam responds to your speech. Bill
counters. Marsha endorses and qualifies. Ji-won says nothing publicly
but intel notes it. Russia and China have their own dynamic — Russia
challenges Western framing, China says little but positions quietly.

---

## FEATURE 8: RUSSIA AND CHINA — PASSIVE INTEGRATION

### Session 7 Scope: Passive World Actors

Russia and China appear in Session 7 as passive world actors. They:
- Appear in world events and affect the NPC-to-NPC matrix
- Are visible in the right sidebar as NPC cards with relations bars
- React through briefing items (Russia responds to a USA sanctions
  move, China reacts to EU partnership announcements)
- Participate in UN Summit as voices in the thread
- Cannot be directly negotiated with yet

Full dialogue integration (authored personality containers, rapport
system, negotiation panels) is a Session 8 deliverable.

### Personality Sketches (For World Event Generation)

**Russia:** Declining great power with revisionist ambitions. Energy
leverage is the primary instrument. Transactional but unpredictable —
rewards loyalty harshly and punishes defection the same way. Sphere
of influence framing, not deal-making. "This is about who you belong
to, not what you get."

**China:** Long-term patience as strategic weapon. Infrastructure as
soft power. Never threatens directly but makes dependency feel
inevitable. Belt and Road framing — you don't notice you've been
captured until you need them. Silence is not neutrality.

### NPC-to-NPC Matrix Impact

Russia and China presence changes the bilateral score dynamics:
- US-Russia tension creates opportunities for player to exploit
- China-Arabia energy relationship affects oil pricing indirectly
- Russia-DPRG relationship adds a second patron for Ji-won
- EU-Russia hostility makes EU alignment more costly if Russia
  has leverage over Europa

---

## FEATURE 9: TECH LEVEL REDESIGN

### Passive Relationship-Weighted Gain

Replaces the non-functional explicit deal-based acquisition.
Each NPC contributes tech passively each turn based on current
relations and a quality weight:

| NPC | Weight | Tech Type |
|-----|--------|-----------|
| EU | 1.00 | R&D, full transfer |
| USA | 0.90 | Military and commercial |
| DPRG | 0.50 | Weapons and surveillance |
| Arabia | 0.30 | Energy infrastructure only |

Formula: `tech_gain = sum of (relations/100 × weight × BASE_TECH_RATE)`
BASE_TECH_RATE = 0.5 (tunable in testing)

Example at EU 80, USA 60, Arabia 70, DPRG 40: gain ≈ 0.875/turn

### Performance Multipliers

**Negotiation outcomes:** Successful deals with EU and USA accelerate
tech gain. A well-negotiated partnership transfers more than a
grudging one. Negotiation quality modifier applied to that NPC's
contribution for the following turn.

**Tax base size:** Larger GDP means more domestic R&D capacity.
Economy efficiency feeds back into tech growth, which feeds back
into economy efficiency. Virtuous cycle for budget-disciplined
players. Compounding disadvantage for heavy skimmers.

### What Tech Level Unlocks

- **EU relationship ceiling:** Rises with tech level. Tech and EU
  alignment reinforce each other deliberately.
- **Economy efficiency modifier:** Real GDP multiplier, not cosmetic.
- **Intelligence effectiveness:** Higher tech = better signals
  intelligence, lower detection risk on operations.
- **Education multiplier (Session 8+):**
  `effective_tech_gain = raw_tech_gain × (1 + education_bonus)`
  Neither relationships alone nor education alone is sufficient
  to become a tech player.

### Strategic Asymmetry

Arabia-aligned players accumulate wealth but not tech capability.
EU-aligned players build capability that compounds over time.
The gap widens invisibly over many eras — then suddenly it isn't
invisible anymore. This is the middle power transition made concrete:
at high tech, Europa generates its own transfers. Bill stops offering
and starts asking.

---

## FEATURE 10: GM INFERENCE LAYER — ARCHITECTURE AND PROTOTYPE

### The Problem It Solves

The pre-authored consequence framework handles known deal options
but cannot reason about novel player proposals. Player types "I want
to make Arabia Europa's exclusive energy partner" in freeform
negotiation — the NPC generates a convincing response but the backend
doesn't know to penalize competing suppliers, adjust the oil price
formula, flag the conflict with the active USA energy deal, or
move the Russia-Arabia bilateral score.

### Architecture

```
Player input
    → Validity check (is this within the game's mechanical scope?)
        → If NO: NPC declines in character, not a system error
        → If YES: GM inference call
            → Structured consequence object
                → NPC response prompt (receives consequences)
                → Consequence engine (executes consequences)
```

### GM Inference Call — What It Answers

1. What is the player proposing?
2. Who does this affect beyond the NPC in the room?
3. What existing deals or commitments does this contradict?
4. What are the second and third order consequences?
5. What is the commitment type and binding level?
6. Is this proposal credible given the current game state?

Output: structured JSON consequence object passed simultaneously
to the NPC response prompt and the consequence engine.

### Key Design Principle

The GM does geopolitical reasoning. The NPC does character work.
These are different cognitive tasks currently collapsed into one call.
Separating them means Sadam-as-character reacts to a specific offer
from a specific player with a specific history, while Claude-as-GM
understands what "exclusive energy partner" means across the whole
relationship web.

### Session 7 Scope: Prototype Only

Full GM inference implementation is a Session 8 deliverable.
Session 7 scope: architect the call structure, build a working
prototype for one NPC (Sadam) and one proposal category
(energy partnerships). Test the structured JSON output format.
Validate that the consequence object passes correctly to both
the NPC prompt and the consequence engine before scaling.

### Relationship to Authored Pillars

The GM inference layer does not override the consequence framework —
it extends it to cover cases the framework didn't pre-author.
Hard-coded rules still take precedence. The GM infers consequences
for novel inputs; it never contradicts authored ones.

---

## FEATURE 11: SCRIPTED BRANCHING CRISES

### Framework

Hand-crafted Sophie's choice moments that fire at specific game
state thresholds. Both options hurt. Neither is clean. The framework
is the Session 7 deliverable — not an exhaustive crisis library.

Each crisis has:
- Trigger condition (game state thresholds)
- Opening event card (the situation as presented to player)
- 3-4 response options (each with distinct consequence profiles)
- Follow-up consequences in subsequent briefings

### The Leak (Reference Crisis — Build First)

**Trigger:** DPRG deal active AND USA relations above 60

**Event:** "Classified documents reveal your back-channel with Ji-won"

**Options:**
- Deny publicly: USA -5, DPRG +5, stability -8, scandal risk
- Admit and apologize: USA +10, DPRG -15, approval -10
- Blame a minister: stability -5, one-time scapegoat, clears event
- Let Ji-won handle it: -$3B personal, DPRG suppresses story

**Design note:** Option 4 (let Ji-won handle it) is the leverage
system made concrete — you're paying him to clean up your mess,
and he remembers that.

### Additional Crisis Templates (Design in Session 7, Implement in Session 8)

- The Opposition Defector: key minister leaks financial records
- The Border Incident: military provocation from an adjacent nation
- The IMF Visit: international audit team arrives unexpectedly
- The Assassination Attempt: staged or real, each has different
  framing options

---

## FEATURE 12: EMERGENCY TOKEN SYSTEM

### Structure

3 tokens per era. Each token pauses the day clock for one free
action: emergency negotiation, crisis response, or covert operation.
Tokens regenerate at the start of each new era.

### Why They Matter

Tokens become more valuable when you don't know how long the era
will last (event-driven era transitions) and when a scripted crisis
fires at an inopportune moment. A player with 0 tokens when The Leak
fires has no safety valve — they take the crisis as presented.
A player who hoarded tokens has options.

### Token Visibility

Tokens displayed in left sidebar near the day counter. Current
token count always visible. No ambiguity about whether you have
the option.

---

## IMPLEMENTATION SEQUENCING

### Pre-Session 7 (Infrastructure Sprint)
1. Player accounts (Supabase Auth)
2. Test account system with reset, seeded snapshots, cheat panel lock

### Session 7 Phase 1 (Foundation)
1. Turn structure redesign (ambient/event modes, day advancement)
2. Era system (transition triggers, historian write-up button)
3. Dashboard rebuild (desktop three-panel, mobile card feed)
4. End of day processing mapped to existing EOT system

### Session 7 Phase 2 (Briefing System)
5. Daily briefing structure and item architecture
6. Player-initiated events
7. Urgency escalation system
8. The Arabia Sanctions arc as first GM-generated event

### Session 7 Phase 3 (New Features)
9. Advisor system (3 advisors, slot system, trust/defection)
10. Backchannel system (detection risk, discovery consequences)
11. UN Summit (mandatory item, auto-position, group chat UI)
12. Tech Level redesign (passive gain formula, performance multipliers)
13. Russia/China passive integration (right sidebar, world events)
14. Emergency token system

### Session 7 Phase 4 (Architecture)
15. GM Inference Layer prototype (Sadam + energy partnerships)
16. Scripted branching crisis framework + The Leak implementation

---

## OPEN QUESTIONS (Carry to Session 7 Design Review)

1. **GM era-close scoring:** Does accumulated threshold weight trigger
   a GM proposal, or do individual thresholds each fire independently?
   Pinned — needs more thought as game gets longer.

2. **Advisor slot unlock conditions:** Shadow Cabinet purchase vs.
   axis threshold vs. era count? Not yet decided.

3. **Backchannel UI specifics:** Dedicated panel or modal overlay?
   How does it feel visually distinct without being a full screen change?

4. **Russia/China passive briefing frequency:** How often do they
   appear in world events in Session 7? Needs tuning in testing.

5. **Tech Level tier thresholds:** What are the breakpoints and what
   does each tier unlock specifically? Needs design before implementation.

---

## DESIGN PRINCIPLES TO PRESERVE

- Hard-code consequences, author personalities, seed starting conditions,
  let Claude generate everything in between
- Sophie's choice principle: best crises force binary where both options hurt
- Mechanics create dependency loops — solving immediate problems deepens
  structural vulnerabilities
- Players should feel clever and compromised simultaneously
- Never let Claude decide consequences — it narrates them
- The game is a narrative generator, not a conventional strategy game
- Success measured by quality of emergent stories, not win/lose conditions
- The player never has to grow — staying small is a legitimate playstyle
- Static choices should never dominate negotiation
