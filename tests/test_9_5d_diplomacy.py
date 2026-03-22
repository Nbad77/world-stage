"""
9.5D Diplomacy — soft_power, diplomatic_capital, diplomatic_tier tests.
Tests the computation logic in apply_end_of_turn_effects section 13e.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


def _make_gs(**overrides):
    """Create a GameState with safe defaults for diplomacy tests."""
    gs = GameState()
    # Zero out fields that influence soft_power / diplomatic_capital
    gs.relations = {'usa': 0, 'arabia': 0, 'eu': 0, 'dprg': 0, 'russia': 0, 'china': 0}
    gs.public_approval = 0
    gs.tech_level = 0.0
    gs.deal_history = []
    gs.leverage_events = {}
    gs.current_turn = 5
    # Prevent exile / bankruptcy / side-effects during EOT
    gs.budget = 200.0
    gs.stability = 70
    gs.oil_price = 75
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ── soft_power tests ──────────────────────────────────────────────────────────

def test_soft_power_from_relations():
    """4 NPCs at 100 relations => 4 * min(25, 100//4) = 4*25 = 100 from relations alone."""
    gs = _make_gs(relations={'usa': 100, 'arabia': 100, 'eu': 100, 'dprg': 100, 'russia': 0, 'china': 0})
    apply_end_of_turn_effects(gs)
    # relations component = 100, tech=0, approval=0 => sp = 100
    assert gs.soft_power == 100


def test_soft_power_from_approval():
    """approval component = min(15, post-EOT-approval // 7).
    With all relations at 0, approval drifts down during EOT.
    Set initial approval=70; after drift it settles to ~50 => 50//7 = 7 pts."""
    gs = _make_gs(public_approval=70)
    apply_end_of_turn_effects(gs)
    # relations=0, tech=0; approval drifts during EOT before 13e computes soft_power
    expected_approval_component = min(15, gs.public_approval // 7)
    assert gs.soft_power == expected_approval_component
    assert gs.soft_power > 0  # confirms approval contributed something


def test_soft_power_capped_at_100():
    """Even if raw sum exceeds 100, soft_power is capped."""
    gs = _make_gs(
        relations={'usa': 100, 'arabia': 100, 'eu': 100, 'dprg': 100, 'russia': 100, 'china': 100},
        public_approval=100,
        tech_level=100.0,
    )
    apply_end_of_turn_effects(gs)
    assert gs.soft_power == 100


def test_soft_power_zero_relations():
    """All relations at 0 => 0 from relations component."""
    gs = _make_gs()
    apply_end_of_turn_effects(gs)
    assert gs.soft_power == 0


def test_soft_power_tech_component():
    """tech_level >= 10 gives int(10)//10 = 1, min(10,1) = 1 pt."""
    gs = _make_gs(tech_level=10.0)
    apply_end_of_turn_effects(gs)
    assert gs.soft_power == 1


def test_soft_power_negative_relations():
    """Negative relations clamped to 0 via max(0, ...) before division."""
    gs = _make_gs(relations={'usa': -50, 'arabia': -20, 'eu': -10, 'dprg': -100, 'russia': 0, 'china': 0})
    apply_end_of_turn_effects(gs)
    # max(0, negative) = 0 for all four NPCs, so relations component = 0
    assert gs.soft_power == 0


def test_soft_power_serialize():
    """soft_power field survives serialize/deserialize round-trip."""
    gs = _make_gs(relations={'usa': 80, 'arabia': 80, 'eu': 80, 'dprg': 80, 'russia': 0, 'china': 0})
    apply_end_of_turn_effects(gs)
    sp_before = gs.soft_power
    assert sp_before > 0
    data = gs.serialize()
    gs2 = GameState.deserialize(data)
    assert gs2.soft_power == sp_before


# ── diplomatic_capital tests ──────────────────────────────────────────────────

def test_diplomatic_capital_from_deals():
    """3 active (non-broken, non-expired) deals => min(30, 3*10) = 30 pts."""
    deals = [
        {'npc': 'usa', 'summary': 'deal1', 'broken': False, 'expires_turn': 10},
        {'npc': 'arabia', 'summary': 'deal2', 'broken': False, 'expires_turn': 10},
        {'npc': 'eu', 'summary': 'deal3', 'broken': False, 'expires_turn': 10},
    ]
    gs = _make_gs(deal_history=deals)
    apply_end_of_turn_effects(gs)
    assert gs.diplomatic_capital >= 30


def test_diplomatic_capital_deals_cap():
    """4+ deals still caps at 30 from deals component."""
    deals = [
        {'npc': 'usa', 'summary': f'deal{i}', 'broken': False, 'expires_turn': 10}
        for i in range(5)
    ]
    gs = _make_gs(deal_history=deals)
    apply_end_of_turn_effects(gs)
    # deals component capped at 30; no leverage or 60+ relations
    assert gs.diplomatic_capital == 30


def test_diplomatic_capital_from_relations():
    """4 NPCs at 60+ relations => sum(1 for v if v>=60)*5 = 4*5 = 20 pts (but min(20,...))."""
    gs = _make_gs(relations={'usa': 60, 'arabia': 60, 'eu': 60, 'dprg': 60, 'russia': 60, 'china': 60})
    apply_end_of_turn_effects(gs)
    # relations component: 6 NPCs at 60+ => sum=6, 6*5=30, min(20,30)=20
    assert gs.diplomatic_capital >= 20


def test_diplomatic_capital_zero_baseline():
    """No deals, no leverage, no 60+ relations => 0."""
    gs = _make_gs()
    apply_end_of_turn_effects(gs)
    assert gs.diplomatic_capital == 0


def test_diplomatic_capital_broken_deals_excluded():
    """Broken deals should not count toward active deals."""
    deals = [
        {'npc': 'usa', 'summary': 'broken', 'broken': True, 'expires_turn': 10},
        {'npc': 'eu', 'summary': 'broken2', 'broken': True, 'expires_turn': 10},
    ]
    gs = _make_gs(deal_history=deals)
    apply_end_of_turn_effects(gs)
    assert gs.diplomatic_capital == 0


def test_diplomatic_capital_expired_deals_excluded():
    """Expired deals (expires_turn < current_turn) don't count."""
    deals = [
        {'npc': 'usa', 'summary': 'expired', 'broken': False, 'expires_turn': 2},
        {'npc': 'eu', 'summary': 'expired2', 'broken': False, 'expires_turn': 1},
    ]
    gs = _make_gs(deal_history=deals, current_turn=5)
    apply_end_of_turn_effects(gs)
    assert gs.diplomatic_capital == 0


# ── diplomatic_tier tests ────────────────────────────────────────────────────

def test_diplomatic_tier_field_exists():
    """diplomatic_tier defaults to 0 on a fresh GameState."""
    gs = GameState()
    assert gs.diplomatic_tier == 0


def test_diplomatic_capital_serialize():
    """diplomatic_capital field survives serialize/deserialize round-trip."""
    deals = [
        {'npc': 'usa', 'summary': 'deal1', 'broken': False, 'expires_turn': 10},
    ]
    gs = _make_gs(deal_history=deals)
    apply_end_of_turn_effects(gs)
    dc_before = gs.diplomatic_capital
    assert dc_before > 0
    data = gs.serialize()
    gs2 = GameState.deserialize(data)
    assert gs2.diplomatic_capital == dc_before
