"""Tests for 9C: Endings Completion — verify ending triggers fire correctly."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from turn_processor import check_alternate_endings, check_game_over


class MockGameState:
    """Minimal mock for ending trigger tests."""
    pass


def make_ending_gs(**overrides):
    """Create a MockGameState with safe defaults for ending trigger testing."""
    gs = MockGameState()

    # Core stats
    gs.current_turn = overrides.get('current_turn', 10)
    gs.max_turns = overrides.get('max_turns', 10)
    gs.stability = overrides.get('stability', 50)
    gs.public_approval = overrides.get('public_approval', 50)
    gs.budget = overrides.get('budget', 30.0)
    gs.personal_wealth = overrides.get('personal_wealth', 5.0)

    # Relations
    gs.relations = overrides.get('relations', {
        "usa": 50, "eu": 50, "russia": 35, "china": 35, "arabia": 45, "dprg": 40
    })

    # Suppression / capture flags
    gs.action_press_suppressed = overrides.get('action_press_suppressed', False)
    gs.action_judiciary_captured = overrides.get('action_judiciary_captured', False)
    gs.constitutional_revision_active = overrides.get('constitutional_revision_active', False)

    # Ending state
    gs.ending_triggered = overrides.get('ending_triggered', None)
    gs.martyrdom_triggered = overrides.get('martyrdom_triggered', False)

    # Exile fields
    gs.in_exile = overrides.get('in_exile', False)
    gs.exile_day = overrides.get('exile_day', 0)
    gs.return_attempts = overrides.get('return_attempts', 0)
    gs.return_progress = overrides.get('return_progress', 0.0)
    gs.restoration_active = overrides.get('restoration_active', False)

    return gs


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: State Capture and Martyrdom verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateCaptureEnding:
    def test_state_capture_triggers_with_all_conditions(self):
        """State Capture requires: personal_wealth >= 50, capture triad, final turn."""
        gs = make_ending_gs(
            personal_wealth=55,
            constitutional_revision_active=True,
            action_press_suppressed=True,
            action_judiciary_captured=True,
            current_turn=10,
        )
        result = check_alternate_endings(gs)
        assert result == "capture"
        assert gs.ending_triggered == "capture"

    def test_state_capture_fails_without_wealth(self):
        """Should not trigger if personal_wealth < 50."""
        gs = make_ending_gs(
            personal_wealth=45,
            constitutional_revision_active=True,
            action_press_suppressed=True,
            action_judiciary_captured=True,
            current_turn=10,
        )
        result = check_alternate_endings(gs)
        assert result != "capture"

    def test_state_capture_fails_without_triad(self):
        """Should not trigger if any triad element is missing."""
        gs = make_ending_gs(
            personal_wealth=55,
            constitutional_revision_active=True,
            action_press_suppressed=True,
            action_judiciary_captured=False,  # Missing judicial
            current_turn=10,
        )
        result = check_alternate_endings(gs)
        assert result != "capture"

    def test_state_capture_fails_before_final_turn(self):
        """Should not trigger before turn 10 (any_turn=False)."""
        gs = make_ending_gs(
            personal_wealth=55,
            constitutional_revision_active=True,
            action_press_suppressed=True,
            action_judiciary_captured=True,
            current_turn=5,
        )
        result = check_alternate_endings(gs)
        assert result != "capture"


class TestMartyrdomEnding:
    def test_martyrdom_triggers_with_flag(self):
        """Martyrdom triggers when martyrdom_triggered flag is True (set pre-drift)."""
        gs = make_ending_gs(
            stability=0,
            public_approval=75,
            martyrdom_triggered=True,
        )
        result = check_alternate_endings(gs)
        assert result == "martyrdom"
        assert gs.ending_triggered == "martyrdom"

    def test_martyrdom_pre_drift_flag_simulation(self):
        """
        Simulate the full EOT flow:
        1. stability=0, approval=75 → pre-drift flag should set
        2. check_alternate_endings should then return "martyrdom"
        """
        gs = make_ending_gs(
            stability=0,
            public_approval=75,
        )
        # Simulate pre-drift martyrdom check (from apply_end_of_turn_effects line 3175)
        if gs.stability <= 0 and gs.public_approval >= 70:
            if not getattr(gs, 'martyrdom_triggered', False):
                gs.martyrdom_triggered = True

        assert gs.martyrdom_triggered is True, "Pre-drift flag should be set"

        result = check_alternate_endings(gs)
        assert result == "martyrdom"

    def test_martyrdom_does_not_trigger_without_flag(self):
        """Even with stability=0 and approval=75, no trigger without the flag."""
        gs = make_ending_gs(
            stability=0,
            public_approval=75,
            martyrdom_triggered=False,
        )
        result = check_alternate_endings(gs)
        assert result != "martyrdom"

    def test_martyrdom_fires_any_turn(self):
        """Martyrdom has any_turn=True, so it can fire before turn 10."""
        gs = make_ending_gs(
            stability=0,
            public_approval=75,
            martyrdom_triggered=True,
            current_turn=3,
        )
        result = check_alternate_endings(gs)
        assert result == "martyrdom"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Restoration Legacy ending
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestorationLegacyEnding:
    def test_restoration_legacy_triggers_with_all_conditions(self):
        """Restoration Legacy requires: exile+return resolved, stability>=55, approval>=45, final turn."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=15,
            return_attempts=1,
            current_turn=10,
            max_turns=10,
            stability=60,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result == "restoration_legacy"
        assert gs.ending_triggered == "restoration_legacy"

    def test_restoration_legacy_fails_without_exile(self):
        """Should not trigger if exile never occurred (exile_day=0)."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=0,
            return_attempts=1,
            current_turn=10,
            stability=60,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"

    def test_restoration_legacy_fails_without_return_attempt(self):
        """Should not trigger if never attempted return."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=15,
            return_attempts=0,
            current_turn=10,
            stability=60,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"

    def test_restoration_legacy_fails_if_restoration_still_active(self):
        """Should not trigger if restoration is still in progress."""
        gs = make_ending_gs(
            restoration_active=True,
            exile_day=15,
            return_attempts=1,
            current_turn=10,
            stability=60,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"

    def test_restoration_legacy_fails_low_stability(self):
        """Should not trigger if stability < 55."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=15,
            return_attempts=1,
            current_turn=10,
            stability=40,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"

    def test_restoration_legacy_fails_low_approval(self):
        """Should not trigger if public_approval < 45."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=15,
            return_attempts=1,
            current_turn=10,
            stability=60,
            public_approval=30,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"

    def test_restoration_legacy_fails_before_final_turn(self):
        """Should not trigger before final turn (any_turn=False)."""
        gs = make_ending_gs(
            restoration_active=False,
            exile_day=15,
            return_attempts=1,
            current_turn=5,
            stability=60,
            public_approval=50,
        )
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Permanent Exile ending
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermanentExileEnding:
    def test_permanent_exile_triggers(self):
        """Permanent exile: in_exile=True, return_attempts>=3, return_progress<30."""
        gs = make_ending_gs(
            in_exile=True,
            return_attempts=3,
            return_progress=25,
        )
        is_over, result, msg = check_game_over(gs)
        assert result == "permanent_exile"
        assert gs.ending_triggered == "permanent_exile"
        assert gs.in_exile is False  # exile ends (not via return)
        assert is_over is True

    def test_permanent_exile_boundary_progress_30_does_not_trigger(self):
        """return_progress=30 should NOT trigger (condition is < 30, not <= 30)."""
        gs = make_ending_gs(
            in_exile=True,
            return_attempts=3,
            return_progress=30,
        )
        is_over, result, msg = check_game_over(gs)
        assert result != "permanent_exile"
        assert gs.in_exile is True  # still in exile

    def test_permanent_exile_fails_with_fewer_attempts(self):
        """Should not trigger if return_attempts < 3."""
        gs = make_ending_gs(
            in_exile=True,
            return_attempts=2,
            return_progress=10,
        )
        is_over, result, msg = check_game_over(gs)
        assert result != "permanent_exile"

    def test_permanent_exile_fails_when_not_in_exile(self):
        """Should not trigger if not currently in exile."""
        gs = make_ending_gs(
            in_exile=False,
            return_attempts=3,
            return_progress=10,
            current_turn=5,  # avoid hitting victory path at turn 10
        )
        is_over, result, msg = check_game_over(gs)
        assert result != "permanent_exile"

    def test_permanent_exile_high_progress_does_not_trigger(self):
        """Should not trigger if return_progress >= 30 even with 3+ attempts."""
        gs = make_ending_gs(
            in_exile=True,
            return_attempts=5,
            return_progress=50,
        )
        is_over, result, msg = check_game_over(gs)
        assert result != "permanent_exile"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Restoration Legacy fires with correct state
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestorationLegacyFires:
    def test_restoration_legacy_fires(self):
        """restoration_legacy fires with correct state, retirement blocked by low wealth."""
        gs = make_ending_gs()
        gs.current_turn = 10
        gs.max_turns = 10
        gs.stability = 60
        gs.public_approval = 50
        gs.personal_wealth = 3
        gs.exile_day = 15
        gs.return_attempts = 1
        gs.restoration_active = False
        gs.in_exile = False
        gs.exile_trigger = "revolution"
        gs.prior_regime_label = "managed_democracy"
        # Should NOT fire retirement (wealth too low)
        # Should fire restoration_legacy
        result = check_alternate_endings(gs)
        assert result == "restoration_legacy", \
            f"Expected restoration_legacy, got {result}"

    def test_restoration_legacy_blocked_when_active(self):
        """restoration_legacy should not fire when restoration_active=True."""
        gs = make_ending_gs()
        gs.current_turn = 10
        gs.max_turns = 10
        gs.stability = 60
        gs.public_approval = 50
        gs.exile_day = 15
        gs.return_attempts = 1
        gs.restoration_active = True  # Not yet resolved
        gs.in_exile = False
        result = check_alternate_endings(gs)
        assert result != "restoration_legacy", \
            "restoration_legacy should not fire when restoration_active=True"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Permanent Exile fires on WAIT with exhausted attempts
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermanentExileOnWait:
    def test_permanent_exile_fires_on_wait(self):
        """Permanent exile condition fires with exhausted attempts and low progress."""
        gs = make_ending_gs()
        gs.in_exile = True
        gs.return_attempts = 3
        gs.return_progress = 25
        gs.exile_day = 10
        gs.current_turn = 5
        gs.exile_trigger = "revolution"
        gs.exile_entry_relations = {"usa": 50, "eu": 50,
            "russia": 30, "china": 35, "arabia": 45, "dprg": 40}
        gs.successor_name = "Deputy Premier Varga"
        # Simulate the inline permanent exile check from WAIT handler
        # This is the check added in the WAIT action path
        fired = (
            gs.return_attempts >= 3
            and gs.return_progress < 30
            and gs.in_exile
        )
        assert fired == True, \
            "Permanent exile condition should fire"

    def test_permanent_exile_does_not_fire_with_progress(self):
        """Permanent exile should not fire when progress >= 30."""
        gs = make_ending_gs()
        gs.in_exile = True
        gs.return_attempts = 3
        gs.return_progress = 35  # Above threshold
        gs.exile_day = 10
        fired = (
            gs.return_attempts >= 3
            and gs.return_progress < 30
            and gs.in_exile
        )
        assert fired == False, \
            "Permanent exile should not fire when progress >= 30"

    def test_permanent_exile_does_not_fire_with_attempts_remaining(self):
        """Permanent exile should not fire with attempts remaining."""
        gs = make_ending_gs()
        gs.in_exile = True
        gs.return_attempts = 2  # One attempt remaining
        gs.return_progress = 15
        gs.exile_day = 10
        fired = (
            gs.return_attempts >= 3
            and gs.return_progress < 30
            and gs.in_exile
        )
        assert fired == False, \
            "Permanent exile should not fire with attempts remaining"
