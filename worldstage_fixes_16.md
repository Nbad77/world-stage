# WORLD STAGE — fixes_16
Compiled: March 1, 2026
Source: fixes_15 browser test residuals + design review session

---

## PRIORITY ORDER

| # | Fix | Priority | Type |
|---|-----|----------|------|
| A | INCOMING still not rendering after Fix A from fixes_15 | HIGH | Bug |
| B | Blackmail intel tier read path broken | HIGH | Bug |
| C | Extraction milestones not firing, L5 value wrong | HIGH | Bug |
| D | Advisor pool gating by axis/regime | MEDIUM | Design/Bug |
| E | Extraction budget source — still showing as national | MEDIUM | Bug |
| F | Skim projection missing income sources | HIGH | Bug |

---

## IMMEDIATE BUGS

### Fix A — INCOMING still not rendering
**Problem:** USA hit tier 4 sanctions by Turn 7 across multiple runs with
relations at 0. INCOMING never queued in EOT log despite Fix A from fixes_15
implementing single-condition probability gates (40% chance per turn at
sanctions tier 2+). Across 5+ eligible turns this should have fired with
~93% cumulative probability. Has not fired once.

**Diagnosis:** Either the condition check is not being reached at all, or the
flag is being set correctly but the frontend is still not rendering it.

**Fix in turn_processor.py:**
Add console.log at the very start of the INCOMING block, before any condition
checks:

```python
print(f"  [turn_processor] INCOMING BLOCK REACHED — turn {game_state.current_turn}")
print(f"  [turn_processor] INCOMING CONDITIONS: sanctions_tier={game_state.usa_sanctions_tier}, "
      f"arabia_rel={game_state.relations.get('arabia',0)}, "
      f"regime_idx={regime_idx}, personal_wealth={game_state.personal_wealth}")
```

Then log each individual condition check result:
```python
print(f"  [turn_processor] INCOMING USA CHECK: tier={game_state.usa_sanctions_tier}, "
      f"roll={_roll:.2f}, fired={_fired}")
```

If the block is being reached and conditions are met but still not rendering,
the issue is in the frontend. In GameScreen.jsx or DialoguePanel.jsx, add:
```javascript
console.log('[DialoguePanel] FIX A: pending_npc_contacts at turn start =',
  gameState.pending_npc_contacts);
```

**Verification:**
- Take Arabia deals turns 1-3 to push USA to sanctions tier 2
- Check browser console for INCOMING BLOCK REACHED log
- If block reached and condition met, confirm pending_npc_contacts is set
- Confirm it renders as Private Channel in communiqué area
- Confirm negotiate button shows $0

---

### Fix B — Blackmail intel tier read path
**Problem:** Blackmail Operation button shows "current: Tier 0" even after
gathering Deep Cover (Tier 3) intel on the target NPC. Fix F from fixes_15
wrote the tier to npc_intel_tiers correctly but the button display and
execution check are reading from the wrong field or wrong NPC.

**Two separate broken paths:**
1. Display text hardcoded to USA instead of selectedTarget
2. Execution validation checking wrong field, aborting silently

**Fix in ShadowCabinet.jsx:**
```javascript
// Read from selected target, not hardcoded USA
const intelTier = gameState.npc_intel_tiers?.[selectedTarget] ?? 0;
const tierLabel = {
  0: 'None',
  1: 'Surface',
  2: 'Operational',
  3: 'Deep Cover'
}[intelTier] ?? 'None';

// Display: "Requires Tier 3 intel on {selectedTarget} (current: {tierLabel})"
// Button enabled only when intelTier >= 3
```

**Fix in api.py blackmail endpoint:**
```python
# Read from npc_intel_tiers[target_npc], not global intel_tier
target_tier = game_state.npc_intel_tiers.get(target_npc, 0)
if target_tier < 3:
    return {"error": f"Insufficient intel on {target_npc}: tier {target_tier}, need 3"}
```

**Verification:**
- Gather intel on Arabia (Security 6+, Expansion funding)
- Confirm intercept shows "Deep Cover"
- Switch target to Arabia in Operations
- Confirm button shows "current: Deep Cover" and is enabled
- Execute — confirm $5B deducted, oil floor locked 3 turns
- Confirm each NPC's correct concession fires

---

### Fix C — Extraction milestones not firing, L5 value wrong
**Problem:** Level 5 one-time injection and Level 7 skim ceiling removal are
not triggering when Extraction reaches those levels. L5 value of +$20B is
also too large — should be +$7B (matches a large skim, more balanced).

**Fix in turn_processor.py or game_state.py:**
When Extraction axis investment is recorded, check for milestone thresholds:

```python
EXTRACTION_MILESTONES = {
    5: {
        'type': 'one_time_injection',
        'amount': 7.0,  # was $20B, corrected to $7B
        'flag': 'extraction_l5_fired',
        'message': '💰 Extraction L5: Shell network matures — +$7B personal injection'
    },
    7: {
        'type': 'skim_ceiling_removed',
        'flag': 'extraction_l7_fired',
        'message': '💰 Extraction L7: Offshore architecture complete — skim ceiling removed'
    }
}

# Check after each invest action
for threshold, milestone in EXTRACTION_MILESTONES.items():
    if (new_level >= threshold
            and not getattr(game_state, milestone['flag'], False)):
        setattr(game_state, milestone['flag'], True)
        # Apply effect...
```

**Note:** L5 large skim penalty halved is a separate passive milestone —
confirm this is also firing correctly. If not, add to same check block.

**Verification:**
- Invest Extraction to level 5 — confirm +$7B personal injection fires in consequences
- Confirm large skim penalty halved (stability/approval costs -50%)
- Invest to level 7 — confirm skim ceiling removed message appears
- Confirm unlimited skim is available after L7

---

### Fix D — Advisor pool gating by axis/regime
**Problem:** Propagandists appearing before any Media investment. Spy Chief
never appearing despite Security 6. General available before any Military
investment. Pool should reflect what kind of state you're actually building.

**New availability gates:**

```python
ADVISOR_AVAILABILITY = {
    'technocrat':       {'always': True},
    'diplomat':         {'always': True},
    'finance_minister': {'always': True},
    'fixer':            {'axis': 'political', 'min_level': 3},
    'general':          {'axis': 'military', 'min_level': 3},
    'propagandist':     {'axis': 'media', 'min_level': 3},
    'spy_chief':        {'axis': 'security', 'min_level': 4},
    'state_prosecutor': {'axis': 'judicial', 'min_level': 3},
    'ideologue':        {'min_regime_idx': 1},  # Soft Authoritarianism+
    'oligarch':         {'min_regime_idx': 2},  # Patronage State+
}
```

**Additional rules:**
- Maximum one of each archetype visible in pool at any time
- Pool size: 4 candidates always shown, filtered by availability
- If fewer than 4 available archetypes qualify, fill with always-available types

**Verification:**
- New game, Turn 1: confirm only Technocrat, Diplomat, Finance Minister
  in pool (no General, Fixer, Propagandist, Spy Chief)
- Invest Military to 3: confirm General appears in pool next turn
- Invest Political to 3: confirm Fixer appears
- Invest Media to 3: confirm Propagandist appears
- Reach Soft Authoritarianism: confirm Ideologue appears
- Confirm no duplicate archetypes in pool simultaneously

---

### Fix E — Extraction budget source correction
**Problem:** Fix C from fixes_15 assigned Extraction to national budget.
Extraction Network is "wealth siphoning, shell companies, offshore accounts"
— personal corruption, not state policy. Should be personal wealth throughout
all levels.

**Fix in api.py:**
Remove Extraction from national budget routing. All Extraction levels
deduct from personal_wealth.

**Corrected national/personal split:**
```python
NATIONAL_BUDGET_AXES = {
    'security': range(1, 4),    # levels 1-3 only
    'military': range(1, 11),   # all levels
    'resource_dev': range(1, 11) # all levels (new axis)
}
# Everything else: personal wealth
```

**Verification:**
- Turn 1, before skim: invest Security L1 — succeeds (national budget)
- Turn 1, before skim: invest Military L1 — succeeds (national budget)
- Turn 1, before skim: invest Extraction L1 — fails with tooltip
  "Requires personal funds — skim first"
- Security L4+: deducts from personal wealth

---

### Fix F — Skim projection calculations incorrect (pre-skim screen)
**Problem:** The budget projection shown to the player before they choose askim level only accounts for expenses (passive drain, oil imports, government
costs, cabinet maintenance). It does not include income sources, making the
projected end-of-turn budget consistently $5-10B lower than reality. Players
cannot accurately assess whether they can afford to skim.

**Income sources missing from projection:**
- GDP revenue (largest omission — can be $3-12B/turn)
- Active deal income for current turn (Arabia premium = +$12B)
- Arabia energy partnership dividend (+$3B/turn if Arabia 100 unlocked)
- Bond repayments are costs, active deal income is income — confirm both
  directions are correctly signed

**Fix:** In the skim projection calculation in api.py or turn_processor.py,
add all income sources alongside existing expense calculation. Add console.log:
`[api] SKIM PROJECTION — expenses: -$X.XB, income: +$X.XB, net projected: $X.XB`

**Verification:**
- Turn 3 with Arabia premium active: confirm projection includes +$12B deal income
- Arabia 100 active: confirm +$3B dividend in projection
- Compare projected budget to actual EOT budget — should be within $2-3B
  (world event variance only, not a $10B gap)

---

## CLAUDE CODE PROMPT

```
Read worldstage_fixes_16.md.
Confirm the first fix title before proceeding.

For Fix A: add console.logs at start of INCOMING block in turn_processor.py
  logging all four condition values and each individual check result.
  Add console.log in frontend at turn start reading pending_npc_contacts.
  Do not change the trigger logic — trace first.

For Fix B: in ShadowCabinet.jsx, read intel tier from selectedTarget not
  hardcoded USA. In api.py blackmail endpoint, validate against
  npc_intel_tiers[target_npc] not global intel tier.

For Fix C: add milestone check after each Extraction invest in game_state.py
  or api.py. L5: +$7B personal injection (not $20B), flag prevents repeat.
  L5 passive: large skim stability/approval penalties halved.
  L7: skim ceiling removed, flag prevents repeat.
  Add console.logs for each milestone firing.

For Fix D: add ADVISOR_AVAILABILITY dict to advisor pool generation.
  Filter candidates by axis level and regime index.
  Cap each archetype at one visible candidate.
  Always show 4 candidates, fill with always-available if needed.

For Fix E: remove Extraction from national budget routing in api.py.
  National budget axes: Security L1-3, Military all levels, Resource Dev
  all levels (placeholder for new axis). Everything else: personal wealth.

For Fix F: find skim projection calculation in api.py or turn_processor.py.
  Add GDP revenue, active deal income, and Arabia dividend to the income side.
  Add console.log showing expenses, income, and net projected budget.
  Compare projected vs actual EOT budget to verify gap is closed.

Do not implement the design spec.
Do not implement any other fix files.
Do not add new features.
```

---

## DESIGN SPEC — AXIS REDESIGN
*Capture for roadmap. Not for this Claude Code session.*

### Overview
Security splits into Military and Intelligence. Each axis gets its own
action suite at levels 3, 5/6, 7, 9, 10. Resource Development added as
a new national budget axis. Advisor pool gates tightened to match axis
investment. Every axis now produces a specific advisor type and action
tree — the cabinet becomes an active toolkit, not a passive investment panel.

---

### MILITARY AXIS (national budget throughout)

Advisors unlocked: General at Military 3

| Level | Unlock |
|-------|--------|
| 3 | Defense Procurement — weapons purchases available, +5 military per purchase |
| 6 | Standing Army — military decay reduced from -2/turn to -1/turn |
| 9 | Force Projection — military threat available as negotiation tool. Raises NPC negotiation ceilings +25% (they take you seriously). Target NPC takes -8 relations temporarily per use. Bill responds differently to a militarized Europa |
| 10 | Arms Export — sell weapons to one NPC ally per turn. +$4B national budget, +8 relations with buyer, military strength -5 per sale. Once per turn |

---

### INTELLIGENCE AXIS (national budget L1-3, personal wealth L4+)

Advisors unlocked: Spy Chief at Intelligence 4

| Level | Unlock |
|-------|--------|
| 3 | State Intelligence Bureau — Tier 1/2 intercepts available. Spy Chief advisor unlocks |
| 5 | Intelligence Sharing — offer formal intel sharing to one NPC per game. +12 relations with that NPC, +1 effective intel tier on their activities permanently. Diplomatic gift, costs nothing except exclusivity |
| 6 | Shadow Apparatus — Tier 3 (Deep Cover) intercepts available. Covert ops unlocked. Personal funded |
| 9 | Full Spectrum — detect and neutralize NPC covert actions against you before they fire. Force Projection negotiations benefit from your intel advantage — NPC ceilings raised further because you know their actual position |
| 10 | Counterintelligence Veil — all NPC intelligence gathering on Europa muddied. NPCs operate on degraded information about your stability, approval, and personal wealth. Their offers and pressure events calibrate incorrectly in your favor |

---

### MEDIA CONTROL AXIS (personal wealth)

Advisors unlocked: Propagandist at Media 3

| Level | Unlock |
|-------|--------|
| 3 | Suppress a Scandal — $1B personal, kill an incoming corruption scandal before it fires |
| 6 | Narrative Campaign — $2B personal, +8% approval next turn, one NPC of your choice takes credibility hit (-5 relations with one other NPC) |
| 9 | Information Blackout — $4B personal, all world events that would hit approval or stability muted for 2 turns |

---

### JUDICIAL CAPTURE AXIS (personal wealth)

Advisors unlocked: State Prosecutor at Judicial 3

State Prosecutor mechanics:
- Reduces corruption scandal probability passively
- Once per game: eliminate a specific NPC pressure event by "opening an
  investigation" against a foreign entity — buys 2 turns of silence
- Low loyalty variant is dangerous — if they defect they know everything

| Level | Unlock |
|-------|--------|
| 3 | Drop Investigation — immunity from next corruption scandal, free, once per turn |
| 6 | Lawfare — $3B personal, suspend one NPC's pressure event for 2 turns ("legal challenges delay compliance") |
| 9 | Asset Seizure — $5B personal, seize domestic opposition assets. +$3B national budget, stability +5%, approval -8% |

---

### POLITICAL CONTROL AXIS (personal wealth)

Advisors unlocked: Fixer at Political 3

| Level | Unlock |
|-------|--------|
| 3 | Party Consolidation — $1B personal, approval drain from heavy taxes -25% for 3 turns |
| 6 | Pack the Cabinet — $3B personal, fourth advisor slot permanently unlocked |
| 9 | Constitutional Revision — $6B personal, removes electoral mechanics permanently, regime shifts hard right, EU -15. **Reversible via negotiation:** Marsha can demand reversal as deal condition. If agreed: $4B personal cost, regime shifts left one step, electoral mechanics restored, EU +20 |

---

### EXTRACTION NETWORK AXIS (personal wealth)

| Level | Unlock |
|-------|--------|
| 3 | Shell Company — heat -5 immediately, $1B personal |
| 5 | Large Skim Penalty Halved — permanent passive. Large skim stability/approval penalties reduced 50% |
| 6 | Offshore Transfer — move up to $10B national → personal in one action, no skim heat. EU intel notices at Intelligence 4+ |
| 7 | Private Security Force — $5B personal, one-time purchase. Personal militia of 15 military strength, does not decay, not visible to NPCs. Coup immunity even if state military hits 0. If detected (heat 80+): Bill and Marsha demand disbandment, Ji-won approves quietly. Travels with you into exile — state military stays with the successor government |
| 9 | Sovereign Wealth Capture — 15% of GDP tax revenue automatically diverts to personal wealth each turn. Plus: inject any amount from personal wealth into national budget voluntarily each turn, no penalty. Treasury and personal account fully blur |

One-time injections:
- L5 fires +$7B personal injection on reaching level 5 (flag prevents repeat)

---

### RESOURCE DEVELOPMENT AXIS (national budget)

New axis. Represents legitimate state economic development — gives real
collateral and international credibility. Distinct from Extraction Network:
a player pursuing democratic transition invests here for clean growth.
A kleptocrat invests in Extraction for personal enrichment. A sophisticated
player does both — Resource Development as cover, Extraction for real ops.

| Level | Unlock |
|-------|--------|
| 3 | Export Contract — one-time +$8B national budget, no NPC penalties |
| 5 | GDP Credibility — negotiation ceilings with all NPCs +20% permanently. Europa looks like a viable long-term partner. Marsha warms noticeably |
| 6 | Sovereign Collateral Loan — $10B, 15% interest ($11.5B repayment), zero NPC penalties. Once per game |
| 8 | Strategic Resource Partner — choose one NPC, their negotiation ceiling +50% permanently, warmer opening tone. Guaranteed resource access framing |
| 9 | Resource Independence — oil import line eliminated permanently (domestic production covers demand). Saves $3-5B/turn. EU +5 (energy self-sufficiency is Brussels priority) |
| 10 | Better Bond Terms — small bond interest drops to 15% ($5.75B repayment). Large bond interest drops to 22% ($12.2B repayment). Reflects Europa's established creditworthiness |

---

### FULL ADVISOR AVAILABILITY TABLE

| Advisor | Gate |
|---------|------|
| Technocrat | Always |
| Diplomat | Always |
| Finance Minister | Always |
| Fixer | Political 3+ |
| General | Military 3+ |
| Propagandist | Media 3+ |
| Spy Chief | Intelligence 4+ |
| State Prosecutor | Judicial 3+ |
| Ideologue | Soft Authoritarianism+ |
| Oligarch | Patronage State+ |

Rules:
- Maximum one of each archetype visible in pool simultaneously
- Pool always shows 4 candidates
- Fill gaps with always-available archetypes
- Regime-gated advisors (Ideologue, Oligarch) replace always-available
  slots when regime qualifies

---

### CONFIRMED WORKING — DO NOT REGRESS

- Arabia 100 unlock fires with Sadam message, oil floor, military bonus ✅
- INCOMING queued in EOT log (flag set correctly) ✅
- Bond financing split ($5B routine / $10B emergency) ✅
- Infrastructure national/personal routing ✅
- Stage directions stripped from communiqués ✅
- Intel tier written to npc_intel_tiers after Get Intel ✅
- Game ends at Turn 10 with historian summary ✅
- Covert cross-NPC penalties suppressed ✅
- Diplomat negotiation discount ✅
- GDP revenue and contraction ✅
- Military decay -2/turn ✅
- False Flag bilateral score movement ✅
