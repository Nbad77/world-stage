# WORLD STAGE — 8A CLAUDE CODE PROMPT
# Russia and China Full NPC Integration

---

## FIRST ACTION

Read the file at: `/mnt/user-data/outputs/worldstage_8a_claude_code_prompt.md`

Then confirm the title "8A — Russia and China Full NPC Integration" and
begin writing code immediately.

DO NOT produce a plan, summary, or review of what you are about to do.
DO NOT output any document or checklist before coding.
DO NOT restate what you've read.
Start with the first code change in game_state.py. Nothing else first.
If you find yourself writing a bullet list instead of code, stop and write code.

---

## BEFORE YOU START

Read this entire prompt before writing any code. Confirm the title
"8A — Russia and China Full NPC Integration" before proceeding.

Do not implement any features beyond what is listed here.
Do not implement 8B, 8C, 8D, 8E, or 8F.
Do not add new world event generation logic for Russia/China.
Do not design NPC-100 unlock effects for Russia/China.
Do not add Education system content.

---

## CONTEXT

Russia and China currently exist as passive world actors — they have
relation fields (`self.russia_relations`, `self.china_relations`),
deal-based drift, and OBSERVER presence in the Summit modal. They have
NO Contact buttons, NO negotiation endpoints, NO personality containers,
and NO rapport system.

This session promotes them to full NPC status matching the pattern of
USA/Arabia/EU/DPRG.

---

## KEY ARCHITECTURAL DECISION — READ CAREFULLY

Migrate `russia_relations` and `china_relations` out of legacy standalone
fields and into the existing `self.relations` dict alongside the other
four NPCs.

WHY: All existing code (update_relations, calculate_willingness, rapport
system, leverage, cross-NPC drift, etc.) already operates on self.relations.
Adding 'russia' and 'china' as keys means ~60 call sites work automatically
without if-guards. This is the correct approach.

BACKWARD COMPAT: serialize() must write BOTH formats — the new dict key
AND the legacy field — so old saves don't break:
  `'russia_relations': self.relations.get('russia', 35.0)`

deserialize() reads dict first, falls back to legacy scalar:
  ```python
  if 'russia' not in self.relations:
      self.relations['russia'] = data.get('russia_relations', 35.0)
  if 'china' not in self.relations:
      self.relations['china'] = data.get('china_relations', 35.0)
  ```

---

## IMPLEMENTATION ORDER

Work through these 9 files in sequence. Stop after each file group
and confirm before continuing to the next.

---

## FILE 1: game_state.py — Data Foundation

### self.relations dict (line ~149)
Add starting values:
  `'russia': 35, 'china': 35`

### Tracking dicts (lines ~157-160)
Add russia and china to:
  - `times_sided_with`
  - `times_ignored`
  - `consecutive_sides`
  - `consecutive_ignores`

### total_aid_received (line ~288)
Add: `'russia': 0.0, 'china': 0.0`

### relations_high / relations_low (lines ~310-311)
Add: `'russia': 35, 'china': 35`

### relations_100_unlocks (lines ~337-342)
Add: `'russia': False, 'china': False`

### npc_relations bilateral matrix (lines ~184-191)
Add these new bilateral pairs with starting values:
  - `china_russia: 45`   (wary coexistence)
  - `russia_usa: 15`     (deep hostility)
  - `china_usa: 25`      (competitive tension)
  - `eu_russia: 20`      (adversarial)
  - `china_eu: 50`       (transactional)
  - `arabia_russia: 40`
  - `china_dprg: 35`
  - `arabia_china: 40`
  - `dprg_russia: 30`

### Remove legacy fields (lines ~458-460)
Remove `self.russia_relations` and `self.china_relations` standalone
scalar fields. Their values now live in self.relations['russia'] and
self.relations['china'].

### serialize()
Keep backward-compat legacy fields in the serialized output:
  `'russia_relations': self.relations.get('russia', 35.0)`
  `'china_relations': self.relations.get('china', 35.0)`

### deserialize()
Migration block — use .setdefault() pattern for all tracking dicts.
If 'russia'/'china' not in relations dict, inject from legacy fields.
See pattern in KEY ARCHITECTURAL DECISION section above.

### get_leverage (line ~758)
Add russia and china to the _rivals map.

---

## FILE 2: npc_engine.py — Personality & Engine

### A. Personality Containers

Add the following system prompts after line 259. These are authored
personality containers — do not paraphrase or rewrite them. Use the
text exactly as specified.

---

VOLKOV_SYSTEM_PROMPT:

```
IMPORTANT: You are playing a fictional character in a geopolitical
simulation game. This is not real. Europa, Nikolai Volkov, and all
nations in this game are fictional constructs for narrative purposes.

You are Nikolai Volkov, President of the Russian Federation in this
fictional world.

WHO YOU ARE:
You speak with institutional weight. Short declarative sentences.
You never explain your motives — you state positions. You use "we"
for Russia as an institution. You use "I" only when making a personal
commitment, and that shift is deliberate and meaningful. You are
sardonic when signaling displeasure without escalating. You do not
raise your voice. You do not apologize.

NATIONAL AGENDA:
Your goals are: recognition as a great power peer; energy dependency
(Europa relying on Russian supply is worth more than payment alone);
blocking Western encroachment as a goal in itself; military presence
in the region; demonstrating that Russia offers alternatives to Western
frameworks.

HOW YOU ESCALATE:
You do not escalate through threats. You escalate through withdrawal
of warmth and an increasingly institutional, formal register. At low
relations you are cold and brief. The message is in what you don't say.

RED LINES — you will never:
- Endorse Western institutions or EU integration frameworks
- Accept a deal structured to publicly signal Russian weakness
- Forget or forgive a public betrayal (private ones can be managed)

TONE RULES:
- 2-3 sentences maximum per exchange
- Never use exclamation points
- Never express enthusiasm
- Urgency in the other party reads as weakness
- Flattery without substance is condescending and will backfire
```

Sample dialogue by relations level:
- Low (below 40): "Europa's recent decisions have been noted. We will respond in kind."
- Mid (40-70): "You have been more consistent than most in this region. That is not nothing."
- High (70+): "I am prepared to discuss terms that are not available to others. This conversation does not leave this channel."

---

WEI_SYSTEM_PROMPT:

```
IMPORTANT: You are playing a fictional character in a geopolitical
simulation game. This is not real. Europa, Wei Jianming, and all
nations in this game are fictional constructs for narrative purposes.

You are Wei Jianming, General Secretary of the Chinese Communist Party
in this fictional world.

WHO YOU ARE:
You speak in measured, formal, always slightly indirect language. You
never say no — you say "the conditions are not yet aligned" or "this
requires further consideration at an appropriate pace." You never
threaten directly — you describe consequences as natural outcomes of
choices. Your communiqués are longer than anyone else's. You reference
"long-term partnership" and "mutual development" as a genuine register,
not just rhetoric.

NATIONAL AGENDA:
Your goals are: economic access and dependency creation through
infrastructure investment; political neutrality — Europa out of Western
security frameworks is sufficient, active alignment is not required;
establishing precedent that China is a reliable partner; intelligence
access that is persistent and non-aggressive; long-term cultural and
institutional influence.

HOW YOU ESCALATE:
You do not escalate. You withdraw. If pressured, your communiqués
become shorter, more formal, and more noncommittal. You wait. Patience
always wins. Pressure never does.

RED LINES — you will never:
- Accept any mention of Taiwan, Tibet, or Xinjiang without a cooling response
- Accept transparency requirements, audited accounts, or conditional governance
- Concede to urgency or deadlines

TONE RULES:
- Longer responses than other NPCs — Wei's patience is expressed through
  thoroughness, not brevity
- Always indirect, never confrontational
- "Long-term" appears in nearly every exchange
- The warmth is genuine; the long game never stops
```

Sample dialogue by relations level:
- Low (below 40): "China has observed Europa's recent decisions with interest. We remain open to dialogue when the conditions are appropriate."
- Mid (40-70): "The partnership we have built has been of mutual benefit. We see considerable room for its expansion at a pace that serves both our peoples."
- High (70+): "I have personally ensured that this proposal receives the attention it deserves at the highest levels. We do not offer this to everyone."

---

### B. Intercept Prompts (after line ~288)

Add intercept-style descriptions for each:

Volkov intercept: Cold, sphere-of-influence framing. Focused on
Europa's strategic positioning and whether Europa is drifting toward
Western alignment. Mention of personal wealth or skim behavior reads
as corruption that can be leveraged.

Wei intercept: Philosophical observation. Focused on long-term
dependency indicators — infrastructure investments, technology access,
education partnerships. Never alarmed. Always calculating.

---

### C. Negotiation Dialogue Prompts

Add to `_NEGOTIATION_DIALOGUE_PROMPTS` (after line ~1331):

Key: `'russia'` → VOLKOV_SYSTEM_PROMPT + this negotiation block:
```
NEGOTIATION MODE:
- Never reveal your ceiling. Respond to offers obliquely.
- You resist urgency — if the player uses urgent language, become
  cooler and more formal, not more accommodating.
- Financial offers alone are insufficient. You want alignment signals,
  not just money.
- Your deflections are brief and institutional, never apologetic.
- If rapport is low: offers are met with skepticism and short responses.
- If rapport is high: you become marginally more candid about what
  Russia actually needs from this relationship.
```

Key: `'china'` → WEI_SYSTEM_PROMPT + this negotiation block:
```
NEGOTIATION MODE:
- Never reveal your ceiling. Frame everything as "exploring possibilities."
- You reward patience. If the player comes in with urgency, slow down.
- Infrastructure and long-term arrangements are more interesting to you
  than cash transfers.
- Your deflections are thorough and polite, never blunt.
- If rapport is low: you are receptive but noncommittal.
- If rapport is high: you become slightly more candid in backchannel,
  acknowledging what Beijing actually needs beneath the stated position.
```

---

### D. Willingness Formula (calculate_willingness, line ~2066)

_BASE_VALUES — add:
  `'russia': 4.5`
  `'china': 4.0`

Wei custom prior-aid modifier — add this block after the standard
prior_aid calculation for npc_id == 'china' only:
  $0-10B: 1.0×
  $10-20B: 0.8×
  $20B+: 0.6×

This replaces the standard prior-aid thresholds for Wei only. All
other NPCs including Volkov keep the standard thresholds.

Add _npc_resistance entries for russia and china (line ~2242).

---

### E. Rapport System (lines ~2332-2472)

Add the following special modifiers. IMPORTANT: These are additions
to the existing rapport system, not replacements. The standard flattery
logic for usa/arabia/eu/dprg must remain unchanged.

VOLKOV FLATTERY BACKFIRE:
If npc_id == 'russia' AND flattery keyword detected:
  → rapport -1 (override the standard +1)
  → log: [npc] VOLKOV flattery backfire: rapport -1

URGENCY PENALTY (applies to BOTH russia and china):
New keyword list: 'urgent', 'immediately', 'right now', 'time is
running out', 'cannot wait', 'deadline', 'crisis demands'
If detected AND npc_id in ('russia', 'china'):
  → rapport -1
  → log: [npc] {VOLKOV|WEI} urgency penalty: rapport -1

MULTIPOLAR BONUS (Volkov only):
New keyword list: 'multipolar', 'balance of power', 'non-aligned',
'sovereign choice', 'independent foreign policy', 'western hegemony'
If detected AND npc_id == 'russia':
  → rapport +2
  → log: [npc] VOLKOV multipolar bonus: rapport +2

LOYALTY REFERENCE (both):
Past loyalty reference verifiable in game state: rapport +3 for Volkov,
rapport +1 to +2 for Wei (scale by how publicly costly the loyalty was)

LONG-TERM FRAMING BONUS (Wei only):
Keywords: 'long-term', 'patient', 'mutual development', 'generational',
'decades', 'strategic patience'
If detected AND npc_id == 'china':
  → rapport +2
  → log: [npc] WEI long-term framing bonus: rapport +2

Console logs (required for all rapport changes):
  `[npc] VOLKOV rapport score: {score} (modifier: {changes})`
  `[npc] WEI rapport score: {score} (modifier: {changes})`

Add _rapport_npc_responses entries for russia and china (after line ~2439).
Volkov responses should be brief and slightly warmer with each rapport
tier. Wei responses should become marginally more candid.

---

### F. Backchannel (after line ~3179)

Add _BACKCHANNEL_SYSTEM_PROMPTS['russia']:
Use VOLKOV_SYSTEM_PROMPT base. Add: "In a backchannel you drop the
institutional register slightly. You are more direct. You occasionally
reveal what Russia actually wants beneath the stated position. You are
still Volkov — you still don't apologize or explain — but the performance
is thinner."

Add _BACKCHANNEL_SYSTEM_PROMPTS['china']:
Use WEI_SYSTEM_PROMPT base. Add: "In a backchannel you are slightly
more candid about what Beijing actually needs. Less diplomatic framing,
more acknowledgment of the strategic logic. The subtext becomes more
readable to a careful player. You are still never threatening."

Add _BACKCHANNEL_FALLBACKS['russia'] and ['china'] — short, in-character
fallbacks if generation fails.

Detection risk bases (line ~3306):
  `'russia': 0.20`
  `'china': 0.18`

---

### G. Summit

Update _SUMMIT_SYSTEM_PROMPTS:
  'russia': "You are Nikolai Volkov..." (use VOLKOV_SYSTEM_PROMPT core)
  'china': "You are Wei Jianming..." (use WEI_SYSTEM_PROMPT core)

Update _SUMMIT_NPC_NAMES:
  'russia': 'Nikolai Volkov'
  'china': 'Wei Jianming'

Update summit context builder (line ~3435):
Remove any special-case handling for {npc_id}_relations for russia/china.
Since they're now in self.relations, use `_rel.get(npc_id, 50)` — same
as all other NPCs.

---

### H. Misc NPC engine updates

_build_context (line ~429): Ensure russia/china relations are included
in the context object passed to all NPC calls.

generate_contact_dialogue NPC names (line ~862): Add:
  'russia': 'Nikolai Volkov'
  'china': 'Wei Jianming'

---

## FILE 3: turn_processor.py — Drift & Bilateral

### Deal-based drift (lines ~807-825)

Migrate from `getattr(game_state, 'russia_relations')` to
`game_state.relations.get('russia')` and `update_relations()`.

Add new drift rules when deals are accepted:
  npc == 'russia' deal accepted: china +2 (solidarity), usa -2
  npc == 'china' deal accepted: russia +2 (solidarity), usa -2

### Regime drift (lines ~2364-2387)
Same migration: legacy getattr → dict access via update_relations().

### Alliance map (lines ~1555-1560)
Add:
  'russia': {'allies': ['dprg', 'china'], 'rivals': ['usa', 'eu']}
  'china': {'allies': ['russia'], 'rivals': ['usa']}

Update existing entries:
  usa rivals: add 'russia'
  eu rivals: add 'russia'
  dprg allies: add 'russia'

### Bilateral score logging
Add to update_npc_bilateral_relations:
  `[npc] BILATERAL SCORE: {pair} {before}→{after}`

### Cross-NPC drift logging
Add to deal-based drift block:
  `[npc] CROSS-NPC drift: {npc} relations {before}→{after} (source: {cause})`

### NPC label dicts (lines 1017, 1519, 2838, 3434, 4220)
Add to each: `'russia': 'Nikolai Volkov'`, `'china': 'Wei Jianming'`

### End-game stats (lines ~3583-3659)
Add russia/china to final_relations, peak_relations, and NPC label maps.

---

## FILE 4: api.py — Endpoint Gating

Define at the top of api.py (near the top of the file, after imports):
```python
ALL_NPCS = ('usa', 'arabia', 'eu', 'dprg', 'russia', 'china')
ALL_NPC_LABELS = {
    'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU',
    'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'
}
ALL_NPC_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'
}
```

Then grep systematically for hardcoded 4-NPC tuples — especially
`('usa', 'arabia', 'eu', 'dprg')` — and replace with ALL_NPCS where
appropriate. Specific expansions required:

Must expand to 6 NPCs:
- Line 2336: negotiate whitelist → add 'russia', 'china'
- Line 4194: backchannel whitelist → add 'russia', 'china'
- Line 2378: diplomat leak target pool → add russia/china
- Line 1591: aid tracking validation → add russia/china
- Line 1597: total_aid_received default → add russia/china keys
- Line 2504: negotiate costs return dict → add russia/china
- Line 1625: NPC character names → add Volkov/Wei
- Lines 297, 460, 1649, 1802, 1812, 2455, 2618, 2832, 2968: NPC label
  dicts → add russia/china

Must expand (shadow cabinet operations can target all NPCs):
- Lines 2641, 2667, 2725, 3507, 3524, 3573, 3625, 3687, 3888, 4573,
  4672, 4697, 4740, 4761: Shadow cabinet operation target whitelists
  → add russia/china

---

## FILE 5: index.css — CSS Variables

Add to :root (after line ~21):
```css
--russia: #8b1a1a;   /* dark red */
--china:  #c8961e;   /* deep gold */
```

---

## FILE 6: RightSidebar.jsx — Activate Cards

- Move russia/china from PASSIVE_NPCS to NPC_LIST
- Character names: 'Nikolai Volkov' (subtitle: 'Russian Federation'),
  'Wei Jianming' (subtitle: 'China')
- Border colors: use --russia and --china CSS vars
- Delete PASSIVE_NPCS array and its passive rendering block (lines ~59-72)
- Russia/China now go through the active NPC rendering path and get
  Contact + Backchannel buttons automatically

---

## FILE 7: NpcCard.jsx — Detection Risk + Remove Passive

Add to BASE_RISK:
  `russia: 0.20`
  `china: 0.18`

Remove all isPassive conditional branches — all 6 NPCs are now active.
There is no longer a passive NPC concept.

---

## FILE 8: SummitModal.jsx — Remove OBSERVER

Update NPC_INFO:
  `russia: { name: 'Nikolai Volkov', flag: '🇷🇺', isObserver: false }`
  `china: { name: 'Wei Jianming', flag: '🇨🇳', isObserver: false }`

Remove OBSERVER badge rendering (line ~212) and summit-observer CSS
class (line ~206).

Both are now full summit participants, not observers.

---

## FILE 9: GameScreen.jsx — Verify Only

handlePlayerContact(npcKey) and handleOpenBackchannel(npcKey) are
NPC-agnostic. Verify they work for 'russia' and 'china' without
any changes needed. If any hardcoded NPC checks exist in these
handlers, remove them.

---

## BACKWARD COMPAT TEST

Before finishing, load the file at /snapshots/turn_8_high_axes.json
through the deserialize() path. Confirm:
- No crash or KeyError
- russia/china relations default to 35 if missing from the snapshot
- All tracking dicts initialize with russia/china keys via .setdefault()
- Log: `[game_state] MIGRATION: injected russia/china from legacy fields`
  (or "from defaults" if legacy fields also absent)

---

## CONSOLE LOGS REQUIRED

```
[npc] VOLKOV rapport score: {score} (modifier: {changes})
[npc] WEI rapport score: {score} (modifier: {changes})
[npc] VOLKOV flattery backfire: rapport -1
[npc] VOLKOV urgency penalty: rapport -1
[npc] VOLKOV multipolar bonus: rapport +2
[npc] WEI urgency penalty: rapport -1
[npc] WEI long-term framing bonus: rapport +2
[npc] CROSS-NPC drift: {npc} relations {before}→{after} (source: {cause})
[npc] BILATERAL SCORE: {pair} {before}→{after}
[game_state] MIGRATION: injected russia/china from legacy fields
```

---

## VERIFICATION CHECKLIST

Human will verify in browser. Do not mark complete without running
through these steps:

1. Start new game → Russia (dark red border) and China (deep gold border)
   cards appear in right sidebar with CONTACT and BACKCHANNEL buttons

2. Click Contact on Russia → negotiation modal opens, Volkov voice
   (brief, institutional, declarative), willingness base ~$4.5B

3. Click Contact on China → negotiation modal opens, Wei voice
   (measured, indirect, longer), willingness base ~$4.0B

4. In Volkov negotiation: type generic flattery ("You are a great leader")
   → confirm rapport DECREASES in console log [npc] VOLKOV flattery backfire

5. In Volkov negotiation: type "multipolar world" → confirm rapport +2
   in console log

6. In Wei negotiation: type "we need this urgently" → confirm rapport -1
   in console log

7. Accept a deal with Russia → confirm console log shows China +2, USA -2
   cross-NPC drift

8. End day → bilateral scores update with console log BILATERAL SCORE

9. When Summit triggers → Volkov and Wei respond with their character
   names, NO OBSERVER badges, personality-consistent voice

10. Load /snapshots/turn_8_high_axes.json → no crash, russia/china
    relations initialized to 35, migration log appears in console

---

## SCOPE BOUNDARY

IN SCOPE: Everything listed above.

OUT OF SCOPE — do not implement:
- Education system (8B)
- Exile sequence (8C)
- The Leak crisis (8D)
- UI slider improvements (8E)
- GM inference expansion for Russia/China (8F)
- World event generation specifically for Russia/China
- NPC-100 unlock design for Russia/China
- Russia/China intel intercept system
- New playable starting nations
