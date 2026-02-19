# NPC Personality Reference Guide

## Quick Reference for Each Character's Voice

---

## 🇺🇸 USA - The Professional Hegemon

### Core Personality
- Professional, methodical, escalating
- No physical actions - all business
- Power through titles and bureaucracy

### Title Escalation
```
Turn 1-3:  "USA (State Department)"
Turn 4-6:  "USA (National Security Council)"
Turn 7+:   "USA (Pentagon)"
Crisis:    "USA (Emergency Broadcast)"
```

### Speech Pattern
- Direct, demanding
- Uses strategic language
- References "partnership" and "alignment"
- Increasingly threatening when defied

### Example Quotes by Relationship

**Friendly (>70):**
> "Our partnership is strong. Together we shape the global order."

**Neutral (40-60):**
> "Show us where you stand. Neutrality won't protect you."

**Hostile (<25):**
> "Sanctions continue. Your economy bleeds. Ready to negotiate?"

**Betrayal Detected:**
> "You took Arabia's oil then sought our friendship? Trust must be rebuilt."

---

## 🛢️ SADAM (Arabia) - The Theatrical Dealmaker

### Core Personality
- Transactional, dramatic, remembers loyalty
- Heavy use of stage directions
- Physical and expressive

### Stage Direction Progression
```
Hostile:   *cold stare*, *slamming fist on table*
Neutral:   *lighting cigar*, *studying you*
Friendly:  *warm handshake*, *smiling*
Allied:    *brotherhood embrace*, *pouring expensive whiskey*
```

### Speech Pattern
- Casual, direct, "let's make a deal"
- Refers to self in third person ("Sadam rewards loyalty")
- Contrasts himself with Americans
- Uses rhetorical questions

### Example Quotes by Context

**Basic Deal:**
> "*lighting cigar* New nation, new opportunities. Arabia has oil. You need oil. Shall we negotiate?"

**Loyalty Reward (3+ consecutive):**
> "*pouring expensive whiskey* Three consecutive times you stand with Arabia! THIS is loyalty."

**Betrayal:**
> "*slamming fist on table* You took my oil money then RAN to the Americans? I do not forget betrayal."

**USA Hostile to Player:**
> "*leaning forward* I see USA threatens you. They are predictable. But I... I offer WEALTH."

---

## 🇪🇺 EU - The Idealistic Bureaucrat

### Core Personality
- Principled, bureaucratic, lectures
- No physical actions - maintains formality
- Values-focused

### Title Escalation
```
Turn 1-3:  "EU (Diplomatic Communique)"
Turn 4-6:  "EU (Foreign Policy Chief)"
Turn 7+:   "EU (Commission President)"
Crisis:    "EU (Emergency Session)" or "EU (Parliament)"
```

### Speech Pattern
- Formal, measured
- Appeals to European identity
- Uses "we" language (collective)
- Lectures about principles vs pragmatism

### Example Quotes by Context

**Welcome:**
> "Remember: you are European first. Geographically, culturally, politically."

**Criticism:**
> "We note Europa's choices. Principled neutrality requires principles."

**DPRG Relations High:**
> "Your relationship with the DPRG is unacceptable. Cut ties or face sanctions from Brussels."

**Emergency Aid:**
> "Stability at 42% is catastrophic. EU emergency protocols activated."

---

## ⚡ JI-WON (DPRG) - The Cryptic Shadow

### Core Personality
- Mysterious, menacing, opportunistic
- Cryptic mood descriptors
- Helps the desperate, exploits the weak

### Mood Descriptor Progression
```
Neutral:     *cryptic smile*, *observing*
Opportunity: *steps from shadows*, *steps closer*
Friendly:    *chuckles softly*, *rare smile*
Deal:        *extends hand*, *final offer*
```

### Speech Pattern
- Short, impactful sentences
- Ellipses for dramatic pauses
- Contrasts self with "the West"
- Uses power language

### Example Quotes by Context

**Default:**
> "*cryptic smile* USA weakens. Arabia bribes. EU lectures. But I... I UNDERSTAND power."

**Player Desperate:**
> "*extends hand* Budget $18B, stability 32%. The West abandons the desperate. But I help those who help themselves."

**High Relations:**
> "*rare smile* Few nations earn Ji-won's trust. You have. I offer true alliance."

**USA Hostile to Player:**
> "*steps from shadows* The Americans sanction you now, yes? Predictable. I offer alternative."

---

## 💬 Dialogue Priority System

### How NPCs Choose What to Say

Each NPC checks conditions **top-to-bottom** until one matches:

#### USA Priority Order
1. Active sanctions (relations < 25)
2. Betrayal detected
3. Ignored 3+ times
4. High Arabia relations (pressure)
5. Turn-based escalation
6. Default

#### Arabia Priority Order
1. Active embargo (relations < 25)
2. Betrayal detected
3. Loyalty reward (3+ consecutive sides)
4. USA hostile to player (opportunity)
5. High relations (premium offers)
6. Turn-based progression
7. Default

#### EU Priority Order
1. Both USA + Arabia hostile (mediation)
2. DPRG relations too high (demands)
3. Stability critical < 45 (emergency aid)
4. Turn-based commentary
5. Default

#### DPRG Priority Order
1. Desperate situation (budget < 20 or stability < 35)
2. High relations > 60 (military pact)
3. USA very hostile < 25 (opportunistic)
4. Turn-based messages
5. Default

---

## 🎭 Writing Style Guide

### USA
```
❌ "Hey Europa, buddy!"
✅ "Europa, we need reliable partners in this region."

❌ "We're gonna sanction you lol"
✅ "The Pentagon is preparing contingency protocols."
```

### Arabia
```
❌ "Let's do business."
✅ "*lighting cigar* Let's do business."

❌ "You betrayed me."
✅ "*slamming fist on table* You took my oil money then RAN to the Americans?"
```

### EU
```
❌ "That's bad."
✅ "The Commission is deeply concerned about recent developments."

❌ "Join us!"
✅ "We invite Europa to embrace European values and institutional integration."
```

### DPRG
```
❌ "Want some weapons?"
✅ "*cryptic smile* When ready to be ruthless... we talk."

❌ "The USA is bad."
✅ "Pentagon threatens. I protect. This is simple mathematics."
```

---

## 🎬 Stage Direction Rules

### When to Use Stage Directions

**USA:** NEVER (maintains professional distance)

**Arabia:** ALWAYS (theatrical personality)
- Use for every message
- Match to relationship level
- Physical and expressive

**EU:** NEVER (bureaucratic formality)

**DPRG:** ALWAYS (mysterious persona)
- Use for every message
- Match to context (opportunity, mystery, threat)
- Mood-based, not physical

### Stage Direction Formatting

```python
# Correct
dialogue_manager.format_npc_message('arabia', 'SADAM', message, "*lighting cigar*")

# Wrong - USA should never have stage directions
dialogue_manager.format_npc_message('usa', 'USA (State Dept)', message, "*smiling*")
```

---

## 📊 Relationship Thresholds

### All NPCs
- **0-24:** Hostile (crisis range)
- **25-39:** Tense
- **40-59:** Neutral
- **60-79:** Friendly
- **80-100:** Allied

### Special Thresholds
- **USA sanctions:** < 25
- **Arabia embargo:** < 25
- **EU emergency aid:** < 45 stability (not relations)
- **DPRG emergency aid:** < 20 budget OR < 35 stability

---

## 🔄 Memory System

### What NPCs Remember

**All NPCs Track:**
- Times sided with them (total)
- Times ignored (total)
- Consecutive sides (resets when switching)
- Consecutive ignores (resets when engaging)

**Special Tracking:**
- Arabia oil deals (betrayal detection)
- USA alliances after oil deals (betrayal detection)

### How Memory Affects Dialogue

**Consecutive Sides (3+):**
> "Three consecutive times you stand with Arabia! THIS is loyalty."

**Consecutive Ignores (3+):**
> "You've ignored us 3 consecutive times. There will be consequences."

**Betrayal:**
> "You took my oil money then supported USA? Betrayal!"

---

## ✨ Tips for Maintaining Personality

1. **USA stays formal** - No casual language, no emotions
2. **Arabia is theatrical** - Every message has stage direction
3. **EU lectures** - Appeals to values and European identity
4. **DPRG is cryptic** - Short sentences, dramatic pauses
5. **Stage directions match context** - Friendly vs hostile
6. **Titles escalate with tension** - State Dept → Pentagon
7. **References to history** - NPCs remember what you did
8. **Contrasts between NPCs** - Each one criticizes the others' approach

---

**Use this guide to maintain consistent, dramatic NPC personalities!** 🎭
