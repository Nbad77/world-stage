"""Tests for 9B Political Biography — compute_biography_context and determine_biography_sections."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from npc_engine import compute_biography_context, determine_biography_sections


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: MockGameState + make_test_game_state
# ═══════════════════════════════════════════════════════════════════════════════

class MockGameState:
    """Minimal mock with only the fields compute_biography_context reads."""
    pass


def make_test_game_state(**overrides):
    """
    Create a MockGameState with safe defaults for all fields biography context reads.

    Override keys use the user-facing names from the spec; this helper maps them
    to the actual GameState field names used by the implementation.
    """
    gs = MockGameState()

    # ── Arc ──────────────────────────────────────────────────────────────────
    turn = overrides.get('turn', 5)
    gs.current_day = turn
    gs.current_turn = turn
    gs.current_era = overrides.get('era', 2)

    gs.state_identity = {
        'regime_type': overrides.get('regime_label', 'managed_democracy')
    }
    gs.regime_history = overrides.get('regime_history', [
        {"era": 1, "label": "managed_democracy", "turns_held": 5}
    ])

    ending_type = overrides.get('ending_type', 'unknown')
    gs.ending_triggered = None if ending_type == 'unknown' else ending_type

    gs.in_exile = overrides.get('in_exile', False)
    gs.exile_day = overrides.get('exile_day', 0)
    gs.exile_trigger = overrides.get('exile_trigger', None)
    gs.departure_heat = overrides.get('departure_heat', None)
    gs.return_attempts = overrides.get('return_attempts', 0)
    gs.restoration_active = overrides.get('restoration_active', False)
    gs.prior_regime_label = overrides.get('prior_regime_label', None)

    # ── Relations ────────────────────────────────────────────────────────────
    rels = overrides.get('relationships', {
        "usa": 55, "eu": 60, "russia": 30, "china": 35, "arabia": 45, "dprg": 40
    })
    gs.relations = dict(rels)
    gs.deal_history = overrides.get('deals_made', [])

    # binding_promises is the actual field name (user spec calls it promise_tracker)
    if 'promise_tracker' in overrides:
        gs.binding_promises = overrides['promise_tracker']
    elif overrides.get('_no_promises', False):
        # Special flag: do NOT set binding_promises at all (for test 6.4)
        pass
    else:
        gs.binding_promises = []

    gs.npc_assistance_tiers = overrides.get('npc_assistance_tiers', {})

    # ── Domestic — suppression flags ─────────────────────────────────────────
    gs.action_press_suppressed = overrides.get('press_suppression_active', False)
    gs.action_judiciary_captured = overrides.get('judicial_capture_active', False)
    gs.action_opposition_dissolved = overrides.get('opposition_dissolved', False)
    gs.action_journalists_liquidated = overrides.get('journalists_liquidated', False)

    # ── Domestic — skim ──────────────────────────────────────────────────────
    # Implementation computes: skim_rate = total_skimmed / (budget * current_turn)
    # So total_skimmed = desired_skim_rate * budget * current_turn
    budget = overrides.get('budget', 65.0)
    gs.budget = budget
    desired_skim_rate = overrides.get('skim_rate', 0.02)
    gs.total_skimmed = desired_skim_rate * gs.budget * gs.current_turn

    # ── Domestic — approval ──────────────────────────────────────────────────
    gs.public_approval = overrides.get('public_approval', overrides.get('approval', 55))
    gs.peak_approval = overrides.get('peak_approval', 65)

    # ── Domestic — education ─────────────────────────────────────────────────
    gs.education_level = overrides.get('education_level', 1)

    # ── Domestic — elections ─────────────────────────────────────────────────
    # Implementation: _elections_held = 1 if election_fired else 0
    #                 _elections_stolen = 1 if election_result == 'rigged' else 0
    elections_held = overrides.get('elections_held', 2)
    elections_stolen = overrides.get('elections_stolen', 0)
    gs.election_fired = elections_held > 0
    gs.election_result = 'rigged' if elections_stolen > 0 else None

    # ── Economy ──────────────────────────────────────────────────────────────
    gs.gdp_base = overrides.get('gdp', 85.0)
    gs.gdp_start = overrides.get('gdp_start', 75.0)
    gs.gdp_peak = overrides.get('gdp_peak', 90.0)

    # ── Personal ─────────────────────────────────────────────────────────────
    gs.personal_wealth = overrides.get('personal_wealth', 5.0)

    return gs


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: compute_biography_context — arc fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestArcFields:
    def test_1_1_exile_occurred_true_when_exile_day_positive(self):
        gs = make_test_game_state(exile_day=10, in_exile=False)
        ctx = compute_biography_context(gs)
        assert ctx["exile_occurred"] is True

    def test_1_2_exile_occurred_true_when_in_exile(self):
        gs = make_test_game_state(in_exile=True, exile_day=0)
        ctx = compute_biography_context(gs)
        assert ctx["exile_occurred"] is True

    def test_1_3_exile_occurred_false_for_clean_game(self):
        gs = make_test_game_state(in_exile=False, exile_day=0)
        ctx = compute_biography_context(gs)
        assert ctx["exile_occurred"] is False

    def test_1_4_return_succeeded_true_when_restored(self):
        gs = make_test_game_state(in_exile=False, exile_day=15, restoration_active=False)
        ctx = compute_biography_context(gs)
        assert ctx["return_succeeded"] is True

    def test_1_5_return_succeeded_false_when_still_in_exile(self):
        gs = make_test_game_state(in_exile=True, exile_day=5)
        ctx = compute_biography_context(gs)
        assert ctx["return_succeeded"] is False

    def test_1_6_return_succeeded_false_when_never_exiled(self):
        gs = make_test_game_state(in_exile=False, exile_day=0)
        ctx = compute_biography_context(gs)
        assert ctx["return_succeeded"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: compute_biography_context — domestic fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomesticFields:
    def test_2_1_suppression_actions_populated(self):
        gs = make_test_game_state(
            press_suppression_active=True,
            judicial_capture_active=True,
            opposition_dissolved=False,
            journalists_liquidated=False,
        )
        ctx = compute_biography_context(gs)
        assert ctx["suppression_actions"] == ["press suppression", "judicial capture"]

    def test_2_2_suppression_actions_empty_when_clean(self):
        gs = make_test_game_state(
            press_suppression_active=False,
            judicial_capture_active=False,
            opposition_dissolved=False,
            journalists_liquidated=False,
        )
        ctx = compute_biography_context(gs)
        assert ctx["suppression_actions"] == []

    def test_2_3_skim_profile_clean(self):
        gs = make_test_game_state(skim_rate=0.02)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "clean"

    def test_2_4_skim_profile_moderate(self):
        gs = make_test_game_state(skim_rate=0.07)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "moderate"

    def test_2_5_skim_profile_heavy(self):
        gs = make_test_game_state(skim_rate=0.15)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "heavy"

    def test_2_6_skim_profile_kleptocratic(self):
        gs = make_test_game_state(skim_rate=0.25)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "kleptocratic"

    def test_2_7_skim_profile_boundary_010_is_moderate(self):
        gs = make_test_game_state(skim_rate=0.10)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "moderate"

    def test_2_8_skim_profile_boundary_020_is_heavy(self):
        gs = make_test_game_state(skim_rate=0.20)
        ctx = compute_biography_context(gs)
        assert ctx["skim_profile"] == "heavy"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: compute_biography_context — economy fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestEconomyFields:
    def test_3_1_gdp_trajectory_grew(self):
        gs = make_test_game_state(gdp_start=75.0, gdp=85.0)
        ctx = compute_biography_context(gs)
        assert ctx["gdp_trajectory"] == "grew"

    def test_3_2_gdp_trajectory_declined(self):
        gs = make_test_game_state(gdp_start=75.0, gdp=65.0)
        ctx = compute_biography_context(gs)
        assert ctx["gdp_trajectory"] == "declined"

    def test_3_3_gdp_trajectory_stable(self):
        gs = make_test_game_state(gdp_start=75.0, gdp=76.0)
        ctx = compute_biography_context(gs)
        assert ctx["gdp_trajectory"] == "stable"

    def test_3_4_gdp_trajectory_volatile(self):
        gs = make_test_game_state(gdp_start=75.0, gdp=79.0)
        ctx = compute_biography_context(gs)
        assert ctx["gdp_trajectory"] == "volatile"

    def test_3_5_debt_crisis_true_when_exile_was_debt(self):
        gs = make_test_game_state(exile_trigger="debt")
        ctx = compute_biography_context(gs)
        assert ctx["debt_crisis_occurred"] is True

    def test_3_6_debt_crisis_false_for_other_collapse(self):
        gs = make_test_game_state(exile_trigger="coup")
        ctx = compute_biography_context(gs)
        assert ctx["debt_crisis_occurred"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 4: reputation axis scores
# ═══════════════════════════════════════════════════════════════════════════════

class TestReputationAxes:
    def test_4_1_statesman_score_high_for_clean_leader(self):
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "honored"}, {"status": "honored"}, {"status": "honored"}
            ],
            public_approval=75,
            skim_rate=0.01,
            gdp_start=60.0,
            gdp=85.0,
            education_level=2,
        )
        ctx = compute_biography_context(gs)
        assert ctx["statesman_score"] >= 70

    def test_4_2_statesman_score_low_for_kleptocrat(self):
        gs = make_test_game_state(
            promise_tracker=[{"status": "broken"}, {"status": "broken"}],
            public_approval=15,
            skim_rate=0.30,
            gdp_start=80.0,
            gdp=60.0,
            education_level=0,
        )
        ctx = compute_biography_context(gs)
        assert ctx["statesman_score"] <= 25

    def test_4_3_statesman_score_never_exceeds_100(self):
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "honored"}, {"status": "honored"},
                {"status": "honored"}, {"status": "honored"}, {"status": "honored"}
            ],
            public_approval=100,
            skim_rate=0.0,
            gdp_start=50.0,
            gdp=200.0,
            education_level=4,
        )
        ctx = compute_biography_context(gs)
        assert ctx["statesman_score"] <= 100

    def test_4_4_statesman_score_never_below_0(self):
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "broken"}, {"status": "broken"},
                {"status": "broken"}, {"status": "broken"}, {"status": "broken"}
            ],
            public_approval=0,
            skim_rate=0.50,
            gdp_start=100.0,
            gdp=30.0,
            education_level=0,
        )
        ctx = compute_biography_context(gs)
        assert ctx["statesman_score"] >= 0

    def test_4_5_reformer_score_high_for_clean_democratic(self):
        gs = make_test_game_state(
            elections_held=3,
            elections_stolen=0,
            education_level=3,
            press_suppression_active=False,
            judicial_capture_active=False,
            opposition_dissolved=False,
            journalists_liquidated=False,
            promise_tracker=[{"status": "honored"}, {"status": "honored"}],
        )
        ctx = compute_biography_context(gs)
        assert ctx["reformer_score"] >= 75

    def test_4_6_reformer_score_low_for_authoritarian(self):
        gs = make_test_game_state(
            elections_held=2,
            elections_stolen=2,
            education_level=0,
            press_suppression_active=True,
            judicial_capture_active=True,
            opposition_dissolved=True,
            journalists_liquidated=True,
        )
        ctx = compute_biography_context(gs)
        assert ctx["reformer_score"] <= 15

    def test_4_7_western_score_high_for_western_aligned(self):
        gs = make_test_game_state(
            relationships={
                "usa": 80, "eu": 85, "russia": 20,
                "china": 25, "arabia": 45, "dprg": 30
            },
            deals_made=[
                {"npc_id": "usa"}, {"npc_id": "eu"}, {"npc_id": "usa"}
            ],
        )
        ctx = compute_biography_context(gs)
        assert ctx["western_score"] >= 65

    def test_4_8_eastern_score_high_for_eastern_aligned(self):
        gs = make_test_game_state(
            relationships={
                "usa": 20, "eu": 25, "russia": 80,
                "china": 75, "arabia": 45, "dprg": 50
            },
            deals_made=[
                {"npc_id": "russia"}, {"npc_id": "china"}, {"npc_id": "russia"}
            ],
            npc_assistance_tiers={"russia": 3, "china": 2},
        )
        ctx = compute_biography_context(gs)
        assert ctx["eastern_score"] >= 65

    def test_4_9_both_scores_can_be_high(self):
        gs = make_test_game_state(
            relationships={
                "usa": 70, "eu": 65, "russia": 75,
                "china": 70, "arabia": 60, "dprg": 50
            },
            deals_made=[
                {"npc_id": "usa"}, {"npc_id": "russia"},
                {"npc_id": "eu"}, {"npc_id": "china"}
            ],
        )
        ctx = compute_biography_context(gs)
        assert ctx["western_score"] >= 50
        assert ctx["eastern_score"] >= 50

    def test_4_10_alignment_label_statesman(self):
        """Statesman requires statesman_score to be dominant (top by >= 15)."""
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "honored"}, {"status": "honored"}, {"status": "honored"}
            ],
            public_approval=80,
            skim_rate=0.01,
            gdp_start=60.0,
            gdp=100.0,
            education_level=3,
            # Lower reformer via rigged elections + suppression
            elections_held=1,
            elections_stolen=1,
            press_suppression_active=True,
            judicial_capture_active=True,
        )
        ctx = compute_biography_context(gs)
        assert ctx["alignment_label"] == "Statesman"

    def test_4_11_alignment_label_pragmatist(self):
        """Pragmatist when top two scores are within 15 of each other."""
        gs = make_test_game_state(
            promise_tracker=[{"status": "honored"}, {"status": "broken"}],
            public_approval=50,
            skim_rate=0.07,
            gdp_start=75.0,
            gdp=77.0,
            education_level=1,
            elections_held=0,
            elections_stolen=0,
            press_suppression_active=True,
        )
        ctx = compute_biography_context(gs)
        assert ctx["alignment_label"] == "Pragmatist"

    def test_4_12_alignment_label_kleptocrat(self):
        """Kleptocrat when skim dominates (100 - statesman is very high)."""
        gs = make_test_game_state(
            skim_rate=0.30,
            promise_tracker=[
                {"status": "broken"}, {"status": "broken"}, {"status": "broken"}
            ],
            public_approval=10,
            gdp_start=80.0,
            gdp=60.0,
        )
        ctx = compute_biography_context(gs)
        assert ctx["alignment_label"] == "Kleptocrat"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 5: determine_biography_sections
# ═══════════════════════════════════════════════════════════════════════════════

class TestBiographySections:
    def test_5_1_no_exile_clean_ending(self):
        ctx = {"exile_occurred": False, "ending_type": "democratic_transition", "return_succeeded": False}
        assert determine_biography_sections(ctx) == ["rise", "consolidation", "legacy"]

    def test_5_2_no_exile_bad_ending(self):
        ctx = {"exile_occurred": False, "ending_type": "state_capture", "return_succeeded": False}
        assert determine_biography_sections(ctx) == ["rise", "fall", "legacy"]

    def test_5_3_no_exile_voted_out(self):
        ctx = {"exile_occurred": False, "ending_type": "voted_out", "return_succeeded": False}
        assert determine_biography_sections(ctx) == ["rise", "exit", "legacy"]

    def test_5_4_exile_return_clean_ending(self):
        ctx = {"exile_occurred": True, "ending_type": "restoration_legacy", "return_succeeded": True}
        assert determine_biography_sections(ctx) == [
            "rise", "consolidation", "exile", "restoration", "legacy"
        ]

    def test_5_5_exile_return_bad_ending(self):
        ctx = {"exile_occurred": True, "ending_type": "state_capture", "return_succeeded": True}
        assert determine_biography_sections(ctx) == [
            "rise", "fall", "exile", "restoration", "legacy"
        ]

    def test_5_6_exile_no_return(self):
        ctx = {"exile_occurred": True, "ending_type": "permanent_exile", "return_succeeded": False}
        assert determine_biography_sections(ctx) == [
            "rise", "fall", "exile", "legacy"
        ]

    def test_5_7_legacy_always_last(self):
        test_cases = [
            {"exile_occurred": False, "ending_type": "democratic_transition", "return_succeeded": False},
            {"exile_occurred": False, "ending_type": "state_capture", "return_succeeded": False},
            {"exile_occurred": False, "ending_type": "voted_out", "return_succeeded": False},
            {"exile_occurred": True, "ending_type": "restoration_legacy", "return_succeeded": True},
            {"exile_occurred": True, "ending_type": "state_capture", "return_succeeded": True},
            {"exile_occurred": True, "ending_type": "permanent_exile", "return_succeeded": False},
        ]
        for ctx in test_cases:
            sections = determine_biography_sections(ctx)
            assert sections[-1] == "legacy", f"legacy not last for {ctx}"

    def test_5_8_rise_always_first(self):
        test_cases = [
            {"exile_occurred": False, "ending_type": "democratic_transition", "return_succeeded": False},
            {"exile_occurred": False, "ending_type": "state_capture", "return_succeeded": False},
            {"exile_occurred": False, "ending_type": "voted_out", "return_succeeded": False},
            {"exile_occurred": True, "ending_type": "restoration_legacy", "return_succeeded": True},
            {"exile_occurred": True, "ending_type": "state_capture", "return_succeeded": True},
            {"exile_occurred": True, "ending_type": "permanent_exile", "return_succeeded": False},
        ]
        for ctx in test_cases:
            sections = determine_biography_sections(ctx)
            assert sections[0] == "rise", f"rise not first for {ctx}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 6: promises computation
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromises:
    def test_6_1_promises_honored_count(self):
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "honored"}, {"status": "honored"},
                {"status": "broken"}, {"status": "pending"}
            ]
        )
        ctx = compute_biography_context(gs)
        assert ctx["promises_honored"] == 2

    def test_6_2_promises_broken_count(self):
        gs = make_test_game_state(
            promise_tracker=[
                {"status": "honored"}, {"status": "honored"},
                {"status": "broken"}, {"status": "pending"}
            ]
        )
        ctx = compute_biography_context(gs)
        assert ctx["promises_broken"] == 1

    def test_6_3_empty_promise_tracker(self):
        gs = make_test_game_state(promise_tracker=[])
        ctx = compute_biography_context(gs)
        assert ctx["promises_honored"] == 0
        assert ctx["promises_broken"] == 0

    def test_6_4_missing_promise_tracker_no_exception(self):
        gs = make_test_game_state(_no_promises=True)
        ctx = compute_biography_context(gs)
        assert ctx["promises_honored"] == 0
        assert ctx["promises_broken"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 7: backer fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackerFields:
    def test_7_1_backer_npcs_populated(self):
        gs = make_test_game_state(
            npc_assistance_tiers={"usa": 2, "russia": 1}
        )
        ctx = compute_biography_context(gs)
        assert set(ctx["backer_npcs"]) == {"usa", "russia"}

    def test_7_2_backer_eastern_weight_affects_eastern_score(self):
        """Eastern score should be higher when eastern backers are present."""
        base_args = dict(
            relationships={
                "usa": 40, "eu": 40, "russia": 50,
                "china": 50, "arabia": 40, "dprg": 40
            },
            deals_made=[],
        )

        gs_no_backer = make_test_game_state(
            npc_assistance_tiers={}, **base_args
        )
        gs_with_backer = make_test_game_state(
            npc_assistance_tiers={"russia": 5, "china": 4}, **base_args
        )

        ctx_no = compute_biography_context(gs_no_backer)
        ctx_with = compute_biography_context(gs_with_backer)

        assert ctx_with["eastern_score"] > ctx_no["eastern_score"]

    def test_7_3_backer_eastern_weight_caps_at_30(self):
        """
        With 2 eastern backers (russia+china), raw weight = 2*20 = 40, capped to 30.
        Adding a 3rd non-eastern backer (dprg) doesn't change backer_eastern count.
        Score with 2 eastern backers should equal score with 2 eastern + 1 non-eastern.
        """
        base_args = dict(
            relationships={
                "usa": 40, "eu": 40, "russia": 50,
                "china": 50, "arabia": 40, "dprg": 40
            },
            deals_made=[],
        )

        gs_two = make_test_game_state(
            npc_assistance_tiers={"russia": 5, "china": 5}, **base_args
        )
        gs_three = make_test_game_state(
            npc_assistance_tiers={"russia": 5, "china": 5, "dprg": 5}, **base_args
        )

        ctx_two = compute_biography_context(gs_two)
        ctx_three = compute_biography_context(gs_three)

        # dprg not counted as eastern — scores should be identical
        assert ctx_two["eastern_score"] == ctx_three["eastern_score"]

        # Also verify cap is actually applied:
        # With 1 backer (weight=20) vs 2 backers (weight=30, not 40)
        gs_one = make_test_game_state(
            npc_assistance_tiers={"russia": 5}, **base_args
        )
        ctx_one = compute_biography_context(gs_one)

        # If uncapped, diff would be (40-20)*0.15 = 3.0 → int increase of ~3
        # With cap, diff is (30-20)*0.15 = 1.5 → int increase of ~1-2
        actual_diff = ctx_two["eastern_score"] - ctx_one["eastern_score"]
        assert actual_diff <= 2, f"Cap not applied: diff={actual_diff} (expected <=2 with cap)"
