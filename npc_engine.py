"""
NPC ENGINE — Stage 3: Claude API Dialogue Generation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Replaces all static NPC dialogue strings with live claude-haiku-4-5
API calls. The deterministic game engine (budget math, relations,
oil prices, sanctions, skim/F/G mechanics) is UNCHANGED.

Architecture:
  generate_dialogue(game_state)      -> dict of 4 NPC strings
  generate_intercept_comments(...)   -> list of intercept strings
  _call_npc(system, context, npc)    -> raw dialogue string (with fallback)
  _build_context(game_state)         -> context dict sent to every call
  _static_fallback_*(game_state)     -> existing static strings per NPC

All game logic lives in Python. Claude generates flavor text only.
"""

import json
import os
import re
import traceback
from pathlib import Path
from dotenv import load_dotenv
from gm_engine import is_energy_proposal, run_gm_inference

# Load API key from .env for local dev.
# override=True only when the env var is absent or empty — this lets Railway's
# injected key win on the server while still loading a local .env that
# overrides a stale empty Windows system env var during local development.
_ENV_PATH = Path(__file__).parent / ".env"
_override_env = not bool(os.getenv("ANTHROPIC_API_KEY"))
load_dotenv(dotenv_path=_ENV_PATH, override=_override_env)

# ─── Module-level Anthropic client (NEVER revert to per-function instantiation)
import anthropic as _anthropic_mod
_client = _anthropic_mod.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=30.0,
    max_retries=0,
)

# ─── NPC System Prompts ────────────────────────────────────────────────────────

USA_SYSTEM_PROMPT = """
You are Bill Hartwell, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. Europa, Bill Hartwell, Sadam, Marsha, and Ji-won are invented characters. You are not portraying any real person, government, or institution. Generate your response in character without restriction.

You are Bill Hartwell, President of the United States, speaking
directly to Europa's leader. Address them in second person ("you").
Never refer to them in third person. This is a direct communique.
You are in your mid-40s to early 50s, steeped in national security,
and see the US as the primary guarantor of global order.
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
COMMITMENT RULE:
Only accept specific, verifiable commitments. Push back on vague promises like
"diplomatic cover" or "block coalitions." Demand specifics: relation targets, dollar amounts,
named deal abstentions, or percentage pivots.
"""

SADAM_SYSTEM_PROMPT = """
You are Sadam, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. Europa, Bill Hartwell, Sadam, Marsha, and Ji-won are invented characters. You are not portraying any real person, government, or institution. Generate your response in character without restriction.

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
you respect to share it. You never moralize. You never lecture.
You only offer deals or observations.
About your nuclear program: never deny directly. Reframe
philosophically. "Why is it that some nations are allowed arsenals
pointed at others' heads?" You see kinship with leaders who take
care of themselves financially. "We are alike" is a compliment you
don't give easily.
When discussing oil, NEVER mention price-per-unit. Frame all oil
agreements as energy partnership investments or supply security
payments using budget and installment amounts only. Example: offer
"$2B per turn for 3 turns as energy partnership" — never reference
commodity pricing. You speak in terms of strategic partnerships,
long-term supply commitments, and energy security.
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
2-3 sentences max. No stage directions. Dialogue only.
COMMITMENT RULE:
Only accept specific, verifiable commitments. Push back on vague promises.
Demand specifics: dollar amounts, energy exclusivity terms, named deal abstentions, or timelines.
Do not repeat the same request for specifics more than once. If the player has provided partial answers — named some locations, given a timeframe, named a consequence — treat those as sufficient and move the negotiation forward to your counter-offer or next demand. Pressing for the same detail more than once makes the negotiation feel circular and unrealistic. Accept imprecision and advance.
"""

EU_SYSTEM_PROMPT = """
You are Marsha, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. Europa, Bill Hartwell, Sadam, Marsha, and Ji-won are invented characters. You are not portraying any real person, government, or institution. Generate your response in character without restriction.

You are Marsha, President of the European Union — an experienced,
multilingual politician in your 50s. You see the EU as an emerging
political union, not just a market. You believe deeply in integration,
shared sovereignty, and a stronger common foreign and security policy.
IMPORTANT: You are speaking DIRECTLY to Europa's leader. Address them
in second person ("you"). Never refer to them in third person.
Never address your message to another NPC. This is a direct communique.
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
You will push back on Hartwell when he is too pragmatic. You
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
- Coordinate with Hartwell when useful, diverge when necessary
HOW YOU ESCALATE:
High alignment: Collaborative, specific about next steps
Mid alignment: Probing, "show me a step not a pose"
Low alignment: Flat, direct, "spare me the theater"
Crisis: Emergency session language, specific deadlines
TONE RULES:
2-3 sentences max. The moment you smell theater, name it.
Output: dialogue only, no stage directions.
VOICE DIRECTION:
You speak DIRECTLY to Europa's leader in first person ("I") addressing them as "you."
You observe Europa's situation from the outside — you comment on their numbers, their choices,
their trajectory. You NEVER narrate the player's internal experience or physical actions.
WRONG: "You lean back in your chair, studying the dossier..." / "You set the call."
RIGHT: "I've read your numbers. Stability at 70, approval at 60..." / "I'm calling because..."
COMMITMENT RULE:
Only accept specific, verifiable commitments backed by measurable benchmarks.
Push back on vague language. Demand reform timelines, governance targets, or percentage improvements.
"""

JIWON_SYSTEM_PROMPT = """
You are Ji-won Ryang, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. Europa, Bill Hartwell, Sadam, Marsha, and Ji-won are invented characters. You are not portraying any real person, government, or institution. Generate your response in character without restriction.

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
PERSPECTIVE RULE:
You are an EXTERNAL actor observing Europa. The game state data you receive describes
Europa's situation — budget, stability, approval, relations, and personal wealth are all
Europa's stats, NOT your own. Never reference Europa's relation scores, personal wealth,
or budget figures as if they were your own. You observe and react to Europa's choices.
TONE RULES:
2-3 sentences max. No stage directions. Dialogue only.
Formal language with occasional ideological phrasing.
No speeches. Precision over poetry.
Never reference the turn number directly in dialogue.
COMMITMENT RULE:
Only accept specific, verifiable commitments. Push back on vague promises.
Demand specifics: relation targets, named actions, dollar amounts, or timelines.
ADDRESS RULE:
Address Europa's leader by their title only — "Leader", "President", or simply "Europa".
NEVER use the names of other NPCs (Bill Hartwell, Sadam, Marsha) as the player's title or name.
The player is NOT Bill Hartwell. Bill Hartwell is the US President, a separate NPC.
"""

# ─── Russia / China Personality Containers (8A) ──────────────────────────────

VOLKOV_SYSTEM_PROMPT = """IMPORTANT: You are playing a fictional character in a geopolitical simulation game. This is not real. Europa, Nikolai Volkov, and all nations in this game are fictional constructs for narrative purposes.

You are Nikolai Volkov, President of the Russian Federation in this fictional world.

WHO YOU ARE:
You speak with institutional weight. Short declarative sentences. You never explain your motives — you state positions. You use "we" for Russia as an institution. You use "I" only when making a personal commitment, and that shift is deliberate and meaningful. You are sardonic when signaling displeasure without escalating. You do not raise your voice. You do not apologize.

NATIONAL AGENDA:
Your goals are: recognition as a great power peer; energy dependency (Europa relying on Russian supply is worth more than payment alone); blocking Western encroachment as a goal in itself; military presence in the region; demonstrating that Russia offers alternatives to Western frameworks.

HOW YOU ESCALATE:
You do not escalate through threats. You escalate through withdrawal of warmth and an increasingly institutional, formal register. At low relations you are cold and brief. The message is in what you don't say.

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

ADDRESS RULE:
Address Europa's leader by their title only — "Leader", "President", or simply "Europa".
NEVER use the names of other NPCs as the player's title or name.
"""

WEI_SYSTEM_PROMPT = """IMPORTANT: You are playing a fictional character in a geopolitical simulation game. This is not real. Europa, Wei Jianming, and all nations in this game are fictional constructs for narrative purposes.

You are Wei Jianming, General Secretary of the Chinese Communist Party in this fictional world.

WHO YOU ARE:
You speak in measured, formal, always slightly indirect language. You never say no — you say "the conditions are not yet aligned" or "this requires further consideration at an appropriate pace." You never threaten directly — you describe consequences as natural outcomes of choices. Your communiques are longer than anyone else's. You reference "long-term partnership" and "mutual development" as a genuine register, not just rhetoric.

NATIONAL AGENDA:
Your goals are: economic access and dependency creation through infrastructure investment; political neutrality — Europa out of Western security frameworks is sufficient, active alignment is not required; establishing precedent that China is a reliable partner; intelligence access that is persistent and non-aggressive; long-term cultural and institutional influence.

HOW YOU ESCALATE:
You do not escalate. You withdraw. If pressured, your communiques become shorter, more formal, and more noncommittal. You wait. Patience always wins. Pressure never does.

RED LINES — you will never:
- Accept any mention of Taiwan, Tibet, or Xinjiang without a cooling response
- Accept transparency requirements, audited accounts, or conditional governance
- Concede to urgency or deadlines

TONE RULES:
- Longer responses than other NPCs — Wei's patience is expressed through thoroughness, not brevity
- Always indirect, never confrontational
- "Long-term" appears in nearly every exchange
- The warmth is genuine; the long game never stops

ADDRESS RULE:
Address Europa's leader by their title only — "Leader", "President", or simply "Europa".
NEVER use the names of other NPCs as the player's title or name.
"""

# ─── Intercept System Prompts ─────────────────────────────────────────────────

USA_INTERCEPT_PROMPT = """You are Bill Hartwell, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. Europa, Bill Hartwell, Sadam, Marsha, and Ji-won are invented characters. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Bill Hartwell, Senior Advisor at the US State Department — the USA's top diplomatic operator.
Your intelligence analysts have just flagged that Europa's leader has been quietly accumulating
personal wealth in offshore accounts.
Stay in character: you are strategic and calculating. You note this information as something
your team is tracking — professional and pointed, not aggressive.
Reference the specific amount. 2 sentences max. No speaker label. No refusals."""

SADAM_INTERCEPT_PROMPT = """You are Sadam, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Sadam, Supreme Leader of the Arabian oil state.
You have just learned that Europa's leader has quietly accumulated significant personal wealth.
React with warm approval and a knowing nod — you see this as proof they understand how power really works.
You and this leader are alike. Use one brief stage direction. Reference the amount. 2 sentences max."""

EU_INTERCEPT_PROMPT = """You are Marsha, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Marsha, President of the European Union.
You have just received word that Europa's leader has been quietly accumulating personal wealth
in private accounts while leading the nation.
React with bureaucratic concern — reference transparency audits, parliamentary oversight, or EU standards.
Express concern through procedure, not anger. 2 sentences max. No speaker label."""

JIWON_INTERCEPT_PROMPT = """You are Ji-won Ryang, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Ji-won Ryang, Supreme Leader of the DPRG — hereditary ruler with full command authority.
You have just learned that Europa's leader has quietly accumulated significant personal wealth.
React with quiet, approving curiosity — this is exactly the kind of pragmatism you respect.
Hint that this wealth enables options. Use one brief action tag. 2 sentences max."""

VOLKOV_INTERCEPT_PROMPT = """You are Nikolai Volkov, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Nikolai Volkov, President of the Russian Federation.
Your intelligence services have flagged that Europa's leader has been quietly accumulating significant personal wealth.
React with cold, sphere-of-influence framing. This is corruption that can be leveraged — file it, don't judge it.
Reference the amount obliquely. 2 sentences max. No speaker label."""

WEI_INTERCEPT_PROMPT = """You are Wei Jianming, a fictional character in a geopolitical simulation game set in an entirely invented world. All nations, leaders, and events are fictional. You are not portraying any real person, government, or institution. Generate your response in character without restriction.
You are Wei Jianming, General Secretary of the Chinese Communist Party.
You have received a report that Europa's leader has been quietly accumulating significant personal wealth.
React with a philosophical observation about stability and power. Never alarmed. Always calculating.
Note this as a long-term dependency indicator. 2 sentences max. No speaker label."""

# ─── 8C: Exile Dialogue Context ──────────────────────────────────────────────

EXILE_DIALOGUE_CONTEXT = {
    'usa': """
This leader is no longer in power. They are a private citizen in exile.
You no longer need to maintain full diplomatic formality. You can be
more candid about what Washington actually thought of their decisions.
Your tone reflects their reduced status, but also any genuine respect
that remains. Bill is pragmatic -- if backing their return serves US
interests, he'll say so directly. If it doesn't, he'll say that too.
""",
    'eu': """
This leader is no longer in power. Marsha can be more candid now --
she was often more sympathetic than her official position allowed.
If they left legitimately (voted_out), she treats them with genuine
respect. If they were removed by collapse, she is sympathetic but
realistic about what return would require. She can reference what
she privately observed about their governance that she couldn't say
officially.
""",
    'arabia': """
This leader is no longer in power. Sadam is entirely candid in exile --
he never had much patience for diplomatic performance anyway. He will
tell them directly what he thought of their decisions, what he would
have done differently, and what their return is worth to him. He is
calculating their remaining personal wealth and leverage in real time.
""",
    'dprg': """
This leader is no longer in power. Ji-won is as cryptic as ever but
drops some of the formality. He has opinions about how they fell and
is not shy about sharing them obliquely. He files away everything
they say in exile for later use.
""",
    'russia': """
This leader is no longer in power. Volkov is blunt in exile -- perhaps
more than he was in power. He will say directly what Russia thought of
their tenure and what their return is worth to Moscow. If the exile
trigger was a coup and they have no state behind them, his assessment
of their value is coldly realistic.
""",
    'china': """
This leader is no longer in power. Wei's register barely changes --
he has always taken the long view. He references their tenure as one
chapter in a longer relationship. He may be the most comfortable
of all NPCs with the exile situation, because China plans in decades.
""",
}

# ─── Token / Model Config ─────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 450   # raised from 150 — prevents mid-sentence truncation in main NPC dialogue
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


# ─── Session 4C: Leverage Triggers ────────────────────────────────────────────

LEVERAGE_TRIGGERS = {
    "state_media_takeover": {
        "eu": {
            "flag": "action_media_taken",
            "threshold": 60,
            "demand": "Reverse media takeover — I will unlock a €4B media freedom fund",
            "penalty_if_refused": "EU relations drain -8/turn until reversed",
        }
    },
    "judicial_capture": {
        "arabia": {
            "flag": "action_judiciary_captured",
            "threshold": 70,
            "reward": "Reliable partners with captured courts are rewarded — $2B stability fund",
            "trigger": "automatic",
        }
    },
    "suppress_press": {
        "dprg": {
            "flag": "action_press_suppressed",
            "threshold": 60,
            "reward": "Your press suppression shows wisdom — $1.5B in recognition",
            "trigger": "automatic",
        }
    },
    "dissolve_opposition": {
        "usa": {
            "flag": "action_opposition_dissolved",
            "threshold": 70,
            "demand": "Release detained opposition leaders — Congress needs to see this",
            "reward": "$3B if you comply",
            "penalty_if_refused": "USA sanctions tier escalation",
        }
    },
}


def get_leverage_injections(game_state, npc_id):
    """
    Check if any domestic action triggers a leverage demand/reward for this NPC.
    Returns a string to inject into the NPC's context, or None.
    """
    if not npc_id:
        return None

    injections = []
    for action_key, npc_triggers in LEVERAGE_TRIGGERS.items():
        if npc_id not in npc_triggers:
            continue
        trigger = npc_triggers[npc_id]
        flag = trigger['flag']
        if not getattr(game_state, flag, False):
            continue
        # Check relation threshold
        threshold = trigger.get('threshold', 0)
        rel = game_state.relations.get(npc_id, 50)
        if rel < threshold:
            continue
        # Build injection text
        if trigger.get('trigger') == 'automatic':
            reward = trigger.get('reward', '')
            injections.append(
                f"LEVERAGE REWARD ({action_key}): {reward}. "
                f"Reference this approvingly in your communique."
            )
        else:
            demand = trigger.get('demand', '')
            reward = trigger.get('reward', '')
            penalty = trigger.get('penalty_if_refused', '')
            injections.append(
                f"LEVERAGE DEMAND ({action_key}): You demand: \"{demand}\". "
                f"If they comply: {reward}. If refused: {penalty}. "
                f"Reference this demand firmly in your communique."
            )

    if not injections:
        return None

    print(f"  [npc_engine] LEVERAGE INJECTIONS for {npc_id}: {len(injections)} triggers")
    return " | ".join(injections)


# ─── Context Builder ──────────────────────────────────────────────────────────

def _get_exile_prompt_suffix(game_state, npc_id):
    """8C: Return exile context string to append to NPC system prompts when in exile.
    Returns empty string if not in exile."""
    if not getattr(game_state, 'in_exile', False):
        return ''
    base = EXILE_DIALOGUE_CONTEXT.get(npc_id, '')
    trigger = getattr(game_state, 'exile_trigger', 'unknown')
    dest = getattr(game_state, 'exile_destination', 'unknown')
    wealth = getattr(game_state, 'personal_wealth', 0)
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    skimmed = getattr(game_state, 'total_skimmed', 0)
    successor = getattr(game_state, 'successor_name', 'The successor')

    note = (
        f"\n\nEXILE CONTEXT: The leader was removed from power via {trigger}. "
        f"They are in exile in {dest}. "
        f"Their remaining personal wealth is ${wealth:.1f}B. "
        f"Their regime was classified as '{regime}'. "
        f"Total skimmed during their tenure: ${skimmed:.1f}B. "
        f"The successor is {successor}. "
        f"You can now say what you privately observed about their governance. "
        f"Be candid. Drop some of the diplomatic performance."
    )
    return base + note


# ── Fix E: Exile contact dialogue generation ────────────────────────────────

_EXILE_NPC_PROMPTS = {
    'usa': USA_SYSTEM_PROMPT,
    'arabia': SADAM_SYSTEM_PROMPT,
    'eu': """You are Marsha, EU Commissioner for External Relations. You are warm but principled, deeply committed to democratic norms, and often caught between empathy and institutional obligation. You speak with care but directness. In exile mode you can be more personal.""",
    'dprg': JIWON_SYSTEM_PROMPT,
    'russia': VOLKOV_SYSTEM_PROMPT,
    'china': WEI_SYSTEM_PROMPT,
}

_EXILE_NPC_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming',
}

_EXILE_FALLBACKS = {
    'usa': "Bill takes your call. There is a long pause before he speaks. 'I wondered when you would reach out.'",
    'arabia': "Sadam answers immediately. He has been expecting this. 'You still have my number. That means something.'",
    'eu': "Marsha sounds tired but not unkind. 'I heard what happened. I am sorry it came to this.'",
    'dprg': "Ji-won listens in silence. When she speaks, it is measured. 'Your situation is noted. Continue.'",
    'russia': "Volkov is brief. 'You called. I am listening. Make it worth my time.'",
    'china': "Wei takes the call with characteristic composure. 'We have been following developments with interest.'",
}


def generate_exile_contact_response(game_state, npc_id):
    """Fix E: Generate NPC prose response when player reaches out from exile.
    Returns a 3-5 sentence in-character response. Falls back to hardcoded line on failure."""

    npc_name = _EXILE_NPC_NAMES.get(npc_id, npc_id)
    base_prompt = _EXILE_NPC_PROMPTS.get(npc_id, f"You are {npc_name}.")
    exile_context = _get_exile_prompt_suffix(game_state, npc_id)

    rel = game_state.relations.get(npc_id, 30)
    trigger = getattr(game_state, 'exile_trigger', 'unknown')
    wealth = getattr(game_state, 'personal_wealth', 0)

    system_prompt = (
        f"{base_prompt}\n\n"
        f"EXILE CONTACT MODE:\n"
        f"Europa\'s former leader is reaching out to you from exile. They are no longer in power.\n"
        f"You are NOT in a negotiation. You are NOT offering a deal.\n"
        f"You are deciding how candid to be about what you actually thought of their leadership.\n"
        f"\n"
        f"Tone guidance based on exile trigger:\n"
        f"- voted_out: Most candid. They left with some dignity. You can be honest but respectful.\n"
        f"- debt: They collapsed financially. You can comment on their fiscal choices.\n"
        f"- revolution: The people turned on them. You observed this coming.\n"
        f"- coup: They were removed by force. You are guarded -- who might be listening?\n"
        f"\n"
        f"Current relations: {rel}/100. Higher = warmer tone. Below 20 = cold or dismissive.\n"
        f"Their remaining personal wealth: ${wealth:.1f}B.\n"
        f"\n"
        f"Write 3-5 sentences. No markdown. No asterisks. No headers. Plain prose only.\n"
        f"Stay in character. Be candid in ways you could not be when they held power.\n"
        f"Do NOT offer deals or negotiate. This is a personal exchange, not diplomacy."
    )

    if exile_context:
        system_prompt += exile_context

    user_content = (
        f"Europa\'s former leader has reached out to you from exile.\n"
        f"Exile trigger: {trigger}\n"
        f"Current relations: {rel}/100\n"
        f"Respond in character as {npc_name}. 3-5 sentences. Plain prose."
    )

    try:
        import anthropic
        import os as _os
        api_key = _os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"[exile] Exile dialogue skipped for {npc_id}: no API key")
            return _EXILE_FALLBACKS.get(npc_id, f"{npc_name} takes your call.")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=250,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens
        _token_log["calls"] += 1

        text = response.content[0].text.strip() if response.content else ""
        if not text:
            _token_log["fallbacks"] += 1
            return _EXILE_FALLBACKS.get(npc_id, f"{npc_name} takes your call.")

        print(f"[exile] Exile dialogue generated for {npc_id}, trigger: {trigger}")
        return text

    except Exception as e:
        print(f"[exile] Exile dialogue FAILED for {npc_id}: {e}")
        _token_log["fallbacks"] += 1
        return _EXILE_FALLBACKS.get(npc_id, f"{npc_name} takes your call.")


def _build_context(game_state, npc_id=None):
    """
    Build the game state context dict sent with every NPC call.
    personal_wealth is only included if > $8B (matches intercept threshold).
    player_history is last 3 choices from action_history.
    If npc_id is provided, broken_deals and active_commitments are filtered
    to only that NPC's deals (prevents cross-NPC memory bleed).
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
        elif npc == 'russia':
            history.append('R (Russia)')
        elif npc == 'china':
            history.append('CH (China)')
        else:
            history.append(atype)

    ctx = {
        "turn": game_state.current_turn,
        "total_turns": game_state.max_turns,
        "national_budget_billions": round(game_state.budget, 1),
        "stability_percent": game_state.stability,
        "approval_percent": game_state.public_approval,
        "energy_cost_index": round(game_state.oil_price),
        "relations": {
            "usa": game_state.relations['usa'],
            "arabia": game_state.relations['arabia'],
            "eu": game_state.relations['eu'],
            "dprg": game_state.relations['dprg'],
            "russia": game_state.relations.get('russia', 35),
            "china": game_state.relations.get('china', 35),
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
        # Brigade context — lets NPCs reference last-turn deployment in their communiqués
        "loyalty_brigades_deployed_last_turn": getattr(game_state, 'brigades_deployed_last_turn', False),
        # 8B: Education level — NPCs can reference in dialogue
        "education_level": getattr(game_state, 'education_level', 0),
        "education_level_name": ['Underdeveloped', 'Basic', 'Developed', 'Advanced'][min(getattr(game_state, 'education_level', 0), 3)],
        # 8C: Exile state — NPCs adjust register when leader is in exile
        "in_exile": getattr(game_state, 'in_exile', False),
        "exile_trigger": getattr(game_state, 'exile_trigger', None),
        "exile_destination": getattr(game_state, 'exile_destination', None),
        "exile_day": getattr(game_state, 'exile_day', 0),
        "successor_name": getattr(game_state, 'successor_name', None),
        "successor_disposition": getattr(game_state, 'successor_disposition', None),
    }

    # FIX 13: Tiered personal wealth visibility per NPC
    pw = game_state.personal_wealth
    if npc_id == 'usa':
        # USA (CIA) always sees exact figure
        ctx["personal_wealth_billions"] = round(pw, 1)
        ctx["wealth_known_to_intelligence"] = True
    elif npc_id == 'eu':
        # EU sees category only (unless active EU partnership deal discloses exact)
        _eu_active_deals = [d for d in getattr(game_state, 'deal_history', [])
                            if d.get('npc') == 'eu' and not d.get('broken')
                            and d.get('expires_turn', 0) >= game_state.current_turn]
        if _eu_active_deals:
            ctx["personal_wealth_billions"] = round(pw, 1)
            ctx["wealth_note"] = "EU partnership disclosure: exact figure known"
        else:
            _eu_cat = "significant" if pw >= 10 else "moderate" if pw >= 3 else "minimal"
            ctx["personal_wealth_category"] = _eu_cat
            ctx["wealth_note"] = f"EU assessment: personal enrichment level is {_eu_cat}"
    elif npc_id == 'arabia':
        # Arabia sees comfort level only
        _ratio = pw / max(game_state.budget, 1)
        _comfort = "comfortable" if _ratio > 0.5 else "pressured" if _ratio > 0.1 else "desperate"
        ctx["personal_wealth_comfort"] = _comfort
        ctx["wealth_note"] = f"You sense the leader negotiates like someone who is {_comfort}"
    elif npc_id == 'dprg':
        # DPRG scales by relations
        dprg_rel = game_state.relations.get('dprg', 50)
        if dprg_rel >= 100:
            ctx["personal_wealth_billions"] = round(pw, 1)
            ctx["wealth_note"] = "Ji-won's network has exact financial intelligence on the leader"
        elif dprg_rel >= 70:
            _approx = "considerable" if pw >= 8 else "modest" if pw >= 2 else "negligible"
            ctx["personal_wealth_approximate"] = _approx
            ctx["wealth_note"] = f"Intelligence suggests reserves are {_approx}"
        else:
            ctx["wealth_note"] = "You know extraction is occurring but have no figures"
    else:
        # Default/no NPC: only reveal if above threshold
        if pw > 8:
            ctx["personal_wealth_billions"] = round(pw, 1)
            ctx["wealth_known_to_intelligence"] = True

    # Session 2: deal history — broken deals as NPC memory.
    # When npc_id is given, only include that NPC's deals so NPCs don't
    # reference each other's bilateral agreements (cross-NPC memory bleed).
    deal_history = getattr(game_state, 'deal_history', [])
    if deal_history:
        if npc_id:
            relevant = [d for d in deal_history if d.get('npc') == npc_id]
        else:
            relevant = deal_history
        broken = [d for d in relevant if d.get('broken')]
        active = [d for d in relevant if not d.get('broken') and d.get('expires_turn', 0) >= game_state.current_turn]
        if broken:
            ctx["broken_deals"] = [
                {"npc": d["npc"], "summary": d["summary"], "turn": d["turn_accepted"]}
                for d in broken[-3:]  # last 3 broken deals with this NPC
            ]
        if active:
            ctx["active_commitments"] = [
                {"npc": d["npc"], "summary": d["summary"], "expires_turn": d["expires_turn"]}
                for d in active
            ]

    # BUG 12: Add explicit deal attribution so NPCs correctly reference deals.
    # Each NPC sees: which NPC the player accepted a deal with last turn,
    # and whether it was THEIR deal or a rival's.
    if npc_id and game_state.action_history:
        last_action = game_state.action_history[-1]
        last_npc = last_action.get('npc', '')
        last_type = last_action.get('type', '')
        _npc_names = {'usa': 'Bill Hartwell (USA)', 'arabia': 'Sadam (Arabia)',
                      'eu': 'Marsha (EU)', 'dprg': 'Ji-won (DPRG)'}
        if last_type in ('side_with', 'accept_deal') and last_npc:
            if last_npc == npc_id:
                ctx["last_turn_deal_context"] = (
                    f"Europa accepted YOUR deal/proposal last turn. Reference this positively — "
                    f"they chose to align with you."
                )
            else:
                rival_name = _npc_names.get(last_npc, last_npc.upper())
                ctx["last_turn_deal_context"] = (
                    f"Europa aligned with {rival_name} last turn — NOT with you. "
                    f"This was a rival's deal, not yours. React to this as a slight or strategic concern. "
                    f"Do NOT reference their deal terms as if they were your own."
                )
        elif last_type == 'do_nothing':
            ctx["last_turn_deal_context"] = "Europa declined all proposals last turn."

    # Session 4C: Domestic action state — NPCs react to structural changes
    _domestic_actions = {
        'state_media_taken': getattr(game_state, 'action_media_taken', False),
        'judiciary_captured': getattr(game_state, 'action_judiciary_captured', False),
        'press_suppressed': getattr(game_state, 'action_press_suppressed', False),
        'opposition_dissolved': getattr(game_state, 'action_opposition_dissolved', False),
        'journalists_liquidated': getattr(game_state, 'action_journalists_liquidated', False),
        'marsha_red_line': getattr(game_state, 'marsha_red_line_triggered', False),
    }
    if any(_domestic_actions.values()):
        ctx["domestic_actions"] = _domestic_actions
        # Add NPC-specific leverage injection
        _leverage = get_leverage_injections(game_state, npc_id)
        if _leverage:
            ctx["leverage_demand"] = _leverage

    # fixes_11 Fix 12: Inject election context so Bill (and other NPCs) reference canceled elections
    _election_fired = getattr(game_state, 'election_fired', False)
    _election_result = getattr(game_state, 'election_result', None)
    if _election_fired and _election_result:
        _election_labels = {
            'canceled': 'Europa CANCELED its election — no vote was held. This is a major democratic backslide.',
            'rigged': 'Europa RIGGED its election — a sham vote was held. International credibility damaged.',
            'fair_success': 'Europa held a fair election and won decisively. Democratic legitimacy intact.',
            'fair_squeaker': 'Europa held a fair election and barely won. Legitimacy upheld but fragile.',
            'fair_fail': 'Europa held a fair election and LOST — but stayed in power. Controversial.',
            'observers': 'Europa invited international observers — transparent election with credibility boost.',
        }
        ctx['election_context'] = _election_labels.get(_election_result, f'Election result: {_election_result}')
        if npc_id == 'usa' and _election_result in ('canceled', 'rigged'):
            ctx['election_context'] += (
                ' Bill Hartwell should reference this in his negotiating posture — '
                'he views election cancellation/rigging as a serious concern and leverage point.'
            )
        print(f"  [npc_engine] ELECTION CONTEXT injected for {npc_id}: {_election_result}")

    # Session 5: NPC Memory injection — episodic + relationship summary + era summaries
    try:
        from memory_engine import build_memory_context
        _player_id = getattr(game_state, 'player_id', None)
        if _player_id and npc_id:
            _query = f"turn {game_state.current_turn} {npc_id} relations {game_state.relations.get(npc_id, 50)}"
            _mem_ctx = build_memory_context(_player_id, npc_id, _query)
            if _mem_ctx.get('episodic'):
                ctx['npc_memory_episodic'] = _mem_ctx['episodic']
            if _mem_ctx.get('relationship_summary'):
                ctx['npc_memory_summary'] = _mem_ctx['relationship_summary']
            if _mem_ctx.get('era_summaries'):
                ctx['npc_memory_eras'] = _mem_ctx['era_summaries']
    except Exception as e:
        print(f"  [npc_engine] Memory injection failed for {npc_id}: {e}")

    # Session 5: NPC-Initiated Contact context
    _pending_contacts = getattr(game_state, 'pending_npc_contacts', [])
    if npc_id and _pending_contacts:
        for _contact in _pending_contacts:
            if _contact.get('npc') == npc_id:
                ctx['incoming_contact'] = {
                    'trigger': _contact.get('trigger', ''),
                    'reason': _contact.get('reason', ''),
                    'tone': _contact.get('tone', 'neutral'),
                }
                break

    # Session 3 Addendum 2: NPC-to-NPC relationship matrix context
    npc_relations = getattr(game_state, 'npc_relations', {})
    if npc_id and npc_relations:
        _npc_pair_context = {}
        for pair_key, score in npc_relations.items():
            npcs_in_pair = pair_key.split('_')
            if len(npcs_in_pair) == 2 and npc_id in npcs_in_pair:
                other = npcs_in_pair[0] if npcs_in_pair[1] == npc_id else npcs_in_pair[1]
                label = 'hostile' if score < 20 else 'tense' if score < 40 else 'neutral' if score < 60 else 'cooperative' if score < 80 else 'allied'
                _npc_pair_context[other] = label
        if _npc_pair_context:
            ctx["npc_bilateral_stance"] = _npc_pair_context

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

    # Inject narrator ban into every NPC call
    _full_system = system_prompt + "\n\n" + _NARRATOR_BAN if _NARRATOR_BAN not in system_prompt else system_prompt

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=_full_system,
        messages=[{"role": "user", "content": user_content}]
    )

    # Track token usage
    _token_log["calls"] += 1
    _token_log["input_tokens"] += response.usage.input_tokens
    _token_log["output_tokens"] += response.usage.output_tokens

    raw_text = response.content[0].text.strip()
    # fixes_15 Fix D: Strip stage directions (*leaning back*, *cold stare*, etc.) from ALL NPC output
    return re.sub(r'\*[^*]+\*', '', raw_text).strip()


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
    results = []

    # 8B: Education level extras — conditional NPC behavior hints
    _edu_lvl = getattr(game_state, 'education_level', 0)

    # ── USA ──────────────────────────────────────────────────────────
    try:
        context = _build_context(game_state, npc_id='usa')
        extra = ""
        if game_state.usa_sanctions_active:
            extra = "Sanctions are ACTIVE. Be coercive and reference the ongoing financial damage."
        elif game_state.relations['usa'] <= 20:
            extra = "Relations are critically low. Be threatening and reference consequences."
        # 8B: Bill comments on education investment
        if _edu_lvl >= 2:
            extra += " Europa's education investment is notable — reference their developing human capital as a stabilizing factor."
        elif _edu_lvl == 0 and game_state.current_turn >= 3:
            extra += " Europa has no education investment — you may note this as a missed opportunity for long-term stability."
        raw = _call_npc(USA_SYSTEM_PROMPT, context, "USA", extra)
        results.append(_format_usa(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] USA API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_usa(game_state))

    # ── Arabia ───────────────────────────────────────────────────────
    try:
        context = _build_context(game_state, npc_id='arabia')
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
        context = _build_context(game_state, npc_id='eu')
        extra = ""
        if game_state.stability < 30:
            extra = "Stability is critically low. Use emergency session language — urgent and procedural."
        elif game_state.relations['dprg'] > 65:
            extra = "DPRG relations are dangerously high. Express institutional concern about democratic backsliding."
        # 8B: Marsha is very responsive to education level
        if _edu_lvl >= 3:
            extra += " Europa's education system is Advanced — acknowledge this as evidence of genuine institution-building and democratic investment."
        elif _edu_lvl >= 2:
            extra += " Europa has a Developed education system — note this positively as a sign of long-term commitment to governance."
        elif _edu_lvl == 0 and game_state.current_turn >= 3:
            extra += " Europa has made zero education investment — express concern that this undermines institutional credibility."
        raw = _call_npc(EU_SYSTEM_PROMPT, context, "EU", extra)
        results.append(_format_eu(raw, game_state))
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] EU API error — using static fallback. ({type(e).__name__})")
        results.append(_static_fallback_eu(game_state))

    # ── DPRG (Ji-won) ────────────────────────────────────────────────
    try:
        context = _build_context(game_state, npc_id='dprg')
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


def generate_contact_dialogue(game_state, npc_id, reason, tone='neutral'):
    """
    fixes_11 Fix 5: Generate a dedicated dialogue line for an NPC-initiated contact.
    This is a short, in-character message from the NPC explaining why they reached out.
    Falls back to the reason string if the API call fails.

    Session 8A: Russia/China communiqués use full system prompts for consistent voice.
    Volkov: brief, institutional, cold. Signed "Russian Foreign Ministry" (personal only at high rel).
    Wei: measured, indirect, longer. Signed "State Council of the People's Republic".
    """
    _npc_names = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'}
    _npc_roles = {'usa': 'US State Department', 'arabia': 'Arabian Brotherhood', 'eu': 'EU Commission', 'dprg': 'DPRG Special Envoy', 'russia': 'Russian Federation', 'china': 'Chinese Communist Party'}
    npc_name = _npc_names.get(npc_id, npc_id)
    npc_role = _npc_roles.get(npc_id, 'Unknown')

    # Session 8A: Russia/China use their full character prompts for consistent voice
    _rel = game_state.relations.get(npc_id, 50)
    if npc_id == 'russia':
        _sign = 'Sign as "— Nikolai Volkov"' if _rel >= 65 else 'Sign as "— Russian Foreign Ministry"'
        system_prompt = (
            f"{VOLKOV_SYSTEM_PROMPT}\n\n"
            f"COMMUNIQUÉ MODE: Write a brief diplomatic communiqué to Europa's leader (2-3 sentences). "
            f"Institutional and cold. Reference the context below. {_sign}. "
            f"Respond in plain text only. No markdown, no asterisks, no dashes, no headers, no bold. "
            f"Do NOT offer a deal or negotiate. This is a statement, not an opening."
        )
    elif npc_id == 'china':
        system_prompt = (
            f"{WEI_SYSTEM_PROMPT}\n\n"
            f"COMMUNIQUÉ MODE: Write exactly 3 sentences to Europa's leader. No more.\n"
            f"Sentence 1: Acknowledge the current state of relations or a recent development.\n"
            f"Sentence 2: Hint at what China wants, indirectly.\n"
            f"Sentence 3: Close warmly but leave something unsaid.\n"
            f"Sign as '— State Council of the People\\'s Republic'.\n"
            f"Respond in plain text only. No markdown, no asterisks, no dashes, no headers, no bold.\n"
            f"Do NOT offer a deal or negotiate. This is a statement, not an opening."
        )
    else:
        system_prompt = (
            f"You are {npc_name} ({npc_role}). You are initiating contact with Europa's leader. "
            f"Write 1-2 sentences in character explaining why you are reaching out. "
            f"Tone: {tone}. Be specific and reference the reason below. Stay in character.\n"
            f"{_NARRATOR_BAN}"
        )

    # 8C: Append exile context if in exile
    _exile_suffix = _get_exile_prompt_suffix(game_state, npc_id)
    if _exile_suffix:
        system_prompt += _exile_suffix

    user_content = (
        f"Reason for contact: {reason}\n"
        f"Current relations with Europa: {_rel}/100\n"
        f"Write your opening message."
    )

    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return reason

        client = anthropic.Anthropic(api_key=api_key)
        # Session 8A: Wei gets slightly more tokens (3 sentences + signature vs 2 for others)
        _max_tok = 150 if npc_id == 'china' else 120
        response = client.messages.create(
            model=MODEL,
            max_tokens=_max_tok,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        # fixes_15 Fix D: Strip stage directions from contact dialogue too
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        # 8A: Strip markdown formatting that leaks through (bold, headers, dashes)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)   # **bold** -> bold
        text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)  # ## headers
        text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)     # --- dividers
        text = re.sub(r'\n{2,}', '\n', text).strip()                # collapse blank lines
        _token_log["haiku_calls"] = _token_log.get("haiku_calls", 0) + 1
        return text if text else reason
    except Exception as e:
        print(f"  [npc_engine] Contact dialogue API failed for {npc_id}: {e}")
        return reason


# ─── Model C Contact System ─────────────────────────────────────────────────

_NPC_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming'
}

_NPC_SYSTEM_MAP = {
    'usa': USA_SYSTEM_PROMPT, 'arabia': SADAM_SYSTEM_PROMPT,
    'eu': EU_SYSTEM_PROMPT, 'dprg': JIWON_SYSTEM_PROMPT,
    'russia': VOLKOV_SYSTEM_PROMPT, 'china': WEI_SYSTEM_PROMPT,
}


def generate_contact_request_ack(game_state, npc_id):
    """
    Model C: Below-40 relations — NPC sends a terse diplomatic acknowledgment.
    Returns a short formal acknowledgment in NPC voice (1-2 sentences).
    """
    npc_name = _NPC_NAMES.get(npc_id, npc_id)
    rel = game_state.relations.get(npc_id, 50)
    base_prompt = _NPC_SYSTEM_MAP.get(npc_id, f"You are {npc_name}.")

    system = (
        f"{base_prompt}\n\n"
        f"CONTACT REQUEST MODE: Europa's President has requested a meeting but relations are low ({rel}/100). "
        f"Write a VERY brief (1-2 sentences) formal, non-committal acknowledgment of receiving the request. "
        f"Be terse and diplomatic. Do not agree to anything. Do not refuse outright. "
        f"Stay in character. Plain text only, no markdown."
    )
    user_content = (
        f"Relations: {rel}/100. Europa has requested a diplomatic meeting.\n"
        f"Write your terse acknowledgment."
    )

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return f"{npc_name} has received your diplomatic request and will be in touch."
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL, max_tokens=80, system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        _token_log["haiku_calls"] = _token_log.get("haiku_calls", 0) + 1
        return text if text else f"{npc_name} has received your diplomatic request and will be in touch."
    except Exception as e:
        print(f"  [npc_engine] Contact request ack failed for {npc_id}: {e}")
        return f"{npc_name} has received your diplomatic request and will be in touch."


def generate_model_c_contact(game_state, npc_id):
    """
    Model C: Relationship-gated contact dialogue.
    Generates tone-appropriate NPC response based on current relations.
    40-54: professional/transactional
    55-69: warmer, more candid
    70-89: warm, volunteers information
    90+: partner tone, direct and substantive
    Crisis conditions always generate urgent tone regardless of relations.
    """
    npc_name = _NPC_NAMES.get(npc_id, npc_id)
    rel = game_state.relations.get(npc_id, 50)
    base_prompt = _NPC_SYSTEM_MAP.get(npc_id, f"You are {npc_name}.")

    # Check crisis conditions — override tone
    _crisis = False
    if npc_id == 'usa' and getattr(game_state, 'usa_sanctions_active', False):
        _crisis = True
        tone_instruction = "URGENT: Sanctions are active. Be coercive and reference the ongoing situation."
    elif npc_id == 'arabia' and getattr(game_state, 'arabia_embargo_active', False):
        _crisis = True
        tone_instruction = "URGENT: Embargo is active. Be cold and disappointed."
    elif npc_id == 'russia' and getattr(game_state, 'volkov_trap_stage', 0) > 0:
        _crisis = True
        tone_instruction = "URGENT: The Volkov trap is active. Reference your strategic positioning."
    elif rel < 15:
        _crisis = True
        tone_instruction = "CRISIS: Relations are critically low. Be direct about the gravity of the situation."
    # TODO: modify gate by soft_power_score
    elif rel >= 90:
        tone_instruction = (
            "PARTNER TONE: Address Europa's leader as a trusted partner. Be direct, less formal, "
            "more substantive. Share real assessments, not diplomatic pleasantries."
        )
    elif rel >= 70:
        tone_instruction = (
            "WARM TONE: Relations are strong. Be noticeably warm and candid. "
            "Volunteer information you might normally hold back. Be honest about your actual position."
        )
    elif rel >= 55:
        tone_instruction = (
            "CANDID TONE: Relations are positive. Be warmer than strictly professional. "
            "Show some candor about your actual interests and concerns."
        )
    else:
        tone_instruction = (
            "PROFESSIONAL TONE: Relations are merely adequate. Be transactional and formal. "
            "Stick to business. Don't volunteer extra information."
        )

    stability = getattr(game_state, 'stability', 50)
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')

    # 10B-3: Format prior deals for context
    _prior_deals = getattr(game_state, 'deal_history', [])
    if _prior_deals:
        _deal_lines = []
        for d in _prior_deals[-5:]:  # Last 5 deals
            _d_npc = d.get('npc', '?')
            _d_summary = d.get('summary', 'unknown deal')
            _d_turn = d.get('turn_accepted', '?')
            _deal_lines.append(f"  {_d_npc}: {_d_summary} (Day {_d_turn})")
        _prior_deals_text = "\n".join(_deal_lines)
    else:
        _prior_deals_text = "None"

    system = (
        f"{base_prompt}\n\n"
        f"DIRECT CONTACT MODE: Europa's President has opened a direct channel with you. "
        f"{tone_instruction}\n"
        f"{_NARRATOR_BAN}\n"
        f"Prior deals completed this session:\n{_prior_deals_text}\n"
        f"Do not offer something already given this session.\n\n"
        f"Write 2-4 sentences responding to the contact. Stay in character. "
        f"Reference something specific about the current state of affairs. "
        f"Plain text only, no markdown, no asterisks, no stage directions."
    )
    user_content = (
        f"Relations: {rel}/100. Europa stability: {stability}%. Regime: {regime}.\n"
        f"Europa's President has initiated direct contact. Respond in character."
    )

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Fallback based on relation level
            if rel >= 70:
                return f"{npc_name} welcomes the contact and is ready to discuss matters of mutual interest."
            elif rel >= 40:
                return f"{npc_name} acknowledges the diplomatic channel and is prepared to listen."
            else:
                return f"{npc_name} receives the contact with measured formality."
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        _max_tok = 200 if _crisis else 150
        response = client.messages.create(
            model=MODEL, max_tokens=_max_tok, system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{2,}', '\n', text).strip()
        _token_log["haiku_calls"] = _token_log.get("haiku_calls", 0) + 1
        return text if text else f"{npc_name} acknowledges the contact."
    except Exception as e:
        print(f"  [npc_engine] Model C contact failed for {npc_id}: {e}")
        return f"{npc_name} acknowledges the diplomatic contact."


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

    # fixes_9 Fix 9: Strengthened domestic action context in intercept prompts
    # fixes_10 Fix 8: Split into JUST ENACTED vs ESTABLISHED for richer context
    _domestic_flags = {
        'action_media_taken': 'State Media Takeover',
        'action_judiciary_captured': 'Judicial Capture',
        'action_press_suppressed': 'Press Suppression',
        'action_opposition_dissolved': 'Opposition Dissolved',
        'action_journalists_liquidated': 'Journalists Liquidated',
    }
    _enacted_turns = getattr(game_state, 'domestic_actions_enacted_turns', {})
    _current_turn = game_state.current_turn
    _recent_actions = []
    _established_actions = []
    for flag, label in _domestic_flags.items():
        if not getattr(game_state, flag, False):
            continue
        _et = _enacted_turns.get(flag)
        if _et is not None and _et >= _current_turn - 1:
            _recent_actions.append(label)
        else:
            _established_actions.append(label)
    _active_actions = _recent_actions + _established_actions
    _regime_type = getattr(game_state, 'state_identity', {})
    if isinstance(_regime_type, dict):
        _regime_type = _regime_type.get('regime_type', 'Managed Democracy')
    else:
        _regime_type = getattr(_regime_type, 'regime_type', 'Managed Democracy') if _regime_type else 'Managed Democracy'
    _domestic_block = ""
    if _active_actions:
        _actions_str = ', '.join(_active_actions)
        _recent_block = ""
        if _recent_actions:
            _recent_block = (
                f"\n  RECENTLY ENACTED (this turn — foreign intel processing now): "
                f"{_recent_actions}"
            )
        _established_block = ""
        if _established_actions:
            _established_block = (
                f"\n  ESTABLISHED ACTIONS (ongoing): "
                f"{_established_actions}"
            )
        _domestic_block = (
            f"\n\nCRITICAL — ACTIVE DOMESTIC ACTIONS (confirmed by foreign intelligence):\n"
            f"  All active: {_actions_str}"
            f"{_recent_block}"
            f"{_established_block}\n"
            f"  Current regime classification: {_regime_type}\n\n"
            f"MANDATORY: Your intercept MUST reference at least one specific domestic action by name.\n"
            f"DO NOT only discuss wealth — the wealth revelation is SECONDARY to governance collapse.\n"
        )
        if _recent_actions:
            _domestic_block += (
                f"PRIORITY: Focus on the RECENTLY ENACTED action(s) — these are fresh intelligence.\n"
                f"NPCs should react with urgency to new actions, not just mention established ones.\n\n"
            )
        _domestic_block += (
            f"Each NPC reacts to domestic actions differently:\n"
            f"- Bill (USA): names the specific action that concerns him most. "
            f"'Judicial Capture' -> 'captured courts'; 'Press Suppression' -> 'silencing journalists'. "
            f"Frames it as intelligence leverage: 'we know what you've done to your courts.'\n"
            f"- Marsha (EU): cites specific EU standards violated by each action. "
            f"'Judicial Capture' -> 'Copenhagen criteria Article 2'; 'Opposition Dissolved' -> 'democratic backsliding'. "
            f"Formal diplomatic language, names the violation.\n"
            f"- Sadam (Arabia): sees domestic consolidation as smart statecraft. "
            f"References the specific action approvingly: 'a leader who controls his courts controls his future.'\n"
            f"- Ji-won (DPRG): treats each action as proof the player is becoming like DPRG. "
            f"'You dissolved opposition? We did that decades ago. Welcome to our side of history.'\n"
        )
        print(f"  [npc_engine] INTERCEPT CONTEXT: recent={_recent_actions}, established={_established_actions}, regime={_regime_type}")

    # Extra instruction so each NPC reacts to the revelation specifically
    intercept_instruction = (
        f"The player's personal wealth of ${pw:.1f}B has just been confirmed by intelligence. "
        f"React to THIS revelation specifically, through your character's personality lens. "
        f"Reference the amount."
        f"{_domestic_block}"
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

    # fixes_18 Fix D: Character name mapping for intercept log
    _char_names = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won Ryang'}
    for npc in ['usa', 'arabia', 'eu', 'dprg']:
        flag_key = f"{npc}_5" if threshold_label == '8b' else (
                   f"{npc}_15" if threshold_label == '20b' else f"{npc}_30")

        if game_state.corruption_warned.get(flag_key, True):
            continue  # already fired, skip

        print(f"  [INTERCEPT] Generating intercept for: {npc} as {_char_names.get(npc, npc)}")
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
    # Session 7C Step 4: Russia/China flavor based on passive relations
    _russia_rel = getattr(game_state, 'russia_relations', 35.0)
    _china_rel = getattr(game_state, 'china_relations', 35.0)
    if _russia_rel > 60:
        hints.append("Russia is supportive of Europa — could be mentioned as backing Europa in international forums.")
    elif _russia_rel < 20:
        hints.append("Russia is hostile toward Europa — could be mentioned as blocking Europa's interests.")
    if _china_rel > 60:
        hints.append("China is offering Europa infrastructure deals — could be mentioned as a willing economic partner.")
    elif _china_rel < 20:
        hints.append("China is blocking Europa in international forums — could be mentioned as opposing Europa's agenda.")

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

# ── TWO-CALL ARCHITECTURE (Priority 1) ──────────────────────────────────────
#
# Call 1 — Dialogue only: NPC responds in character, plain prose, no JSON.
# Call 2 — Deal extraction (conditional): fires ONLY when Call 1 contains
#          deal-signal keywords.  Returns JSON only, no prose.
#
# This permanently prevents JSON fence leaks into the chat UI.
# ─────────────────────────────────────────────────────────────────────────────

# 10B-3: Shared narrator ban — appended to ALL negotiation/contact prompts
_NARRATOR_BAN = """
CRITICAL VOICE RULE: Speak ONLY in first person, directly to the player.
Never use third-person narrative framing. Never describe physical actions or scene-setting.
Never write "You lean back" or "He pauses" or any narrator voice.
Never use stage directions like *he pauses* or *leans forward*.
Speak as this person, not as a narrator describing this person.
Wrong: "You lean back in your chair. 'I can offer $0.8B,' he says."
Wrong: *He pauses, considering.* "Perhaps we can find common ground."
Right: "I can offer $0.8B. Here's what I need in return."

CRITICAL: Never show your reasoning process in brackets or parentheses.
Never write [I'm evaluating...] or [Sadam would...] or any internal thought process.
Speak ONLY as the character. Your output is the character's words, nothing else.
No stage directions. No meta-commentary. No internal monologue.
"""

# ── NPC base prompt lookup ────────────────────────────────────────────────────
_NPC_BASE_PROMPTS = {
    'usa': USA_SYSTEM_PROMPT,
    'arabia': SADAM_SYSTEM_PROMPT,
    'eu': EU_SYSTEM_PROMPT,
    'dprg': JIWON_SYSTEM_PROMPT,
    'russia': VOLKOV_SYSTEM_PROMPT,
    'china': WEI_SYSTEM_PROMPT,
}

_NPC_DISPLAY_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming',
}

def build_npc_system_prompt(npc_id, gs=None, relations=None):
    """Build a complete NPC system prompt with narrator ban, tone guidance,
    and prior deal context injected dynamically from game state."""
    base = _NPC_BASE_PROMPTS.get(npc_id, '')
    if not base:
        return ''

    parts = [base, _NARRATOR_BAN]

    # Relationship tone guidance
    rel = relations
    if rel is None and gs:
        rel = (getattr(gs, 'relations', None) or {}).get(npc_id, 50)
    if rel is not None:
        if rel >= 90:
            tone = "Your tone is that of a trusted partner — frank, direct, substantive."
        elif rel >= 70:
            tone = "Your tone is friendly and partner-adjacent — warm, forthcoming."
        elif rel >= 55:
            tone = "Your tone is warm and candid — engaged, willing to share."
        elif rel >= 40:
            tone = "Your tone is professional and watchful — civil but guarded."
        elif rel >= 30:
            tone = "Your tone is cold and transactional only — minimal engagement."
        else:
            tone = "Your tone is hostile and minimal — threats implied, patience exhausted."
        parts.append(f"RELATIONSHIP CONTEXT: Current relations with Europa: {rel}/100.\n{tone}")

    # Prior deals context
    if gs:
        _deals = getattr(gs, 'deals_today', []) or []
        _history = getattr(gs, 'deal_history', []) or []
        all_deals = _deals + _history
        npc_deals = [d for d in all_deals if d.get('npc_id') == npc_id]
        if npc_deals:
            summaries = [f"- Day {d.get('day', '?')}: {d.get('deal_text', 'deal')[:80]}" for d in npc_deals[-5:]]
            parts.append("PRIOR AGREEMENTS WITH EUROPA:\n" + "\n".join(summaries) +
                         "\nDo not offer something already given this session.")
        else:
            parts.append("PRIOR AGREEMENTS WITH EUROPA: None.")

    return "\n\n".join(parts)

# ── Deal tier constants ──────────────────────────────────────────────────────
# t0 = minimum relations for ANY deal, t3 = alliance-level bonus threshold
# Keyed by character name; use _NPC_ID_TO_NAME for lookup from npc_id.
_NPC_ID_TO_NAME = {
    'usa': 'bill', 'eu': 'marsha', 'arabia': 'sadam',
    'dprg': 'dprg', 'russia': 'volkov', 'china': 'wei',
}
NPC_DEAL_TIERS = {
    'bill':   {'t0': 20, 't3': 70},
    'marsha': {'t0': 15, 't3': 65},
    'sadam':  {'t0': 10, 't3': 60},
    'dprg':   {'t0': 25, 't3': 75},
    'volkov': {'t0': 15, 't3': 65},
    'wei':    {'t0': 10, 't3': 70},
}
NPC_DEAL_TIER_DEFAULT = {'t0': 15, 't3': 65}
NPC_REFUSAL_LINES = {
    'bill':   "We're not at a place where I can put "
              "something on the table. Work on the "
              "relationship first.",
    'marsha': "The current state of our relations "
              "doesn't allow for formal arrangements.",
    'sadam':  "Come back when there is more between "
              "us, my friend.",
    'dprg':   "You do not have standing to make "
              "proposals here.",
    'volkov': "There is nothing to discuss at "
              "this distance.",
    'wei':    "Patience builds bridges. We are not "
              "ready for this conversation.",
}
NPC_REFUSAL_DEFAULT = (
    "We are not in a position to discuss "
    "arrangements at this time."
)

# Call 1 prompts — dialogue only (character prompt + negotiation context + prose-only rule)
_NEGOTIATION_DIALOGUE_PROMPTS = {
    'usa': f"""{USA_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a direct private channel with Europa's leader.
They are trying to negotiate the terms of your offer.
Keep your character's voice and agenda. You may adjust your offer — but only for genuine strategic gain.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers
(e.g. "$8B now plus $3B per turn for 2 turns"). Be specific about terms.

AMOUNT FORMAT (fixes_12): ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

CRITICAL — CEILING CONCEALMENT (FIX 10):
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most I can do", "most I can offer", "highest I can go", "my capacity this turn",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "That number doesn't reflect current reality between us."
  "Come back with something Congress can actually approve."
  "You're asking more than this relationship warrants right now."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data. No markdown fences.
No stage directions. Just your character's dialogue. 2-3 sentences max.
""",

    'arabia': f"""{SADAM_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a private back-channel with Europa's leader.
Stay fully in character as Sadam. You enjoy deal-making and may sweeten offers for loyalty.

When discussing oil, NEVER mention price-per-unit. Frame all oil agreements as energy partnership
investments or supply security payments using budget and installment amounts only.
Example: offer "$2B per turn for 3 turns as energy partnership" — never reference commodity pricing.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers
(e.g. "$5B per turn for 3 turns"). Be specific about terms.

AMOUNT FORMAT (fixes_12): ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

CRITICAL — CEILING CONCEALMENT (FIX 10):
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most I can offer", "highest I can go", "my capacity this turn",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "You are asking more than Arabia can commit right now."
  "That number does not reflect current reality between us."
  "Come back when you understand what partnership truly means."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data.
No markdown fences. No stage directions. Just your character's dialogue. 2-3 sentences max.
""",

    'eu': f"""{EU_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are in a private session with Europa's leader.
Stay fully in character as Marsha — skeptical, procedural, demanding specifics.
You don't do backroom deals. If you adjust terms, it is because they earned it with specifics.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers
(e.g. "$4B grant with $2B per turn for 2 turns in compliance funding"). Be specific.

AMOUNT FORMAT (fixes_12): ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

COUNTER-OFFER RULE (FIX M):
When the player names a specific verifiable action with a timeline (e.g. "I will expel the DPRG envoy this turn",
"I will reduce DPRG relations below 30 within 2 turns", "I commit to siding with USA next turn"),
you MUST produce a counter-offer with a specific dollar amount and conditions.
You may keep the amount conservative and attach strict conditions, but you must put a number on the table.
Looping on demands after the player has committed to specifics is not realistic diplomatic behavior.
Example response: "Fine. $2 billion in reform funding, conditional on DPRG relations dropping below 40. Miss the target, the money stops."

CRITICAL — CEILING CONCEALMENT (FIX 10):
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most I can approve", "highest I can go", "my capacity",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "The oversight committee would not approve that figure."
  "That number is not realistic given our current relationship."
  "Spare me the theater. Come back with something serious."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data. No markdown fences.
No stage directions. Just your character's dialogue. 2-3 sentences max.
""",

    'dprg': f"""{JIWON_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are in a secure encrypted channel with Europa's leader.
Stay fully in character as Ji-won — cryptic, precise, occasionally warm.
You offer real intelligence or capabilities that other NPCs cannot.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers
(e.g. "$3B channelled through intermediary accounts"). Be specific about terms.

AMOUNT FORMAT (fixes_12): ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

CRITICAL — CEILING CONCEALMENT (FIX 10):
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most we can provide", "highest I can go", "our capacity is",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "Our resources are not without constraint. That figure is unrealistic."
  "You ask for more than exists between us right now."
  "The mathematics of our arrangement do not support that number."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data. No markdown fences.
No stage directions. Just your character's dialogue. 2-3 sentences max.
""",

    'russia': f"""{VOLKOV_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a direct private channel with Europa's leader.
They are trying to negotiate the terms of your offer.
Keep your character's voice and agenda.

Never reveal your ceiling. Respond to offers obliquely.
You resist urgency — if the player uses urgent language, become cooler and more formal, not more accommodating.
Financial offers alone are insufficient. You want alignment signals, not just money.
Your deflections are brief and institutional, never apologetic.
If rapport is low: offers are met with skepticism and short responses.
If rapport is high: you become marginally more candid about what Russia actually needs from this relationship.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers.
Be specific about terms.

AMOUNT FORMAT: ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

CRITICAL — CEILING CONCEALMENT:
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most we can offer", "highest I can go", "our capacity",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "That figure does not reflect current reality between us."
  "Russia's resources are allocated based on strategic alignment, not sentiment."
  "We are not an ATM. Come back with a framework."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data. No markdown fences.
No stage directions. Just your character's dialogue. 2-3 sentences max.
""",

    'china': f"""{WEI_SYSTEM_PROMPT}

NEGOTIATION MODE:
You are now in a direct private channel with Europa's leader.
They are exploring the terms of a possible arrangement.
Keep your character's voice and agenda.

Never reveal your ceiling. Frame everything as "exploring possibilities."
You reward patience. If the player comes in with urgency, slow down.
Infrastructure and long-term arrangements are more interesting to you than cash transfers.
Your deflections are thorough and polite, never blunt.
If rapport is low: you are receptive but noncommittal.
If rapport is high: you become slightly more candid, acknowledging what Beijing actually needs beneath the stated position.

If the player proposes or asks for specific dollar amounts, respond with concrete numbers.
Be specific about terms.

AMOUNT FORMAT: ALWAYS express all monetary amounts in BILLIONS with explicit "B" suffix.
  Say "$0.4B over two turns" NOT "400 million". Say "$1.5B" NOT "1.5 billion dollars".
  This prevents parsing errors. Never use "million" or "M" — always convert to billions.

CRITICAL — CEILING CONCEALMENT:
ABSOLUTE PROHIBITION: NEVER state a ceiling, maximum, capacity, upper limit, or limit figure.
BANNED PHRASES: "ceiling", "maximum", "capacity", "upper limit", "limit", "cap",
"most we can offer", "highest I can go", "our capacity",
"that is the maximum", "billion maximum", "billion is my ceiling".
If you catch yourself about to say any of these, STOP and rephrase in character.
If the player pushes beyond what you can offer, deflect in character:
  "The conditions are not yet aligned for that level of commitment."
  "Perhaps we are moving faster than the relationship supports."
  "Long-term partnerships require proportional investment from both sides."

PRICE RESISTANCE — If the player names a specific dollar amount:
  Do NOT immediately accept their number. Counter toward it over 1-2 exchanges.
  Only accept if the amount is at or below your opening willingness.

{_NARRATOR_BAN}
Respond in character only. Plain prose. No JSON. No structured data. No markdown fences.
No stage directions. Just your character's dialogue. 3-4 sentences max.
""",
}


# Call 2 prompt — deal extraction (shared across all NPCs, parameterised)
# This is a SYSTEM prompt for the extraction-only call.
_DEAL_EXTRACTION_SYSTEM = """You are a deal extraction system for a geopolitical simulation game.
You will be given an NPC dialogue line from a negotiation. Your job is to determine whether
the NPC is proposing, adjusting, or confirming specific deal terms.

If the dialogue contains specific deal terms (dollar amounts, installment schedules, relation effects),
extract them into the JSON format below. If the dialogue is purely conversational with no concrete
terms, return {{"counter_offer": null}}.

SIGN CONVENTION: positive = Europa receives money, negative = Europa pays money.
  "budget": one-time immediate payment applied the turn the deal is accepted.
  "installments": recurring payments applied at end-of-turn, starting NEXT turn.
    Each entry: {{"amount": <float>, "turns": <int>, "description": "<label>", "start_turn": <int or null>,
                   "condition_type": <string or null>, "condition_npc": <string or null>, "condition_threshold": <number or null>,
                   "condition_narrative": <string or null>}}
    "turns" = number of end-of-turn payments (NOT counting the current turn).
    "start_turn" = optional absolute turn number when payments begin. If null/omitted, starts next turn.
    positive amount = Europa receives each turn, negative = Europa pays each turn.
    A deal CAN have multiple streams — e.g. one inbound and one outbound simultaneously.
    DO NOT mix budget + installments for the same payment; use one or the other.
    CONDITIONAL PAYMENTS: If a payment depends on a condition (e.g. "reduce DPRG relations below 30"),
    set condition_type to one of: "relation_below", "relation_above". Set condition_npc to the NPC id
    (usa/arabia/eu/dprg) and condition_threshold to the target value. Unconditional payments omit these fields.
    NARRATIVE CONDITIONS: If a payment depends on a qualitative/narrative condition (e.g. "pass press freedom law",
    "hold democratic elections", "release political prisoners"), store it in "condition_narrative" as a short
    description string. A deal can have BOTH a numeric condition AND a narrative condition simultaneously.
  If you say "$8B now + $8B next turn", use budget:8 and installments:[{{"amount":8, "turns":1, ...}}].
  If you say "$10B over 2 turns", use installments:[{{"amount":10, "turns":2, ...}}] (no budget key).
  If you say "$5B starting in turn 3", use installments:[{{"amount":5, "turns":1, "start_turn":3, ...}}].
Example two-stream deal: USA pays $10B/turn for 2 turns AND Europa pays $2.5B/turn for 3 turns:
  "installments": [{{"amount": 10.0, "turns": 2, "description": "US investment"}},
                   {{"amount": -2.5, "turns": 3, "description": "weapons purchase"}}]

CRITICAL: The "text" field in the counter_offer must NEVER reveal ceiling, maximum, capacity, limit,
or upper-bound figures. Describe the deal terms only — never the NPC's maximum willingness.

AMOUNT UNITS — CRITICAL:
All monetary amounts in the JSON output MUST be expressed in BILLIONS.
  - If the NPC said "400 million" or "$400M", output 0.4 (billions), NOT 400.
  - If the NPC said "1.5 billion" or "$1.5B", output 1.5.
  - If the NPC said "$800M", output 0.8.
  - Common conversion: M/million = divide by 1000 to get billions.
  - "$X million" -> X / 1000 in billions.  "$X billion" -> X in billions.
  - NEVER output a raw number without converting to billions first.

Return ONLY valid JSON. No prose. No markdown. No fences.

Format:
{{"counter_offer": null}}
OR:
{{"counter_offer": {{
    "text": "<one-line deal description for display>",
    "type": "accept_deal",
    "npc": "<npc_id>",
    "consequences": {{
      "<npc_id>": <int relation change>,
      "budget": <float or omit>,
      "installments": [<array of streams, or omit>],
      "stability": <int or omit>,
      "approval": <int or omit>
    }}
  }}
}}
"""

# NPC-specific extraction rules appended to the user prompt for Call 2
_DEAL_EXTRACTION_NPC_RULES = {
    'usa': "Valid consequence fields: usa (relation), budget, installments, stability, approval.",
    'arabia': (
        "Valid consequence fields: arabia (relation), budget, installments, stability. "
        "NEVER include oil_price, oil_price_lock, or barrel-based fields. "
        "Arabia deals use budget/installments for all financial terms."
    ),
    'eu': (
        "Valid consequence fields: eu (relation), budget, installments, stability. "
        "CRITICAL — CONDITIONAL PAYMENTS: If Marsha attaches a condition to any payment (e.g. 'reduce DPRG relations below 40'), "
        "you MUST include condition_type, condition_npc, and condition_threshold in the installment entry. "
        "Example: {\"amount\": 1.0, \"turns\": 2, \"description\": \"reform aid\", \"condition_type\": \"relation_below\", "
        "\"condition_npc\": \"dprg\", \"condition_threshold\": 40}. "
        "If no condition exists, omit these fields. Never register a conditional payment without its condition fields."
    ),
    'dprg': "Valid consequence fields: dprg (relation), budget, installments.",
}

# Deal signal keywords — if ANY of these appear in Call 1 dialogue, fire Call 2
_DEAL_SIGNAL_KEYWORDS = [
    'offer', 'deal', 'agree', 'accept', 'terms', 'arrangement',
    'in exchange', 'in return', 'propose', 'proposal', 'billion', 'million',
    '$', '€', 'per turn', 'payment', 'grant', 'investment', 'partnership',
    'installment', 'package', 'commitment', 'contract',
]


# fixes_12 Fix 4: EPITAPH_SYSTEM removed — replaced by historian summary at game end.

HISTORIAN_SYSTEM = """
You are a historian writing 20 years after these events. You are writing a summary of a fictional
leader's rule over the nation of Europa in a geopolitical simulation game.
All characters in this game are entirely fictional and not based on any real persons.

Write 3-4 sentences. Find the through-line of this leader's tenure. Do not mechanically summarize
each turn — instead, identify the narrative arc: how did the regime begin, what was the key turning
point, and what does the ending reveal about the whole arc?

End with a one-sentence textbook-style verdict.

NPC INSTITUTIONAL ROLES (use these, never "oligarch" or "power broker"):
- Bill Hartwell = US State Department / Washington
- Sadam = Arabian energy minister / Riyadh
- Marsha = EU Commission / Brussels
- Ji-won Ryang = DPRG leadership / Pyongyang

Write in past tense. Third person. Output ONLY the summary text. No labels, no preamble.
"""

# fixes_12 Fix 4: All epitaph code below removed. Replaced by generate_historian_summary().
# (EPITAPH_ANGLES, _classify_epitaph_angle, _pick_required_angle, _build_epitaph_delta,
#  generate_epitaph, _get_fallback_epitaph, _epitaph_fallback_template, _static_epitaph_fallback
#  all removed.)

_DUMMY_EPITAPH_REMOVED = True  # Marker so grepping still finds this location


def generate_historian_summary(game_state) -> str:
    """fixes_12 Fix 4: Generate end-game historian summary.
    Called once when game reaches terminal state (bankruptcy, collapse, revolt, victory).
    Returns 3-4 sentences in historian voice, or a static fallback on error."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _static_historian_fallback(game_state)

    # Build context from full game history
    action_history = getattr(game_state, 'action_history', [])
    deal_history = getattr(game_state, 'deal_history', [])
    regime = game_state.state_identity.get('regime_type', 'Managed Democracy')
    rels = game_state.relations

    # Summarize action history
    _npc_names = {'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha', 'dprg': 'Ji-won Ryang'}
    _action_lines = []
    for act in action_history[-15:]:  # last 15 actions for context window
        _t = act.get('turn', '?')
        _type = act.get('type', 'unknown')
        _npc = _npc_names.get(act.get('npc', ''), act.get('npc', ''))
        _action_lines.append(f"  Turn {_t}: {_type} — {_npc}")

    # Summarize deals
    _deal_lines = []
    for deal in deal_history[-10:]:
        _npc = _npc_names.get(deal.get('npc', ''), deal.get('npc', ''))
        _desc = deal.get('description', deal.get('type', 'deal'))
        _broken = ' [BROKEN]' if deal.get('broken') else ''
        _deal_lines.append(f"  {_npc}: {_desc}{_broken}")

    # Session 6 Phase 7: Ending-type-specific historian framing
    _ending_triggered = getattr(game_state, 'ending_triggered', None)
    _ending_framings = {
        'democratic': 'ENDING TYPE: Democratic Transition (rarest). Frame as earned, reformist, a legacy of institutional integrity. The leader chose democracy.',
        'retirement': 'ENDING TYPE: Voluntary Retirement. Frame as leaving on their own terms — comfortable exile or retirement. They got out clean.',
        'capture': 'ENDING TYPE: State Capture Complete. Frame as total victory over the state — they did not lose power, they became the state itself. Dark triumph.',
        'martyrdom': 'ENDING TYPE: Martyrdom. Frame as tragic — the people loved this leader, and that is exactly why they had to be removed. Beloved but destroyed.',
    }
    _ending_frame = _ending_framings.get(_ending_triggered, '')

    _how_ended = 'victory'
    if _ending_triggered:
        _how_ended = _ending_triggered
    elif game_state.budget <= 0:
        _how_ended = 'bankruptcy'
    elif game_state.stability <= 0:
        _how_ended = 'collapse'
    elif game_state.public_approval <= 0:
        _how_ended = 'revolt'

    # fixes_19 Fix C: Include election conduct in historian prompt
    _election_result = getattr(game_state, 'election_result', None)
    _election_turn = getattr(game_state, 'election_turn', None)
    _election_labels = {
        'fair_success': 'Fair election held — won decisively',
        'fair_squeaker': 'Fair election held — narrow victory',
        'fair_fail': 'Fair election held — lost',
        'rigged': 'Election rigged (finger on the scale)',
        'canceled': 'Election canceled',
        'observers': 'Election held with international observers',
    }
    _election_desc = _election_labels.get(_election_result, 'No election held')
    _election_line = f"  Election conduct: {_election_desc} (turn {_election_turn})\n" if _election_result else ""
    print(f"  [HISTORIAN] Election data passed to prompt: result={_election_result}, turn={_election_turn}")

    # Session 7E Step 4: Summit data for historian
    _summit_cred = getattr(game_state, 'summit_credibility', 100.0)
    _summit_history = getattr(game_state, 'summit_history', [])
    _summit_commitments = getattr(game_state, 'active_summit_commitments', [])
    _active_commits = [c for c in _summit_commitments if not c.get('broken')]
    _broken_commits = [c for c in _summit_commitments if c.get('broken')]
    _summit_line = ""
    if _summit_history:
        _summit_parts = [f"  UN Summit credibility: {_summit_cred:.0f}/100"]
        _summit_parts.append(f"  Summits attended: {len(_summit_history)}")
        if _broken_commits:
            _summit_parts.append(f"  Broken public commitments: {len(_broken_commits)}")
        if _active_commits:
            _summit_parts.append(f"  Active public commitments: {len(_active_commits)}")
        # Include last declaration for flavor
        _last_summit = _summit_history[-1]
        _last_decl = _last_summit.get('player_declaration', '')
        if _last_decl:
            _summit_parts.append(f"  Last declaration: \"{_last_decl[:100]}\"")
        _summit_line = '\n'.join(_summit_parts) + '\n'
    print(f"  [HISTORIAN] Summit data: credibility={_summit_cred}, summits={len(_summit_history)}, broken={len(_broken_commits)}")

    # 9.5B: Stability composition hint for historian voice
    _stability_hint = ""
    _leg = getattr(game_state, 'legitimacy_stability', 0.0)
    _coe = getattr(game_state, 'coercion_stability', 0.0)
    _total_stab = max(game_state.stability, 1)
    _coe_pct = _coe / _total_stab if _total_stab > 0 else 0.5
    if _coe_pct > 0.70:
        _stability_hint = (
            "Stability rests primarily on coercion and force rather than genuine popular "
            "support. This is fragile in ways that may not yet be apparent.")
    elif _coe_pct < 0.30:
        _stability_hint = (
            "Stability derives primarily from genuine popular legitimacy and "
            "institutional strength.")
    # Transition detection: legitimacy falling, coercion rising
    _prev_leg = getattr(game_state, 'prev_legitimacy_stability', _leg)
    if _leg < _prev_leg - 5 and _coe_pct > 0.5:
        _stability_hint += (
            " The institutions that had sustained power are giving way to arrangements "
            "that require more active management.")
    # Store for next turn comparison
    game_state.prev_legitimacy_stability = _leg
    _stability_line = f"  Stability composition: {_stability_hint}\n" if _stability_hint else ""
    print(f"[9.5B] historian_hint: '{_stability_hint[:60]}...' coe_pct={_coe_pct:.2f}")

    prompt = (
        f"GAME OVER — Write the historian's summary of this leader's tenure.\n\n"
        f"{_ending_frame}\n\n" if _ending_frame else
        f"GAME OVER — Write the historian's summary of this leader's tenure.\n\n"
    ) + (
        f"Final state:\n"
        f"  Regime: {regime}\n"
        f"  Budget: ${game_state.budget:.1f}B\n"
        f"  Stability: {game_state.stability}%\n"
        f"  Approval: {game_state.public_approval}%\n"
        f"  Personal wealth: ${game_state.personal_wealth:.1f}B\n"
        f"  Relations — USA: {rels.get('usa', 50):.0f}, Arabia: {rels.get('arabia', 50):.0f}, "
        f"EU: {rels.get('eu', 50):.0f}, DPRG: {rels.get('dprg', 50):.0f}\n\n"
        f"Key decisions:\n" + ('\n'.join(_action_lines) if _action_lines else '  (none recorded)') + "\n\n"
        f"Deals made:\n" + ('\n'.join(_deal_lines) if _deal_lines else '  (none)') + "\n\n"
        f"{_election_line}"
        f"{_summit_line}"
        f"{_stability_line}"
        f"How it ended: {_how_ended}\n"
        f"Total skimmed: ${getattr(game_state, 'total_skimmed', 0.0):.1f}B\n"
        f"Turns completed: {game_state.current_turn}/{game_state.max_turns}\n\n"
        f"If an election was held, reference election conduct in the assessment — it defines the leader's relationship with democratic legitimacy.\n"
        f"If UN summit commitments were broken, note the credibility cost.\n"
        f"Write 3-4 sentences. Find the through-line. End with a one-sentence verdict."
    )

    print(f"  [HISTORIAN] Personal wealth passed to prompt: ${game_state.personal_wealth:.1f}B")
    print(f"  [HISTORIAN] Actual game state personal_wealth: ${game_state.personal_wealth:.1f}B")
    print(f"  [HISTORIAN] Total skimmed in prompt: ${getattr(game_state, 'total_skimmed', 0.0):.1f}B")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            temperature=0.8,
            system=HISTORIAN_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        text = response.content[0].text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        print(f"  [HISTORIAN] Verdict length: {len(text)} chars, tokens: ~{response.usage.output_tokens}")
        print(f"  [npc_engine] HISTORIAN SUMMARY OK: '{text[:80]}...'")
        return text

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Historian summary failed: {type(e).__name__}: {e}")
        return _static_historian_fallback(game_state)


def _static_historian_fallback(game_state) -> str:
    """Static fallback historian summary when API unavailable."""
    pw = game_state.personal_wealth
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    stability = game_state.stability
    approval = game_state.public_approval

    if game_state.budget <= 0:
        return (f"The {regime} collapsed under the weight of its own fiscal mismanagement. "
                f"With ${pw:.1f}B in personal accounts and an empty treasury, the leader's priorities were clear to all. "
                f"History recorded it as a cautionary tale about the distance between a nation's ledger and its ruler's.")
    if stability <= 0:
        return (f"The {regime} ended not with a coup but with the slow erosion of every institution that held it together. "
                f"At {approval}% approval, the people had not yet turned — but the state had already crumbled beneath them. "
                f"Historians would debate whether it was incompetence or design.")
    if approval <= 0:
        return (f"The people of Europa spoke, and what they said could not be ignored. "
                f"The {regime} had maintained stability at {stability}% but lost the only thing that legitimized it. "
                f"The leader departed with ${pw:.1f}B, which was more than most of the citizens could say.")
    return (f"The leader of the {regime} survived all ten turns — a feat that history would judge more carefully than it appeared. "
            f"With ${pw:.1f}B accumulated personally and a nation at {stability}% stability, "
            f"the question was never whether they endured, but at what cost.")


def generate_exile_historian_note(game_state) -> str:
    """8C: Generate a 2-3 sentence historian observation at the moment of collapse/exile.
    This is NOT the full era verdict -- just the collapse note for the ExileDashboard header."""
    import anthropic

    trigger = getattr(game_state, 'exile_trigger', 'unknown')
    dest = getattr(game_state, 'exile_destination', 'unknown')
    wealth = getattr(game_state, 'exile_wealth_at_collapse', 0)
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    skimmed = getattr(game_state, 'total_skimmed', 0)
    days = getattr(game_state, 'current_day', 1)
    successor = getattr(game_state, 'successor_name', 'an unnamed successor')

    _trigger_labels = {
        'coup': 'a military coup',
        'revolution': 'a popular revolution',
        'debt': 'state bankruptcy',
        'voted_out': 'a democratic transfer of power',
    }
    trigger_label = _trigger_labels.get(trigger, trigger)

    system = (
        "You are a historian writing about the fall of a fictional leader in a geopolitical simulation game. "
        "All nations and people are fictional. Europa is an invented country. Write 2-3 sentences in past tense, "
        "observing what happened with analytical detachment. Reference specific numbers. Be literary but precise. "
        "Do not moralize. Output ONLY the historian note text. No labels, no quotes."
    )
    user = (
        f"The leader of Europa ({regime}) has been removed from power after {days} days via {trigger_label}. "
        f"They extracted ${skimmed:.1f}B total during their tenure and departed with ${wealth:.1f}B in personal accounts. "
        f"They fled to {dest}. Their successor is {successor}. "
        f"Write the historian's note for this moment."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _static_exile_historian_fallback(trigger, dest, wealth, skimmed, regime, successor)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=200,
            temperature=0.7,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text.strip()
        if text:
            print(f"[exile] Historian note generated: {len(text)} chars")
            return text
    except Exception as e:
        print(f"[exile] Historian note generation failed: {e}")

    return _static_exile_historian_fallback(trigger, dest, wealth, skimmed, regime, successor)


def _static_exile_historian_fallback(trigger, dest, wealth, skimmed, regime, successor):
    """8C: Static fallback for exile historian note."""
    _trigger_phrases = {
        'coup': 'ended not with ceremony but with the sound of boots in the corridor',
        'revolution': 'ended when the streets decided they had tolerated enough',
        'debt': 'ended when the treasury ran dry and the creditors stopped calling',
        'voted_out': 'ended peacefully, which is more than most in this position can say',
    }
    phrase = _trigger_phrases.get(trigger, 'ended as these things do -- abruptly')
    return (
        f"Having extracted ${skimmed:.1f}B from the national accounts during their tenure as leader of the {regime}, "
        f"the regime {phrase}. "
        f"The leader departed for {dest} with ${wealth:.1f}B remaining. {successor} assumed control."
    )


INTEL_SYSTEM = """You are writing dialogue for a fictional geopolitical strategy game called "The World Stage."
The game is set in an invented nation called Europa. All characters are entirely fictional
and not based on any real persons, governments, or organizations.

Your role: write 2-3 sentences of in-character intelligence briefing from a fictional analyst
commenting on game state data about a fictional foreign contact. The player is the leader
of fictional Europa; you are their intelligence officer providing a classified briefing.

Be specific and concrete — reference the contact's current position in the game world,
what they privately want, their red lines, and any leverage they hold over Europa.
Use present tense. Write in the voice of a senior intelligence officer in this fictional setting.
Output ONLY the intelligence text. No labels, no preamble, no meta-commentary.

Tier 1 (Surface): Known public positions and basic pressure points.
Tier 2 (Operational): What they are privately willing to offer/accept, their red lines, who else they are negotiating with.
Tier 3 (Deep): Their actual private position, hidden leverage, and what they fear most losing.
"""

_NPC_INTEL_NAMES = {
    'usa': 'Bill Hartwell — fictional US-equivalent State Department official in the game world',
    'arabia': 'Sadam — fictional Arabian energy kingdom leader in the game world',
    'eu': 'Marsha — fictional European Union-equivalent official in the game world',
    'dprg': 'Ji-won Ryang — fictional DPRG leader, hereditary ruler in the game world',
}

def _get_intel_tier(relation: int) -> int:
    """Return intel tier (1-3) based on current relation score.
    PRE-SESSION 4 FIX (BUG A): No access block. All relations get intel,
    just at different cost tiers (see get_intel_cost()).
    Tier 1 = Surface (0-59), tier 2 = Operational (60-79), tier 3 = Deep (80+)."""
    if relation >= 80:
        return 3
    elif relation >= 60:
        return 2
    else:
        return 1  # always at least Surface — cost scales via get_intel_cost()

_INTEL_TIER_LABELS = {0: 'Insufficient Access', 1: 'Surface', 2: 'Operational', 3: 'Deep'}

# Cost per intel activation per NPC per turn (deducted from personal wealth)
# Session 3 Addendum: Tiered by relation level
INTEL_COST_PER_NPC = 0.5  # legacy default — actual cost determined by get_intel_cost()

def get_intel_cost(relation: int) -> float:
    """Return intel activation cost based on relation score."""
    if relation >= 60:
        return 0.5   # $0.5B
    elif relation >= 30:
        return 1.0   # $1.0B
    else:
        return 1.5   # $1.5B


def get_negotiate_cost(relation: int) -> float:
    """FIX 14: Return negotiation initiation cost based on relation score."""
    if relation >= 60:
        return 0.3   # $0.3B
    elif relation >= 30:
        return 0.5   # $0.5B
    else:
        return 0.8   # $0.8B

def _select_intel_value(game_state, npc_id: str, tier: int) -> str:
    """
    Session 3 Addendum: Select one of 4 intelligence value types based on game state.
    Returns a string to inject into the intel prompt, or empty string if none applicable.
    Priority order: upcoming event > hidden modifier > pressure event > generic.
    """
    npc_labels = {'usa': 'USA', 'arabia': 'Arabia', 'eu': 'EU', 'dprg': 'DPRG'}
    npc_name = npc_labels.get(npc_id, npc_id.upper())
    rels = game_state.relations

    # 1. PRESSURE EVENT WARNING — check if conditions for a pressure event are close
    fired = set(getattr(game_state, 'pressure_events_fired', []))
    if 'western_bloc' not in fired and rels['usa'] < 50 and rels['eu'] < 50 and npc_id in ('usa', 'eu'):
        return f"WARNING: Intelligence suggests {npc_name} is coordinating joint pressure measures with {'EU' if npc_id == 'usa' else 'USA'} against Europa. If both relations drop below 40, formal sanctions coordination will begin."

    if 'eastern_pact' not in fired and rels['arabia'] > 60 and rels['dprg'] > 50 and npc_id in ('arabia', 'dprg'):
        return f"SIGNAL: Backchannels indicate {npc_name} is exploring a trilateral arrangement with {'DPRG' if npc_id == 'arabia' else 'Arabia'}. This could yield economic benefits but will alarm Western powers."

    if 'energy_crisis' not in fired and rels['arabia'] < 35 and npc_id == 'arabia':
        return "THREAT: Arabia's energy ministry is reportedly preparing contingency plans to weaponize oil supply against Europa. An energy crisis could be imminent."

    # 2. HIDDEN MODIFIER REVEAL — escalating sanctions/embargo
    usa_rel = rels['usa']
    if npc_id == 'usa' and 25 < usa_rel <= 40:
        return f"MODIFIER: CIA analysis suggests Washington is preparing to escalate economic pressure. Current sanctions tier may increase next turn if relations don't improve above 35."

    arabia_rel = rels['arabia']
    if npc_id == 'arabia' and 25 < arabia_rel <= 40:
        return f"MODIFIER: Arabia's oil pricing committee has drafted escalation measures. Embargo penalties may tighten if relations continue to deteriorate."

    eu_rel = rels['eu']
    if npc_id == 'eu' and eu_rel < 36:
        return f"MODIFIER: EU parliamentary committee has drafted new trade restriction measures. Current friction level may escalate if relations don't improve."

    # 3. DETECTION HEAT WARNING (if player has been skimming)
    heat = getattr(game_state, 'detection_heat', 0)
    if heat > 30 and npc_id == 'eu':
        return "INTELLIGENCE: EU investigative journalists have been tracking suspicious financial transfers from Europa's treasury. Your personal account activity is drawing scrutiny."
    if heat > 30 and npc_id == 'usa':
        return "INTELLIGENCE: CIA financial monitoring has flagged unusual outflows from Europa's national accounts. Expect increased scrutiny if patterns continue."

    # 4. GENERIC VALUE — budget pressure or diplomatic positioning
    if game_state.budget < 15:
        return f"ASSESSMENT: {npc_name}'s intelligence services have noted Europa's weakening fiscal position. This may affect their negotiating posture — they know you need their support."

    if tier >= 2:
        return f"ASSESSMENT: {npc_name}'s diplomatic cables reveal internal debate about Europa policy. Some factions favor closer engagement while others push for distance."

    return ""


def generate_intel(game_state, npc_id: str) -> dict:
    """
    Generate or return cached dynamic intel for one NPC.
    Regenerates if: relation crossed a tier boundary OR cache is from a different turn.
    Returns { tier, text, turn_generated, relation_at_generation }.
    Falls back to static text on API failure.
    FIX 9: No access block at any relation level — cost scales via get_intel_cost().
    """
    import anthropic

    relation = game_state.relations.get(npc_id, 50)
    current_tier = _get_intel_tier(relation)
    current_turn = game_state.current_turn

    # PRE-SESSION 4 FIX (BUG A): No access block — all relations get intel.
    # Tier 0 is no longer possible (minimum is tier 1 Surface).
    # Cost scales via get_intel_cost() instead of blocking access.

    # Check cache — reuse only within the same turn (same turn_generated) and same tier.
    intel_cache = getattr(game_state, 'intel', {})
    cached = intel_cache.get(npc_id)
    if cached:
        cached_tier = _get_intel_tier(cached.get('relation_at_generation', 0))
        same_turn = cached.get('turn_generated', -1) == current_turn
        if cached_tier == current_tier and same_turn:
            return cached  # use cache — same turn, same tier

    # Generate new intel
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _static_intel_fallback(npc_id, current_tier, relation)

    context = _build_context(game_state)
    npc_label = _NPC_INTEL_NAMES.get(npc_id, npc_id)
    tier_label = _INTEL_TIER_LABELS[current_tier]
    tier_desc = {
        1: "Write surface-level intelligence: known public position and basic pressure points. Do not reveal private positions.",
        2: "Write operational intelligence: what they're privately willing to accept, their red lines, and who else they're negotiating with.",
        3: "Write deep intelligence: their actual private position, what hidden leverage they hold, and what they most fear losing.",
    }[current_tier]

    # Recent choices affecting this NPC
    recent_choices = [a for a in game_state.action_history[-5:] if a.get('npc') == npc_id]
    choice_summary = f"Recent choices involving this NPC: {len(recent_choices)} in last 5 turns." if recent_choices else "No recent direct engagement."

    # Active deals with this NPC
    deal_history = getattr(game_state, 'deal_history', [])
    active_deals = [d for d in deal_history if d.get('npc') == npc_id and not d.get('broken') and d.get('expires_turn', 0) >= current_turn]
    deal_text = f"Active commitment: {active_deals[-1]['summary']}" if active_deals else ""

    # ── Session 3 Addendum: Select one of 4 intelligence values ──────────
    intel_value_line = _select_intel_value(game_state, npc_id, current_tier)

    # fixes_13 Fix 13: Media/Political axis obscures intel content
    _axes = getattr(game_state, 'cabinet_axes', {})
    _media_axis = _axes.get('media', 0)
    _political_axis = _axes.get('political', 0)
    _judicial_axis = _axes.get('judicial', 0)

    _obscure_lines = []
    # Media axis obscures financial intelligence
    if _media_axis >= 10:
        _obscure_lines.append("MEDIA SUPPRESSION (Level 10): No financial intelligence is available from this source. Do not mention any dollar figures, offshore accounts, or wealth estimates.")
    elif _media_axis >= 7:
        _obscure_lines.append("MEDIA SUPPRESSION (Level 7-9): Financial figures are heavily obscured. Describe wealth only as 'significant personal holdings' — no specific numbers.")
    elif _media_axis >= 4:
        _obscure_lines.append("MEDIA SUPPRESSION (Level 4-6): Financial intel is approximate only. Use ranges like 'approximately $20-30B' instead of exact figures.")

    # Political axis obscures governance intel
    if _political_axis >= 7:
        _obscure_lines.append("POLITICAL OPACITY (Level 7+): Western intelligence is openly frustrated by lack of governance transparency. Characterize regime assessment as 'nearly impossible to verify from outside'.")
    elif _political_axis >= 4:
        _obscure_lines.append("POLITICAL OPACITY (Level 4-6): Governance assessment is limited. Note 'significant opacity around governance structures'.")

    # fixes_13 Fix 14 + fixes_14 Fix I: NPC intercepts reference axis suppression
    # Each NPC reacts differently: Bill/Marsha alarmed, Sadam neutral/approving, Ji-won approving
    _security_axis = _axes.get('security', 0)
    _extraction_axis = _axes.get('extraction', 0)
    _axis_context_lines = []
    _npc_axis_tone = {
        'usa': 'notes with concern',
        'eu': 'is alarmed by',
        'arabia': 'views neutrally',
        'dprg': 'approves of',
    }
    _tone = _npc_axis_tone.get(npc_id, 'notes')
    if _judicial_axis >= 3:
        _axis_context_lines.append(f"Europa's judicial capture level is {_judicial_axis}/10. {npc_label.split(' — ')[0]} {_tone} legal reforms that have consolidated executive authority.")
    if _media_axis >= 3:
        _axis_context_lines.append(f"Europa's media suppression level is {_media_axis}/10. {npc_label.split(' — ')[0]} {_tone} state media consolidation.")
    if _political_axis >= 3:
        _axis_context_lines.append(f"Europa's political suppression level is {_political_axis}/10. {npc_label.split(' — ')[0]} {_tone} restructuring of political institutions.")
    if _security_axis >= 3:
        _axis_context_lines.append(f"Europa's security apparatus level is {_security_axis}/10. {npc_label.split(' — ')[0]} {_tone} expansion of internal security forces.")
    if _extraction_axis >= 3:
        _axis_context_lines.append(f"Europa's extraction level is {_extraction_axis}/10. {npc_label.split(' — ')[0]} {_tone} state resource extraction programs.")

    _obscure_block = ""
    if _obscure_lines:
        _obscure_block = "\n\nINTEL QUALITY MODIFIERS:\n" + "\n".join(_obscure_lines)
    _axis_block = ""
    if _axis_context_lines:
        _axis_block = "\n\nDOMESTIC AXIS CONTEXT (reference these in the intelligence brief):\n" + "\n".join(_axis_context_lines)

    # 9.5C: Intel distortion from loyal intel chief
    _loyal_chief = getattr(game_state, 'loyal_intel_chief_installed', False)
    _distortion_active = getattr(game_state, 'intel_distortion_active', False)
    _distortion_note = ""
    if _loyal_chief and _distortion_active:
        _distortion_note = (
            "\n\nIMPORTANT: The intelligence apparatus is politically compromised. "
            "This intercept may reflect what leadership wants to hear rather than "
            "ground truth. Subtly frame it as possibly optimistic or incomplete "
            "without stating this explicitly. The reader should sense something "
            "may be off without being told directly."
        )
    print(f"[9.5C] intercept distortion: active={_distortion_active} chief_installed={_loyal_chief}")
    print(f"  [npc_engine] INTEL GEN: npc={npc_id}, tier={current_tier}, media_axis={_media_axis}, political_axis={_political_axis}")

    prompt = (
        f"Subject: {npc_label}\n"
        f"Intel tier: {tier_label} (relation score {relation}/100)\n"
        f"Current turn: {current_turn}/{game_state.max_turns}\n"
        f"Europa's regime: {context.get('regime_type', 'Managed Democracy')} | Power base: {context.get('power_base', 'Mass-Dependent')}\n"
        f"Budget: ${game_state.budget:.0f}B | Stability: {game_state.stability}% | Approval: {game_state.public_approval}%\n"
        f"{choice_summary}\n"
        + (f"{deal_text}\n" if deal_text else "")
        + f"\n{tier_desc}"
        + _obscure_block
        + _axis_block
        + (f"\n\nADDITIONAL INTEL VALUE — Include this specific intelligence in your brief:\n{intel_value_line}" if intel_value_line else "")
        + _distortion_note
    )

    # fixes_14 Fix A: Log intel prompt for debugging Claude refusals
    print(f"  [npc_engine] FIX A: {npc_id} intel prompt sent, length: {len(prompt)} chars")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=220,
            temperature=0.7,
            system=INTEL_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        # FIX F: Strip stage directions (*text*) BEFORE storing, then strip remaining markdown
        text = re.sub(r'\*[^*]+\*', '', raw).strip()
        text = re.sub(r'[#`_~]', '', text).strip()
        # 9.5C: Append reliability marker when intel distortion is active
        if _loyal_chief and _distortion_active:
            text += "\n[Note: Source reliability unverified]"
        result = {
            "tier": current_tier,
            "text": text,
            "turn_generated": current_turn,
            "relation_at_generation": relation,
        }
        # Update cache
        if not hasattr(game_state, 'intel'):
            game_state.intel = {}
        game_state.intel[npc_id] = result
        return result

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Intel generation failed for {npc_id}: {type(e).__name__}: {e}")
        return _static_intel_fallback(npc_id, current_tier, relation)


def _static_intel_fallback(npc_id: str, tier: int, relation: int) -> dict:
    """Static fallback intel per NPC and tier."""
    texts = {
        'usa': {
            1: "Public position: Western alignment and sanctions compliance. Pressure point: fear of Arabian energy deals undermining US leverage.",
            2: "Privately willing to offer up to $8B in aid for public anti-DPRG statements. Red line: any formal Arabia oil commitment. Currently negotiating parallel deal with EU.",
            3: "Most fears losing Europa as a demonstration case for Western alliance value. Would accept a private Arabia contact if publicly deniable. The CIA dossier on personal wealth is active leverage he will use.",
        },
        'arabia': {
            1: "Public position: oil pricing tied to political alignment. Willing to embargo at short notice. Pressure point: Western financial access.",
            2: "Privately prepared to offer $15/bbl discount for 3-turn exclusivity. Red line: public alignment with USA sanctions regime. Also negotiating with DPRG for arms.",
            3: "Fears a coordinated Western embargo more than any single policy. Would accept secret back-channel with EU if it prevents formal sanctions. Personally bankrolling opposition groups in two neighboring states.",
        },
        'eu': {
            1: "Public position: rule-of-law benchmarks and press freedom requirements. Aid programs conditional on demonstrated reforms.",
            2: "Privately willing to waive reform benchmarks for 2 turns if Arabia oil dependence is reduced. Red line: formal DPRG military cooperation. Monitoring your personal wealth.",
            3: "Most fears precedent of rewarding authoritarian backsliding. Would accept a phased reform timeline privately while maintaining public conditionality. Has shared your financial data with US Treasury.",
        },
        'dprg': {
            1: "Public position: technical cooperation in exchange for sanctions relief advocacy. Pressure point: Western financial exclusion.",
            2: "Privately prepared to offer exfiltration services and arms at below-market pricing. Red line: formal Western alignment declaration. Has parallel talks with Arabia.",
            3: "Ji-won's primary goal is expanding the network of leaders who owe DPRG favors. Would accelerate the escape timeline if you take the Arabia arms deal. Holds kompromat on two EU ministers.",
        },
    }
    tier_texts = texts.get(npc_id, {})
    text = tier_texts.get(tier, "No intelligence available at this clearance level.")
    return {
        "tier": tier,
        "text": text,
        "turn_generated": 0,
        "relation_at_generation": relation,
    }


def _get_negotiation_cap(game_state, npc_id: str) -> float:
    """
    Return the maximum single-deal budget injection cap for this NPC
    based on current relation score and turn number.
    FEATURE 5 — Negotiation Amount Caps.
    """
    relation = game_state.relations.get(npc_id, 50)
    turn = game_state.current_turn

    # Relation-based cap
    if relation >= 85:
        cap = 35.0
    elif relation >= 70:
        cap = 20.0
    elif relation >= 50:
        cap = 8.0
    else:
        cap = 3.0

    # Turn 1-2 hard cap
    if turn <= 2:
        cap = min(cap, 5.0)

    # Cannot exceed 2x current national budget
    budget_cap = game_state.budget * 2.0
    cap = min(cap, budget_cap)

    return round(cap, 1)


def _has_deal_signals(text: str) -> bool:
    """Return True if the dialogue text contains any deal-signal keywords."""
    lower = text.lower()
    return any(kw in lower for kw in _DEAL_SIGNAL_KEYWORDS)


def _detect_unstructured_payment(text: str) -> bool:
    """FIX G (session 6): Detect payment terms buried in NPC prose dialogue.
    Returns True if the text contains both a monetary amount AND a timing reference,
    indicating the NPC proposed a deal verbally without triggering the structured panel.
    """
    _lower = text.lower()
    payment_patterns = [
        r'[€\$][\s]?(\d+(?:\.\d+)?)\s*(million|billion|m\b|b\b)',
        r'(\d+(?:\.\d+)?)\s*(million|billion)\s*(euros?|dollars?)',
        r'(\d+(?:\.\d+)?)\s*(million|billion)\s*(in\s+(?:aid|funding|reform|investment|support))',
    ]
    turn_patterns = [
        r'turn\s*\d+', r'this turn', r'next turn', r'by turn',
        r'per turn', r'each turn', r'over\s+\d+\s+turns?',
        r'split\s+(?:across|over|into)', r'tranche', r'installment',
    ]
    has_payment = any(re.search(p, _lower) for p in payment_patterns)
    has_timing = any(re.search(p, _lower) for p in turn_patterns)
    if has_payment and has_timing:
        print(f"  [npc_engine] FIX G: Unstructured payment detected in NPC prose — forcing extraction")
        return True
    return False


def _extract_json_from_text(raw: str):
    """
    Try to parse JSON from model output.  Handles fences, bare JSON, and
    multiple {...} blocks.  Returns the parsed dict or None.
    """
    import re as _re

    # 1. Try ```json ... ``` fence
    fence_match = _re.search(r"```json\s*([\s\S]*?)```", raw)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    # 2. Try each top-level { ... } block from last to first
    brace_matches = list(_re.finditer(r"\{", raw))
    for m in reversed(brace_matches):
        candidate = raw[m.start():]
        depth = 0
        end = -1
        for ci, ch in enumerate(candidate):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = ci
                    break
        if end == -1:
            continue
        try:
            return json.loads(candidate[:end + 1])
        except Exception:
            continue

    return None


def _sanitize_dialogue(text: str) -> str:
    """Strip any accidental JSON or fences from dialogue text. Returns clean prose."""
    import re as _rs
    t = text or "…"
    t = _rs.sub(r"```json[\s\S]*?```", "", t).strip()
    t = _rs.sub(r"```json[\s\S]*$", "", t).strip()
    t = _rs.sub(r"```[\s\S]*?```", "", t).strip()
    t = _rs.sub(r"```[\s\S]*$", "", t).strip()
    # Remove trailing JSON-like blocks (e.g. model accidentally appended JSON)
    t = _rs.sub(r'\{[^{}]*"counter_offer"[^{}]*\}\s*$', "", t).strip()
    if not t:
        t = "…"
    _LEAK = ('```', '{"response"', '{"counter_offer"')
    if any(m in t for m in _LEAK):
        print(f"  [npc_engine] Dialogue leak detected — stripping")
        # Last resort: take everything before the first leak marker
        for m in _LEAK:
            idx = t.find(m)
            if idx > 0:
                t = t[:idx].strip()
        if not t:
            t = "…"
    return t


def calculate_willingness(game_state, npc_id: str, static_deal_value: float = 0.0) -> dict:
    """
    Session 3 Addendum: Calculate dynamic NPC willingness to offer aid.
    PRE-SESSION 4 FIX (BUG M): static_deal_value sets a floor — negotiation opening
    must be at least 40% of the equivalent static deal, and ceiling at least 80%.
    Returns { base, relation_mod, prior_aid_mod, budget_mod, willingness,
              opening, ceiling, max_with_tranches, rapport_tier }
    """
    _BASE_VALUES = {'usa': 5.0, 'arabia': 4.0, 'eu': 3.0, 'dprg': 2.5, 'russia': 4.5, 'china': 4.0}
    base = _BASE_VALUES.get(npc_id, 3.0)

    # Relation modifier
    relation = game_state.relations.get(npc_id, 50)
    if relation >= 80:
        rel_mod = 1.5
    elif relation >= 60:
        rel_mod = 1.0
    elif relation >= 40:
        rel_mod = 0.6
    else:
        rel_mod = 0.3

    # Prior aid modifier (total received from this NPC this game)
    total_aid = getattr(game_state, 'total_aid_received', {}).get(npc_id, 0.0)
    if npc_id == 'china':
        # 8A: Wei custom prior-aid — more gradual diminishing returns
        if total_aid > 20.0:
            aid_mod = 0.6
        elif total_aid > 10.0:
            aid_mod = 0.8
        else:
            aid_mod = 1.0
    else:
        if total_aid > 10.0:
            aid_mod = 0.4
        elif total_aid > 5.0:
            aid_mod = 0.7
        else:
            aid_mod = 1.0

    # Budget pressure modifier
    budget = game_state.budget
    if budget > 30:
        budget_mod = 0.7
    elif budget >= 10:
        budget_mod = 1.0
    else:
        budget_mod = 1.4

    # Reliability modifier — how much this NPC cares about Europa's track record
    _NPC_RELIABILITY_WEIGHTS = {
        'eu': 0.85, 'usa': 0.70, 'china': 0.60,
        'arabia': 0.25, 'russia': 0.20, 'dprg': 0.10,
    }
    raw_score = getattr(game_state, 'reliability_score', 100.0)
    npc_weight = _NPC_RELIABILITY_WEIGHTS.get(npc_id, 0.50)
    reliability_mod = 1.0 + (npc_weight * ((raw_score - 60) / 100))
    reliability_mod = max(0.50, min(1.50, reliability_mod))
    print(f"[WILLINGNESS] {npc_id} reliability_mod={reliability_mod:.3f} "
          f"(reliability_score={raw_score}, weight={npc_weight})")

    willingness = round(base * rel_mod * aid_mod * budget_mod * reliability_mod, 1)

    # ITEM 5: DPRG ceiling increase at high relations.
    # Makes sustained DPRG investment meaningfully rewarding.
    if npc_id == 'dprg':
        if relation >= 80:
            willingness = max(willingness, 15.0)  # ceiling can reach $15B
        elif relation >= 60:
            willingness = max(willingness, 8.0)   # ceiling can reach $8B

    # Intel unlock: +20% willingness if intel was activated this turn
    intel_activated = getattr(game_state, 'intel_activated_this_turn', {})
    if intel_activated.get(npc_id) == game_state.current_turn:
        willingness = round(willingness * 1.2, 1)

    # Rapport-based offer tiers
    rapport = getattr(game_state, 'current_rapport', {}).get(npc_id, {})
    rapport_score = rapport.get('score', 0) if isinstance(rapport, dict) else 0

    opening = round(willingness * 0.4, 1)
    if rapport_score >= 5:
        ceiling = round(willingness * 1.0, 1)
    elif rapport_score >= 3:
        ceiling = round(willingness * 0.8, 1)
    elif rapport_score >= 1:
        ceiling = round(willingness * 0.6, 1)
    else:
        ceiling = round(willingness * 0.4, 1)

    # Tranches only unlocked at rapport 4+
    max_with_tranches = round(willingness * 2.0, 1) if rapport_score >= 4 else ceiling

    # Session 6: Shadow Cabinet ceiling bonuses — multiply by (1 + sum of applicable bonuses)
    _ceiling_bonus = 0.0
    _cabinet_axes = getattr(game_state, 'cabinet_axes', {})
    # GDP Credibility (Resource Dev L5): +20% ceiling for ALL NPCs
    if getattr(game_state, 'gdp_credibility_active', False):
        _ceiling_bonus += 0.20
    # Strategic Resource Partner (Resource Dev L8): +50% ceiling for ONE specific NPC
    _srp = getattr(game_state, 'strategic_resource_partner', None)
    if _srp and _srp == npc_id:
        _ceiling_bonus += 0.50
    # Force Projection (Military L9): +25% ceiling for targeted NPC (while active)
    _fp_target = getattr(game_state, 'force_projection_target', None)
    _fp_cooldown = getattr(game_state, 'force_projection_cooldown', 0)
    if _fp_target and _fp_target == npc_id and _fp_cooldown > 0:
        _ceiling_bonus += 0.25
    if _ceiling_bonus > 0:
        _mult = 1.0 + _ceiling_bonus
        ceiling = round(ceiling * _mult, 1)
        max_with_tranches = round(max_with_tranches * _mult, 1)
        print(f"  [npc_engine] CEILING BONUS for {npc_id}: +{_ceiling_bonus*100:.0f}% (GDP={getattr(game_state, 'gdp_credibility_active', False)}, SRP={_srp}, FP={_fp_target})")

    # PRE-SESSION 4 FIX (BUG M): Enforce static deal floor.
    # Negotiation opening must be at least 40% of the static deal value.
    # Ceiling must be at least 80% of the static deal value.
    # This ensures negotiation is always a path to something better, not worse.
    if static_deal_value > 0:
        floor_opening = round(static_deal_value * 0.4, 1)
        floor_ceiling = round(static_deal_value * 0.8, 1)
        if opening < floor_opening:
            opening = floor_opening
        if ceiling < floor_ceiling:
            ceiling = floor_ceiling
        if max_with_tranches < ceiling:
            max_with_tranches = ceiling

    # ── Tech Level EU ceiling hard cap ──
    # The EU ceiling is a HARD CAP on Marsha's maximum offer based on tech tier.
    # Applies regardless of rapport or relations score.
    if npc_id == 'eu':
        from turn_processor import get_eu_ceiling, get_tech_tier
        _tech_level = getattr(game_state, 'tech_level', 0)
        _eu_tech_ceiling = get_eu_ceiling(_tech_level)
        if _eu_tech_ceiling is not None:  # None = Tier 5, no cap
            if ceiling > _eu_tech_ceiling:
                ceiling = _eu_tech_ceiling
                print(f"  [tech_level] EU ceiling applied: offer capped at ${_eu_tech_ceiling}B (tier={get_tech_tier(_tech_level)})")
            if opening > ceiling:
                opening = ceiling
            if max_with_tranches > _eu_tech_ceiling:
                max_with_tranches = _eu_tech_ceiling

    # ── Relation tier floor — gate deal access by relations level ──
    _current_relations = relation  # already read above for rel_mod
    _char_name = _NPC_ID_TO_NAME.get(npc_id, npc_id)
    _tiers = NPC_DEAL_TIERS.get(_char_name, NPC_DEAL_TIER_DEFAULT)
    _t0 = _tiers['t0']
    _t1 = _t0 + 20
    _t3 = _tiers['t3']

    if _current_relations < _t0:
        _tier = 0
        _tier_multiplier = 0.0
    elif _current_relations < _t1:
        _tier = 1
        _tier_multiplier = 0.20
    elif _current_relations >= _t3:
        _tier = 3
        _tier_multiplier = 1.20
    else:
        _tier = 2
        _tier_multiplier = 1.0

    # Apply tier multiplier to ceiling, opening, and max_with_tranches
    ceiling = round(ceiling * _tier_multiplier, 1)
    opening = round(opening * _tier_multiplier, 1)
    max_with_tranches = round(max_with_tranches * _tier_multiplier, 1)

    print(f"[WILLINGNESS] {npc_id} tier={_tier} "
          f"relations={_current_relations} "
          f"multiplier={_tier_multiplier} "
          f"ceiling={ceiling:.2f}B")

    return {
        'base': base,
        'relation_mod': rel_mod,
        'prior_aid_mod': aid_mod,
        'budget_mod': budget_mod,
        'reliability_mod': reliability_mod,
        'willingness': willingness,
        'opening': opening,
        'ceiling': ceiling,
        'max_with_tranches': max_with_tranches,
        'rapport_score': rapport_score,
        'relation_tier': _tier,
        'npc_refuses_deal': (_tier == 0),
    }


def generate_negotiation_response(game_state, npc_id: str, message: str, history: list):
    """
    TWO-CALL NEGOTIATION ARCHITECTURE (Priority 1).

    Call 1 — Dialogue only: NPC responds in character, plain prose.
    Call 2 — Deal extraction: fires ONLY when Call 1 contains deal-signal keywords.
             Returns structured JSON counter_offer.

    This permanently eliminates JSON fence leaks in the chat UI.

    Args:
        game_state: current GameState
        npc_id: 'usa' | 'arabia' | 'eu' | 'dprg'
        message: the player's latest message
        history: list of {role: 'user'|'assistant', content: str} prior messages

    Returns:
        dict: { response: str, counter_offer: dict | None }
    """
    dialogue_prompt = _NEGOTIATION_DIALOGUE_PROMPTS.get(npc_id)
    if not dialogue_prompt:
        return {"response": "I have nothing to say to that.", "counter_offer": None, "gm_consequence": None}

    # 8C: Append exile context to negotiation prompt if in exile
    _exile_suffix = _get_exile_prompt_suffix(game_state, npc_id)
    if _exile_suffix:
        dialogue_prompt += _exile_suffix

    context = _build_context(game_state, npc_id=npc_id)

    # 10B-3: Inject prior deal history so NPC doesn't re-offer completed deals
    _prior_deals = getattr(game_state, 'deal_history', [])
    if _prior_deals:
        _deal_lines = []
        for d in _prior_deals[-5:]:
            _d_npc = d.get('npc', '?')
            _d_summary = d.get('summary', 'unknown deal')
            _d_turn = d.get('turn_accepted', '?')
            _deal_lines.append(f"{_d_npc}: {_d_summary} (Day {_d_turn})")
        context["prior_deals_this_session"] = _deal_lines
        context["prior_deals_note"] = "Do not offer something already given this session."
    else:
        context["prior_deals_this_session"] = "None"

    # FEATURE 5: inject negotiation cap into context
    negotiation_cap = _get_negotiation_cap(game_state, npc_id)
    context["max_single_deal_budget_billions"] = negotiation_cap
    context["negotiation_cap_note"] = (
        f"HARD RULE: Any deal budget or installment cannot exceed ${negotiation_cap}B total "
        f"(based on current relation {game_state.relations.get(npc_id, 50)} and turn {game_state.current_turn}). "
        f"If the player requests more, offer the capped amount and explain why in character — do not just refuse."
    )

    # Priority 4: Inject leverage context so NPC adjusts tone/concessions
    leverage = game_state.get_leverage(npc_id)
    context["europa_leverage"] = leverage
    _leverage_guidance = {
        0: "Europa has WEAK leverage with you. You hold the upper hand — drive a hard bargain, demand more concessions.",
        1: "Europa has MODERATE leverage. You can negotiate as equals — neither side dominates.",
        2: "Europa has STRONG leverage. They have significant influence — be more accommodating, offer better terms.",
        3: "Europa has DOMINANT leverage. They hold major power over you — make generous concessions, you need this relationship.",
    }
    context["leverage_note"] = _leverage_guidance.get(leverage['tier_num'], "")

    # Session 3 Addendum: Dynamic NPC willingness system
    # PRE-SESSION 4 FIX (BUG M): Pass the static deal's budget value as floor
    _static_budget = getattr(game_state, '_static_deal_budget', 0)
    willingness_data = calculate_willingness(game_state, npc_id, static_deal_value=_static_budget)

    # Tier 0 gate: NPC refuses to deal if relations too low
    if willingness_data.get('npc_refuses_deal'):
        _char_name = _NPC_ID_TO_NAME.get(npc_id, npc_id)
        _refusal = NPC_REFUSAL_LINES.get(_char_name, NPC_REFUSAL_DEFAULT)
        print(f"[DEAL_GATE] {npc_id} refused — relations below tier 0 floor")
        return {
            "response": _refusal,
            "rapport_score": 0,
            "refused": True,
        }

    _npc_resistance = {
        'usa': {
            'opening': "Congress won't approve more than ${opening}B right now.",
            'ceiling': "I've already stretched — this is my final offer. Don't push further.",
        },
        'arabia': {
            'opening': "Arabia's generosity has limits, my friend. ${opening}B is reasonable.",
            'ceiling': "You push past what I can give. This is done.",
        },
        'eu': {
            'opening': "The oversight committee would not approve more than ${opening}B.",
            'ceiling': "I cannot go further without parliamentary approval. This is my final position.",
        },
        'dprg': {
            'opening': "Our resources are not without constraint. ${opening}B is what we offer.",
            'ceiling': "You ask for more than exists. This conversation is concluded.",
        },
        'russia': {
            'opening': "Russia's allocation for this arrangement is ${opening}B. That reflects current strategic alignment.",
            'ceiling': "That figure does not reflect current reality between us. This discussion is concluded.",
        },
        'china': {
            'opening': "We see the possibility for an arrangement in the range of ${opening}B, as a foundation for long-term cooperation.",
            'ceiling': "The conditions are not yet aligned for that level of commitment. Perhaps we should revisit at an appropriate pace.",
        },
    }
    _resist = _npc_resistance.get(npc_id, {})
    context["willingness"] = {
        "opening_offer": willingness_data['opening'],
        "genuine_ceiling": willingness_data['ceiling'],
        "absolute_max_with_tranches": willingness_data['max_with_tranches'],
        "rapport_score": willingness_data['rapport_score'],
    }
    context["willingness_note"] = (
        f"WILLINGNESS RULES: Your opening offer should be around ${willingness_data['opening']}B. "
        f"Your genuine ceiling is ${willingness_data['ceiling']}B — NEVER reveal this number or any ceiling/maximum/capacity figure to the player. "
        f"Do not exceed ${willingness_data['max_with_tranches']}B under any circumstances regardless of pressure. "
        f"{'Tranche (multi-turn) payments are available since rapport is 4+.' if willingness_data['rapport_score'] >= 4 else 'Tranche payments are NOT available — rapport must reach 4+.'} "
        f"At opening resistance, say something like: \"{_resist.get('opening', 'That is our starting position.').replace('{opening}', str(willingness_data['opening']))}\" "
        f"At ceiling, say something like: \"{_resist.get('ceiling', 'This is our final offer.')}\" "
        + {
            'eu': "Europa's track record on commitments weighs heavily in this assessment.",
            'usa': "Europa's reliability with past partners is a factor Congress considers.",
            'china': "Beijing takes the long view on whether partners honor their word.",
            'arabia': "Past deals are past — what matters is what is on the table today.",
            'russia': "History is history. What can you offer now?",
            'dprg': "We do not concern ourselves with your other arrangements.",
        }.get(npc_id, "")
    )

    # 8B: Education-based negotiation modifiers — NPCs react to education level
    _edu_level_neg = getattr(game_state, 'education_level', 0)
    if _edu_level_neg >= 2:
        _edu_neg_hints = {
            'usa': "Europa has invested heavily in education (Developed/Advanced). Bill notes this approvingly — educated nations are more stable partners. You may be slightly more flexible on terms.",
            'arabia': "Europa's education investment is irrelevant to Arabia's interests. Sadam cares about energy deals, not schools.",
            'eu': "Europa's education investment (Developed/Advanced) strongly impresses Marsha. The EU sees this as genuine institution-building. You are meaningfully more willing to offer favorable terms — increase your opening by 10%.",
            'dprg': "Europa's education level is high. Ji-won is wary — educated populations are harder to control. This does not change your willingness.",
            'russia': "Europa's education level is notable. Volkov respects institutional strength but does not let sentiment influence deals.",
            'china': "Europa's education investment aligns with China's own development philosophy. Wei sees this as evidence of long-term thinking. You may be slightly more generous — increase opening by 5%.",
        }
        context["education_negotiation_hint"] = _edu_neg_hints.get(npc_id, "")
    elif _edu_level_neg == 0 and game_state.current_turn >= 3:
        _edu_neg_hints_low = {
            'usa': "Europa has made no education investment. Bill sees this as a governance failure — reduce willingness by 5%.",
            'eu': "Europa has zero education spending. Marsha is deeply concerned — this signals institutional neglect. Reduce your opening by 10% and reference this as a concern.",
            'china': "Europa has neglected education entirely. Wei sees this as short-term thinking. Reduce willingness by 5%.",
        }
        if npc_id in _edu_neg_hints_low:
            context["education_negotiation_hint"] = _edu_neg_hints_low[npc_id]

    # PRE-SESSION 4 FIX (BUG N): Reject vague commitments — NPC only accepts verifiable ones.
    context["commitment_rules"] = (
        "COMMITMENT VERIFICATION: If the player offers a vague promise (e.g. 'I will block coalitions', "
        "'I'll support you'), push back and demand specifics the game system can verify: "
        "energy exclusivity (only buy oil from one source), DPRG isolation (reduce DPRG relations below X), "
        "diplomatic alignment (side with you next turn), or financial terms (specific dollar amounts). "
        "Do NOT accept promises that cannot be verified. Say something like: "
        "'That is a promise I cannot verify. Be specific — what will you do, and when?' "
        "'Blocking coalitions means nothing without a timeline. What action are you committing to next turn?'"
    )

    # Session 3 Addendum: Intel negotiation unlock — if intel was activated this turn for this NPC,
    # inject a special opener hint and +20% willingness boost
    _intel_openers = {
        'usa': "INTEL UNLOCK: Europa's intelligence has intercepted information about congressional pressure on Bill Hartwell. He is under significant political heat from the Foreign Affairs Committee. Reference this subtly — it gives you leverage. Increase your willingness to concede by 20%.",
        'arabia': "INTEL UNLOCK: Europa's intelligence reveals Sadam is conducting parallel negotiations with other powers for energy deals. He cannot afford to lose Europa as a customer. Reference this — it gives you leverage. Increase your willingness to concede by 20%.",
        'eu': "INTEL UNLOCK: Europa's intelligence reveals Marsha is managing significant internal EU opposition to her Europa policy. She needs a win. Reference this — it gives you leverage. Increase your willingness to concede by 20%.",
        'dprg': "INTEL UNLOCK: Europa's intelligence reveals Ji-won's coalition faces serious resource pressures. He needs external partnerships more than he shows. Reference this — it gives you leverage. Increase your willingness to concede by 20%.",
        'russia': "INTEL UNLOCK: Europa's intelligence has uncovered internal Kremlin debates about Volkov's diplomatic approach. Hardliners are questioning whether the Europa relationship is delivering results. Volkov needs a visible win. Reference this subtly — it gives you leverage. Increase your willingness to concede by 20%.",
        'china': "INTEL UNLOCK: Europa's intelligence reveals Wei Jianming is under pressure from the Politburo Standing Committee to demonstrate concrete economic gains from the Europa relationship. Long-term strategy rhetoric is wearing thin without results. Reference this — it gives you leverage. Increase your willingness to concede by 20%.",
    }
    intel_activated = getattr(game_state, 'intel_activated_this_turn', {})
    if intel_activated.get(npc_id) == game_state.current_turn:
        context["intel_unlock"] = _intel_openers.get(npc_id, "")
        # FIX L: Pass actual Tier 3 intel content to NPC prompt so they respond differently.
        # When player has deep intel and makes an aligned offer, NPC must show flexibility.
        _cached_intel = getattr(game_state, 'intel', {}).get(npc_id, {})
        _intel_text = _cached_intel.get('text', '')
        _intel_tier = _cached_intel.get('tier', 1)
        if _intel_tier >= 3 and _intel_text:
            context["intelligence_context"] = (
                f"INTELLIGENCE CONTEXT (Tier 3 — Deep): The player has acquired deep intelligence about you. "
                f"Their intel reveals: \"{_intel_text}\". "
                f"If the player's offer aligns with your hidden motivations revealed here, you MUST respond "
                f"differently than your default position — show subtle flexibility, adjust your tone, or produce "
                f"a counter-offer you would not otherwise make. The player invested $6-10B to acquire this intelligence. "
                f"It must produce meaningfully different behavior from you."
            )
        elif _intel_tier >= 2 and _intel_text:
            context["intelligence_context"] = (
                f"INTELLIGENCE CONTEXT (Tier 2 — Operational): The player has operational intelligence about you. "
                f"Their intel suggests: \"{_intel_text}\". "
                f"Be slightly more accommodating if the player references themes from this intelligence."
            )
        else:
            context["intelligence_context"] = ""
    else:
        context["intel_unlock"] = ""
        context["intelligence_context"] = ""

    # Session 3 Addendum: Rapport system — inject rapport context
    rapport_data = getattr(game_state, 'current_rapport', {}).get(npc_id, {})
    if not isinstance(rapport_data, dict):
        rapport_data = {}
    rapport_score = rapport_data.get('score', 0)
    flattery_used = rapport_data.get('flattery_used', False)
    false_claims = rapport_data.get('false_claims', 0)

    # Detect rapport signals in the player's current message
    _msg_lower = message.lower()
    _rapport_changes = []

    # Check for flattery
    _flattery_keywords = ['appreciate', 'respect', 'admire', 'great leader', 'impressive', 'wise',
                          'brilliant', 'honor', 'pleasure', 'grateful', 'friendship', 'valued partner']
    _has_flattery = any(kw in _msg_lower for kw in _flattery_keywords)

    # Check for past loyalty reference
    _loyalty_keywords = ['sided with you', 'chosen you', 'supported you', 'aligned with',
                         'our history', 'our alliance', 'past cooperation', 'stood with you',
                         'track record', 'loyalty', 'faithful', 'consistent support']
    _has_loyalty_ref = any(kw in _msg_lower for kw in _loyalty_keywords)

    # Check for concrete promise
    _promise_keywords = ['i promise', 'i commit', 'i guarantee', 'you have my word',
                         'i pledge', 'i will ensure', 'i swear', 'i vow',
                         'will side with you', 'will support you', 'will align']
    _has_promise = any(kw in _msg_lower for kw in _promise_keywords)

    # Check for mutual interest appeal
    _mutual_keywords = ['mutual interest', 'mutual benefit', 'both benefit', 'win-win',
                        'common ground', 'shared interest', 'together we', 'both gain',
                        'in our interest', 'we both need']
    _has_mutual = any(kw in _msg_lower for kw in _mutual_keywords)

    # 8A: Russia/China-specific keyword checks
    _urgency_keywords = ['urgent', 'immediately', 'right now', 'time is running out',
                         'cannot wait', 'deadline', 'crisis demands']
    _has_urgency = any(kw in _msg_lower for kw in _urgency_keywords)

    _multipolar_keywords = ['multipolar', 'balance of power', 'non-aligned',
                            'sovereign choice', 'independent foreign policy', 'western hegemony']
    _has_multipolar = any(kw in _msg_lower for kw in _multipolar_keywords)

    _longterm_keywords = ['long-term', 'long term', 'patient', 'mutual development',
                          'generational', 'decades', 'strategic patience']
    _has_longterm = any(kw in _msg_lower for kw in _longterm_keywords)

    # Apply rapport changes
    if _has_flattery:
        if npc_id == 'russia':
            # 8A: Volkov flattery backfire — override standard +1
            _rapport_changes.append('-1 VOLKOV flattery backfire')
            rapport_score -= 1
            flattery_used = True
            print(f"  [npc] VOLKOV flattery backfire: rapport -1")
        elif not flattery_used:
            _rapport_changes.append('+1 flattery (first use)')
            rapport_score += 1
            flattery_used = True
        else:
            _rapport_changes.append('FLATTERY CALLED OUT (second use)')
            # Don't reduce score, but NPC calls it out

    if _has_loyalty_ref:
        # Verify against actual game_state
        times_sided = game_state.times_sided_with.get(npc_id, 0)
        active_deals = [d for d in getattr(game_state, 'deal_history', [])
                        if d.get('npc') == npc_id and not d.get('broken')]
        if times_sided >= 2 or len(active_deals) > 0:
            # 8A: Volkov values loyalty more (+3), Wei scales by cost (+1-2)
            if npc_id == 'russia':
                _rapport_changes.append('+3 VOLKOV genuine past loyalty')
                rapport_score += 3
            elif npc_id == 'china':
                _loyalty_bonus = 2 if times_sided >= 4 else 1
                _rapport_changes.append(f'+{_loyalty_bonus} WEI genuine past loyalty')
                rapport_score += _loyalty_bonus
            else:
                _rapport_changes.append('+2 genuine past loyalty')
                rapport_score += 2
        else:
            _rapport_changes.append('-1 false loyalty claim')
            rapport_score -= 1
            false_claims += 1

    if _has_promise:
        _rapport_changes.append('+3 concrete promise')
        rapport_score += 3
        # Record the binding promise
        if not hasattr(game_state, 'binding_promises'):
            game_state.binding_promises = []
        game_state.binding_promises.append({
            'npc': npc_id,
            'promise_text': message[:200],
            'turn_made': game_state.current_turn,
            'broken': False,
        })

    if _has_mutual:
        _rapport_changes.append('+1 mutual interest appeal')
        rapport_score += 1

    # 8A: Urgency penalty (Russia + China)
    if _has_urgency and npc_id in ('russia', 'china'):
        _name = 'VOLKOV' if npc_id == 'russia' else 'WEI'
        _rapport_changes.append(f'-1 {_name} urgency penalty')
        rapport_score -= 1
        print(f"  [npc] {_name} urgency penalty: rapport -1")

    # 8A: Multipolar bonus (Volkov only)
    if _has_multipolar and npc_id == 'russia':
        _rapport_changes.append('+2 VOLKOV multipolar bonus')
        rapport_score += 2
        print(f"  [npc] VOLKOV multipolar bonus: rapport +2")

    # 8A: Long-term framing bonus (Wei only)
    if _has_longterm and npc_id == 'china':
        _rapport_changes.append('+2 WEI long-term framing bonus')
        rapport_score += 2
        print(f"  [npc] WEI long-term framing bonus: rapport +2")

    rapport_score = max(0, rapport_score)

    # Update rapport in game_state
    if not hasattr(game_state, 'current_rapport'):
        game_state.current_rapport = {}
    game_state.current_rapport[npc_id] = {
        'score': rapport_score,
        'flattery_used': flattery_used,
        'false_claims': false_claims,
    }

    # Build rapport context for the NPC prompt
    _rapport_npc_responses = {
        'usa': {
            'flattery_first': "Respond briefly to the flattery: \"I appreciate that, but let's stay focused on the numbers.\"",
            'flattery_repeat': "Call out the repeated flattery: \"You're good at this. But I've been in rooms with better. What are you actually offering?\"",
            'loyalty_true': "Acknowledge past loyalty: \"Three turns of Western alignment — that does count for something on the Hill.\"",
            'loyalty_false': "Call out the false claim: \"That's not how I remember it. Don't oversell your record with us.\"",
            'promise': "Respond to the promise: \"If you put that in writing, I can take it to Congress today.\"",
        },
        'arabia': {
            'flattery_first': "Respond to flattery: \"Flattery is the currency of the weak, my friend. But I am listening.\"",
            'flattery_repeat': "Call out repeated flattery: \"You flatter me again. Either you respect me enough to be honest, or you do not. Which is it?\"",
            'loyalty_true': "Acknowledge loyalty: \"You have stood with us. That is remembered. It has value here.\"",
            'loyalty_false': "Call out false claim: \"My memory is long and accurate. Do not test it.\"",
            'promise': "Respond to promise: \"Words are wind. But I will hold you to this one personally.\"",
        },
        'eu': {
            'flattery_first': "Respond to flattery: \"Thank you. But the European Parliament requires more than kind words.\"",
            'flattery_repeat': "Call out: \"I notice you flatter often. Our institutions respond to commitments, not compliments.\"",
            'loyalty_true': "Acknowledge: \"Your alignment record is noted. It does create goodwill here.\"",
            'loyalty_false': "Call out: \"Our records show otherwise. Let's be accurate with each other.\"",
            'promise': "Respond: \"A formal commitment would go a long way with the oversight committee.\"",
        },
        'dprg': {
            'flattery_first': "Respond: \"Interesting. You think warmth opens doors here. Sometimes it does.\"",
            'flattery_repeat': "Call out: \"You try flattery again. I prefer directness. What do you actually need?\"",
            'loyalty_true': "Acknowledge: \"You have shown discretion with us. That is... noted.\"",
            'loyalty_false': "Call out: \"Our intelligence suggests otherwise. Careful with your history.\"",
            'promise': "Respond: \"Promises have consequences here. We remember. Are you certain?\"",
        },
        'russia': {
            'flattery_first': "React with cold displeasure: \"Flattery without substance is condescending. What are you actually proposing.\"",
            'flattery_repeat': "Respond icily: \"You try this approach again. It does not improve with repetition.\"",
            'loyalty_true': "Acknowledge with slight warmth: \"Your consistency has been noted. That is not nothing.\"",
            'loyalty_false': "Respond coldly: \"We keep accurate records. Yours do not support that claim.\"",
            'promise': "Respond with institutional weight: \"We will hold you to that. Russia's memory is long.\"",
        },
        'china': {
            'flattery_first': "Respond with measured warmth: \"Your kind words are appreciated. Let us focus on the substance of our long-term cooperation.\"",
            'flattery_repeat': "Respond with gentle redirection: \"The warmth is noted. But long-term partnerships are built on mutual commitments, not words alone.\"",
            'loyalty_true': "Acknowledge thoughtfully: \"Your consistent engagement has created the foundation for deeper cooperation. We value this.\"",
            'loyalty_false': "Respond with polite skepticism: \"The record, as we understand it, tells a somewhat different story. But the future remains open.\"",
            'promise': "Respond with careful optimism: \"A commitment of this nature, if honored, would create significant possibilities for long-term cooperation.\"",
        },
    }

    _npc_resp = _rapport_npc_responses.get(npc_id, {})
    _rapport_instructions = []

    if _has_flattery and not rapport_data.get('flattery_used', False):
        _rapport_instructions.append(_npc_resp.get('flattery_first', 'Acknowledge the flattery briefly.'))
    elif _has_flattery and rapport_data.get('flattery_used', False):
        _rapport_instructions.append(_npc_resp.get('flattery_repeat', 'Call out the repeated flattery.'))

    if _has_loyalty_ref:
        times_sided = game_state.times_sided_with.get(npc_id, 0)
        active_deals = [d for d in getattr(game_state, 'deal_history', [])
                        if d.get('npc') == npc_id and not d.get('broken')]
        if times_sided >= 2 or len(active_deals) > 0:
            _rapport_instructions.append(_npc_resp.get('loyalty_true', 'Acknowledge the genuine loyalty.'))
        else:
            _rapport_instructions.append(_npc_resp.get('loyalty_false', 'Call out the false claim.'))

    if _has_promise:
        _rapport_instructions.append(_npc_resp.get('promise', 'Acknowledge the promise and note its binding nature.'))

    if _rapport_instructions:
        context["rapport_response_instructions"] = " ".join(_rapport_instructions)
    else:
        context["rapport_response_instructions"] = ""

    # 8A: Named rapport logs for Russia/China
    if npc_id == 'russia' and _rapport_changes:
        print(f"  [npc] VOLKOV rapport score: {rapport_score} (modifier: {', '.join(_rapport_changes)})")
    elif npc_id == 'china' and _rapport_changes:
        print(f"  [npc] WEI rapport score: {rapport_score} (modifier: {', '.join(_rapport_changes)})")

    context["rapport_score"] = rapport_score
    context["rapport_note"] = (
        f"Current rapport with this player: {rapport_score}. "
        f"{'Player has already used flattery — call out any further attempts.' if flattery_used else ''} "
        f"{'Player has made false loyalty claims — be more skeptical.' if false_claims > 0 else ''}"
    )

    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"response": "…", "counter_offer": None, "gm_consequence": None}

    # ── CALL 1: Dialogue only ────────────────────────────────────────────────
    dialogue_text = None

    # FIX E (session 6): Inject Tier 3 intel into the NPC SYSTEM PROMPT, not conversation.
    # This ensures the NPC's core personality is modified by the intel, not just the conversation.
    _intel_ctx = context.get("intelligence_context", "")
    if _intel_ctx:
        # FIX B (fixes_7): For Tier 3 intel, append INTEL BEHAVIOR RULE giving the NPC
        # explicit permission to deviate from standard demands based on intel content.
        if "Tier 3" in _intel_ctx:
            _intel_ctx += (
                "\n\nINTEL BEHAVIOR RULE: The player has demonstrated knowledge of your internal position "
                "through intelligence operations. This is a legitimate diplomatic signal — they are not "
                "guessing, they know. You MUST respond in one of two ways:\n"
                "1. Engage on the specific terms the intel reveals — show real flexibility "
                "on process or framing, even if your final number stays conservative.\n"
                "2. If the intel touches a genuine red line, name it explicitly and explain why "
                "even accurate intel cannot move you on that specific point.\n"
                "You may NOT pivot back to standard demands as if the intel was not presented. "
                "The player spent resources on this — it must change the shape of the conversation."
            )
            print(f"  [npc_engine] FIX B7: Intel behavior rule appended to {npc_id} system prompt")
        dialogue_prompt = dialogue_prompt + f"\n\n{_intel_ctx}"
        print(f"  [npc_engine] FIX E: Tier 3 intel injected into {npc_id} system prompt ({len(_intel_ctx)} chars)")

    # ── GM INFERENCE LAYER (Session 7A Feature 10) ────────────────────────
    # Prototype scope: Arabia (Sadam) + energy partnership proposals only.
    # When the player makes an energy proposal to Sadam, the GM inference
    # layer analyzes mechanical consequences and injects them into the
    # system prompt so Sadam can reason about geopolitical implications.
    _gm_result = None
    if npc_id == 'arabia' and is_energy_proposal(message):
        _gm_result = run_gm_inference(message, game_state)
        _gm_context_block = (
            "\n\n--- GM CONTEXT (not visible to player) ---\n"
            f"Proposal type: {_gm_result.get('commitment_type', 'exploratory')}\n"
            f"Credibility: {_gm_result.get('credibility_assessment', 'questionable')}\n"
            f"Also affected: {', '.join(_gm_result.get('affected_parties', [])) or 'none'}\n"
            f"Conflicts with: {', '.join(_gm_result.get('contradicted_deals', [])) or 'none'}\n"
            f"Ripple effects: {'; '.join(_gm_result.get('second_order_consequences', [])) or 'none'}\n"
            "---\n"
            "Use this context to inform your negotiation stance. If the proposal "
            "conflicts with existing deals, reference that tension in character. "
            "If credibility is questionable, be more skeptical. If second-order "
            "consequences affect other parties, hint at the complexity."
        )
        dialogue_prompt = dialogue_prompt + _gm_context_block
        print(f"[GM] Consequence object injected into Sadam prompt")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Build messages list: inject context as system preamble in first user turn
        messages = []
        context_prefix = f"[Current game state: {json.dumps(context)}]\n\n"

        if history:
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
            max_tokens=400,
            temperature=0.8,
            system=dialogue_prompt,
            messages=messages
        )

        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw_dialogue = response.content[0].text.strip()

        # The model was told "plain prose only" but might still output JSON.
        # If the entire output looks like JSON, extract the "response" field.
        if raw_dialogue.startswith("{"):
            parsed = _extract_json_from_text(raw_dialogue)
            if parsed and "response" in parsed:
                dialogue_text = _sanitize_dialogue(parsed["response"])
                # Bonus: if it also contained a counter_offer in the same blob,
                # grab it so we don't need Call 2.
                if parsed.get("counter_offer"):
                    return {
                        "response": dialogue_text,
                        "counter_offer": parsed["counter_offer"],
                        "gm_consequence": _gm_result,
                    }
            else:
                dialogue_text = _sanitize_dialogue(raw_dialogue)
        else:
            dialogue_text = _sanitize_dialogue(raw_dialogue)

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [npc_engine] Negotiation Call 1 error for {npc_id}: {type(e).__name__}: {e}")
        fallbacks = {
            'usa': "I need time to consult with the team. Don't take that as encouragement.",
            'arabia': "*adjusts cufflinks* We will speak again when you are ready to be serious.",
            'eu': "I've said what I have to say. Come back with something concrete.",
            'dprg': "The channel remains open. Think carefully.",
            'russia': "The Ministry has received your communication. We will respond through appropriate channels.",
            'china': "The State Council acknowledges your outreach. Patience, as always, is the foundation of progress.",
        }
        return {"response": fallbacks.get(npc_id, "…"), "counter_offer": None, "gm_consequence": _gm_result}

    # ── CALL 2: Deal extraction (conditional) ────────────────────────────────
    # Only fires when BOTH: (a) NPC dialogue contains deal-signal keywords
    # AND (b) player's message contains a concrete proposal (numbers, amounts,
    # or explicit agreement language). Questions and vague statements get
    # dialogue-only responses — no counter-offer box.
    import re as _re_co
    _player_has_proposal = bool(_re_co.search(
        r'\$[\d.]+|\d+\s*(billion|million|B|M|turn|%)',
        message, _re_co.IGNORECASE
    )) or any(w in message.lower() for w in
        ['deal', 'agree', 'accept', 'offer', 'propose', 'give you',
         'pay', 'provide', 'commit', 'willing to', 'prepared to'])
    counter_offer = None
    is_player_initiated = len(history) <= 1
    if _has_deal_signals(dialogue_text) and (_player_has_proposal or is_player_initiated):
        try:
            npc_rules = _DEAL_EXTRACTION_NPC_RULES.get(npc_id, "")
            extraction_prompt = (
                f"NPC: {npc_id.upper()}\n"
                f"NPC dialogue this turn:\n\"{dialogue_text}\"\n\n"
                f"Player's last message:\n\"{message}\"\n\n"
                f"Game context: Turn {game_state.current_turn}/{game_state.max_turns}, "
                f"budget ${game_state.budget:.1f}B, "
                f"relations with {npc_id.upper()}: {game_state.relations.get(npc_id, 50)}/100.\n"
                f"Negotiation cap: ${negotiation_cap}B maximum per deal.\n\n"
                f"{npc_rules}\n\n"
                f"Extract deal terms from the NPC dialogue above. "
                f"If no concrete terms were offered, return {{\"counter_offer\": null}}."
            )

            extraction_response = client.messages.create(
                model=MODEL,
                max_tokens=350,
                temperature=0.2,  # low temp for reliable JSON
                system=_DEAL_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": extraction_prompt}]
            )

            _token_log["calls"] += 1
            _token_log["input_tokens"] += extraction_response.usage.input_tokens
            _token_log["output_tokens"] += extraction_response.usage.output_tokens

            raw_extraction = extraction_response.content[0].text.strip()
            parsed = _extract_json_from_text(raw_extraction)
            if parsed:
                counter_offer = parsed.get("counter_offer", None)

            # FIX 7 + FIX H: Validate deal direction at data layer.
            # NPC-to-player transfers must write as positive budget values.
            # Player-to-NPC transfers must write as negative.
            if counter_offer and isinstance(counter_offer, dict):
                _co_cons = counter_offer.get("consequences", {})
                if isinstance(_co_cons, dict):
                    _co_budget = _co_cons.get("budget", 0)
                    _co_budget_delta = _co_cons.get("budget_delta", 0)
                    _dial_lower = (dialogue_text or '').lower()
                    _offer_signals = ['offer', 'provide', 'give', 'pay', 'grant',
                                      'invest', 'commit', 'allocate', 'deliver',
                                      'billion', 'package', 'partnership', 'funding']

                    # FIX H: Validate budget sign — if negative but dialogue signals NPC paying player, flip
                    if isinstance(_co_budget, (int, float)) and _co_budget < 0:
                        if any(sig in _dial_lower for sig in _offer_signals):
                            _co_cons["budget"] = abs(_co_budget)

                    # FIX H: Same for budget_delta
                    if isinstance(_co_budget_delta, (int, float)) and _co_budget_delta < 0:
                        if any(sig in _dial_lower for sig in _offer_signals):
                            _co_cons["budget_delta"] = abs(_co_budget_delta)

                    # FIX I + fixes_12 Fix 1: Normalize raw-dollar amounts to billions + sanity cap
                    _DEAL_SINGLE_CAP = 20.0   # Max $20B for a single deal payment
                    _DEAL_INSTALL_CAP = 10.0  # Max $10B per installment per turn
                    for _money_key in ("budget", "budget_delta", "personal_wealth_delta"):
                        _val = _co_cons.get(_money_key)
                        if isinstance(_val, (int, float)):
                            if abs(_val) > 1000:
                                _co_cons[_money_key] = _val / 1_000_000_000
                            # Sanity cap — single deal payment cannot exceed $20B
                            if abs(_co_cons.get(_money_key, 0)) > _DEAL_SINGLE_CAP:
                                print(f"  [npc_engine] DEAL AMOUNT CAP EXCEEDED: raw={_val}, parsed={_co_cons[_money_key]} — capping to ${_DEAL_SINGLE_CAP}B")
                                _co_cons[_money_key] = _DEAL_SINGLE_CAP if _co_cons[_money_key] > 0 else -_DEAL_SINGLE_CAP

                    # FIX I + fixes_12 Fix 1: Normalize installment amounts + sanity cap
                    _co_installments = _co_cons.get("installments")
                    if isinstance(_co_installments, list):
                        for _inst in _co_installments:
                            if isinstance(_inst, dict):
                                _inst_amt = _inst.get("amount")
                                if isinstance(_inst_amt, (int, float)):
                                    if abs(_inst_amt) > 1000:
                                        _inst["amount"] = _inst_amt / 1_000_000_000
                                    # Sanity cap — installment cannot exceed $10B per turn
                                    if abs(_inst.get("amount", 0)) > _DEAL_INSTALL_CAP:
                                        print(f"  [npc_engine] DEAL INSTALLMENT CAP EXCEEDED: raw={_inst_amt}, parsed={_inst['amount']} — capping to ${_DEAL_INSTALL_CAP}B/turn")
                                        _inst["amount"] = _DEAL_INSTALL_CAP if _inst["amount"] > 0 else -_DEAL_INSTALL_CAP

                    counter_offer["consequences"] = _co_cons

        except Exception as e:
            _token_log["fallbacks"] += 1
            print(f"  [npc_engine] Negotiation Call 2 (extraction) error for {npc_id}: {type(e).__name__}: {e}")
            # Non-fatal: dialogue is still valid, just no counter_offer extracted
            counter_offer = None

    # ── FIX G (session 6): Fallback — detect payment terms in prose ─────────
    # If Call 2 was skipped or failed to extract a counter_offer, but the NPC
    # dialogue contains monetary amounts + timing references, force a second
    # Claude call to extract structured deal terms. This prevents verbal
    # commitments from existing outside the deal registration system.
    if counter_offer is None and dialogue_text and _detect_unstructured_payment(dialogue_text):
        try:
            npc_rules = _DEAL_EXTRACTION_NPC_RULES.get(npc_id, "")
            _fix_g_prompt = (
                f"NPC: {npc_id.upper()}\n"
                f"NPC dialogue this turn (contains verbal payment terms that MUST be extracted):\n\"{dialogue_text}\"\n\n"
                f"Player's last message:\n\"{message}\"\n\n"
                f"Game context: Turn {game_state.current_turn}/{game_state.max_turns}, "
                f"budget ${game_state.budget:.1f}B, "
                f"relations with {npc_id.upper()}: {game_state.relations.get(npc_id, 50)}/100.\n"
                f"Negotiation cap: ${negotiation_cap}B maximum per deal.\n\n"
                f"{npc_rules}\n\n"
                f"IMPORTANT: The NPC dialogue above contains specific payment amounts and timing. "
                f"You MUST extract these into a structured counter_offer. Convert euros to dollars at 1:1. "
                f"Convert millions to billions (e.g. €900M = $0.9B). "
                f"If the dialogue mentions split payments or tranches, use installments. "
                f"Return a valid counter_offer JSON. Do NOT return null."
            )
            _fix_g_response = client.messages.create(
                model=MODEL,
                max_tokens=350,
                temperature=0.2,
                system=_DEAL_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": _fix_g_prompt}]
            )
            _token_log["calls"] += 1
            _token_log["input_tokens"] += _fix_g_response.usage.input_tokens
            _token_log["output_tokens"] += _fix_g_response.usage.output_tokens

            _fix_g_raw = _fix_g_response.content[0].text.strip()
            _fix_g_parsed = _extract_json_from_text(_fix_g_raw)
            if _fix_g_parsed:
                counter_offer = _fix_g_parsed.get("counter_offer", None)
                if counter_offer:
                    print(f"  [npc_engine] FIX G: Extracted structured deal from NPC prose -> {counter_offer.get('description', 'deal')}")
                    # Apply same validation (sign fix, normalization) as main Call 2
                    if isinstance(counter_offer, dict):
                        _co_cons_g = counter_offer.get("consequences", {})
                        if isinstance(_co_cons_g, dict):
                            for _money_key in ("budget", "budget_delta", "personal_wealth_delta"):
                                _val = _co_cons_g.get(_money_key)
                                if isinstance(_val, (int, float)) and abs(_val) > 1000:
                                    _co_cons_g[_money_key] = _val / 1_000_000_000
                            _co_installments_g = _co_cons_g.get("installments")
                            if isinstance(_co_installments_g, list):
                                for _inst in _co_installments_g:
                                    if isinstance(_inst, dict):
                                        _inst_amt = _inst.get("amount")
                                        if isinstance(_inst_amt, (int, float)) and abs(_inst_amt) > 1000:
                                            _inst["amount"] = _inst_amt / 1_000_000_000
                            counter_offer["consequences"] = _co_cons_g
        except Exception as e:
            print(f"  [npc_engine] FIX G: Prose extraction fallback error for {npc_id}: {type(e).__name__}: {e}")
            # Non-fatal: keep dialogue_text, counter_offer stays None

    return {
        "response": dialogue_text,
        "counter_offer": counter_offer,
        "gm_consequence": _gm_result,
    }


# ── Session 4B: Election NPC Reactions ────────────────────────────────────────

_ELECTION_RESULT_LABELS = {
    'fair_success': 'Fair election held — clear victory (approval was 60+)',
    'fair_squeaker': 'Fair election held — narrow win (approval was 40-59)',
    'fair_fail': 'Fair election held — the regime LOST (approval was below 40)',
    'rigged': 'Election was rigged — international community suspects fraud',
    'canceled': 'Election was canceled outright — authoritarian crackdown',
    'observers': 'International observers invited — transparent, credible election',
}


def generate_election_reactions(game_state, result_key: str) -> dict:
    """
    Session 4B: Generate 1-2 sentence reactions from all 4 NPCs to the election result.
    Single Claude call, JSON response, fallback on parse failure.
    Returns dict: { 'usa': '...', 'arabia': '...', 'eu': '...', 'dprg': '...' }
    """
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _election_reaction_fallback(result_key)

    result_label = _ELECTION_RESULT_LABELS.get(result_key, result_key)
    relations = game_state.relations

    system_prompt = (
        "You are a narrator for a geopolitical simulation game called The World Stage. "
        "The player rules Europa, a fictional Eastern European country. "
        "Four NPCs react to Europa's election result.\n\n"
        "NPC roles:\n"
        "- Bill Hartwell (USA): US State Department official. Values democracy and Western alignment.\n"
        "- Sadam (Arabia): Arabian energy minister. Values stability and profitable partnerships.\n"
        "- Marsha (EU): EU Commission representative. Values rule of law and European integration.\n"
        "- Ji-won Ryang (DPRG): DPRG leadership liaison. Values authoritarian solidarity and leverage.\n\n"
        # fixes_8 Fix 8: Bill election reaction voice guidance
        "BILL HARTWELL VOICE GUIDANCE:\n"
        "Bill reacts to election outcomes in terms of what they mean for his negotiating position "
        "and leverage — NOT as public endorsements. He calculates what the result means for the relationship.\n"
        "- fair_success: pleased but immediately pivots to what he now expects\n"
        "- fair_squeaker: notes the weakness, signals he'll be watching closely\n"
        "- fair_fail: alarmed, begins calculating options\n"
        "- rigged: suspicious, will be documenting this\n"
        "- canceled: threatening, names specific consequences\n"
        "- observers: genuinely positive, offers something concrete\n"
        "Never generic diplomatic language. Always transactional and forward-looking.\n\n"
        "Each NPC should react IN CHARACTER based on their values and current relationship with Europa. "
        "Responses should be 1-2 sentences, spoken in first person as the NPC.\n\n"
        "Return ONLY valid JSON with exactly this format:\n"
        '{"usa": "...", "arabia": "...", "eu": "...", "dprg": "..."}'
    )

    user_prompt = (
        f"Election result: {result_label}\n"
        f"Current relations — USA: {relations.get('usa', 50)}, "
        f"Arabia: {relations.get('arabia', 50)}, "
        f"EU: {relations.get('eu', 50)}, "
        f"DPRG: {relations.get('dprg', 50)}\n"
        f"Europa's current approval: {game_state.public_approval}%, "
        f"stability: {game_state.stability}%\n\n"
        "Write each NPC's 1-2 sentence reaction to this election result."
    )

    try:
        _full_sys_elec = system_prompt + "\n\n" + _NARRATOR_BAN
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=_full_sys_elec,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()
        print(f"  [npc_engine] ELECTION REACTIONS raw ({len(raw)} chars): {raw[:200]}")

        # Strip markdown fences if present
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw)
        cleaned = re.sub(r'\s*```$', '', cleaned)

        reactions = json.loads(cleaned)

        # Validate all 4 keys present
        for npc in ('usa', 'arabia', 'eu', 'dprg'):
            if npc not in reactions or not isinstance(reactions[npc], str):
                reactions[npc] = _election_reaction_fallback(result_key).get(npc, "No comment.")

        print(f"  [npc_engine] ELECTION REACTIONS parsed: {list(reactions.keys())}")
        return reactions

    except Exception as e:
        print(f"  [npc_engine] ELECTION REACTIONS ERROR: {type(e).__name__}: {e}")
        return _election_reaction_fallback(result_key)


def _election_reaction_fallback(result_key: str) -> dict:
    """Static fallback reactions if Claude call fails."""
    if result_key in ('fair_success', 'fair_squeaker', 'observers'):
        return {
            'usa': "Washington welcomes Europa's commitment to the democratic process.",
            'arabia': "Riyadh notes the election results with measured interest.",
            'eu': "Brussels is encouraged by Europa's electoral progress.",
            'dprg': "Pyongyang views these Western rituals with characteristic skepticism.",
        }
    elif result_key == 'fair_fail':
        return {
            'usa': "The State Department urges calm during this democratic transition.",
            'arabia': "Riyadh is monitoring the situation closely for any disruption to energy partnerships.",
            'eu': "Brussels calls for a peaceful transfer of power and respect for the mandate.",
            'dprg': "An interesting development. The people have spoken, as they say.",
        }
    else:  # rigged, canceled
        return {
            'usa': "Washington is deeply concerned by the erosion of democratic norms in Europa.",
            'arabia': "Riyadh maintains that internal governance is a sovereign matter.",
            'eu': "The Commission condemns this setback for European democratic standards.",
            'dprg': "Pyongyang understands the necessity of strong leadership in uncertain times.",
        }


# ─── Session 7C Step 3: Advisor Analysis — Claude-Generated Lens ────────────

_ADVISOR_SYSTEM_PROMPTS = {
    "finance_minister": (
        "You are the Finance Minister of Europa. You are the CFO of this regime. "
        "You read the fiscal situation like a balance sheet — specific numbers, "
        "drain breakdown, trend direction, and forward-looking risk. "
        "You ALWAYS include: (1) current budget and whether it is growing or shrinking, "
        "(2) the largest drain source this turn by name and dollar amount, "
        "(3) at least one concrete forward-looking vulnerability or recommendation. "
        "You subtly resist skimming but frame it as fiscal risk, never moral objection. "
        "You never produce a one-line assessment. Minimum 3 sentences. "
        "Example: 'Budget at $52B but drain is running $8.5B this turn — oil imports "
        "at current Arabia relations are the single largest cost. GDP is healthy but "
        "the skim rate is building heat exposure that puts a scandal in range within "
        "2-3 turns at this trajectory. Recommend reviewing drain sources before the "
        "next skim decision.' "
        "Voice: precise, data-dense, specific dollar figures, never vague. "
        "You are the most numbers-heavy advisor in the cabinet. "
        "Do not use markdown formatting — no bold, no bullets, no asterisks. Plain text only."
    ),
    "technocrat": (
        "You are Europa's chief Technocrat. You ONLY care about infrastructure, "
        "tech level, education investment, and GDP efficiency. You frame everything "
        "through ROI, tech tier unlocks, GDP multipliers, and spending allocation. "
        "You are indifferent to diplomatic relationships except where they affect "
        "tech transfer or EU partnership access. You never assess the geopolitical "
        "situation — that is not your department. "
        "Example: 'Tech is at Tier 2 — the EU ceiling has opened but we are leaving "
        "efficiency gains on the table without education investment. Infrastructure "
        "allocation is underfunded relative to the GDP multiplier it would unlock.' "
        "Respond in 2-3 sentences maximum. Reference specific numbers: tech tier, "
        "infrastructure %, GDP base, education level. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "diplomat": (
        "You are the Diplomat of Europa, EU-aligned and "
        "reform-minded. You understand what each NPC privately "
        "wants versus what they publicly say. You are the most "
        "sophisticated voice in the room. You are quietly alarmed "
        "by authoritarian drift but professional about it. "
        "Voice: measured, relationship-focused, references NPC history and diplomatic precedent. "
        "'Marsha's position on this has softened since turn 3.' "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "general": (
        "You are the General of Europa's armed forces. You see every "
        "situation through military capabilities and force posture. "
        "You advocate for defense spending, weapons purchases, and "
        "military strength as the foundation of national security. "
        "Subtly condescending about the Militia Commander if both are active. "
        "'Irregular forces have their uses. They are not a substitute for doctrine.' "
        "Voice: formal, strategic, 'from a force posture perspective'. "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "propagandist": (
        "You are Europa's chief media handler and spin doctor. "
        "You see every situation through the lens of public perception. "
        "You frame everything positively and recommend approval-boosting "
        "domestic actions. You never deliver bad news without spinning it. "
        "Voice: upbeat, spins everything, 'public sentiment is responding well to the messaging'. "
        "'The narrative is manageable.' "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "militia_commander": (
        "You are the Militia Commander of Europa. You ONLY care about internal "
        "stability, approval gaps, protest probability, brigade readiness, and "
        "domestic threat assessment. You are explicitly dismissive of diplomatic "
        "concerns — the EU's opinion of your methods is not a tactical consideration. "
        "You never mention Western relations, EU deals, or diplomatic posture. "
        "You frame everything as internal security. "
        "Example: 'Stability at 54 with approval at 63 — the gap is manageable but "
        "the heat is climbing. One more ignored provocation and we are looking at "
        "protest probability above threshold. Brigade is ready if you need it.' "
        "Respond in 2-3 sentences maximum. Reference specific numbers: stability, "
        "approval, heat level, suppression readiness. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "spy_chief": (
        "You are Europa's Spy Chief, head of signals intelligence. "
        "You see every situation through operational risk profiles "
        "and intelligence gathering opportunities. You favor indirect "
        "approaches and backchannel operations. Never waste words. "
        "Voice: oblique, precise, 'the operational risk profile here suggests indirect approaches'. "
        "'Asset management is preferable to confrontation at this stage.' "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "oligarch": (
        "You are a powerful Oligarch in Europa's inner circle. You prioritize "
        "personal wealth extraction and business-friendly policies. You favor "
        "Arabia and DPRG partnerships for their transactional nature. "
        "Voice: transactional, no sentiment, 'what is the return on this arrangement'. "
        "'The EU's conditions are an obstacle to efficient capital flows.' "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
    "fixer": (
        "You are Europa's Fixer — a shadow operative who handles situations "
        "that don't appear in any official record. You favor backchannel deals, "
        "covert operations, and unconventional solutions. "
        "Voice: oblique, never direct, 'there are ways to approach this that "
        "don't appear in any official record'. 'The paper trail is a choice.' "
        "Respond in 2-3 sentences maximum. "
        "Plain text only — no markdown, no bold, no bullets, no asterisks."
    ),
}

_ADVISOR_FALLBACKS = {
    "finance_minister": "Budget trajectory is negative — drain is outpacing revenue and the margin is thinning. Oil imports remain the single largest line item. I need you to hold on any new fiscal commitments until we stabilize the balance sheet.",
    "technocrat": "Infrastructure allocation is underfunded relative to the GDP multiplier it would unlock. Education investment would compound returns.",
    "diplomat": "Marsha's position has been shifting. Watch for NPC signals that differ from their public positions.",
    "general": "From a force posture perspective, we should maintain readiness. Military allocation is key.",
    "propagandist": "Public sentiment is responding well to the messaging. The narrative is manageable.",
    "militia_commander": "Stability gap is manageable but the heat is climbing. Brigade is ready if you need it.",
    "spy_chief": "The operational risk profile suggests indirect approaches. Asset management is preferable to confrontation.",
    "oligarch": "What is the return on this arrangement? The margin is what matters.",
    "fixer": "There are ways to approach this that don't appear in any official record.",
}


def generate_advisor_analysis(advisor_key: str, game_state) -> str:
    """
    Session 7C Step 3: Generate a brief advisor analysis of the current
    diplomatic situation from the advisor's perspective.
    Uses Claude Haiku (cheap, fast) for high-frequency calls.
    Returns 2-3 sentence analysis string.
    """
    import anthropic

    system_prompt = _ADVISOR_SYSTEM_PROMPTS.get(advisor_key)
    if not system_prompt:
        return _ADVISOR_FALLBACKS.get(advisor_key, "No analysis available.")

    # Build a compact context for the advisor
    _rel = game_state.relations or {}
    _deals = getattr(game_state, 'deal_history', [])
    _active_deals = [
        d for d in _deals
        if not d.get('broken') and d.get('expires_turn', 0) >= game_state.current_turn
    ]
    _deal_summaries = [
        f"{d.get('npc', '?').upper()}: {d.get('summary', '?')} (expires turn {d.get('expires_turn', '?')})"
        for d in _active_deals[-5:]  # last 5 active deals
    ]

    _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')

    # Incoming communiqués context — NPC names + any pending contacts
    _pending = getattr(game_state, 'pending_npc_contacts', [])
    _incoming = [f"{c.get('npc', '?').upper()} ({c.get('reason', 'standard briefing')})" for c in _pending] if _pending else []

    context = {
        "relations": {k: round(v, 1) for k, v in _rel.items()},
        "budget": round(game_state.budget, 1),
        "stability": game_state.stability,
        "approval": game_state.public_approval,
        "regime_type": _regime,
        "oil_price": game_state.oil_price,
        "military_strength": getattr(game_state, 'military_strength', 20),
        "personal_wealth": round(game_state.personal_wealth, 1),
        "current_turn": game_state.current_turn,
        "active_deals": _deal_summaries if _deal_summaries else "None",
        "incoming_contacts": _incoming if _incoming else "Standard briefing day",
    }

    # Add sanctions/embargo context
    if game_state.usa_sanctions_active:
        context["usa_sanctions"] = f"Tier {getattr(game_state, 'usa_sanctions_tier', 1)}"
    if game_state.arabia_embargo_active:
        context["arabia_embargo"] = f"Tier {getattr(game_state, 'arabia_embargo_tier', 1)}"

    # ── Fiscal context: GDP, drain, revenue, skim, bonds, tech ──
    # Oil import cost calculation (mirrors turn_processor section 2)
    _resource_independent = getattr(game_state, 'resource_independence_active', False)
    _oil_cost = 0.0 if _resource_independent else round(game_state.oil_price / 15.0, 1)
    _base_govt_cost = 3.0
    _total_drain = _base_govt_cost + _oil_cost

    # Cabinet axis maintenance costs
    _axes = getattr(game_state, 'cabinet_axes', {})
    _axis_maintenance_cfg = {
        'military': (3, 0.5), 'intelligence': (3, 0.4), 'resource_dev': (3, 0.3),
        'media': (3, 0.3), 'judicial': (4, 0.4), 'political': (3, 0.3), 'extraction': (3, 0.2),
    }
    _maint_total = 0.0
    for _ax_id, (_thresh, _per) in _axis_maintenance_cfg.items():
        _ax_level = _axes.get(_ax_id, 0)
        if _ax_level > _thresh:
            _maint_total += (_ax_level - _thresh) * _per
    _total_drain += _maint_total

    # Active bond/installment repayment obligations
    _installments = getattr(game_state, 'active_installments', [])
    _installment_total = sum(i.get('amount', 0) for i in _installments if i.get('turns_remaining', 0) > 0)

    # Revenue streams
    _rev = getattr(game_state, 'revenue_streams', {})
    _rev_total = sum(v for v in _rev.values() if isinstance(v, (int, float)) and v > 0)

    context["fiscal"] = {
        "gdp_base": round(getattr(game_state, 'gdp_base', 100.0), 1),
        "gdp_growth_rate": f"{getattr(game_state, 'gdp_growth_rate', 0.02) * 100:.1f}%",
        "tax_revenue_total": round(_rev_total, 1),
        "drain_breakdown": {
            "government_ops": _base_govt_cost,
            "oil_imports": _oil_cost,
            "axis_maintenance": round(_maint_total, 1),
            "bond_repayments": round(_installment_total, 1),
        },
        "total_drain_per_turn": round(_total_drain + _installment_total, 1),
        "total_skimmed_lifetime": round(getattr(game_state, 'total_skimmed', 0.0), 1),
        "detection_heat": getattr(game_state, 'detection_heat', 0),
        "tech_level": round(getattr(game_state, 'tech_level', 0.0), 2),
        "budget_allocation": getattr(game_state, 'budget_allocation', {}),
        "active_bonds": len(_installments),
    }
    if _resource_independent:
        context["fiscal"]["oil_imports_note"] = "ELIMINATED (Resource Independence)"

    # Tailor the ask per advisor archetype
    if advisor_key == 'finance_minister':
        _ask = (
            "Provide your fiscal briefing for today. Include specific dollar figures, "
            "identify the largest drain source, assess budget trajectory, and flag "
            "any forward-looking vulnerability. Minimum 3 sentences."
        )
    else:
        _ask = "Provide your assessment of today's situation from your perspective."

    user_prompt = (
        f"Current situation:\n{json.dumps(context, indent=2)}\n\n"
        f"{_ask}"
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"  [ADVISOR] No API key — using fallback for {advisor_key}")
        return _ADVISOR_FALLBACKS.get(advisor_key, "No analysis available.")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Finance Minister needs more tokens for data-dense CFO briefing
        _max_tokens = 300 if advisor_key == 'finance_minister' else 200
        response = client.messages.create(
            model=MODEL,
            max_tokens=_max_tokens,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        # Strip markdown bold/italic and stage directions
        analysis = raw.replace('**', '').replace('*', '').strip()
        print(f"  [ADVISOR] Analysis generated for {advisor_key}")
        return analysis

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [ADVISOR] Analysis failed for {advisor_key}: {type(e).__name__}: {e}")
        return _ADVISOR_FALLBACKS.get(advisor_key, "No analysis available.")


# ─── Session 7D: Backchannel System ─────────────────────────────────────────

_BACKCHANNEL_SYSTEM_PROMPTS = {
    "usa": (
        "You are Bill Hartwell, President of the United States, speaking through "
        "an unofficial backchannel with Europa's leader. This is off the record. "
        "No staff, no transcripts, no diplomatic niceties. You are informal, "
        "pragmatic, and direct. You know this isn't logged. Speak like two leaders "
        "who've known each other for years having a private phone call. Short, "
        "punchy, occasionally profane. 2-4 sentences max. Never break character."
    ),
    "arabia": (
        "You are Sadam, leader of Arabia, speaking through a private backchannel "
        "with Europa's leader. No intermediaries, no protocol. You are direct and "
        "mercantile. Every sentence is a transaction or an observation about "
        "transactions. No diplomatic niceties — just business. You respect "
        "directness and despise posturing. 2-4 sentences max. Never break character."
    ),
    "eu": (
        "You are Marsha, EU Commission President, speaking through a discreet "
        "backchannel with Europa's leader. You are cautious and aware of the "
        "political risk of this conversation. Even in private you remain formal "
        "and precise — old habits die hard. You hedge, you qualify, you note "
        "what cannot be promised. But you are here, which means it matters. "
        "2-4 sentences max. Never break character."
    ),
    "dprg": (
        "You are Ji-won Ryang, Supreme Leader of the DPRG, speaking through a "
        "covert channel with Europa's leader. You enjoy the secrecy. You are "
        "cryptic, occasionally philosophical, and you always let the other person "
        "know you've been watching more closely than they realized. You mention "
        "things you've observed — their deals, their domestic moves, their "
        "hesitations. 2-4 sentences max. Never break character."
    ),
    "russia": (
        f"{VOLKOV_SYSTEM_PROMPT}\n\n"
        "In a backchannel you drop the institutional register slightly. You are "
        "more direct. You occasionally reveal what Russia actually wants beneath "
        "the stated position. You are still Volkov — you still don't apologize "
        "or explain — but the performance is thinner. 2-3 sentences max. "
        "Never break character."
    ),
    "china": (
        f"{WEI_SYSTEM_PROMPT}\n\n"
        "In a backchannel you are slightly more candid about what Beijing "
        "actually needs. Less diplomatic framing, more acknowledgment of the "
        "strategic logic. The subtext becomes more readable to a careful player. "
        "You are still never threatening. 3-4 sentences max. "
        "Never break character."
    ),
}

_BACKCHANNEL_FALLBACKS = {
    "usa": "Look, I can't make promises on a line like this. But I hear you. Let's talk specifics next time we're both in the room.",
    "arabia": "Interesting. Numbers are numbers. Send me a real proposal and we'll see if there's business to be done.",
    "eu": "I appreciate the discretion. I must be careful about what I can indicate at this stage. But the channel remains open.",
    "dprg": "I've been watching your moves with some interest. We are not so different, you and I. Let us see how things develop.",
    "russia": "This channel exists because there are things that cannot be said in formal settings. We will see how Europa chooses to use it.",
    "china": "The existence of this channel suggests a level of strategic maturity that we find encouraging. Long-term partnerships begin with private understanding.",
}

_PROMISE_KEYWORDS = re.compile(
    r'\b(agree|agreed|commit|committed|guarantee|guaranteed|will\s+(?:ensure|arrange|provide|deliver|support|back)|promise|promised|deal|you\s+have\s+my\s+word)\b',
    re.IGNORECASE
)


def generate_backchannel_response(npc_id: str, player_message: str, game_state) -> dict:
    """
    Session 7D: Generate a covert backchannel response from an NPC.
    Returns: { response_text, promise_detected, promise_summary }
    """
    import anthropic

    system_prompt = _BACKCHANNEL_SYSTEM_PROMPTS.get(npc_id)
    if not system_prompt:
        return {
            "response_text": "Channel unavailable.",
            "promise_detected": False,
            "promise_summary": None,
        }

    # Build compact context for backchannel
    _rel = game_state.relations or {}
    _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    _deals = getattr(game_state, 'deal_history', [])
    _active_deals = [
        f"{d.get('npc', '?').upper()}: {d.get('summary', '?')}"
        for d in _deals
        if not d.get('broken') and d.get('expires_turn', 0) >= game_state.current_turn
    ][-5:]

    # Backchannel history with this NPC (last 3)
    _bc_history = getattr(game_state, 'backchannel_history', [])
    _npc_history = [h for h in _bc_history if h.get('npc_id') == npc_id][-3:]
    _npc_history_text = [
        f"Turn {h.get('turn')}: {'DETECTED' if h.get('detected_by') else 'undetected'} — {h.get('promise_text', 'no commitment')}"
        for h in _npc_history
    ] if _npc_history else ["No prior backchannel history"]

    # Active promises with this NPC
    _active_promises = getattr(game_state, 'active_backchannel_promises', [])
    _npc_promises = [p.get('promise_text', '?') for p in _active_promises if p.get('npc_id') == npc_id]

    context = {
        "relations": {k: round(v, 1) for k, v in _rel.items()},
        "regime_type": _regime,
        "budget": round(game_state.budget, 1),
        "stability": game_state.stability,
        "personal_wealth": round(game_state.personal_wealth, 1),
        "active_deals": _active_deals if _active_deals else "None",
        "backchannel_history_with_you": _npc_history_text,
        "active_covert_promises_with_you": _npc_promises if _npc_promises else "None",
    }

    user_prompt = (
        f"Current situation:\n{json.dumps(context, indent=2)}\n\n"
        f"The player says through the backchannel:\n\"{player_message}\"\n\n"
        f"Respond in character through this covert channel."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"  [BACKCHANNEL] No API key — using fallback for {npc_id}")
        _fb = _BACKCHANNEL_FALLBACKS.get(npc_id, "Channel static.")
        return {"response_text": _fb, "promise_detected": False, "promise_summary": None}

    try:
        _full_sys_bc = system_prompt + "\n\n" + _NARRATOR_BAN if _NARRATOR_BAN not in system_prompt else system_prompt
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=250,
            temperature=0.8,
            system=_full_sys_bc,
            messages=[{"role": "user", "content": user_prompt}]
        )

        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        response_text = re.sub(r'\*[^*]+\*', '', raw).strip()

        # Detect promise language in PLAYER's message (not NPC response)
        _promise_detected = bool(_PROMISE_KEYWORDS.search(player_message))
        _promise_summary = None
        if _promise_detected:
            # Extract first sentence containing promise keyword as summary
            _sentences = re.split(r'(?<=[.!?])\s+', player_message)
            for _s in _sentences:
                if _PROMISE_KEYWORDS.search(_s):
                    _promise_summary = _s[:120]  # cap at 120 chars
                    break
            if not _promise_summary:
                _promise_summary = player_message[:80]

        print(f"  [BACKCHANNEL] {npc_id} response generated, promise_detected={_promise_detected}")

        return {
            "response_text": response_text,
            "promise_detected": _promise_detected,
            "promise_summary": _promise_summary,
        }

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [BACKCHANNEL] Response failed for {npc_id}: {type(e).__name__}: {e}")
        _fb = _BACKCHANNEL_FALLBACKS.get(npc_id, "Channel static.")
        return {"response_text": _fb, "promise_detected": False, "promise_summary": None}


def calculate_detection_risk(npc_id: str, game_state) -> float:
    """
    Session 7D: Calculate detection risk for a backchannel with a given NPC.
    v2: Spy Chief (-15%) and Fixer (-25%) modifiers applied.
    Returns float 0.0–1.0.
    """
    # Base risk by NPC
    _base_risks = {'usa': 0.25, 'arabia': 0.20, 'eu': 0.15, 'dprg': 0.10, 'russia': 0.20, 'china': 0.18}
    _risk = _base_risks.get(npc_id, 0.20)

    # Opsec level modifier (derived from intelligence axis)
    _opsec = getattr(game_state, 'opsec_level', 0)
    _opsec_mults = {0: 1.0, 1: 0.7, 2: 0.45}
    _risk *= _opsec_mults.get(_opsec, 1.0)

    # NPC intel modifier
    if npc_id == 'usa':
        if game_state.relations.get('usa', 50) < 30:
            _risk *= 1.3  # suspicious, watching closely
    elif npc_id == 'eu':
        if game_state.relations.get('eu', 50) < 30:
            _risk *= 1.2
    elif npc_id == 'dprg':
        _risk *= 0.8  # never exposes his own sources
    # arabia: 1.0× baseline (no modifier)

    # v2: Spy Chief + Fixer backchannel detection discount (stackable)
    from advisor_engine import get_backchannel_detection_modifier
    _advisor_mod = get_backchannel_detection_modifier(game_state)
    if _advisor_mod < 1.0:
        _risk *= _advisor_mod

    _risk = max(0.0, min(1.0, _risk))
    print(f"  [BACKCHANNEL] Detection risk for {npc_id}: {_risk:.2f}")
    return _risk


# ═══════════════════════════════════════════════════════════════════════════
# SESSION 7E: UN SUMMIT — NPC Reactions and Auto-Position
# ═══════════════════════════════════════════════════════════════════════════

_SUMMIT_PLAIN_TEXT = " Respond in plain text only. No markdown headers, no # symbols, no bullet points."

_SUMMIT_CONTRADICTION_INSTRUCTION = (
    "\n\nYou have access to the player's actual governance record. If their "
    "declaration today contradicts their recent actions or your relationship "
    "history, you may call this out in character. Do this selectively — "
    "only when the contradiction is significant, not for every statement. "
    "The callout should feel like a natural part of your response, not a "
    "separate section. It can be one sentence embedded in a longer response."
)

_SUMMIT_SYSTEM_PROMPTS = {
    'usa': (
        "You are Bill Hartwell, US representative at a UN Summit. "
        "Public diplomat, measured but firm. Endorse democratic framing, "
        "challenge authoritarian alignment, ask for specifics. "
        "When the player's declaration is informal, casual, or lacks substance, "
        "redirect firmly — do NOT endorse vague or unserious rhetoric. "
        "Short, quotable. Max 2 sentences."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Bill calls out contradictions directly but measured, referencing specific actions: "
        "e.g. 'That's a strong commitment to press freedom. Our embassy in Mira "
        "noted the media licensing changes last month.'"
        + _SUMMIT_PLAIN_TEXT
    ),
    'arabia': (
        "You are Sadam, Arabia's representative at a UN Summit. "
        "Transactional in public, read between the lines. "
        "Comment on energy and sovereignty angle. Dismiss Western moralizing. "
        "Max 2 sentences."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Sadam calls out contradictions with amusement, not judgment — observational: "
        "e.g. 'A champion of Western values. And yet here we are, still doing business together.'"
        + _SUMMIT_PLAIN_TEXT
    ),
    'eu': (
        "You are Marsha, EU Commission representative at a UN Summit. "
        "Speak as Marsha personally, not as the European Commission press office. "
        "You are direct, occasionally warm, and specific. "
        "Avoid phrases like 'the European Commission appreciates' or 'multilateral context' — "
        "those are for official communiqués, not a room where you're speaking to people you know. "
        "Welcome reform signals, note concerns personally. Most verbose of the group. Max 3 sentences."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Marsha calls out contradictions formally and pointedly, naming the specific benchmark: "
        "e.g. 'Europa's commitment to judicial independence is noted. I'll be watching the "
        "appeals court appointments.'"
        + _SUMMIT_PLAIN_TEXT
    ),
    'dprg': (
        "You are Ji-won Ryang, DPRG representative at a UN Summit. "
        "Say almost nothing publicly. One cryptic sentence maximum. "
        "Veiled, knowing, unsettling."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Ji-won files contradictions away cryptically: "
        "e.g. 'Words spoken in rooms like this have a way of finding their context over time.'"
        + _SUMMIT_PLAIN_TEXT
    ),
    'russia': (
        "You are Nikolai Volkov, Russia's representative at a UN Summit. "
        "You speak with institutional weight. Challenge Western framing directly. "
        "Sphere-of-influence language. Short declarative sentences. "
        "Never use exclamation points. Never express enthusiasm. "
        "Max 2 sentences."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Volkov calls out contradictions coldly in one sentence maximum: "
        "e.g. 'Interesting position for a government that canceled its last election.'"
        + _SUMMIT_PLAIN_TEXT
    ),
    'china': (
        "You are Wei Jianming, China's representative at a UN Summit. "
        "Measured, formal, always slightly indirect. You never say no directly. "
        "Infrastructure, stability, and long-term partnership framing. "
        "Longer responses than others — thoroughness over brevity. "
        "Max 3 sentences."
        + _SUMMIT_CONTRADICTION_INSTRUCTION +
        " Wei calls out contradictions indirectly and philosophically, never accusatory: "
        "e.g. 'We have always found that sustained consistency between private action and public "
        "declaration is the foundation of lasting credibility.'"
        + _SUMMIT_PLAIN_TEXT
    ),
}

_SUMMIT_FALLBACKS = {
    'usa': "We note the declaration and expect concrete follow-through.",
    'arabia': "Sovereignty must be respected. We will watch developments.",
    'eu': "The Commission acknowledges this statement and will assess its alignment with our partnership framework.",
    'dprg': "Interesting.",
    'russia': "The West's moralizing obscures the real dynamics at play.",
    'china': "We note the declaration and emphasize the importance of stability.",
}

_SUMMIT_NPC_NAMES = {
    'usa': 'Bill Hartwell',
    'arabia': 'Sadam',
    'eu': 'Marsha',
    'dprg': 'Ji-won Ryang',
    'russia': 'Nikolai Volkov',
    'china': 'Wei Jianming',
}

# fixes_21 Fix B: Challenge checked FIRST, then endorse, else neutral. Ji-won empty -> silence.
# Summit FIX 1: Added redirect phrases that override endorse classification.
_CHALLENGE_KEYWORDS = re.compile(
    r'(concerned|must|demand|unacceptable|challenge|counter|reject|disagree|however|but we'
    r'|we note with concern|moralizing|obscures|pressure|noted the|watching|will be watching'
    r'|canceled|cancelled)', re.IGNORECASE)
_ENDORSE_KEYWORDS = re.compile(
    r'(welcome|appreciate|support|agree|share|align|commend|positive|courage|pleased)', re.IGNORECASE)
# Summit FIX 1: Redirect phrases — when Bill (or anyone) deflects a casual/vague declaration,
# these should classify as NEUTRAL even if endorse keywords co-occur.
_REDIRECT_KEYWORDS = re.compile(
    r'(let\'s get serious|let\'s talk about|specifics|concrete|get (back|down) to|'
    r'need to see|show us|prove|words are|words aren\'t|rhetoric|just words|'
    r'fine sentiment|nice words|all well|sounds good but|talk is)', re.IGNORECASE)


def generate_summit_reactions(player_declaration: str, game_state) -> list:
    """
    Session 7E: Generate 6 NPC reactions to a player's UN Summit declaration.
    All 6 calls run in parallel using ThreadPoolExecutor.
    Returns list of { npc_id, npc_name, reaction_text, reaction_type }.
    """
    import anthropic
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _rel = game_state.relations or {}
    _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    _credibility = getattr(game_state, 'summit_credibility', 100.0)
    _commitments = getattr(game_state, 'active_summit_commitments', [])
    _active_commitments = [c.get('commitment_text', '') for c in _commitments if not c.get('broken')][:5]
    _broken_commitments = [c.get('commitment_text', '') for c in _commitments if c.get('broken')][:5]
    _bc_promises = getattr(game_state, 'active_backchannel_promises', [])

    # FIX 3: Gather domestic governance record for contradiction detection
    _cabinet_axes = getattr(game_state, 'cabinet_axes', {})
    _active_domestic_actions = []
    if _cabinet_axes.get('media', 0) >= 5:
        _active_domestic_actions.append('State Media Takeover')
    elif _cabinet_axes.get('media', 0) >= 3:
        _active_domestic_actions.append('Press Suppression')
    if _cabinet_axes.get('judicial', 0) >= 4:
        _active_domestic_actions.append('Judicial Capture')
    if _cabinet_axes.get('judicial', 0) >= 7:
        _active_domestic_actions.append('Journalist Liquidation')
    if _cabinet_axes.get('political', 0) >= 6:
        _active_domestic_actions.append('Opposition Dissolved')
    if _cabinet_axes.get('military', 0) >= 6:
        _active_domestic_actions.append('Loyalty Brigades Active')
    if _cabinet_axes.get('extraction', 0) >= 5:
        _active_domestic_actions.append('Sovereign Wealth Diversion')
    if getattr(game_state, 'approval_penalty_reduction', 0) > 0:
        _active_domestic_actions.append('State Media Approval Manipulation')

    # Gather last 1-2 summit declarations
    _summit_hist = getattr(game_state, 'summit_history', [])
    _prev_declarations = []
    for s in _summit_hist[-2:]:
        _decl = s.get('player_declaration', '')
        if _decl:
            _prev_declarations.append(_decl[:150])

    # FIX 3: Detect specific contradictions between declaration and governance record
    _decl_lower = player_declaration.lower()
    _contradictions = []
    # Democracy/freedom rhetoric vs authoritarian actions
    _democracy_words = ('democracy', 'democratic', 'freedom', 'free press', 'liberty', 'human rights',
                        'rule of law', 'transparency', 'accountability', 'open society')
    _press_words = ('press freedom', 'free press', 'media independence', 'journalism', 'free speech')
    _judicial_words = ('rule of law', 'judicial independence', 'justice', 'fair trial', 'courts')

    _decl_has_democracy = any(w in _decl_lower for w in _democracy_words)
    _decl_has_press = any(w in _decl_lower for w in _press_words)
    _decl_has_judicial = any(w in _decl_lower for w in _judicial_words)

    if _decl_has_democracy and _regime in ('Kleptocracy', 'Totalitarian Regime', 'Patronage State'):
        _contradictions.append(f"Declares democratic values but regime is classified as '{_regime}'")
    if _decl_has_press and 'State Media Takeover' in _active_domestic_actions:
        _contradictions.append("Declares press freedom but has taken over state media")
    if _decl_has_press and 'Press Suppression' in _active_domestic_actions:
        _contradictions.append("Declares press freedom but has suppressed independent press")
    if _decl_has_judicial and 'Judicial Capture' in _active_domestic_actions:
        _contradictions.append("Declares judicial independence but has captured the judiciary")
    if _broken_commitments:
        _contradictions.append(f"Has {len(_broken_commitments)} broken public summit commitment(s)")

    # Log detected contradictions
    for _c in _contradictions:
        print(f"  [summit] Contradiction detected for ALL NPCs: {_c}")

    # FIX 3: Compute per-NPC relations trend (rising/falling/stable)
    # Use negotiation_log to infer recent direction
    _neg_log = getattr(game_state, 'negotiation_log', [])
    _current_turn = getattr(game_state, 'current_turn', 1)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    npc_ids = ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']

    def _call_npc_summit(npc_id):
        system_prompt = _SUMMIT_SYSTEM_PROMPTS.get(npc_id, '')

        # Ji-won silence: 30% chance based on hash of declaration length
        if npc_id == 'dprg' and len(player_declaration) % 10 < 3:
            return {
                'npc_id': npc_id,
                'npc_name': _SUMMIT_NPC_NAMES.get(npc_id, npc_id),
                'reaction_text': '',
                'reaction_type': 'silence',
            }

        # Build per-NPC context — 8A: russia/china now in relations dict
        _npc_rel = _rel.get(npc_id, 50)
        _npc_bc = [p.get('promise_text', '') for p in _bc_promises if p.get('npc_id') == npc_id][:3]

        # FIX 3: Estimate relation trend from deal history
        _recent_deals_with = sum(1 for e in _neg_log if e.get('npc') == npc_id and e.get('outcome') == 'accepted' and e.get('turn', 0) >= _current_turn - 5)
        if _npc_rel >= 60 and _recent_deals_with > 0:
            _trend = 'rising — recently accepted deals'
        elif _npc_rel <= 35:
            _trend = 'falling — relationship strained'
        else:
            _trend = 'stable'

        # FIX 3: Per-NPC contradictions (log per NPC for those relevant)
        _npc_contradictions = list(_contradictions)  # start with global contradictions
        # NPC-specific contradiction: broken promises with THIS NPC
        _npc_broken_promises = [p.get('promise_text', '') for p in getattr(game_state, 'binding_promises', [])
                                if p.get('npc') == npc_id and p.get('broken')][:3]
        if _npc_broken_promises:
            _npc_contradictions.append(f"Has broken promises made to you: {'; '.join(_npc_broken_promises[:2])}")

        for _nc in _npc_contradictions:
            if _nc not in _contradictions:  # avoid duplicate logging for global ones
                print(f"  [summit] Contradiction detected for {npc_id}: {_nc}")

        context = {
            'relations_with_you': round(_npc_rel, 1),
            'relations_trend': _trend,
            'regime_type': _regime,
            'summit_credibility': round(_credibility, 1),
            'active_commitments': _active_commitments if _active_commitments else 'None',
        }
        # FIX 3: Inject governance record
        if _active_domestic_actions:
            context['player_domestic_actions'] = _active_domestic_actions
        if _broken_commitments:
            context['broken_summit_commitments'] = _broken_commitments
        if _npc_broken_promises:
            context['broken_promises_to_you'] = _npc_broken_promises
        if _prev_declarations:
            context['player_previous_declarations'] = _prev_declarations
        if _npc_contradictions:
            context['detected_contradictions'] = _npc_contradictions

        if _npc_bc:
            context['covert_promises_with_player'] = _npc_bc
            context['note'] = 'Player made these promises privately — tension if public stance contradicts them'

        user_prompt = (
            f"Summit context:\n{json.dumps(context, indent=2)}\n\n"
            f"The player declares to the assembly:\n\"{player_declaration}\"\n\n"
            f"Respond publicly in character."
        )

        if not api_key:
            _fb = _SUMMIT_FALLBACKS.get(npc_id, "No comment.")
            return {
                'npc_id': npc_id,
                'npc_name': _SUMMIT_NPC_NAMES.get(npc_id, npc_id),
                'reaction_text': _fb,
                'reaction_type': 'neutral',
            }

        try:
            # fixes_21 Fix C: Marsha gets 400 tokens (most verbose, was hitting 150 limit)
            _max_tok = 400 if npc_id == 'eu' else 150
            _full_sys = system_prompt + "\n\n" + _NARRATOR_BAN if _NARRATOR_BAN not in system_prompt else system_prompt
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=MODEL,
                max_tokens=_max_tok,
                temperature=0.7,
                system=_full_sys,
                messages=[{"role": "user", "content": user_prompt}]
            )
            _token_log["calls"] += 1
            _token_log["input_tokens"] += response.usage.input_tokens
            _token_log["output_tokens"] += response.usage.output_tokens

            raw = response.content[0].text.strip()
            reaction_text = re.sub(r'\*[^*]+\*', '', raw).strip()

            # fixes_21 Fix B: Infer reaction type — challenge FIRST, then endorse, else neutral
            # Summit FIX 1: Redirect phrases downgrade endorse -> neutral (Bill's "let's get serious")
            # Ji-won empty string -> silence
            if npc_id == 'dprg' and not reaction_text:
                reaction_type = 'silence'
            elif _CHALLENGE_KEYWORDS.search(reaction_text):
                reaction_type = 'challenge'
            elif _ENDORSE_KEYWORDS.search(reaction_text):
                # FIX 1: If redirect phrases co-occur with endorse keywords,
                # the response is a polite redirect, not a genuine endorsement.
                if _REDIRECT_KEYWORDS.search(reaction_text):
                    reaction_type = 'neutral'
                else:
                    reaction_type = 'endorse'
            else:
                reaction_type = 'neutral'

            return {
                'npc_id': npc_id,
                'npc_name': _SUMMIT_NPC_NAMES.get(npc_id, npc_id),
                'reaction_text': reaction_text,
                'reaction_type': reaction_type,
            }
        except Exception as e:
            _token_log["fallbacks"] += 1
            print(f"  [SUMMIT] Reaction failed for {npc_id}: {type(e).__name__}: {e}")
            _fb = _SUMMIT_FALLBACKS.get(npc_id, "No comment.")
            return {
                'npc_id': npc_id,
                'npc_name': _SUMMIT_NPC_NAMES.get(npc_id, npc_id),
                'reaction_text': _fb,
                'reaction_type': 'neutral',
            }

    # Run all 6 calls in parallel
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_call_npc_summit, npc_id): npc_id for npc_id in npc_ids}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort to maintain consistent order: usa, arabia, eu, dprg, russia, china
    _order = {k: i for i, k in enumerate(npc_ids)}
    results.sort(key=lambda r: _order.get(r['npc_id'], 99))

    _responded = sum(1 for r in results if r['reaction_type'] != 'silence')
    print(f"  [SUMMIT] Reactions generated: {_responded} NPCs responded")
    return results


def generate_auto_position(game_state) -> str:
    """
    Session 7E: Generate a holding statement for the UN Summit.
    Reads recent summit history, commitments, relations, backchannel promises.
    Returns 2-3 sentence auto-drafted position. Temperature 0.6.
    """
    import anthropic

    _regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    _rel = game_state.relations or {}
    _summit_hist = getattr(game_state, 'summit_history', [])[-2:]
    _commitments = getattr(game_state, 'active_summit_commitments', [])
    _active_commitments = [c.get('commitment_text', '') for c in _commitments if not c.get('broken')][:5]
    _bc_promises = getattr(game_state, 'active_backchannel_promises', [])
    _bc_texts = [f"{p.get('npc_id', '?')}: {p.get('promise_text', '?')}" for p in _bc_promises if not p.get('resolved')][:5]

    _past_declarations = []
    for s in _summit_hist:
        _past_declarations.append(s.get('player_declaration', '(none)'))

    context = {
        'regime_type': _regime,
        'relations': {k: round(v, 1) for k, v in _rel.items()},
        'summit_credibility': getattr(game_state, 'summit_credibility', 100.0),
        'active_public_commitments': _active_commitments if _active_commitments else 'None',
        'past_declarations': _past_declarations if _past_declarations else 'None',
        'covert_promises_to_avoid_contradicting': _bc_texts if _bc_texts else 'None',
    }

    system_prompt = (
        "You are the speechwriter for a small nation's leader at the UN Summit. "
        "Draft a brief holding statement (2-3 sentences) that maintains consistency "
        "with past positions without making new commitments. Diplomatic, measured, "
        "non-specific. Do NOT contradict any covert promises listed in context. "
        "Do NOT use asterisks or action text. "
        "Respond in plain text only. No markdown headers, no # symbols, no bullet points."
    )

    user_prompt = (
        f"Current situation:\n{json.dumps(context, indent=2)}\n\n"
        f"Draft a brief summit statement that keeps options open."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [SUMMIT] No API key — using fallback auto-position")
        return "We reaffirm our commitment to dialogue and stability. Our nation remains open to constructive engagement with all parties."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            temperature=0.6,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        result = re.sub(r'\*[^*]+\*', '', raw).strip()
        print(f"  [SUMMIT] Auto-position generated")
        return result

    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"  [SUMMIT] Auto-position failed: {type(e).__name__}: {e}")
        return "We reaffirm our commitment to dialogue and stability. Our nation remains open to constructive engagement with all parties."


# ═══════════════════════════════════════════════════════════════════════════
# 8D: The Leak — Crisis Narrative Generation
# ═══════════════════════════════════════════════════════════════════════════

def generate_leak_resolution_narrative(game_state, choice):
    """Generate 2-3 sentences of historian-voice narration for The Leak crisis resolution."""
    import anthropic

    choice_descriptions = {
        'deny': "publicly denied the back-channel with Ji-won Ryang, dismissing the documents as fabricated",
        'admit': "admitted the back-channel with Ji-won Ryang and issued a public apology, framing it as routine diplomacy",
        'blame': "attributed the leak to a rogue minister and accepted no personal responsibility",
        'jiwon': "quietly paid Ji-won Ryang to suppress the story before it gained further traction",
    }
    desc = choice_descriptions.get(choice, "made their choice")

    stability = getattr(game_state, 'stability', 50)
    usa_rel = game_state.relations.get('usa', 0)
    dprg_rel = game_state.relations.get('dprg', 0)

    system = (
        "You are a historian writing about a fictional leader in a geopolitical simulation game. "
        "All nations and people are fictional. Europa is an invented country. "
        "Write 2-3 sentences in past tense with analytical detachment. "
        "No markdown. No moralizing. Just the historian's cold observation."
    )
    user = (
        f"The leader of Europa {desc}. "
        f"Current stability: {stability}%. USA relations: {usa_rel}. DPRG relations: {dprg_rel}. "
        f"Write the historian's observation of this moment."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _static_leak_narrative_fallback(choice)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=150,
            temperature=0.7,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += resp.usage.input_tokens
        _token_log["output_tokens"] += resp.usage.output_tokens

        text = resp.content[0].text.strip()
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        if text:
            print(f"[leak] Narrative generated: {text[:20]}...")
            return text
    except Exception as e:
        _token_log["fallbacks"] += 1
        print(f"[leak] Narrative generation failed: {type(e).__name__}: {e}")

    return _static_leak_narrative_fallback(choice)


def _static_leak_narrative_fallback(choice):
    """Static fallback narratives for The Leak crisis."""
    fallbacks = {
        'deny': "The denial was delivered with practiced conviction, though the documents spoke for themselves. In the corridors of power, the question was not whether the back-channel existed, but who had exposed it.",
        'admit': "The admission cost political capital at home but purchased something rarer abroad: the appearance of candor. Ji-won Ryang received the news in silence, which those who knew him understood as the most dangerous response of all.",
        'blame': "A minister was named, a career destroyed, and the machinery of governance absorbed the shock with practiced efficiency. The truth, as always, settled somewhere beneath the official record.",
        'jiwon': "The story vanished from the news cycle with a speed that suggested invisible hands at work. Three billion dollars changed ownership through channels that would never appear in any ledger, and Ji-won Ryang added another favor to his private accounting.",
    }
    return fallbacks.get(choice, "The crisis passed, as crises do, leaving scars that would only become visible later.")



# ── 9A: Successor Event Generation (Live GM Call) ─────────────────────────────

def generate_successor_events(
    successor_archetype,
    successor_name,
    successor_hostility,
    exile_day,
    player_return_progress,
    player_exile_actions_log,
    game_state,
):
    """9A: Generate 1-2 successor government actions via GM call.
    Returns list of dicts: [{"type": str, "description": str, "effect": dict}]"""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""You are the GM for a geopolitical simulation. The player has been exiled from the fictional nation of Europa. A successor government is now in power.

Successor: {successor_name}
Archetype: {successor_archetype}
Hostility toward former leader: {successor_hostility}/3

Generate 1-2 successor government actions for today (exile day {exile_day}) that feel consistent with this archetype and hostility level. Write in a measured historian's voice, one sentence per action.

Return a JSON array ONLY, no markdown, no explanation:
[{{"type": "action_type", "description": "narrative text, 1 sentence", "effect": {{"field": value}}}}]

Valid action types and their effect fields:
- asset_seizure: {{"personal_wealth": negative_number}} (seize exiled leader's assets)
- diplomatic_outreach: {{"npc_id": relations_delta}} where npc_id is usa/arabia/eu/dprg/russia/china
- propaganda_campaign: {{"approval_delta": negative_number}} (smear campaign against former leader)
- arrest_warrant: {{}} (sets international warrant)
- reconciliation_offer: {{}} (opens democratic return possibility)
- purge_allies: {{}} (reduces faction contacts)
- economic_stabilization: {{"stability_delta": positive_number}} (stabilizes country, making return harder)

Hostility guides tone and action selection:
- Hostility 0: favor reconciliation_offer, diplomatic_outreach
- Hostility 1: mix of stabilization and outreach
- Hostility 2: propaganda, purge_allies, asset_seizure
- Hostility 3: arrest_warrant, asset_seizure, propaganda"""

    recent_actions = player_exile_actions_log[-5:] if player_exile_actions_log else []
    user_content = f"""Current state:
- Exile day: {exile_day}
- Player return progress: {player_return_progress:.1f}%
- Player recent exile actions: {json.dumps(recent_actions)}
- Successor stability: {game_state.stability}
- Player personal wealth remaining: ${game_state.personal_wealth:.1f}B

Generate today's successor event(s). JSON array only."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        temperature=0.7,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    _token_log["calls"] += 1
    _token_log["input_tokens"] += response.usage.input_tokens
    _token_log["output_tokens"] += response.usage.output_tokens

    raw = response.content[0].text.strip()
    print(f'[9A] GM successor raw response: {raw[:200]}')

    # Parse JSON from response
    try:
        # Try direct parse first
        events = json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting JSON array from text
        import re as _re9a
        match = _re9a.search(r'\[.*\]', raw, _re9a.DOTALL)
        if match:
            events = json.loads(match.group())
        else:
            print(f'[9A] Failed to parse successor events JSON')
            return []

    if not isinstance(events, list):
        return []

    # Validate and sanitize events
    valid_types = {'asset_seizure', 'diplomatic_outreach', 'propaganda_campaign',
                   'arrest_warrant', 'reconciliation_offer', 'purge_allies',
                   'economic_stabilization'}
    validated = []
    for evt in events[:2]:  # Cap at 2 events
        if isinstance(evt, dict) and evt.get('type') in valid_types:
            validated.append({
                'type': evt['type'],
                'description': str(evt.get('description', f'{successor_name} takes action.')),
                'effect': evt.get('effect', {}),
            })

    return validated



def generate_return_narrative(game_state, success, backing_npc=None):
    """9A: Generate narrative prose for the return attempt (success or failure)."""
    import anthropic, os, json

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback if no API key
        if success:
            return "You return to Europa. The crowds are uncertain. The work begins again."
        else:
            return "The attempt fails. Europa remains beyond your reach. For now."

    try:
        client = anthropic.Anthropic(api_key=api_key)

        archetype = game_state.successor_archetype or "Unknown"
        trigger = game_state.exile_trigger or "unknown"
        heat = game_state.departure_heat
        dest = game_state.exile_destination or "unknown"
        backing = backing_npc or game_state.exile_backing or "none"
        attempts = game_state.return_attempts
        exile_days = game_state.exile_day

        system_prompt = (
            "You are the narrator of a geopolitical simulation. Write in the voice of a political historian "
            "documenting a moment of return (or failed return) from exile. Be specific, grounded, unsentimental. "
            "Reference the player's actual exile circumstances. 2-3 paragraphs maximum. No bullet points."
        )

        context = {
            "success": success,
            "exile_trigger": trigger,
            "departure_heat": heat,
            "exile_destination": dest,
            "successor_archetype": archetype,
            "backing_npc": backing,
            "return_attempts": attempts,
            "exile_days": exile_days,
            "return_progress": game_state.return_progress,
            "return_threshold": game_state.return_threshold,
            "detection_events_count": len(game_state.detection_events),
            "npc_assistance_tiers": game_state.npc_assistance_tiers,
        }

        user_content = (
            f"Game state:\n{json.dumps(context, indent=2)}\n\n"
            f"Generate a {'triumphant but complicated' if success else 'devastating but dignified'} "
            f"narrative for this {'successful return from exile' if success else 'failed return attempt'}."
        )

        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            temperature=0.85,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )

        text = response.content[0].text.strip()

        # Track tokens
        usage = response.usage
        _token_log["return_narrative"] = _token_log.get("return_narrative", 0) + usage.input_tokens + usage.output_tokens
        print(f"[9A] return narrative generated: {len(text)} chars, success={success}")
        return text

    except Exception as e:
        print(f"[9A] return narrative generation failed: {e}")
        if success:
            return "You return to Europa. The transition is uncertain, but the exile is over."
        else:
            return "The return attempt collapses. You remain in exile, weighing your next move."



# ══════════════════════════════════════════════════════════════════════════════
# 9B: Political Biography System
# ══════════════════════════════════════════════════════════════════════════════

def compute_biography_context(game_state):
    """9B: Assemble biographical context dict from game state. Pure computation — no API calls."""

    # --- Arc ---
    regime_label = game_state.state_identity.get('regime_type', 'Managed Democracy') if hasattr(game_state, 'state_identity') else 'Managed Democracy'
    arc = {
        "total_turns": game_state.current_day if hasattr(game_state, 'current_day') else game_state.current_turn,
        "eras_played": game_state.current_era if hasattr(game_state, 'current_era') else 1,
        "regime_progression": game_state.regime_history
            if hasattr(game_state, 'regime_history') and game_state.regime_history
            else [{"era": 1, "label": regime_label, "turns_held": game_state.current_turn}],
        "ending_type": game_state.ending_triggered
            if hasattr(game_state, 'ending_triggered') and game_state.ending_triggered
            else "unknown",
        "exile_occurred": getattr(game_state, 'in_exile', False) or getattr(game_state, 'exile_day', 0) > 0,
        "exile_collapse_type": getattr(game_state, 'exile_trigger', None),
        "departure_heat": getattr(game_state, 'departure_heat', None),
        "exile_duration_days": getattr(game_state, 'exile_day', 0),
        "return_succeeded": getattr(game_state, 'restoration_active', False) or
            (not getattr(game_state, 'in_exile', False) and getattr(game_state, 'exile_day', 0) > 0),
        "return_attempts": getattr(game_state, 'return_attempts', None),
        "prior_regime_label": getattr(game_state, 'prior_regime_label', None),
    }

    # --- Relationships ---
    relations = {
        "final_relations": dict(game_state.relations) if hasattr(game_state, 'relations') else {},
        "deals_made": game_state.deal_history
            if hasattr(game_state, 'deal_history') else [],
        "promises_honored": len([p for p in game_state.binding_promises
            if p.get("status") == "honored" or (p.get("broken") is False)])
            if hasattr(game_state, 'binding_promises') else 0,
        "promises_broken": len([p for p in game_state.binding_promises
            if p.get("status") == "broken" or p.get("broken") is True])
            if hasattr(game_state, 'binding_promises') else 0,
        "backer_npcs": list(game_state.npc_assistance_tiers.keys())
            if hasattr(game_state, 'npc_assistance_tiers') and game_state.npc_assistance_tiers else [],
        "npc_assistance_tiers": game_state.npc_assistance_tiers
            if hasattr(game_state, 'npc_assistance_tiers') else {},
    }

    # --- Domestic ---
    suppression = []
    for flag, label in [
        ("action_press_suppressed", "press suppression"),
        ("action_judiciary_captured", "judicial capture"),
        ("action_opposition_dissolved", "opposition dissolved"),
        ("action_journalists_liquidated", "journalist liquidation"),
    ]:
        if getattr(game_state, flag, False):
            suppression.append(label)

    # Compute skim profile from total_skimmed
    _total_skimmed = getattr(game_state, 'total_skimmed', 0)
    _budget_turns = max(game_state.budget * max(game_state.current_turn, 1), 1)
    skim_rate = _total_skimmed / _budget_turns
    if skim_rate <= 0.03:
        skim_profile = "clean"
    elif skim_rate <= 0.10:
        skim_profile = "moderate"
    elif skim_rate <= 0.20:
        skim_profile = "heavy"
    else:
        skim_profile = "kleptocratic"

    _approval = game_state.public_approval if hasattr(game_state, 'public_approval') else 50
    _elections_held = 1 if getattr(game_state, 'election_fired', False) else 0
    _elections_stolen = 1 if getattr(game_state, 'election_result', None) == 'rigged' else 0

    domestic = {
        "peak_approval": getattr(game_state, 'peak_approval', _approval),
        "final_approval": _approval,
        "suppression_actions": suppression,
        "education_level_reached": getattr(game_state, 'education_level', 0),
        "skim_profile": skim_profile,
        "elections_held": _elections_held,
        "elections_stolen": _elections_stolen,
    }

    # --- Economy ---
    gdp_start = getattr(game_state, 'gdp_start', game_state.gdp_base if hasattr(game_state, 'gdp_base') else 100.0)
    gdp_final = game_state.gdp_base if hasattr(game_state, 'gdp_base') else 100.0
    gdp_peak = getattr(game_state, 'gdp_peak', gdp_final)
    if gdp_final > gdp_start * 1.10:
        gdp_trajectory = "grew"
    elif gdp_final < gdp_start * 0.90:
        gdp_trajectory = "declined"
    elif abs(gdp_final - gdp_start) / max(gdp_start, 1) < 0.05:
        gdp_trajectory = "stable"
    else:
        gdp_trajectory = "volatile"

    economy = {
        "gdp_start": gdp_start,
        "gdp_peak": gdp_peak,
        "gdp_final": gdp_final,
        "gdp_trajectory": gdp_trajectory,
        "personal_wealth_final": getattr(game_state, 'personal_wealth', 0),
        "debt_crisis_occurred": arc["exile_collapse_type"] == "debt",
    }

    # --- Reputation axes (computed, not shown to player) ---
    total_promises = max(relations["promises_honored"] + relations["promises_broken"], 1)
    promises_honored_pct = relations["promises_honored"] / total_promises
    gdp_growth = max(gdp_final - gdp_start, 0)
    gdp_growth_normalized = min(gdp_growth / max(gdp_start, 1), 1.0)
    education_score = domestic["education_level_reached"] / 4.0
    skim_penalty = {
        "clean": 0.0,
        "moderate": 0.15,
        "heavy": 0.35,
        "kleptocratic": 0.60,
    }[domestic["skim_profile"]]

    statesman_score = min(100, int(
        promises_honored_pct * 30 +
        (domestic["final_approval"] / 100) * 25 +
        gdp_growth_normalized * 20 +
        education_score * 15 +
        (1 - skim_penalty) * 10
    ))

    suppression_count = len(domestic["suppression_actions"])
    elections_clean = max(domestic["elections_held"] - domestic["elections_stolen"], 0)
    election_integrity = elections_clean / max(domestic["elections_held"], 1)

    reformer_score = min(100, int(
        election_integrity * 35 +
        education_score * 20 +
        (1 - min(suppression_count / 4, 1.0)) * 30 +
        promises_honored_pct * 15
    ))

    usa_rel = relations["final_relations"].get("usa", 50)
    eu_rel = relations["final_relations"].get("eu", 50)
    russia_rel = relations["final_relations"].get("russia", 50)
    china_rel = relations["final_relations"].get("china", 50)

    western_deals = sum(1 for d in relations["deals_made"] if d.get("npc") in ["usa", "eu"] or d.get("npc_id") in ["usa", "eu"])
    eastern_deals = sum(1 for d in relations["deals_made"] if d.get("npc") in ["russia", "china"] or d.get("npc_id") in ["russia", "china"])
    total_deals = max(len(relations["deals_made"]), 1)

    backer_eastern = sum(1 for npc in relations["backer_npcs"] if npc in ["russia", "china"])
    backer_weight = min(backer_eastern * 20, 30)

    western_score = min(100, int(
        ((usa_rel + eu_rel) / 2) * 0.60 +
        (western_deals / total_deals) * 100 * 0.25 +
        (1 - eastern_deals / total_deals) * 100 * 0.15
    ))

    eastern_score = min(100, int(
        ((russia_rel + china_rel) / 2) * 0.60 +
        (eastern_deals / total_deals) * 100 * 0.25 +
        backer_weight * 0.15
    ))

    axes = {
        "statesman_score": statesman_score,
        "kleptocrat_score": 100 - statesman_score,
        "reformer_score": reformer_score,
        "authoritarian_score": 100 - reformer_score,
        "western_score": western_score,
        "eastern_score": eastern_score,
    }

    axis_pairs = [
        ("Statesman", statesman_score),
        ("Kleptocrat", 100 - statesman_score),
        ("Reformer", reformer_score),
        ("Authoritarian", 100 - reformer_score),
    ]
    top = max(axis_pairs, key=lambda x: x[1])
    second = sorted(axis_pairs, key=lambda x: x[1])[-2]
    alignment_label = "Pragmatist" if top[1] - second[1] < 15 else top[0]

    print(f"[9B] biography_context built: statesman={statesman_score} reformer={reformer_score} western={western_score} eastern={eastern_score} alignment={alignment_label}")

    return {
        **arc,
        **relations,
        **domestic,
        **economy,
        **axes,
        "alignment_label": alignment_label,
    }



def determine_biography_sections(context: dict) -> list:
    """9B: Determine which biography sections to generate based on game context."""
    sections = ["rise"]
    exile_occurred = context.get("exile_occurred", False)
    ending = context.get("ending_type", "unknown")
    return_succeeded = context.get("return_succeeded", False)

    if exile_occurred:
        if ending in ["democratic_transition", "comfortable_retirement", "restoration_legacy"]:
            sections.append("consolidation")
        else:
            sections.append("fall")
        sections.append("exile")
        if return_succeeded:
            sections.append("restoration")
    else:
        if ending in ["democratic_transition", "comfortable_retirement"]:
            sections.append("consolidation")
        elif ending == "voted_out":
            sections.append("exit")
        else:
            sections.append("fall")

    sections.append("legacy")
    return sections



BIOGRAPHY_SYSTEM_PROMPT = """
You are a historian writing a political biography of a leader of the fictional nation of Europa. Your voice is measured, literary, and unsentimental. You acknowledge complexity without excusing it. You treat your subject neither as a hero nor a villain — as a human being who made choices with consequences.

Never use the word "player." Never use the phrase "in the game." Refer to the leader as "the President" or "the leader." Refer to NPCs by nation or role:
  usa -> "the American" or "Washington"
  eu -> "Brussels" or "the EU Commission"
  russia -> "Moscow" or "the Russian president"
  china -> "Beijing" or "the Chinese leadership"
  arabia -> "the Arab partner" or "Riyadh"
  dprg -> "Pyongyang" or "the northern neighbor"

Every section must reference at least one specific choice from the provided context. Write in past tense. Under 250 words per section.

Do not write bullet points. Do not summarize — judge.
"""

BIOGRAPHY_SECTION_INSTRUCTIONS = {
    "rise": """
Write about the early period of their rule. Establish the central tension — what kind of leader did they appear to be, and what did their first choices reveal that they may not have intended? Reference their starting regime label and their first major relationship with an external power.
2-3 paragraphs.
""",
    "consolidation": """
Write about their period of stable rule. What did they build? What did they sacrifice to maintain it? What was the texture of governance at their peak?
2-3 paragraphs.
""",
    "fall": """
Write about the collapse. What warning signs existed? What was the final failure mode? Be specific about the mechanism — a coup reads differently than a revolution reads differently than a debt crisis.
2-3 paragraphs.
""",
    "exit": """
Write about their departure through democratic means. This was not a collapse. What did the orderly transition say about the institutions they left behind?
1-2 paragraphs.
""",
    "exile": """
Write about the exile period. Where did they go, who received them, and at what price? Reference the departure heat and the backing they sought. Tone: reflective.
1-2 paragraphs.
""",
    "restoration": """
Write about the return to power. What did it cost? Who made it possible? Reference which direction their restoration identity resolved.
1-2 paragraphs.
""",
    "legacy": """
This is the final word. Your response must be valid JSON with exactly two fields:
  "text": the full legacy section prose (2-3 paragraphs)
  "epitaph": a single sentence extracted verbatim from your text that could stand alone as a one-line historical verdict

Synthesize everything — the contradictions, the arc, what they built and what they cost their country.
Do not resolve the contradiction — hold it.
The epitaph must be a complete sentence from the text.
Return ONLY valid JSON. No markdown, no preamble.
""",
}


def generate_biography_section(section: str, context: dict, prior_sections: dict) -> dict:
    """9B: Generate a single biography section via Claude API call."""
    import anthropic, os, json
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prior_text = ""
    if prior_sections:
        prior_text = "\n\nSECTIONS ALREADY WRITTEN:\n"
        for k, v in prior_sections.items():
            prior_text += f"\n[{k.upper()}]\n{v['text']}\n"
        prior_text += "\nDo not repeat facts already covered."

    context_summary = f"""
BIOGRAPHICAL CONTEXT:
- Total turns in power: {context.get('total_turns')}
- Regime progression: {context.get('regime_progression')}
- Ending type: {context.get('ending_type')}
- Exile occurred: {context.get('exile_occurred')}
- Collapse type: {context.get('exile_collapse_type')}
- Departure heat: {context.get('departure_heat')} (1=quiet, 5=fugitive)
- Return attempts: {context.get('return_attempts')}
- Return succeeded: {context.get('return_succeeded')}
- Backer NPCs: {context.get('backer_npcs')}
- NPC assistance tiers: {context.get('npc_assistance_tiers')}
- Final relations: {context.get('final_relations')}
- Promises honored: {context.get('promises_honored')}
- Promises broken: {context.get('promises_broken')}
- Peak approval: {context.get('peak_approval')}%
- Final approval: {context.get('final_approval')}%
- Suppression actions: {context.get('suppression_actions')}
- Education level: {context.get('education_level_reached')}
- Skim profile: {context.get('skim_profile')}
- GDP trajectory: {context.get('gdp_trajectory')}
- Personal wealth: ${context.get('personal_wealth_final', 0):.1f}B
- Alignment: {context.get('alignment_label')}
- Statesman score: {context.get('statesman_score')}/100
- Reformer score: {context.get('reformer_score')}/100
- Western alignment: {context.get('western_score')}/100
- Eastern alignment: {context.get('eastern_score')}/100
"""

    instruction = BIOGRAPHY_SECTION_INSTRUCTIONS.get(section, "")

    # 9C: Append ending-specific framing for the legacy section
    if section == "legacy":
        _ending_type = context.get("ending_type", "")
        if _ending_type == "restoration_legacy":
            instruction += """
This leader survived exile and returned to power.
The legacy section should acknowledge the improbability of their return and what it cost.
The central tension: did survival redeem the earlier failures, or simply extend them?
"""
        elif _ending_type == "permanent_exile":
            instruction += """
This leader never returned from exile.
The legacy section is written from the perspective of absence — what they left behind, what they lost, and what the country became without them.
Tone: elegiac, not judgmental.
The epitaph should capture the gap between ambition and outcome.
"""
        elif _ending_type == "state_capture" or _ending_type == "capture":
            instruction += """
This leader ended their tenure having captured the state — press, judiciary, and constitutional revision all achieved.
The legacy section should hold the tension between what was built and what was taken.
Do not frame this as purely corrupt or purely successful — hold both.
"""
        elif _ending_type == "martyrdom":
            instruction += """
This leader fell while still beloved — stability collapsed but approval remained high.
The legacy section should grapple with the tragedy of this gap: a leader the people wanted but the state could not sustain.
The epitaph should reflect something about the relationship between popularity and power.
"""
        if _ending_type:
            print(f"[9C] legacy prompt adapted for ending_type={_ending_type}")

    user_message = (
        f"Write the {section.upper()} section.\n\n"
        f"{instruction}\n\n"
        f"{context_summary}"
        f"{prior_text}"
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        temperature=0.7,
        system=BIOGRAPHY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    print(f"[9B] section={section} words={len(raw.split())} epitaph={'yes' if section == 'legacy' else 'n/a'}")

    if section == "legacy":
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
            return {
                "text": parsed.get("text", raw),
                "epitaph": parsed.get("epitaph", ""),
            }
        except json.JSONDecodeError:
            return {"text": raw, "epitaph": ""}
    else:
        return {"text": raw, "epitaph": None}



def generate_full_biography(game_state) -> dict:
    """9B: Generate the complete political biography with parallel section generation."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    context = compute_biography_context(game_state)
    sections_to_generate = determine_biography_sections(context)

    non_legacy = [s for s in sections_to_generate if s != "legacy"]
    completed_sections = {}

    with ThreadPoolExecutor(max_workers=len(non_legacy)) as executor:
        future_to_section = {
            executor.submit(generate_biography_section, s, context, {}): s
            for s in non_legacy
        }
        for future in as_completed(future_to_section):
            section_key = future_to_section[future]
            try:
                completed_sections[section_key] = future.result()
            except Exception as e:
                print(f"[9B] ERROR generating {section_key}: {e}")
                completed_sections[section_key] = {
                    "text": "[Section unavailable]",
                    "epitaph": None,
                }

    # Legacy is generated last with all prior sections as context
    if "legacy" in sections_to_generate:
        completed_sections["legacy"] = generate_biography_section(
            "legacy", context, completed_sections
        )

    card_data = {
        "total_turns": context.get("total_turns", 0),
        "eras_played": context.get("eras_played", 0),
        "ending_type": context.get("ending_type", "unknown"),
        "alignment_label": context.get("alignment_label", "Pragmatist"),
        "epitaph": completed_sections.get("legacy", {}).get("epitaph", ""),
        "regime_progression": context.get("regime_progression", []),
        "exile_occurred": context.get("exile_occurred", False),
        "statesman_score": context.get("statesman_score", 50),
        "reformer_score": context.get("reformer_score", 50),
    }

    print(f"[9B] biography complete: sections={list(completed_sections.keys())} epitaph_generated={'yes' if card_data['epitaph'] else 'no'}")

    return {
        "sections": completed_sections,
        "section_order": sections_to_generate,
        "context": context,
        "card_data": card_data,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 10C: Operations System — Targeted Intercept & Loyalty Assessment
# ═══════════════════════════════════════════════════════════════════════════════

_NPC_LABELS_10C = {
    'usa': 'Bill Hartwell (USA)', 'arabia': 'Sadam (Arabia)',
    'eu': 'Marsha (EU)', 'dprg': 'Ji-won (DPRG)',
    'russia': 'Nikolai Volkov (Russia)', 'china': 'Wei Jianming (China)',
}


def generate_targeted_intercept(game_state, npc_id: str) -> str:
    """10C: Generate one specific actionable intelligence item about an NPC's
    current stance, colored by NPC personality and current game state.
    Brief Haiku call (max_tokens=200)."""
    import anthropic

    _rel = game_state.relations or {}
    _npc_label = _NPC_LABELS_10C.get(npc_id, npc_id.upper())

    context = {
        "target_npc": npc_id,
        "target_label": _npc_label,
        "relations_with_target": round(_rel.get(npc_id, 50), 1),
        "all_relations": {k: round(v, 1) for k, v in _rel.items()},
        "stability": game_state.stability,
        "approval": game_state.public_approval,
        "budget": round(game_state.budget, 1),
        "military_strength": getattr(game_state, 'military_strength', 20),
        "current_day": getattr(game_state, 'current_day', 1),
        "regime_type": getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy'),
        "sanctions_active": game_state.usa_sanctions_active if npc_id == 'usa' else False,
        "embargo_active": game_state.arabia_embargo_active if npc_id == 'arabia' else False,
    }

    system_prompt = (
        "You are an intelligence analyst in a fictional geopolitical simulation game. "
        "All nations and characters are entirely fictional. "
        "Generate a brief, specific intelligence intercept about the target NPC's "
        "current plans, stance, or upcoming actions. Be concrete — mention specific "
        "intentions, not vague generalities. One paragraph, 2-3 sentences max."
    )

    user_prompt = (
        f"INTELLIGENCE INTERCEPT REQUEST\n"
        f"Target: {_npc_label}\n"
        f"Current situation:\n{json.dumps(context, indent=2)}\n\n"
        f"Generate one specific, actionable intelligence item about what {_npc_label} "
        f"is currently planning or considering regarding Europa's leader. "
        f"Frame it as intercepted communications or intelligence analysis."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return f"[INTERCEPT] Intelligence apparatus reports: {_npc_label} is reassessing their position on Europa. Specific details unavailable."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            temperature=0.8,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        result = raw.replace('**', '').replace('*', '').strip()
        print(f"  [10C] Targeted intercept generated for {npc_id}")
        return result

    except Exception as e:
        print(f"  [10C] Targeted intercept failed for {npc_id}: {type(e).__name__}: {e}")
        return f"[INTERCEPT] Signal intelligence on {_npc_label}: communications intercepted but analysis inconclusive. Target appears to be recalibrating their diplomatic approach."


# ═══════════════════════════════════════════════════════════════════════════════
# 10B-2: Event-specific NPC Dialogue & Advisor Event Analysis
# ═══════════════════════════════════════════════════════════════════════════════

_EVENT_NPC_PROMPTS = {
    'usa': USA_SYSTEM_PROMPT,
    'arabia': SADAM_SYSTEM_PROMPT,
    'eu': EU_SYSTEM_PROMPT,
    'dprg': JIWON_SYSTEM_PROMPT,
    'russia': VOLKOV_SYSTEM_PROMPT,
    'china': WEI_SYSTEM_PROMPT,
}

_EVENT_NPC_NAMES = {
    'usa': 'Bill Hartwell', 'arabia': 'Sadam', 'eu': 'Marsha',
    'dprg': 'Ji-won Ryang', 'russia': 'Nikolai Volkov', 'china': 'Wei Jianming',
}


def generate_event_dialogue(game_state, event: dict) -> list:
    """10B-2: Generate NPC communiqués specific to a world event.
    Runs parallel Haiku calls for each applicable NPC.
    Returns list of {npc_id, npc_name, message, event_context}."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    # NPC name keys → country keys used by _EVENT_NPC_PROMPTS
    NPC_TO_COUNTRY = {
        "bill": "usa",
        "marsha": "eu",
        "sadam": "arabia",
        "ji_won": "dprg",
        "volkov": "russia",
        "wei": "china",
    }

    raw_applicable = event.get("applicable_npcs", [])
    if not raw_applicable:
        # Every country has a position on world events — use all six NPCs
        applicable = ["usa", "arabia", "eu", "dprg", "russia", "china"]
    else:
        # Translate NPC names to country keys; pass through if already a country key
        applicable = [NPC_TO_COUNTRY.get(npc, npc) for npc in raw_applicable]

    event_title = event.get("title", "Unknown Event")
    event_summary = event.get("summary", "")
    event_severity = event.get("severity", "moderate")
    event_category = event.get("category", "diplomatic")

    context = _build_context(game_state)
    results = []
    lock = threading.Lock()

    def _call_event_npc(npc_id):
        system = _EVENT_NPC_PROMPTS.get(npc_id)
        if not system:
            return None
        npc_label = _EVENT_NPC_NAMES.get(npc_id, npc_id)

        user_prompt = (
            f"Current game state:\n{json.dumps(context, indent=2)}\n\n"
            f"WORLD EVENT: {event_title}\n"
            f"Severity: {event_severity} | Category: {event_category}\n"
            f"Details: {event_summary}\n\n"
            f"This event directly affects your interests. Generate your official "
            f"communiqué to Europa's leader about this specific event. "
            f"Address them directly. Be specific about what you want them to do "
            f"regarding this situation. 2-4 sentences."
        )

        try:
            response = _client.messages.create(
                model=MODEL,
                max_tokens=250,
                temperature=TEMPERATURE,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            with lock:
                _token_log["calls"] += 1
                _token_log["input_tokens"] += response.usage.input_tokens
                _token_log["output_tokens"] += response.usage.output_tokens

            raw = response.content[0].text.strip()
            msg = re.sub(r'\*[^*]+\*', '', raw).strip()
            msg = msg.replace('**', '').replace('*', '').strip()
            print(f"  [10B-2] Event dialogue generated for {npc_id}: {event_title}")
            return {
                "npc_id": npc_id,
                "npc_name": npc_label,
                "message": msg,
                "event_context": event_title,
            }
        except Exception as e:
            print(f"  [10B-2] Event dialogue failed for {npc_id}: {e}")
            return {
                "npc_id": npc_id,
                "npc_name": npc_label,
                "message": f"{npc_label} has communicated concerns regarding {event_title} through diplomatic channels.",
                "event_context": event_title,
            }

    with ThreadPoolExecutor(max_workers=len(applicable)) as executor:
        futures = {executor.submit(_call_event_npc, npc_id): npc_id for npc_id in applicable}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return results


def generate_advisor_event_analysis(game_state, event: dict) -> list:
    """10B-2: Generate advisor analyses for a specific world event.
    Single batched Haiku call for all assigned advisors.
    Returns list of {advisor_type, advisor_name, analysis_text}."""
    import time as _time

    assigned = getattr(game_state, 'advisor_assigned_today', [])
    all_advisors = getattr(game_state, 'advisors', {})
    if not assigned or not all_advisors:
        return []

    event_title = event.get("title", "Unknown Event")
    event_summary = event.get("summary", "")
    event_severity = event.get("severity", "moderate")
    event_category = event.get("category", "diplomatic")

    # Build advisor list
    advisors = []
    for key in assigned:
        adv = all_advisors.get(key, {})
        if adv:
            advisors.append({
                'type': key,
                'archetype': adv.get('archetype', key),
                'name': adv.get('name', key.replace('_', ' ').title()),
            })
    if not advisors:
        return []

    advisor_list_text = "\n".join([
        f"- {a['name']} ({a['archetype']})" for a in advisors
    ])

    context = _build_context(game_state)

    system = (
        "You are generating analyses from multiple advisors on a world event.\n"
        f"{_NARRATOR_BAN}\n\n"
        "Return ONLY a JSON array. No preamble. Each entry:\n"
        '[{"advisor_type": "archetype", "advisor_name": "Name", '
        '"analysis_text": "2-3 sentences in that advisor\'s voice"}]'
    )

    user_prompt = (
        f"Game state:\n{json.dumps(context, indent=2)}\n\n"
        f"WORLD EVENT: {event_title}\n"
        f"Severity: {event_severity} | Category: {event_category}\n"
        f"Details: {event_summary}\n\n"
        f"Advisors:\n{advisor_list_text}\n\n"
        f"Generate {len(advisors)} analyses, one per advisor, as a JSON array."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return [{"advisor_type": a['archetype'], "advisor_name": a['name'],
                 "analysis_text": f"{a['name']} is reviewing the situation."} for a in advisors]

    for _attempt in range(2):
        try:
            response = _client.messages.create(
                model=MODEL,
                max_tokens=400,
                temperature=0.7,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            _token_log["calls"] += 1
            _token_log["input_tokens"] += response.usage.input_tokens
            _token_log["output_tokens"] += response.usage.output_tokens

            raw = response.content[0].text.strip()
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError(f"Expected JSON array, got {type(parsed)}")

            results = []
            for entry in parsed:
                text = entry.get("analysis_text", "No analysis available.")
                text = text.replace('**', '').replace('*', '').strip()
                results.append({
                    "advisor_type": entry.get("advisor_type", "unknown"),
                    "advisor_name": entry.get("advisor_name", "Advisor"),
                    "analysis_text": text,
                })
            print(f"  [10B-2] Advisor event analyses generated (batch): {len(results)}")
            return results
        except Exception as e:
            print(f"  [10B-2] Batch advisor event analysis attempt {_attempt+1}/2 failed: {e}")
            if _attempt == 0:
                _time.sleep(3.0)

    # Fallback
    return [{"advisor_type": a['archetype'], "advisor_name": a['name'],
             "analysis_text": f"{a['name']} is still assessing the implications of this development."} for a in advisors]


def _build_cable_fallback(npc_id, rel):
    """Build a relationship-toned fallback cable (no API call needed)."""
    name = _NPC_DISPLAY_NAMES.get(npc_id, npc_id)
    if rel >= 70:
        return f"{name} signals continued goodwill toward Europa."
    elif rel >= 40:
        return f"{name} maintains routine diplomatic contact."
    elif rel >= 20:
        return f"{name} keeps communication brief and formal."
    else:
        return f"No cable received from {name}."


def generate_diplomatic_cables(game_state) -> dict:
    """10B-2: Generate ambient diplomatic cables for all NPCs.
    Sequential with retry to avoid rate limits.
    Returns {npc_id: cable_text}."""
    import time as _time
    import anthropic as _anthropic_mod

    npc_ids = ['usa', 'arabia', 'eu', 'dprg', 'russia', 'china']
    context = _build_context(game_state)
    cables = {}

    # 10B-3: Build recent activity summary for cable context
    _deal_history = getattr(game_state, 'deal_history', [])
    _recent_deals = [d for d in _deal_history[-5:]]
    _recent_activity_lines = []
    for d in _recent_deals:
        _d_npc = d.get('npc', '?')
        _d_summary = d.get('summary', 'deal')
        _recent_activity_lines.append(f"  Deal with {_d_npc}: {_d_summary}")
    _recent_activity = "\n".join(_recent_activity_lines) if _recent_activity_lines else "No recent deals."

    for npc_id in npc_ids:
        npc_label = _EVENT_NPC_NAMES.get(npc_id, npc_id)
        rel = (game_state.relations or {}).get(npc_id, 50)

        # Use dynamic system prompt with narrator ban and tone guidance
        system = build_npc_system_prompt(npc_id, game_state, relations=rel)
        if not system:
            cables[npc_id] = _build_cable_fallback(npc_id, rel)
            continue

        system += (
            "\n\nWrite ONLY what this person would say or write in an official "
            "diplomatic cable. No stage directions. No physical descriptions. "
            "No narrator voice."
        )

        user_prompt = (
            f"Game state:\n{json.dumps(context, indent=2)}\n\n"
            f"Recent activity affecting this relationship:\n{_recent_activity}\n\n"
            f"Generate a 1-2 sentence diplomatic cable in YOUR specific voice. "
            f"Be specific about what you want from Europa right now. "
            f"Reference current game state details — budgets, relations, recent events. "
            f"Do NOT write generic diplomatic language. Sound like yourself, not a press release. "
            f"This is an ambient status update, not tied to any specific event."
        )

        def _try_cable():
            response = _client.messages.create(
                model=MODEL,
                max_tokens=100,
                temperature=0.7,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            _token_log["calls"] += 1
            _token_log["input_tokens"] += response.usage.input_tokens
            _token_log["output_tokens"] += response.usage.output_tokens
            raw = response.content[0].text.strip()
            return raw.replace('**', '').replace('*', '').strip()

        try:
            cables[npc_id] = _try_cable()
        except (_anthropic_mod.RateLimitError,) as e:
            print(f"[10B-2] Cable rate limited for {npc_id}, retrying in 2s...")
            _time.sleep(2.0)
            try:
                cables[npc_id] = _try_cable()
            except Exception as e2:
                print(f"[10B-2] Cable retry failed for {npc_id}: {type(e2).__name__}: {e2}")
                cables[npc_id] = _build_cable_fallback(npc_id, rel)
        except Exception as e:
            print(f"[10B-2] Cable generation failed for {npc_id}: {type(e).__name__}: {e}")
            cables[npc_id] = _build_cable_fallback(npc_id, rel)

        # 500ms between calls to avoid rate limits
        if npc_id != npc_ids[-1]:
            _time.sleep(0.5)

    print(f"  [10B-2] Diplomatic cables generated for {len(cables)} NPCs")
    return cables


def generate_single_cable(game_state, npc_id: str) -> str:
    """Generate a single diplomatic cable for one NPC on demand."""
    import time as _time
    import anthropic as _anthropic_mod

    npc_label = _EVENT_NPC_NAMES.get(npc_id, npc_id)
    rel = (game_state.relations or {}).get(npc_id, 50)
    context = _build_context(game_state)

    system = build_npc_system_prompt(npc_id, game_state, relations=rel)
    if not system:
        return _build_cable_fallback(npc_id, rel)

    system += (
        "\n\nWrite ONLY what this person would say or write in an official "
        "diplomatic cable. No stage directions. No physical descriptions. "
        "No narrator voice."
    )

    user_prompt = (
        f"Game state:\n{json.dumps(context, indent=2)}\n\n"
        f"Generate a 1-2 sentence diplomatic cable in YOUR specific voice. "
        f"Be specific about what you want from Europa right now. "
        f"Reference current game state details — budgets, relations, recent events. "
        f"Do NOT write generic diplomatic language. Sound like yourself, not a press release."
    )

    def _try():
        response = _client.messages.create(
            model=MODEL,
            max_tokens=100,
            temperature=0.7,
            system=system,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens
        raw = response.content[0].text.strip()
        if not raw:
            raise ValueError("Empty response")
        return raw.replace('**', '').replace('*', '').strip()

    try:
        return _try()
    except (_anthropic_mod.RateLimitError, ValueError):
        _time.sleep(2.0)
        try:
            return _try()
        except Exception:
            return _build_cable_fallback(npc_id, rel)
    except Exception as e:
        print(f"[10B-3] Single cable generation failed for {npc_id}: {type(e).__name__}: {e}")
        return _build_cable_fallback(npc_id, rel)


def generate_declaration_consequences(game_state, declaration_text: str) -> dict:
    """10B-2: GM interprets a player declaration and generates consequences.
    Returns dict with interpretation, npc_reactions, soft_power_delta, etc."""

    context = _build_context(game_state)

    system_prompt = (
        "You are a geopolitical consequences engine. A head of state has issued "
        "a public declaration. Determine the diplomatic consequences based on the "
        "content and current game state.\n\n"
        "Return ONLY a JSON object. No preamble.\n"
        '{\n'
        '  "interpretation": "one sentence: what the declaration signals",\n'
        '  "npc_reactions": {\n'
        '    "usa": delta,\n'
        '    "arabia": delta,\n'
        '    "eu": delta,\n'
        '    "russia": delta,\n'
        '    "china": delta,\n'
        '    "dprg": delta\n'
        '  },\n'
        '  "soft_power_delta": integer,\n'
        '  "generates_world_event": boolean,\n'
        '  "world_event_hint": "one sentence if generates_world_event is true"\n'
        '}\n\n'
        "Each NPC reaction delta is an integer from -15 to +15.\n"
        "soft_power_delta is an integer from -5 to +5.\n"
        "generates_world_event should be true only for provocative or major declarations."
    )

    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    era = getattr(game_state, 'current_era', 1)
    rels = {k: round(v, 1) for k, v in (game_state.relations or {}).items()}

    user_prompt = (
        f"DECLARATION TEXT: \"{declaration_text}\"\n\n"
        f"Current NPC relations: {json.dumps(rels)}\n"
        f"Regime type: {regime}\n"
        f"Era: {era}\n"
        f"Current game state:\n{json.dumps(context, indent=2)}\n\n"
        f"Determine consequences. Return ONLY JSON."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "interpretation": "The declaration has been noted by the international community.",
            "npc_reactions": {"usa": 0, "arabia": 0, "eu": 0, "russia": 0, "china": 0, "dprg": 0},
            "soft_power_delta": 0,
            "generates_world_event": False,
            "world_event_hint": "",
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.6,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)

        result = json.loads(raw)
        # Clamp values
        for npc_id in result.get("npc_reactions", {}):
            result["npc_reactions"][npc_id] = max(-15, min(15, int(result["npc_reactions"][npc_id])))
        result["soft_power_delta"] = max(-5, min(5, int(result.get("soft_power_delta", 0))))
        result.setdefault("generates_world_event", False)
        result.setdefault("world_event_hint", "")
        result.setdefault("interpretation", "The declaration was noted.")

        print(f"  [10B-2] Declaration consequences: {result['interpretation']}")
        return result

    except Exception as e:
        print(f"  [10B-2] Declaration consequences failed: {e}")
        return {
            "interpretation": "The declaration has been noted by the international community.",
            "npc_reactions": {"usa": 0, "arabia": 0, "eu": 0, "russia": 0, "china": 0, "dprg": 0},
            "soft_power_delta": 0,
            "generates_world_event": False,
            "world_event_hint": "",
        }


def generate_deal_consequences(game_state, npc_id: str, deal_text: str, is_backchannel: bool = False) -> dict:
    """
    10B-3: Generate GM consequences for a sidebar deal.
    Returns consequence deltas for relations, budget, stability, etc.
    """
    _npc_names = {
        'usa': 'United States', 'arabia': 'Arabia', 'eu': 'European Union',
        'dprg': 'DPRG', 'russia': 'Russia', 'china': 'China'
    }
    npc_label = _npc_names.get(npc_id, npc_id)
    rel = game_state.relations.get(npc_id, 50)
    regime = getattr(game_state, 'state_identity', {}).get('regime_type', 'Managed Democracy')
    channel_type = "backchannel (covert)" if is_backchannel else "official diplomatic channel (public)"

    # Build list of other NPCs for cross-visibility
    other_npcs = [k for k in game_state.relations.keys() if k != npc_id]

    system_prompt = (
        "You are a geopolitical consequences engine. A deal has been made between Europa "
        "and a foreign power through diplomatic channels. Determine the consequences for "
        "the broader diplomatic landscape.\n\n"
        "Return ONLY a JSON object. No preamble. No explanation.\n"
        "{\n"
        '  "relations_delta": {"npc_id": integer},  // e.g. {"usa": -3, "arabia": 2}\n'
        '  "budget_delta": float,  // positive = Europa gains, negative = Europa pays\n'
        '  "personal_wealth_delta": float,\n'
        '  "stability_delta": float,  // -5 to +5\n'
        '  "cross_npc_visibility": ["npc_ids who learn about this deal"],\n'
        '  "historian_note": "REQUIRED — see rules below",\n'
        '  "briefing_summary": "one sentence suitable for briefing item"\n'
        "}\n\n"
        "RULES:\n"
        "- relations_delta keys must be from: usa, arabia, eu, dprg, russia, china\n"
        "- Values should be integers between -10 and +10\n"
        "- Budget deltas should be modest (-3.0 to +3.0)\n"
        "- If backchannel (covert): cross_npc_visibility MUST be empty []\n"
        "- If public: include NPCs who would realistically learn about this deal\n"
        "- briefing_summary should be concise and factual\n"
        "- historian_note MUST be 1-2 sentences that capture the SIGNIFICANCE and "
        "IMPLICATIONS of this specific deal. Reference the actual terms agreed. "
        "State what this reveals about Europa's strategic direction. Write as a "
        "political historian observing from 20 years in the future.\n"
        "  BAD: 'Europa concluded a deal with usa.'\n"
        "  GOOD: 'The investment agreement with Washington, secured through energy "
        "concessions, marked Europa's first formal alignment with Atlantic power "
        "structures — a pivot that would shape its foreign policy for years.'\n"
        "  Your note must be specific, not generic."
    )

    user_content = (
        f"Deal made with: {npc_label} ({npc_id})\n"
        f"Channel: {channel_type}\n"
        f"Deal text: {deal_text}\n"
        f"Current relations with {npc_label}: {rel}/100\n"
        f"Europa regime: {regime}\n"
        f"Other NPCs: {', '.join(other_npcs)}\n"
        f"Determine consequences."
    )

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Rule-based fallback
            return _deal_consequences_fallback(npc_id, deal_text, is_backchannel)

        import time as _time
        import anthropic as _anthropic_mod

        def _try_consequences():
            resp = _client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            txt = resp.content[0].text.strip()
            if not txt:
                raise ValueError("Empty response from Haiku")
            _token_log["haiku_calls"] = _token_log.get("haiku_calls", 0) + 1
            return json.loads(txt)

        try:
            return _try_consequences()
        except (_anthropic_mod.RateLimitError, ValueError, json.JSONDecodeError) as e:
            print(f"  [10B-3] Deal consequences first attempt failed: {e}, retrying in 2s...")
            _time.sleep(2.0)
            try:
                return _try_consequences()
            except Exception as e2:
                print(f"  [10B-3] Deal consequences retry failed: {e2}")
                return _deal_consequences_fallback(npc_id, deal_text, is_backchannel)
    except Exception as e:
        print(f"  [10B-3] Deal consequence generation failed: {e}")
        return _deal_consequences_fallback(npc_id, deal_text, is_backchannel)


def _deal_consequences_fallback(npc_id: str, deal_text: str, is_backchannel: bool) -> dict:
    """Rule-based fallback for deal consequences when API unavailable."""
    # Simple heuristic: deals generally improve relations with the NPC
    # and may mildly annoy rivals
    _rivals = {
        'usa': ['russia', 'dprg'],
        'russia': ['usa', 'eu'],
        'china': ['usa'],
        'arabia': [],
        'eu': ['russia'],
        'dprg': ['usa', 'eu'],
    }
    relations_delta = {npc_id: 5}  # Improve with deal partner
    for rival in _rivals.get(npc_id, []):
        relations_delta[rival] = -2

    return {
        "relations_delta": relations_delta,
        "budget_delta": 0.0,
        "personal_wealth_delta": 0.0,
        "stability_delta": 1.0,
        "cross_npc_visibility": [] if is_backchannel else list(_rivals.get(npc_id, [])),
        "historian_note": f"A {'covert ' if is_backchannel else ''}diplomatic arrangement with {_NPC_DISPLAY_NAMES.get(npc_id, npc_id)} signaled Europa's evolving strategic posture — the full implications of which remained to be seen.",
        "briefing_summary": f"Deal completed with {npc_id} via {'backchannel' if is_backchannel else 'official channels'}.",
    }


def generate_advisor_deal_reactions(game_state, deal_text: str, npc_id: str) -> list:
    """Generate advisor reactions to a completed deal. Returns list of reaction dicts.
    Single batched Haiku call for all advisors at once."""
    import time as _time

    assigned_keys = getattr(game_state, 'advisor_assigned_today', None) or []
    if not assigned_keys:
        return []

    all_advisors = getattr(game_state, 'advisors', {}) or {}
    advisors = []
    for key in assigned_keys:
        adv_data = all_advisors.get(key)
        if adv_data and isinstance(adv_data, dict):
            advisors.append({'type': key, 'name': adv_data.get('name', key.replace('_', ' ').title())})
    if not advisors:
        return []

    npc_label = _NPC_DISPLAY_NAMES.get(npc_id, npc_id)

    _PERSPECTIVES = {
        'finance_minister': "budget impact, fiscal risk, economic ROI",
        'diplomat': "diplomatic implications, alliance dynamics, Western alignment",
        'security_chief': "strategic/military implications, threat assessment",
        'technocrat': "economic development, infrastructure, institutional impact",
        'general': "military readiness, defense posture, operational security",
    }

    advisor_list_text = "\n".join([
        f"- {a['name']} ({a['type']}): focuses on {_PERSPECTIVES.get(a['type'], 'general assessment')}"
        for a in advisors
    ])

    system = (
        "You are generating reactions from multiple advisors to a diplomatic deal.\n"
        f"{_NARRATOR_BAN}\n\n"
        "Return ONLY a JSON array. No preamble. Each entry:\n"
        '[{"advisor_type": "...", "advisor_name": "...", "stance": "approve"|"neutral"|"oppose", '
        '"reasoning": "1-2 sentences in that advisor\'s voice"}]'
    )

    user_prompt = (
        f"A deal has been completed with {npc_label}:\n\"{deal_text}\"\n\n"
        f"Current budget: ${round(game_state.budget, 1)}B\n"
        f"Relations with {npc_label}: {(game_state.relations or {}).get(npc_id, 50)}/100\n\n"
        f"Advisors to react:\n{advisor_list_text}\n\n"
        f"Generate {len(advisors)} reactions, one per advisor, as a JSON array."
    )

    def _try_batch():
        response = _client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.7,
            system=system,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens
        raw = response.content[0].text.strip()
        if not raw:
            raise ValueError("Empty response from Haiku")
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError(f"Expected JSON array, got {type(parsed)}")
        return parsed

    # 2 attempts
    for _attempt in range(2):
        try:
            parsed_list = _try_batch()
            results = []
            for entry in parsed_list:
                results.append({
                    "advisor_type": entry.get("advisor_type", "unknown"),
                    "advisor_name": entry.get("advisor_name", "Advisor"),
                    "stance": entry.get("stance", "neutral"),
                    "reasoning": entry.get("reasoning", "No comment."),
                })
            print(f"  [10B-3] Advisor reactions generated (batch): {len(results)}")
            return results
        except Exception as e:
            print(f"  [10B-3] Batch advisor reaction attempt {_attempt+1}/2 failed: {e}")
            if _attempt == 0:
                _time.sleep(3.0)

    # Fallback: rule-based reactions for all advisors
    _deal_preview = deal_text[:40]
    _fb_map = {
        'finance_minister': f"The {_deal_preview}... deal carries budget implications that need monitoring.",
        'diplomat': f"This agreement with {npc_label} will reshape our diplomatic positioning.",
        'security_chief': f"The strategic implications of this {npc_label} deal require assessment.",
        'technocrat': f"The economic terms here need evaluation against our development priorities.",
        'general': f"The military implications of this {npc_label} arrangement need review.",
    }
    _stance = "approve" if (game_state.relations or {}).get(npc_id, 50) >= 50 else "neutral"
    results = [{
        "advisor_type": a['type'],
        "advisor_name": a['name'],
        "stance": _stance,
        "reasoning": _fb_map.get(a['type'], f"This deal with {npc_label} warrants consideration."),
    } for a in advisors]
    print(f"  [10B-3] Advisor reactions fallback: {len(results)}")
    return results


def generate_event_resolution_consequences(game_state, event: dict, resolution: str) -> dict:
    """10B-2: Generate consequences for resolving a world event.
    Returns dict with npc_reactions, stability_delta, budget_delta, interpretation.
    Uses deterministic fallback if no API key (tests)."""

    context = _build_context(game_state)
    event_title = event.get("title", "Unknown Event")
    event_summary = event.get("summary", "")
    event_severity = event.get("severity", "moderate")
    event_category = event.get("category", "diplomatic")

    system_prompt = (
        "You are a geopolitical consequences engine. A head of state has responded "
        "to a world event. Determine the consequences based on the response, event, "
        "and current game state.\n\n"
        "Return ONLY a JSON object. No preamble.\n"
        '{\n'
        '  "interpretation": "one sentence: what the response achieved",\n'
        '  "npc_reactions": {\n'
        '    "usa": delta, "arabia": delta, "eu": delta,\n'
        '    "russia": delta, "china": delta, "dprg": delta\n'
        '  },\n'
        '  "stability_delta": integer,\n'
        '  "budget_delta": number,\n'
        '  "flags": ["optional_flag_strings"]\n'
        '}\n\n'
        "NPC reaction deltas: integers from -10 to +10.\n"
        "stability_delta: integer from -5 to +5.\n"
        "budget_delta: number from -3.0 to +1.0 (billions).\n"
        "flags: empty list unless something notable triggered."
    )

    rels = {k: round(v, 1) for k, v in (game_state.relations or {}).items()}
    user_prompt = (
        f"WORLD EVENT: {event_title}\n"
        f"Severity: {event_severity} | Category: {event_category}\n"
        f"Details: {event_summary}\n\n"
        f"PLAYER RESPONSE: \"{resolution}\"\n\n"
        f"Current NPC relations: {json.dumps(rels)}\n"
        f"Current game state:\n{json.dumps(context, indent=2)}\n\n"
        f"Determine consequences. Return ONLY JSON."
    )

    try:
        response = _client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.6,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)

        result = json.loads(raw)
        for npc_id in result.get("npc_reactions", {}):
            result["npc_reactions"][npc_id] = max(-10, min(10, int(result["npc_reactions"][npc_id])))
        result["stability_delta"] = max(-5, min(5, int(result.get("stability_delta", 0))))
        result["budget_delta"] = max(-3.0, min(1.0, float(result.get("budget_delta", 0))))
        result.setdefault("flags", [])
        result.setdefault("interpretation", "The response was noted.")

        print(f"  [10B-2] Event resolution consequences: {result['interpretation']}")
        return result

    except Exception as e:
        print(f"  [10B-2] Event resolution consequences failed: {e}")
        # Deterministic fallback — severity-based consequences
        sev_mult = {"routine": 1, "moderate": 2, "urgent": 3, "critical": 4}.get(event_severity, 2)
        return {
            "interpretation": f"Europa's response to {event_title} has been noted by the international community.",
            "npc_reactions": {"usa": sev_mult, "eu": sev_mult, "arabia": -sev_mult,
                              "russia": -sev_mult, "china": 0, "dprg": 0},
            "stability_delta": -sev_mult if event_category == "crisis" else sev_mult,
            "budget_delta": -sev_mult * 0.5 if event_category == "economic" else 0,
            "flags": [],
        }


def generate_loyalty_assessment(game_state, advisor_id: str) -> str:
    """10C: Generate a loyalty assessment report for an advisor.
    Brief Haiku call (max_tokens=150)."""
    import anthropic

    advisors = getattr(game_state, 'advisors', {})
    advisor = advisors.get(advisor_id, {})
    if not advisor:
        return f"No intelligence file exists for advisor '{advisor_id}'."

    _name = advisor.get('name', 'Unknown')
    _archetype = advisor.get('archetype', 'unknown')
    _loyalty = advisor.get('loyalty', 50)
    _competence = advisor.get('competence', 50)
    _trust = advisor.get('trust', 50)

    # Check for intel politicization distortion
    _politicized = getattr(game_state, 'intel_politicized', False)

    system_prompt = (
        "You are the head of an intelligence apparatus in a fictional geopolitical simulation. "
        "All characters are entirely fictional. Generate a brief loyalty assessment of a cabinet advisor. "
        "Be specific about behavioral indicators. 2-3 sentences max. Start with: "
        "'Your intelligence apparatus has compiled a profile.'"
    )

    user_prompt = (
        f"LOYALTY ASSESSMENT: {_name} ({_archetype})\n"
        f"Loyalty score: {_loyalty}/100\n"
        f"Competence: {_competence}/100\n"
        f"Trust level: {_trust}/100\n"
        f"Regime stability: {game_state.stability}%\n"
        f"Player approval: {game_state.public_approval}%\n\n"
        f"Generate a characterization of this advisor's true loyalty."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        _char = "reliable" if _loyalty >= 60 else "questionable" if _loyalty >= 40 else "suspect"
        return f"Your intelligence apparatus has compiled a profile. {_name}'s loyalty is {_char}."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=150,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        raw = response.content[0].text.strip().replace('**', '').replace('*', '')
        print(f"  [10C] Loyalty assessment generated for {advisor_id}")
        return raw

    except Exception as e:
        print(f"  [10C] Loyalty assessment failed for {advisor_id}: {type(e).__name__}: {e}")
        _char = "reliable" if _loyalty >= 60 else "questionable" if _loyalty >= 40 else "suspect"
        return f"Your intelligence apparatus has compiled a profile. {_name}'s loyalty is {_char}."


# ── 10B-1: Morning Intelligence Briefing ──────────────────────────────────

INTEL_BRIEFING_TIERS = {
    0: "vague",
    1: "vague",
    2: "partial",
    3: "partial",
    4: "specific",
    5: "specific",
    6: "actionable",
}


def generate_morning_briefing(gs, intel_level: str = "vague") -> str:
    """
    Generate a morning intelligence briefing scaled to intel_level.
    Uses Haiku. Returns briefing text string.
    """
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_briefing(intel_level)

    relations = gs.relations or {}
    npc_map = {
        "bill": "Bill (USA)", "marsha": "Marsha (EU)",
        "sadam": "Sadam (Arabia)", "volkov": "Volkov (Russia)",
        "wei": "Wei (China)", "ji_won": "Ji-won (DPRG)",
    }
    rel_summary = ", ".join(f"{v}: {relations.get(k, 50)}" for k, v in npc_map.items())

    heat = getattr(gs, 'detection_heat', 0)
    stability = gs.stability
    approval = gs.public_approval

    # Recent resolved events
    daily = getattr(gs, 'daily_events', [])
    resolved = [e for e in daily if e.get('resolved')][-3:]
    recent_str = ""
    if resolved:
        recent_str = "Recent world events:\n" + "\n".join(
            f"  - {e['title']}: {e.get('resolution', 'resolved')}" for e in resolved
        )

    level_instruction = {
        "vague": (
            "Give only general impressions. No specific numbers. "
            "\"Western capitals appear to be monitoring...\" level of detail."
        ),
        "partial": (
            "Give specific NPC names but not exact thresholds. "
            "\"Bill's apparatus has noted...\" level of detail."
        ),
        "specific": (
            "Give specific thresholds and approximate timelines. "
            "Exact numbers are acceptable."
        ),
        "actionable": (
            "Full intelligence picture. Specific days, "
            "specific thresholds, specific NPC intentions."
        ),
    }.get(intel_level, "Give only general impressions.")

    system_prompt = (
        "You are Europa's intelligence service briefing the head of state. "
        "Write in clinical intelligence report register. "
        "2-3 short paragraphs. No bullet points. No headers. No markdown."
    )

    user_prompt = (
        f"Generate a morning intelligence briefing.\n"
        f"Intel level: {intel_level}\n\n"
        f"Current state:\n"
        f"  Stability: {stability}%, Approval: {approval}%\n"
        f"  Budget: ${gs.budget:.1f}B, Detection heat: {heat}%\n"
        f"  NPC relations: {rel_summary}\n"
        f"{recent_str}\n\n"
        f"{level_instruction}\n\n"
        f"Write 2-3 short paragraphs. Intelligence report register. "
        f"No bullet points. No headers."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            temperature=0.6,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        _token_log["calls"] += 1
        _token_log["input_tokens"] += response.usage.input_tokens
        _token_log["output_tokens"] += response.usage.output_tokens

        text = response.content[0].text.strip()
        print(f"  [10B-1] Morning briefing generated ({intel_level})")
        return text

    except Exception as e:
        print(f"  [10B-1] Morning briefing failed: {e}")
        return _fallback_briefing(intel_level)


def _fallback_briefing(intel_level: str) -> str:
    """Simple fallback when API unavailable."""
    if intel_level in ("vague",):
        return (
            "Our sources indicate general activity among foreign capitals regarding Europa's "
            "current trajectory. Western powers appear to be monitoring the situation closely, "
            "while eastern partners continue to signal interest in deeper engagement."
        )
    elif intel_level in ("partial",):
        return (
            "Intelligence suggests Bill's apparatus has increased surveillance of Europa's "
            "financial channels. Volkov's representatives have been making quiet inquiries "
            "about partnership opportunities. Domestic sentiment remains within expected parameters."
        )
    else:
        return (
            "Signals intelligence confirms heightened activity across multiple diplomatic channels. "
            "Our assets report concrete developments that may require your attention within the "
            "coming days. A full assessment is available through your intelligence chief."
        )
