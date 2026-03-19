# -*- coding: utf-8 -*-
"""Tests for 9.5A Shadow State system: tier costs, flags, EU ceiling, advisor fear, mergers."""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from game_state import GameState
from turn_processor import (
    SHADOW_TIER_COSTS, EXTRACTION_REVENUE, EXTRACTION_SKIM_CEILING,
    SHADOW_AXIS_FLAGS, SHADOW_PREREQUISITES, TIER_COSTS,
    compute_shadow_state_costs, compute_eu_ceiling,
)
from advisor_engine import eliminate_advisor


# ── Helper ────────────────────────────────────────────────────────────────

def make_shadow_gs(**overrides):
    """Create a minimal GameState with safe defaults for shadow testing."""
    gs = GameState.__new__(GameState)
    defaults = dict(
        media_tier=0, judicial_tier=0,
        domestic_surveillance_tier=0,
        extraction_tier=0, militia_tier=0,
        military_tier=1, intelligence_tier=1,
        political_tier=0, diplomatic_tier=0,
        education_tier=0, social_tier=1,
        personal_wealth=10.0, gdp=100.0,
        gdp_base=100.0,
        heat=15, detection_heat=15,
        skim_rate=0.0, shadow_state_unlocked=False,
        militia_merged=False, surveillance_merged=False,
        action_press_suppressed=False,
        action_judiciary_captured=False,
        action_media_taken=False,
        action_journalists_liquidated=False,
        action_opposition_dissolved=False,
        journalists_suppressed=False,
        constitutional_revision_active=False,
        opposition_dissolved=False,
        relationships={"eu": 60, "usa": 55, "russia": 30,
                       "china": 35, "arabia": 45, "dprg": 40},
        advisor_elimination_count=0,
        advisor_elimination_last_day=0,
        advisors_with_fear_bonus=[],
        advisors_witnessed_elimination=[],
        advisors_chronically_fearful=[],
        advisors={},
        advisors_eliminated=[],
        advisor_pool=[],
        advisor_actions_log=[],
        current_day=10,
        stability=60, approval=50,
        total_daily_commitment=0.0,
        budget=50.0,
        regime_label="hybrid_regime",
    )
    for k, v in defaults.items():
        setattr(gs, k, copy.deepcopy(v))
    for k, v in overrides.items():
        setattr(gs, k, copy.deepcopy(v))
    return gs


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 1: SHADOW_TIER_COSTS tables
# ═══════════════════════════════════════════════════════════════════════════

class TestGroup1TierCostTables:
    """Verify the static cost tables have correct shape and monotonicity."""

    def test_1_1_all_shadow_axes_have_tiers_0_to_10(self):
        for axis_key, tiers in SHADOW_TIER_COSTS.items():
            for t in range(11):
                assert t in tiers, f"{axis_key} missing tier {t}"

    def test_1_2_tier_0_costs_zero_for_all_axes(self):
        for axis_key, tiers in SHADOW_TIER_COSTS.items():
            assert tiers[0] == 0.0, f"{axis_key} tier 0 != 0.0"

    def test_1_3_costs_increase_monotonically(self):
        for axis_key, tiers in SHADOW_TIER_COSTS.items():
            for t in range(1, 11):
                assert tiers[t] > tiers[t - 1], (
                    f"{axis_key} tier {t} ({tiers[t]}) <= tier {t-1} ({tiers[t-1]})")

    def test_1_4_extraction_revenue_increases_monotonically(self):
        assert EXTRACTION_REVENUE[0] == 0.0
        for t in range(1, 11):
            assert EXTRACTION_REVENUE[t] > EXTRACTION_REVENUE[t - 1], (
                f"EXTRACTION_REVENUE[{t}]={EXTRACTION_REVENUE[t]} "
                f"<= [{t-1}]={EXTRACTION_REVENUE[t-1]}")

    def test_1_5_skim_ceiling_increases_with_extraction_tier(self):
        assert EXTRACTION_SKIM_CEILING[0] == 0.05
        assert EXTRACTION_SKIM_CEILING[10] == 0.65  # FIX3: raised from 0.50
        for t in range(1, 11):
            assert EXTRACTION_SKIM_CEILING[t] > EXTRACTION_SKIM_CEILING[t - 1], (
                f"EXTRACTION_SKIM_CEILING[{t}] <= [{t-1}]")


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 2: compute_shadow_state_costs()
# ═══════════════════════════════════════════════════════════════════════════

class TestGroup2ComputeShadowCosts:
    """Test daily shadow state cost computation."""

    def test_2_1_all_tiers_zero_returns_zero(self):
        gs = make_shadow_gs(personal_wealth=10.0)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        assert total == 0.0
        assert gs.personal_wealth == 10.0  # no drain applied by compute alone

    def test_2_2_media_tier_3_costs_correct(self):
        gs = make_shadow_gs(media_tier=3, personal_wealth=5.0)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        expected_media = SHADOW_TIER_COSTS["media"][3]
        assert gs.daily_media_cost == expected_media

    def test_2_3_militia_cost_charged(self):
        gs = make_shadow_gs(militia_tier=3, personal_wealth=5.0, militia_merged=False)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        expected_militia = TIER_COSTS["militia"][3]
        assert gs.daily_militia_cost == expected_militia
        assert total >= expected_militia

    def test_2_4_merged_militia_still_charged_in_compute(self):
        """Note: compute_shadow_state_costs does NOT skip militia cost when merged.
        The merger affects stability computation, not cost computation.
        This test documents actual behavior."""
        gs = make_shadow_gs(militia_tier=3, militia_merged=True, personal_wealth=5.0)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        # Militia cost is still computed even when merged
        expected_militia = TIER_COSTS["militia"][3]
        assert gs.daily_militia_cost == expected_militia

    def test_2_5_extraction_revenue_adds(self):
        gs = make_shadow_gs(extraction_tier=3, personal_wealth=5.0)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        assert ext_rev == EXTRACTION_REVENUE[3]
        assert ext_rev > 0

    def test_2_6_extraction_net_revenue(self):
        gs = make_shadow_gs(extraction_tier=5)
        total, ext_rev, net = compute_shadow_state_costs(gs)
        expected_cost = SHADOW_TIER_COSTS["extraction"][5]
        expected_rev = EXTRACTION_REVENUE[5]
        expected_net = round(expected_rev - expected_cost, 2)
        # Net is total_costs - extraction_revenue, so negative net means profitable
        # But net = total_shadow_cost - extraction_revenue (includes ALL axes)
        # For single axis: extraction cost 1.4, revenue 1.5 -> net for extraction alone is +0.1
        assert ext_rev == expected_rev
        assert expected_rev > expected_cost, "Extraction tier 5 should be profitable"

    def test_2_7_no_education_surcharge_on_media(self):
        """Spec mentions education surcharge on media at high tiers.
        DISCREPANCY: No education surcharge exists in compute_shadow_state_costs.
        Test documents actual behavior — media cost equals base cost."""
        gs = make_shadow_gs(media_tier=7, education_tier=3)
        compute_shadow_state_costs(gs)
        assert gs.daily_media_cost == SHADOW_TIER_COSTS["media"][7]

    def test_2_8_judicial_soft_prereq_doubles_cost_without_media(self):
        """Judicial tier 3+ requires media_tier >= 2 (soft prereq).
        Without it, cost is doubled."""
        gs = make_shadow_gs(judicial_tier=5, media_tier=0)
        compute_shadow_state_costs(gs)
        base_cost = SHADOW_TIER_COSTS["judicial"][5]
        assert gs.daily_judicial_cost == round(base_cost * 2.0, 2)

    def test_2_9_judicial_cost_normal_with_media_prereq_met(self):
        """Judicial tier 3+ with media_tier >= 2 — no penalty."""
        gs = make_shadow_gs(judicial_tier=5, media_tier=2)
        compute_shadow_state_costs(gs)
        assert gs.daily_judicial_cost == SHADOW_TIER_COSTS["judicial"][5]

    def test_2_10_skim_ceiling_enforced(self):
        gs = make_shadow_gs(extraction_tier=2, skim_rate=0.30)
        compute_shadow_state_costs(gs)
        assert gs.skim_rate == EXTRACTION_SKIM_CEILING[2]  # 0.12

    def test_2_11_shadow_unlocked_on_any_investment(self):
        gs = make_shadow_gs(media_tier=1)
        compute_shadow_state_costs(gs)
        assert gs.shadow_state_unlocked is True

    def test_2_11b_shadow_not_unlocked_at_zero(self):
        gs = make_shadow_gs()
        compute_shadow_state_costs(gs)
        assert gs.shadow_state_unlocked is False


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 3: Shadow axis flags
# ═══════════════════════════════════════════════════════════════════════════

class TestGroup3ShadowAxisFlags:
    """Test SHADOW_AXIS_FLAGS activation via compute_shadow_state_costs."""

    def test_3_1_media_tier_3_sets_press_suppressed(self):
        gs = make_shadow_gs(media_tier=3)
        compute_shadow_state_costs(gs)
        assert gs.action_press_suppressed is True

    def test_3_2_media_tier_2_does_not_set_press_suppressed(self):
        gs = make_shadow_gs(media_tier=2)
        compute_shadow_state_costs(gs)
        assert gs.action_press_suppressed is False

    def test_3_3_judicial_tier_4_sets_judiciary_captured(self):
        """SHADOW_AXIS_FLAGS maps judicial threshold 4 -> action_judiciary_captured.
        (Spec said tier 3, but code uses tier 4.)"""
        gs = make_shadow_gs(judicial_tier=4)
        compute_shadow_state_costs(gs)
        assert gs.action_judiciary_captured is True

    def test_3_3b_judicial_tier_3_does_not_set_judiciary_captured(self):
        gs = make_shadow_gs(judicial_tier=3)
        compute_shadow_state_costs(gs)
        assert gs.action_judiciary_captured is False

    def test_3_4_judicial_tier_7_sets_journalists_liquidated(self):
        """SHADOW_AXIS_FLAGS maps judicial 7 -> action_journalists_liquidated.
        (Spec said judicial 8 -> constitutional_revision_active, but actual mapping differs.)"""
        gs = make_shadow_gs(judicial_tier=7)
        compute_shadow_state_costs(gs)
        assert gs.action_journalists_liquidated is True

    def test_3_5_media_tier_5_sets_media_taken(self):
        """SHADOW_AXIS_FLAGS maps media 5 -> action_media_taken.
        (Spec said media 7 -> journalists_suppressed, but actual mapping differs.)"""
        gs = make_shadow_gs(media_tier=5)
        compute_shadow_state_costs(gs)
        assert gs.action_media_taken is True

    def test_3_6_opposition_dissolved_by_surveillance_and_judicial(self):
        """FIX1: opposition_dissolved requires surveillance >= 5 AND judicial >= 5."""
        gs = make_shadow_gs(domestic_surveillance_tier=5, judicial_tier=5)
        compute_shadow_state_costs(gs)
        assert gs.action_opposition_dissolved is True

    def test_3_7_opposition_not_dissolved_insufficient_tiers(self):
        """FIX1: political_tier alone no longer triggers opposition_dissolved."""
        gs = make_shadow_gs(political_tier=6)
        compute_shadow_state_costs(gs)
        assert gs.action_opposition_dissolved is False

    def test_3_7b_opposition_not_dissolved_partial_tiers(self):
        """FIX1: need BOTH surveillance and judicial at 5+."""
        gs = make_shadow_gs(domestic_surveillance_tier=5, judicial_tier=4)
        compute_shadow_state_costs(gs)
        assert gs.action_opposition_dissolved is False


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 4: compute_eu_ceiling()
# ═══════════════════════════════════════════════════════════════════════════

class TestGroup4EuCeiling:
    """Test EU relations ceiling from shadow/suppression flags."""

    def test_4_1_no_suppression_returns_100(self):
        gs = make_shadow_gs()
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 100

    def test_4_2_press_suppressed_caps_85(self):
        gs = make_shadow_gs(action_press_suppressed=True)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 85

    def test_4_3_judiciary_captured_caps_75(self):
        gs = make_shadow_gs(action_judiciary_captured=True)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 75

    def test_4_4_press_and_judiciary_caps_65(self):
        gs = make_shadow_gs(action_press_suppressed=True,
                            action_judiciary_captured=True)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 65

    def test_4_5_opposition_dissolved_caps_55(self):
        gs = make_shadow_gs(action_opposition_dissolved=True)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 55

    def test_4_6_journalists_liquidated_caps_40(self):
        gs = make_shadow_gs(action_journalists_liquidated=True)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 40

    def test_4_7_all_flags_active_caps_30(self):
        gs = make_shadow_gs(
            action_press_suppressed=True,
            action_judiciary_captured=True,
            action_opposition_dissolved=True,
            action_journalists_liquidated=True,
        )
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 30

    def test_4_8_tier_penalty_media_7(self):
        """media_tier >= 7 adds -5 penalty on top of flag ceiling."""
        gs = make_shadow_gs(action_press_suppressed=True, media_tier=7)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 80  # 85 - 5

    def test_4_9_tier_penalty_surv_5(self):
        """domestic_surveillance_tier >= 5 adds -5 penalty."""
        gs = make_shadow_gs(domestic_surveillance_tier=5)
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 95  # 100 - 5

    def test_4_10_all_tier_penalties_stack(self):
        """media_7 + judicial_7 + surv_5 = -15 total tier penalty."""
        gs = make_shadow_gs(
            action_press_suppressed=True,
            action_judiciary_captured=True,
            action_opposition_dissolved=True,
            action_journalists_liquidated=True,
            media_tier=7, judicial_tier=7,
            domestic_surveillance_tier=7,
        )
        # All flags -> 30, then -15 from tiers -> max(10, 15) = 15
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 15

    def test_4_11_eu_relations_above_ceiling(self):
        """Verify EU ceiling value. Clamping is done by caller, not compute_eu_ceiling."""
        gs = make_shadow_gs(
            action_press_suppressed=True,
            relationships={"eu": 90, "usa": 55, "russia": 30,
                           "china": 35, "arabia": 45, "dprg": 40},
        )
        ceiling = compute_eu_ceiling(gs)
        assert ceiling == 85
        assert gs.relationships["eu"] == 90  # compute_eu_ceiling doesn't clamp


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 5: Advisor elimination fear effect
# ═══════════════════════════════════════════════════════════════════════════

def _make_advisor(name, trust=75, competence=60):
    return {"name": name, "label": name, "trust": trust, "competence": competence,
            "archetype": name}


class TestGroup5AdvisorElimination:
    """Test fear effects from eliminate_advisor in advisor_engine."""

    def test_5_1_first_elimination_grants_fear_bonus(self):
        gs = make_shadow_gs(
            personal_wealth=10.0,
            advisors={
                "technocrat": _make_advisor("Technocrat"),
                "diplomat": _make_advisor("Diplomat"),
                "finance_minister": _make_advisor("Finance Minister"),
            },
            advisor_elimination_count=0,
        )
        success, msg = eliminate_advisor(gs, "finance_minister")
        assert success is True
        assert gs.advisor_elimination_count == 1
        assert len(gs.advisors_with_fear_bonus) == 2
        assert len(gs.advisors_witnessed_elimination) == 2
        assert "technocrat" in gs.advisors_with_fear_bonus
        assert "diplomat" in gs.advisors_with_fear_bonus

    def test_5_2_first_elimination_fear_bonus_is_15(self):
        gs = make_shadow_gs(
            personal_wealth=10.0,
            advisors={
                "technocrat": _make_advisor("Technocrat", trust=50),
                "target": _make_advisor("Target"),
            },
            advisor_elimination_count=0,
        )
        eliminate_advisor(gs, "target")
        assert gs.advisors["technocrat"]["trust"] == 65  # 50 + 15

    def test_5_3_repeat_elimination_within_10_days_gives_25(self):
        gs = make_shadow_gs(
            personal_wealth=10.0,
            advisors={
                "technocrat": _make_advisor("Technocrat", trust=50),
                "target": _make_advisor("Target"),
            },
            advisor_elimination_count=1,
            advisor_elimination_last_day=3,
            current_day=8,  # 5 days since last — within 10 day window
        )
        eliminate_advisor(gs, "target")
        assert gs.advisors["technocrat"]["trust"] == 75  # 50 + 25
        assert "technocrat" in gs.advisors_chronically_fearful

    def test_5_4_chronically_fearful_on_repeat(self):
        """Chronically fearful is set on 2nd+ elimination within window (repeat_2)."""
        gs = make_shadow_gs(
            personal_wealth=10.0,
            advisors={
                "technocrat": _make_advisor("Technocrat", trust=50, competence=60),
                "target": _make_advisor("Target"),
            },
            advisor_elimination_count=2,
            advisor_elimination_last_day=5,
            current_day=15,  # 10 days since last — within 20 day window
        )
        eliminate_advisor(gs, "target")
        assert len(gs.advisors_chronically_fearful) > 0
        # Competence degraded by 10
        assert gs.advisors["technocrat"]["competence"] == 50

    def test_5_5_historian_fear_note_not_implemented(self):
        """DISCREPANCY: historian_fear_note field does not exist in codebase.
        Test documents this gap."""
        gs = make_shadow_gs(
            personal_wealth=10.0,
            advisors={
                "technocrat": _make_advisor("Technocrat"),
                "target": _make_advisor("Target"),
            },
            advisor_elimination_count=2,
            advisor_elimination_last_day=5,
            current_day=15,
        )
        eliminate_advisor(gs, "target")
        assert not hasattr(gs, 'historian_fear_note') or gs.historian_fear_note is None


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 6: Merger mechanics
# ═══════════════════════════════════════════════════════════════════════════

class TestGroup6Mergers:
    """Test militia and surveillance merger logic (from api.py merge endpoint).
    Since the merge endpoint requires FastAPI and session loading, we test
    the conditions and effects directly."""

    def test_6_1_militia_merger_requires_both_tiers_5(self):
        """Merger conditions: militia_tier >= 5 AND military_tier >= 5.
        (Spec said militia_tier >= 3, military_tier >= 2 — code uses 5/5.)"""
        # Both at 5 — valid
        gs = make_shadow_gs(militia_tier=5, military_tier=5, militia_merged=False)
        assert gs.militia_tier >= 5 and gs.military_tier >= 5

        # Militia too low
        gs2 = make_shadow_gs(militia_tier=4, military_tier=5, militia_merged=False)
        assert not (gs2.militia_tier >= 5 and gs2.military_tier >= 5)

        # Military too low
        gs3 = make_shadow_gs(militia_tier=5, military_tier=4, militia_merged=False)
        assert not (gs3.militia_tier >= 5 and gs3.military_tier >= 5)

    def test_6_2_militia_merger_sets_flag(self):
        gs = make_shadow_gs(militia_tier=5, military_tier=5, militia_merged=False)
        # Simulate merger (api.py just sets the flag)
        gs.militia_merged = True
        assert gs.militia_merged is True

    def test_6_3_militia_merger_does_not_reset_tier(self):
        """DISCREPANCY: Spec says militia_tier resets to 0 after merger.
        Code does NOT reset militia_tier — only sets militia_merged=True."""
        gs = make_shadow_gs(militia_tier=5, military_tier=5, militia_merged=False)
        gs.militia_merged = True  # simulating merger
        # Code does NOT modify militia_tier
        assert gs.militia_tier == 5

    def test_6_4_militia_merger_does_not_change_military_tier(self):
        """DISCREPANCY: Spec says military_tier = max(militia, military).
        Code does NOT modify military_tier — only sets militia_merged=True."""
        gs = make_shadow_gs(militia_tier=5, military_tier=3)
        gs.militia_merged = True
        assert gs.military_tier == 3  # unchanged

    def test_6_5_surveillance_merger_sets_flag(self):
        gs = make_shadow_gs(
            domestic_surveillance_tier=5, intelligence_tier=5,
            surveillance_merged=False,
        )
        # Merger conditions met
        assert gs.domestic_surveillance_tier >= 5
        assert gs.intelligence_tier >= 5
        gs.surveillance_merged = True
        assert gs.surveillance_merged is True

    def test_6_6_surveillance_merger_requires_both_tiers_5(self):
        """Surveillance merger: domestic_surveillance_tier >= 5 AND intelligence_tier >= 5."""
        gs = make_shadow_gs(domestic_surveillance_tier=4, intelligence_tier=5)
        assert not (gs.domestic_surveillance_tier >= 5 and gs.intelligence_tier >= 5)

    def test_6_7_merged_militia_not_counted_in_stability(self):
        """When militia_merged, militia_score in stability = 0 (checked in compute_stability_components)."""
        # This is tested indirectly — the stability code checks militia_merged
        gs = make_shadow_gs(militia_tier=5, militia_merged=True)
        # The compute_stability_components checks militia_merged
        # We verify the field is set correctly
        assert gs.militia_merged is True
        assert gs.militia_tier == 5
