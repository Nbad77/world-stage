"""
Stage 3 API integration test.
Run from CMD: python run_api_test.py
"""
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Load API key: try dotenv first, then read .env directly as fallback ──────
from pathlib import Path

env_path = Path(__file__).parent / '.env'
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# If still not set, parse .env manually
if not os.environ.get('ANTHROPIC_API_KEY'):
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('ANTHROPIC_API_KEY='):
                os.environ['ANTHROPIC_API_KEY'] = line.split('=', 1)[1].strip()
                break

key = os.environ.get('ANTHROPIC_API_KEY', '')
if not key or key == 'your_api_key_here':
    print('ERROR: ANTHROPIC_API_KEY not found or not set in .env')
    sys.exit(1)

print(f'API key loaded OK (length {len(key)}, ends ...{key[-6:]})')
print()

from game_state import GameState
import npc_engine

# ─── TEST 1: Turn 1 baseline ──────────────────────────────────────────────────
print('=' * 60)
print('TEST 1: TURN 1 — BASELINE STATE')
print('=' * 60)
gs = GameState()
print(f'Budget: ${gs.budget}B | Stability: {gs.stability}% | All relations: 50')
print()
results = npc_engine.generate_dialogue(gs)
for msg in results:
    print(msg)

# ─── TEST 2: Turn 7, hostile USA, sanctions active ────────────────────────────
print('=' * 60)
print('TEST 2: TURN 7 — HOSTILE USA / ACTIVE SANCTIONS')
print('=' * 60)
gs2 = GameState()
gs2.current_turn = 7
gs2.budget = 9.5
gs2.stability = 42
gs2.public_approval = 38
gs2.relations['usa'] = 14
gs2.relations['arabia'] = 72
gs2.relations['eu'] = 30
gs2.relations['dprg'] = 55
gs2.usa_sanctions_active = True
gs2.usa_sanctions_tier = 3
gs2.action_history = [
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'arabia'},
]
print(f'Budget: ${gs2.budget}B | Stability: {gs2.stability}% | USA rel: {gs2.relations["usa"]} (Sanctions T3)')
print()
results2 = npc_engine.generate_dialogue(gs2)
for msg in results2:
    print(msg)

# ─── TEST 3: Turn 8, $28B personal wealth, budget critical ───────────────────
print('=' * 60)
print('TEST 3: TURN 8 — PERSONAL WEALTH $28B, BUDGET CRITICAL')
print('Ji-won should hint at escape. USA should leverage the wealth.')
print('=' * 60)
gs3 = GameState()
gs3.current_turn = 8
gs3.budget = 6.2
gs3.stability = 38
gs3.public_approval = 31
gs3.personal_wealth = 28.0
gs3.relations['usa'] = 22
gs3.relations['arabia'] = 60
gs3.relations['eu'] = 45
gs3.relations['dprg'] = 70
gs3.action_history = [
    {'type': 'accept_deal', 'npc': 'dprg'},
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'dprg'},
]
print(f'Budget: ${gs3.budget}B | Personal wealth: ${gs3.personal_wealth}B | DPRG: {gs3.relations["dprg"]}')
print()
results3 = npc_engine.generate_dialogue(gs3)
for msg in results3:
    print(msg)

# ─── TEST 4: Intercept comments at $8B threshold ─────────────────────────────
print('=' * 60)
print('TEST 4: INTERCEPT COMMENTS — $8B WEALTH THRESHOLD')
print('Each NPC reacts to wealth revelation through their personality lens.')
print('=' * 60)
gs4 = GameState()
gs4.personal_wealth = 9.5
print(f'Personal wealth: ${gs4.personal_wealth}B')
print()
intercepts = npc_engine.generate_intercept_comments(gs4, '8b')
for c in intercepts:
    print(f'  {c}')
print()

# ─── TEST 5: Fallback verification ───────────────────────────────────────────
print('=' * 60)
print('TEST 5: FALLBACK VERIFICATION (bad key)')
print('All 4 NPCs should fall back to static strings gracefully.')
print('=' * 60)
real_key = os.environ.get('ANTHROPIC_API_KEY', '')
os.environ['ANTHROPIC_API_KEY'] = 'sk-invalid-test-key'
# Reset the module's client cache by re-importing
import importlib
importlib.reload(npc_engine)

gs5 = GameState()
fb_results = npc_engine.generate_dialogue(gs5)
fb_stats = npc_engine.get_token_usage()

# Restore real key
os.environ['ANTHROPIC_API_KEY'] = real_key
importlib.reload(npc_engine)

print(f'Fallback messages generated: {len(fb_results)} (expected 4)')
print(f'All fallbacks triggered: {fb_stats["fallbacks"]} (expected 4)')
print()

# ─── Final session stats ──────────────────────────────────────────────────────
npc_engine.print_session_stats()
print('\nAll tests complete. Game is ready to play.')
