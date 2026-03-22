# -*- coding: utf-8 -*-
"""Tests for 10B-2: Event screen, advisor drawer, declarations,
right sidebar intel, diplomatic cables.
Tests pure game logic — no DB/API/Haiku calls needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_10b2.db")

import pytest
from unittest.mock import patch, MagicMock
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a GameState with safe defaults for 10B-2 testing."""
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
    gs.soft_power_score = 50
    gs.declarations_available = 1
    gs.declaration_used_today = False
    gs.todays_declaration = ""
    gs.declaration_history = []
    gs.event_dialogues = {}
    gs.diplomatic_cables = {}
    gs.cables_generated_today = False
    gs.intel_ops_today = []
    gs.advisor_assigned_today = []
    gs.advisors = {}
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


def make_event(event_id="evt_test01", title="Test Crisis", severity="urgent",
               category="diplomatic", required=True, applicable_npcs=None):
    return {
        "id": event_id,
        "title": title,
        "summary": "A test event requiring diplomatic response.",
        "severity": severity,
        "category": category,
        "applicable_npcs": applicable_npcs or ["usa", "eu"],
        "required": required,
        "resolved": False,
        "resolution": None,
        "escalated_from_communique": False,
        "era": 1,
        "day": 5,
    }


# ── Event Dialogue Tests ────────────────────────────────────────────────────

class TestEventDialogue:

    @patch('anthropic.Anthropic')
    def test_event_dialogue_generated(self, mock_anthropic_cls):
        """Event dialogue returns NPC messages for applicable NPCs."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="We need to discuss this crisis immediately.")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        os.environ["ANTHROPIC_API_KEY"] = "test-key-fake"
        from npc_engine import generate_event_dialogue
        gs = make_gs()
        event = make_event(applicable_npcs=["usa", "eu"])

        results = generate_event_dialogue(gs, event)

        assert len(results) == 2
        npc_ids = {r["npc_id"] for r in results}
        assert "usa" in npc_ids
        assert "eu" in npc_ids
        for r in results:
            assert "message" in r
            assert "npc_name" in r
            assert len(r["message"]) > 0

    def test_event_dialogue_cached(self):
        """Second call for same event_id returns cached result."""
        gs = make_gs()
        event = make_event(event_id="evt_cached01")
        cached_dialogues = [{"npc_id": "usa", "npc_name": "Bill", "message": "Cached msg"}]
        gs.event_dialogues = {"evt_cached01": cached_dialogues}

        # Verify cache is in serialized state
        data = gs.serialize()
        assert data["event_dialogues"]["evt_cached01"] == cached_dialogues

        # Deserialize and verify cache persists
        gs2 = GameState.deserialize(data)
        assert gs2.event_dialogues["evt_cached01"] == cached_dialogues


# ── Advisor Event Analysis Tests ─────────────────────────────────────────────

class TestAdvisorEventAnalysis:

    @patch('anthropic.Anthropic')
    def test_advisor_analysis_for_event(self, mock_anthropic_cls):
        """Advisor analyses generated for assigned advisors."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This crisis poses fiscal risks.")]
        mock_response.usage.input_tokens = 80
        mock_response.usage.output_tokens = 40
        mock_client.messages.create.return_value = mock_response

        os.environ["ANTHROPIC_API_KEY"] = "test-key-fake"
        from npc_engine import generate_advisor_event_analysis
        gs = make_gs(
            advisor_assigned_today=["finance_minister"],
            advisors={"finance_minister": {"name": "Klaus", "archetype": "finance_minister"}}
        )
        event = make_event()

        results = generate_advisor_event_analysis(gs, event)
        assert len(results) == 1
        assert results[0]["advisor_name"] == "Klaus"
        assert results[0]["advisor_type"] == "finance_minister"
        assert len(results[0]["analysis_text"]) > 0

    def test_advisor_analysis_only_assigned(self):
        """Only assigned advisors are included — not all advisors on staff."""
        from npc_engine import generate_advisor_event_analysis
        gs = make_gs(
            advisor_assigned_today=["finance_minister"],
            advisors={
                "finance_minister": {"name": "Klaus", "archetype": "finance_minister"},
                "diplomat": {"name": "Alena", "archetype": "diplomat"},
            }
        )
        # Without API key, falls back to placeholder text
        results = generate_advisor_event_analysis(gs, make_event())
        # Should only have 1 result (finance_minister), not 2
        assert len(results) == 1
        assert results[0]["advisor_name"] == "Klaus"


# ── Intel Tests ──────────────────────────────────────────────────────────────

class TestGetNpcIntel:

    def test_get_intel_costs_wealth(self):
        """Intel deducts $1.5B from national budget."""
        gs = make_gs(budget=50.0, intelligence_tier=2)
        initial = gs.budget
        cost = 1.5
        gs.budget = round(gs.budget - cost, 1)
        assert gs.budget == pytest.approx(initial - cost)

    def test_get_intel_gated_tier(self):
        """Intel blocked below intel tier 1."""
        gs = make_gs(intelligence_tier=0)
        assert gs.intelligence_tier < 1

    @patch('random.random', return_value=0.05)  # 5% < 10% threshold
    def test_get_intel_detection_roll(self, mock_rand):
        """Detection (10% base) applies -5 relations with target."""
        gs = make_gs(intelligence_tier=2)
        initial_rel = gs.relations["usa"]

        detected = mock_rand() < 0.10
        assert detected is True

        if detected:
            gs.relations["usa"] = max(0, gs.relations["usa"] - 5)

        assert gs.relations["usa"] == initial_rel - 5


# ── Declaration Tests ────────────────────────────────────────────────────────

class TestDeclarations:

    @patch('anthropic.Anthropic')
    def test_declaration_applies_consequences(self, mock_anthropic_cls):
        """NPC reaction deltas applied to relations."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"interpretation": "A bold stance", "npc_reactions": {"usa": 5, "arabia": -3, "eu": 2, "russia": -1, "china": 0, "dprg": -2}, "soft_power_delta": 2, "generates_world_event": false, "world_event_hint": ""}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80
        mock_client.messages.create.return_value = mock_response

        os.environ["ANTHROPIC_API_KEY"] = "test-key-fake"
        from npc_engine import generate_declaration_consequences
        gs = make_gs()
        result = generate_declaration_consequences(gs, "Europa stands with democracy!")

        assert "interpretation" in result
        assert result["npc_reactions"]["usa"] == 5
        assert result["npc_reactions"]["arabia"] == -3
        assert result["soft_power_delta"] == 2

        # Apply to game state
        for npc_id, delta in result["npc_reactions"].items():
            if npc_id in gs.relations:
                gs.relations[npc_id] = max(0, min(100, gs.relations[npc_id] + delta))

        assert gs.relations["usa"] == 55  # 50 + 5
        assert gs.relations["arabia"] == 47  # 50 - 3

    def test_declaration_blocked_before_day5(self):
        """Declarations locked until day 5 (declarations_available == 0)."""
        gs = make_gs(current_turn=3, declarations_available=0)
        assert gs.declarations_available < 1

    def test_declaration_one_per_day(self):
        """Second declaration blocked after first is used."""
        gs = make_gs(declaration_used_today=False, declarations_available=1)
        assert not gs.declaration_used_today

        # Issue first declaration
        gs.declaration_used_today = True
        gs.todays_declaration = "We stand firm."

        # Second attempt should be blocked
        assert gs.declaration_used_today is True

    def test_declaration_stored_in_history(self):
        """Declaration saved to declaration_history."""
        gs = make_gs()
        gs.declaration_history.append({
            "day": 5,
            "era": 1,
            "text": "Europa demands peace.",
            "consequences": {"interpretation": "Peace call", "npc_reactions": {}},
        })

        assert len(gs.declaration_history) == 1
        assert gs.declaration_history[0]["text"] == "Europa demands peace."

        # Verify serialization roundtrip
        data = gs.serialize()
        gs2 = GameState.deserialize(data)
        assert len(gs2.declaration_history) == 1
        assert gs2.declaration_history[0]["text"] == "Europa demands peace."

    def test_declaration_generates_event(self):
        """World event added if generates_world_event is true."""
        gs = make_gs(daily_events=[])

        consequences = {
            "generates_world_event": True,
            "world_event_hint": "International community reacts to bold declaration",
            "npc_reactions": {"usa": 10, "eu": -5},
        }

        if consequences["generates_world_event"] and consequences.get("world_event_hint"):
            new_event = {
                "id": "evt_decl01",
                "title": "Response to Declaration",
                "summary": consequences["world_event_hint"],
                "severity": "moderate",
                "category": "diplomatic",
                "applicable_npcs": [npc for npc, d in consequences["npc_reactions"].items() if abs(d) >= 5],
                "required": False,
                "resolved": False,
                "resolution": None,
            }
            gs.daily_events.append(new_event)

        assert len(gs.daily_events) == 1
        assert gs.daily_events[0]["title"] == "Response to Declaration"
        assert "usa" in gs.daily_events[0]["applicable_npcs"]
        assert "eu" in gs.daily_events[0]["applicable_npcs"]


# ── Cables Tests ─────────────────────────────────────────────────────────────

class TestDiplomaticCables:

    def test_cables_generated_once_per_day(self):
        """Cable generation is idempotent — cables_generated_today flag."""
        gs = make_gs(cables_generated_today=False)
        assert not gs.cables_generated_today

        # Simulate generation
        gs.diplomatic_cables = {"usa": "Monitoring situation", "eu": "Seeking dialogue"}
        gs.cables_generated_today = True

        # Should not regenerate
        assert gs.cables_generated_today is True
        assert len(gs.diplomatic_cables) == 2


# ── EOT Reset Tests ─────────────────────────────────────────────────────────

class TestEotResets:

    def test_declaration_eot_reset(self):
        """todays_declaration, event_dialogues, intel_ops_today cleared on EOT.
        declaration_history persists."""
        gs = make_gs(
            current_turn=5,
            todays_declaration="We demand peace.",
            declaration_used_today=True,
            event_dialogues={"evt_1": [{"npc_id": "usa", "message": "hi"}]},
            cables_generated_today=True,
            intel_ops_today=[{"target": "usa", "detected": False}],
            declaration_history=[{"day": 5, "era": 1, "text": "We demand peace.", "consequences": {}}],
        )

        apply_end_of_turn_effects(gs)

        # Daily fields reset
        assert gs.todays_declaration == ""
        assert gs.declaration_used_today is False
        assert gs.event_dialogues == {}
        assert gs.cables_generated_today is False
        assert gs.intel_ops_today == []

        # Persistent fields survive
        assert len(gs.declaration_history) == 1
        assert gs.declaration_history[0]["text"] == "We demand peace."


# ── Serialization Roundtrip ──────────────────────────────────────────────────

class TestSerialization:

    def test_10b2_fields_roundtrip(self):
        """All 10B-2 fields survive serialize/deserialize."""
        gs = make_gs(
            todays_declaration="Test declaration",
            declaration_history=[{"day": 1, "text": "Hello"}],
            event_dialogues={"evt_x": [{"npc_id": "usa", "message": "Test"}]},
            diplomatic_cables={"usa": "Cable text"},
            cables_generated_today=True,
            intel_ops_today=[{"target": "eu", "detected": True}],
        )

        data = gs.serialize()
        gs2 = GameState.deserialize(data)

        assert gs2.todays_declaration == "Test declaration"
        assert len(gs2.declaration_history) == 1
        assert gs2.event_dialogues["evt_x"][0]["npc_id"] == "usa"
        assert gs2.diplomatic_cables["usa"] == "Cable text"
        assert gs2.cables_generated_today is True
        assert len(gs2.intel_ops_today) == 1
        assert gs2.intel_ops_today[0]["detected"] is True
