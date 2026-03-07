# Daily Briefing System — Design Specification
## Session 5 Deliverable (doc only — no implementation this session)

---

## Overview

The Daily Briefing is a turn-start information panel that synthesizes the current game state into a narrative intelligence report. It replaces the raw stat dump with a contextual summary that helps the player understand **what happened**, **why it matters**, and **what to watch**.

Generated once per turn via a single Claude Haiku call, cached on `game_state.current_briefing`.

---

## Structure

### 1. Header
```
DAILY BRIEFING — Turn {N} of {max_turns}
Regime: {regime_type} | Power Base: {power_base}
```

### 2. Priority Alert (0-2 per briefing)
Urgent items requiring immediate attention. Drawn from:
- Sanctions/embargo escalation risk (relations within 5 of tier boundary)
- Imminent election (election_turn - 1)
- Budget bankruptcy projection (projected budget <= $3B)
- Active scandal fallout
- Advisor betrayal last turn
- NPC-initiated contacts pending

Format:
```
[!] PRIORITY: {alert_description}
```

### 3. State of the Nation (always present)
3-4 sentence summary of domestic conditions:
- Budget health (surplus/deficit trend, maintenance costs)
- Stability trajectory (rising/falling/stable)
- Approval sentiment (popular/divided/hostile)
- Economic indicators (GDP growth, tax burden impact)

### 4. Foreign Relations Summary (always present)
One line per NPC with directional indicator:
```
USA (Bill Hartwell):  {relation} — {trend} — {key_context}
ARABIA (Sadam):       {relation} — {trend} — {key_context}
EU (Marsha Lindgren): {relation} — {trend} — {key_context}
DPRG (Ji-won):        {relation} — {trend} — {key_context}
```

Trend: Rising / Stable / Declining / Critical
Key context: active deals, sanctions, recent negotiation, incoming contact

### 5. Cabinet Status (if any axes > 0)
Summary of Shadow Cabinet state:
- Active axis levels and maintenance cost
- Advisor roster (names, loyalty warnings)
- Brigade operation results from last turn

### 6. Intelligence Assessment (if intel apparatus active)
- Detection heat level and trend
- Known NPC stances (from intel intercepts)
- Soft power / diplomatic capital summary

### 7. Advisor Whispers (if advisors active)
Each active advisor contributes a 1-sentence observation filtered through their bias:
- Advisors with bias_stat distort the relevant number
- Low-loyalty advisors may provide misleading assessments
- High-competence advisors give more actionable intelligence

Format:
```
{advisor_icon} {advisor_name} ({label}): "{observation}"
```

---

## Generation Pipeline

### Input Assembly
```python
def build_briefing_context(game_state) -> str:
    """Assemble all data needed for the briefing prompt."""
    # 1. Core stats snapshot
    # 2. Relations + trends (compare to previous turn)
    # 3. Active alerts (sanctions, election, bankruptcy)
    # 4. Cabinet axes summary
    # 5. Advisor roster with bias info
    # 6. Last turn's EOT messages (summarized)
    # 7. Pending NPC contacts
    # 8. Memory context (Tier 2 relationship summaries)
```

### Prompt Structure
```
System: You are the intelligence chief of Europa, preparing the daily briefing
for the country's leader. Write in a terse, professional intelligence style.
Maximum 250 words. Use the exact stat values provided — do not invent numbers.

User: [assembled context from build_briefing_context()]

Instructions:
- Start with any PRIORITY alerts
- Summarize domestic conditions in 3-4 sentences
- One line per foreign power with relation value, trend, and key context
- If advisors are active, include their observations (apply their bias)
- End with 1 sentence on recommended focus area
- Never use markdown headers — use line breaks and [!] prefixes only
```

### Caching
- Generated once when turn starts (first GET /game/{id} with new turn number)
- Stored in `game_state.current_briefing` (string)
- Cleared at end of turn (`apply_end_of_turn_effects`)
- If generation fails, fallback to structured stat summary (no Claude call)

---

## Frontend Integration

### New Component: `BriefingPanel.jsx`
- Displayed at top of turn, before action choices
- Monospace font, dark background (intelligence report aesthetic)
- Collapsible — starts expanded on new turn, can be minimized
- "Dismiss" button advances to action phase

### Placement in GameScreen Flow
```
Turn Start
  -> BriefingPanel (new)
  -> IntelAllocationPanel (existing)
  -> OffersPanel / SkimPanel (existing)
  -> DialoguePanel (existing)
```

---

## Advisor Distortion in Briefings

When advisors have `bias_stat` and fail their loyalty check:
1. The briefing prompt receives the **distorted** stat value (true + bias_direction)
2. Claude writes the briefing using the distorted number
3. Player sees a plausible but inaccurate assessment
4. Only by cross-referencing the StatusBar (which shows true values) can the player detect the lie

This creates a trust game: do you believe your advisor or your dashboard?

---

## Data Dependencies

| Field | Source | Used For |
|-------|--------|----------|
| `game_state.*` (all core stats) | game_state.py | State of the Nation |
| `game_state.relations` | game_state.py | Foreign Relations Summary |
| `game_state.cabinet_axes` | game_state.py | Cabinet Status |
| `game_state.advisors` | game_state.py | Advisor Whispers |
| `game_state.advisor_distortions` | advisor_engine.py | Distorted stat values |
| `game_state.pending_npc_contacts` | turn_processor.py | Priority Alerts |
| `game_state.deal_history` | game_state.py | Foreign Relations context |
| `NpcRelationshipSummary` | memory_engine.py | Relationship context |
| EOT messages from previous turn | turn_processor.py | What happened last turn |

---

## Token Budget

- Input context: ~800 tokens (stat snapshot + summaries)
- Output: ~350 tokens (250 words target)
- Model: claude-haiku-4-5-20251001
- Temperature: 0.4 (factual but with personality)
- Max tokens: 500

---

## Implementation Notes (for future session)

1. **New game_state fields:**
   - `current_briefing: str | None` — cached briefing text
   - `briefing_turn: int` — turn number the briefing was generated for
   - `previous_turn_stats: dict` — snapshot of key stats at previous EOT (for trend detection)

2. **New API behavior:**
   - `GET /game/{id}` checks if `briefing_turn < current_turn` and generates if needed
   - New field in response: `briefing: str`

3. **New backend function:**
   - `generate_daily_briefing(game_state) -> str` in a new `briefing_engine.py`

4. **Fallback:**
   - If Claude call fails, return a structured template using f-strings
   - Template includes all stats but no narrative personality

---

## Open Questions (to resolve before implementation)

1. Should the briefing be skippable or mandatory reading?
2. Should advisor distortions be marked in any way (e.g., italics for distorted values)?
3. Should the briefing include specific deal recommendations or stay observational?
4. How to handle turn 1 briefing (no previous turn data for trends)?
5. Should briefing text be included in the legacy/ending screen as a historical record?
