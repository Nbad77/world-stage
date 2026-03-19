# WORLD STAGE — Axes Redesign Design Document
Generated: March 13, 2026

---

## CORE PRINCIPLE

Axes should create pressure on each other, not race to max in parallel.
The prerequisite web forces trade-offs in sequencing — sequencing is where
the interesting strategic stories live.

**Soft prerequisites, not hard blocks.** Costs become prohibitive and effects
are severely diminished without prerequisites, but the player isn't hard-locked.
This preserves agency while making the logic feel realistic.

---

## THE AXES

Current seven axes, proposed additions in brackets:

1. Military Strength
2. Intelligence
3. Political (patronage / elite capture)
4. Resource Development
5. Tech Level
6. Education
7. [Diplomatic]
8. [Militia / Loyalty Brigade — split from Military]

---

## PREREQUISITE WEBS

### What gates what

**Political control (elite capture, judiciary, press suppression):**
- Full judicial capture requires Political axis ≥ 3 AND stability ≥ 40
- Cannot hit Political axis 6+ without some domestic suppression history
- Dissolving opposition requires Loyalty Brigade tier ≥ 2 OR Military axis ≥ 5
- Regime type label gates certain purchases (see Regime Type section below)

**Extraction / economic:**
- High extraction tiers require Resource Development axis ≥ 3
- Max extraction requires Education ≥ Developed (Level 2) — educated workforce
  enables sophisticated financial extraction without economic collapse
- Sovereign wealth diversion at scale requires Tech Level ≥ Tier 2 (financial
  infrastructure to move money cleanly)

**Military:**
- Military axis ≥ 5 requires Tech Level ≥ Tier 2 (modern equipment needs
  modern logistics and maintenance capability)
- Military axis ≥ 7 requires Education ≥ Basic (Level 1) (officer corps,
  technical specializations)
- Military axis ≥ 8 requires Intel axis ≥ 4 (operational security for
  advanced military capability)

**Intelligence:**
- Intel axis ≥ 4 requires Tech Level ≥ Tier 1
- Intel axis ≥ 6 requires Tech Level ≥ Tier 3 (signals intelligence,
  cyber capability)
- Shadow apparatus tier upgrades require Political axis ≥ 2 (legal cover
  for covert ops)

**Diplomatic:**
- Diplomatic axis is structurally incompatible with domestic suppression
  past certain thresholds (see Western alignment ceiling below)
- Diplomatic axis ≥ 5 requires Education ≥ Basic (credible diplomatic
  corps needs educated staff)
- Cannot maintain Diplomatic axis ≥ 7 AND Judicial Capture — the
  contradiction becomes internationally untenable

---

## STABILITY: TWO-COMPONENT MODEL

The displayed stability number is the same, but its *composition* determines
failure modes. Backend tracks both components; frontend shows the sum.

### Legitimacy Stability
Sources: approval, functioning institutions, education, clean elections,
democratic track record, Diplomatic axis.

Characteristics:
- Resilient to economic shocks and political pressure — institutions absorb them
- Vulnerable to scandals and legitimacy crises
- Fails slowly and visibly — player sees it coming
- Recovers through approval-building actions

### Coercion Stability
Sources: Military Strength, Loyalty Brigade deployment, suppression actions,
elite patronage payments, Militia integration (see below).

Characteristics:
- Maintains at low approval — this is the point
- Requires active maintenance spending; let it lapse and it degrades
- Fails suddenly and catastrophically with minimal warning
- Recovery requires either re-deployment (expensive) or transitioning to
  legitimacy stability (slow)

### Why composition matters
- A player at 65% from legitimacy is stable against elite plots but
  vulnerable to scandals
- A player at 65% from coercion is stable against scandals but vulnerable
  to coup and sudden collapse
- Switching paths mid-game is possible but expensive: dismantling coercion
  infrastructure while building legitimacy doesn't produce 0 instability,
  it produces a dangerous gap period

### Stability floor from regime type
- Democracy with functioning institutions: high legitimacy stability floor,
  coercion stability hard-capped low
- Soft authoritarianism: mixed, both systems partially functional
- Full dictatorship: high coercion stability ceiling, legitimacy stability
  degrades unless actively maintained (expensive)

---

## MILITARY / MILITIA SPLIT

### Current state
Military axis (formal) and Loyalty Brigades (personal) are independent
with no interaction.

### Proposed split
Two distinct institutions with different capabilities and loyalty profiles:

**Formal Military:**
- Professional, capable, potentially disloyal
- Affected by Military axis upgrades, equipment purchases
- Decays without maintenance spending
- High capability = high coup threat if not politically managed

**Militia / Loyalty Brigades:**
- Less capable, highly loyal to the player personally
- Funded from personal wealth (stays personal, doesn't transfer to successor)
- Lower ceiling on what they can accomplish militarily
- No coup threat — they're yours

### The merger mechanic
At Soft Authoritarianism+ regime label, option appears: **Integrate Loyalty
Brigade into Military Command.**

Effects:
- Combined capability (highest of the two, not additive — professionalization
  is hard to undo)
- Reduced dual maintenance cost
- Coup protection spike — most loyal troops now most capable troops
- Loses deniability — it's now a state institution (Marsha can formally object,
  -5 EU relations)
- Military effectiveness reduced by 15% — loyalists aren't as professional
- Irreversible — once integrated, cannot re-separate

**This is a character-defining moment.** A player who does this is committing
to a specific kind of regime.

---

## LOYAL GENERALS / LOYAL INTELLIGENCE CHIEFS

Installing politically reliable but less competent leadership.

### Loyal Generals
Costs: Political axis ≥ 3 to unlock. Personal wealth expenditure.
Effects:
- Coup probability −30% (approximate)
- Military strength cap reduced (can't maintain equipment, run complex ops)
- Military decay rate +10% (incompetent logistics)
- Ceiling on military accomplishments shrinks even as personal security improves

### Loyal Intelligence Chief
Costs: Political axis ≥ 3. Personal wealth expenditure.
Effects:
- Coup/defection protection +20%
- Intel intercept quality degrades (reports what you want to hear)
- Detection risk on your own covert operations +15% (bad at their jobs)
- At high Education + Loyal Intel Chief: specific vulnerability — educated
  population, blind intelligence apparatus, player doesn't see dissent forming

Both reversible but costly. Restoring capable leadership after purging:
- Takes 3+ days of transition
- Costs money
- The capable officers who survived will remember being passed over
  (trust −10 with restored chief)

---

## HIGH MILITARY WITHOUT POLITICAL LOYALTY = COUP AMPLIFIER

Military axis measures capability, not loyalty. A strong military with
low Political axis is a liability.

**Rule:** Military axis > Political axis by more than 3 points increases
coup probability meaningfully (not linearly — threshold-based spike).

The Political axis becomes the thing that converts raw military power
into *your* power. Players who build military without building political
control are creating an institution that doesn't owe them anything.

The Loyal Generals mechanic is one way to solve this. The other way is
the merger mechanic. Both work. Neither is free.

---

## INTELLIGENCE AXIS: POLITICIZATION PENALTY

Higher intelligence capability is good. But a highly politicized
intelligence apparatus tells you what you want to hear.

**Rule:** At Political axis ≥ 7 AND Intel axis ≥ 5, intelligence
intercepts gain a "distortion" flag. Some percentage of intercepts
are marked as potentially unreliable. Player must spend to verify
(extra cost, extra time) or take them at face value.

This models the real-world intelligence failure mode of authoritarian
regimes — the apparatus reports upward what leadership wants to be true.

The Spy Chief advisor archetype already has a trust/defection mechanic.
This is a structural version of the same problem that exists even
with a loyal chief.

---

## DIPLOMATIC AXIS

### What it is NOT
Just spending money on NPC relations. That's already in the game.

### What it IS
Relationship resilience and structural access. A transactional player
buys relations that are brittle. A diplomatic player builds relationships
that absorb shocks.

### Mechanics

**Resilience:**
- Relations decay slower (−1 per turn becomes −0.7 per turn at Diplomatic 5+)
- NPC pressure events give more runway before confrontations
- Broken commitments hurt more (reputation makes violation more conspicuous)
  BUT recovery path also exists (high diplomatic axis = apology is credible)

**Structural access:**
- At Diplomatic ≥ 4: cooling-off options appear in crises not available
  to low-diplomatic players (quiet back-channel resolution)
- At Diplomatic ≥ 5: summit credibility starts higher, broken commitments
  partially absorbable
- At Diplomatic ≥ 6: NPC-to-NPC manipulation becomes constructive as well
  as destructive (can bring two NPCs closer together for your benefit)
- At Diplomatic ≥ 7: exclusivity deal structures available that require
  reputation for honoring agreements

**The incompatibility:**
Diplomatic axis is structurally incompatible with aggressive authoritarian
consolidation past a certain threshold. A regime that liquidates journalists
and captures the judiciary cannot maintain a credible diplomatic corps.

Hard ceiling: Diplomatic axis cannot exceed 6 with Judicial Capture active
AND Press Suppression active. Cannot exceed 8 at Totalitarian regime label.

This makes Diplomatic axis the clearest path indicator for Democratic Transition
ending — and the thing you sacrifice most visibly when you go authoritarian.

---

## WESTERN ALIGNMENT CEILING

Each domestic suppression axis level above a threshold hard-caps what
EU relations can reach, regardless of rapport. Systematic, not just
event-based.

Proposed caps:

| Domestic Suppression State | EU Relations Hard Cap |
|---------------------------|----------------------|
| None | 100 (no cap) |
| Press Suppression only | 85 |
| Judicial Capture | 75 |
| Press + Judicial | 65 |
| Opposition Dissolved | 55 |
| Liquidate Journalists | 40 |
| All suppression active | 30 |

Marsha references the cap in-character when it fires, not as a system error.

---

## EDUCATION INTERACTIONS (additions to existing 8B design)

**Education makes suppression more expensive at higher levels:**
- Education Level 2: propaganda campaigns cost +20%, diminishing returns
  on approval gain
- Education Level 3: suppression actions cost +10% approval loss (population
  knows what's happening), coup resistance +20% (educated populations are
  harder to intimidate into supporting a coup)

**Education vs. extractability:**
- Higher education enables more sophisticated extraction (can hide it better,
  more financial infrastructure) but also makes the population more aware
- Brain drain at Level 3 + low approval is already in spec — this is
  the political version of the same tension

**Education gates:**
- Military axis ≥ 7 requires Education ≥ Basic
- Diplomatic axis ≥ 5 requires Education ≥ Basic
- Max extraction tiers require Education ≥ Developed

---

## REGIME TYPE AS GATE (not just label)

Regime type label should be prescriptive for certain purchases, not just
descriptive. The label shift IS the unlock.

| Purchase | Minimum Regime Type Required |
|----------|------------------------------|
| Militia integration | Soft Authoritarianism+ |
| Loyal Generals | Patronage State+ |
| Loyal Intel Chief | Patronage State+ |
| Liquidate Journalists | Kleptocracy or higher |
| State Media Takeover (full) | Soft Authoritarianism+ |
| Oligarch advisor | Patronage State+ |
| Propagandist advisor | Soft Authoritarianism+ |

Players who want to stay in the democratic range are hard-capped on
certain authoritarian tools. This makes the label itself consequential
rather than cosmetic.

---

## SUSTAINABILITY GAP

Reaching a high axis level and *holding* it are different problems.

**Rule:** The axis level a player can *sustain* should be capped by
economic output. Military axis level 8 requires ongoing budget commitment;
if extraction + skimming depletes the national budget, maintenance
fails and the axis degrades.

This connects to the education-economy feedback: heavy skim → economy
degrades → can't maintain military → military decays faster → coup
risk rises. The dependency loop that punishes short-term thinking.

---

## COLLAPSE TYPE DETERMINATION

Collapse type is now determined by game state at the moment of collapse,
not by arbitrary trigger. This makes the exile sequence feel earned
rather than scripted.

### Coup d'état
**Triggers when:**
- Military axis high (≥ 6) AND Political axis low (≤ 3)
- OR: Loyal Generals NOT installed AND Military Strength ≥ 70 AND
  approval < 25
- OR: Military axis high AND stability < 20

**Character:** Military faction seizes power. DPRG/Russia connection
may help you return. Comeback requires military faction support.

### Democratic Revolution
**Most likely when:**
- Education Level ≥ 2 (educated population, organized)
- Approval < 20 AND legitimacy stability was primary (regime didn't
  build coercion infrastructure)
- Press suppression absent or recently imposed (population has channels
  to organize)

**Character:** Mass movement. Marsha approves. Bill sends cautious support.
Comeback requires mass movement backing — and you probably can't get it
because they just kicked you out.

### Authoritarian/Elite Coup
**Most likely when:**
- Political axis high (elite capture), but trust broken with specific
  elite factions
- Oligarch advisors with low loyalty
- Personal wealth very high (elite factions want a cut you stopped giving)

**Character:** Palace coup, not popular uprising. Successor is a Hardliner
from your own political network. DPRG/Russia potential supporters. Comeback
requires elite faction realignment — expensive.

### Military Coup (incompetent military path)
**Most likely when:**
- Loyal Generals installed (reduced capability but loyal)
- BUT coup fires from external pressure when the loyal-but-incompetent
  military fails to handle a real crisis
- Stability collapses from external event the military couldn't manage

**Character:** Different from the strong-military coup. This one happens
because you tried to protect yourself from your own generals and left yourself
unable to handle real threats.

### Debt Crisis / IMF Forced Transition
**Most likely when:**
- National budget deeply negative multiple turns
- Pre-warning ignored
- EU/USA withdraw support

**Character:** Not a coup or revolution — a managed collapse. Comeback
requires external creditor backing. Most expensive path back.

### Voted Out (Voluntary / Election Loss)
**Triggers when:**
- Election mechanic fires AND approval below win threshold AND player
  accepts result (or approval too low to steal)

**Character:** Cleanest exit, least damaged relationships. Comeback
is actually most plausible — you didn't destroy everything on the way out.

---

## EU PEACEKEEPING / INTERVENTION CONDITION MECHANIC

When EU (or USA) saves the player from imminent collapse — intervenes
to stabilize rather than let them fall — they arrive with conditions
that must be maintained or the peacekeepers leave.

**EU Peacekeeping Conditions (examples):**
- Press suppression must be reversed within 3 days
- No new suppression actions for X days
- Election must be held within Y days and be internationally observed
- Judicial Capture must be dismantled (long process — each step costs
  stability as institutions rebuild)
- Intel budget must drop below a ceiling (no secret apparatus)

**Mechanics:**
- Conditions tracked explicitly in game state (condition_type, deadline,
  peacekeeper_day_count)
- Each day peacekeepers are present: stability +5, but sovereignty
  reduced (some actions unavailable)
- Breaking a condition: peacekeepers begin withdrawal (3-day notice),
  Western relations hit, stability loses the bonus abruptly
- Honoring all conditions: stability gradually transfers from coercion
  to legitimacy type — the peacekeepers are doing the work of institutional
  rebuilding you couldn't do yourself

**NPC dialogue during intervention:**
- Marsha: formal, watching closely, willing to extend timeline for
  genuine progress
- Bill: pragmatic, cares less about conditions than stability, may
  push Marsha to ease requirements if geopolitical situation warrants
- Sadam: quiet disapproval — you needed foreigners to save you
- Volkov: public condemnation, private message offering an alternative
  if you expel the peacekeepers

---

## STABILITY: HOW EU INTERVENTION INTERACTS WITH TWO-COMPONENT MODEL

EU intervention adds a third temporary stability source:
**External Stability** — high while peacekeepers present, collapses
immediately if they leave.

During intervention, backend tracks:
- legitimacy_stability (growing slowly as institutions rebuild)
- coercion_stability (degrading as suppression tools are removed)
- external_stability (peacekeeper bonus, flat)
- displayed_stability = sum of all three

Transition from intervention to self-sustaining:
- If player honors conditions long enough, legitimacy_stability grows
  to replace external_stability before peacekeepers leave
- If player breaks conditions early, external_stability vanishes before
  legitimacy_stability is built — dangerous gap

---

## AXIS REBALANCING FOR OPEN WORLD (Session 9/10)

Current problem: axes can be maxed in roughly one era. This breaks
open-world pacing where eras are the narrative containers.

**Proposed approach: per-era soft caps**

Each axis has a maximum achievable level per era determined by starting
conditions and prerequisite satisfaction. The cap rises each era based
on what was built previously.

Example for Military:
- Era 1 soft cap: 6 (limited by fresh-start budget)
- Era 2 soft cap: 8 (if budget disciplined in Era 1)
- Era 3 soft cap: 10 (if prerequisites met)

Hard cap stays at 10 (or whatever max is). Soft cap means costs increase
dramatically above the era threshold — not impossible, just very expensive.

**Alternative: cooldown between upgrades**

Each axis upgrade requires a minimum number of days before the next
purchase. Scales with the axis level — higher levels require longer
consolidation periods. Represents institutional change taking time.

Example:
- Level 1→2: 3 days
- Level 4→5: 7 days
- Level 7→8: 14 days

This is simpler to implement and more legible to the player.

**Recommendation:** Cooldown approach for implementation simplicity,
per-era soft caps as a design target to tune during Session 10 testing.

---

## BLACK BUDGET SYSTEM

### The Core Mechanic

Black budget operations are available from Day 1, no regime gate required.
Historically accurate — every democracy runs them. The constraint isn't
access, it's two things: funding source and operational direction.

**Funding source is a choice with consequences:**

| Source | Signal | NPC Visibility | Consequence |
|--------|--------|----------------|-------------|
| National budget allocation | Democratic intent | Visible to all with intel capability — normal state behavior | Legitimizes the operation; exposure is a scandal, not a revelation |
| Personal skimmed wealth | Consolidation intent | Visible to high-tier intel NPCs as anomalous | Exposure is existential — you're running a private army with stolen public money |

The player doesn't have to declare their path. The funding choice IS the
declaration, made incrementally over many days before the consequences
are fully visible.

### What National Budget Black Ops Signal

Spending national budget on black ops is a democratic government doing
what democratic governments do. The USA does this. France does this.
The UK does this. The constraint is institutional:

- Budget line is technically auditable (opposition, press, EU observers
  can eventually find it)
- Forces the player to balance black ops against visible public spending
- As democracy grows — higher approval, higher stability, stronger GDP —
  the player can allocate more without political cost. A legitimate, popular
  government with a strong economy can sustain a meaningful intelligence
  apparatus without scandal. The democratic path earns more black budget
  capacity over time.
- Marsha sees this as normal. Bill sees this as normal. Neither reacts
  unless the operations cross the domestic use threshold.

### What Skimmed Black Ops Signal

Using personal wealth (skimmed from national budget) to fund operations
is categorically different. You are:

- Stealing public money to build a private covert capability
- Creating a capability that is personal, not institutional — it travels
  with you into exile, it doesn't transfer to a successor
- Signaling to any NPC intelligence agency watching that you are
  consolidating personal power, not building state capacity

A player who starts skimming Day 1 and immediately funnels that money
into black budget operations is broadcasting their trajectory. They may
not realize it. The NPCs notice before the consequences arrive.

### The Democratic Skim Ceiling

To maintain a functional democracy, the player should not be able to
skim much at all. Not because it's prohibited, but because:

- A democratic government with free press and opposition has exposure
  risk for financial irregularities
- Education Level 2+ populations are harder to deceive about where
  the money went
- High approval democratic governments don't *need* to skim — the
  legitimate salary and benefits of a popular head of state are substantial
- Marsha's EU conditions often include financial transparency requirements
  that make large-scale skimming mechanically risky

The skim ceiling for a player maintaining genuine democratic metrics
(approval 60+, free press, clean elections) should be low — maybe
$0.5-1B per era before scandal risk becomes prohibitive. The player
can choose to push past it, but they're making a visible choice.

### The Skim Cascade

A player who goes heavy on early skimming sets off a cascade:

1. Skim depletes national budget → less available for public services
2. Less public spending → approval pressure → stability pressure
3. Falling approval → need for suppression to maintain stability
4. Suppression requires personal wealth → need to skim more
5. More skim → less national budget → back to step 1

This is the authoritarian dependency loop made concrete. The player
who starts skimming fast isn't just making a financial choice — they're
boarding a train with a specific destination.

### Domestic Operations Gate (The Line)

Black budget operations divide into two categories regardless of funding source:

**Foreign operations** (available to democracies):
- Foreign Influence Ops (destabilize foreign NPC's domestic situation)
- Covert intelligence gathering abroad
- Proxy support to foreign factions
- Backchannel diplomatic operations

**Domestic operations** (authoritarian gate):
- Militia deployment against domestic population
- Suppression of internal political opponents
- Surveillance of domestic press and opposition
- Loyalty Brigade domestic use beyond security theater

The moment a player crosses the domestic threshold, regime label shifts.
That shift is visible to all NPCs with intelligence capability.
It is not reversible without EU intervention conditions.

---

## NPC INTELLIGENCE AND COERCION

### All NPCs Have Intelligence Agencies

The player isn't the only one running covert operations. Every NPC
has an intelligence capability that watches the player and each other.
NPCs use what they find.

**Intelligence capability by NPC (approximate):**

| NPC | Intel Capability | What They Watch |
|-----|-----------------|-----------------|
| Bill (USA) | Highest | Everything — financial flows, military moves, domestic ops, skim patterns |
| Marsha (EU) | High | Financial transparency, democratic backsliding, press/judicial status |
| Volkov (Russia) | High | Military movements, Western alignment signals, elite faction health |
| Wei (China) | High | Economic dependency creation, long-term strategic drift |
| Sadam (Arabia) | Moderate | Energy deals, Western alignment, regime stability |
| Ji-won (DPRG) | Low-moderate | Military capability, isolation signals, other NPC relationships |

### How NPCs Use What They Find

**Leverage:** An NPC who discovers your black budget operations, skim
patterns, or covert actions files that information. It doesn't fire
immediately. It becomes a card they play when they need something —
in negotiations, during crises, as an implied threat when you reject
their offer. "We've had a productive relationship. I'd hate for certain
information to become relevant to ongoing discussions."

**Leaks:** NPCs can choose to leak damaging information to the press,
to other NPCs, or to domestic opposition. This is a weapon, not a
consequence — they choose when to use it for maximum effect. Bill
leaking your skim data to Marsha right before you need EU funds is
a deliberate move, not an automatic system.

**Coercion in negotiation:** NPCs reference what they know in dialogue.
Volkov doesn't say "I know you've been talking to Marsha about
infrastructure funding." He says something that makes clear he knows,
without stating it. The player understands the implication. This is
the intelligence apparatus expressed through NPC voice rather than
through a mechanical notification.

**Coalition coercion:** If usa_eu bilateral score is high, Bill and
Marsha can coordinate what they know. You face a joint pressure event
that references information from both their intelligence files
simultaneously. The combined weight is more than either alone.

### The Player's Counter-Moves

Higher intel capability = better awareness of what NPCs know about you
and what they're planning to do with it.

- **Tier 1 intel:** You know there's an NPC intelligence operation
  targeting you. General awareness.
- **Tier 2 intel:** You know which NPC, rough scope of what they've
  found, whether they've shared it with other NPCs.
- **Tier 3 intel:** Specific intelligence on what they have, when
  they're planning to use it, who they've told. Allows preemption —
  you can make a move before the lever gets pulled.

Higher diplomatic axis = more resilience when the lever does get pulled.
A player with strong diplomatic standing can weather a leak that would
destroy a player with no diplomatic capital.

**The preemption options** (once Tier 3 intel reveals an imminent leak):
- Get ahead of it publicly (reduces damage, costs approval)
- Approach the NPC directly in backchannel (expensive, but disarms them)
- Preemptively leak something on *them* (escalation, damages the bilateral
  relationship, but removes the card)
- Do nothing (gamble that the leak won't land, or that you can absorb it)

### NPC Intelligence and the Black Budget Funding Source

Bill's intelligence apparatus specifically tracks financial flows. A player
funding black ops from skimmed personal wealth generates a pattern that
differs from national budget funding — the money moves differently, the
vendors are different, the paper trail (such as it is) looks different.

At high intel capability, Bill can distinguish the two. This feeds directly
into his assessment of the player's democratic trajectory and his
willingness to maintain the relationship. A player using national budget
for black ops is a democratic partner with an intelligence apparatus.
A player using skimmed money is building a personal power base.
Bill has seen this before. He knows what comes next.

---

## OPEN QUESTIONS

1. **What is the maximum level for each axis?** Currently 10 is implied.
   Does this change with the new prerequisite structure?

2. **How do axis rebalancing changes interact with pre-redesign saves?**
   Migration strategy needed.

3. **Diplomatic axis implementation priority.** This is a new axis, not
   a redesign of an existing one. Does it ship in Session 9 alongside the
   narrative engine, or is it a Session 10 item?

4. **Militia/Military split — is Militia its own axis or just a renamed
   Loyalty Brigade?** The current brigade system is tier-based (1-3),
   not an axis. Decide before implementation.

5. **Two-component stability — does the player ever see the split, or
   only the sum?** Strong case for opacity (the discovery that your
   stability was coercion-based is part of the surprise when it fails)
   but some case for a cryptic hint in historian voice.

---

## WHAT NEEDS TO HAPPEN BEFORE IMPLEMENTATION

1. This design conversation → design doc (this file)
2. Decide on open questions above
3. Session 9 design conversation for narrative engine
4. Axis rebalancing spec as part of Session 9 or early Session 10
5. Claude Code implementation in dedicated session (not bundled with 9A/9B
   — this is architectural enough to deserve its own session)

---

## BLACK BUDGET PHASE PROGRESSION

### Phase 1 — Democratic Black Budget (no regime gate)
Available from Day 1. Foreign ops only. Funding from national budget
is normal state behavior; funding from skim is an early warning signal
that NPCs with sufficient intel capability will eventually notice.
Exposure = scandal, survivable. Domestic ops blocked.

### Phase 2 — Gray Zone (Patronage State label)
Black budget expands in capability. Domestic ops technically possible
but each use risks legitimacy heat. Western NPCs shift from "formally
concerned" to "quietly calculating." Exposure now confirms a pattern
rather than creating one. Both national budget and skim funding still
available, but skim funding at scale is now clearly visible to Bill/Marsha.

### Phase 3 — Authoritarian Integration (Soft Authoritarianism+)
Militia axis gate opens. Full domestic ops available. Merger mechanic
available. Deniability largely irrelevant domestically — no institutions
left to hold you accountable. Western NPCs know. The question is only
whether the relationship survives it. Personal wealth funding is now
the expected mode; national budget funding of covert ops at this stage
is actually less suspicious to Western NPCs (it looks more institutional).

---

## DIPLOMATIC EFFECTIVENESS SYSTEM

### Three Distinct Scores (not axes)

**1. Diplomatic Capacity** — spendable, infrastructure-based
What you buy with diplomatic budget allocation. Size and quality of your
corps, depth of institutional relationships, repair runway after incidents.
Not displayed prominently — it's the infrastructure that makes the other
two scores actionable.

**2. Soft Power** — derived, behavior-based
Reflects what Europa *is* as a country. Cannot be purchased directly.
Calculated from:
- Education level (weight: 25%) — educated population = cultural credibility
- GDP size relative to NPC (weight: 20%) — economic weight commands respect
- Democratic track record (weight: 20%) — clean elections, free press, no
  judicial capture; decays fast when suppression actions are taken
- Legitimacy stability component (weight: 15%) — coercion stability does
  not contribute to soft power
- Resource/military dependency others have on you (weight: 20%) — clients
  who depend on you generate soft power passively

High soft power: NPCs bring opportunities to you. Your democratic claims
are credible. Bill treats you as a partner, not a client.
Low soft power: you are always the supplicant. Offers are discounted.
Your commitments are assumed to be transactional.

**3. Reliability Score** — derived, track-record-based
Your actual commitment-honoring history. Cannot be purchased.
Calculated from:
- Proportion of public commitments honored (weight: 40%)
- Proportion of backchannel promises honored (weight: 30%)
  (weighted lower because NPCs outside the backchannel don't see these,
  but the NPC who was on the other end remembers)
- Summit credibility score (weight: 20%)
- Time since last major deal break (weight: 10%) — reliability recovers
  slowly with consistent good behavior

High reliability: your offers land at face value. NPCs commit faster
because they believe you'll follow through. Credibility arrives in the
room before you do.
Low reliability: every offer is discounted before you speak. NPCs
demand more upfront, shorter installment windows, harder conditions.
"We've been through this before" is now part of every negotiation.

---

## DIPLOMATIC POWER MULTIPLIERS

These factors modify how much leverage NPCs can actually apply against
you when relationships sour. They don't improve relationships — they
change the cost-benefit calculation for NPC pressure.

### Military Strength as Diplomatic Cover
Strong military → smaller countries have less ability to apply meaningful
pressure. They can be angry; they can't make you feel it.

Mechanically: military strength above a threshold reduces the *severity*
of pressure events from lower-tier NPCs. The event still fires. The
consequence is reduced. Great powers (Bill, Marsha, Volkov, Wei) are
not affected by military strength below middle-power transition — they
can still hurt you regardless.

At middle-power transition (Tech Tier 5): military strength begins to
affect great power pressure calculations modestly. Not immunity —
modulation.

### GDP Weight
Large GDP → the NPC has more to lose by souring the relationship.
Marsha's leverage decreases as Europa's economy becomes substantial
enough that the relationship is mutually valuable rather than
patron-client.

Mechanically: GDP above a threshold reduces relation decay rate after
incidents with EU and USA specifically (they have the most to lose
economically). Does not affect DPRG or Arabia significantly — their
relationship calculus is less GDP-sensitive.

### Resource/Military Dependency Network
Countries dependent on Europa's resources or military contracts will:
- Absorb bad behavior longer before applying pressure
- Lobby on Europa's behalf in regional councils and UN
- Reduce the effective cost of aggressive moves by creating a buffer
  constituency

Kompromat on an NPC: active version of dependency.
- Dependent NPC: deferential, tolerates your behavior out of need
- Compromised NPC: controlled anger, cooperates but is looking for exit
  The NPC's dialogue register is distinct — tightly formal, no warmth,
  no rapport-building. They are not your ally; they are your hostage.
- If kompromat is ever burned (leaked, discovered, loses relevance):
  relationship collapses immediately and completely. They have been
  waiting for this.

---

## DIPLOMATIC STANDING (per-NPC)

Distinct from the relation score. A second per-NPC value.

**Relation score**: current health of the relationship. Goes up and down
with deals, incidents, commitments.

**Diplomatic standing**: institutional credibility your corps has built
with that NPC's government over time. Changes slowly.

The distinction matters in crisis:
- Low relations + high standing: they're angry right now, but they still
  respect you as an actor. Repair is possible and your ambassador's calls
  get returned.
- High relations + low standing: you've been paying them and they like
  the money, but nobody at their foreign ministry takes you seriously.
  When the money stops, there's nothing underneath.

### Standing mechanics
- Increases slowly through: keeping commitments, responding to diplomatic
  signals promptly, engaging constructively at summits, proactive outreach
  in quiet periods
- Decreases through: ignored diplomatic signals, broken commitments,
  recalled ambassadors not addressed, escalating pattern of bad behavior
- Standing hits zero → ambassador recall fires automatically
- Standing at zero → diplomatic spending has no effectiveness on that NPC
  until a sustained pattern change is demonstrated (minimum 5+ days of
  clean behavior before standing begins recovering)

---

## THE AMBASSADOR RECALL MECHANIC

### When it fires
- Standing drops below threshold (behavior-driven automatic)
- Sharp single-incident relation drop (NPC choice — a weapon, not automatic)
- Preemptive warning shot (NPC signals displeasure before acting — fires
  as DEVELOPING in briefing before becoming URGENT)

### What it means mechanically
While ambassador is recalled:
- Backchannel options to that NPC unavailable (pipeline offline)
- Cannot initiate formal contact without signaling you're backing down
- Debrief briefing item fires: "Ambassador has returned. She requests
  an audience."

### Debrief quality by diplomatic capacity
- Low capacity: ambassador is rattled, reports NPC was angry, limited
  actionable intelligence. You know there's a problem. You don't know
  what they actually want.
- High capacity: full intelligence picture. Why they're angry specifically.
  What they mentioned twice (the actual ask beneath the official grievance).
  Internal disagreements visible in the room. What the repair path
  probably looks like.

### Options after debrief
- Send ambassador back with a message (costs diplomatic capacity,
  signals repair intent)
- Cold-call the NPC directly (high stakes — works very well or makes
  it worse; bypasses corps entirely)
- Wait for them to send their ambassador first (power play — who blinks)
- Use third-party intermediary (Ji-won for Russia; increases leverage
  cost — Ji-won now knows what you're willing to offer)
- Escalate publicly (aggressive option — makes the dispute visible to
  all NPCs, expensive but sometimes forces resolution)

---

## DIMINISHING RETURNS AND THE DIPLOMATIC WALL

### The buffer model
Each diplomatic spend to soften a blow draws from a per-NPC buffer.
Buffer replenishes slowly through good behavior — commitments kept,
signals responded to, summit engagement, proactive outreach.

If wild moves happen faster than the buffer replenishes:
- Buffer empties
- Diplomatic spending loses effectiveness progressively
- Once empty: spending has *no* effect. The corps is sending messages
  into a void.

### Diplomacy becomes costlier as behavior gets wilder
This is not linear. The cost curve steepens:
- First major incident: diplomatic spend of $1B absorbs most of the blow
- Second major incident (same NPC, within same era): same $1B absorbs less
- Third incident: diminishing returns, standing taking structural damage
- Pattern of incidents: standing degrading regardless of spending —
  the corps can't outrun the reputation your actions are building

### The point of no return
No single announced threshold. Visible in retrospect. The historian
version: "By the fourth era, Europa had accumulated enough grievances
with enough parties simultaneously that no single diplomatic intervention
could address them all."

Mechanically: when standing hits zero with 3+ NPCs simultaneously, a
"diplomatic isolation" flag sets. Briefing items shift in language.
NPCs begin referencing each other's grievances in their own communications
— a coordination dynamic that is worse than facing each NPC individually.
The advisor (if diplomatic-aligned) begins flagging that repair would
require simultaneous progress on multiple fronts, which is structurally
very difficult.

This is the isolated kleptocrat endgame expressed through diplomatic
collapse rather than financial or military collapse.

---

## SOFT POWER AND RELIABILITY IN THE BIOGRAPHY ENGINE

Both scores should appear explicitly in the Session 9B historical verdict.

The historian contrasts them:
- High soft power + low reliability: "Europa commanded respect it could
  not sustain. Partners came to the table believing in what Europa
  represented; they left remembering what it had done."
- Low soft power + high reliability: "Europa was never impressive on paper.
  What it had was a reputation for doing what it said. In the long run,
  that proved more durable than the advantages of larger powers."
- High both: the democratic transition path, rarest ending legacy
- Low both: state capture / isolation endgame


---

## THE POWERFUL AUTHORITARIAN PATH

The hardest path in the game. Harder than democratic transition because
it requires active maintenance of two genuinely contradictory things
simultaneously, forever.

### What It Is

Authoritarianism compounds inward — coercion, extraction, personal wealth.
International legitimacy requires projecting something outward that other
states can justify engaging with. The dictator who manages both isn't
pretending to be democratic — that's the amateur move. They're offering
*substitutes* for democratic legitimacy that sophisticated international
actors can use to justify the relationship.

### The Three Pillars

**Strategic indispensability**
You control something the international system cannot easily replace.
Resources, military position, geographic chokepoint. Other states develop
a vested interest in your stability that overrides democratic objections.
This is the dependency network mechanic elevated to great power logic.

**Stability as export**
The argument isn't "we're good" — it's "the alternative is worse and
we're the only thing preventing it." Bill doesn't love you but needs the
region stable. Marsha doesn't approve but a collapsed Europa is worse
for the EU than an authoritarian Europa. Requires maintaining genuine
stability — a collapsing dictatorship loses this argument immediately.

**Selective international participation**
Engage on issues where your interests align with Western preferences,
stay quiet on the rest. Vote with the USA on something that suits you;
in return they don't push the judicial capture conversation. Fund a UN
development initiative — costs little, generates diplomatic standing
credit. Strategic cooperation on high-visibility issues creates cover
for everything else.

### International Legitimacy Score (hidden)

Distinct from soft power and reliability. Measures whether the
international system has effectively decided to treat you as a legitimate
actor regardless of domestic behavior. Can be high even with low soft
power if you've made yourself indispensable and strategically useful.

**Built by:**
- Resource or military dependency network above threshold
- Stability above threshold (not a failing state)
- Selective cooperation — actively backing key NPC initiatives at summits
  even when it costs something; they have receipts to show their own
  domestic audiences
- Strategic restraint — not doing the most egregious things publicly.
  Liquidating journalists in secret is different from doing it on camera.
- Consistent summit presence — a dictator who goes dark for three summits
  signals weakness or instability

**Costs to maintain:**
- Every major public violation costs legitimacy points, slow to recover
- You're permanently one catastrophic public incident away from losing
  the "we can work with this" consensus
- Western capitals that defend you will drop you the moment defending
  you becomes more costly than replacing you
- Volkov and Wei respect your international standing but also resent it —
  you're playing their game better than they are in certain respects.
  Specific rivalry dynamic.

### The Failure Mode

The powerful authoritarian with international legitimacy doesn't collapse
from a coup or revolution. They collapse from **miscalculation**.

So successful at managing the international community that they believe
they're genuinely untouchable. One move too many. One relationship burned
too publicly. The consensus that protected them evaporates. What looked
like stable equilibrium was actually the international community making
a continuous bet-by-bet decision to keep tolerating you. When the
calculus tips, it tips everywhere simultaneously.

Historian verdict (distinct from all other paths):
"He mistook tolerance for acceptance, and found out the difference too late."

### Bill's Characterization on This Path

Bill isn't naive about authoritarians — the USA has propped up dozens.
What he calculates is whether you're *manageable*. The moment you stop
being manageable — too powerful, too unpredictable, or a domestic
political liability — the relationship ends and ends fast.

The transition from "strategic partner" to "problem to be solved" is
the most dangerous moment on this path. It should feel like it.


---

## DOMESTIC SPENDING REDESIGN: COMMITMENT MODEL

### Core Principle

No allocation sliders. Instead, **ongoing spending commitments**.
Each capability tier costs a fixed amount per day to maintain.
The budget pie is a read-out of all active commitments vs. revenue.
Surplus or deficit is the result, not an input.

This maps to how states actually work. A government doesn't decide each
year what percentage goes to the military — it has existing programs,
contracts, personnel that cost what they cost. Changing that is a
political and logistical act, not a slider adjustment.

### What the Budget Pie Shows

Stacked committed per-day spending across all categories vs. revenue
sources (GDP + taxes + resource dividends + NPC deal installments).
The number at the bottom: daily surplus or deficit.

No allocation needed. The pie is a consequence of your commitments,
not an input to them.

### Moving Up vs. Moving Down

**Moving up** (committing to a higher tier):
- New per-day cost begins immediately
- Capability builds toward new tier over transition period
- Signals to NPCs (military tier-up visible to Volkov/Wei/Bill)

**Moving down** (cutting a commitment):
- Capability begins decaying toward lower tier
- Some cuts have immediate political consequences
  (cutting public services = approval hit, cutting military = coup risk signal)
- Some NPCs notice and react (cutting diplomatic corps = standing decay
  accelerates; cutting intelligence = detection risk rises)
- Cannot cut below 0 — the state has a floor of basic functions

### One-Off Covert Operations

Replaces the old "buy tier X for $Y lump sum" model.

Ongoing commitment spending = the institution (what capability you have).
One-off operations = what you do with that capability.

Tier determines:
- Which operations are available
- How effective they are
- Detection risk profile

Operations cost from personal wealth (Shadow Cabinet) or black budget
allocation, not from the commitment pool. This cleanly separates
"what kind of state are you building" (commitments) from
"what are you doing this week" (operations).

---

## PER-TIER SPENDING COMMITMENTS

All costs in $B/day. Costs are tunable constants in turn_processor.py.

### Military

| Tier | Name | $/day | Capability | Notes |
|------|------|-------|------------|-------|
| 0 | Minimal | 0.0 | Rapid decay, no deterrence | Coup risk elevated |
| 1 | Basic Defense | 0.8 | Territorial integrity | DPRG threat reduced |
| 2 | Regional Force | 1.6 | Regional deterrence | USA alliance value activates |
| 3 | Serious Military | 2.5 | Great power respect | Diplomatic multiplier active |
| 4 | Advanced Force | 3.8 | Near-peer capability | Middle power signal |

Education reduction: Military Tier 3+ costs -$0.3B/day at Education Level 2+
(better-trained officer corps, more efficient logistics)

### Intelligence (National Apparatus)

| Tier | Name | $/day | Capability | Notes |
|------|------|-------|------------|-------|
| 0 | None | 0.0 | No intercepts | Detection blind |
| 1 | Basic Signals | 0.5 | Tier 1 intercepts | Standard world event previews |
| 2 | Active Collection | 1.0 | Tier 2 intercepts | NPC-to-NPC hints, negotiation bonuses |
| 3 | Full Apparatus | 1.8 | Tier 3 intercepts | Near-complete actionable intel |

Tech Level reduction: Intel Tier 2+ costs -$0.2B/day at Tech Tier 3+
Education reduction: Intel Tier 3 costs -$0.2B/day at Education Level 2+

Shadow apparatus (personal/covert) remains in Shadow Cabinet,
funded from personal wealth. Not shown in domestic budget.

### Diplomatic Corps

| Tier | Name | $/day | Capability | Notes |
|------|------|-------|------------|-------|
| 0 | Minimal | 0.0 | No repair capacity | Ambassador recalls not addressed |
| 1 | Basic Corps | 0.5 | Modest repair runway | Debrief quality: basic |
| 2 | Professional | 1.0 | Good repair, standing recovery | Debrief quality: good |
| 3 | Full Corps | 1.5 | Max repair runway | Diplomatic intel surfaces regularly |
| 4 | Elite Corps | 2.2 | Comprehensive capability | Kompromat opportunities surface |

Education reduction: Diplomatic Tier 3+ costs -$0.3B/day at Education Level 2+
(educated diplomats, stronger institutional knowledge)

### Social Infrastructure / Public Services

| Tier | Name | $/day | Capability | Notes |
|------|------|-------|------------|-------|
| 0 | Neglected | 0.0 | Approval decay, stability fragile | Education returns halved |
| 1 | Basic Services | 0.6 | Approval floor +5, stability +3 | Education returns normal |
| 2 | Functional | 1.2 | Approval floor +12, stability +7 | Education returns +20% |
| 3 | Strong Services | 2.0 | Approval floor +20, stability +12 | Education returns +35%, EU warm |

Note: Education spending below Social Infrastructure tier has
severely diminished returns. Cannot have good education without
the foundation of public services.

### Education

| Tier | Name | $/day | Capability | Notes |
|------|------|-------|------------|-------|
| 0 | Underdeveloped | 0.0 | No compounding effects | |
| 1 | Basic | 0.5 | GDP +5%, tech absorption +10% | Reduces military/intel costs |
| 2 | Developed | 1.1 | GDP +12%, tech absorption +20% | Reduces diplomatic costs |
| 3 | Advanced | 1.9 | GDP +20%, tech absorption +35% | Brain drain risk if approval < 30 |

Education is the multiplier for everything else. The player who
invests here early is paying a real budget cost but reducing the
cost of every other commitment over time. The player who skips it
pays full price for everything indefinitely.

### Resource Development

| Tier | Name | $/day | Payoff Phase | Notes |
|------|------|-------|-------------|-------|
| 0 | Untapped | 0.0 | No investment | Raw resources, no leverage |
| 1 | Early Development | 0.7 | Investment phase (~10 days) | Small export revenue begins |
| 2 | Active Extraction | 1.4 | Partial self-funding (~20 days) | Dependency relationships possible |
| 3 | Mature Sector | 2.2 | Self-funding + surplus | Full extraction opportunity |
| 4 | Strategic Resource | 3.0 | Significant surplus | International legitimacy contribution |

**The resource timing curve:**
- Investment phase: full cost, no return. Deficit pressure is real.
- Partial self-funding: revenue offsets 40-60% of daily cost.
- Self-funding: revenue covers cost. Net zero.
- Surplus: generates positive daily revenue above commitment cost.

The flip from deficit to surplus is the resource player's strategic
milestone. Surviving long enough to reach it is the challenge.

Once generating surplus: the skim opportunity emerges structurally.
The surplus is exactly where diversion is easiest to hide.

---

## TOTAL COMMITMENT SCALING

Example commitment stacks at different development stages:

**Early democratic player (Era 1-2):**
Military Tier 1: $0.8B
Intelligence Tier 1: $0.5B
Diplomatic Tier 1: $0.5B
Social Infrastructure Tier 2: $1.2B
Education Tier 1: $0.5B
Resource Tier 1: $0.7B
**Total: $4.2B/day**

**Mid-game legitimate leader (Era 3-4):**
Military Tier 2: $1.6B
Intelligence Tier 2: $1.0B
Diplomatic Tier 3: $1.5B (reduced by education: $1.2B)
Social Infrastructure Tier 3: $2.0B
Education Tier 2: $1.1B
Resource Tier 2: $1.4B (partially self-funding: net $0.6B)
**Total: ~$9.0B/day (before education cost reductions)**
**With education reductions: ~$8.4B/day**

**Late-game authoritarian (Era 4-5):**
Military Tier 3: $2.5B (+ Loyal Generals surcharge)
Intelligence Tier 3: $1.8B
Diplomatic Tier 1: $0.5B (they've deprioritized this)
Social Infrastructure Tier 1: $0.6B (bare minimum)
Education Tier 1: $0.5B (suppressed)
Resource Tier 3: $0.0B net (self-funding + surplus)
Shadow apparatus: from personal wealth (not in budget)
**Total: ~$5.9B/day national budget**
**But: personal wealth being drained by shadow ops simultaneously**

The authoritarian path looks cheaper on the national budget —
but the personal wealth drain from covert operations, brigade
maintenance, and patronage payments is where the real cost lives.
Two separate resource puzzles running simultaneously.

---

## CUTTING COMMITMENTS: CONSEQUENCES BY CATEGORY

| Category Cut | Immediate | Short-term | NPC Reaction |
|-------------|-----------|-----------|--------------|
| Military | Decay begins | Coup risk signal | Volkov/Wei notice |
| Intelligence | Detection risk rises | Intercept quality drops | Bill notices gap |
| Diplomatic | Standing decay accelerates | Repair capacity gone | All NPCs get harder |
| Social Infrastructure | Approval hit | Education returns halved | Marsha flags |
| Education | Slow decay | Cost reductions lost over time | Bill/Marsha flag |
| Resource | Development halts | Progress lost | Dependency partners nervous |


---

## TAX SYSTEM

### Current Implementation (for reference)

Three tax rate sliders: income, corporate, resource extraction.
Applied as multipliers to base revenue values in turn_processor.py.
Resource tax = resource_base × resource_rate where resource_base
is currently semi-fixed, not dynamically connected to resource
development investment. This is the foundation we're building on.

### Tax Rate Calculation

```
daily_tax_revenue = (
  income_revenue
  + corporate_revenue
  + resource_revenue
)

income_revenue = GDP × income_rate × laffer_modifier(income_rate)
corporate_revenue = GDP × corp_rate × 0.6 × laffer_modifier(corp_rate)
resource_revenue = resource_base × resource_rate × policy_modifier

laffer_modifier(rate):
  0–25%:  1.00 (full collection, minimal drag)
  25–45%: 1.00 - ((rate - 25) × 0.015)
  45–60%: 0.75 - ((rate - 45) × 0.025)
  60%+:   diminishing sharply, severe growth suppression

structure_modifier (applied to income_revenue):
  Elite-heavy:  × 1.10 revenue, GDP growth -3%/era
  Balanced:     × 1.00
  Mass-heavy:   × 0.90 revenue, approval -8, GDP growth -2%/era

institution_modifier (applied to total):
  Judicial capture active:     +0.05
  Education Level 0–1:         -0.08 (inefficient administration)
  Education Level 2+:          +0.05 (efficient tax authority)
  High corruption heat:        -0.10 (evasion, leakage)

tax_approval_penalty (diminishing at low approval):
  penalty = base_penalty × (approval / 100)
  At 80% approval: full penalty
  At 30% approval: 37.5% of penalty
  At 10% approval: 12.5% — already miserable, more taxes barely register
```

### Skim as a Visible Slider

Skim moves from a hidden action to a visible slider in the budget view.
The moral weight becomes unavoidable — it's right there next to tax rate.

```
effective_budget_revenue = tax_revenue × (1 - skim_rate)
personal_wealth_gain += tax_revenue × skim_rate

skim_heat_generation:
  skim_rate 0–5%:   low heat generation
  skim_rate 5–15%:  accelerating heat generation
  skim_rate 15%+:   nonlinear spike — hard to hide at scale

skim_detection_threshold drops at:
  Education Level 2+: educated population notices irregularities
  Free press active:  investigative journalism surfaces patterns
  High Intel NPC:     Bill's apparatus tracks financial flows
```

The budget pie shows the gap between revenue and commitments visibly.
If running a deficit with skim_rate at 15%, the cause and consequence
are on the same screen.

---

## RESOURCE POLICY MODEL

### The Core Choice: State-Led vs. Private Sector

Single toggle per resource tier. Can switch but transition costs apply
(several days before new model kicks in).

**State-Led extraction:**
- Government owns and operates resource sector
- Revenue flows directly to national budget at resource_rate
- High immediate income, slower long-term growth
- No private investment multiplier
- NPC signal: Marsha less comfortable, Wei more interested
- Skim opportunity: state ownership makes diversion easiest

**Private Sector extraction:**
- Government licenses to private companies, taxes profits
- Lower immediate revenue (taxing profits not gross)
- Private investment accelerates development tier progression
- GDP grows faster, resource sector matures sooner
- Creates domestic oligarch constituency needing political management
- NPC signal: Marsha approves, Bill reads as market-oriented

```
resource_revenue:
  State-Led:      resource_base × resource_rate (gross)
  Private Sector: resource_base × 0.45 × resource_rate (profits only)
  
  Private Sector development_speed_modifier: × 1.4
  (reaches self-funding phase faster)
```

The resource tax rate slider applies to whichever model is active.
Same rate, different base — Private Sector yields less immediately,
more eventually.

### Foreign Exploitation Rights

Selling resource access to NPCs. Inverts the dependency dynamic.

| NPC | What They Want | Revenue | Side Effects |
|-----|---------------|---------|--------------|
| EU | Rare earths, clean energy | $1.5–2.5B/turn | EU +8, Tech +2/turn |
| USA | Strategic minerals, port access | $2–3B/turn | USA +5, Volkov -8 |
| China (Wei) | Infrastructure, port access | $2.5–3.5B/turn | USA -10, tech dependency |
| Russia (Volkov) | Energy pipelines, bases | $1.5–2B/turn | EU -12, USA -15 |
| Arabia | Agricultural contracts | $1–1.5B/turn | Arabia +5, stable |

Foreign exploitation is public — other NPCs see who has access to
Europa's resources. Granting Wei port access is visible to Bill.
Granting Volkov pipeline rights is visible to Marsha.
You can only grant the same resource to one NPC at a time.

---

## BOND MARKET AND INTERNATIONAL LENDING

### Dynamic Bond Rates

```
bond_rate = base_rate + risk_premium + access_modifier

base_rate: 2.5% (floor — sovereign debt baseline)

risk_premium components:
  deficit_trend:     +0.3% per day of consecutive deficit
  stability_type:    coercion stability adds +0.8% risk premium
                     (sudden collapse risk priced in)
  existing_debt:     +0.15% per $10B outstanding
  political_risk:    +0.5% at Patronage State, +1.2% at Kleptocracy

access_modifier (which markets you can access):
  EU relations 60+:  -0.4% (EU capital markets)
  USA relations 60+: -0.3% (US capital markets)
  Education 2+:      -0.2% (institutional credibility)
  Tech Tier 3+:      -0.1% (sophisticated financial infrastructure)
  Volkov lending:    rate artificially low (2%), conditions hidden
  Wei lending:       rate low (1.5%), dependency terms compound slowly
```

Bond rate displayed visibly: "International bond rate: 4.2%"
Rising rate triggers briefing items: debt sustainability warnings,
IMC (International Monetary Council) outreach, creditor nervousness.

### Emergency Loan Requests at UN / Regional Council

Player in fiscal distress can table a loan request publicly at
next Summit or regional council. Everyone sees the vulnerability.

**NPC lending behavior in character:**

- **Marsha:** favorable rate, reform conditions attached (press freedom,
  fiscal transparency, judicial independence). Conditions are binding
  commitments tracked same as any deal. Slow to offer, generous if
  you've earned trust.

- **Bill:** market rate, strategic alignment conditions. Faster than
  Marsha. Conditions are geopolitical not reform-oriented.

- **Volkov:** offers quickly, generously, low rate. Conditions unstated
  upfront — emerge later when he needs something you can't refuse.
  The trap. Dialogue is warm and framed as partnership.

- **Wei:** similar to Volkov but slower, more patient. Belt and Road
  framing — infrastructure loans that create dependency. By the time
  debt is due you need him more than he needs you. Never threatens
  directly.

- **Sadam:** straightforward and transactional. High rate, energy
  partnership conditions, no ideological strings. Most honest lender.

- **Ji-won:** cannot offer meaningful amounts. Can broker introductions
  to other lenders — for a price. Ji-won knowing your financial
  desperation is itself leverage he files away.

### NPC Coalition Lending

At high usa_eu bilateral score: Bill and Marsha coordinate joint
loan package. Bigger than either alone, but both sets of conditions
simultaneously. Player gets more money, more constrained.

At low NPC bilateral scores: play lenders against each other.
"Volkov offered me $3B at 2%. What can you do?" Bill hates Volkov
having leverage and may improve terms. Active financial diplomacy —
using your crisis as negotiating leverage.

### Player Bailing Out Other Countries

The prestige move. Signals a different kind of actor.

A smaller nation in crisis appears in briefing. Options:
- Bilateral loan (you set rate and conditions — you're the NPC now)
- Grant (costs you, earns soft power, creates client)
- Through regional council (public, maximizes soft power signal)
- Decline (neutral to slightly negative with requesting nation)
- Let another great power bail them out (they become that power's
  client instead of yours)

The nation you bail out: votes with you at UN, provides basing rights,
supports your positions in regional councils. The client state mechanic
born here. You've just done what Bill does to you.

### IMC (International Monetary Council)

Abstracted neutral institutional lender. Slower than bilateral,
more conditions, but conditions are legitimizing not politically
compromising. Taking IMC money signals fiscal responsibility —
submitting to external audit. Western NPCs read positively.

**Debt restructuring via IMC:**
If in a debt spiral, IMC can restructure in exchange for austerity.
- Reduced spending commitments forced by external requirement
- Several eras of constrained sovereignty
- Marsha and Bill effectively have veto over budget during restructuring
- Survival, but barely
- Historian notes the period: "The years of the IMC program were the
  closest Europa came to genuine accountability — not by choice."

