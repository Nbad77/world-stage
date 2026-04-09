# -*- coding: utf-8 -*-
"""Tests for 10B-3: Deal consequences, briefing items, cable refresh, voice fix.
Tests pure game logic — no DB/API/Haiku calls needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_10b3.db")

import pytest
from unittest.mock import patch, MagicMock
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a GameState with safe defaults for 10B-3 testing."""
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
    gs.relations = {'usa': 55, 'arabia': 45, 'eu': 60, 'dprg': 30, 'russia': 35, 'china': 40}
    gs.legitimacy_stability = 60.0
    gs.coercion_stability = 20.0
    gs.deals_today = []
    gs.deal_history = []
    gs.diplomatic_cables = {}
    gs.cables_generated_today = False
    for key, val in overrides.items():
        setattr(gs, key, val)
    return gs


# ── Section 2: Deal Consequences ────────────────────────────────────────────

def test_deal_consequences_generated():
    """generate_deal_consequences returns a valid consequence dict."""
    from npc_engine import _deal_consequences_fallback
    result = _deal_consequences_fallback('usa', '$2B economic assistance', False)
    assert 'relations_delta' in result
    assert 'budget_delta' in result
    assert 'stability_delta' in result
    assert 'briefing_summary' in result
    assert 'historian_note' in result
    assert 'cross_npc_visibility' in result


def test_deal_consequences_applied():
    """Deal consequence deltas are applied to game state."""
    gs = make_gs()
    old_usa = gs.relations['usa']
    old_stability = gs.legitimacy_stability

    # Simulate applying consequences
    consequences = {
        'relations_delta': {'usa': 5, 'russia': -3},
        'budget_delta': -1.5,
        'personal_wealth_delta': 0.5,
        'stability_delta': 2.0,
        'cross_npc_visibility': ['russia'],
        'historian_note': 'A deal was struck.',
        'briefing_summary': 'Economic deal with USA.',
    }

    for npc_key, delta in consequences['relations_delta'].items():
        if npc_key in gs.relations:
            gs.update_relations(npc_key, delta)
    gs.update_budget(consequences['budget_delta'])
    gs.personal_wealth += consequences['personal_wealth_delta']
    gs.legitimacy_stability += consequences['stability_delta']

    assert gs.relations['usa'] == old_usa + 5
    # Session 11: negative deltas are dampened (standing=50, reliability=100 -> ~0.40 dampening)
    # effective = -3 * (1 - 0.40) = -1.8 -> 35 - 1.8 = 33.2
    assert abs(gs.relations['russia'] - 33.2) < 0.1
    assert gs.budget == 50.0 - 1.5
    assert gs.personal_wealth == 10.5
    assert gs.legitimacy_stability == old_stability + 2.0


def test_backchannel_no_cross_npc():
    """Covert backchannel deals have empty cross_npc_visibility."""
    from npc_engine import _deal_consequences_fallback
    result = _deal_consequences_fallback('arabia', 'Oil partnership', True)
    assert result['cross_npc_visibility'] == []


def test_public_deal_cross_npc_visible():
    """Public deals include rival NPCs in cross_npc_visibility."""
    from npc_engine import _deal_consequences_fallback
    result = _deal_consequences_fallback('usa', 'Military aid package', False)
    assert len(result['cross_npc_visibility']) > 0
    # USA's rivals include russia and dprg
    assert any(npc in result['cross_npc_visibility'] for npc in ['russia', 'dprg'])


def test_deal_added_to_deals_today():
    """Completed deal is recorded in gs.deals_today."""
    gs = make_gs()
    assert len(gs.deals_today) == 0

    deal_record = {
        'id': 'deal_5_usa_0',
        'npc_id': 'usa',
        'npc_name': 'Bill Hartwell',
        'deal_text': '$2B economic package',
        'briefing_summary': 'Economic deal with USA.',
        'source': 'sidebar',
        'day': 5,
        'consequences': {},
    }
    gs.deals_today.append(deal_record)
    assert len(gs.deals_today) == 1
    assert gs.deals_today[0]['npc_id'] == 'usa'
    assert gs.deals_today[0]['source'] == 'sidebar'


def test_deals_today_serializes():
    """deals_today survives serialize/deserialize cycle."""
    gs = make_gs()
    gs.deals_today = [{
        'id': 'deal_5_usa_0',
        'npc_id': 'usa',
        'npc_name': 'Bill Hartwell',
        'deal_text': 'Test deal',
        'briefing_summary': 'Test summary',
        'source': 'sidebar',
        'day': 5,
        'consequences': {},
    }]

    data = gs.serialize()
    assert 'deals_today' in data
    assert len(data['deals_today']) == 1

    gs2 = GameState.deserialize(data)
    assert len(gs2.deals_today) == 1
    assert gs2.deals_today[0]['npc_id'] == 'usa'


def test_deals_reset_on_eot():
    """deals_today clears on end-of-turn."""
    gs = make_gs()
    gs.deals_today = [{'id': 'deal_5_usa_0', 'npc_id': 'usa'}]
    assert len(gs.deals_today) == 1

    apply_end_of_turn_effects(gs)
    assert len(gs.deals_today) == 0


# ── Section 4: Cable Refresh ────────────────────────────────────────────────

def test_cables_clear_on_eot():
    """Diplomatic cables are cleared on end-of-turn for fresh regeneration."""
    gs = make_gs()
    gs.diplomatic_cables = {'usa': 'Old cable text', 'arabia': 'Another old cable'}
    gs.cables_generated_today = True

    apply_end_of_turn_effects(gs)

    assert gs.diplomatic_cables == {}
    assert gs.cables_generated_today == False


# ── Section 1: Narrator Voice Ban ───────────────────────────────────────────

def test_no_narrator_voice_in_negotiation_prompts():
    """All negotiation prompts include the narrator ban instruction."""
    from npc_engine import _NEGOTIATION_DIALOGUE_PROMPTS, _NARRATOR_BAN
    for npc_id, prompt in _NEGOTIATION_DIALOGUE_PROMPTS.items():
        assert 'CRITICAL VOICE RULE' in prompt, f"{npc_id} prompt missing narrator ban"
        assert 'No stage directions' in prompt, f"{npc_id} prompt still allows stage directions"
        # Ensure old stage direction permissions are removed
        assert '(with stage directions)' not in prompt, f"{npc_id} still has stage direction permission"
        assert '(with brief stage directions' not in prompt, f"{npc_id} still has brief stage direction permission"


def test_stage_directions_removed_from_base_prompts():
    """Sadam and Ji-won base prompts no longer encourage stage directions."""
    from npc_engine import SADAM_SYSTEM_PROMPT, JIWON_SYSTEM_PROMPT
    assert 'stage directions naturally' not in SADAM_SYSTEM_PROMPT
    assert '*lighting cigar*' not in SADAM_SYSTEM_PROMPT
    assert 'One stage direction per response' not in SADAM_SYSTEM_PROMPT
    assert '*brief action if needed*' not in JIWON_SYSTEM_PROMPT


def test_build_npc_system_prompt_includes_narrator_ban():
    """build_npc_system_prompt injects narrator ban and tone guidance."""
    from npc_engine import build_npc_system_prompt, _NARRATOR_BAN
    gs = make_gs()
    prompt = build_npc_system_prompt('usa', gs)
    assert 'CRITICAL VOICE RULE' in prompt
    assert 'RELATIONSHIP CONTEXT' in prompt
    assert 'PRIOR AGREEMENTS' in prompt


def test_build_npc_system_prompt_tone_hostile():
    """Low relations produce hostile tone guidance."""
    from npc_engine import build_npc_system_prompt
    gs = make_gs(relations={'usa': 15, 'arabia': 45, 'eu': 60, 'dprg': 30, 'russia': 35, 'china': 40})
    prompt = build_npc_system_prompt('usa', gs)
    assert 'hostile and minimal' in prompt


def test_build_npc_system_prompt_tone_partner():
    """High relations produce partner tone guidance."""
    from npc_engine import build_npc_system_prompt
    gs = make_gs(relations={'usa': 95, 'arabia': 45, 'eu': 60, 'dprg': 30, 'russia': 35, 'china': 40})
    prompt = build_npc_system_prompt('usa', gs)
    assert 'trusted partner' in prompt


def test_cable_fallback_toned():
    """Cable fallback text is relationship-toned, not generic."""
    from npc_engine import _build_cable_fallback
    assert 'goodwill' in _build_cable_fallback('usa', 75)
    assert 'routine' in _build_cable_fallback('usa', 50)
    assert 'brief' in _build_cable_fallback('usa', 25)
    assert 'No cable' in _build_cable_fallback('usa', 10)
