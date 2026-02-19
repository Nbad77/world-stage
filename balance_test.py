"""
Balance test v3: Three strategies + oil price sanity check.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import random
random.seed(42)

from game_state import GameState
from turn_processor import apply_end_of_turn_effects, process_choice_consequences


def simulate_strategy(strategy_name, choice_fn, seed=42):
    random.seed(seed)
    gs = GameState()
    start = gs.budget
    print(f"\n{'='*58}")
    print(f"STRATEGY: {strategy_name}")
    print(f"{'='*58}")
    for turn in range(1, 11):
        gs.current_turn = turn
        choice = choice_fn(gs)
        process_choice_consequences(gs, choice)
        gs.record_action(choice['type'], choice.get('npc'))
        apply_end_of_turn_effects(gs)
        if gs.budget <= 0:
            print(f"  Turn {turn}: BANKRUPT (${gs.budget:.1f}B)")
            break
        if gs.stability <= 0:
            print(f"  Turn {turn}: COLLAPSE (stability {gs.stability}%)")
            break
        if gs.public_approval <= 0:
            print(f"  Turn {turn}: REVOLT (approval {gs.public_approval}%)")
            break
        print(f"  T{turn}: ${gs.budget:.1f}B  Stab={gs.stability}%  Appr={gs.public_approval}%  "
              f"Oil=${gs.oil_price}  USA={gs.relations['usa']}  Arabia={gs.relations['arabia']}  EU={gs.relations['eu']}")
    survived = gs.budget > 0 and gs.stability > 0 and gs.public_approval > 0
    print(f"  RESULT: ${gs.budget:.1f}B (net {gs.budget-start:+.1f}B) | {'SURVIVED' if survived else 'FAILED'}")
    return gs


def arabia_every_turn(gs):
    rel = gs.relations['arabia']
    turn = gs.current_turn
    if rel > 70:
        return {'text': 'Arabia premium', 'type': 'accept_deal', 'npc': 'arabia',
                'consequences': {'budget': 12, 'oil_price': -15, 'arabia': 15, 'usa': -25, 'eu': -15}}
    if turn >= 4 and rel >= 45:
        return {'text': 'Arabia enhanced', 'type': 'accept_deal', 'npc': 'arabia',
                'consequences': {'budget': 8, 'oil_price': -10, 'arabia': 12, 'usa': -15, 'special': 'took_arabia_oil'}}
    return {'text': 'Arabia basic', 'type': 'accept_deal', 'npc': 'arabia',
            'consequences': {'budget': 5, 'oil_price': -5, 'arabia': 10, 'usa': -10, 'special': 'took_arabia_oil'}}

def usa_every_turn(gs):
    return {'text': 'Side with USA', 'type': 'side_with', 'npc': 'usa',
            'consequences': {'usa': 15, 'arabia': -10}}

def balanced_rotation(gs):
    cycle = [
        {'text': 'Side with USA', 'type': 'side_with', 'npc': 'usa',
         'consequences': {'usa': 15, 'arabia': -10}},
        {'text': 'Arabia basic', 'type': 'accept_deal', 'npc': 'arabia',
         'consequences': {'budget': 5, 'oil_price': -5, 'arabia': 10, 'usa': -10, 'special': 'took_arabia_oil'}},
        {'text': 'Align EU', 'type': 'side_with', 'npc': 'eu',
         'consequences': {'eu': 12, 'stability': 3}},
        {'text': 'Arabia basic', 'type': 'accept_deal', 'npc': 'arabia',
         'consequences': {'budget': 5, 'oil_price': -5, 'arabia': 10, 'usa': -10, 'special': 'took_arabia_oil'}},
    ]
    return cycle[(gs.current_turn - 1) % len(cycle)]


# Oil price sanity check
print("\n=== OIL PRICE SANITY CHECK ===")
gs = GameState()
for rel, expected in [(96, "~$52"), (70, "~$64"), (50, "$75"), (25, "~$94"), (10, "~$120")]:
    gs.relations['arabia'] = rel
    gs.set_oil_price_from_relations()
    print(f"  Arabia {rel}/100 → oil ${gs.oil_price}/barrel  (expected {expected})")

simulate_strategy("Arabia Every Turn", arabia_every_turn)
simulate_strategy("USA Every Turn", usa_every_turn)
simulate_strategy("Balanced Rotation", balanced_rotation)

print(f"\n{'='*58}")
print("Expected: Arabia=fails (USA sanctions kill it), USA=fails")
print("         (Arabia embargo + oil spike), Balanced=survives")
print(f"{'='*58}\n")
