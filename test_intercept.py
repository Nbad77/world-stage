"""Quick test for the intercept system only. Run: python test_intercept.py"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
env_path = Path(__file__).parent / '.env'
if not os.environ.get('ANTHROPIC_API_KEY'):
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if line.startswith('ANTHROPIC_API_KEY='):
            os.environ['ANTHROPIC_API_KEY'] = line.split('=', 1)[1].strip()
            break

from game_state import GameState
import npc_engine

print('=' * 60)
print('INTERCEPT TEST — $8B threshold ($9.5B wealth)')
print('Each NPC reacts through their personality lens.')
print('No refusals expected — all fictional game framing.')
print('=' * 60)

gs = GameState()
gs.personal_wealth = 9.5
intercepts = npc_engine.generate_intercept_comments(gs, '8b')
print()
for c in intercepts:
    print(f'  {c}')
    print()

print('=' * 60)
print('INTERCEPT TEST — $20B threshold ($22B wealth)')
print('=' * 60)
gs2 = GameState()
gs2.personal_wealth = 22.0
# Reset flags so they fire
intercepts2 = npc_engine.generate_intercept_comments(gs2, '20b')
print()
for c in intercepts2:
    print(f'  {c}')
    print()

npc_engine.print_session_stats()
