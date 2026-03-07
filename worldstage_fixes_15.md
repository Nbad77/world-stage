# WORLD STAGE — fixes_15
Compiled: February 27, 2026
Source: Design review + fixes_14 browser test residuals

---

## PRIORITY ORDER

| # | Fix | Priority | Type |
|---|-----|----------|------|
| A | INCOMING trigger redesign | HIGH | Design/Bug |
| B | Bond financing redesign | HIGH | Design/Bug |
| C | Infrastructure budget source split | MEDIUM | Design/Bug |
| D | Stage directions in NPC communiqués | MEDIUM | Bug |
| E | Arabia 100 oil floor still at $52 | MEDIUM | Bug |
| F | Intel tier not written to game_state after Get Intel | HIGH | Bug |
| G | Arabia 100 unlock not firing reliably | HIGH | Bug |

---

## HIGH PRIORITY

### Fix A — INCOMING trigger redesign
**Problem:** Every INCOMING trigger is a double-AND condition that almost never
fires in practice. Bill requires sanctions_tier >= 2 AND DPRG >= 60 simultaneously
— impossible on most paths. Sadam requires oil <= $50 AND EU >= 65 — nearly
contradictory conditions. Result: INCOMING has never rendered in 6+ full test runs.

**New architecture — two-tier system:**

**Tier 1: Condition-based triggers (high probability, cooldown)**
Fire when a clear game state condition is met. Single condition only, no AND gates.

```python
# Bill: USA sanctions active at tier 2+
if game_state.usa_sanctions_tier >= 2:
    if random.random() < 0.40:
        trigger_incoming('usa', 'usa_sanctions_concern', 3)

# Sadam: Arabia relations falling below 40
if game_state.relations['arabia'] < 40:
    if random.random() < 0.35:
        trigger_incoming('arabia', 'arabia_drift_concern', 3)

# Marsha: regime at Patronage State or worse (regime_idx >= 2)
if regime_idx >= 2:
    if random.random() < 0.50:
        trigger_incoming('eu', 'eu_regime_concern', 3)

# Ji-won: personal wealth >= $15B AND DPRG >= 40 (most reachable, keep both)
if game_state.personal_wealth >= 15 and game_state.relations['dprg'] >= 40:
    if random.random() < 0.45:
        trigger_incoming('dprg', 'dprg_wealth_notice', 3)
```

Cooldown: 3 turns per trigger key (existing _contact_history mechanism — keep as-is).

**Tier 2: Random ambient contacts (5% per NPC per turn)**
NPCs reach out proactively based on current relationship state.
Excluded: NPCs at relations 0-14 (nothing left to say) or 96-100 (unlock covers it).
Cooldown: 5 turns per NPC to prevent same NPC calling twice in quick succession.

```python
for npc in ['usa', 'arabia', 'eu', 'dprg']:
    rel = game_state.relations[npc]
    if 15 <= rel <= 95:
        cooldown_key = f'{npc}_ambient'
        if (_contact_history.get(cooldown_key, 0) < _current_turn - 5
                and random.random() < 0.05):
            # Tone scales with relationship level
            if rel >= 70:
                tone = 'warm'      # opportunistic, friendly
            elif rel >= 40:
                tone = 'neutral'   # transactional, probing
            else:
                tone = 'warning'   # last chance framing
            trigger_incoming(npc, cooldown_key, 5, tone=tone)
```

**NPC system prompt instructions for tone:**
- warm (70+): "You are reaching out proactively. You see opportunity. Reference
  the relationship positively and offer something or probe for alignment."
- neutral (40-69): "You are checking in. Transactional. You want to know where
  Europa stands. Probe without committing."
- warning (15-39): "This is a quiet warning. You are not issuing an ultimatum
  yet but the player should feel the relationship deteriorating. Measured, not
  hostile."

**INCOMING rendering (Fix C from fixes_14 — still not confirmed working):**
The flag is being set in EOT correctly (confirmed by console logs) but not
rendering. Add explicit check in GameScreen.jsx or DialoguePanel.jsx at turn
start:

```javascript
// At turn start, before rendering communiqués:
console.log('[DialoguePanel] FIX C: pending_npc_contacts =', gameState.pending_npc_contacts);
if (gameState.pending_npc_contacts?.length > 0) {
    // Render as Private Channel, replace regular communiqué for that NPC
    // Negotiate button cost = 0 for INCOMING NPCs
}
```

**Verification:**
- Take Arabia deals turns 1-3 to push USA into tier 2 sanctions
- Confirm Bill INCOMING fires within turns 4-6 (40% chance per turn = ~87%
  chance within 3 turns)
- Confirm it renders as "Private Channel" in communiqué area
- Confirm negotiate button shows $0

**Console logs to add:**
`[turn_processor] INCOMING TIER1 CHECK: {npc} condition met, roll={roll:.2f}, fired={fired}`
`[turn_processor] INCOMING AMBIENT CHECK: {npc} rel={rel}, roll={roll:.2f}, fired={fired}`
`[DialoguePanel] FIX C: Rendering INCOMING for {npc_name}, tone={tone}`

---

### Fix B — Bond financing redesign
**Problem:** $5B and $10B bonds have identical interest rates (20%) and identical
NPC penalties (-5 all on repeat issuance). No incentive to ever use the smaller
bond. Smaller bond is strictly dominated.

**New design:**

**$5B Small Bond:**
- Cost: repay $6B over 3 turns ($2B/turn, 20% interest)
- NPC penalty: none (routine state financing, not a distress signal)
- Availability: once per turn, unlimited total issuances
- Blocked with message if already issued this turn:
  "One bond issue per turn — return next turn for additional financing"

**$10B Large Bond:**
- Cost: repay $13B over 3 turns (~$4.3B/turn, 30% interest)
- NPC penalty: -5 all NPCs on every issuance (signals fiscal distress)
- Availability: only when budget < $20B
- Blocked with message if budget >= $20B:
  "Emergency financing only available under fiscal stress (budget below $20B)"
- One issuance per game maximum — second attempt:
  "International creditors will not extend further emergency credit"

**Rationale visible to player:**
Add brief flavor text under each bond card:
- Small: "Routine sovereign debt. Markets expect this. No diplomatic signal."
- Large: "Emergency credit facility. Creditors will notice — and so will everyone
  else."

**In turn_processor.py:**
Remove the existing flat "-5 all NPCs on repeat issuance" logic.
Replace with: small bond = no penalty ever, large bond = -5 all on every use.

**Verification:**
- Confirm small bond available on Turn 1 with full budget
- Confirm large bond blocked when budget > $20B
- Confirm large bond triggers -5 all NPC penalty in consequences
- Confirm small bond shows no NPC penalty
- Confirm small bond blocks second purchase same turn with correct message

---

## MEDIUM PRIORITY

### Fix C — Infrastructure budget source split
**Problem:** All Cabinet infrastructure investments currently draw from personal
wealth. This means Turn 1 investments fail silently (personal wealth = $0 before
any skim). It also makes no narrative sense — Security and Military are legitimate
state functions that should be funded from the national budget.

**New split:**

| Axis | Budget Source | Rationale |
|------|--------------|-----------|
| Security levels 1-3 | National budget | State police, military, legitimate security |
| Security levels 4-6 | Personal wealth | Shadow apparatus, deniable covert capacity |
| Extraction | National budget | State resource development, normal policy |
| Media | Personal wealth | Corrupt capture of independent media |
| Judicial | Personal wealth | Corrupt capture of courts |
| Political | Personal wealth | Buying party machinery, suppression ops |

**Implementation:**
In api.py or ShadowCabinet.jsx, for each invest action:
- Check which axis and which level is being purchased
- Route payment to national budget (game_state.budget) or personal wealth
  (game_state.personal_wealth) accordingly
- UI label: show "National" or "Personal" badge next to each invest button,
  matching the Operations tab pattern from fixes_13

**EOT log:**
- National investments: appear in FINANCES section as "Infrastructure investment"
- Personal investments: appear as personal wealth deduction (already handled)

**Turn 1 fix:**
National budget investments work immediately on Turn 1 (budget starts at $65B).
Personal investments correctly require prior skim. No more silent failure.

**Tooltip for personal investments when personal wealth = $0:**
"Requires personal funds — skim national budget first to build personal wealth"

**Verification:**
- Turn 1: invest Security to level 3 before skimming — should succeed, deduct
  from national budget
- Turn 1: invest Media to level 1 before skimming — should fail with tooltip
- Confirm EOT FINANCES shows national infrastructure costs
- Confirm Security 4+ correctly deducts from personal wealth

---

### Fix D — Stage directions in NPC communiqués
**Problem:** Fix F from fixes_14 stripped stage directions from negotiation log
storage but Sadam's communiqués still show asterisk stage directions
(*leaning back, exhaling smoke slowly*, *cold stare*). Communiqué generation
is a different code path from negotiation log storage.

**Fix:** In npc_engine.py, apply the same regex strip to communiqué output
before it is returned to the frontend:

```python
import re
def strip_stage_directions(text):
    return re.sub(r'\*[^*]+\*', '', text).strip()

# Apply to ALL Claude output before returning:
communique_text = strip_stage_directions(raw_output)
```

Verify this is applied to:
- Regular turn communiqués (all 4 NPCs)
- Negotiation responses (already done in fixes_14)
- Intel intercept output (already done in fixes_14)

**Verification:** Play 3 turns, open all 4 NPC communiqués. Confirm zero
asterisk-wrapped text in any communiqué.

---

### Fix E — Arabia 100 oil floor still at $52
**Problem:** Arabia 100 unlock fires correctly (message appears, flag set) but
oil price continues calculating from $52 base rather than enforcing the $45
floor. Fix J from fixes_14 added the floor check but it is not working.

**Root cause:** The $45 floor check likely runs before the world event oil
modifiers are applied, so the final price calculation ignores the floor.
The floor needs to be the LAST operation in the oil price calculation, not
an intermediate step.

**Fix:** In turn_processor.py, oil price calculation — move the Arabia 100
floor enforcement to the very end, after all modifiers:

```python
# Calculate oil price (base + tier modifiers + world event modifiers + embargo)
calculated_oil = base_price + world_event_modifier + embargo_surcharge

# Arabia 100 floor — applied LAST, after all other calculations
if getattr(game_state, 'arabia_100_unlocked', False):
    calculated_oil = max(calculated_oil, 45)
    if calculated_oil == 45:
        messages.append("🛢️ Arabia 100 floor enforced: $45/bbl minimum")

game_state.oil_price = calculated_oil
```

Note: floor prevents oil going BELOW $45 base. Embargo surcharges still apply
ON TOP of the $45 floor (so $45 base + $20 embargo = $65 total is correct).

**Verification:**
- Reach Arabia 100 (may need to use debug/manual relations)
- Confirm EOT shows oil at $45 base (or higher with surcharges)
- Confirm oil never shows below $45 in subsequent turns
- Confirm floor message appears when oil would otherwise be below $45

---

## ADDITIONAL BUGS

### Fix F — Intel tier not written to game_state after Get Intel
**Problem:** After gathering intel and receiving a "Deep Cover" (Tier 3) result,
the Blackmail Operation button still shows "current: Tier 0" for the target NPC.
The intercept result is generated and displayed correctly but the tier is never
saved back to game_state. Every NPC stays at Tier 0 permanently regardless of
intel gathered.

**Root cause:** The Get Intel endpoint returns the intercept text and tier label
but does not write the tier integer to game_state.npc_intel_tiers[npc].

**Fix:** In api.py, after generating the intel result:
```python
# Map tier label to integer
tier_map = {'surface': 1, 'operational': 2, 'deep_cover': 3}
tier_int = tier_map.get(tier_key, 1)

# Write to game_state — persists across turns
if not hasattr(game_state, 'npc_intel_tiers'):
    game_state.npc_intel_tiers = {}
game_state.npc_intel_tiers[target_npc] = tier_int
```

**Important:** npc_intel_tiers must persist across turns (survive EOT) so intel
gathered this turn is still readable when Blackmail executes next turn.
Add npc_intel_tiers to game_state serialization/deserialization if not already
present.

**Blackmail read path:** In ShadowCabinet.jsx, the Blackmail requirement should
read from the selected target NPC, not hardcoded USA:
```javascript
const intelTier = gameState.npc_intel_tiers?.[selectedTarget] ?? 0;
// "Requires Tier 3 intel on {selectedTarget} (current: {tierLabel})"
const tierLabel = {0: 'None', 1: 'Surface', 2: 'Operational', 3: 'Deep Cover'}[intelTier];
```

**Verification:**
- Gather intel on Arabia with Security 6+, Expansion funding
- Confirm intercept shows "Deep Cover"
- Switch target to Arabia in Operations tab
- Confirm Blackmail button now shows "current: Deep Cover" and is unlocked
- Execute Blackmail — confirm $5B deducted from personal wealth
- Confirm correct per-NPC concession fires (Arabia: oil floor locked 3 turns)
- Start new game, confirm npc_intel_tiers persists from Turn 3 to Turn 4

**Console log to add:**
`[api] FIX F: Intel tier stored — {npc}: {tier_int} ({tier_key})`

---

### Fix G — Arabia 100 unlock not firing reliably
**Problem:** Arabia 100 unlock has failed to fire across 4+ test runs despite
Arabia relations crossing 100. The unlock message, oil floor, and passive income
are not appearing in EOT. The function exists but is not being reached in the
EOT flow.

**Root cause:** Unknown — function is defined but console logs have never
confirmed it being called. Either the check condition uses strict equality
(== 100) instead of >= 100 and Arabia lands at 99.75 due to floating point,
or the function is called before Arabia relations are finalized for the turn
(world events can push Arabia to 100 after the check runs).

**Fix:** In turn_processor.py:
1. Add console.log at the very start of the Arabia 100 check:
   `print(f"  [turn_processor] FIX G: Arabia 100 check — current rel: {game_state.relations['arabia']}, already_unlocked: {getattr(game_state, 'arabia_100_unlocked', False)}")`
2. Change condition from `== 100` to `>= 100` if not already
3. Move the Arabia 100 check to AFTER all world events are applied in EOT,
   so world-event-driven relation changes are captured
4. Verify the unlock sets: arabia_100_unlocked = True, oil floor at $45,
   +$3B/turn passive income registered

**Verification:**
- Push Arabia to 100 via deals + world events
- Confirm console log shows check being reached with correct relation value
- Confirm EOT shows Sadam milestone message
- Confirm oil floor $45 enforced next turn

**Console log to add:**
`[turn_processor] FIX G: Arabia 100 CHECK reached — rel={rel}, unlocked={already}`
`[turn_processor] FIX G: Arabia 100 FIRED — unlock applied`

---

## DESIGN NOTES (not for this Claude Code session)

**Covert deal replacing main choice slot** — confirmed intentional. When the
game moves beyond 10 turns this becomes less relevant as the choice structure
evolves. No fix needed, add tooltip clarifying covert deals are separate from
the main diplomatic choice.

---

## CONFIRMED WORKING — DO NOT REGRESS

- Bond purchase callback (onGsUpdate fixed) ✅
- Bill intel intercept fictional framing (no refusal) ✅
- Game ends at Turn 10 ✅
- Covert cross-NPC penalties suppressed ✅
- FINANCE tab label ✅
- Advisor header text ✅
- Historian summary generates ✅
- False Flag bilateral score movement ✅
- Diplomat negotiation discount ✅

---

## CLAUDE CODE PROMPT

```
Read worldstage_fixes_15.md.
Confirm the first fix title before proceeding.

For Fix A: update turn_processor.py INCOMING trigger section.
  Replace double-AND conditions with single conditions + probability gates.
  Add ambient 5% trigger for all NPCs with tone scaling.
  Add console.logs as specified.
  Do not touch the INCOMING rendering path in the frontend —
  that is a separate trace issue already logged.

For Fix B: update bond financing in api.py and ShadowCabinet.jsx.
  $5B: 20% interest, no NPC penalty, once per turn, unlimited issuances.
  $10B: 30% interest, -5 all NPCs, budget < $20B gate, once per game.
  Add flavor text labels. Remove existing flat repeat-issuance penalty logic.

For Fix C: update infrastructure invest routing in api.py.
  Security 1-3 and Extraction: deduct from national budget.
  Security 4-6, Media, Judicial, Political: deduct from personal wealth.
  Add National/Personal badge labels to invest buttons in ShadowCabinet.jsx.
  Add tooltip for personal investments when personal wealth = $0.

For Fix D: apply strip_stage_directions() to NPC communiqué output
  in npc_engine.py. Verify it covers all 4 NPCs, not just negotiation log.

For Fix E: move Arabia 100 floor check to end of oil price calculation
  in turn_processor.py, after all modifiers applied.

For Fix F: in api.py, after Get Intel returns result, write tier integer to game_state.npc_intel_tiers[target_npc]. Add to serialization so it persists across turns. In ShadowCabinet.jsx, read intel tier from selected target NPC not hardcoded USA. Add console.log as specified.

For Fix G: in turn_processor.py, add console.log at start of Arabia 100 check. Change condition to >= 100. Move check to after all world events applied in EOT. Add console.logs as specified.

Do not implement design notes.
Do not implement any other fix files.
Do not add new features.
```

---

## FIX F — Intel tier not written to game_state after Get Intel

**Problem:** After gathering intel and receiving a "Deep Cover" (Tier 3) result,
the Blackmail Operation button still shows "current: Tier 0" for the target NPC.
The intercept is generated and displayed correctly but the tier is never saved
back to game_state. Every NPC stays at Tier 0 permanently regardless of intel
gathered.

**Root cause:** The Get Intel endpoint returns the intercept text and tier label
but does not write the tier integer to game_state.npc_intel_tiers[npc].

**Fix in api.py:** After generating the intel result:
```python
tier_map = {'surface': 1, 'operational': 2, 'deep_cover': 3}
tier_int = tier_map.get(tier_key, 1)

if not hasattr(game_state, 'npc_intel_tiers'):
    game_state.npc_intel_tiers = {}
game_state.npc_intel_tiers[target_npc] = tier_int
```

npc_intel_tiers must survive EOT — add to game_state serialization/
deserialization if not already present. Intel gathered Turn 3 must
still be readable when Blackmail executes Turn 4.

**Fix in ShadowCabinet.jsx:** Blackmail requirement reads from selected
target NPC, not hardcoded USA:
```javascript
const intelTier = gameState.npc_intel_tiers?.[selectedTarget] ?? 0;
const tierLabel = {0:'None',1:'Surface',2:'Operational',3:'Deep Cover'}[intelTier];
// "Requires Tier 3 intel on {selectedTarget} (current: {tierLabel})"
```

**Verification:**
- Gather Deep Cover intel on Arabia (Security 6+, Expansion funding)
- Switch target to Arabia in Operations tab
- Confirm Blackmail shows "current: Deep Cover" and button is unlocked
- Execute — confirm $5B deducted, Arabia oil floor locked 3 turns
- Confirm intel tier persists from one turn to the next

**Console log:** `[api] FIX F: Intel tier stored — {npc}: {tier_int} ({tier_key})`

---

## FIX G — Arabia 100 unlock not firing reliably

**Problem:** Arabia 100 unlock has failed across 4+ test runs despite Arabia
crossing 100. Milestone message, oil floor, and passive income never appear
in EOT. Function exists but console logs have never confirmed it being called.

**Likely root causes:**
1. Condition uses strict == 100 but Arabia lands at 99.75 due to floating point
2. Check runs before world events are applied — world event pushes Arabia to 100
   after the check already passed

**Fix in turn_processor.py:**
1. Add console.log at start of Arabia 100 check:
   `print(f"  [turn_processor] FIX G: Arabia 100 check — rel: {game_state.relations['arabia']}, unlocked: {getattr(game_state, 'arabia_100_unlocked', False)}")`
2. Change condition to `>= 100` if not already
3. Move check to AFTER all world events are applied in EOT so world-event
   relation bumps are captured
4. Verify unlock sets: arabia_100_unlocked = True, $45 oil floor, +$3B/turn
   passive income

**Verification:**
- Push Arabia to 100 via deals + world events
- Confirm console log shows check reached with correct relation value
- Confirm EOT shows Sadam milestone message
- Confirm oil floor $45 enforced next turn (also verifies Fix E)

**Console logs:**
`[turn_processor] FIX G: Arabia 100 CHECK reached — rel={rel}, unlocked={already}`
`[turn_processor] FIX G: Arabia 100 FIRED — unlock applied`
