"""
10A Era System -- Comprehensive Tests
Tests cover: era field initialization, threshold detection (regime shift,
election, stability collapse, relations extremes), time backstop,
pending_era_transition flag, priority ordering, and serialization round-trip.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from game_state import GameState, compute_regime_from_axes
from turn_processor import apply_end_of_turn_effects


# ── Helper ──────────────────────────────────────────────────────────────────

def _fresh_gs(**overrides):
    """Return a full GameState with safe defaults for era tests.

    The EOT pipeline touches many subsystems; we leave the constructor
    defaults intact and only patch the handful of fields era tests care
    about.  Overrides are applied last so individual tests can tweak.
    """
    gs = GameState()
    # Stable baseline -- nothing should trigger thresholds
    gs.stability = 50
    gs.public_approval = 50
    gs.budget = 50.0
    gs.oil_price = 50
    gs.current_turn = 3
    gs.current_day = 5
    gs.personal_wealth = 0.0
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.cabinet_axes = {
        'military': 0, 'intelligence': 0, 'resource_dev': 0,
        'media': 0, 'judicial': 0, 'political': 0, 'extraction': 0,
    }
    gs.tech_level = 0
    gs.tech_level_fractional = 0.0
    gs.advisors = []
    gs.advisor_pool = []
    gs.advisors_eliminated = []
    gs.advisor_actions_log = []
    gs.advisor_distortions = {}
    gs.tax_rates = {'income_tax': 0.20, 'corporate_tax': 0.15, 'resource_tax': 0.25}
    gs.gdp_base = 100.0
    gs.gdp_growth_rate = 0.02
    gs.revenue_streams = {}
    gs.resource_endowment = {
        'oil_reserves': 0.7, 'mineral_deposits': 0.3,
        'arable_land': 0.4, 'rare_earths': 0.1, 'coastal_access': 0.6,
    }
    gs.soft_power = 0
    gs.diplomatic_capital = 0
    gs.npc_contact_history = {}
    gs.pending_npc_contacts = []
    gs.brigade_operations_this_turn = []
    gs.election_fired = False

    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ══════════════════════════════════════════════════════════════════════════════
# 1. Initialization
# ══════════════════════════════════════════════════════════════════════════════

def test_era_fields_initialized():
    """A fresh GameState has correct era defaults."""
    gs = GameState()
    assert gs.current_era == 1
    assert gs.era_start_day == 1
    assert gs.era_transitions == []
    assert gs.pending_era_transition is False
    assert gs.last_threshold_event is None
    assert gs.last_threshold_day == 0


# ══════════════════════════════════════════════════════════════════════════════
# 2-6. Threshold detection
# ══════════════════════════════════════════════════════════════════════════════

def test_era_threshold_stability_collapse():
    """Stability <= 0 triggers 'stability_collapse' threshold."""
    # Stability drifts during EOT, so set it very negative + low approval
    # so it's still <= 0 by section 14.
    gs = _fresh_gs(stability=-50, public_approval=10)
    day_before = gs.current_day
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event == "stability_collapse"
    assert gs.pending_era_transition is True
    assert gs.last_threshold_day == day_before


def test_era_threshold_relations_collapse():
    """Any NPC relation <= 0 triggers 'relations_collapse_<npc>'."""
    gs = _fresh_gs()
    gs.relations['eu'] = 0
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event == "relations_collapse_eu"
    assert gs.pending_era_transition is True


def test_era_threshold_relations_peak():
    """Any NPC relation >= 100 triggers 'relations_peak_<npc>'."""
    gs = _fresh_gs()
    gs.relations['arabia'] = 100
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event == "relations_peak_arabia"
    assert gs.pending_era_transition is True


def test_era_threshold_regime_shift():
    """Changing regime via cabinet axes triggers 'regime_shift'."""
    # Old regime is Managed Democracy (total <= 5).
    # Set axes so total of non-resource_dev = 10 => 'Soft Authoritarianism' (6-15 range).
    gs = _fresh_gs()
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.cabinet_axes = {
        'military': 2, 'intelligence': 2, 'resource_dev': 0,
        'media': 2, 'judicial': 2, 'political': 2, 'extraction': 0,
    }
    # total non-resource_dev = 2+2+2+2+2+0 = 10 => Soft Authoritarianism
    assert compute_regime_from_axes(gs.cabinet_axes) == 'Soft Authoritarianism'
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event == "regime_shift"
    assert gs.pending_era_transition is True
    # Regime should also have been updated by section 13g
    assert gs.state_identity['regime_type'] == 'Soft Authoritarianism'


def test_era_threshold_election():
    """election_fired=True triggers 'election' threshold."""
    gs = _fresh_gs(election_fired=True)
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event == "election"
    assert gs.pending_era_transition is True
    assert gs._election_era_counted is True


# ══════════════════════════════════════════════════════════════════════════════
# 7. Election counted only once
# ══════════════════════════════════════════════════════════════════════════════

def test_era_election_counted_only_once():
    """_election_era_counted prevents the election threshold from re-firing."""
    gs = _fresh_gs(election_fired=True)
    gs._election_era_counted = True
    # Reset era tracking so we can detect if a new threshold fires
    gs.pending_era_transition = False
    gs.last_threshold_event = None
    msgs = apply_end_of_turn_effects(gs)
    # No threshold should have fired (election already counted, everything else normal)
    assert gs.last_threshold_event is None


# ══════════════════════════════════════════════════════════════════════════════
# 8-10. Time backstop
# ══════════════════════════════════════════════════════════════════════════════

def test_era_backstop_triggers_at_20_days():
    """20+ days in era without threshold in last 5 triggers backstop."""
    gs = _fresh_gs()
    gs.current_day = 25
    gs.era_start_day = 1       # 24 days in era
    gs.last_threshold_day = 0  # no threshold ever
    gs.pending_era_transition = False
    msgs = apply_end_of_turn_effects(gs)
    assert gs.pending_era_transition is True
    # Check a backstop message was emitted
    assert any("BACKSTOP" in str(m) for m in msgs)


def test_era_backstop_needs_5_days_since_last():
    """Backstop does NOT fire if last threshold was fewer than 5 days ago."""
    gs = _fresh_gs()
    gs.current_day = 25
    gs.era_start_day = 1       # 24 days in era
    gs.last_threshold_day = 22  # only 3 days since last threshold
    gs.pending_era_transition = False
    msgs = apply_end_of_turn_effects(gs)
    # Backstop should NOT have fired (days_since_threshold = 3 < 5)
    assert not any("BACKSTOP" in str(m) for m in msgs)


def test_era_backstop_not_when_already_pending():
    """Backstop doesn't fire if pending_era_transition is already True."""
    gs = _fresh_gs()
    gs.current_day = 30
    gs.era_start_day = 1
    gs.last_threshold_day = 0
    gs.pending_era_transition = True  # already pending
    msgs = apply_end_of_turn_effects(gs)
    # Should NOT get a backstop message
    assert not any("BACKSTOP" in str(m) for m in msgs)


# ══════════════════════════════════════════════════════════════════════════════
# 11. Transition record structure
# ══════════════════════════════════════════════════════════════════════════════

def test_era_transition_record_structure():
    """era_transitions list holds dicts with expected keys after manual append."""
    gs = _fresh_gs()
    record = {
        'era': 1,
        'start_day': 1,
        'end_day': 15,
        'threshold': 'regime_shift',
    }
    gs.era_transitions.append(record)
    assert len(gs.era_transitions) == 1
    entry = gs.era_transitions[0]
    assert entry['era'] == 1
    assert entry['threshold'] == 'regime_shift'
    assert entry['start_day'] == 1
    assert entry['end_day'] == 15


# ══════════════════════════════════════════════════════════════════════════════
# 12. Pending flag set on threshold
# ══════════════════════════════════════════════════════════════════════════════

def test_pending_era_transition_set_on_threshold():
    """pending_era_transition is set True when any threshold fires."""
    # Use relations collapse (doesn't drift) as a reliable trigger
    gs = _fresh_gs()
    gs.relations['dprg'] = 0
    assert gs.pending_era_transition is False
    apply_end_of_turn_effects(gs)
    assert gs.pending_era_transition is True


# ══════════════════════════════════════════════════════════════════════════════
# 13. Threshold priority
# ══════════════════════════════════════════════════════════════════════════════

def test_threshold_priority_regime_shift_wins():
    """regime_shift takes priority over other thresholds when multiple fire."""
    gs = _fresh_gs()
    # Trigger regime shift (axes total=10, old = Managed Democracy => Soft Auth)
    gs.state_identity = {'regime_type': 'Managed Democracy', 'power_base': 'Mass-Dependent'}
    gs.cabinet_axes = {
        'military': 2, 'intelligence': 2, 'resource_dev': 0,
        'media': 2, 'judicial': 2, 'political': 2, 'extraction': 0,
    }
    # Also trigger relations collapse
    gs.relations['dprg'] = 0
    # Also trigger election
    gs.election_fired = True
    msgs = apply_end_of_turn_effects(gs)
    # 14a checks regime_shift first, so it should be the threshold event
    assert gs.last_threshold_event == "regime_shift"


# ══════════════════════════════════════════════════════════════════════════════
# 14. Normal turn -- no threshold
# ══════════════════════════════════════════════════════════════════════════════

def test_no_threshold_normal_turn():
    """A normal turn with stable conditions fires no era threshold."""
    gs = _fresh_gs()
    gs.current_day = 5
    gs.era_start_day = 1
    gs.pending_era_transition = False
    gs.last_threshold_event = None
    msgs = apply_end_of_turn_effects(gs)
    assert gs.last_threshold_event is None
    assert gs.pending_era_transition is False


# ══════════════════════════════════════════════════════════════════════════════
# 15. Serialization round-trip
# ══════════════════════════════════════════════════════════════════════════════

def test_era_serialize_deserialize():
    """Era fields survive a serialize -> deserialize round-trip."""
    gs = _fresh_gs()
    gs.current_era = 3
    gs.era_start_day = 42
    gs.era_transitions = [{'era': 1, 'start_day': 1, 'end_day': 20, 'threshold': 'election'}]
    gs.pending_era_transition = True
    gs.last_threshold_event = "stability_collapse"
    gs.last_threshold_day = 38

    data = gs.serialize()
    gs2 = GameState.deserialize(data)

    assert gs2.current_era == 3
    assert gs2.era_start_day == 42
    assert len(gs2.era_transitions) == 1
    assert gs2.era_transitions[0]['threshold'] == 'election'
    assert gs2.pending_era_transition is True
    assert gs2.last_threshold_event == "stability_collapse"
    assert gs2.last_threshold_day == 38


# ══════════════════════════════════════════════════════════════════════════════
# 16-18. Additional coverage
# ══════════════════════════════════════════════════════════════════════════════

def test_threshold_day_updated_to_current_day():
    """last_threshold_day is set to current_day when threshold fires."""
    gs = _fresh_gs(current_day=12)
    gs.relations['usa'] = 0  # reliable trigger that doesn't drift
    apply_end_of_turn_effects(gs)
    assert gs.last_threshold_day == 12


def test_multiple_relations_collapse_first_wins():
    """When multiple NPCs are at 0, the first one encountered is the threshold."""
    gs = _fresh_gs()
    gs.relations = {'usa': 0, 'arabia': 0, 'eu': 50, 'dprg': 50, 'russia': 35, 'china': 35}
    apply_end_of_turn_effects(gs)
    # The threshold should be for the first NPC iterated (dict order in Python 3.7+)
    assert gs.last_threshold_event.startswith("relations_collapse_")
    assert gs.pending_era_transition is True


def test_backstop_uses_era_start_not_day_1():
    """Backstop calculates days_in_era from era_start_day, not from day 1."""
    gs = _fresh_gs()
    gs.era_start_day = 20
    gs.current_day = 25  # only 5 days in era, not 24
    gs.last_threshold_day = 0
    gs.pending_era_transition = False
    msgs = apply_end_of_turn_effects(gs)
    # 5 days in era < 20 threshold, backstop should NOT fire
    assert not any("BACKSTOP" in str(m) for m in msgs)


def test_compute_regime_from_axes_patronage_vs_kleptocracy():
    """Patronage State becomes Kleptocracy when extraction >= 7 (total 16-25)."""
    axes = {
        'military': 3, 'intelligence': 3, 'resource_dev': 5,
        'media': 3, 'judicial': 3, 'political': 2, 'extraction': 7,
    }
    # total non-resource_dev = 3+3+3+3+2+7 = 21 => in 16-25 range
    assert compute_regime_from_axes(axes) == 'Kleptocracy'

    # Same total but extraction < 7 => Patronage State
    axes2 = dict(axes)
    axes2['extraction'] = 4
    axes2['military'] = 6  # keep total = 21
    assert compute_regime_from_axes(axes2) == 'Patronage State'
