"""
9.5A Commitment Model — Comprehensive Tests
Tests: TIER_COSTS, cooldowns, GDP gates, compute_daily_commitment_cost,
compute_tax_revenue, check_prerequisites, apply_commitment_eot_checks
"""
import sys
import pytest

sys.path.insert(0, r"C:\Users\nbbq8\OneDrive\Creative Projects\Claude Apps\GeoSim 3")

from turn_processor import (
    TIER_COSTS, TIER_UPGRADE_COOLDOWNS, GDP_GATES, PREREQUISITES,
    COMMITMENT_EDUCATION_DISCOUNTS, COMMITMENT_TECH_DISCOUNTS,
    check_prerequisites, compute_daily_commitment_cost, compute_tax_revenue,
    apply_commitment_eot_checks,
)


# ── Helper: MockGS ───────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a minimal game state with safe defaults for commitment tests."""
    defaults = dict(
        military_tier=1, intelligence_tier=1, diplomatic_tier=0,
        social_tier=1, education_tier=0, resource_tier=0,
        political_tier=0, militia_tier=0,
        personal_wealth=10.0, tech_level=0,
        detection_heat=0,
        gdp_base=100.0, public_approval=55, stability=50,
        income_tax_rate=0.25, corporate_tax_rate=0.20,
        tax_rates={'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25},
        resource_endowment={'oil_reserves': 0.7},
        tax_structure='balanced', skim_rate=0.0,
        usa_sanctions_tier=0, arabia_embargo_tier=0,
        state_identity={'regime_type': 'Managed Democracy'},
        _infra_gdp_bonus=0.0, education_level=0,
        # Daily cost fields (set by compute_daily_commitment_cost)
        daily_military_cost=0, daily_intel_cost=0, daily_diplomatic_cost=0,
        daily_social_cost=0, daily_education_cost=0, daily_resource_cost=0,
        total_daily_commitment=0,
        # EOT check fields
        action_press_suppressed=False, action_judiciary_captured=False,
        action_opposition_dissolved=False, action_journalists_liquidated=False,
        coup_amplifier_active=False, intel_politicized=False,
        eu_relations_ceiling=100, commitment_deficit_days=0,
        relations={'eu': 50, 'usa': 50, 'arabia': 50, 'dprg': 30},
        prerequisite_violations={},
    )
    defaults.update(overrides)

    class MockGS:
        def update_budget(self, amount):
            self.budget = round(getattr(self, 'budget', 30.0) + amount, 2)
        def update_personal_wealth(self, amount, source=''):
            self.personal_wealth = round(self.personal_wealth + amount, 2)

    gs = MockGS()
    for k, v in defaults.items():
        setattr(gs, k, v)
    return gs


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: TIER_COSTS tables
# ══════════════════════════════════════════════════════════════════════════════

class TestTierCosts:
    def test_1_1_all_axes_have_tiers_0_through_10(self):
        """All axes have entries for tiers 0-10."""
        expected_keys = set(range(11))
        for axis_key, tiers in TIER_COSTS.items():
            assert set(tiers.keys()) == expected_keys, \
                f"{axis_key} missing tiers: {expected_keys - set(tiers.keys())}"

    def test_1_2_tier_0_always_costs_zero(self):
        """Tier 0 always costs 0."""
        for axis_key, tiers in TIER_COSTS.items():
            assert tiers[0] == 0.0, f"{axis_key} tier 0 cost is {tiers[0]}, expected 0.0"

    def test_1_3_costs_increase_monotonically(self):
        """Each tier costs more than the previous."""
        for axis_key, tiers in TIER_COSTS.items():
            for t in range(1, 11):
                assert tiers[t] > tiers[t - 1], \
                    f"{axis_key} tier {t} ({tiers[t]}) not > tier {t-1} ({tiers[t-1]})"

    def test_1_4_militia_costs_are_positive(self):
        """Militia entries exist and are positive at tier 5."""
        assert TIER_COSTS["militia"][5] > 0, "Militia tier 5 should have positive cost"


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: TIER_UPGRADE_COOLDOWNS
# ══════════════════════════════════════════════════════════════════════════════

class TestCooldowns:
    def test_2_1_cooldowns_increase_with_tier(self):
        """For each axis: cooldown at tier N >= cooldown at tier N-1."""
        for axis_key, cds in TIER_UPGRADE_COOLDOWNS.items():
            tiers = sorted(cds.keys())
            for i in range(1, len(tiers)):
                assert cds[tiers[i]] >= cds[tiers[i - 1]], \
                    f"{axis_key} tier {tiers[i]} cooldown ({cds[tiers[i]]}) " \
                    f"< tier {tiers[i-1]} ({cds[tiers[i-1]]})"

    def test_2_2_tier_10_cooldowns_at_least_25(self):
        """Higher tiers have longer cooldowns: tier 10 >= 25 days."""
        for axis_key, cds in TIER_UPGRADE_COOLDOWNS.items():
            assert cds[10] >= 25, \
                f"{axis_key} tier 10 cooldown is {cds[10]}, expected >= 25"

    def test_2_3_tier_1_cooldowns_short(self):
        """Tier 1 cooldowns are short (<= 3 days)."""
        for axis_key, cds in TIER_UPGRADE_COOLDOWNS.items():
            assert cds[1] <= 3, \
                f"{axis_key} tier 1 cooldown is {cds[1]}, expected <= 3"


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: GDP_GATES
# ══════════════════════════════════════════════════════════════════════════════

class TestGDPGates:
    def test_3_1_tiers_0_through_6_have_no_gate(self):
        """GDP_GATES does not contain keys 0-6."""
        for t in range(7):
            assert t not in GDP_GATES, f"Tier {t} should not have a GDP gate"

    def test_3_2_gdp_gate_increases_with_tier(self):
        """GDP_GATES[7] < [8] < [9] < [10]."""
        assert GDP_GATES[7] < GDP_GATES[8] < GDP_GATES[9] < GDP_GATES[10]

    def test_3_3_tier_10_requires_250B(self):
        """Tier 10 requires $250B GDP."""
        assert GDP_GATES[10] == 250.0


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 4: compute_daily_commitment_cost()
# ══════════════════════════════════════════════════════════════════════════════

class TestCommitmentCost:
    def test_4_1_all_tiers_zero_returns_zero(self):
        """All tiers at 0 returns 0 budget cost."""
        gs = make_gs(military_tier=0, intelligence_tier=0, social_tier=0,
                     diplomatic_tier=0, education_tier=0, resource_tier=0,
                     political_tier=0, militia_tier=0)
        budget_total, militia_cost = compute_daily_commitment_cost(gs)
        assert budget_total == 0.0, f"Expected 0, got {budget_total}"
        assert militia_cost == 0.0

    def test_4_2_default_tiers_return_expected_range(self):
        """Default tiers (mil=1, intel=1, social=1) return budget between 1.0 and 2.5."""
        gs = make_gs()
        budget_total, _ = compute_daily_commitment_cost(gs)
        assert 1.0 <= budget_total <= 2.5, \
            f"Expected 1.0-2.5, got {budget_total}"

    def test_4_3_militia_cost_returned_separately(self):
        """Militia tier 3 returns positive militia_cost from function."""
        gs = make_gs(militia_tier=3)
        budget_total, militia_cost = compute_daily_commitment_cost(gs)
        assert militia_cost > 0, f"Expected positive militia cost, got {militia_cost}"
        assert militia_cost == TIER_COSTS["militia"][3]

    def test_4_4_militia_cost_not_in_budget_total(self):
        """Militia cost should not be included in budget_total."""
        gs_no_militia = make_gs(militia_tier=0)
        bt_no, _ = compute_daily_commitment_cost(gs_no_militia)

        gs_with_militia = make_gs(militia_tier=5)
        bt_with, mc = compute_daily_commitment_cost(gs_with_militia)

        assert bt_no == bt_with, \
            f"Budget totals should match regardless of militia: {bt_no} vs {bt_with}"
        assert mc > 0

    def test_4_5_education_discount_applies_to_military(self):
        """Military tier 3 with education tier 2 gets a discount."""
        gs = make_gs(military_tier=3, education_tier=2)
        compute_daily_commitment_cost(gs)
        base_cost = TIER_COSTS["military"][3]
        assert gs.daily_military_cost < base_cost, \
            f"Expected discount: {gs.daily_military_cost} should be < {base_cost}"

    def test_4_6_education_discount_not_below_threshold(self):
        """Military tier 2 with education tier 2: no discount (discount requires mil 3+)."""
        gs = make_gs(military_tier=2, education_tier=2)
        compute_daily_commitment_cost(gs)
        base_cost = TIER_COSTS["military"][2]
        assert gs.daily_military_cost == base_cost, \
            f"Expected no discount: {gs.daily_military_cost} should equal {base_cost}"

    def test_4_7_tech_discount_applies_to_intelligence(self):
        """Intel tier 2 with tech_level >= 50 (tech_tier 3) gets discount."""
        gs = make_gs(intelligence_tier=2, tech_level=50)
        compute_daily_commitment_cost(gs)
        base_cost = TIER_COSTS["intelligence"][2]
        assert gs.daily_intel_cost < base_cost, \
            f"Expected discount: {gs.daily_intel_cost} should be < {base_cost}"

    def test_4_8_stored_costs_match_returned_total(self):
        """total_daily_commitment on gs matches budget_total return value."""
        gs = make_gs(military_tier=2, intelligence_tier=2, social_tier=2)
        budget_total, _ = compute_daily_commitment_cost(gs)
        assert gs.total_daily_commitment == budget_total, \
            f"Stored {gs.total_daily_commitment} != returned {budget_total}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 5: compute_tax_revenue()
# NOTE: compute_tax_revenue() returns a dict and does NOT modify game_state.
# Skim diversion, heat generation, and personal_wealth updates happen in
# Section 6 budget integration (apply_end_of_turn_effects), not here.
# Tests adapted to check returned dict values.
# ══════════════════════════════════════════════════════════════════════════════

class TestTaxRevenue:
    def test_5_1_laffer_low_rate_full_collection(self):
        """Income at 20% rate: Laffer modifier = 1.0 (full collection)."""
        gs = make_gs(income_tax_rate=0.20, gdp_base=100.0)
        result = compute_tax_revenue(gs)
        # income_base = 100 * 0.20 * 0.10 = 2.0, laffer=1.0
        assert result['laffer_income'] == 1.0

    def test_5_2_laffer_high_rate_reduces_returns(self):
        """Income at 55% rate: Laffer modifier < 1.0."""
        gs = make_gs(income_tax_rate=0.55, gdp_base=100.0)
        result = compute_tax_revenue(gs)
        assert result['laffer_income'] < 1.0, \
            f"Expected Laffer < 1.0 at 55%, got {result['laffer_income']}"

    def test_5_3_laffer_extreme_rate_severe_penalty(self):
        """Income at 70% rate: Laffer modifier severely reduced."""
        gs = make_gs(income_tax_rate=0.70, gdp_base=100.0)
        result = compute_tax_revenue(gs)
        assert result['laffer_income'] <= 0.75, \
            f"Expected Laffer <= 0.75 at 70%, got {result['laffer_income']}"

    def test_5_4_elite_structure_changes_income(self):
        """Elite-heavy tax structure modifies income vs balanced."""
        gs_elite = make_gs(tax_structure='elite_heavy', income_tax_rate=0.25)
        gs_balanced = make_gs(tax_structure='balanced', income_tax_rate=0.25)
        r_elite = compute_tax_revenue(gs_elite)
        r_balanced = compute_tax_revenue(gs_balanced)
        # elite_heavy: income modifier 0.85, corporate 1.15
        # elite income < balanced income (0.85 < 1.0)
        assert r_elite['income_rev'] < r_balanced['income_rev'], \
            f"Elite income {r_elite['income_rev']} should be < balanced {r_balanced['income_rev']}"

    def test_5_5_mass_structure_decreases_corporate(self):
        """Mass-heavy tax structure reduces corporate revenue vs balanced."""
        gs_mass = make_gs(tax_structure='mass_heavy', corporate_tax_rate=0.20)
        gs_balanced = make_gs(tax_structure='balanced', corporate_tax_rate=0.20)
        r_mass = compute_tax_revenue(gs_mass)
        r_balanced = compute_tax_revenue(gs_balanced)
        assert r_mass['corp_rev'] < r_balanced['corp_rev'], \
            f"Mass corp {r_mass['corp_rev']} should be < balanced {r_balanced['corp_rev']}"

    def test_5_6_education_increases_tax_efficiency(self):
        """Education level 2 yields more revenue than level 0."""
        gs_edu2 = make_gs(education_level=2)
        gs_edu0 = make_gs(education_level=0)
        r2 = compute_tax_revenue(gs_edu2)
        r0 = compute_tax_revenue(gs_edu0)
        assert r2['net_revenue'] > r0['net_revenue'], \
            f"Edu2 net {r2['net_revenue']} should be > edu0 net {r0['net_revenue']}"

    def test_5_7_heat_above_60_reduces_revenue(self):
        """FIX1: detection_heat > 60 applies -0.10 institution_mod penalty."""
        gs_high = make_gs(detection_heat=70)
        gs_low = make_gs(detection_heat=20)
        r_high = compute_tax_revenue(gs_high)
        r_low = compute_tax_revenue(gs_low)
        assert r_high['net_revenue'] < r_low['net_revenue'], \
            f"Heat 70 revenue {r_high['net_revenue']} should be < heat 20 revenue {r_low['net_revenue']}"

    def test_5_7b_heat_41_to_60_applies_smaller_penalty(self):
        """FIX1: detection_heat 41-60 applies -0.05 institution_mod penalty."""
        gs_mid = make_gs(detection_heat=50)
        gs_low = make_gs(detection_heat=30)
        r_mid = compute_tax_revenue(gs_mid)
        r_low = compute_tax_revenue(gs_low)
        assert r_mid['net_revenue'] < r_low['net_revenue'], \
            f"Heat 50 revenue {r_mid['net_revenue']} should be < heat 30 revenue {r_low['net_revenue']}"

    def test_5_7c_heat_40_or_below_no_penalty(self):
        """FIX1: detection_heat <= 40 has no institution_mod penalty."""
        gs_a = make_gs(detection_heat=40)
        gs_b = make_gs(detection_heat=10)
        r_a = compute_tax_revenue(gs_a)
        r_b = compute_tax_revenue(gs_b)
        assert r_a['net_revenue'] == r_b['net_revenue'], \
            f"Heat 40 and 10 should produce equal revenue (both <= 40 threshold)"

    def test_5_8_skim_diverts_in_result(self):
        """Skim rate 10% produces skim_income > 0 in returned dict."""
        gs = make_gs(skim_rate=0.10, gdp_base=100.0)
        result = compute_tax_revenue(gs)
        assert result['skim_income'] > 0, f"Expected skim > 0, got {result['skim_income']}"
        assert result['net_revenue'] < result['gross_revenue'], \
            "Net revenue should be less than gross when skimming"

    def test_5_9_skim_zero_no_diversion(self):
        """Skim rate 0% produces zero skim_income."""
        gs = make_gs(skim_rate=0.0)
        result = compute_tax_revenue(gs)
        assert result['skim_income'] == 0.0, f"Expected 0 skim, got {result['skim_income']}"

    def test_5_10_high_skim_larger_diversion(self):
        """Higher skim rate produces more diversion."""
        gs_low = make_gs(skim_rate=0.05)
        gs_high = make_gs(skim_rate=0.20)
        r_low = compute_tax_revenue(gs_low)
        r_high = compute_tax_revenue(gs_high)
        assert r_high['skim_income'] > r_low['skim_income']

    def test_5_11_skim_heat_generated_in_compute_tax_revenue(self):
        """FIX2: Skim heat is now generated inside compute_tax_revenue()
        when skim_rate > 5%. Heat = (skim_rate - 0.05) * 100."""
        gs = make_gs(skim_rate=0.20, detection_heat=0)
        compute_tax_revenue(gs)
        # 20% - 5% = 15% -> 15 heat
        assert gs.detection_heat == 15, \
            f"Expected 15 heat from 20% skim, got {gs.detection_heat}"

    def test_5_11b_skim_below_threshold_no_heat(self):
        """FIX2: Skim rate <= 5% generates no heat."""
        gs = make_gs(skim_rate=0.05, detection_heat=0)
        compute_tax_revenue(gs)
        assert gs.detection_heat == 0, \
            f"Expected 0 heat from 5% skim, got {gs.detection_heat}"

    def test_5_11c_skim_heat_accumulates(self):
        """FIX2: Skim heat adds to existing detection_heat."""
        gs = make_gs(skim_rate=0.10, detection_heat=30)
        compute_tax_revenue(gs)
        # 10% - 5% = 5% -> 5 heat, starting from 30
        assert gs.detection_heat == 35, \
            f"Expected 35 total heat (30 + 5), got {gs.detection_heat}"

    def test_5_12_resource_not_tier_dependent(self):
        """DISCREPANCY: compute_tax_revenue does not use resource_tier.
        Resource revenue uses fixed GDP fraction * resource_rate * oil_factor,
        not resource_tier. The tier affects daily commitment cost, not revenue."""
        gs = make_gs(resource_tier=3)
        gs2 = make_gs(resource_tier=1)
        r1 = compute_tax_revenue(gs)
        r2 = compute_tax_revenue(gs2)
        assert r1['resource_rev'] == r2['resource_rev'], \
            "Resource revenue should be identical regardless of resource_tier"

    def test_5_13_resource_policy_not_implemented(self):
        """DISCREPANCY: compute_tax_revenue does not check resource_policy.
        The design spec describes state_led vs private_sector modifiers,
        but current implementation uses fixed formula."""
        gs_state = make_gs(resource_policy='state_led')
        gs_private = make_gs(resource_policy='private_sector')
        r_s = compute_tax_revenue(gs_state)
        r_p = compute_tax_revenue(gs_private)
        assert r_s['resource_rev'] == r_p['resource_rev'], \
            "Resource policy should have no effect (not yet implemented)"


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 6: check_prerequisites()
# ══════════════════════════════════════════════════════════════════════════════

class TestPrerequisites:
    def test_6_1_military_5_requires_tech_2_unmet(self):
        """Military tier 5 with tech_level=1 (tech_tier 0): prerequisite not met."""
        gs = make_gs(tech_level=1)
        result = check_prerequisites(gs, 'military', 5)
        assert result['met'] is False
        assert result['cost_multiplier'] == 2.0

    def test_6_2_military_5_met_with_tech_2(self):
        """Military tier 5 with tech_level=25 (tech_tier 2): prerequisite met."""
        # PREREQUISITES["military"][5] = {"tech_level": 2}
        # tech_level is checked as getattr(gs, 'tech_level', 0) and compared to 2
        gs = make_gs(tech_level=2)
        result = check_prerequisites(gs, 'military', 5)
        assert result['met'] is True
        assert result['cost_multiplier'] == 1.0

    def test_6_3_gdp_gate_triggers_cost_multiplier(self):
        """Military tier 7 with GDP $60B (below $80B gate): cost multiplier >= 3."""
        gs = make_gs(gdp_base=60.0, tech_level=2, education_tier=1, intelligence_tier=4)
        result = check_prerequisites(gs, 'military', 7)
        assert result['cost_multiplier'] >= 3.0, \
            f"Expected >= 3.0, got {result['cost_multiplier']}"

    def test_6_4_gdp_gate_not_triggered_above_threshold(self):
        """Military tier 7 with GDP $100B (above $80B gate): no GDP multiplier."""
        gs = make_gs(gdp_base=100.0, tech_level=2, education_tier=1, intelligence_tier=4)
        result = check_prerequisites(gs, 'military', 7)
        # Should still have cost_multiplier from any unmet soft prereqs
        # but NOT from GDP gate
        assert 'GDP' not in ' '.join(result.get('violations', [])), \
            "Should not have GDP violation above gate"

    def test_6_5_diplomatic_7_hard_blocked_with_judicial_capture(self):
        """Diplomatic tier 7 with judicial capture: hard blocked."""
        gs = make_gs(action_judiciary_captured=True, education_tier=1)
        result = check_prerequisites(gs, 'diplomatic', 7)
        assert result['hard_blocked'] is True

    def test_6_6_diplomatic_7_not_blocked_without_judicial_capture(self):
        """Diplomatic tier 7 without judicial capture: not hard blocked."""
        gs = make_gs(action_judiciary_captured=False, education_tier=1)
        result = check_prerequisites(gs, 'diplomatic', 7)
        assert result['hard_blocked'] is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 7: EOT checks (apply_commitment_eot_checks)
# ══════════════════════════════════════════════════════════════════════════════

class TestEOTChecks:
    def test_7_1_coup_amplifier_fires_when_gap_gt_3(self):
        """Military tier 7 - political tier 3 = gap 4 > 3: coup amplifier active."""
        gs = make_gs(military_tier=7, political_tier=3)
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.coup_amplifier_active is True

    def test_7_2_coup_amplifier_not_active_within_3(self):
        """Military tier 5 - political tier 3 = gap 2 <= 3: no coup amplifier."""
        gs = make_gs(military_tier=5, political_tier=3)
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.coup_amplifier_active is False

    def test_7_3_intel_politicized_above_threshold(self):
        """Political tier 7, intel tier 5: intel politicized."""
        gs = make_gs(political_tier=7, intelligence_tier=5)
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.intel_politicized is True

    def test_7_4_intel_not_politicized_below_threshold(self):
        """Political tier 6, intel tier 5: intel NOT politicized."""
        gs = make_gs(political_tier=6, intelligence_tier=5)
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.intel_politicized is False

    def test_7_5_eu_ceiling_press_suppression_caps_85(self):
        """Press suppression active: EU ceiling = 85, EU relations capped."""
        gs = make_gs(action_press_suppressed=True)
        gs.relations['eu'] = 90
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.eu_relations_ceiling == 85
        assert gs.relations['eu'] <= 85

    def test_7_6_eu_ceiling_all_suppression_30(self):
        """All four suppression flags: EU ceiling = 30."""
        gs = make_gs(
            action_press_suppressed=True,
            action_judiciary_captured=True,
            action_opposition_dissolved=True,
            action_journalists_liquidated=True,
        )
        gs.relations['eu'] = 95
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.eu_relations_ceiling == 30
        assert gs.relations['eu'] == 30

    def test_7_7_eu_ceiling_no_suppression_100(self):
        """No suppression flags: EU ceiling = 100."""
        gs = make_gs()
        msgs = []
        apply_commitment_eot_checks(gs, msgs)
        assert gs.eu_relations_ceiling == 100

    def test_7_8_sustainability_gap_deficit_days_increment(self):
        """Commitment > revenue * 1.2: deficit_days increments."""
        gs = make_gs(total_daily_commitment=20.0, commitment_deficit_days=0)
        # Need daily costs set for the degradation search
        gs.daily_military_cost = 5.0
        gs.military_tier = 3
        msgs = []
        apply_commitment_eot_checks(gs, msgs, net_revenue=10.0)
        # 20.0 > 10.0 * 1.2 = 12.0, so deficit_days should increment
        assert gs.commitment_deficit_days == 1

    def test_7_9_sustainability_gap_tier_degrades_after_5_days(self):
        """After 5 deficit days: highest-cost tier degrades, counter resets."""
        gs = make_gs(
            total_daily_commitment=20.0,
            commitment_deficit_days=4,  # will become 5 after increment
            military_tier=3,
        )
        gs.daily_military_cost = 5.0  # highest cost
        gs.daily_intel_cost = 0.3
        gs.daily_diplomatic_cost = 0.0
        gs.daily_social_cost = 0.4
        gs.daily_education_cost = 0.0
        gs.daily_resource_cost = 0.0
        gs.intelligence_tier = 1
        gs.social_tier = 1
        msgs = []
        apply_commitment_eot_checks(gs, msgs, net_revenue=10.0)
        # deficit_days goes 4 -> 5, triggering degradation
        assert gs.military_tier == 2, f"Expected mil tier 2, got {gs.military_tier}"
        assert gs.commitment_deficit_days == 0, "Should reset after degradation"

    def test_7_10_sustainability_no_degrade_when_surplus(self):
        """When commitment <= revenue * 1.2: deficit_days resets to 0."""
        gs = make_gs(
            total_daily_commitment=5.0,
            commitment_deficit_days=3,
            military_tier=3,
        )
        gs.daily_military_cost = 1.4
        msgs = []
        # 5.0 <= 10.0 * 1.2 = 12.0, so surplus — deficit resets to 0
        apply_commitment_eot_checks(gs, msgs, net_revenue=10.0)
        assert gs.commitment_deficit_days == 0, \
            f"Expected 0 (reset), got {gs.commitment_deficit_days}"
