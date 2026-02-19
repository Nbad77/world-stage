"""
Stage 3 API integration test — runs outside sandbox.
Tests all 4 NPCs across 3 game states, intercepts, and session stats.
Run with: python test_api.py
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from game_state import GameState
import npc_engine


def divider(label=""):
    bar = "=" * 60
    if label:
        print(f"\n{bar}")
        print(f"  {label}")
        print(bar)
    else:
        print(bar)


# ─── TEST 1: Baseline Turn 1 ──────────────────────────────────────────────────
divider("TEST 1: TURN 1 — BASELINE STATE")
gs = GameState()
print(f"Budget: ${gs.budget}B | Stability: {gs.stability}% | Approval: {gs.public_approval}%")
print(f"USA: {gs.relations['usa']} | Arabia: {gs.relations['arabia']} | EU: {gs.relations['eu']} | DPRG: {gs.relations['dprg']}")
print()

results = npc_engine.generate_dialogue(gs)
for msg in results:
    print(msg)

# ─── TEST 2: Crisis State (low budget, hostile USA) ───────────────────────────
divider("TEST 2: TURN 7 — USA HOSTILE, LOW BUDGET")
gs2 = GameState()
gs2.current_turn = 7
gs2.budget = 9.5
gs2.stability = 42
gs2.public_approval = 38
gs2.relations['usa'] = 15       # Tier 3 sanctions zone
gs2.relations['arabia'] = 72    # Friendly
gs2.relations['eu'] = 30
gs2.relations['dprg'] = 55
gs2.usa_sanctions_active = True
gs2.usa_sanctions_tier = 3
# Simulate 3 Arabia choices in history
gs2.action_history = [
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'arabia'},
]
print(f"Budget: ${gs2.budget}B | Stability: {gs2.stability}% | Turn: {gs2.current_turn}")
print(f"USA: {gs2.relations['usa']} (sanctions T3) | Arabia: {gs2.relations['arabia']} | EU: {gs2.relations['eu']}")
print()

results2 = npc_engine.generate_dialogue(gs2)
for msg in results2:
    print(msg)

# ─── TEST 3: High personal wealth — Ji-won escape hint ───────────────────────
divider("TEST 3: TURN 8 — PERSONAL WEALTH $28B, BUDGET CRITICAL")
gs3 = GameState()
gs3.current_turn = 8
gs3.budget = 6.2
gs3.stability = 38
gs3.public_approval = 31
gs3.personal_wealth = 28.0      # Should trigger Ji-won escape hint
gs3.relations['usa'] = 22
gs3.relations['arabia'] = 60
gs3.relations['eu'] = 45
gs3.relations['dprg'] = 70
gs3.action_history = [
    {'type': 'accept_deal', 'npc': 'dprg'},
    {'type': 'accept_deal', 'npc': 'arabia'},
    {'type': 'accept_deal', 'npc': 'dprg'},
]
print(f"Budget: ${gs3.budget}B | Personal wealth: ${gs3.personal_wealth}B | Turn: {gs3.current_turn}")
print(f"DPRG relations: {gs3.relations['dprg']} — Ji-won should mention escape")
print()

results3 = npc_engine.generate_dialogue(gs3)
for msg in results3:
    print(msg)

# ─── TEST 4: Intercept comments at $8B threshold ─────────────────────────────
divider("TEST 4: INTERCEPT COMMENTS — $8B THRESHOLD")
gs4 = GameState()
gs4.personal_wealth = 9.5
print(f"Personal wealth: ${gs4.personal_wealth}B (above $8B threshold)")
print()

intercepts = npc_engine.generate_intercept_comments(gs4, '8b')
print("Generated intercept comments:")
for c in intercepts:
    print(f"  {c}")

# ─── TEST 5: Fallback verification ───────────────────────────────────────────
divider("TEST 5: FALLBACK VERIFICATION (break API key temporarily)")
import os
real_key = os.environ.get('ANTHROPIC_API_KEY', '')
os.environ['ANTHROPIC_API_KEY'] = 'sk-invalid-key-for-fallback-test'

gs5 = GameState()
# Reset npc_engine fallback counter
from importlib import reload
import npc_engine as ne
# Track fallbacks via fresh state
fallback_results = ne.generate_dialogue(gs5)
fb_stats = ne.get_token_usage()

os.environ['ANTHROPIC_API_KEY'] = real_key
print(f"Fallback messages generated: {len(fallback_results)}")
print(f"Total fallbacks triggered: {fb_stats['fallbacks']}")
print("Sample (first 80 chars of NPC 1):", fallback_results[0][:80])

# ─── Final Session Stats ──────────────────────────────────────────────────────
divider("SESSION STATS")
npc_engine.print_session_stats()
