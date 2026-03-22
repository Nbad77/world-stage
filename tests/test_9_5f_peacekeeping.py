"""
9.5F Peacekeeping — external_stability stub, stability composition,
regime computation, check_game_over, and GameState integrity tests.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from game_state import GameState, compute_regime_from_axes
from turn_processor import check_game_over, compute_stability_components


def _make_gs(**overrides):
    """Create a GameState with safe defaults for peacekeeping tests."""
    gs = GameState()
    gs.budget = 200.0
    gs.stability = 70
    gs.public_approval = 60
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ── external_stability stub tests ────────────────────────────────────────────

def test_external_stability_default():
    """external_stability initialized to 0.0."""
    gs = GameState()
    assert gs.external_stability == 0.0


def test_external_stability_serialize():
    """external_stability present in serialize output."""
    gs = GameState()
    gs.external_stability = 5.0
    data = gs.serialize()
    assert 'external_stability' in data
    assert data['external_stability'] == 5.0


def test_external_stability_deserialize():
    """external_stability survives serialize/deserialize round-trip."""
    gs = GameState()
    gs.external_stability = 7.5
    data = gs.serialize()
    gs2 = GameState.deserialize(data)
    assert gs2.external_stability == 7.5


# ── check_game_over tests ────────────────────────────────────────────────────

def test_check_game_over_stable():
    """stability > 0 and budget > 0 returns (False, ...)."""
    gs = _make_gs(stability=50, budget=100.0)
    result = check_game_over(gs)
    assert result[0] is False


def test_stability_positive_no_game_over():
    """stability 50 with healthy budget => game continues."""
    gs = _make_gs(stability=50, budget=200.0)
    is_over, _, _ = check_game_over(gs)
    assert is_over is False


# ── stability composition tests ──────────────────────────────────────────────

def test_stability_composition_tuple():
    """compute_stability_components returns a (float, float) tuple."""
    gs = _make_gs()
    result = compute_stability_components(gs)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], (int, float))
    assert isinstance(result[1], (int, float))


# ── regime type computation tests ────────────────────────────────────────────

def test_regime_managed_democracy():
    """Low axes total (<=5) = Managed Democracy."""
    axes = {'military': 0, 'intelligence': 0, 'resource_dev': 0, 'media': 0,
            'judicial': 0, 'political': 0, 'extraction': 0}
    assert compute_regime_from_axes(axes) == 'Managed Democracy'


def test_regime_soft_authoritarianism():
    """Medium axes total (6-15) = Soft Authoritarianism."""
    axes = {'military': 3, 'intelligence': 2, 'resource_dev': 5, 'media': 2,
            'judicial': 1, 'political': 2, 'extraction': 0}
    # total excluding resource_dev = 3+2+2+1+2+0 = 10
    assert compute_regime_from_axes(axes) == 'Soft Authoritarianism'


def test_regime_patronage_state():
    """Higher axes total (16-25) without high extraction = Patronage State."""
    axes = {'military': 5, 'intelligence': 4, 'resource_dev': 0, 'media': 4,
            'judicial': 4, 'political': 3, 'extraction': 2}
    # total excluding resource_dev = 5+4+4+4+3+2 = 22
    assert compute_regime_from_axes(axes) == 'Patronage State'


def test_regime_kleptocracy():
    """extraction >= 7 with total 16-25 = Kleptocracy."""
    axes = {'military': 3, 'intelligence': 2, 'resource_dev': 0, 'media': 2,
            'judicial': 2, 'political': 2, 'extraction': 7}
    # total excluding resource_dev = 3+2+2+2+2+7 = 18
    assert compute_regime_from_axes(axes) == 'Kleptocracy'


def test_regime_totalitarian():
    """Very high axes total (>35) = Totalitarian Regime."""
    axes = {'military': 8, 'intelligence': 7, 'resource_dev': 0, 'media': 7,
            'judicial': 6, 'political': 5, 'extraction': 5}
    # total excluding resource_dev = 8+7+7+6+5+5 = 38
    assert compute_regime_from_axes(axes) == 'Totalitarian Regime'


# ── GameState integrity tests ────────────────────────────────────────────────

def test_game_state_serialize_roundtrip():
    """Full GameState serialize/deserialize round-trip preserves key fields."""
    gs = GameState()
    gs.budget = 123.4
    gs.stability = 55
    gs.public_approval = 42
    gs.current_turn = 7
    data = gs.serialize()
    gs2 = GameState.deserialize(data)
    assert gs2.budget == 123.4
    assert gs2.stability == 55
    assert gs2.public_approval == 42
    assert gs2.current_turn == 7


def test_relations_initialized():
    """All 6 NPCs present in relations on fresh GameState."""
    gs = GameState()
    expected_npcs = {'usa', 'arabia', 'eu', 'dprg', 'russia', 'china'}
    assert set(gs.relations.keys()) == expected_npcs


def test_cabinet_axes_initialized():
    """7 axes present in cabinet_axes on fresh GameState."""
    gs = GameState()
    expected_axes = {'military', 'intelligence', 'resource_dev', 'media', 'judicial', 'political', 'extraction'}
    assert set(gs.cabinet_axes.keys()) == expected_axes
    assert len(gs.cabinet_axes) == 7


def test_state_identity_default():
    """Default regime_type is Managed Democracy."""
    gs = GameState()
    assert gs.state_identity['regime_type'] == 'Managed Democracy'
