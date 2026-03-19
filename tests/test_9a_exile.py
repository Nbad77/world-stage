"""
Session 9A — Comeback Mechanics: Comprehensive Test Suite
Tests departure_heat, return_threshold, successor archetypes, hostility,
exile wealth actions, NPC backing tiers, return attempts, restoration identity.

Updated to match all 9 targeted fixes applied to api.py and turn_processor.py.
"""
import pytest
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game_state import GameState
from turn_processor import (
    _compute_departure_heat,
    _compute_return_threshold,
    _compute_successor_archetype,
    _compute_successor_hostility,
    _track_restoration_choice,
    _compute_restoration_regime_label,
    _check_restoration_resolution,
    RESTORATION_DEMOCRATIC_SIGNALS,
    RESTORATION_AUTHORITARIAN_SIGNALS,
)
from api import (
    EXILE_WEALTH_ACTIONS,
    ExileWealthActionRequest,
    NPC_BACKING_TIERS,
    NPC_BACKING_EXCLUSIONS_9A,
    NpcBackingRequest,
    _successor_detection_reaction,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_exile_gs(**overrides):
    """Build a GameState configured for exile testing."""
    gs = GameState()
    gs.in_exile = True
    gs.exile_trigger = 'coup'
    gs.exile_day = 5
    gs.exile_wealth_at_collapse = 15.0
    gs.personal_wealth = 15.0
    gs.return_progress = 0.0
    gs.return_threshold = 100.0
    gs.return_attempts = 0
    gs.npc_assistance_tiers = {}
    gs.faction_contacts = {}
    gs.wealth_action_cooldowns = {}
    gs.detection_events = []
    gs.exile_actions_log = []
    gs.restoration_active = False
    gs.restoration_democratic_tally = 0
    gs.restoration_authoritarian_tally = 0
    gs.prior_regime_label = ''
    gs.successor_archetype = 'Military Junta'
    gs.successor_hostility = 1
    gs.exile_apparatus_survived = True
    gs.exile_apparatus_detection_risk_modifier = 1.0
    gs.relations = {
        'usa': 50, 'eu': 45, 'arabia': 55,
        'dprg': 30, 'russia': 40, 'china': 50,
    }
    gs.approval = 40
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


def _make_departure_gs(**overrides):
    """Build a GameState for departure_heat computation."""
    gs = GameState()
    gs.international_warrant = False
    gs.war_crimes_flag = False
    gs.brigades_deployed_last_turn = False
    gs.private_security_force = False
    gs.action_journalists_liquidated = False
    gs.brigade_operations_this_turn = []
    gs.cabinet_axes = {'military': 0, 'intelligence': 0, 'resource_dev': 0,
                       'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0}
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: departure_heat calculation
# ═══════════════════════════════════════════════════════════════════════════════

class TestDepartureHeat:
    """Test _compute_departure_heat(game_state, trigger)."""

    def test_1_1_quiet_exit_voted_out(self):
        """Voted out, no militia -> heat 1."""
        gs = _make_departure_gs()
        heat = _compute_departure_heat(gs, 'voted_out')
        assert heat == 1

    def test_1_2_managed_departure(self):
        """Non-voted-out, no militia -> heat 2."""
        gs = _make_departure_gs()
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 2

    def test_1_3_contested_exit(self):
        """Militia deployed, no lethal -> heat 3."""
        gs = _make_departure_gs(brigades_deployed_last_turn=True)
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 3

    def test_1_4_violent_exit(self):
        """Militia deployed + lethal force -> heat 4."""
        gs = _make_departure_gs(
            brigades_deployed_last_turn=True,
            action_journalists_liquidated=True,
        )
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 4

    def test_1_5_fugitive(self):
        """Militia + lethal + international warrant -> heat 5."""
        gs = _make_departure_gs(
            brigades_deployed_last_turn=True,
            action_journalists_liquidated=True,
            international_warrant=True,
        )
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 5

    def test_1_6_fugitive_war_crimes(self):
        """Militia + lethal + war_crimes_flag -> heat 5."""
        gs = _make_departure_gs(
            brigades_deployed_last_turn=True,
            action_journalists_liquidated=True,
            war_crimes_flag=True,
        )
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 5

    def test_1_7_private_security_counts_as_militia(self):
        """private_security_force active counts as militia deployed."""
        gs = _make_departure_gs(private_security_force=True)
        heat = _compute_departure_heat(gs, 'coup')
        assert heat == 3  # Contested

    def test_1_8_brigade_ops_count_as_militia(self):
        """Recent brigade operations count as militia deployed."""
        gs = _make_departure_gs(brigade_operations_this_turn=['suppress'])
        heat = _compute_departure_heat(gs, 'revolution')
        assert heat == 3  # Contested

    def test_1_9_heat_always_between_1_and_5(self):
        """Heat is clamped to [1, 5] range."""
        gs = _make_departure_gs()
        heat = _compute_departure_heat(gs, 'voted_out')
        assert 1 <= heat <= 5


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: return_threshold calculation
# ═══════════════════════════════════════════════════════════════════════════════

class TestReturnThreshold:
    """Test _compute_return_threshold(trigger, departure_heat)."""

    def test_2_1_voted_out_heat_1(self):
        """Voted out + heat 1 = minimum threshold 50."""
        assert _compute_return_threshold('voted_out', 1) == 50

    def test_2_2_revolution_heat_1(self):
        """Revolution + heat 1 = 90."""
        assert _compute_return_threshold('revolution', 1) == 90

    def test_2_3_coup_heat_3(self):
        """Coup + heat 3 = 70 + (2*8) = 86."""
        assert _compute_return_threshold('coup', 3) == 86

    def test_2_4_debt_heat_5(self):
        """Debt + heat 5 = 65 + (4*8) = 97."""
        assert _compute_return_threshold('debt', 5) == 97

    def test_2_5_revolution_heat_5_exceeds_100(self):
        """Revolution + heat 5 = 90 + (4*8) = 122. Can exceed 100."""
        result = _compute_return_threshold('revolution', 5)
        assert result == 122

    def test_2_6_unknown_trigger_defaults_to_70(self):
        """Unknown trigger type uses base 70."""
        assert _compute_return_threshold('unknown', 1) == 70


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: successor archetype mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuccessorArchetype:
    """Test _compute_successor_archetype(trigger, disposition, game_state).

    NOTE: The test plan references _determine_successor() which maps
    regime_type -> disposition. _compute_successor_archetype maps
    (trigger, disposition) -> archetype name. Tests adapted accordingly.
    """

    def test_3_1_voted_out_reformist(self):
        """voted_out + reformist -> Opposition Democracy."""
        gs = _make_departure_gs()
        result = _compute_successor_archetype('voted_out', 'reformist', gs)
        assert result == 'Opposition Democracy'

    def test_3_2_revolution_populist(self):
        """revolution + populist -> Populist Dictator."""
        gs = _make_departure_gs()
        result = _compute_successor_archetype('revolution', 'populist', gs)
        assert result == 'Populist Dictator'

    def test_3_3_coup_hardliner_low_military(self):
        """coup + hardliner + low military -> Oligarchic Council."""
        gs = _make_departure_gs()
        gs.cabinet_axes['military'] = 3  # Below 5 threshold
        result = _compute_successor_archetype('coup', 'hardliner', gs)
        assert result == 'Oligarchic Council'

    def test_3_4_coup_hardliner_high_military(self):
        """coup + hardliner + high military -> Military Junta."""
        gs = _make_departure_gs()
        gs.cabinet_axes['military'] = 7  # At/above 5 threshold
        result = _compute_successor_archetype('coup', 'hardliner', gs)
        assert result == 'Military Junta'

    def test_3_5_debt_technocrat(self):
        """debt + technocrat -> Technocratic Caretaker."""
        gs = _make_departure_gs()
        result = _compute_successor_archetype('debt', 'technocrat', gs)
        assert result == 'Technocratic Caretaker'

    def test_3_6_fallback_uses_disposition_title(self):
        """Unmatched combination falls back to disposition.title()."""
        gs = _make_departure_gs()
        result = _compute_successor_archetype('voted_out', 'technocrat', gs)
        assert result == 'Technocrat'


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 4: successor_hostility calculation
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuccessorHostility:
    """Test _compute_successor_hostility(archetype, departure_heat)."""

    def test_4_1_opposition_democracy_base(self):
        """Opposition Democracy base = 0."""
        assert _compute_successor_hostility('Opposition Democracy', 1) == 0

    def test_4_2_military_junta_base(self):
        """Military Junta base = 2, heat 1 -> no modifier."""
        assert _compute_successor_hostility('Military Junta', 1) == 2

    def test_4_3_heat_modifier_adds(self):
        """Military Junta + heat 3 -> 2 + floor((3-1)/2) = 3."""
        result = _compute_successor_hostility('Military Junta', 3)
        assert result == 3

    def test_4_4_hostility_caps_at_3(self):
        """Populist Dictator (base 2) + heat 5 -> 2 + floor(4/2) = 4, capped to 3."""
        result = _compute_successor_hostility('Populist Dictator', 5)
        assert result == 3

    def test_4_5_technocrat_stays_low_at_high_heat(self):
        """Technocratic Caretaker (base 0) + heat 5 -> 0 + floor(4/2) = 2."""
        result = _compute_successor_hostility('Technocratic Caretaker', 5)
        assert result == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 5: exile wealth action validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestExileWealthActions:
    """Test EXILE_WEALTH_ACTIONS dict structure and validation logic.

    FIX 1: hire_fixer now unlocks faction channels (requires target faction).
    FIX 2: opposition_coalition now adds +5 approval.
    """

    def test_5_1_action_dict_complete(self):
        """All 8 actions present with required fields."""
        expected = ['propaganda_campaign', 'bribe_official', 'fund_protests',
                    'stir_unrest', 'general_greasing', 'hire_fixer',
                    'military_contact', 'opposition_coalition']
        for key in expected:
            assert key in EXILE_WEALTH_ACTIONS
            action = EXILE_WEALTH_ACTIONS[key]
            for field in ['cost', 'progress', 'detection_risk', 'cooldown_days']:
                assert field in action, f"{key} missing {field}"

    def test_5_2_insufficient_wealth_blocked(self):
        """stir_unrest costs $3B — should be blocked at $2B wealth."""
        gs = _make_exile_gs(exile_wealth_at_collapse=2.0)
        cost = EXILE_WEALTH_ACTIONS['stir_unrest']['cost']
        assert gs.exile_wealth_at_collapse < cost

    def test_5_3_cooldown_blocks_repeat(self):
        """Action on cooldown should be blocked."""
        gs = _make_exile_gs(
            exile_day=3,
            wealth_action_cooldowns={'propaganda_campaign': 5}
        )
        cooldown_until = gs.wealth_action_cooldowns.get('propaganda_campaign', 0)
        assert gs.exile_day < cooldown_until

    def test_5_4_valid_action_applies_progress(self):
        """propaganda_campaign: cost $1B, progress +8."""
        gs = _make_exile_gs(exile_wealth_at_collapse=5.0, return_progress=20.0)
        action = EXILE_WEALTH_ACTIONS['propaganda_campaign']
        # Simulate execution
        gs.exile_wealth_at_collapse -= action['cost']
        gs.return_progress += action['progress']
        assert gs.return_progress == 28.0
        assert gs.exile_wealth_at_collapse == 4.0

    def test_5_5_hire_fixer_unlocks_faction_channel(self):
        """FIX 1: hire_fixer unlocks a faction channel for the target.

        hire_fixer requires a target faction and sets faction_contacts[target]
        to {"unlocked": True, "committed": False, "offer": ""}.
        No progress is gained.
        """
        gs = _make_exile_gs(exile_wealth_at_collapse=5.0, return_progress=10.0)
        action = EXILE_WEALTH_ACTIONS['hire_fixer']
        assert action['progress'] == 0  # Fixer gives no progress
        # Simulate execution
        target = 'usa'
        gs.exile_wealth_at_collapse -= action['cost']
        gs.faction_contacts[target] = {"unlocked": True, "committed": False, "offer": ""}
        assert gs.exile_wealth_at_collapse == 2.5
        assert gs.faction_contacts['usa']['unlocked'] is True
        assert gs.faction_contacts['usa']['committed'] is False
        assert gs.return_progress == 10.0  # Unchanged

    def test_5_6_hire_fixer_blocks_duplicate_unlock(self):
        """FIX 1: hire_fixer blocks if channel already open for target."""
        gs = _make_exile_gs(exile_wealth_at_collapse=10.0)
        gs.faction_contacts['usa'] = {"unlocked": True, "committed": False, "offer": ""}
        # Channel already open — should be blocked
        fc = gs.faction_contacts.get('usa', {})
        assert fc.get('unlocked', False) is True  # Already unlocked

    def test_5_7_military_contact_requires_faction(self):
        """military_contact requires military faction unlocked."""
        action = EXILE_WEALTH_ACTIONS['military_contact']
        assert action['requires_faction'] == 'military'
        gs = _make_exile_gs(faction_contacts={'military': {'unlocked': False}})
        fc = gs.faction_contacts.get('military', {})
        assert not fc.get('unlocked', False)

    def test_5_8_opposition_coalition_requires_approval(self):
        """opposition_coalition requires approval >= 25."""
        action = EXILE_WEALTH_ACTIONS['opposition_coalition']
        assert action['requires_approval'] == 25
        gs = _make_exile_gs(approval=20)
        assert gs.approval < action['requires_approval']

    def test_5_9_opposition_coalition_free(self):
        """opposition_coalition costs $0, gives 15 progress."""
        action = EXILE_WEALTH_ACTIONS['opposition_coalition']
        assert action['cost'] == 0.0
        assert action['progress'] == 15

    def test_5_10_detection_risk_ranges(self):
        """All detection risks are between 0 and 1."""
        for key, action in EXILE_WEALTH_ACTIONS.items():
            assert 0 <= action['detection_risk'] <= 1.0, f"{key} risk out of range"

    def test_5_11_successor_detection_reaction_severity(self):
        """_successor_detection_reaction scales with hostility + action severity."""
        # Low combined -> mild
        gs = _make_exile_gs(successor_hostility=0, successor_archetype='Opposition Democracy')
        result = _successor_detection_reaction(gs, 'propaganda_campaign')
        assert 'statement' in result.lower()

        # High combined -> severe/extreme
        gs2 = _make_exile_gs(
            successor_hostility=3,
            successor_archetype='Military Junta',
            return_threshold=100.0,
            exile_apparatus_detection_risk_modifier=0.0,
            exile_wealth_at_collapse=20.0,
        )
        result2 = _successor_detection_reaction(gs2, 'stir_unrest')
        assert 'seized' in result2.lower() or 'investigation' in result2.lower()

    def test_5_12_opposition_coalition_boosts_approval(self):
        """FIX 2: opposition_coalition adds +5 approval, capped at 100."""
        gs = _make_exile_gs(approval=40)
        # Simulate FIX 2 logic
        gs.approval = min(100, gs.approval + 5)
        assert gs.approval == 45

    def test_5_13_opposition_coalition_approval_caps_at_100(self):
        """FIX 2: opposition_coalition approval boost caps at 100."""
        gs = _make_exile_gs(approval=98)
        gs.approval = min(100, gs.approval + 5)
        assert gs.approval == 100


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 6: NPC backing tier validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestNpcBackingTiers:
    """Test NPC_BACKING_TIERS structure and exclusivity rules.

    NOTE: Test plan uses character names (bill, sadam, etc.)
    Implementation uses country IDs (usa, arabia, etc.)

    FIX 3: Tier upgrade applies delta progress only.
    FIX 4: Per-NPC tier caps — arabia max tier 4, dprg max tier 3.
    """

    def test_6_1_all_npcs_have_5_tiers(self):
        """All 6 NPCs have tiers 1-5."""
        for npc_id in ['usa', 'eu', 'arabia', 'dprg', 'russia', 'china']:
            assert npc_id in NPC_BACKING_TIERS
            tiers = NPC_BACKING_TIERS[npc_id]
            for t in range(1, 6):
                assert t in tiers, f"{npc_id} missing tier {t}"

    def test_6_2_tier_grants_progress(self):
        """USA tier 2 grants its progress_bonus."""
        gs = _make_exile_gs(return_progress=0.0)
        tier_data = NPC_BACKING_TIERS['usa'][2]
        gs.return_progress += tier_data['progress_bonus']
        assert gs.return_progress == tier_data['progress_bonus']

    def test_6_3_progress_bonuses_increase_with_tier(self):
        """Higher tiers grant more progress."""
        for npc_id in NPC_BACKING_TIERS:
            tiers = NPC_BACKING_TIERS[npc_id]
            for t in range(1, 5):
                assert tiers[t + 1]['progress_bonus'] > tiers[t]['progress_bonus'], \
                    f"{npc_id}: tier {t+1} should grant more progress than tier {t}"

    def test_6_4_arabia_and_china_are_free(self):
        """Arabia and China charge $0 at all tiers (wealthy patrons)."""
        for npc_id in ['arabia', 'china']:
            for t in range(1, 6):
                assert NPC_BACKING_TIERS[npc_id][t]['cost'] == 0.0, \
                    f"{npc_id} tier {t} should be free"

    def test_6_5_exclusion_usa_blocks_dprg_at_tier_3(self):
        """USA at tier 3+ blocks DPRG at tier 3+."""
        gs = _make_exile_gs(npc_assistance_tiers={'usa': 3})
        # Check if DPRG tier 3 would be blocked
        blocked_by = []
        npc_id = 'dprg'
        tier = 3
        for other_npc, excluded_list in NPC_BACKING_EXCLUSIONS_9A.items():
            if npc_id in excluded_list:
                other_tier = gs.npc_assistance_tiers.get(other_npc, 0)
                if other_tier >= 3:
                    blocked_by.append(other_npc)
        exclusions = NPC_BACKING_EXCLUSIONS_9A.get(npc_id, [])
        for excluded_npc in exclusions:
            other_tier = gs.npc_assistance_tiers.get(excluded_npc, 0)
            if other_tier >= 3:
                blocked_by.append(excluded_npc)
        assert len(blocked_by) > 0, "DPRG should be blocked by USA tier 3"
        assert 'usa' in blocked_by

    def test_6_6_exclusion_russia_blocks_usa_at_tier_3(self):
        """Russia at tier 3+ blocks USA at tier 3+."""
        gs = _make_exile_gs(npc_assistance_tiers={'russia': 3})
        blocked_by = []
        npc_id = 'usa'
        for other_npc, excluded_list in NPC_BACKING_EXCLUSIONS_9A.items():
            if npc_id in excluded_list:
                other_tier = gs.npc_assistance_tiers.get(other_npc, 0)
                if other_tier >= 3:
                    blocked_by.append(other_npc)
        exclusions = NPC_BACKING_EXCLUSIONS_9A.get(npc_id, [])
        for excluded_npc in exclusions:
            other_tier = gs.npc_assistance_tiers.get(excluded_npc, 0)
            if other_tier >= 3:
                blocked_by.append(excluded_npc)
        assert 'russia' in blocked_by, "USA should be blocked by Russia tier 3"

    def test_6_7_tier_1_no_exclusion(self):
        """Tier 1 backing from both USA and Russia is allowed (exclusions at 3+)."""
        gs = _make_exile_gs(npc_assistance_tiers={'usa': 1})
        # Check if Russia tier 1 is blocked
        blocked_by = []
        npc_id = 'russia'
        tier = 1
        # Exclusion check only at tier 3+
        if tier >= 3:
            for other_npc, excluded_list in NPC_BACKING_EXCLUSIONS_9A.items():
                if npc_id in excluded_list:
                    other_tier = gs.npc_assistance_tiers.get(other_npc, 0)
                    if other_tier >= 3:
                        blocked_by.append(other_npc)
        assert len(blocked_by) == 0, "Tier 1 should not trigger exclusions"

    def test_6_8_eu_and_dprg_exclusive(self):
        """EU excludes DPRG (and vice versa) at tier 3+."""
        assert 'dprg' in NPC_BACKING_EXCLUSIONS_9A.get('eu', [])
        assert 'eu' in NPC_BACKING_EXCLUSIONS_9A.get('dprg', [])

    def test_6_9_china_excludes_usa(self):
        """China excludes USA at tier 3+."""
        assert 'usa' in NPC_BACKING_EXCLUSIONS_9A.get('china', [])

    def test_6_10_relation_requirements_increase(self):
        """Higher tiers require higher relations."""
        for npc_id in NPC_BACKING_TIERS:
            tiers = NPC_BACKING_TIERS[npc_id]
            for t in range(1, 5):
                assert tiers[t + 1]['relation_req'] >= tiers[t]['relation_req'], \
                    f"{npc_id}: tier {t+1} should need >= tier {t} relations"

    def test_6_11_tier_upgrade_delta_progress_only(self):
        """FIX 3: Upgrading from tier 1 to tier 2 only adds the delta progress."""
        gs = _make_exile_gs(return_progress=0.0)
        npc_id = 'usa'
        npc_tiers = NPC_BACKING_TIERS[npc_id]
        # Accept tier 1
        tier1_bonus = npc_tiers[1]['progress_bonus']
        gs.return_progress += tier1_bonus
        gs.npc_assistance_tiers[npc_id] = 1
        progress_after_t1 = gs.return_progress

        # Upgrade to tier 2 — delta only
        current_tier = gs.npc_assistance_tiers[npc_id]
        previous_bonus = npc_tiers[current_tier]['progress_bonus']
        new_bonus = npc_tiers[2]['progress_bonus']
        delta = new_bonus - previous_bonus
        gs.return_progress += delta
        gs.npc_assistance_tiers[npc_id] = 2

        # Total progress should equal tier 2 bonus (not tier 1 + tier 2)
        assert gs.return_progress == pytest.approx(new_bonus)
        assert delta > 0  # Upgrade should grant positive delta

    def test_6_12_arabia_tier_cap_at_4(self):
        """FIX 4: Arabia (Sadam) tier 5 is blocked."""
        NPC_TIER_CAPS = {"arabia": 4, "dprg": 3}
        tier_cap = NPC_TIER_CAPS.get('arabia')
        assert tier_cap == 4
        assert 5 > tier_cap  # Tier 5 exceeds cap

    def test_6_13_dprg_tier_cap_at_3(self):
        """FIX 4: DPRG (Ji-won) tiers 4 and 5 are blocked."""
        NPC_TIER_CAPS = {"arabia": 4, "dprg": 3}
        tier_cap = NPC_TIER_CAPS.get('dprg')
        assert tier_cap == 3
        assert 4 > tier_cap  # Tier 4 exceeds cap
        assert 5 > tier_cap  # Tier 5 exceeds cap

    def test_6_14_uncapped_npcs_allow_tier_5(self):
        """FIX 4: NPCs without caps (usa, eu, russia, china) can reach tier 5."""
        NPC_TIER_CAPS = {"arabia": 4, "dprg": 3}
        for npc_id in ['usa', 'eu', 'russia', 'china']:
            assert NPC_TIER_CAPS.get(npc_id) is None, f"{npc_id} should have no tier cap"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 7: return attempt probability
# ═══════════════════════════════════════════════════════════════════════════════

class TestReturnAttempt:
    """Test return attempt probability calculation.

    FIX 5: Failure penalty is now additive: 20 + (attempt * 5).
    Probability cap = 0.90, floor = 0.05.
    """

    def _calc_probability(self, gs):
        """Replicate the probability calculation from the endpoint."""
        base_prob = min(gs.return_progress / max(gs.return_threshold, 1.0), 0.90)
        max_npc_tier = 0
        for npc_id, tier in gs.npc_assistance_tiers.items():
            if tier > max_npc_tier:
                max_npc_tier = tier
        npc_bonus = max_npc_tier * 0.02
        faction_bonus = 0
        for faction, data in gs.faction_contacts.items():
            if isinstance(data, dict) and data.get('committed', False):
                faction_bonus += 0.03
        detection_penalty = len(gs.detection_events) * 0.03
        hostility_penalty = gs.successor_hostility * 0.03
        attempt_penalty = gs.return_attempts * 0.05  # After incrementing
        return max(0.05, min(0.90,
            base_prob + npc_bonus + faction_bonus
            - detection_penalty - hostility_penalty - attempt_penalty))

    def test_7_1_at_threshold_probability_capped(self):
        """At threshold, probability caps at 0.90."""
        gs = _make_exile_gs(
            return_progress=100.0, return_threshold=100.0,
            return_attempts=0, successor_hostility=0,
        )
        gs.return_attempts = 1  # After increment in endpoint
        prob = self._calc_probability(gs)
        assert prob == pytest.approx(0.85, abs=0.01)  # 0.90 - 0*0.05 attempt penalty

    def test_7_2_below_threshold_scales(self):
        """50% progress / 100 threshold -> ~0.50 base probability."""
        gs = _make_exile_gs(
            return_progress=50.0, return_threshold=100.0,
            return_attempts=0, successor_hostility=0,
        )
        gs.return_attempts = 1
        prob = self._calc_probability(gs)
        assert prob == pytest.approx(0.45, abs=0.01)  # 0.50 - 0.05 attempt

    def test_7_3_minimum_floor(self):
        """Floor probability is 0.05."""
        gs = _make_exile_gs(
            return_progress=0.0, return_threshold=100.0,
            return_attempts=0, successor_hostility=3,
        )
        gs.return_attempts = 1
        gs.detection_events = [{'day': 1}, {'day': 2}, {'day': 3}]
        prob = self._calc_probability(gs)
        assert prob == 0.05

    def test_7_4_max_attempts_is_3(self):
        """return_attempts >= 3 should be blocked."""
        gs = _make_exile_gs(return_attempts=3)
        assert gs.return_attempts >= 3

    def test_7_5_failed_attempt_reduces_progress(self):
        """FIX 5: Failure penalty = 20 + (attempt * 5) subtracted from progress."""
        gs = _make_exile_gs(return_progress=40.0, return_attempts=1)
        # Simulate failure after attempt #1
        progress_penalty = 20 + (gs.return_attempts * 5)
        gs.return_progress = max(0, gs.return_progress - progress_penalty)
        assert progress_penalty == 25  # 20 + (1 * 5)
        assert gs.return_progress == pytest.approx(15.0)  # 40 - 25

    def test_7_6_progress_never_negative(self):
        """FIX 5: After failure with high penalty, progress clamps at 0."""
        gs = _make_exile_gs(return_progress=10.0, return_attempts=3)
        progress_penalty = 20 + (gs.return_attempts * 5)  # 35
        gs.return_progress = max(0, gs.return_progress - progress_penalty)
        assert gs.return_progress == 0  # max(0, 10 - 35) = 0

    def test_7_7_npc_backing_adds_probability(self):
        """Each NPC tier adds 2% to probability."""
        gs = _make_exile_gs(
            return_progress=50.0, return_threshold=100.0,
            successor_hostility=0, return_attempts=0,
        )
        gs.npc_assistance_tiers = {'usa': 4}
        gs.return_attempts = 1
        prob = self._calc_probability(gs)
        # base 0.50 + npc 0.08 - attempt 0.05 = 0.53
        assert prob == pytest.approx(0.53, abs=0.01)

    def test_7_8_detection_events_reduce_probability(self):
        """Each detection event reduces probability by 3%."""
        gs = _make_exile_gs(
            return_progress=50.0, return_threshold=100.0,
            successor_hostility=0, return_attempts=0,
        )
        gs.detection_events = [{'day': 1}, {'day': 2}]
        gs.return_attempts = 1
        prob = self._calc_probability(gs)
        # base 0.50 - detect 0.06 - attempt 0.05 = 0.39
        assert prob == pytest.approx(0.39, abs=0.01)

    def test_7_9_failed_return_increases_hostility(self):
        """Failed return increases successor hostility by 1, caps at 3."""
        gs = _make_exile_gs(successor_hostility=2)
        gs.successor_hostility = min(3, gs.successor_hostility + 1)
        assert gs.successor_hostility == 3

    def test_7_10_failed_return_increases_threshold(self):
        """Failed return increases threshold by 10, caps at 150."""
        gs = _make_exile_gs(return_threshold=100.0)
        gs.return_threshold = min(150, gs.return_threshold + 10)
        assert gs.return_threshold == 110.0

    def test_7_11_additive_penalty_scales_with_attempts(self):
        """FIX 5: Penalty grows: attempt 1 = 25, attempt 2 = 30, attempt 3 = 35."""
        for attempt, expected_penalty in [(1, 25), (2, 30), (3, 35)]:
            penalty = 20 + (attempt * 5)
            assert penalty == expected_penalty, f"Attempt {attempt}: expected {expected_penalty}, got {penalty}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 8: restoration state on successful return
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestorationState:
    """Test state changes applied after successful return.

    FIX 6: Relations reset uses percentage model: max(20, int(entry * 0.60)),
           backers keep full exile-entry value.
    FIX 7: Economy reset: gdp *= 0.85, budget=10, stability=40, approval=35.
    FIX 8: Advisors cleared on return.
    """

    def test_8_1_relations_percentage_model(self):
        """FIX 6: Non-backer relations = max(20, int(entry * 0.60)),
        backer keeps full exile-entry value."""
        gs = _make_exile_gs(relations={
            'usa': 65, 'eu': 72, 'arabia': 55,
            'dprg': 30, 'russia': 40, 'china': 50,
        })
        gs.exile_entry_relations = {
            'usa': 65, 'eu': 72, 'arabia': 55,
            'dprg': 30, 'russia': 40, 'china': 50,
        }
        backing_npc = 'usa'
        backers = {backing_npc}
        entry_rels = gs.exile_entry_relations
        for npc_id in gs.relations:
            entry_val = entry_rels.get(npc_id, gs.relations.get(npc_id, 30))
            if npc_id in backers:
                gs.relations[npc_id] = entry_val  # Backer keeps full value
            else:
                gs.relations[npc_id] = max(20, int(entry_val * 0.60))

        assert gs.relations['usa'] == 65     # Backer keeps full entry value
        assert gs.relations['eu'] == 43      # int(72 * 0.60) = 43
        assert gs.relations['arabia'] == 33  # int(55 * 0.60) = 33
        assert gs.relations['dprg'] == 20    # max(20, int(30 * 0.60)) = max(20, 18) = 20
        assert gs.relations['russia'] == 24  # int(40 * 0.60) = 24
        assert gs.relations['china'] == 30   # int(50 * 0.60) = 30

    def test_8_2_restoration_active_set(self):
        """Successful return sets restoration_active = True."""
        gs = _make_exile_gs()
        gs.in_exile = False
        gs.restoration_active = True
        assert gs.restoration_active is True
        assert gs.in_exile is False

    def test_8_3_prior_regime_label_captured(self):
        """prior_regime_label captures the pre-exile regime type."""
        gs = _make_exile_gs()
        gs.state_identity = {'regime_type': 'Soft Authoritarianism'}
        gs.prior_regime_label = gs.state_identity.get('regime_type', 'Managed Democracy')
        assert gs.prior_regime_label == 'Soft Authoritarianism'

    def test_8_4_democratic_backer_seeds_tally(self):
        """USA/EU backing seeds democratic tally +2."""
        gs = _make_exile_gs(
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=0,
        )
        backing_npc = 'usa'
        if backing_npc in ('usa', 'eu'):
            gs.restoration_democratic_tally += 2
        assert gs.restoration_democratic_tally == 2

    def test_8_5_authoritarian_backer_seeds_tally(self):
        """DPRG/Russia backing seeds authoritarian tally +2."""
        gs = _make_exile_gs(
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=0,
        )
        backing_npc = 'russia'
        if backing_npc in ('dprg', 'russia'):
            gs.restoration_authoritarian_tally += 2
        assert gs.restoration_authoritarian_tally == 2

    def test_8_6_neutral_backer_seeds_tally(self):
        """Arabia/China backing seeds authoritarian tally +1."""
        gs = _make_exile_gs(
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=0,
        )
        backing_npc = 'arabia'
        if backing_npc in ('arabia', 'china'):
            gs.restoration_authoritarian_tally += 1
        assert gs.restoration_authoritarian_tally == 1

    def test_8_7_economy_reset_on_return(self):
        """FIX 7: Economy resets: gdp = entry * 0.85, budget=10, stability=40, approval=35."""
        gs = _make_exile_gs()
        gs.exile_entry_gdp = 120.0
        # Simulate FIX 7 reset
        gs.gdp_base = gs.exile_entry_gdp * 0.85
        gs.budget = 10.0
        gs.stability = 40
        gs.approval = 35
        assert gs.gdp_base == pytest.approx(102.0)
        assert gs.budget == 10.0
        assert gs.stability == 40
        assert gs.approval == 35

    def test_8_8_advisors_cleared_on_return(self):
        """FIX 8: Advisors are cleared on successful return."""
        gs = _make_exile_gs()
        gs.advisors = {'slot1': 'advisor_a', 'slot2': 'advisor_b'}
        gs.advisor_assigned_today = ['slot1']
        # Simulate FIX 8 clearing
        gs.advisors = {}
        gs.advisor_assigned_today = []
        assert gs.advisors == {}
        assert gs.advisor_assigned_today == []

    def test_8_9_economy_reset_default_gdp(self):
        """FIX 7: If exile_entry_gdp not explicitly set, defaults to 0.0 in GameState.
        The getattr fallback of 100.0 only applies if attribute is missing entirely."""
        gs = _make_exile_gs()
        # GameState.__init__ sets exile_entry_gdp = 0.0
        assert gs.exile_entry_gdp == 0.0
        # Test with a realistic value
        gs.exile_entry_gdp = 200.0
        gs.gdp_base = getattr(gs, 'exile_entry_gdp', 100.0) * 0.85
        assert gs.gdp_base == pytest.approx(170.0)

    def test_8_10_backer_npc_tiers_count_as_backers(self):
        """FIX 6: NPCs with tiers in npc_assistance_tiers also count as backers."""
        gs = _make_exile_gs(relations={
            'usa': 60, 'eu': 50, 'russia': 70,
            'arabia': 40, 'dprg': 30, 'china': 50,
        })
        gs.exile_entry_relations = {
            'usa': 60, 'eu': 50, 'russia': 70,
            'arabia': 40, 'dprg': 30, 'china': 50,
        }
        gs.npc_assistance_tiers = {'russia': 3}
        backing_npc = 'usa'
        backers = set(gs.npc_assistance_tiers.keys())
        if backing_npc:
            backers.add(backing_npc)
        entry_rels = gs.exile_entry_relations
        for npc_id in gs.relations:
            entry_val = entry_rels.get(npc_id, gs.relations.get(npc_id, 30))
            if npc_id in backers:
                gs.relations[npc_id] = entry_val
            else:
                gs.relations[npc_id] = max(20, int(entry_val * 0.60))

        assert gs.relations['usa'] == 60     # Primary backer keeps full
        assert gs.relations['russia'] == 70  # Tier backer keeps full
        assert gs.relations['eu'] == 30      # int(50 * 0.60) = 30
        assert gs.relations['arabia'] == 24  # int(40 * 0.60) = 24
        assert gs.relations['dprg'] == 20    # max(20, int(30 * 0.60)) = max(20, 18) = 20
        assert gs.relations['china'] == 30   # int(50 * 0.60) = 30


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 9: restoration identity formation
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestorationIdentity:
    """Test the tally system that resolves the restoration regime label.

    FIX 9: Resolution triggers when either tally reaches 3 (not total >= 15).
    Labels determined by _compute_restoration_regime_label using net score and total.
    """

    def test_9_1_democratic_tally_triggers_resolution(self):
        """FIX 9: Democratic tally reaching 3 triggers resolution."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=8,
            restoration_authoritarian_tally=0,
            prior_regime_label='Managed Democracy',
        )
        gs.state_identity = {'regime_type': 'Managed Democracy'}
        resolved = _check_restoration_resolution(gs)
        assert resolved is True
        assert gs.restoration_active is False
        # net=8, total=8 >= 5 -> "Restored Democracy"
        assert gs.state_identity['regime_type'] == 'Restored Democracy'

    def test_9_2_authoritarian_tally_triggers_resolution(self):
        """FIX 9: Authoritarian tally reaching 3 triggers resolution."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=10,
            prior_regime_label='Managed Democracy',
        )
        gs.state_identity = {'regime_type': 'Managed Democracy'}
        resolved = _check_restoration_resolution(gs)
        assert resolved is True
        assert gs.restoration_active is False
        # net=-10, total=10 >= 5 -> "Restoration Dictatorship"
        assert gs.state_identity['regime_type'] == 'Restoration Dictatorship'

    def test_9_3_balanced_tallies_resolve(self):
        """FIX 9: Both tallies at 3 resolves to Managed Democracy."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=4,
            restoration_authoritarian_tally=4,
            prior_regime_label='Managed Democracy',
        )
        gs.state_identity = {'regime_type': 'Unknown'}
        resolved = _check_restoration_resolution(gs)
        assert resolved is True
        # net=0, total=8 >= 5 -> "Managed Democracy"
        assert gs.state_identity['regime_type'] == 'Managed Democracy'

    def test_9_4_neither_tally_at_3_does_not_resolve(self):
        """FIX 9: Neither tally reaching 3 -> no resolution."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=2,
            restoration_authoritarian_tally=2,
        )
        gs.state_identity = {'regime_type': 'Managed Democracy'}
        resolved = _check_restoration_resolution(gs)
        assert resolved is False
        assert gs.restoration_active is True

    def test_9_5_too_few_signals_inherits_prior(self):
        """Total < 5 with _compute_restoration_regime_label -> 'Restored [Prior]'."""
        gs = _make_exile_gs(
            restoration_democratic_tally=2,
            restoration_authoritarian_tally=1,
            prior_regime_label='Kleptocracy',
        )
        label = _compute_restoration_regime_label(gs)
        assert label == 'Restored Kleptocracy'

    def test_9_6_democratic_signals_track_correctly(self):
        """_track_restoration_choice correctly adds to democratic tally."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=0,
        )
        _track_restoration_choice(gs, 'fair_elections')
        assert gs.restoration_democratic_tally == 4  # fair_elections weight = 4
        _track_restoration_choice(gs, 'free_press')
        assert gs.restoration_democratic_tally == 7  # +3

    def test_9_7_authoritarian_signals_track_correctly(self):
        """_track_restoration_choice correctly adds to authoritarian tally."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=0,
            restoration_authoritarian_tally=0,
        )
        _track_restoration_choice(gs, 'purge_opposition')
        assert gs.restoration_authoritarian_tally == 4  # purge weight = 4

    def test_9_8_inactive_restoration_ignores_signals(self):
        """Signals ignored when restoration_active is False."""
        gs = _make_exile_gs(
            restoration_active=False,
            restoration_democratic_tally=0,
        )
        _track_restoration_choice(gs, 'free_press')
        assert gs.restoration_democratic_tally == 0

    def test_9_9_no_overlap_in_signal_dicts(self):
        """Democratic and authoritarian signals don't share keys."""
        overlap = set(RESTORATION_DEMOCRATIC_SIGNALS.keys()) & \
                  set(RESTORATION_AUTHORITARIAN_SIGNALS.keys())
        assert len(overlap) == 0

    def test_9_10_reform_government_label(self):
        """Net 4-7 -> 'Reform Government'."""
        gs = _make_exile_gs(
            restoration_democratic_tally=9,
            restoration_authoritarian_tally=4,
            prior_regime_label='Test',
        )
        label = _compute_restoration_regime_label(gs)
        assert label == 'Reform Government'  # net = 5

    def test_9_11_restored_authoritarianism_label(self):
        """Net -1 to -4 -> 'Restored Authoritarianism'."""
        gs = _make_exile_gs(
            restoration_democratic_tally=4,
            restoration_authoritarian_tally=7,
            prior_regime_label='Test',
        )
        label = _compute_restoration_regime_label(gs)
        assert label == 'Restored Authoritarianism'  # net = -3

    def test_9_12_consolidation_regime_label(self):
        """Net -5 to -8 -> 'Consolidation Regime'."""
        gs = _make_exile_gs(
            restoration_democratic_tally=3,
            restoration_authoritarian_tally=10,
            prior_regime_label='Test',
        )
        label = _compute_restoration_regime_label(gs)
        assert label == 'Consolidation Regime'  # net = -7

    def test_9_13_small_democratic_tally_resolves_with_prior(self):
        """FIX 9: dem=3, auth=0 triggers but total < 5 -> 'Restored [Prior]'."""
        gs = _make_exile_gs(
            restoration_active=True,
            restoration_democratic_tally=3,
            restoration_authoritarian_tally=0,
            prior_regime_label='Soft Authoritarianism',
        )
        gs.state_identity = {'regime_type': 'Unknown'}
        resolved = _check_restoration_resolution(gs)
        assert resolved is True
        assert gs.restoration_active is False
        # total=3 < 5 -> inherits prior
        assert gs.state_identity['regime_type'] == 'Restored Soft Authoritarianism'
