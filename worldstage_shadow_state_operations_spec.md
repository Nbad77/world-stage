# WORLD STAGE — Shadow State & Operations Redesign
# Design Spec — Session 9.5A-Shadow
# Generated: March 2026

---

## OVERVIEW

This document specifies the Shadow State axis system, the operations
reorganization, and the intelligence operations suite. It is the
authoritative design spec for Session 9.5A-Shadow implementation.

### Core Principle

The Shadow State is the parallel power structure the player builds
alongside the legitimate state. Everything in it costs personal wealth,
exists outside official accounts, and carries deniability — until it
doesn't.

**Legitimate state (Domestic tab):** National budget, public commitments,
institutional capability. Democratic path compounds here.

**Shadow State (collapsible section in Domestic tab):** Personal wealth,
covert infrastructure, parallel institutions. Authoritarian path
compounds here.

The two paths are not mutually exclusive — the most dangerous player
is the one who maintains both simultaneously.

---

## UI STRUCTURE

### Shadow State Section — Hidden Until First Investment

Located at the bottom of the Domestic tab, below the national
commitment tiers.

**Before first investment:**
Locked panel. Header: "SHADOW STATE" (muted, lock icon).
Flavor text: *"Some instruments of power don't appear in public accounts."*

**After first investment:**
Unlocks permanently. Shows all five Shadow State axes with their
current tier levels and per-turn personal wealth costs.

### ShadowCabinet Overlay — Renamed and Reorganized

The existing Shadow Cabinet overlay (opened from StatusBar button)
is renamed to **CABINET** and reorganized:

- **POWER BASE drawer** (replaces Infrastructure): personal axes only
  (Media, Judicial, Domestic Surveillance, Extraction, Militia).
  National axes removed — those live in Domestic tab.
- **OPERATIONS drawer** (existing): reorganized per this spec.
- **ADVISORS drawer** (existing): unchanged.

Add redirect note at top of POWER BASE drawer:
*"National commitments (Military, Intelligence, Diplomatic, Resource)
are managed in the Domestic tab."*

Remove: budget allocation percentage bar (Intel 20%, Mil 20% etc.) —
this was the old allocation slider model. Replace with single line
showing personal wealth balance.

---

## THE FIVE SHADOW STATE AXES

All costs are in $B/day from personal wealth.
All axes use the 10-tier commitment model (same as national axes).
Militia and Extraction Network have merger mechanics.

---

### Axis 1: Media & Information Control

Personal wealth. 10 tiers. Per-turn cost.

| Tier | Name | $/day | Effects |
|------|------|-------|---------|
| 0 | Free Press | 0.0 | No control. Journalist investigations active. |
| 1 | State Voice | 0.2 | State media presence. Soft narrative advantage. |
| 2 | Favorable Coverage | 0.4 | Independent outlets pressured. Approval floor +3. |
| 3 | Press Pressure | 0.6 | License revocations. Sets `action_press_suppressed`. EU cap 85. |
| 4 | Censorship Infrastructure | 0.9 | Opposition media disrupted. Approval floor +8. Heat generation reduced. |
| 5 | Selective Suppression | 1.2 | Critical outlets closed. Propaganda approval bonus +5/turn. |
| 6 | Controlled Narrative | 1.6 | Near-total press control. EU cap 70. Historian hints at approval gap. |
| 7 | Information Monopoly | 2.1 | All independent press eliminated. Sets `journalists_suppressed`. |
| 8 | Total Media Control | 2.7 | Propaganda approval +10/turn. EU cap 55. Bill flags pattern. |
| 9 | Propaganda State | 3.4 | Population information environment fully managed. |
| 10 | Information Totalitarianism | 4.2 | Approval figures and reality fully decoupled. Propagandist advisor distortion maximized. |

**Key interactions:**
- Education Tier 3+: costs +30% (educated populations harder to deceive)
- Free press restoration: 5 days per tier to unwind (not instant)
- Tier 6+: Propagandist advisor distortion intensifies — displayed approval increasingly unreliable
- Historian hints activate at Tier 4+

---

### Axis 2: Judicial & Legal Capture

Personal wealth. 10 tiers. Per-turn cost.

| Tier | Name | $/day | Effects |
|------|------|-------|---------|
| 0 | Independent Courts | 0.0 | Full judicial independence. Corruption exposed. |
| 1 | Sympathetic Bench | 0.2 | Key appointments made. Delayed prosecutions. |
| 2 | Managed Justice | 0.4 | Corruption investigations slowed. |
| 3 | Captured Prosecution | 0.7 | Sets `action_judiciary_captured`. Scandal heat reduced. EU cap 75. |
| 4 | Suspended Investigations | 1.0 | All corruption investigations halted. |
| 5 | Political Prosecutions | 1.4 | Opposition can be prosecuted. Requires Political Tier 3+. |
| 6 | Legal Immunity | 1.9 | Full personal immunity. EU cap 60. |
| 7 | Courts as Weapon | 2.5 | Opposition leaders prosecuted at will. |
| 8 | Constitutional Revision | 3.2 | Term limits removable. Sets `constitutional_revision_active`. State Capture ending unlocks. |
| 9 | Legal Architecture | 4.0 | Permanent power structures legally embedded. |
| 10 | Total Legal Control | 5.0 | Judiciary indistinguishable from executive. Diplomatic Tier hard-capped at 4. |

**Key interactions:**
- Requires Political Tier 3+ to unlock Tier 5+
- Dismantling: 3+ days per tier, stability dip each step
- Tier 8+ cannot coexist with Diplomatic Tier 7+ (hard incompatibility)

---

### Axis 3: Domestic Surveillance & Control

Personal wealth. 10 tiers. Per-turn cost.
**Merger mechanic** available at Full Dictatorship+.

| Tier | Name | $/day | Effects |
|------|------|-------|---------|
| 0 | Open Society | 0.0 | No surveillance. Dissent forms openly. |
| 1 | Informant Network | 0.3 | Basic opposition monitoring. Early unrest warning. |
| 2 | Political Intelligence | 0.6 | Faction mapping. Coup warning lead time +2 turns. |
| 3 | Active Infiltration | 0.9 | Protest disruption. Opposition weakened. |
| 4 | Targeted Harassment | 1.3 | Opposition leaders neutralized. |
| 5 | Suppression Apparatus | 1.8 | Sets `opposition_dissolved` when combined with Judicial Tier 5+. |
| 6 | Loyalty Enforcement | 2.4 | Purge capability. Elite faction control improved. |
| 7 | Population Surveillance | 3.0 | Dissent prediction. Coup probability -25%. |
| 8 | Pervasive Control | 3.8 | Near-total domestic intelligence dominance. |
| 9 | Atomized Society | 4.7 | Population unable to organize. Legitimacy stability cannot recover above 30. |
| 10 | Total Control | 5.8 | One-party state achievable. |

**Merger mechanic — "Integrate into National Intelligence":**

Available when: Full Dictatorship regime label AND Domestic Surveillance
Tier 5+ AND National Intelligence Tier 4+.

Effects:
- Combined daily cost = National Intel cost + (Domestic Surveillance cost × 0.6)
  — cost efficiency reward for full authoritarian commitment
- Capability: takes higher of the two for most functions
- Moves Domestic Surveillance cost from personal wealth to national budget
- Coup protection spike
- **Loyalty mechanic activates:** merged apparatus needs Political Tier 5+
  to stay loyal. If Intel Tier > Political Tier by 3+ points: apparatus
  generates distorted reports (same politicization penalty from 9.5A,
  now covering surveillance data too)
- Marsha: -8 EU relations, formal statement
- Bill: recalculates your threat assessment
- Irreversible

---

### Axis 4: Extraction Network

Personal wealth investment. **Net revenue generator** — costs less than
it produces. The "commitment" is maintaining the infrastructure; the
return is a higher skim ceiling and reduced detection per dollar.

| Tier | Name | $/day cost | $/day generated | Skim ceiling |
|------|------|-----------|----------------|--------------|
| 0 | No Network | 0.0 | 0.0 | 5% skim max (hard cap without network) |
| 1 | Basic Skim | 0.1 | 0.3 | 8% max |
| 2 | Shell Structure | 0.2 | 0.7 | 12% max |
| 3 | Offshore Routing | 0.4 | 1.2 | 18% max |
| 4 | Sovereign Access | 0.6 | 1.8 | 25% max |
| 5 | Systematic Extraction | 0.9 | 2.5 | 32% max. Heat nonlinear above here. |
| 6 | Institutional Capture | 1.3 | 3.3 | 38% max |
| 7 | Revenue Stream Control | 1.8 | 4.2 | 44% max |
| 8 | Treasury Integration | 2.4 | 5.2 | 50% max |
| 9 | State-Personal Fusion | 3.1 | 6.3 | 56% max |
| 10 | Full Kleptocracy | 4.0 | 7.5 | 65% max. Personal/state finances indistinguishable. |

**Key interactions:**
- Detection risk scales nonlinearly at Tier 5+
- Bill's apparatus notices pattern at Tier 6+
- Education Tier 2+: detection threshold drops (population notices irregularities)
- Judicial Capture Tier 4+: reduces detection heat 30% (investigations suppressed)
- Tier 8+: feeds Kleptocrat biography axis score heavily
- Without Extraction Network: skim hard-capped at 5%

**Skim slider location:** Moves from Domestic tab to Shadow State section.
Display format: "XX% — $X.XB/day diverted" (shows both percentage AND
dollar amount). Heat warnings at 15%+ and 25%+.

**Pre-EOT skim prompt:** Discontinued. Skim rate is persistent; applies
automatically each turn. No more per-turn prompt.

---

### Axis 5: Militia / Loyalty Brigades

Personal wealth. 10 tiers. Per-turn cost.
**Merger mechanic** available at Soft Authoritarianism+.

| Tier | Name | $/day | Capability |
|------|------|-------|-----------|
| 0 | None | 0.0 | No personal force. |
| 1 | Street Network | 0.2 | Basic intimidation, demonstration disruption. |
| 2 | Loyalty Cells | 0.5 | Organized presence, rally protection. |
| 3 | Brigade Formation | 0.9 | Meaningful personal force. Coup protection +10%. |
| 4 | Armed Brigades | 1.4 | Real military capability (limited). Deniability decreasing. |
| 5 | Paramilitary Force | 2.0 | Serious capability. Marsha -5 if discovered. |
| 6 | Personal Army | 2.7 | Comparable to lower military tiers. |
| 7 | Parallel Military | 3.5 | Rivals state military in loyalty if not capability. |
| 8 | Shadow Army | 4.4 | Full parallel force. International community aware. |
| 9 | Dominant Loyalty Force | 5.4 | Exceeds formal military loyalty. |
| 10 | Personal Sovereign Force | 6.5 | Private army. Everyone knows. |

**Merger mechanic — "Integrate Brigade into Military Command":**

Available when: Soft Authoritarianism+ regime label.

Effects:
- Combined daily cost = Military cost + (Militia cost × 0.6) — cost efficiency
- Combined capability: highest of the two (professionalization hard to undo)
- Coup protection spike — most loyal troops now most capable
- Military effectiveness -15% (loyalists aren't as professional)
- Loses deniability — Marsha formally objects (-5 EU relations)
- Irreversible — once integrated, cannot re-separate

---

## EU RELATIONS CEILING — CONSOLIDATED TABLE

Fires automatically in EOT based on suppression state flags.
These are structural caps, not Marsha's choice. Marsha can negotiate
cap relief in exchange for reform commitments (tracked promises).

| Suppression combination | EU cap |
|------------------------|--------|
| None | 100 |
| Media Tier 3+ | 85 |
| Judicial Tier 3+ | 75 |
| Media Tier 3+ AND Judicial Tier 3+ | 65 |
| Domestic Surveillance Tier 5+ | 55 |
| Media Tier 7+ | 40 |
| All three axes Tier 7+ | 30 |

**Marsha's bargaining mechanic:**
When EU cap is active, Marsha can offer cap relief in backchannel
in exchange for specific rollback conditions. Conditions become tracked
promises. Cap relief fires when conditions are honored, not before.

---

## SHADOW STATE COST COMPUTATION

New function `compute_shadow_state_costs(gs)` in turn_processor.py.
Mirrors `compute_daily_commitment_cost()` but:
- Reads shadow axis tier fields
- Drains `personal_wealth` instead of `budget`
- Extraction Network generates revenue (adds to personal_wealth)
- Militia cost is personal wealth (same as now)

Called in EOT after `compute_daily_commitment_cost()`.

---

## OPERATIONS REORGANIZATION

### Structure

Four sections, each gated by axis tier levels.
**Two operations per turn maximum** (one legitimate + one shadow).
Tunable in future sessions.

### MILITARY ACTIONS

Gated by Military tier.

**Force Projection** (Tier 3+)
- FREE (no cost)
- Effect: Military threat — target NPC ceilings +25%, target -8 relations
- 3-turn cooldown after use
- Represents using military capability as diplomatic leverage

**Arms Export** (Tier 2+)
- Cost: variable (scales with Military tier + Tech level)
- Formula:
  ```
  export_value = $2B × (military_tier/5 + 0.5) × (1.0 + tech_tier × 0.1)
  military_cost = 3 + floor(military_tier / 3)
  ```
  Examples: Mil 3, Tech 0 = $2.2B / Mil 7, Tech 4 = $5.3B / Mil 10, Tech 8 = $8.5B
- Relations bonus with buyer: +8 (diminishes -2 per repeat sale, min +2)
- Cross-NPC visibility: all NPCs with Intel Tier 2+ see the sale and react
  in character (Bill sees Volkov sale: -8; Marsha sees Volkov sale: -6 etc.)
- DPRG sales: Bill -12, Marsha -10 (pariah signal)

**Military Modernization — Tranche 1** (Tech Tier 2+, Military Tier 3+)
- Cost: $5B national, one-time permanent
- Effect: Military strength decay rate -20% permanently
- NPCs notified: Bill and Volkov receive briefing item

**Military Modernization — Tranche 2** (Tech Tier 4+, Military Tier 5+)
- Cost: $8B national, one-time permanent
- Effect: Intel intercept quality +15% for military targets.
  Detection risk on your covert ops -10%.

**Military Modernization — Tranche 3** (Tech Tier 6+, Military Tier 7+)
- Cost: $12B national, one-time permanent
- Effect: Military tier upgrade costs -20% permanently.
  Force Projection cooldown reduced to 2 turns.

---

### INTELLIGENCE ACTIONS

Gated by Intelligence tier.

**Intelligence Sharing** (Intel Tier 2+, relations ≥ 50)
Bilateral ongoing agreement. Three depth levels per NPC.

| Level | Gate | What You Give | What You Get | Relations |
|-------|------|--------------|--------------|-----------|
| 1 — Signals Exchange | Intel Tier 2+, rel ≥ 50 | Low-level intercepts | Same from partner | +8 |
| 2 — Active Sharing | Intel Tier 3+, rel ≥ 65 | Tier 2 intercepts, some sources | Better intercepts, negotiation hints | +15 |
| 3 — Full Partnership | Intel Tier 4+, rel ≥ 75 | Near-complete picture | Partner's full intel on third parties | +20, summit cred +10 |

Mutual obligation: partner NPCs can request sharing. Refusing Level 2+ costs -10 relations.

Ending an agreement:
- Formal withdrawal: -15 relations, 3-day notice
- Abrupt termination: -25 relations, partner may leak what they know
- Partner terminates: -10 relations, access lost immediately

**Coalition Intelligence Network** (Intel Tier 4+, Level 2+ with 3+ NPCs):
All member NPCs share intercepts on non-members with you.
- Leaving costs -20 with all members
- Caught running covert ops against a member: network collapses

**Crisis Intelligence Package** (Intel Tier 2+)
- Available when target NPC stability < 30 OR in active crisis
- Cost: $1.5B personal or national (funding source signal)
- Effect: relations +12, rapport built, NPC remembers in biography
- One-time per NPC per era
- Historian voice: "In their moment of vulnerability, Europa offered
  intelligence rather than distance. The gesture was noted."

**Targeted Intercept** (Intel Tier 3+)
- Cost: $2B personal
- Effect: specific intelligence on one NPC's current plans
- 2-turn cooldown

**Kompromat Collection** (Intel Tier 3+)
- Cost: $1.5B personal, 7-day collection operation
- Detection risk per day during collection
- On success: NPC enters "Controlled" state
- NPC dialogue shifts to formally correct, no warmth
- NPC pressure events against you suppressed
- 3 uses before NPC neutralizes it
- 5% chance per day of NPC counter-intel discovering the file
  → relationship collapses immediately if discovered
- Shelf life: 20 days before relevance degrades
- Burn option: leak it publicly — destroys relationship permanently,
  causes NPC domestic crisis, +15 with NPC's rivals
- Ji-won: cannot collect kompromat (no meaningful leverage exists)

**Loyalty Assessment** (Intel Tier 2+ OR Domestic Surveillance Tier 3+)
- Cost: $1B personal
- Target: one currently hired advisor
- Effect: reveals true loyalty score + historian voice assessment
- Detection risk: 15% — if advisor detects: loyalty -20 immediately
- Cooldown: 3 days per advisor
- If `intel_politicized` is True: assessment may be distorted
  (disloyal advisor could receive clean bill of health)
- Historian voice format: "Your intelligence apparatus has compiled a
  profile. [Advisor name]'s loyalty is [characterization]."

**Loyalty Enforcement** (Domestic Surveillance Tier 5+)
- Cost: $2B personal
- Effect: target advisor loyalty +15
- Side effect: advisor gains hidden `coerced` flag
  — loyal but looking for exit. If player weakened (approval < 30
  or exile triggered), coerced advisors defect first and may
  actively support successor
- Detection risk: 25% — if detected, advisor immediately leaves staff

**Counter-Intelligence Sweep** (Intel Tier 2+)
- Cost: $2B personal
- Effect: detection heat -15, reveals one active NPC intel op targeting you
- 2-turn cooldown

**Full Spectrum** (Intel Tier 9) — existing, keep
**Counterintelligence Veil** (Intel Tier 10) — existing, keep

---

### DIPLOMATIC ACTIONS

Gated by Diplomatic tier.

**Trade Mission** (Diplomatic Tier 2+)
- Cost: $1.5B national
- Effect: one-time relations +10 with target NPC
- 3-turn cooldown

**Diplomatic Pressure Campaign** (Diplomatic Tier 2+)
- Renamed from "Foreign Influence Op"
- Cost: $1.5B personal
- Effect: +5 relations with target NPC
- Target selector across all NPCs

**Opposition Funding** (Diplomatic Tier 3+)
- Cost: $3B personal, high detection risk
- Effect: destabilizes NPC domestic situation
- NPC approval/stability penalty in their country
- If detected: relations -20, NPC considers hostile act

---

### SHADOW OPERATIONS

Gated by Shadow State axis tiers.
Count toward the one shadow operation per turn cap.

**Political Sabotage** (Domestic Surveillance Tier 3+)
- Cost: $3B personal
- Detection: 25% (requires Intel Tier 2+)
- Effect: target NPC pressure suspended 1 turn, cross-NPC penalty -50%

**Reputation Laundering** (Extraction Tier 3+)
- Cost: $3B personal
- Detection: none
- Effect: heat -15

**Fabricate Crisis** (Domestic Surveillance Tier 4+)
- Cost: $4B personal
- Detection: 35%
- Effect: target NPC pressure suspended 2 turns

**Blackmail Operation** (Intel Tier 3+)
- Cost: $5B personal
- Detection: 40%, NPC -5 relations permanent if caught
- Effect: extract one-time concession from target NPC

**False Flag** (Domestic Surveillance Tier 5+)
- Cost: $6B personal
- Detection: 50% (if caught: both NPCs -20)
- Effect: blame action on target NPC, bilateral -10 between target and another NPC

**Journalist Elimination** (Media Tier 7+ AND Judicial Tier 5+)
- Cost: $4B personal
- Detection: always discovered eventually — question is when and by whom
- Effect:
  - Removes specific active press threat
  - Stability decay slowed for 3 turns
  - Approval decay slowed for 3 turns
  - Sets `journalists_liquidated` flag permanently
  - EU cap drops to 40
  - Bill flags it — western alignment score hit
- One-time use per game. Permanent flag.

**Asset Exfiltration** (Intel Tier 4+)
- Cost: $2B personal
- Effect: extract personal wealth from frozen/at-risk accounts
- Available when personal_wealth at risk (exile state, sanctions)

---

## OPERATIONS REMOVED / REPLACED

These operations are removed because their function is now handled
by Shadow State axis ongoing effects or commitment tier upgrades:

| Removed | Replaced by |
|---------|-------------|
| Propaganda Campaign (ops) | Media & Information Control axis (ongoing) |
| Domestic Suppression (ops) | Domestic Surveillance axis (ongoing) |
| Defense Procurement | Military tier upgrade in Domestic tab |

---

## ADVISOR SYSTEM — DISTORTION REMINDER

The loyalty assessment operation interacts with the existing
stat distortion system. Relevant advisor distortions:

- **Propagandist:** inflates displayed approval. Education reduces effectiveness.
- **General:** inflates displayed military strength.
- **Militia Commander:** inflates displayed stability.
- **Spy Chief:** deflates displayed heat.
- **Oligarch:** inflates displayed budget AND deflates heat.
- **Fixer:** deflates displayed heat.

The **Oligarch** and **Fixer** are the advisors most likely to have
low hidden loyalty — they are explicitly self-interested. Loyalty
Assessment is how the player finds this out.

Biography reference if player never ran assessment:
*"He surrounded himself with advisors whose interests he never examined
too closely. In retrospect, the oversight was costly."*

---

## IMPLEMENTATION SEQUENCE

All of the above ships as **Session 9.5A-Shadow** — one session
because Shadow State axes gate the Shadow Operations, and both
gate the Operations drawer reorganization.

Implementation order within the session:

1. game_state.py: 5 new shadow axis tier fields + merger flags
2. turn_processor.py: `compute_shadow_state_costs()` function
3. turn_processor.py: EU ceiling check updated for new tier thresholds
4. api.py: shadow tier upgrade/downgrade endpoints
5. api.py: skim endpoint updated (persistent rate, no per-turn prompt)
6. DomesticTab.jsx: Shadow State section (hidden until first investment)
7. DomesticTab.jsx: skim slider moved here, dollar amount added
8. ShadowCabinet.jsx: Infrastructure drawer → POWER BASE (personal axes only)
9. ShadowCabinet.jsx: budget allocation bar removed
10. ShadowCabinet.jsx: Operations drawer reorganized per spec
11. api.py: new operation endpoints (arms export scaling, intel sharing,
    loyalty assessment, loyalty enforcement, kompromat, etc.)
12. npc_engine.py: intelligence sharing bilateral state + dialogue

---

## ADVISOR ELIMINATION — FEAR EFFECT

Elimination currently fires archetype-specific NPC consequences
(General eliminated → military decay, Diplomat eliminated → EU/USA -5).
This section adds the domestic benefit layer.

### Immediate Effect — Fear Response

When any advisor is eliminated, all other currently hired advisors receive:
- Loyalty +15 immediately
- Hidden `fear_bonus_active` flag for 5 days
- During fear window: advisor stat distortion reduced 50%
  (scared advisors tell more truth — they don't want to be next)

### Decay and Inversion

After the 5-day fear window:
- Loyalty returns toward baseline (fear is not durable)
- Each advisor who witnessed the elimination gains permanent
  `witnessed_elimination` flag
- On player weakness (approval < 30, exile triggered, coup attempt):
  witnessed advisors are more likely to defect — they've been
  calculating their exit since the moment it happened

### Repeat Eliminations

**Second elimination within 10 days:**
- Fear effect stronger: loyalty +25, 7-day window
- All remaining advisors gain `chronically_fearful` flag
- Chronically fearful advisors: loyalty stays artificially high
  but competence degrades -10 (too scared to give honest analysis)
- Feeds into intel politicization: high political control +
  fearful advisors = everyone tells you what you want to hear

**Third elimination within 20 days:**
- Remaining advisors deeply loyal and deeply unreliable
- Historian voice activates: *"By his third year, the President
  had surrounded himself with people who agreed with everything
  he said. This was, in retrospect, not a sign of strength."*

### Biography Arc

A player who eliminated multiple advisors receives a specific
historian note about the information environment they created —
and whether it contributed to their eventual downfall.

The `chronically_fearful` flag feeds the biography context as
`advisor_fear_culture: bool`. The Legacy section historian prompt
references it when True.

### Implementation Notes

New fields in game_state.py:
```python
advisor_elimination_count: int = 0
advisor_elimination_last_day: int = 0
advisors_with_fear_bonus: list = []    # active fear window
advisors_witnessed_elimination: list = [] # permanent flag
advisors_chronically_fearful: list = []   # permanent flag
```

In advisor_engine.py, `eliminate_advisor()`:
- After existing NPC consequence logic, apply fear effect to
  all remaining `gs.advisors` entries
- Set fear_bonus_active on each
- Increment elimination count
- Check repeat thresholds and apply chronically_fearful if met

In `get_displayed_*` functions:
- When advisor has `fear_bonus_active`: distortion magnitude × 0.5
- When advisor has `chronically_fearful`: competence -10 for all
  analysis quality checks

---

## OPEN QUESTIONS FOR FUTURE SESSIONS

1. Coalition Intelligence Network — full NPC-to-NPC sharing logic
   needs more design before implementation. Stub for now.
2. Kompromat burn mechanic — leaking publicly needs NPC crisis
   event design (what does their domestic crisis look like?).
3. Arms export to DPRG — Ji-won receiving weapons has implications
   for the broader regional stability system. Design before enabling.
4. Operations cap tuning (currently 2/turn) — revisit in Session 10
   when open-world pacing is established.
5. Loyalty Enforcement coerced flag — needs exile sequence integration
   (coerced advisors defect first on exile trigger).
