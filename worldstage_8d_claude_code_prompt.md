# WORLD STAGE — 8D Claude Code Prompt
# The Leak — Scripted Branching Crisis
Generated: March 12, 2026

---

## FIRST ACTION

Read this file completely before writing any code.
Confirm the title "8D — The Leak" before starting.
Do not produce a plan or summary. Begin with game_state.py. Nothing else first.
Do not implement any feature not listed here.

---

## WHAT THIS IS

The Leak is the first scripted branching crisis — a hand-crafted Sophie's choice
moment that fires at a specific game state threshold. Both options hurt. Neither
is clean. This establishes the framework that future crises will reuse.

The Leak fires when the player has been playing both sides: maintaining a DPRG
relationship while USA relations are high. Someone leaked the backchannel.
Now the player must decide how to handle it — and every option costs something.

---

## SCOPE BOUNDARY

IN SCOPE: Everything in this prompt.
OUT OF SCOPE: Any other scripted crises, any Session 8E/8F features,
any changes to the exile system, any new NPC personalities beyond
what's specified here for crisis dialogue.

---

## FILE 1: game_state.py

Add these fields to GameState.__init__():

```python
self.the_leak_fired = False        # True once triggered, never fires again
self.the_leak_resolved = False     # True once player picks a response
self.the_leak_choice = None        # 'deny' | 'admit' | 'blame' | 'jiwon'
self.the_leak_followup_fired = False  # True once follow-up consequences fire
self.scapegoat_used = False        # True once blame-a-minister has been used
                                   # (one-time mechanic across all crises)
```

Add to serialize() and deserialize() with safe defaults (all False/None
if missing — safe for pre-8D saves).

---

## FILE 2: turn_processor.py

### Trigger Detection

Add a check at the TOP of the end-of-day processing loop, BEFORE world
events fire. If the_leak_fired is already True, skip. Otherwise:

```python
def _check_the_leak_trigger(gs):
    """
    Fires if: DPRG deal active AND USA relations above 60.
    DPRG deal active = any entry in gs.active_deals where npc == 'dprg'
    and the deal is not expired.
    """
    if gs.the_leak_fired:
        return False
    if gs.relations.get('usa', 0) <= 60:
        return False
    dprg_has_active_deal = any(
        d.get('npc') == 'dprg' and not d.get('expired', False)
        for d in gs.active_deals
    )
    if not dprg_has_active_deal:
        return False
    return True
```

When trigger fires:
- Set gs.the_leak_fired = True
- Add a crisis briefing item to the day's briefing output with tag "CRISIS"
- Log: `[leak] The Leak triggered: dprg_deal=True usa_relations={value}`

### Follow-Up Consequences

Add a separate function that runs at the start of the NEXT day after
the_leak_resolved becomes True and the_leak_followup_fired is False:

```python
def _process_leak_followup(gs):
    """Fires one day after player resolves The Leak."""
    if not gs.the_leak_resolved:
        return
    if gs.the_leak_followup_fired:
        return
    
    choice = gs.the_leak_choice
    
    if choice == 'deny':
        # Scandal risk materializes — roll 40% chance
        import random
        if random.random() < 0.40:
            gs.heat = min(100, gs.heat + 15)
            # Add follow-up briefing item: "Media questions persist"
        # No further mechanical consequence — already hit on choice
    
    elif choice == 'admit':
        # DPRG sends a cold communiqué — no mechanics, just narrative
        # Add follow-up briefing item: Ji-won communiqué
        pass
    
    elif choice == 'blame':
        # Minister is publicly named — approval hit materializes
        gs.approval = max(0, gs.approval - 5)
        # Add follow-up briefing item: "Minister denies involvement"
    
    elif choice == 'jiwon':
        # Story suppressed — Ji-won sends a brief communiqué acknowledging
        # the arrangement. Warm but carries implicit weight.
        # Add follow-up briefing item: Ji-won communiqué
        pass
    
    gs.the_leak_followup_fired = True
    print(f"[leak] Follow-up consequences fired: choice={choice}")
```

---

## FILE 3: api.py

### New Endpoint

Add POST /game/{game_id}/crisis/the_leak with body:
```json
{ "choice": "deny" | "admit" | "blame" | "jiwon" }
```

Handler logic:

```python
@app.post("/game/{game_id}/crisis/the_leak")
async def resolve_the_leak(game_id: str, body: dict, ...):
    gs = load_game(game_id)
    
    if not gs.the_leak_fired:
        raise HTTPException(400, "The Leak has not triggered")
    if gs.the_leak_resolved:
        raise HTTPException(400, "The Leak already resolved")
    
    choice = body.get('choice')
    if choice not in ('deny', 'admit', 'blame', 'jiwon'):
        raise HTTPException(400, "Invalid choice")
    
    # Check scapegoat availability
    if choice == 'blame' and gs.scapegoat_used:
        raise HTTPException(400, "Scapegoat already used")
    
    # Apply immediate consequences
    if choice == 'deny':
        gs.relations['usa'] = max(0, gs.relations.get('usa', 0) - 5)
        gs.relations['dprg'] = min(100, gs.relations.get('dprg', 0) + 5)
        gs.stability = max(0, gs.stability - 8)
        # Scandal risk fires in follow-up (40% next day)
        result_text = _generate_leak_resolution_narrative(gs, 'deny')
    
    elif choice == 'admit':
        gs.relations['usa'] = min(100, gs.relations.get('usa', 0) + 10)
        gs.relations['dprg'] = max(0, gs.relations.get('dprg', 0) - 15)
        gs.approval = max(0, gs.approval - 10)
        result_text = _generate_leak_resolution_narrative(gs, 'admit')
    
    elif choice == 'blame':
        gs.stability = max(0, gs.stability - 5)
        gs.scapegoat_used = True
        result_text = _generate_leak_resolution_narrative(gs, 'blame')
    
    elif choice == 'jiwon':
        if gs.personal_wealth < 3.0:
            raise HTTPException(400, "Insufficient personal wealth")
        gs.personal_wealth -= 3.0
        gs.relations['dprg'] = min(100, gs.relations.get('dprg', 0) + 3)
        result_text = _generate_leak_resolution_narrative(gs, 'jiwon')
    
    gs.the_leak_resolved = True
    gs.the_leak_choice = choice
    
    save_game(gs)
    
    print(f"[leak] Resolved: choice={choice}")
    
    return {
        "result": result_text,
        "choice": choice,
        "consequences": _build_leak_consequence_summary(choice, gs)
    }
```

### Narrative Generation

Add _generate_leak_resolution_narrative() in npc_engine.py.
This is a single Claude call (Haiku, ~150 tokens) that generates
2-3 sentences of historian-voice narration describing the player's
choice and its immediate effect. Not an NPC voice — the narrator's
voice, same register as the per-turn epitaph.

```python
def _generate_leak_resolution_narrative(gs, choice):
    choice_descriptions = {
        'deny': "publicly denied the back-channel with Ji-won",
        'admit': "admitted the back-channel and issued a public apology",
        'blame': "attributed the leak to a minister and accepted no personal responsibility",
        'jiwon': "quietly paid Ji-won to suppress the story"
    }
    prompt = f"""You are writing 2-3 sentences in the voice of a political historian 
narrating a moment in a leader's career. The leader {choice_descriptions[choice]}.
Current stability: {gs.stability}%. USA relations: {gs.relations.get('usa', 0)}.
DPRG relations: {gs.relations.get('dprg', 0)}.
Write in past tense. No markdown. No moralizing. Just the historian's cold observation."""
    # Call MODEL, return text
```

### Consequence Summary Helper

```python
def _build_leak_consequence_summary(choice, gs):
    """Returns a dict of what changed for display in the crisis resolution panel."""
    summaries = {
        'deny': {
            'usa': -5, 'dprg': +5, 'stability': -8,
            'note': 'Scandal risk: 40% chance of heat +15 tomorrow'
        },
        'admit': {
            'usa': +10, 'dprg': -15, 'approval': -10,
            'note': 'DPRG will respond coldly. USA credibility restored.'
        },
        'blame': {
            'stability': -5,
            'note': 'Scapegoat used. This option is now permanently unavailable.'
        },
        'jiwon': {
            'personal_wealth': -3.0, 'dprg': +3,
            'note': 'Ji-won suppressed the story. He remembers the favor.'
        }
    }
    return summaries[choice]
```

---

## FILE 4: Frontend — LeakCrisisModal.jsx (new component)

Create a new component: src/components/LeakCrisisModal.jsx

### Structure

Full-screen modal (same visual weight as SummitModal — this is a crisis,
not a routine event). Dark overlay. Does not close until player makes a choice.

**Header:**
```
🔴 CRISIS — THE LEAK
Classified documents reveal your back-channel with Ji-won Ryang
```

**Body — situation description:**
```
International media is reporting on classified communications between 
your office and DPRG leadership. The documents appear authentic. 
Bill Hartwell has requested an urgent explanation. Ji-won has gone silent.
You have hours to decide how to respond.
```

**Four choice cards** — each card shows:
- Option label (bold)
- One-sentence description
- Consequence preview (exact numbers, shown in muted text)
- Warning badge if applicable

**Option A — DENY PUBLICLY**
Description: "Issue a statement dismissing the documents as fabricated."
Consequences: USA −5 · DPRG +5 · Stability −8 · Scandal risk 40%

**Option B — ADMIT AND APOLOGIZE**
Description: "Acknowledge the communications and frame them as routine diplomacy."
Consequences: USA +10 · DPRG −15 · Approval −10%

**Option C — BLAME A MINISTER**
Description: "Attribute the leak to a rogue official. Name someone."
Consequences: Stability −5
Warning badge: "ONE-TIME — Scapegoat mechanic permanently consumed"
If gs.scapegoat_used === true: card is greyed out, shows "UNAVAILABLE —
scapegoat already used"

**Option D — LET JI-WON HANDLE IT**
Description: "Contact Ji-won's office and arrange for the story to disappear."
Consequences: −$3B personal · DPRG +3 · Story suppressed
If gs.personal_wealth < 3.0: Confirm button disabled, shows
"Insufficient funds ($3B required)"

**Footer:**
No close button. No escape. The player must choose.
Small italic text: "This decision will be recorded in your political biography."

### Interaction

On clicking a choice card: show a confirmation step within the modal
(not a separate modal). Card highlights, shows "Confirm this choice?" 
with Confirm / Back buttons. Confirm calls POST /game/{id}/crisis/the_leak.

On resolution: modal shows the historian narrative (from API response),
consequence summary (from API response), then a single "Continue" button
that closes the modal and returns to the dashboard. The day then advances.

### Styling

Use existing crisis/summit modal CSS patterns. Red accent color for the
CRISIS header badge. Choice cards use the same pattern as static deal
choice cards but with a more compressed layout to fit four options.

---

## FILE 5: Frontend — Integration

### GameScreen.jsx

Add state: `showLeakCrisis` (boolean), initialized false.

In the briefing item rendering logic: when a briefing item has tag "CRISIS"
and type "the_leak", render it as a special CRISIS card in the briefing list
(red border, urgent styling) with an "ADDRESS CRISIS" button that sets
`showLeakCrisis = true`.

The crisis card should not be dismissable — it stays in the briefing until
the player clicks ADDRESS CRISIS and completes the modal.

Render `<LeakCrisisModal>` when showLeakCrisis is true.

Pass props: `gs`, `onResolve` (callback that refreshes game state and closes modal).

### api.js

Add:
```javascript
export async function resolveTheLeakCrisis(gameId, choice) {
  return apiFetch(`/game/${gameId}/crisis/the_leak`, {
    method: 'POST',
    body: JSON.stringify({ choice })
  });
}
```

---

## CONSOLE LOGS REQUIRED

```
[leak] The Leak triggered: dprg_deal=True usa_relations={value}
[leak] Resolved: choice={choice}
[leak] Follow-up consequences fired: choice={choice}
[leak] Narrative generated: {first_20_chars}...
```

---

## VERIFICATION STEPS (human verifies in browser)

1. **Trigger test:** DEV panel → set usa_relations = 75, add an active DPRG deal
   (use debug set_state or cheat panel), End Day → CRISIS card appears in briefing

2. **Modal renders:** Click ADDRESS CRISIS → full-screen modal appears with
   situation text and 4 choice cards with correct consequence numbers

3. **Scapegoat gate:** gs.scapegoat_used = false → Option C available.
   Resolve crisis with Option C. Start new game, trigger again → Option C
   greyed out "UNAVAILABLE"

4. **Insufficient funds gate:** Set personal_wealth = 1.0 → Option D shows
   disabled with "Insufficient funds" message

5. **Deny path:** Choose DENY → USA drops 5, DPRG rises 5, stability drops 8,
   confirm in console log. Next day → 40% scandal roll fires in uvicorn log.

6. **Admit path:** Choose ADMIT → USA rises 10, DPRG drops 15, approval drops 10.
   Next day → Ji-won follow-up communiqué appears in briefing.

7. **Ji-won path:** Choose LET JI-WON HANDLE IT → $3B deducted from personal
   wealth, DPRG +3. Next day → Ji-won communiqué appears.

8. **Historian narrative:** After any choice, resolution screen shows 2-3
   sentences of historian prose before Continue button.

9. **One-time trigger:** After resolving, the_leak_fired = True. Trigger
   conditions met again → crisis does NOT fire a second time.

10. **Backward compat:** Load pre-8D save → no crash, all leak fields
    initialize to safe defaults.

---

## DO NOT IMPLEMENT

- Any other scripted crises (Opposition Defector, Border Incident, IMF Visit,
  Assassination Attempt) — framework only, The Leak only
- Emergency token system
- Any comeback mechanics
- Any Session 8E or 8F features
- Any changes to the exile system
- Any changes to the summit or backchannel systems
