# -*- coding: utf-8 -*-
"""Tests for 10C Operations System: ops caps, military/intel/diplomatic/shadow operations.
Tests the pure game logic — no DB/API needed. API endpoint tests use monkeypatching."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_10c.db")

import pytest
from game_state import GameState
from turn_processor import apply_end_of_turn_effects


# ── Helper ────────────────────────────────────────────────────────────────

def make_gs(**overrides):
    """Create a full GameState with safe defaults for 10C operations testing."""
    gs = GameState()
    gs.budget = 50.0
    gs.personal_wealth = 20.0
    gs.stability = 60
    gs.public_approval = 55
    gs.military_strength = 30
    gs.military_tier = 3
    gs.intelligence_tier = 3
    gs.diplomatic_tier = 2
    gs.detection_heat = 30
    gs.current_day = 10
    gs.current_turn = 10
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
    gs.modernization_tranche_1 = False
    gs.modernization_tranche_2 = False
    gs.modernization_tranche_3 = False
    gs.arms_export_count = 0
    gs.journalist_elimination_available = True
    gs.journalist_elimination_day = 0
    gs.journalist_elimination_discovery_day = 0
    gs.loyal_generals_installed = False
    for k, v in overrides.items():
        setattr(gs, k, v)
    return gs


# ── API endpoint testing via monkeypatch ──────────────────────────────────

_stored_gs = {}

def _mock_load(sid):
    return _stored_gs.get(sid)

def _mock_save(sid, gs):
    _stored_gs[sid] = gs

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    """Patch api._load_gs and _save_gs to use in-memory dict."""
    import api
    monkeypatch.setattr(api, '_load_gs', _mock_load)
    monkeypatch.setattr(api, '_save_gs', _mock_save)
    _stored_gs.clear()

def _store_gs(gs):
    sid = "test-session"
    _stored_gs[sid] = gs
    return sid


# ── Import API endpoint functions ─────────────────────────────────────────

from fastapi.testclient import TestClient
from api import app
_client = TestClient(app)


# ══════════════════════════════════════════════════════════════════════════
# OPERATIONS CAP TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_ops_cap_legitimate_enforced():
    """2nd legitimate op should be rejected."""
    gs = make_gs(diplomatic_tier=2)
    sid = _store_gs(gs)
    r1 = _client.post(f"/game/{sid}/operations/diplomatic-pressure", json={"target_npc": "usa"})
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    r2 = _client.post(f"/game/{sid}/operations/diplomatic-pressure", json={"target_npc": "arabia"})
    assert r2.status_code == 400
    assert "cap" in r2.json()["detail"].lower()


def test_ops_cap_shadow_enforced():
    """2nd shadow op should be rejected."""
    gs = make_gs(domestic_surveillance_tier=3, extraction_tier=3)
    sid = _store_gs(gs)
    r1 = _client.post(f"/game/{sid}/operations/reputation-laundering", json={})
    assert r1.status_code == 200
    r2 = _client.post(f"/game/{sid}/operations/political-sabotage", json={"target_npc": "usa"})
    assert r2.status_code == 400
    assert "cap" in r2.json()["detail"].lower()


def test_ops_cap_resets_eot():
    """Ops caps reset after end-of-turn."""
    gs = make_gs(ops_legitimate_this_turn=1, ops_shadow_this_turn=1)
    apply_end_of_turn_effects(gs)
    assert gs.ops_legitimate_this_turn == 0
    assert gs.ops_shadow_this_turn == 0


# ══════════════════════════════════════════════════════════════════════════
# MILITARY TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_force_projection_applies_debuff():
    """Force Projection should set ceiling modifier on target NPC."""
    gs = make_gs(military_tier=3, force_projection_cooldown=0)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/force-projection", json={"target_npc": "arabia"})
    assert r.status_code == 200
    updated = _stored_gs[sid]
    mods = getattr(updated, 'force_projection_modifiers', {})
    assert 'arabia' in mods
    assert mods['arabia']['ceiling_modifier'] == 1.25


def test_force_projection_cooldown():
    """Force Projection should be blocked when on cooldown."""
    gs = make_gs(military_tier=3, force_projection_cooldown=2)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/force-projection", json={"target_npc": "usa"})
    assert r.status_code == 400
    assert "cooldown" in r.json()["detail"].lower()


def test_arms_export_diminishing_returns():
    """Arms export relations bonus should decrease with prior sales."""
    gs1 = make_gs(military_tier=3, arms_export_count=0)
    sid1 = "test-arms1"
    _stored_gs[sid1] = gs1
    r1 = _client.post(f"/game/{sid1}/operations/arms-export", json={"target_npc": "arabia"})
    assert r1.status_code == 200
    assert r1.json()["relations_bonus"] == 8  # max(2, 8-0*2)

    gs2 = make_gs(military_tier=3, arms_export_count=3)
    sid2 = "test-arms2"
    _stored_gs[sid2] = gs2
    r2 = _client.post(f"/game/{sid2}/operations/arms-export", json={"target_npc": "arabia"})
    assert r2.status_code == 200
    assert r2.json()["relations_bonus"] == 2  # max(2, 8-3*2)


def test_arms_export_cross_npc_bill():
    """Bill (USA) should react negatively to arms export to Russia."""
    gs = make_gs(military_tier=3,
                 relations={'usa': 60, 'arabia': 50, 'eu': 50, 'dprg': 30, 'russia': 40, 'china': 35})
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/arms-export", json={"target_npc": "russia"})
    assert r.status_code == 200
    reactions = r.json()["cross_npc_reactions"]
    assert reactions.get('usa') == -8


def test_modernization_t1_prereqs():
    """Tranche 2 should be blocked before Tranche 1 is complete."""
    gs = make_gs(military_tier=5, tech_level=4.0, modernization_tranche_1=False)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/modernization", json={"tranche": 2})
    assert r.status_code == 400
    assert "Tranche 1" in r.json()["detail"]


def test_modernization_t1_decay_modifier():
    """Modernization T1 flag should reduce military decay (applied in EOT)."""
    gs = make_gs(military_tier=0, modernization_tranche_1=True,
                 military_strength=50, cabinet_axes={'military': 0, 'intelligence': 3,
                 'resource_dev': 2, 'media': 2, 'judicial': 2, 'political': 2, 'extraction': 2})
    old_mil = gs.military_strength
    apply_end_of_turn_effects(gs)
    # With T1 and tier 0: base decay = 2, after T1 0.8x = -max(1, round(1.6)) = -2 ...
    # The modifier is applied, military should have decreased
    assert gs.military_strength < old_mil


# ══════════════════════════════════════════════════════════════════════════
# INTELLIGENCE TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_kompromat_7day_collection():
    """Kompromat collection should mature after 7 days in EOT."""
    gs = make_gs()
    gs.kompromat_collection_active = {
        'usa': {'day_started': 2, 'detection_risk_per_day': 0.0}
    }
    gs.current_day = 9  # 9 - 2 = 7
    apply_end_of_turn_effects(gs)
    assert 'usa' in gs.kompromat_holdings
    assert gs.kompromat_holdings['usa']['active'] is True
    assert gs.kompromat_holdings['usa']['uses_remaining'] == 3
    assert 'usa' not in gs.kompromat_collection_active


def test_kompromat_detection_roll():
    """Kompromat collection with 100% detection should always be caught."""
    gs = make_gs()
    gs.kompromat_collection_active = {
        'arabia': {'day_started': gs.current_day, 'detection_risk_per_day': 1.0}
    }
    old_rel = gs.relations['arabia']
    apply_end_of_turn_effects(gs)
    assert 'arabia' not in gs.kompromat_collection_active
    assert gs.relations['arabia'] < old_rel
    detected = [e for e in gs.operations_log if e.get('detected')]
    assert len(detected) >= 1


def test_kompromat_uses_decrement():
    """Using kompromat should decrement uses_remaining."""
    gs = make_gs(intelligence_tier=3)
    gs.kompromat_holdings = {
        'eu': {'active': True, 'uses_remaining': 3, 'day_collected': 5, 'burned': False}
    }
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/kompromat-use",
                     json={"target_npc": "eu", "action": "suppress"})
    assert r.status_code == 200
    updated = _stored_gs[sid]
    assert updated.kompromat_holdings['eu']['uses_remaining'] == 2


def test_kompromat_ji_won_blocked():
    """Kompromat collection should be blocked for Ji-won (DPRG)."""
    gs = make_gs(intelligence_tier=3)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/kompromat-start", json={"target_npc": "dprg"})
    assert r.status_code == 400
    assert "Ji-won" in r.json()["detail"]


def test_loyalty_assessment_distortion():
    """Loyalty assessment should return an assessment string."""
    gs = make_gs(intelligence_tier=2, intel_politicized=True)
    gs.advisors = {
        'spy_chief': {
            'archetype': 'spy_chief', 'name': 'Test Spy',
            'loyalty': 20, 'competence': 60, 'trust': 30
        }
    }
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/loyalty-assessment",
                     json={"advisor_id": "spy_chief"})
    assert r.status_code == 200
    assert "assessment" in r.json()


def test_counter_intel_heat_reduction():
    """Counter-Intel Sweep should reduce detection heat by 15."""
    gs = make_gs(intelligence_tier=2, detection_heat=50, counter_intel_cooldown=0)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/counter-intel", json={})
    assert r.status_code == 200
    assert r.json()["heat_after"] == 35


# ══════════════════════════════════════════════════════════════════════════
# SHADOW TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_journalist_elimination_one_time():
    """Second journalist elimination should be blocked."""
    gs = make_gs(media_tier=7, judicial_tier=5, journalist_elimination_available=False)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/journalist-elimination", json={})
    assert r.status_code == 400
    assert "already used" in r.json()["detail"].lower()


def test_journalist_discovery_delayed():
    """Journalist elimination consequences should fire at discovery day."""
    gs = make_gs()
    gs.journalist_elimination_discovery_day = 10
    gs.current_day = 10
    gs.eu_relations_ceiling = 100
    gs.relations['eu'] = 60
    # The elimination endpoint sets this flag immediately; discovery fires later
    gs.action_journalists_liquidated = True
    apply_end_of_turn_effects(gs)
    # compute_eu_ceiling sees action_journalists_liquidated=True → cap 40
    assert gs.eu_relations_ceiling <= 40
    assert gs.relations['eu'] <= 40
    assert gs.journalist_elimination_discovery_day == 0


def test_journalist_flag_permanent():
    """Journalist elimination should set permanent flag."""
    gs = make_gs(media_tier=7, judicial_tier=5, journalist_elimination_available=True)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/journalist-elimination", json={})
    assert r.status_code == 200
    updated = _stored_gs[sid]
    assert updated.action_journalists_liquidated is True
    assert updated.journalist_elimination_available is False


def test_false_flag_bilateral_hit():
    """False Flag should work and return target/blame info."""
    gs = make_gs(domestic_surveillance_tier=5)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/false-flag",
                     json={"target_npc": "usa", "blame_npc": "eu"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["target"] == "usa"
    assert data["blame"] == "eu"


# ══════════════════════════════════════════════════════════════════════════
# DIPLOMATIC TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_trade_mission_cooldown():
    """Trade Mission should enforce 3-day cooldown."""
    gs = make_gs(diplomatic_tier=2, trade_mission_cooldown=0)
    sid = _store_gs(gs)
    r1 = _client.post(f"/game/{sid}/operations/trade-mission", json={"target_npc": "usa"})
    assert r1.status_code == 200
    r2 = _client.post(f"/game/{sid}/operations/trade-mission", json={"target_npc": "arabia"})
    assert r2.status_code == 400
    assert "cooldown" in r2.json()["detail"].lower()


def test_opposition_funding_detection():
    """Opposition funding should reduce relations (side effect -5 even if undetected)."""
    gs = make_gs(diplomatic_tier=3, personal_wealth=20.0)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/opposition-funding", json={"target_npc": "usa"})
    assert r.status_code == 200
    updated = _stored_gs[sid]
    assert updated.relations['usa'] < 50  # side effect -5 minimum


# ══════════════════════════════════════════════════════════════════════════
# COOLDOWN & EOT TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_cooldowns_decrement_eot():
    """All cooldowns should decrement by 1 each EOT."""
    gs = make_gs(counter_intel_cooldown=3, trade_mission_cooldown=2,
                 targeted_intercept_cooldown=1)
    apply_end_of_turn_effects(gs)
    assert gs.counter_intel_cooldown == 2
    assert gs.trade_mission_cooldown == 1
    assert gs.targeted_intercept_cooldown == 0


def test_cooldowns_floor_at_zero():
    """Cooldowns at 0 should stay at 0 after EOT."""
    gs = make_gs(counter_intel_cooldown=0, trade_mission_cooldown=0,
                 targeted_intercept_cooldown=0)
    apply_end_of_turn_effects(gs)
    assert gs.counter_intel_cooldown == 0
    assert gs.trade_mission_cooldown == 0
    assert gs.targeted_intercept_cooldown == 0


def test_intel_sharing_level_gate():
    """Intel sharing Level 2 should require intel_tier 3."""
    gs = make_gs(intelligence_tier=2,
                 relations={'usa': 70, 'arabia': 50, 'eu': 50, 'dprg': 30, 'russia': 35, 'china': 35})
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/intel-sharing",
                     json={"target_npc": "usa", "level": 2})
    assert r.status_code == 400  # intel_tier 2 < 3 required


def test_reputation_laundering_no_detection():
    """Reputation laundering should reduce heat with no risk."""
    gs = make_gs(extraction_tier=3, detection_heat=40)
    sid = _store_gs(gs)
    r = _client.post(f"/game/{sid}/operations/reputation-laundering", json={})
    assert r.status_code == 200
    updated = _stored_gs[sid]
    assert updated.detection_heat == 25


def test_force_projection_modifier_expires():
    """Force projection ceiling modifier should expire after set day."""
    gs = make_gs()
    gs.force_projection_modifiers = {
        'usa': {'ceiling_modifier': 1.25, 'expires_day': 10}
    }
    gs.current_day = 10
    apply_end_of_turn_effects(gs)
    assert 'usa' not in gs.force_projection_modifiers
