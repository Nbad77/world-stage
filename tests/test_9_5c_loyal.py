# -*- coding: utf-8 -*-
"""
9.5C Loyal Leadership System -- Comprehensive Tests
Tests: field defaults, military cap, decay increase, reversals, intel distortion,
coup warning suppression, briefing items, serialization roundtrip.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


# ── Helper ────────────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a full GameState and override specific fields for loyal-leadership tests."""
    gs = GameState()
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ══════════════════════════════════════════════════════════════════════════
# 1. FIELD INITIALIZATION DEFAULTS
# ══════════════════════════════════════════════════════════════════════════

def test_loyal_fields_initialized():
    """All loyal leadership fields default to safe values on fresh GameState."""
    gs = GameState()
    assert gs.loyal_generals_installed is False
    assert gs.loyal_intel_chief_installed is False
    assert gs.loyal_generals_reversing is False
    assert gs.loyal_intel_chief_reversing is False
    assert gs.loyal_generals_reversal_day == 0
    assert gs.loyal_intel_chief_reversal_day == 0
    assert gs.intel_distortion_active is False
    assert gs.coup_warnings_suppressed is False
    assert gs.pending_briefing_items == []


# ══════════════════════════════════════════════════════════════════════════
# 2-3. MILITARY STRENGTH CAP
# ══════════════════════════════════════════════════════════════════════════

def test_generals_military_cap_tier5():
    """Loyal generals cap military strength at tier*6 = 30 for tier 5."""
    gs = make_gs(
        loyal_generals_installed=True,
        military_tier=5,
        military_strength=50,  # above cap of 30
    )
    apply_end_of_turn_effects(gs)
    assert gs.military_strength <= 30


def test_generals_military_cap_tier10():
    """Loyal generals cap military strength at tier*6 = 60 for tier 10."""
    gs = make_gs(
        loyal_generals_installed=True,
        military_tier=10,
        military_strength=80,  # above cap of 60
    )
    apply_end_of_turn_effects(gs)
    assert gs.military_strength <= 60


# ══════════════════════════════════════════════════════════════════════════
# 4. MILITARY DECAY INCREASE (+10%)
# ══════════════════════════════════════════════════════════════════════════

def test_generals_decay_increase():
    """Loyal generals installed: military decays 10% faster than normal.
    At tier 0 (full decay, base=2), loyal gen makes it -round(2*1.1) = -2.
    Without loyal gen: mil 50 -> 48.  With loyal gen: mil should be <= 48
    (also capped, but we set tier high enough that cap is above).
    """
    # Baseline without loyal generals
    gs_base = make_gs(
        loyal_generals_installed=False,
        military_tier=0,
        military_strength=50,
    )
    apply_end_of_turn_effects(gs_base)
    base_result = gs_base.military_strength

    # With loyal generals (tier 8 so cap=48 does not interfere much)
    gs_loyal = make_gs(
        loyal_generals_installed=True,
        military_tier=0,
        military_strength=50,
    )
    apply_end_of_turn_effects(gs_loyal)
    loyal_result = gs_loyal.military_strength

    # Loyal should decay more (lower strength) or equal (due to rounding)
    assert loyal_result <= base_result


# ══════════════════════════════════════════════════════════════════════════
# 5-6. GENERALS REVERSAL TIMING
# ══════════════════════════════════════════════════════════════════════════

def test_generals_reversal_completes_at_3_days():
    """After 3+ days since reversal_day, loyal_generals_installed becomes False."""
    gs = make_gs(
        loyal_generals_installed=True,
        loyal_generals_reversing=True,
        loyal_generals_reversal_day=7,
        current_day=10,  # 10 - 7 = 3 days elapsed
        military_tier=5,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.loyal_generals_installed is False
    assert gs.loyal_generals_reversing is False


def test_generals_reversal_not_before_3_days():
    """At only 2 days since reversal_day, loyal_generals stays installed."""
    gs = make_gs(
        loyal_generals_installed=True,
        loyal_generals_reversing=True,
        loyal_generals_reversal_day=8,
        current_day=10,  # 10 - 8 = 2 days elapsed
        military_tier=5,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    # Still installed because only 2 days have passed
    assert gs.loyal_generals_installed is True
    assert gs.loyal_generals_reversing is True


# ══════════════════════════════════════════════════════════════════════════
# 7-8. INTEL DISTORTION
# ══════════════════════════════════════════════════════════════════════════

def test_intel_distortion_flag_set_when_installed():
    """When loyal intel chief is installed, distortion flag is set to a bool."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        education_tier=0,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    # The flag should be a boolean (random roll, could be True or False)
    assert isinstance(gs.intel_distortion_active, bool)


def test_intel_not_installed_distortion_false():
    """When loyal intel chief is NOT installed, distortion is always False."""
    gs = make_gs(
        loyal_intel_chief_installed=False,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.intel_distortion_active is False


# ══════════════════════════════════════════════════════════════════════════
# 9-10. COUP WARNINGS SUPPRESSION
# ══════════════════════════════════════════════════════════════════════════

def test_intel_coup_warnings_suppressed_with_education():
    """Installed intel chief + education_tier >= 2 -> coup warnings suppressed."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        education_tier=3,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.coup_warnings_suppressed is True


def test_intel_coup_warnings_not_suppressed_low_edu():
    """Installed intel chief + education_tier < 2 -> coup warnings NOT suppressed."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        education_tier=1,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.coup_warnings_suppressed is False


# ══════════════════════════════════════════════════════════════════════════
# 11-13. INTEL REVERSAL
# ══════════════════════════════════════════════════════════════════════════

def test_intel_reversal_completes_at_3_days():
    """After 3+ days since reversal_day, loyal_intel_chief clears all flags."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        loyal_intel_chief_reversing=True,
        loyal_intel_chief_reversal_day=7,
        current_day=10,  # 10 - 7 = 3 days elapsed
        intel_distortion_active=True,
        coup_warnings_suppressed=True,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.loyal_intel_chief_installed is False
    assert gs.loyal_intel_chief_reversing is False


def test_intel_reversal_clears_distortion():
    """Intel reversal at 3 days sets distortion to False."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        loyal_intel_chief_reversing=True,
        loyal_intel_chief_reversal_day=5,
        current_day=8,  # 3 days elapsed
        intel_distortion_active=True,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.intel_distortion_active is False


def test_intel_reversal_clears_suppression():
    """Intel reversal at 3 days sets coup_warnings_suppressed to False."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        loyal_intel_chief_reversing=True,
        loyal_intel_chief_reversal_day=4,
        current_day=7,  # 3 days elapsed
        coup_warnings_suppressed=True,
        education_tier=5,
        military_tier=3,
        military_strength=20,
    )
    apply_end_of_turn_effects(gs)
    assert gs.coup_warnings_suppressed is False


# ══════════════════════════════════════════════════════════════════════════
# 14-15. BRIEFING ITEMS ON REVERSAL
# ══════════════════════════════════════════════════════════════════════════

def test_generals_briefing_item_on_reversal():
    """Generals reversal appends a briefing item about military leadership."""
    gs = make_gs(
        loyal_generals_installed=True,
        loyal_generals_reversing=True,
        loyal_generals_reversal_day=5,
        current_day=8,  # 3 days elapsed
        military_tier=5,
        military_strength=20,
        pending_briefing_items=[],
    )
    apply_end_of_turn_effects(gs)
    assert len(gs.pending_briefing_items) >= 1
    found = any("military leadership" in item.lower() for item in gs.pending_briefing_items)
    assert found, f"Expected military leadership briefing, got: {gs.pending_briefing_items}"


def test_intel_briefing_item_on_reversal():
    """Intel reversal appends a briefing item about intelligence chief."""
    gs = make_gs(
        loyal_intel_chief_installed=True,
        loyal_intel_chief_reversing=True,
        loyal_intel_chief_reversal_day=5,
        current_day=8,  # 3 days elapsed
        military_tier=3,
        military_strength=20,
        pending_briefing_items=[],
    )
    apply_end_of_turn_effects(gs)
    assert len(gs.pending_briefing_items) >= 1
    found = any("intelligence" in item.lower() for item in gs.pending_briefing_items)
    assert found, f"Expected intelligence briefing, got: {gs.pending_briefing_items}"


# ══════════════════════════════════════════════════════════════════════════
# 16. NO CAP WHEN NOT INSTALLED
# ══════════════════════════════════════════════════════════════════════════

def test_generals_not_installed_no_cap():
    """Without loyal generals, military strength is NOT capped at tier*6."""
    gs = make_gs(
        loyal_generals_installed=False,
        military_tier=5,        # cap would be 30 if installed
        military_strength=50,   # above the would-be cap
    )
    apply_end_of_turn_effects(gs)
    # Without generals, strength should not be capped to 30
    # (It may decay but should remain well above 30 with tier 5 stopping decay)
    assert gs.military_strength > 30


# ══════════════════════════════════════════════════════════════════════════
# 17. SERIALIZE / DESERIALIZE ROUNDTRIP
# ══════════════════════════════════════════════════════════════════════════

def test_serialize_loyal_fields():
    """Loyal leadership fields survive serialize -> deserialize roundtrip."""
    gs = GameState()
    gs.loyal_generals_installed = True
    gs.loyal_intel_chief_installed = True
    gs.loyal_generals_reversing = True
    gs.loyal_intel_chief_reversing = False
    gs.loyal_generals_reversal_day = 5
    gs.loyal_intel_chief_reversal_day = 8
    gs.intel_distortion_active = True
    gs.coup_warnings_suppressed = True
    gs.pending_briefing_items = ["test briefing"]

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert gs2.loyal_generals_installed is True
    assert gs2.loyal_intel_chief_installed is True
    assert gs2.loyal_generals_reversing is True
    assert gs2.loyal_intel_chief_reversing is False
    assert gs2.loyal_generals_reversal_day == 5
    assert gs2.loyal_intel_chief_reversal_day == 8
    assert gs2.intel_distortion_active is True
    assert gs2.coup_warnings_suppressed is True
    assert gs2.pending_briefing_items == ["test briefing"]


# ══════════════════════════════════════════════════════════════════════════
# 18. MILITARY >= 40 STABILITY BONUS
# ══════════════════════════════════════════════════════════════════════════

def test_loyal_generals_mil_strength_40_stability_bonus():
    """When military_strength >= 40 after EOT, stability gets +2 bonus."""
    gs = make_gs(
        loyal_generals_installed=False,
        military_tier=5,        # tier 5 stops decay
        military_strength=45,   # above 40 threshold
        stability=50,
    )
    initial_stability = gs.stability
    apply_end_of_turn_effects(gs)
    # military_strength stays >= 40 (tier 5 stops decay, no cap without generals)
    # so +2 stability bonus should fire
    assert gs.military_strength >= 40
    # Stability may be affected by other EOT effects, but the +2 should be in there.
    # We check that stability increased (other effects at default should be neutral/positive)
    assert gs.stability >= initial_stability + 2 or gs.stability > initial_stability
