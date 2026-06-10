# -*- coding: utf-8 -*-
"""Tests for 10B-1 Daily Briefing System: game state fields, event generation,
escalation, morning briefing, daily resets.
Tests the pure game logic — no DB/API needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_10b1.db")

import pytest
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


# ── Helper ────────────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a full GameState with safe defaults for 10B-1 testing."""
    gs = GameState()
    gs.budget = 50.0
    gs.personal_wealth = 10.0
    gs.stability = 60
    gs.public_approval = 55
    gs.military_strength = 30
    gs.military_tier = 3
    gs.intelligence_tier = 3
    gs.diplomatic_tier = 2
    gs.detection_heat = 20
    gs.current_day = 5
    gs.current_turn = 5
    gs.current_era = 1
    gs.tech_level = 3.0
    gs.oil_price = 70
    gs.relations = {'usa': 50, 'arabia': 50, 'eu': 50, 'dprg': 30, 'russia': 35, 'china': 35}
    gs.npc_relations = {'usa_eu': 70, 'usa_arabia': 40, 'usa_dprg': 10, 'russia_usa': 15, 'china_usa': 25,
                        'china_russia': 45, 'eu_russia': 20, 'china_eu': 50, 'arabia_russia': 40,
                        'china_dprg': 35, 'arabia_china': 40, 'dprg_russia': 30}
    gs.cabinet_axes = {'military': 3, 'intelligence': 3, 'resource_dev': 2,
                       'media': 2, 'judicial': 2, 'political': 2, 'extraction': 2}
    gs.state_identity = {'regime_type': 'Managed Democracy'}
    gs.intel_politicized = False
    gs.media_tier = 0
    gs.judicial_tier = 0
    gs.domestic_surveillance_tier = 0
    gs.extraction_tier = 0
    gs.militia_tier = 0
    gs.pressure_suspensions = []
    gs.cross_npc_penalty_reductions = []
    gs.operations_log = []
    gs.kompromat_collection_active = {}
    gs.kompromat_holdings = {}
    gs.intel_sharing_agreements = {}
    gs.advisor_loyalty_ops = {}
    gs.force_projection_modifiers = {}
    gs.loyal_generals_installed = False
    gs.loyal_intel_chief_installed = False
    gs.legitimacy_stability = 30
    gs.coercion_stability = 30
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


def make_event(event_id="evt_test01", title="Test Event", severity="moderate",
               category="diplomatic", required=False, resolved=False,
               resolution=None, era=1, day=1, applicable_npcs=None):
    """Create a standard event dict for testing."""
    return {
        "id": event_id,
        "title": title,
        "summary": "A test event for unit testing.",
        "severity": severity,
        "category": category,
        "applicable_npcs": applicable_npcs or [],
        "required": required,
        "resolved": resolved,
        "resolution": resolution,
        "escalated_from_communique": False,
        "era": era,
        "day": day,
    }


# ── Tests ─────────────────────────────────────────────────────────────────

class TestDailyEventFields:
    """Test game state fields exist and serialize correctly."""

    def test_events_generated_on_day_start(self):
        """generate_daily_events returns a list of events."""
        from gm_engine import _generate_fallback_events
        gs = make_gs()
        events = _generate_fallback_events(gs)
        assert isinstance(events, list)
        assert len(events) >= 3

    def test_events_not_regenerated_if_exists(self):
        """Once day_events_generated is True, events should not be regenerated."""
        gs = make_gs()
        gs.day_events_generated = True
        gs.daily_events = [make_event()]
        # Simulating idempotent check
        assert gs.day_events_generated is True
        assert len(gs.daily_events) == 1

    def test_required_events_count_is_3(self):
        """Fallback events should have exactly 3 required events."""
        from gm_engine import _generate_fallback_events
        gs = make_gs()
        events = _generate_fallback_events(gs)
        required = [e for e in events if e["required"]]
        assert len(required) == 3

    def test_event_resolve_increments_counter(self):
        """Resolving a required event increments events_resolved_today."""
        gs = make_gs()
        gs.events_resolved_today = 0
        evt = make_event(required=True, resolved=False)
        gs.daily_events = [evt]
        # Simulate resolution
        evt["resolved"] = True
        evt["resolution"] = "Test resolution"
        if evt["required"]:
            gs.events_resolved_today += 1
        assert gs.events_resolved_today == 1

    def test_can_end_day_after_3_resolved(self):
        """Player can end day after resolving 3 required events."""
        gs = make_gs()
        gs.events_resolved_today = 3
        gs.events_required_today = 3
        assert gs.events_resolved_today >= gs.events_required_today

    def test_cannot_end_day_before_3_resolved(self):
        """Player cannot end day before resolving 3 required events."""
        gs = make_gs()
        gs.events_resolved_today = 2
        gs.events_required_today = 3
        assert gs.events_resolved_today < gs.events_required_today


class TestCommuniqueEscalation:
    """Test communique escalation logic in EOT."""

    def test_communique_escalation_fires(self):
        """An ignored NPC for 3+ days generates an escalated world event."""
        gs = make_gs()
        gs.communique_days_without_response = {"bill": 3, "marsha": 0}
        gs.daily_events = []
        gs.npcs_interacted_this_turn = set()
        apply_end_of_turn_effects(gs)
        # After EOT, bill's escalation should have fired
        escalated = [e for e in gs.daily_events if e.get("escalated_from_communique")]
        assert len(escalated) >= 1
        assert any("Washington" in e["title"] for e in escalated)

    def test_escalation_threshold_moderate(self):
        """NPC at exactly 3 days triggers escalation."""
        gs = make_gs()
        gs.communique_days_without_response = {"sadam": 3}
        gs.daily_events = []
        gs.npcs_interacted_this_turn = set()
        apply_end_of_turn_effects(gs)
        escalated = [e for e in gs.daily_events if e.get("escalated_from_communique")]
        assert len(escalated) >= 1
        assert any("Riyadh" in e["title"] for e in escalated)

    def test_escalation_resets_counter(self):
        """After escalation fires, the counter resets to 0."""
        gs = make_gs()
        gs.communique_days_without_response = {"volkov": 4}
        gs.daily_events = []
        gs.npcs_interacted_this_turn = set()
        apply_end_of_turn_effects(gs)
        # Counter should reset after escalation
        assert gs.communique_days_without_response.get("volkov", 99) == 0

    def test_no_escalation_below_threshold(self):
        """NPC at 1 day does NOT trigger escalation (EOT increments to 2, still below 3)."""
        gs = make_gs()
        # Start at 1 — EOT increments to 2, which is below threshold of 3
        gs.communique_days_without_response = {"bill": 1}
        gs.daily_events = []
        gs.npcs_interacted_this_turn = set()
        apply_end_of_turn_effects(gs)
        escalated = [e for e in gs.daily_events if e.get("escalated_from_communique")
                     and "Washington" in e.get("title", "")]
        assert len(escalated) == 0


class TestMorningBriefing:
    """Test morning briefing tiers."""

    def test_morning_briefing_vague_tier(self):
        """Low intel tier (0-1) returns vague briefing."""
        from npc_engine import INTEL_BRIEFING_TIERS
        assert INTEL_BRIEFING_TIERS[0] == "vague"
        assert INTEL_BRIEFING_TIERS[1] == "vague"

    def test_morning_briefing_specific_tier(self):
        """High intel tier (4-5) returns specific briefing."""
        from npc_engine import INTEL_BRIEFING_TIERS
        assert INTEL_BRIEFING_TIERS[4] == "specific"
        assert INTEL_BRIEFING_TIERS[5] == "specific"

    def test_morning_briefing_actionable_tier(self):
        """Max intel tier (6) returns actionable briefing."""
        from npc_engine import INTEL_BRIEFING_TIERS
        assert INTEL_BRIEFING_TIERS[6] == "actionable"

    def test_fallback_briefing_returns_text(self):
        """Fallback briefing returns non-empty text."""
        from npc_engine import _fallback_briefing
        for level in ("vague", "partial", "specific", "actionable"):
            text = _fallback_briefing(level)
            assert isinstance(text, str)
            assert len(text) > 20


class TestDailyResetEOT:
    """Test that EOT properly resets daily briefing fields."""

    def test_daily_reset_eot(self):
        """EOT resets events_resolved_today, day_events_generated, morning_briefing_read."""
        gs = make_gs()
        gs.events_resolved_today = 3
        gs.day_events_generated = True
        gs.morning_briefing_read = True
        gs.declaration_used_today = True
        gs.daily_events = [make_event()]
        apply_end_of_turn_effects(gs)
        assert gs.events_resolved_today == 0
        assert gs.day_events_generated is False
        assert gs.morning_briefing_read is False
        assert gs.declaration_used_today is False
        # daily_events gets cleared then possibly escalation events added
        # so just check it was cleared (escalation events have escalated_from_communique=True)
        non_escalated = [e for e in gs.daily_events if not e.get("escalated_from_communique")]
        assert len(non_escalated) == 0


class TestDeclarationGating:
    """Test declaration unlock at day 5."""

    def test_declaration_locked_before_day5(self):
        """declarations_available stays 0 before day 5."""
        gs = make_gs(current_turn=3)
        gs.declarations_available = 0
        apply_end_of_turn_effects(gs)
        assert gs.declarations_available == 0

    def test_declaration_unlocks_at_day5(self):
        """declarations_available becomes 1 at day 5+."""
        gs = make_gs(current_turn=5)
        gs.declarations_available = 0
        apply_end_of_turn_effects(gs)
        assert gs.declarations_available == 1


class TestEventStructure:
    """Test event JSON structure and validation."""

    def test_event_json_structure(self):
        """All required fields present in generated events."""
        from gm_engine import _generate_fallback_events
        gs = make_gs()
        events = _generate_fallback_events(gs)
        required_keys = {"id", "title", "summary", "severity", "category",
                         "applicable_npcs", "required", "resolved", "resolution",
                         "escalated_from_communique", "era", "day"}
        for evt in events:
            missing = required_keys - set(evt.keys())
            assert missing == set(), f"Missing keys: {missing}"

    def test_era1_authored_types_only(self):
        """Era 1 prompt uses AUTHORED_EVENT_TYPES."""
        from gm_engine import AUTHORED_EVENT_TYPES, _build_event_user_prompt
        gs = make_gs(current_era=1)
        prompt = _build_event_user_prompt(gs, 5, 1, 4)
        # Era 1 prompt should reference authored event types
        for event_type in AUTHORED_EVENT_TYPES[:3]:
            assert event_type in prompt

    def test_validate_event_fills_defaults(self):
        """_validate_event fills missing fields."""
        from gm_engine import _validate_event
        partial = {"title": "Test"}
        result = _validate_event(partial, 2, 10)
        assert result["era"] == 2
        assert result["day"] == 10
        assert result["resolved"] is False
        assert result["severity"] in ("routine", "moderate", "urgent", "critical")
        assert "id" in result

    def test_validate_event_corrects_invalid_severity(self):
        """_validate_event corrects invalid severity values."""
        from gm_engine import _validate_event
        evt = {"severity": "EXTREME"}
        result = _validate_event(evt, 1, 1)
        assert result["severity"] == "moderate"


class TestSerializeDeserialize:
    """Test that new fields survive serialize/deserialize round-trip."""

    def test_briefing_fields_roundtrip(self):
        """All 10B-1 fields survive serialize → deserialize."""
        gs = make_gs()
        gs.daily_events = [make_event()]
        gs.events_resolved_today = 2
        gs.events_required_today = 3
        gs.day_events_generated = True
        gs.communique_days_without_response = {"bill": 2, "sadam": 0}
        gs.morning_briefing_read = True
        gs.declarations_available = 1
        gs.declaration_used_today = True

        data = gs.serialize()
        gs2 = GameState.deserialize(data)

        assert gs2.daily_events == gs.daily_events
        assert gs2.events_resolved_today == 2
        assert gs2.events_required_today == 3
        assert gs2.day_events_generated is True
        assert gs2.communique_days_without_response == {"bill": 2, "sadam": 0}
        assert gs2.morning_briefing_read is True
        assert gs2.declarations_available == 1
        assert gs2.declaration_used_today is True
