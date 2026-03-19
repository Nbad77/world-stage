# WORLD STAGE — fixes_8c.md
# Exile Sequence — Post-Comet Fix Batch
Generated: March 12, 2026

---

## FIRST ACTION

Read this file completely before writing any code.
Confirm the title "fixes_8c — Exile Sequence Post-Comet" before starting.
Do not produce a plan or summary. Implement Fix A first, then stop and wait.
Proceed fix by fix in order. Do not skip any fix.
Do not implement any feature not listed here.

---

## FIX A — HTTP 500 on Diplomatic Choice (CRITICAL)

**Problem:** Every attempt to submit a diplomatic choice causes an HTTP 500 error.
Turn cannot advance. The AI generation call for diplomatic responses is failing.

**Likely cause:** Model string regression — same class of bug as the Haiku string
regression fixed in 8A (generate_contact_dialogue had hardcoded
"claude-3-haiku-20240307" instead of MODEL constant).

**Fix:**
1. Search npc_engine.py and api.py for any hardcoded model strings:
   - "claude-3-haiku-20240307"
   - "claude-3-opus-20240229"
   - "claude-3-sonnet-20240229"
   - Any other hardcoded model string that is not the MODEL constant
2. Replace all occurrences with the MODEL constant
3. Also check: any function added during 8C implementation that makes
   a Claude API call — confirm each one uses MODEL, not a hardcoded string
4. Check api.py for any new endpoints added in 8C that call Claude —
   verify their error handling is not swallowing the real error

**Console log to add:**
```
[api] diplomatic choice handler — model: {model_string_used}
```
Add to the diplomatic choice handler so the model string is visible in
the CONSEQUENCES panel on every turn advance.

**Verification:** Human submits a diplomatic choice → no HTTP 500 → turn advances.

---

## FIX B — Destination City Not Rendering (CRITICAL)

**Problem:** ExileDashboard always shows "EXILE — Unknown" for destination,
regardless of NPC relations. Destination city and flavor text are never displayed.

**Root cause:** Destination routing likely only calculates at the moment an
organic exile trigger fires (in exile_sequence_start() or equivalent). When
in_exile is toggled via DEV panel, game_state has no exile_destination set,
so ExileDashboard gets null/empty and falls back to "Unknown."

**Fix — two parts:**

Part 1 — Backend: In game_state.py or turn_processor.py, extract the destination
calculation into a standalone helper function:

```python
def _calculate_exile_destination(gs):
    """Returns (destination_city, destination_npc) based on highest NPC relations."""
    relations = {
        'usa': gs.relations.get('usa', 0),
        'arabia': gs.relations.get('arabia', 0),
        'eu': gs.relations.get('eu', 0),
        'dprg': gs.relations.get('dprg', 0),
        'russia': gs.relations.get('russia', 0),
        'china': gs.relations.get('china', 0),
    }
    top_npc = max(relations, key=relations.get)
    destinations = {
        'usa': ('Washington D.C.', 'usa'),
        'eu': ('Brussels', 'eu'),
        'arabia': ('Riyadh', 'arabia'),
        'dprg': ('Pyongyang', 'dprg'),
        'russia': ('Moscow', 'russia'),
        'china': ('Shanghai', 'china'),
    }
    return destinations[top_npc]
```

Part 2 — ExileDashboard.jsx: If exile_destination is null or empty string,
call the backend to calculate it on the fly rather than showing "Unknown."
Add a fallback: when ExileDashboard mounts and exile_destination is empty,
make one API call to GET /game/{id}/state and derive the destination from
the highest relations value in the response. Display derived destination
immediately without waiting for a page reload.

**Console log to add:**
```
[exile] Destination calculated: {city} (highest NPC: {npc}, relations: {value})
```

**Verification:**
1. DEV panel: set usa_relations = 90, all others = 20, toggle in_exile ON
2. ExileDashboard shows "Washington D.C." (or equivalent USA destination)
3. Repeat with eu_relations = 90 → shows "Brussels"
4. Repeat with russia_relations = 90 → shows "Moscow"

---

## FIX C — Flavor Text Not Displayed (HIGH)

**Problem:** No destination flavor text or wealth-tier text appears anywhere
in ExileDashboard. There is no text box or section for it.

**Fix — ExileDashboard.jsx:**
Add a flavor text section below the destination header. Content is determined
by two factors: destination NPC and wealth tier.

Wealth tiers:
- Above $20B: "comfortable" tier
- $5B–$20B: "functional" tier
- Below $5B: "desperate" tier

Flavor text strings — hardcode these exactly:

**USA destination:**
- Comfortable: "A Georgetown townhouse. Consultants return your calls. Your book deal is already being discussed."
- Functional: "A corporate apartment in Foggy Bottom. You have meetings. You have options."
- Desperate: "A budget hotel near Dulles. You have forty-eight hours to make yourself useful to someone."

**EU destination:**
- Comfortable: "A villa outside Brussels. MEPs take your lunches. You are a cautionary tale they find instructive."
- Functional: "A serviced flat in the European Quarter. Useful, for now."
- Desperate: "A hostel near Schuman. The Commission does not return calls from people in your position."

**Arabia destination:**
- Comfortable: "A suite at the Four Seasons Riyadh. Sadam's people check in regularly. Comfort has a price."
- Functional: "A guesthouse outside the city. Quiet. Watched."
- Desperate: "A room that smells of air conditioning and obligation. You owe someone something."

**DPRG destination:**
- Comfortable: "Pyongyang guest quarters. The hospitality is absolute and non-negotiable."
- Functional: "A state guesthouse. Ji-won's people know where you are at all times."
- Desperate: "You are here because nowhere else would take you. Ji-won knows this too."

**Russia destination:**
- Comfortable: "A dacha outside Moscow. Volkov decided you were worth something. For now."
- Functional: "A Moscow apartment. Functional. The FSB has your passport."
- Desperate: "A hotel room in a city you won't name. Volkov's generosity has conditions."

**China destination:**
- Comfortable: "A serviced apartment in Shanghai's French Concession. Comfortable. Watched."
- Functional: "A business hotel in Pudong. Wei's office has noted your arrival."
- Desperate: "A transit arrangement through Shenzhen. Temporary, they say."

Display format in ExileDashboard: italic text, muted color, beneath the
destination city header. Should feel like a historian observation, not a
status readout.

**Verification:**
1. DEV panel: set personal_wealth = 25, usa highest relations, in_exile ON
   → Georgetown comfortable flavor text appears
2. Set personal_wealth = 3 → desperate flavor text appears
3. Set china highest → Shanghai flavor text

---

## FIX D — Covert Operations Section Missing (CRITICAL)

**Problem:** The EXILE ACTIONS panel in ExileDashboard only contains WAIT.
Covert operations (destabilization, relationship maintenance, return preparation)
are entirely absent.

**Fix — ExileDashboard.jsx:**
Add a COVERT OPERATIONS section to the exile actions panel.
Only render this section if `exile_apparatus_survived === true`.
If apparatus did not survive, show a greyed-out section with text:
"Shadow apparatus compromised — covert operations unavailable."

Three operations to add as buttons:

**Destabilization**
- Label: "DESTABILIZE"
- Description: "Sow instability in Europa. Weakens the successor government."
- Cost: $1.5B
- Effect on click: POST /game/{id}/exile_action with action_type "covert_op",
  op_type "destabilization"
- Result: successor_relations_modifier applied, log entry generated

**Relationship Maintenance**
- Label: "MAINTAIN NETWORK"
- Description: "Keep your contacts warm. Slows NPC relation decay in exile."
- Cost: $0.8B
- Effect on click: POST /game/{id}/exile_action with action_type "covert_op",
  op_type "relationship_maintenance"
- Result: pauses NPC relation drift for 3 days, log entry generated

**Return Preparation**
- Label: "PREPARE RETURN"
- Description: "Lay groundwork for a comeback. Reduces return cost with one NPC."
- Cost: $2.0B — player selects which NPC before confirming
- Effect on click: POST /game/{id}/exile_action with action_type "covert_op",
  op_type "return_preparation", target_npc: selected NPC
- Result: return_price_modifier applied to that NPC, log entry generated

Each button must show a cost confirmation dialog before executing.
Format: "DESTABILIZE — Cost: $1.5B. Confirm?" with Confirm / Cancel.

**Backend — api.py:**
Confirm /game/{id}/exile_action already handles op_type routing for
"destabilization", "relationship_maintenance", "return_preparation".
If not, add the routing. Stub effects are acceptable — log entries and
cost deduction must work even if downstream effects are placeholders.

**Console logs to add:**
```
[exile] Covert op executed: {op_type}, cost: ${cost}B, apparatus: survived={survived}
[exile] Covert op blocked: apparatus not survived
```

**Verification:**
1. DEV panel: in_exile ON, apparatus_survived = true (if field exists in DEV panel)
2. COVERT OPERATIONS section appears with 3 buttons
3. Click DESTABILIZE → confirmation dialog appears → confirm → $1.5B deducted,
   log entry in ExileDashboard
4. DEV panel: apparatus_survived = false → section shows "unavailable" state

---

## FIX E — NPC Exile Dialogue Not Generating Prose (HIGH)

**Problem:** REACH OUT in exile mode returns only a mechanical log line
("Reached out to USA. Relations: 21 → 26. Cost: $1.0B. Operating without
state leverage.") — no AI-generated NPC dialogue. The whole dramatic weight
of the exile sequence depends on candid NPC conversations.

**Fix — api.py and npc_engine.py:**

In the exile_action handler for "reach_out", after deducting cost and
adjusting relations, make a Claude API call to generate NPC dialogue.

In npc_engine.py, add function generate_exile_contact_response():

```python
def generate_exile_contact_response(gs, npc_id):
    """Generates NPC response to player reaching out from exile."""
    exile_context = _get_exile_prompt_suffix(gs, npc_id)
    # Build system prompt: NPC personality container + exile context
    # Key instruction: NPC is more candid than in-power mode.
    # They are not in a negotiation. They are deciding how much
    # to reveal about what they actually thought of the player.
    # Tone varies by:
    #   - exile_trigger: voted_out gets most candid, coup gets most guarded
    #   - NPC personality (Volkov sparse, Wei indirect, Bill direct, etc.)
    #   - current relations: high = warmer, low = cold or absent
    # Length: 3-5 sentences. No markdown. Plain prose.
    # Model: MODEL constant (not hardcoded)
```

The exile_context (_get_exile_prompt_suffix) should already exist in
npc_engine.py from 8C implementation. Confirm it is actually being
passed into this new call.

In api.py exile_action handler:
- After relations update, call generate_exile_contact_response()
- Return the generated dialogue in the API response JSON alongside
  the mechanical log data
- Format: {"result": "...", "npc_dialogue": "...", "cost": X, "relations_change": X}

In ExileDashboard.jsx:
- After REACH OUT response, display npc_dialogue in a styled dialogue
  box, same visual treatment as normal NPC communiqués but with a
  muted/desaturated color to reflect exile context
- Show mechanical log (cost, relations change) beneath the dialogue box

**Console log to add:**
```
[exile] Exile dialogue generated for {npc_id}, trigger: {exile_trigger}
```

**Verification:**
1. in_exile ON → REACH OUT on Bill → AI-generated prose appears
2. REACH OUT on Volkov → distinct sparse institutional voice
3. REACH OUT on Marsha → warmer if EU relations high
4. Log shows [exile] Exile dialogue generated in CONSEQUENCES panel

---

## FIX F — REACH OUT Cost Confirmation Dialog Missing (MEDIUM)

**Problem:** REACH OUT executes immediately on click with no cost preview
or confirmation step. Player cannot see what it will cost before committing.

**Fix — ExileDashboard.jsx:**
Add a confirmation modal before executing REACH OUT. Modal shows:
- NPC name
- Estimated cost ($0.5B–$1.5B based on relations, same formula as current)
- Current relations value
- Confirm / Cancel buttons

Only execute the API call on Confirm.

**Verification:**
Click REACH OUT on any NPC → modal appears with cost → Cancel dismisses
without deducting → Confirm executes and deducts.

---

## FIX G — Apparatus Status Indicator Missing (MEDIUM)

**Problem:** No apparatus status indicator visible anywhere in ExileDashboard.
Player cannot see whether their shadow apparatus survived.

**Fix — ExileDashboard.jsx:**
Add a compact status line to the exile header area (near wealth/runway display):

If apparatus survived:
  "🕵️ Shadow apparatus: ACTIVE — $0.3B/day"

If apparatus did not survive:
  "🕵️ Shadow apparatus: COMPROMISED — covert ops unavailable"

Also update the runway calculation to reflect apparatus status:
- Apparatus active: burn rate = $0.5B/day ($0.2B living + $0.3B apparatus)
- Apparatus compromised: burn rate = $0.2B/day (living only)

**Verification:**
1. DEV panel: apparatus_survived = true → "ACTIVE" status and $0.5B/day burn rate
2. DEV panel: apparatus_survived = false → "COMPROMISED" status and $0.2B/day

---

## FIX H — ACCEPT BACKING Exclusion Warning Missing Specific Names (LOW)

**Problem:** The backing confirmation modal says "competing backing doors
will close" generically, without naming which specific NPCs will be excluded.

**Fix — ExileDashboard.jsx:**
In the BACKING confirmation modal for each NPC, show the specific
parties that will be excluded. Hardcode the exclusion map:

```javascript
const BACKING_EXCLUSIONS = {
  usa: ['DPRG', 'Russia'],
  russia: ['USA', 'EU'],
  dprg: ['USA', 'EU'],
  china: ['USA'],
  eu: [],
  arabia: [],
};
```

Modal text: "Accepting [NPC] backing will permanently close backing
from: [excluded list]." If exclusions is empty, omit this line.

**Verification:**
Click BACKING on USA → modal shows "will permanently close backing
from: DPRG, Russia" before confirming.

---

## VERIFICATION SEQUENCE

Implement fixes in order A through H. After each fix, add the required
console.log and stop. Do not proceed to the next fix without confirmation.

Human will verify in browser after each fix.

After all fixes are implemented, the human will re-run the Comet test
script to confirm full pass.

## DO NOT IMPLEMENT

- Comeback mechanics (Session 9A)
- Successor GM call (Session 9A)
- Any new NPC personalities
- Any Session 8D, 8E, or 8F features
- Any changes to the main dashboard
- Any changes to the summit system
