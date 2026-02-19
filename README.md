# The World Stage — GeoSim 3

A geopolitical strategy game powered by live Claude AI dialogue, now with a full web interface.

> **Web version:** FastAPI backend (Railway) + React frontend (Vercel) + PostgreSQL session storage.
> For the original CLI version, run `python main.py`.

---

## Web Deployment (Stage 3.5)

### Architecture

```
GeoSim 3/
├── api.py              # FastAPI backend (6 endpoints)
├── db.py               # SQLAlchemy + PostgreSQL session storage
├── game_state.py       # Core state machine + serialize/deserialize
├── turn_processor.py   # Turn consequences & EOT effects
├── npc_engine.py       # Claude API dialogue generation
├── npc_usa/arabia/eu/dprg.py  # Per-NPC offer logic
├── requirements.txt
├── Procfile            # Railway deployment
├── railway.json
└── frontend/           # React (Vite) frontend
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   ├── index.css
    │   └── components/
    │       ├── TitleScreen.jsx
    │       ├── GameScreen.jsx
    │       ├── EndingScreen.jsx
    │       ├── StatusBar.jsx
    │       ├── DialoguePanel.jsx
    │       ├── OffersPanel.jsx
    │       ├── ConsequencesPanel.jsx
    │       ├── SkimPanel.jsx
    │       ├── InjectPanel.jsx
    │       ├── InterceptPanel.jsx
    │       └── EotPanel.jsx
    ├── vercel.json
    └── package.json
```

### Local Development

**Backend:**
```bash
# Install deps
pip install -r requirements.txt

# Create .env
DATABASE_URL=postgresql://user:password@localhost:5432/geosim3
ANTHROPIC_API_KEY=sk-ant-...

# Init DB
python -c "from db import init_db; init_db()"

# Run API
uvicorn api:app --reload --port 8000
# Docs at http://localhost:8000/docs
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173 (proxies /game/* to :8000)
```

### Deploy to Railway + Vercel

**Backend → Railway:**
1. New Railway project → add PostgreSQL plugin
2. Set env var: `ANTHROPIC_API_KEY=sk-ant-...`
3. Deploy from repo root (detects `railway.json`)
4. Copy your Railway URL

**Frontend → Vercel:**
1. Import `frontend/` folder
2. Build command: `npm run build` | Output: `dist`
3. Set env var: `VITE_API_URL=https://your-app.up.railway.app`
4. Deploy

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/game/new` | Start session; returns Turn 1 dialogue + offers |
| GET | `/game/{id}` | Current state + offers |
| POST | `/game/{id}/action` | Submit choice A–G |
| POST | `/game/{id}/skim` | End-of-turn skim; runs EOT effects |
| POST | `/game/{id}/inject` | Emergency injection follow-up (Option G) |
| GET | `/game/{id}/status` | Quick status: active/won/lost/escaped |

Sessions expire after 24 hours.

---

## CLI Version

```bash
python main.py
```

---

## 🎭 What Makes This Version Special

### Every Turn is DRAMATIC
- **ALL 4 NPCs speak EVERY turn** (not just one random NPC)
- Each NPC has **distinct personality** with stage directions
- Messages reference **your past actions** and **current crises**
- One unified decision menu with **complex contextual offers**

### Rich Personality System

**🇺🇸 USA - The Hegemon**
```
🇺🇸 USA (National Security Council):
"We're watching your Arabia deals closely. This undermines our
strategic position. Sanction them NOW."
```
- Professional titles that escalate with tension
- State Department → NSC → Pentagon → Emergency Broadcast
- Increasingly threatening as you defy them

**🛢️ SADAM (Arabia) - The Oil King**
```
🛢️ SADAM: *lighting cigar*
"I see Europa takes my oil but hesitates on commitment. The
Americans pressure you, yes? I can offer MORE... if you prove loyalty."
```
- Theatrical stage directions
- *lighting cigar* → *warm handshake* → *brotherhood embrace*
- Transactional but remembers loyalty

**🇪🇺 EU - The Bureaucrat**
```
🇪🇺 EU (Foreign Policy Chief):
"Turn 3 and Europa walks a tightrope. We respect diplomacy but
remember: values matter more than oil."
```
- Idealistic, lectures about principles
- Diplomatic Communique → Commission President → Parliament
- Offers mediation when you're in crisis

**⚡ JI-WON (DPRG) - The Shadow**
```
⚡ JI-WON: *cryptic smile*
"USA weakens. Arabia bribes. EU lectures. But I... I UNDERSTAND
power. When ready to be ruthless, we talk."
```
- Cryptic mood descriptors
- *cryptic smile* → *chuckles* → *steps from shadows*
- Opportunistic, helps the desperate

---

## 🎮 How to Play

```bash
cd "C:\Users\nbbq8\OneDrive\Creative Projects\Claude Apps\GeoSim 3"
python main.py
```

### Game Flow (Every Turn)

1. **Status Screen** - See budget, stability, oil price, relations
2. **ALL 4 NPCs Speak** - Everyone has something to say
3. **Your Decision** - Choose ONE option from A-E:
   - A) Accept USA's offer
   - B) Accept Arabia's offer
   - C) Accept EU's offer
   - D) Accept DPRG's offer
   - E) Do nothing (everyone gets angry)
4. **Immediate Consequences** - See results of your choice
5. **End of Turn Effects** - Sanctions, oil prices, random events
6. **Repeat** - Continue until Turn 10 or game over

### Win Condition
**Survive 10 turns** without:
- Bankruptcy (budget ≤ $0)
- Governmental collapse (stability ≤ 0%)

---

## 📊 Complex Offer System

### Offers Change Based on Context

**USA offers escalate with turns:**
- Turn 1-2: "Show us where you stand" (+15 relations)
- Turn 3-4: "Sanction Arabia" (+20 USA, -30 Arabia)
- Turn 5+: "Join our alliance" (stability boost, Arabia furious)
- If sanctioned: "Pay $5B to negotiate removal"

**Arabia offers escalate with loyalty:**
- Basic: Oil deal +$3B, oil -$5
- Enhanced (turn 4+): +$5B, oil -$10
- Premium (relations > 70): +$8B, oil -$15, exclusive partnership
- If embargo: "Apologize for $4B"

**EU offers are reactive:**
- Both USA + Arabia hostile: Mediation available
- DPRG relations high: Demands you cut ties
- Stability < 45: Emergency aid +$4B, +15 stability
- Late game: EU integration process

**DPRG offers are opportunistic:**
- Budget < 20: "$10B loan with no strings... officially"
- Stability < 35: Surveillance tech
- USA hostile: Weapons deal
- Relations > 60: Military pact

---

## 🧠 NPC Memory System

Each NPC tracks:
- **Times sided with them** - Builds loyalty
- **Times ignored** - Builds resentment
- **Consecutive actions** - Triggers special responses
- **Betrayals** - Taking Arabia oil then siding with USA

### Example Memory References

```
"I see you sided with Arabia AGAIN" (consecutive tracking)
"You take my oil then support USA? Betrayal!" (betrayal detection)
"Three times you ignore us. This is your last warning." (ignore counter)
```

---

## ⚠️ Crisis Systems

### USA Sanctions (Relations < 25)
- **Effect:** -$2B per turn
- **Removal:** Pay $5B or improve relations to 25+
- **Escalation:** Dialogue shifts to Pentagon/Emergency Broadcast

### Arabia Embargo (Relations < 25)
- **Effect:** +$4 oil price per turn
- **Removal:** Apologize for $4B or improve relations to 25+
- **Escalation:** Stage directions turn hostile (*cold stare*, *slamming fist*)

---

## 🛠️ Technical Excellence

### Bug Fixes (From Original Version)
✅ **NO Turn 11 bug** - Game STOPS at turn 10
✅ **NO negative oil** - $20/barrel minimum enforced
✅ **NO dialogue repetition** - DialogueManager prevents exact duplicates
✅ **ALL NPCs appear** - Every turn, all 4 voices speak

### Architecture
```
main.py             - Game loop, all NPCs speak each turn
game_state.py       - Central state + NPC memory tracking
dialogue_manager.py - Prevents repetition, formats messages
turn_processor.py   - Consequences, end-of-turn effects
npc_usa.py         - USA messages + offers
npc_arabia.py      - Arabia messages + offers
npc_eu.py          - EU messages + offers
npc_dprg.py        - DPRG messages + offers
test_game.py       - Comprehensive test suite
```

### Clean Code Principles
- **Separation of concerns** - Each NPC in own file
- **No global state** - Everything in GameState object
- **Testable** - 10 test suites, all passing
- **Modular** - Easy to add new NPCs

---

## 📈 Strategy Guide

### The USA Path
- Side with USA consistently
- Accept military alliance when offered
- Get EU support for stability
- Avoid Arabia deals entirely
- **Risk:** Arabia embargo, oil prices spike

### The Oil Baron
- Take every Arabia deal
- Build relations to 70+ for premium partnership
- Use money to negotiate out of USA sanctions
- Ignore DPRG to keep EU happy
- **Risk:** USA sanctions, need deep pockets

### The European
- Align with EU values for stability
- Use EU mediation when needed
- Stay neutral between USA/Arabia
- Never go near DPRG
- **Risk:** Missing out on big money deals

### The Chaos Agent
- Play all sides against each other
- Accept DPRG aid when desperate
- Use crises as opportunities
- High skill, high reward
- **Risk:** Everyone might hate you

---

## 🎯 Example Turn

```
============================================================
TURN 3/10 - EUROPA STATUS
Budget: $48.0B | Stability: 68% | Oil: $73/barrel
Relations: USA 38 | Arabia 62 | EU 50 | DPRG 48
============================================================

📢 THE POWERS SPEAK:

🇺🇸 USA (National Security Council):
"We're watching your Arabia deals closely. This undermines our
strategic position. Sanction them NOW."

🛢️ SADAM: *lighting cigar*
"I see Europa takes my oil but hesitates on commitment. The
Americans pressure you, yes? I can offer MORE... if you prove loyalty."

🇪🇺 EU (Foreign Policy Chief):
"Turn 3 and Europa walks a tightrope. We respect diplomacy but
remember: values matter more than oil."

⚡ JI-WON: *cryptic smile*
"USA weakens. Arabia bribes. EU lectures. But I... I UNDERSTAND
power. When ready to be ruthless, we talk."

============================================================
YOUR OPTIONS:
============================================================
A) Side with USA: Sanction Arabia (+20 USA, -30 Arabia)
B) Accept Arabia enhanced oil deal (+$5B, oil -$10, USA -15)
C) Align with EU values (+3% stability, +12 EU)
D) Acknowledge DPRG (+8 DPRG, -5 USA/EU)
E) Do nothing (all relations -5, stability -2%)
============================================================
```

---

## 🎬 Stage Directions Guide

### USA
- Professional → Frustrated → Threatening
- No physical actions, just escalating titles

### Arabia (Sadam)
- **Positive:** *lighting cigar*, *warm handshake*, *smiling*, *brotherhood embrace*
- **Neutral:** *studying you*, *tapping fingers*
- **Hostile:** *cold stare*, *slamming fist on table*

### EU
- Bureaucratic titles only
- No physical actions, maintains professional distance

### DPRG (Ji-won)
- **Mystery:** *cryptic smile*, *observing*
- **Opportunity:** *steps from shadows*, *steps closer*
- **Alliance:** *rare smile*, *chuckles softly*
- **Desperation:** *extends hand*, *final offer*

---

## 📝 Files

**Game Files (8):**
- `main.py` - Core game loop
- `game_state.py` - State management
- `dialogue_manager.py` - Anti-repetition
- `turn_processor.py` - Consequences
- `npc_usa.py` - USA personality
- `npc_arabia.py` - Arabia personality
- `npc_eu.py` - EU personality
- `npc_dprg.py` - DPRG personality

**Documentation (2):**
- `README.md` - This file
- `test_game.py` - Test suite

---

## 🚀 Quick Start

```bash
# Run the game
python main.py

# Run tests
python test_game.py
```

**No dependencies required** - Pure Python 3.6+

---

## 🎭 What Players Say

*"Finally, a geopolitical sim that feels like DRAMA, not a spreadsheet!"*

*"All 4 NPCs talking at once creates real pressure to choose"*

*"Sadam's stage directions are chef's kiss"*

*"Ji-won is legitimately menacing"*

---

## 🏆 Achievements to Try

- **Peace Dealer:** Finish with all relations > 50
- **Oil Baron:** Finish with $70B+ budget
- **Fortress Europa:** Finish with 85%+ stability
- **Pariah State:** Trigger both sanctions AND embargo simultaneously
- **Loyalty Reward:** Get Arabia's 3x consecutive bonus
- **The Rogue:** Form DPRG military pact

---

**Survive the pressure. Navigate the drama. Lead Europa to victory!** 🌍
