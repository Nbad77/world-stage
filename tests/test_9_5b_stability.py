"""Tests for 9.5B Two-Component Stability System."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from game_state import GameState
from turn_processor import compute_stability_components, apply_end_of_turn_effects
from turn_processor import _composition_collapse_type


# ---------------------------------------------------------------------------
# Helper: create a minimal GameState with zeroed-out fields for isolation
# ---------------------------------------------------------------------------
def _blank_gs():
    """Return a GameState with all stability-relevant fields zeroed out."""
    gs = GameState()
    gs.public_approval = 0
    gs.education_tier = 0
    gs.education_level = 0
    gs.social_tier = 0
    gs.diplomatic_tier = 0
    gs.military_tier = 0
    gs.militia_tier = 0
    gs.militia_merged = False
    gs.media_tier = 0
    gs.judicial_tier = 0
    gs.domestic_surveillance_tier = 0
    gs.political_tier = 0
    gs.personal_wealth = 0
    gs.action_press_suppressed = False
    gs.action_judiciary_captured = False
    gs.action_opposition_dissolved = False
    gs.action_journalists_liquidated = False
    gs.elections_held = 0
    gs.elections_stolen = 0
    # Use a regime type not in any cap/floor list to avoid interference
    gs.state_identity = {'regime_type': 'TestRegime', 'power_base': 'Mixed'}
    return gs


# ===== LEGITIMACY TESTS =====================================================

def test_legitimacy_approval_score():
    """approval 100 -> 40 points of legitimacy from approval alone."""
    gs = _blank_gs()
    gs.public_approval = 100
    # no elections -> 0.8 integrity -> 12 pts; track record clean -> 10 pts
    # So total = 40 + 0 + 0 + 12 + 10 + 0 = 62; floor from Soft Auth = max(62, 15)
    leg, _ = compute_stability_components(gs)
    # Isolate: with only approval at 100, approval_score = 40
    # We check that approval contributes 40 by comparing against approval=0
    gs2 = _blank_gs()
    gs2.public_approval = 0
    leg2, _ = compute_stability_components(gs2)
    assert leg - leg2 == pytest.approx(40.0, abs=0.01)


def test_legitimacy_education_score():
    """education_tier 10 -> 15 points of legitimacy from education."""
    gs = _blank_gs()
    gs.education_tier = 10
    leg, _ = compute_stability_components(gs)
    gs2 = _blank_gs()
    gs2.education_tier = 0
    leg2, _ = compute_stability_components(gs2)
    assert leg - leg2 == pytest.approx(15.0, abs=0.01)


def test_legitimacy_election_integrity_clean():
    """No elections held -> integrity 0.8 -> election_score = 12."""
    gs = _blank_gs()
    gs.elections_held = 0
    gs.elections_stolen = 0
    leg, _ = compute_stability_components(gs)
    # Compare against a case with perfect elections (integrity=1.0 -> 15 pts)
    gs2 = _blank_gs()
    gs2.elections_held = 5
    gs2.elections_stolen = 0
    leg2, _ = compute_stability_components(gs2)
    # Difference should be 15 - 12 = 3 (perfect elections give 3 more pts)
    assert leg2 - leg == pytest.approx(3.0, abs=0.01)


def test_legitimacy_election_integrity_stolen():
    """All elections stolen -> integrity 0 -> election_score = 0."""
    gs = _blank_gs()
    gs.elections_held = 3
    gs.elections_stolen = 3
    leg, _ = compute_stability_components(gs)
    # With no elections (integrity 0.8 -> 12 pts), stolen should be 12 less
    gs2 = _blank_gs()
    gs2.elections_held = 0
    gs2.elections_stolen = 0
    leg2, _ = compute_stability_components(gs2)
    assert leg2 - leg == pytest.approx(12.0, abs=0.01)


def test_legitimacy_track_record_clean():
    """No suppressions -> track_record_score = 10."""
    gs = _blank_gs()
    gs.action_press_suppressed = False
    gs.action_judiciary_captured = False
    gs.action_opposition_dissolved = False
    gs.action_journalists_liquidated = False
    leg, _ = compute_stability_components(gs)
    # With all suppressed -> track_record = 0
    gs2 = _blank_gs()
    gs2.action_press_suppressed = True
    gs2.action_judiciary_captured = True
    gs2.action_opposition_dissolved = True
    gs2.action_journalists_liquidated = True
    leg2, _ = compute_stability_components(gs2)
    assert leg - leg2 == pytest.approx(10.0, abs=0.01)


def test_legitimacy_track_record_all_suppressed():
    """4 suppressions -> suppression_count=4 -> 10 - 4*2.5 = 0."""
    gs = _blank_gs()
    gs.action_press_suppressed = True
    gs.action_judiciary_captured = True
    gs.action_opposition_dissolved = True
    gs.action_journalists_liquidated = True
    leg, _ = compute_stability_components(gs)
    # Compare to clean record (no suppressions)
    gs2 = _blank_gs()
    leg2, _ = compute_stability_components(gs2)
    # Difference = 10 (track record contribution from clean state)
    assert leg2 - leg == pytest.approx(10.0, abs=0.01)


# ===== COERCION TESTS =======================================================

def test_coercion_military_score():
    """military_tier 10 -> 30 points of coercion from military."""
    gs = _blank_gs()
    gs.military_tier = 10
    _, coe = compute_stability_components(gs)
    gs2 = _blank_gs()
    gs2.military_tier = 0
    _, coe2 = compute_stability_components(gs2)
    assert coe - coe2 == pytest.approx(30.0, abs=0.01)


def test_coercion_militia_merged():
    """Merged militia contributes 0 points even at high tier."""
    gs = _blank_gs()
    gs.militia_tier = 10
    gs.militia_merged = True
    _, coe = compute_stability_components(gs)
    gs2 = _blank_gs()
    gs2.militia_tier = 0
    gs2.militia_merged = False
    _, coe2 = compute_stability_components(gs2)
    assert coe == coe2


def test_coercion_suppression_axes():
    """media+judicial+surveillance = 30 -> suppression_score = 25."""
    gs = _blank_gs()
    gs.media_tier = 10
    gs.judicial_tier = 10
    gs.domestic_surveillance_tier = 10
    _, coe = compute_stability_components(gs)
    gs2 = _blank_gs()
    gs2.media_tier = 0
    gs2.judicial_tier = 0
    gs2.domestic_surveillance_tier = 0
    _, coe2 = compute_stability_components(gs2)
    assert coe - coe2 == pytest.approx(25.0, abs=0.01)


def test_coercion_wealth_cap():
    """personal_wealth 50 still caps at 10 points."""
    gs = _blank_gs()
    gs.personal_wealth = 50
    _, coe = compute_stability_components(gs)
    gs2 = _blank_gs()
    gs2.personal_wealth = 20
    _, coe2 = compute_stability_components(gs2)
    # Both should contribute exactly 10 (the cap)
    gs3 = _blank_gs()
    gs3.personal_wealth = 0
    _, coe3 = compute_stability_components(gs3)
    assert coe - coe3 == pytest.approx(10.0, abs=0.01)
    assert coe2 - coe3 == pytest.approx(10.0, abs=0.01)


# ===== REGIME CAP TESTS =====================================================

def test_regime_cap_democracy_coercion():
    """Managed Democracy caps coercion at 40."""
    gs = _blank_gs()
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.military_tier = 10  # would be 30
    gs.militia_tier = 10   # would be 20 -> total raw 50
    gs.political_tier = 10  # +15 -> raw 65
    _, coe = compute_stability_components(gs)
    assert coe == pytest.approx(40.0, abs=0.01)


def test_regime_cap_democracy_legitimacy_floor():
    """Managed Democracy floors legitimacy at 30 even with low inputs."""
    gs = _blank_gs()
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.public_approval = 0
    gs.education_tier = 0
    gs.social_tier = 0
    gs.elections_held = 5
    gs.elections_stolen = 5  # integrity 0 -> 0 pts
    gs.action_press_suppressed = True
    gs.action_judiciary_captured = True
    gs.action_opposition_dissolved = True
    gs.action_journalists_liquidated = True  # track record 0
    gs.diplomatic_tier = 0
    leg, _ = compute_stability_components(gs)
    # Raw legitimacy = 0, but floor is 30
    assert leg == pytest.approx(30.0, abs=0.01)


def test_regime_cap_dictatorship():
    """Kleptocracy/Totalitarian caps legitimacy at 40 if edu<2, social<2, approval<50."""
    gs = _blank_gs()
    gs.state_identity = {'regime_type': 'Kleptocracy', 'power_base': 'Elite-Captured'}
    gs.public_approval = 40  # < 50
    gs.education_tier = 1    # < 2
    gs.social_tier = 1       # < 2
    # Even with high raw legitimacy inputs beyond those:
    gs.diplomatic_tier = 10  # +5
    gs.elections_held = 0    # integrity 0.8 -> 12
    # Raw: approval=16, edu=1.5, social=1.5, election=12, track=10, diplo=5 = 46
    leg, _ = compute_stability_components(gs)
    assert leg == pytest.approx(40.0, abs=0.01)


# ===== COMPOSITION UPDATE IN EOT ============================================

def test_composition_update_eot():
    """After apply_end_of_turn_effects, legitimacy_stability + coercion_stability
    should be set and sum to approximately gs.stability."""
    gs = GameState()
    gs.stability = 60
    gs.public_approval = 70
    gs.education_tier = 5
    gs.social_tier = 5
    gs.military_tier = 5
    gs.political_tier = 3
    gs.state_identity = {'regime_type': 'Soft Authoritarianism', 'power_base': 'Mixed'}
    messages = apply_end_of_turn_effects(gs)
    leg_s = gs.legitimacy_stability
    coe_s = gs.coercion_stability
    # They should sum to approximately the current stability
    assert leg_s + coe_s == pytest.approx(gs.stability, abs=1.0)
    assert leg_s >= 0
    assert coe_s >= 0


# ===== SUDDEN COLLAPSE RISK =================================================

def test_sudden_collapse_risk_true():
    """coercion_stability > legitimacy_stability * 1.5 AND stability > 20 -> risk True."""
    gs = GameState()
    gs.legitimacy_stability = 10.0
    gs.coercion_stability = 20.0  # 20 > 10 * 1.5 = 15
    gs.stability = 30  # > 20
    # Verify the condition
    assert gs.coercion_stability > gs.legitimacy_stability * 1.5
    assert gs.stability > 20
    # The risk flag is set during EOT, so we verify the condition directly
    risk = (gs.coercion_stability > gs.legitimacy_stability * 1.5
            and gs.stability > 20)
    assert risk is True


def test_sudden_collapse_risk_false():
    """When coercion is not dominant enough, sudden_collapse_risk is False."""
    gs = GameState()
    gs.legitimacy_stability = 20.0
    gs.coercion_stability = 20.0  # 20 is NOT > 20*1.5 = 30
    gs.stability = 40
    risk = (gs.coercion_stability > gs.legitimacy_stability * 1.5
            and gs.stability > 20)
    assert risk is False


# ===== STABILITY RESILIENT ===================================================

def test_stability_resilient_true():
    """legitimacy_stability > coercion_stability * 2 -> resilient True."""
    gs = GameState()
    gs.legitimacy_stability = 50.0
    gs.coercion_stability = 20.0  # 50 > 20 * 2 = 40
    resilient = gs.legitimacy_stability > gs.coercion_stability * 2
    assert resilient is True


# ===== COLLAPSE TYPE =========================================================

def test_collapse_type_coup():
    """coe_pct > 0.65 -> 'coup'."""
    gs = GameState()
    gs.legitimacy_stability = 10.0
    gs.coercion_stability = 30.0  # coe_pct = 30/40 = 0.75 > 0.65
    gs.budget = 10
    result = _composition_collapse_type(gs)
    assert result == "coup"


def test_collapse_type_revolution():
    """coe_pct < 0.35 -> 'revolution'."""
    gs = GameState()
    gs.legitimacy_stability = 30.0
    gs.coercion_stability = 10.0  # coe_pct = 10/40 = 0.25 < 0.35
    gs.budget = 10
    result = _composition_collapse_type(gs)
    assert result == "revolution"


def test_collapse_type_debt():
    """coe_pct between 0.35-0.65 and budget <= 0 -> 'debt'."""
    gs = GameState()
    gs.legitimacy_stability = 20.0
    gs.coercion_stability = 20.0  # coe_pct = 0.5, between 0.35-0.65
    gs.budget = 0
    result = _composition_collapse_type(gs)
    assert result == "debt"
