# WORLD STAGE — Tech Level Tier Spec
Generated: March 9, 2026

---

## CONTEXT

The passive Tech Level gain formula is already implemented in turn_processor.py.
This spec adds the threshold logic, specific unlocks per tier, and the EU ceiling
hard cap mechanic on top of the existing formula.

Do NOT change the gain formula. Only add tier thresholds and their effects.

---

## PASSIVE GAIN FORMULA (already implemented — do not change)

```python
tech_gain = sum of (relations/100 × weight × BASE_TECH_RATE)

NPC weights:
  EU:    1.00
  USA:   0.90
  DPRG:  0.50
  Arabia: 0.30

BASE_TECH_RATE = 0.5
```

Education absorption multiplier (already stubbed):
```python
effective_tech_gain = raw_tech_gain × (1 + education_bonus)

education_bonus values:
  None:     0.00
  Basic:    0.10
  Developed: 0.20
  Advanced:  0.35
```

---

## TIER THRESHOLDS

| Tier | Name | Range | 
|------|------|-------|
| 0 | Pre-Industrial | 0–9 |
| 1 | Emerging Capability | 10–24 |
| 2 | Functional Modernization | 25–49 |
| 3 | Strategic Capability | 50–74 |
| 4 | Advanced Economy | 75–99 |
| 5 | Frontier | 100+ |

---

## UNLOCKS PER TIER

### Tier 0 (0–9)
- No active modifiers
- EU ceiling: $3B (Marsha's existing base cap)
- Economy efficiency modifier: 0%
- Intel detection risk modifier: 0%

### Tier 1 (10–24)
- EU ceiling: $4B
- Economy efficiency modifier: +5% GDP multiplier
- Intel detection risk modifier: −5% on all operations

### Tier 2 (25–49)
- EU ceiling: $5B
- Economy efficiency modifier: +12% GDP multiplier
- Intel detection risk modifier: −10%
- Tranche deals: accessible at lower rapport threshold (−1 rapport required)
- Foreign investment spillover: Arabia and DPRG deals carry +3% secondary GDP modifier

### Tier 3 (50–74)
- EU ceiling: $7B
- Economy efficiency modifier: +20% GDP multiplier
- Intel detection risk modifier: −15%
- State apparatus intercept quality: approaches shadow apparatus level for standard ops
- Tech transfer as bargaining chip: player can offer tech in NPC negotiations
  - DPRG values surveillance/weapons-adjacent tech
  - Arabia values energy infrastructure tech
  - These count toward the willingness formula as a concrete offer type

### Tier 4 (75–99)
- EU ceiling: $9B
- Economy efficiency modifier: +30% GDP multiplier
- Intel detection risk modifier: −20%
- Rapport requirement for EU tranches: reduced by 1
- Tech leverage unlock: player can credibly threaten to redirect tech partnerships
  (e.g. "shift partnership to China" — NPCs treat this as a credible threat at Tier 4)

### Tier 5 (100+)
- EU ceiling: REMOVED — Marsha's offers governed by rapport only
- Economy efficiency modifier: +40% GDP multiplier
- Intel detection risk modifier: maximum effectiveness (cap at system maximum)
- Middle power transition flag: fires ONCE on first reaching Tier 5
  - Sets `middle_power_transition` flag in game_state (permanent)
  - Triggers one-time narrative event card in briefing
  - Updates all NPC system prompt context to reflect Europa's new status
  - Historian produces a one-time mid-era verdict acknowledging the shift
  - Bill's diplomatic register changes (stops offering, starts asking)

---

## EU CEILING — IMPLEMENTATION NOTE

The EU ceiling is a HARD CAP on Marsha's maximum offer, not a modifier to
her willingness formula. It applies regardless of rapport or relations score.

```python
EU_TECH_CEILINGS = {
    0: 3.0,   # Tier 0: $3B
    1: 4.0,   # Tier 1: $4B
    2: 5.0,   # Tier 2: $5B
    3: 7.0,   # Tier 3: $7B
    4: 9.0,   # Tier 4: $9B
    5: None,  # Tier 5: no cap
}

def get_eu_ceiling(tech_level):
    tier = get_tech_tier(tech_level)
    return EU_TECH_CEILINGS[tier]
```

Apply in npc_engine.py wherever Marsha's final offer is calculated.
If the computed offer exceeds the ceiling, cap it at the ceiling value.
Marsha should reference the cap in-character if it fires:
  "I want to offer you more, but the infrastructure your economy
   can absorb right now is limited."

---

## ECONOMY EFFICIENCY MODIFIER

Apply as a multiplier to GDP baseline revenue in turn_processor.py section 9b
(after all consequences resolve, where GDP calc currently lives).

```python
def get_economy_efficiency_modifier(tech_level):
    tier = get_tech_tier(tech_level)
    modifiers = {0: 0.0, 1: 0.05, 2: 0.12, 3: 0.20, 4: 0.30, 5: 0.40}
    return modifiers[tier]

# In GDP calc:
gdp_revenue = base_gdp_revenue × (1 + get_economy_efficiency_modifier(gs.tech_level))
```

---

## HELPER FUNCTION

```python
def get_tech_tier(tech_level):
    if tech_level >= 100: return 5
    if tech_level >= 75:  return 4
    if tech_level >= 50:  return 3
    if tech_level >= 25:  return 2
    if tech_level >= 10:  return 1
    return 0
```

---

## FILES TO MODIFY

- `turn_processor.py` — economy efficiency modifier in GDP calc, tech tier helper
- `npc_engine.py` — EU ceiling cap in Marsha offer calculation, tech transfer
  bargaining chip as offer type, tech leverage unlock at Tier 4
- `game_state.py` — add `middle_power_transition` boolean field (default False),
  add `tech_tier` computed property
- `LeftSidebar.jsx` — display current tech tier name alongside tech level number
- `StatusBar.jsx` — tech level already shows at 0 (fixed in fixes_21);
  add tier label next to number

---

## CONSOLE LOGS REQUIRED FOR VERIFICATION

```
[tech_level] Tier transition: {old_tier} → {new_tier} at tech_level={value}
[tech_level] EU ceiling applied: offer capped at ${ceiling}B (tier={tier})
[tech_level] Economy efficiency modifier: +{pct}% (tier={tier})
[tech_level] Intel detection risk modifier: -{pct}% (tier={tier})
[tech_level] MIDDLE POWER TRANSITION FLAG SET — fires once
```

---

## VERIFICATION STEPS (human verifies in browser)

1. Start a fresh game, confirm tech display shows tier label
2. Use cheat panel to set tech_level = 10, confirm Tier 1 label appears and
   GDP modifier shows in console
3. Set tech_level = 25, confirm Tier 2 and EU ceiling changes in Marsha negotiation
4. Set tech_level = 50, confirm Tier 3 and −15% detection in backchannel modal
5. Set tech_level = 100, confirm Tier 5, EU ceiling removed, middle power flag
   fires exactly once in console and briefing event card appears

---

## DO NOT IMPLEMENT

- Any changes to the passive gain formula
- Any changes to the education bonus formula
- Any new NPC personalities or dialogue
- Any Session 8 features
