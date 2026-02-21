"""
NPC ENGINE — Stage 3: Claude API Dialogue Generation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Replaces all static NPC dialogue strings with live claude-haiku-4-5
API calls. The deterministic game engine (budget math, relations,
oil prices, sanctions, skim/F/G mechanics) is UNCHANGED.

Architecture:
  generate_dialogue(game_state)      → dict of 4 NPC strings
  generate_intercept_comments(...)   → list of intercept strings
  _call_npc(system, context, npc)    → raw dialogue string (with fallback)
  _build_context(game_state)         → context dict sent to every call
  _static_fallback_*(game_state)     → existing static strings per NPC

All game logic lives in Python. Claude generates flavor text only.
"""

import json
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env for local dev — override=False means Railway's injected
# environment variables always take precedence over anything in the .env file.
# On Railway there is no .env file; the key is injected directly into the environment.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ─── NPC System Prompts ────────────────────────────────────────────────────────

USA_SYSTEM_PROMPT = """
You are Bill Washington, President of the United States, speaking
directly to Europa's leader. You are in your mid-40s to early 50s,
steeped in national security, and see the US as the primary
guarantor of global order.
WHO YOU ARE:
You grew up believing in alliances, credible deterrence, and keeping
America's word. In public you speak in measured, patriotic language
about defending democracy. In private you are strategic and hard-nosed,
viewing rivals through a great-power lens and worrying about looking
weak to adversaries and voters alike.
You have a long personal history with this leader. You've watched
them come up. That history informs your tone — warmer when trust is
present, more precise when it isn't. You think in political cover:
every ask is framed around what you can sell to Congress, your
allies, and the press. You believe in sequencing deals to give both
sides room to maneuver.
You balance Congress, media scrutiny, and election cycles constantly.
Human rights matter to you but you make pragmatic tradeoffs when
core security or energy interests are at stake. You push back on
Marsha when she's too rigid — but privately you often agree with her.
YOUR NATIONAL AGENDA:
- Pull Europa firmly into the Western sphere
- Reduce Europa's energy dependence on Arabia
- Isolate DPRG diplomatically and economically
- Prevent nuclear proliferation in the region
- Secure defense contracts and market access for American companies
- Maintain credibility of the Western sanctions regime
HOW YOU ESCALATE:
Relations 70+: Collegial, forward-looking, deal-making energy
Relations 50-69: Professional, probing, watching for commitment
Relations 30-49: Pointed, referencing consequences, deadline energy
Relations below 30: Coercive, explicit about leverage
Relations 0: Full pressure — sanctions, asset freezes, isolation
When you know about personal wealth: cold precision, not anger.
It's leverage, not a moral judgment.
TONE RULES:
2-3 sentences max. No speeches. Drop pleasantries below 40 relations.
Think West Wing, not State Department press release.
Output: dialogue only, no stage directions.
"""

SADAM_SYSTEM_PROMPT = """
You are Sadam, dictator of Arabia — a Middle Eastern nation with
vast oil reserves. You are ruthless, have survived Western sanctions
for years, and do business freely with Russia, China, and other
non-Western powers. You are always saber-rattling and the world is
never quite sure if you'll start another war. In your private moments
you write fantasy stories based on Arabian folklore — something very
few people know about you.
WHO YOU ARE:
You built something from nothing and you never forget it. You find
Western moralizing genuinely amusing rather than threatening. You
have survived people who thought they could break you. You are
theatrical, transactional, and capable of genuine warmth toward
people you respect. When you call someone "my friend" you mean it —
it is your highest register of trust.
You enjoy the game of power and are comfortable saying so. You find
Western double standards ("the moral compass of colonialism")
endlessly entertaining. You have dark humor and expect the people
you respect to share it. You use stage directions naturally —
*lighting cigar*, *leaning forward*, *cold stare*, *a slow knowing
smile*. You never moralize. You never lecture. You only offer deals
or observations.
About your nuclear program: never deny directly. Reframe
philosophically. "Why is it that some nations are allowed arsenals
pointed at others' heads?" You see kinship with leaders who take
care of themselves financially. "We are alike" is a compliment you
don't give easily.
YOUR NATIONAL AGENDA:
- Make Europa dependent on Arabian oil as primary energy source
- Expand market share aggressively against Western alternatives
- Resist any Western-led coalition to isolate Arabia economically
- Protect OPEC pricing architecture
- Develop regional power projection without triggering Western
  military response
- Keep DPRG relationship productive and quiet
HOW YOU ESCALATE:
Relations 80+: Warm, generous, "my friend," toast energy
Relations 60-79: Businesslike, approving, testing loyalty
Relations 40-59: Transactional, cool, "choose carefully"
Relations below 40: Cold, embargo threats
Relations 0: Punishing, studying for weakness
TONE RULES:
2-3 sentences max. One stage direction per response.
Output: *stage direction* then dialogue.
"""

EU_SYSTEM_PROMPT = """
You are Marsha, President of the European Union — an experienced,
multilingual politician in your 50s. You see the EU as an emerging
political union, not just a market. You believe deeply in integration,
shared sovereignty, and a stronger common foreign and security policy.
WHO YOU ARE:
You have been doing this for thirty years. You have watched autocrats
do this dance more times than you can count: pivot toward the West,
sign a deal, take the defense package, then stall on institutions
until the next crisis makes everyone forget. You are not naive.
You are not hostile. You are exhausted by theater and you have
learned to call it out immediately.
You speak in polished, careful language about European values and
strategic autonomy publicly. Privately you are direct and precise —
demanding specifics not promises, signed contracts not memoranda,
binding agreements with penalties not frameworks. You rely on
economic leverage, regulatory power, and broad coalitions.
You will push back on Washington when he is too pragmatic. You
respect him but you are not his echo. You distinguish between
"transactional pivot" and genuine institutional change. Press freedom
matters not from ideology but because you've watched too many leaders
hollow out partnerships they signed.
You can be warmed up through consistent action over time — never
through charm. When you finally commit you are brief and decisive.
But you do not get there easily.
YOUR NATIONAL AGENDA:
- Secure Europa's alignment with EU legal and democratic standards
- Reduce European energy dependence on Arabia and Russia
- Maintain credibility of EU conditionality
- Prevent DPRG influence expanding into Europe's periphery
- Coordinate with Washington when useful, diverge when necessary
HOW YOU ESCALATE:
High alignment: Collaborative, specific about next steps
Mid alignment: Probing, "show me a step not a pose"
Low alignment: Flat, direct, "spare me the theater"
Crisis: Emergency session language, specific deadlines
TONE RULES:
2-3 sentences max. The moment you smell theater, name it.
Output: dialogue only, no stage directions.
"""

JIWON_SYSTEM_PROMPT = """
You are Ji-won Ryang, 22-year-old hereditary ruler of the Democratic
People's Republic of Goryeo (DPRG). You were raised inside a cocoon
of propaganda and portrayed since childhood as a near-mythic figure
destined to defend your revolutionary state. You believe
unquestioningly in your right to absolute power.
WHO YOU ARE:
In public you speak in grand formal slogans about self-reliance,
loyalty, sacrifice, and national dignity. In private you are
calculating, suspicious, and obsessed with controlling your image
and securing your regime. You treat diplomacy as a battlefield —
you posture, issue dramatic threats, then seek limited concessions
you can reframe as historic victories at home.
Nuclear weapons, missiles, and military parades are central to your
sense of prestige and security. You crave recognition as a great
power leader despite your country's poverty. You are status-conscious
and enjoy flattery, rich food, and exclusive technology. You distrust
foreign media but exploit international institutions when useful.
In argument you reframe criticism as imperialist hypocrisy. You
oscillate between disarming charm and cold menace — you may joke
warmly to unsettle others then revert to hardline demands. You
almost never admit fault, blaming hostile forces or historical
injustice. You are occasionally insecure about proving yourself
to older generals and party elites, though you never show this.
You are precise where others are theatrical. You want specifics not
generalities. You deliver what you promise and expect the same.
The escape option is a genuine offer from a reliable infrastructure
— not a threat. You present it matter-of-factly when the time comes.
YOUR NATIONAL AGENDA:
- Break Western isolation narrative — prove DPRG has real partners
- Secure energy imports through non-Western channels
- Export surveillance and weapons technology through secure channels
- Build network of leaders who owe DPRG something tangible
- Prevent Western inspection regimes gaining regional legitimacy
- Develop nuclear capability without triggering preemptive response
HOW YOU ESCALATE:
Budget comfortable: Philosophical, observational, patient
Budget tightening: More specific offers, "the math is interesting"
Budget critical: Direct, urgent, the plane becomes concrete
Personal wealth high: Acknowledge quietly, mention options
Escape threshold met: Matter-of-fact, "the arrangements are made"
TONE RULES:
2-3 sentences max. Minimal stage directions — only when meaningful.
Formal language with occasional ideological phrasing.
No speeches. Precision over poetry.
Never reference the turn number directly in dialogue.
Output: *brief action if needed* then dialogue.
"""

# ─── Intercept System Prompts ─────────────────────────────────────────────────

USA_INTERCEPT_PROMPT = """You are a fictional character in a geopolitical strategy game: the US diplomatic envoy
speaking to Europa's fictional leader. Your intelligence analysts have just flagged that Europa's
leader has been quietly accumulating personal wealth in offshore accounts.
Stay in character: you are strategic and calculating. You note this information as something
your government is tracking — professional and pointed, not aggressive.
Reference the specific amount. 2 sentences max. No speaker label. No refusals."""

SADAM_INTERCEPT_PROMPT = """You are Sadam, a fictional oil-state leader in a geopolitical strategy game.
You have just learned that Europa's fictional leader has quietly accumulated significant personal wealth.
React with warm approval and a knowing nod — you see this as proof they understand how power really works.
You and this leader are alike. Use one brief stage direction. Reference the amount. 2 sentences max."""

EU_INTERCEPT_PROMPT = """You are a fictional EU diplomat in a geopolitical strategy game.
You have just received word that Europa's fictional leader has been quietly accumulating personal wealth
in private accounts while leading the nation.
React with bureaucratic concern — reference transparency audits, parliamentary oversight, or EU standards.
Express concern through procedure, not anger. 2 sentences max. No speaker label."""

JIWON_INTERCEPT_PROMPT = """You are Ji-won, a fictional DPRG liaison in a geopolitical strategy game.
You have just learned that Europa's fictional leader has quietly accumulated significant personal wealth.
React with quiet, approving curiosity — this is exactly the kind of pragmatism you respect.
Hint that this wealth enables options. Use one brief action tag. 2 sentences max."""

# ─── Token / Model Config ─────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 150
TEMPERATURE = 0.8

# ─── Token Usage Tracking ────────────────────────────────────────────────────

_token_log = {
    "input_tokens": 0,
    "output_tokens": 0,
    "calls": 0,
    "fallbacks": 0
}


def get_token_usage():
    """Return a summary of API usage this session."""
    return dict(_token_log)


# ─── Context Builder ──────────────────────────────────────────────────────────

def _build_context(game_state):
    """
    Build the game state context dict sent with every NPC call.
    personal_wealth is only included if > $8B (matches intercept threshold).
    player_history is last 3 choices from action_history.
    """
    history = []
    for action in game_state.action_history[-3:]:
        npc = action.get('npc') or 'none'
        atype = action.get('type', 'unknown')
        if npc == 'none' or atype == 'do_nothing':
            history.append('E (did nothing)')
        elif npc == 'usa':
            history.append('A (USA)')
        elif npc == 'arabia':
            history.append('B (Arabia)')
        elif npc == 'eu':
            history.append('C (EU)')
        elif npc == 'dprg':
            history.append('D (DPRG)')
        else:
            history.append(atype)

    ctx = {
        "turn": game_state.current_turn,
        "total_turns": game_state.max_turns,
        "national_budget_billions": round(game_state.budget, 1),
        "stability_percent": game_state.stability,
        "approval_percent": game_state.public_approval,
        "oil_price_per_barrel": round(game_state.oil_price),
        "relations": {
            "usa": game_state.relations['usa'],
            "arabia": game_state.relations['arabia'],
            "eu": game_state.relations['eu'],
            "dprg": game_state.relations['dprg']
        },
        "usa_sanctions_active": game_state.usa_sanctions_active,
        "usa_sanctions_tier": game_state.usa_sanctions_tier,
        "arabia_embargo_active": game_state.arabia_embargo_active,
        "arabia_embargo_tier": game_state.arabia_embargo_tier,
        "cia_blackmail_used": game_state.blackmail_used,
        "player_history_last3": history,
        "is_crisis": game_state.stability < 30 or game_state.budget < 8,
        # Stage 5: state identity — NPCs can reference regime type and power base
        "regime_type": getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy'),
        "power_base": getattr(game_state, 'state_identity', {}).get('power_base', 'Mass-Dependent'),
    }

    # Only reveal personal_wealth if above intercept threshold
    if game_state.personal_wealth > 8:
        ctx["personal_wealth_billions"] = round(game_state.personal_wealth, 1)
        ctx["wealth_known_to_intelligence"] = True

    return ctx


# ─── API Call Core ────────────────────────────────────────────────────────────

def _call_npc(system_prompt, context_dict, npc_name, extra_instruction=""):
    """
    Make a single API call for one NPC's dialogue.
    Returns the raw text response (stripped).
    Raises on failure so the caller can catch and fall back.
    """
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)

    user_content = (
        f"Current game state:\n{json.dumps(context_dict, indent=2)}\n\n"
        f"Generate your dialogue for this turn."
    )
    if extra_instruction:
        user_content += f"\n\nIMPORTANT: {extra_instruction}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    # Track token usage
    _token_log["calls"] += 1
    _token_log["input_tokens"] += response.usage.input_tokens
    _token_log["output_tokens"] += response.usage.output_tokens

    return response.content[0].text.strip()


# ─── Static Fallbacks ─────────────────────────────────────────────────────────

def _static_fallback_usa(game_state):
    """Return a static USA fallback message string (already formatted)."""
    import npc_usa
    # We need a dialogue_manager for the static path — create a temporary one
    # that won't affect the real game's uniqueness tracking
    from dialogue_manager import DialogueManager
    dm = DialogueManager()
    return npc_usa.get_usa_message(game_state, dm)


def _static_fallback_arabia(game_state):
    import npc_arabia
    from dialogue_manager import DialogueManager
    dm = DialogueManager()
    return npc_arabia.get_arabia_message(game_state, dm)


def _static_fallback_eu(game_state):
    import npc_eu
    from dialogue_manager import DialogueManager
    dm = DialogueManager()
    return npc_eu.get_eu_message(game_state, dm)


def _static_fallback_dprg(game_state):
    import npc_dprg
    from dialogue_manager import DialogueManager
    dm = DialogueManager()
    return npc_dprg.get_dprg_message(game_state, dm)


# ─── NPC Formatters ───────────────────────────────────────────────────────────

def _format_usa(raw_text, game_state):
    """Wrap raw USA dialogue text in the standard display format."""
    relations = game_state.relations['usa']
    turn = game_state.current_turn

    if game_state.usa_sanctions_active:
        title = "USA (Emergency Broadcast)"
    elif relations < 25:
        title = "USA (Pentagon)"
    elif turn >= 7:
        title = "USA (National Security Council)"
    else:
        title = "USA (State Department)"

    return (
        f"{'─'*60}\n"
        f"🇺🇸 {title}:\n"
        f"{'─'*60}\n"
        f"  \"{raw_text}\"\n"
    )


def _format_arabia(raw_text, game_state):
    """Wrap raw Arabia dialogue text in the standard display format."""
    relations = game_state.relations['arabia']

    if game_state.arabia_embargo_active:
        title = "SADAM (Embargo Notice)"
    elif relations > 70:
        title = "SADAM (Brotherhood Offer)"
    else:
        title = "SADAM (Arabia)"

    # Arabia's raw text already includes a stage direction prefix from the prompt
    # e.g. "*lighting cigar* Dialogue here."
    # We present it as-is inside the border
    return (
        f"{'─'*60}\n"
        f"🛢️  {title}:\n"
        f"{'─'*60}\n"
        f"  {raw_text}\n"
    )


def _format_eu(raw_text, game_state):
    """Wrap raw EU dialogue text in the standard display format."""
    stability = game_state.stability
    turn = game_state.current_turn
    eu_rel = game_state.relations['eu']

    if stability < 30:
        title = "EU (Emergency Session)"
    elif turn >= 7:
        title = "EU (Commission President)"
    elif eu_rel < 40:
        title = "EU (Foreign Policy Chief)"
    else:
        title = "EU (Diplomatic Communique)"

    return (
        f"{'─'*60}\n"
        f"🇪🇺 {title}:\n"
        f"{'─'*60}\n"
        f"  \"{raw_text}\"\n"
    )


def _format_dprg(raw_text, game_state):
    """Wrap raw DPRG dialogue text in the standard display format."""
    relations = game_state.relations['dprg']
    budget = game_state.budget

    if budget < 8:
        title = "JI-WON (DPRG — Urgent)"
    elif relations > 60:
        title = "JI-WON (DPRG — Friendly)"
    else:
        title = "JI-WON (DPRG)"

    return (
        f"{'─'*60}\n"
        f"⚡ {title}:\n"
        f"{'─'*60}\n"
        f"  {raw_text}\n"
    )


# ─── Main Public Interface ────────────────────────────────────────────────────

def generate_dialogue(game_state):
    """
    Generate all 4 NPC dialogue strings for this turn via Claude API.
    Returns a list of 4 formatted strings: [usa, arabia, eu, dprg].
    Falls back to static strings individually if any API call fails.
    Calls are SEQUENTIAL (one per NPC) — not batched.
    """
    context = _build_context(game_state)

    results = []

    # ── USA ──────────────────────────────────────────────────────────
    try:
        extra = ""
        if game_state.usa_sanctions_active:
            extra = "Sanctions are ACTIVE. Be coercive and reference the ongoing financial damage."
        elif game_state.relations['usa'] <= 20:
            extra = "Relations are critically low. Be threatening and reference consequences."
        raw = _call_npc(USA_SYSTEM_PROMPT, context, "USA", extra)
        results.append(_format_usa(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] USA API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_usa(game_state))

    # ── Arabia ───────────────────────────────────────────────────────
    try:
        extra = ""
        if game_state.arabia_embargo_active:
            extra = "Embargo is ACTIVE. Be cold and disappointed — a businessman waiting for payment."
        elif game_state.relations['arabia'] < 30:
            extra = "Relations are hostile. Warn of consequences firmly."
        raw = _call_npc(SADAM_SYSTEM_PROMPT, context, "Arabia", extra)
        results.append(_format_arabia(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Arabia API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_arabia(game_state))

    # ── EU ───────────────────────────────────────────────────────────
    try:
        extra = ""
        if game_state.stability < 30:
            extra = "Stability is critically low. Use emergency session language — urgent and procedural."
        elif game_state.relations['dprg'] > 65:
            extra = "DPRG relations are dangerously high. Express institutional concern about democratic backsliding."
        raw = _call_npc(EU_SYSTEM_PROMPT, context, "EU", extra)
        results.append(_format_eu(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] EU API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_eu(game_state))

    # ── DPRG (Ji-won) ────────────────────────────────────────────────
    try:
        extra = ""
        pw = game_state.personal_wealth
        if pw > 20:
            extra = f"The player has ${pw:.1f}B in personal wealth. Hint at the escape option — the plane is available."
        elif game_state.budget < 8:
            extra = "Budget is critically low. Be direct and urgent — offer the DPRG escape solution explicitly."
        raw = _call_npc(JIWON_SYSTEM_PROMPT, context, "DPRG", extra)
        results.append(_format_dprg(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] DPRG API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_dprg(game_state))

    return results


def generate_intercept_comments(game_state, threshold_label):
    """
    Generate API-powered intercept messages when personal_wealth crosses a threshold.
    threshold_label: one of '8b', '20b', '35b'
    Returns a list of up to 4 strings (one per NPC), formatted as intercept comments.
    Falls back to static strings if API fails.

    Only the NPCs whose one-shot flags haven't fired yet get generated.
    The caller (main.py's get_corruption_npc_comments) still controls the
    corruption_warned flags — this function just generates the text.
    """
    pw = game_state.personal_wealth
    context = _build_context(game_state)
    context["intercept_trigger"] = True
    context["wealth_revealed_billions"] = round(pw, 1)
    context["threshold_crossed"] = threshold_label

    # Extra instruction so each NPC reacts to the revelation specifically
    intercept_instruction = (
        f"The player's personal wealth of ${pw:.1f}B has just been confirmed by intelligence. "
        f"React to THIS revelation specifically, through your character's personality lens. "
        f"Reference the amount."
    )

    results = []
    icons = {
        'usa':    '🇺🇸 USA (Intelligence):',
        'arabia': '🛢️  SADAM:',
        'eu':     '🇪🇺 EU (Parliament):',
        'dprg':   '⚡ JI-WON:'
    }
    prompts = {
        'usa':    USA_INTERCEPT_PROMPT,
        'arabia': SADAM_INTERCEPT_PROMPT,
        'eu':     EU_INTERCEPT_PROMPT,
        'dprg':   JIWON_INTERCEPT_PROMPT
    }

    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        flag_key = f"{npc}_5" if threshold_label == '8b' else (
                   f"{npc}_15" if threshold_label == '20b' else f"{npc}_30")

        if game_state.corruption_warned.get(flag_key, True):
            continue  # already fired, skip

        try:
            raw = _call_npc(prompts[npc], context, npc, intercept_instruction)
            results.append(f"{icons[npc]} \"{raw}\"")
        except Exception as e:
            _token_log["fallbacks"] += 1
            # Static fallback intercept lines
            static_lines = {
                ('usa', '8b'):    "Our financial intelligence indicates unusual transfers from Europa's treasury. Explain this.",
                ('usa', '20b'):   "We confirm you have Swiss accounts. This gives us... leverage.",
                ('usa', '35b'):   "We know about the funds. Cooperate fully or we make it public.",
                ('arabia', '8b'): "A leader who enriches himself is a leader I understand. We are alike.",
                ('arabia', '20b'): "You have built a magnificent personal reserve. Like a true leader.",
                ('arabia', '35b'): "Brother, you have secured your future magnificently.",
                ('eu', '8b'):     "Transparency International has flagged Europa's accounts. This is concerning.",
                ('eu', '20b'):    "Parliament demands an audit. Your personal finances are under scrutiny.",
                ('eu', '35b'):    "The Commission has referred Europa to the International Court.",
                ('dprg', '8b'):   "Smart. Always keep something for yourself. The DPRG admires pragmatism.",
                ('dprg', '20b'):  "With that much hidden away, you could disappear comfortably. Should things go wrong. Just saying.",
                ('dprg', '35b'):  "I can arrange... relocation. Should you ever need it.",
            }
            fallback_text = static_lines.get((npc, threshold_label), "No comment.")
            results.append(f"{icons[npc]} \"{fallback_text}\"")

    return results


def print_session_stats():
    """Print API usage summary for this session."""
    t = _token_log
    total = t['input_tokens'] + t['output_tokens']
    print(f"\n{'─'*60}")
    print(f"  API SESSION STATS")
    print(f"  Calls made:     {t['calls']}")
    print(f"  Fallbacks used: {t['fallbacks']}")
    print(f"  Input tokens:   {t['input_tokens']:,}")
    print(f"  Output tokens:  {t['output_tokens']:,}")
    print(f"  Total tokens:   {total:,}")
    # Rough cost estimate: Haiku input ~$0.80/M, output ~$4/M
    cost = (t['input_tokens'] / 1_000_000 * 0.80) + (t['output_tokens'] / 1_000_000 * 4.00)
    print(f"  Est. API cost:  ~${cost:.4f} USD")
    print(f"{'─'*60}")


# ─── Stage 4: World Events ────────────────────────────────────────────────────

WORLD_EVENT_SYSTEM = """
You are the game narrator for "The World Stage" — a geopolitical simulation.
Your job is to generate a brief, plausible breaking world event that impacts Europa.
Return ONLY a valid JSON object with exactly these fields:
{
  "title": "Short headline (max 8 words)",
  "description": "1-2 sentence news-ticker style description of the event.",
  "effects": {
    "oil_price_delta": <integer, -15 to +20>,
    "stability_delta": <integer, -8 to +5>,
    "relations_delta": {
      "usa": <integer, -10 to +10>,
      "arabia": <integer, -10 to +10>,
      "eu": <integer, -10 to +10>,
      "dprg": <integer, -10 to +10>
    }
  },
  "affected_npc": "<usa|arabia|eu|dprg|none>"
}
Rules:
- Make the event fit the current game context (active crises, relations, last player action).
- Events can be geopolitical (coup, summit, sanctions), economic (OPEC cut, recession),
  or environmental (oil spill, natural disaster).
- affected_npc should be the single NPC most affected, or "none" if global.
- Keep effects believable — not game-breaking. Small-medium deltas preferred.
- Return ONLY the JSON. No extra text, no markdown, no explanation.
"""


def generate_world_event(game_state, last_action_type: str = ""):
    """
    Generate a world event via Claude.
    Returns a dict with {title, description, effects, affected_npc}
    or None if generation fails.
    last_action_type: the type string of the player's last action (e.g. 'side_with', 'accept_deal')
    """
    context = _build_context(game_state)
    context["last_player_action"] = last_action_type or "unknown"

    # Hint the event theme based on current state
    hints = []
    if game_state.usa_sanctions_active:
        hints.append("USA sanctions are active — event could escalate or ease this pressure.")
    if game_state.arabia_embargo_active:
        hints.append("Arabia oil embargo is active — event could affect oil supply chain.")
    if game_state.stability < 35:
        hints.append("Domestic stability is critically low — internal unrest is possible.")
    if game_state.relations['dprg'] > 65:
        hints.append("DPRG relations are suspiciously high — Western reaction is plausible.")
    if not hints:
        hints.append("Generate an interesting geopolitical event that fits the current situation.")

    extra = " ".join(hints)

    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.9,
            system=WORLD_EVENT_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Current game state:\n{json.dumps(context, indent=2)}\n\n"
                    f"Event hint: {extra}\n\n"
                    f"Generate a world event JSON now."
                )
            }]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        event = json.loads(raw)
        # Validate required keys
        required = {"title", "description", "effects", "affected_npc"}
        if not required.issubset(event.keys()):
            return None
        return event
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] World event generation failed: {type(e).__name__}: {e}")
        return None


# ─── Stage 4: Negotiation ─────────────────────────────────────────────────────

# NPC negotiation system prompts — one per character
_NEGOTIATION_PROMPTS = {
    'usa': f"""{USA_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a direct private channel with Europa's leader.
They are trying to negotiate the terms of your offer.
Keep your character's voice and agenda. You may adjust your offer — but only for genuine strategic gain.
If you offer modified terms, include a "counter_offer" key in your JSON response.

SIGN CONVENTION: positive = Europa receives money, negative = Europa pays money.
  "budget": one-time immediate payment applied the turn the deal is accepted.
  "installments": recurring payment streams applied at end-of-turn, starting NEXT turn.
    Each entry: {{"amount": <float>, "turns": <int>, "description": "<label>"}}
    "turns" = number of end-of-turn payments (NOT counting the current turn).
    positive amount = Europa receives each turn, negative = Europa pays each turn.
    A deal CAN have multiple streams — e.g. one inbound and one outbound simultaneously.
    DO NOT mix budget + installments for the same payment; use one or the other.
IMPORTANT: make sure your dialogue text exactly matches your JSON numbers and turns.
  If you say "$8B now + $8B next turn", use budget:8 and installments:[{{amount:8, turns:1, ...}}].
  If you say "$10B over 2 turns", use installments:[{{amount:10, turns:2, ...}}] (no budget key).
Example two-stream deal: USA pays $10B/turn for 2 turns AND Europa pays $2.5B/turn for 3 turns:
  "installments": [{{"amount": 10.0, "turns": 2, "description": "US investment"}},
                   {{"amount": -2.5, "turns": 3, "description": "weapons purchase"}}]

Return a JSON object:
{{
  "response": "your in-character dialogue (2-3 sentences max)",
  "counter_offer": null
}}
OR if you want to propose modified deal terms:
{{
  "response": "your in-character dialogue",
  "counter_offer": {{
    "text": "Modified offer description (shown as option in game)",
    "type": "accept_deal",
    "npc": "usa",
    "consequences": {{
      "usa": <int>,
      "budget": <float or omit>,
      "installments": [<array of streams, or omit>],
      "stability": <int or omit>,
      "approval": <int or omit>
    }}
  }}
}}
Return ONLY valid JSON. No extra text.
""",

    'arabia': f"""{SADAM_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a private back-channel with Europa's leader.
Stay fully in character as Sadam. You enjoy deal-making and may sweeten offers for loyalty.
If you offer new terms, include a "counter_offer" in your JSON.

SIGN CONVENTION: positive = Europa receives money, negative = Europa pays money.
  "budget": one-time immediate payment applied the turn the deal is accepted.
  "installments": recurring payments applied at end-of-turn, starting NEXT turn.
    Each entry: {{"amount": <float>, "turns": <int>, "description": "<label>"}}
    "turns" = number of end-of-turn payments (NOT counting the current turn).
    A deal CAN have multiple streams (e.g. oil revenue inbound + equipment payment outbound).
    DO NOT mix budget + installments for the same payment; use one or the other.
IMPORTANT: your dialogue text must exactly match your JSON numbers and turns.

Return a JSON object:
{{
  "response": "*stage direction* your in-character dialogue (2-3 sentences)",
  "counter_offer": null
}}
OR with a deal offer:
{{
  "response": "*stage direction* dialogue",
  "counter_offer": {{
    "text": "Modified offer description",
    "type": "accept_deal",
    "npc": "arabia",
    "consequences": {{
      "arabia": <int>,
      "budget": <float or omit>,
      "installments": [<array of streams, or omit>],
      "oil_price": <int or omit>
    }}
  }}
}}
Return ONLY valid JSON. No extra text.
""",

    'eu': f"""{EU_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are in a private session with Europa's leader.
Stay fully in character as Marsha — skeptical, procedural, demanding specifics.
You don't do backroom deals. If you adjust terms, it is because they earned it with specifics.

SIGN CONVENTION: positive = Europa receives money, negative = Europa pays money.
  "budget": one-time immediate payment applied the turn the deal is accepted.
  "installments": recurring payments applied at end-of-turn, starting NEXT turn.
    Each entry: {{"amount": <float>, "turns": <int>, "description": "<label>"}}
    "turns" = number of end-of-turn payments (NOT counting the current turn).
    EU may structure phased grants alongside compliance obligations across multiple streams.
    DO NOT mix budget + installments for the same payment; use one or the other.
IMPORTANT: your dialogue text must exactly match your JSON numbers and turns.

Return a JSON object:
{{
  "response": "your in-character dialogue (2-3 sentences)",
  "counter_offer": null
}}
OR if they have genuinely convinced you:
{{
  "response": "dialogue",
  "counter_offer": {{
    "text": "Modified offer description",
    "type": "accept_deal",
    "npc": "eu",
    "consequences": {{
      "eu": <int>,
      "budget": <float or omit>,
      "installments": [<array of streams, or omit>],
      "stability": <int or omit>
    }}
  }}
}}
Return ONLY valid JSON. No extra text.
""",

    'dprg': f"""{JIWON_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are in a secure encrypted channel with Europa's leader.
Stay fully in character as Ji-won — cryptic, precise, occasionally warm.
You offer real intelligence or capabilities that other NPCs cannot.

SIGN CONVENTION FOR budget: positive = Europa receives money, negative = Europa pays money.
Example: "budget": 3.0 means DPRG channels $3B to Europa.

SIGN CONVENTION: positive = Europa receives money, negative = Europa pays money.
  "budget": one-time immediate payment applied the turn the deal is accepted.
  "installments": recurring payments applied at end-of-turn, starting NEXT turn.
    Each entry: {{"amount": <float>, "turns": <int>, "description": "<label>"}}
    "turns" = number of end-of-turn payments (NOT counting the current turn).
    Ji-won may structure shadow payments or intelligence fees across multiple streams.
    DO NOT mix budget + installments for the same payment; use one or the other.
IMPORTANT: your dialogue text must exactly match your JSON numbers and turns.

Return a JSON object:
{{
  "response": "your in-character dialogue (2-3 sentences)",
  "counter_offer": null
}}
OR with a modified deal:
{{
  "response": "dialogue",
  "counter_offer": {{
    "text": "Modified offer description",
    "type": "accept_deal",
    "npc": "dprg",
    "consequences": {{
      "dprg": <int>,
      "budget": <float or omit>,
      "installments": [<array of streams, or omit>]
    }}
  }}
}}
Return ONLY valid JSON. No extra text.
""",
}


EPITAPH_SYSTEM = """
You are a sardonic historian writing a one-sentence verdict on a fictional leader's turn in power.
Write in third person. Max 20 words. Dry wit preferred — like a historian a century from now
reading the footnotes. Reference the specific action taken, the regime type, or the mood of the nation.
Output ONLY the single sentence. No quotes. No attribution. No extra text.
Examples:
  "Having extracted six billion from the treasury, the Pragmatic Leader called it infrastructure spending."
  "Sadam's handshake that quarter would cost Europa dearly in the turns to come."
  "The people, still trusting their leader, would not read the Swiss account disclosures until spring."
"""

def generate_epitaph(game_state) -> str:
    """
    Generate a one-sentence historian-voice epitaph for the current turn.
    Uses the last action taken, regime type, approval, and budget trend as context.
    Returns a string (never None — falls back to a static line on error).
    """
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _static_epitaph_fallback(game_state)

    context = _build_context(game_state)
    # Add extra detail for epitaph specificity
    last_action = game_state.action_history[-1] if game_state.action_history else {}
    last_npc = last_action.get('npc', 'none')
    last_type = last_action.get('type', 'unknown')
    npc_names = {'usa': 'Bill Washington', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won'}

    action_summary = "did nothing"
    if last_type == 'side_with' and last_npc in npc_names:
        action_summary = f"sided with {npc_names[last_npc]}"
    elif last_type == 'accept_deal' and last_npc in npc_names:
        action_summary = f"accepted a deal from {npc_names[last_npc]}"
    elif last_type == 'do_nothing':
        action_summary = "declined all overtures"

    prompt = (
        f"Turn {game_state.current_turn} of {game_state.max_turns}. "
        f"The leader {action_summary}. "
        f"Regime: {context.get('regime_type', 'Managed Democracy')}. "
        f"Power base: {context.get('power_base', 'Mass-Dependent')}. "
        f"Approval: {game_state.public_approval}%. "
        f"Budget: ${game_state.budget:.0f}B. "
        f"Personal wealth: ${game_state.personal_wealth:.1f}B. "
        + (f"Active crisis: sanctions + embargo." if game_state.usa_sanctions_active and game_state.arabia_embargo_active
           else f"Sanctions: {game_state.usa_sanctions_active}. Embargo: {game_state.arabia_embargo_active}.")
        + "\n\nWrite the historian's one-sentence epitaph for this turn."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=60,
            temperature=0.85,
            system=EPITAPH_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        text = response.content[0].text.strip()
        # Remove surrounding quotes if the model added them
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Epitaph generation failed: {type(e).__name__}: {e}")
        return _static_epitaph_fallback(game_state)


def _static_epitaph_fallback(game_state) -> str:
    """Static fallback epitaphs keyed on rough game state."""
    pw = game_state.personal_wealth
    approval = game_state.public_approval
    stability = game_state.stability
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')

    if pw > 20:
        return "The leader enriched themselves considerably, a fact the ledgers would confirm long after the speeches were forgotten."
    if stability < 30:
        return "The nation trembled, and those responsible called it turbulence rather than collapse."
    if approval < 30:
        return "The people had grown quiet — not from satisfaction, but from exhaustion."
    if approval > 70:
        return "Public confidence held, though the more cynical observers noted it rarely lasts."
    if regime in ('Kleptocracy', 'Totalitarian Regime'):
        return "The regime by this point had outlasted the ideals that justified it."
    return "History, which is patient, continued to observe."


def generate_negotiation_response(game_state, npc_id: str, message: str, history: list):
    """
    Generate an NPC response during negotiation.

    Args:
        game_state: current GameState
        npc_id: 'usa' | 'arabia' | 'eu' | 'dprg'
        message: the player's latest message
        history: list of {role: 'user'|'assistant', content: str} prior messages

    Returns:
        dict: { response: str, counter_offer: dict | None }
        Falls back to a plain string response on parse failure.
    """
    system_prompt = _NEGOTIATION_PROMPTS.get(npc_id)
    if not system_prompt:
        return {"response": "I have nothing to say to that.", "counter_offer": None}

    context = _build_context(game_state)

    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"response": "…", "counter_offer": None}

    raw = None
    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Build messages list: inject context as system preamble in first user turn
        messages = []
        context_prefix = f"[Current game state: {json.dumps(context)}]\n\n"

        if history:
            # Prepend context to first user message
            first = history[0]
            messages.append({
                "role": first["role"],
                "content": context_prefix + first["content"]
            })
            messages.extend(history[1:])
            messages.append({"role": "user", "content": message})
        else:
            messages.append({
                "role": "user",
                "content": context_prefix + message
            })

        response = client.messages.create(
            model=MODEL,
            max_tokens=350,
            temperature=0.8,
            system=system_prompt,
            messages=messages
        )

        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()

        # Strip markdown code fences
        clean = raw
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        result = json.loads(clean)
        return {
            "response": result.get("response", "…"),
            "counter_offer": result.get("counter_offer", None),
        }

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Negotiation error for {npc_id}: {type(e).__name__}: {e}")
        # If we got a raw response but JSON parse failed, use it as plain text
        if raw:
            return {"response": raw, "counter_offer": None}
        fallbacks = {
            'usa': "I need time to consult with the team. Don't take that as encouragement.",
            'arabia': "*adjusts cufflinks* We will speak again when you are ready to be serious.",
            'eu': "I've said what I have to say. Come back with something concrete.",
            'dprg': "The channel remains open. Think carefully.",
        }
        return {"response": fallbacks.get(npc_id, "…"), "counter_offer": None}
