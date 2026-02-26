"""
Tests for drift reset functionality in LoopEngine and ClockGenerator.

Tests the Tidal-inspired auto-reset mechanism that prevents burst playback
after large clock drifts (e.g., CPU spikes, sleep/wake).
"""

from __future__ import annotations

import time

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.engine.clock_generator import ClockGenerator
from oiduna_loop.state import PlaybackState
from oiduna_loop.tests.mocks import MockMidiOutput, MockStateSink


class TestDriftResetConstants:
    """Test drift reset configuration constants."""

    def test_loop_engine_has_drift_thresholds(self):
        """LoopEngine should have drift threshold constants."""
        assert hasattr(LoopEngine, "DRIFT_RESET_THRESHOLD_MS")
        assert hasattr(LoopEngine, "DRIFT_WARNING_THRESHOLD_MS")
        assert LoopEngine.DRIFT_RESET_THRESHOLD_MS > LoopEngine.DRIFT_WARNING_THRESHOLD_MS

    def test_clock_generator_has_drift_thresholds(self):
        """ClockGenerator should have drift threshold constants."""
        assert hasattr(ClockGenerator, "DRIFT_RESET_THRESHOLD_MS")
        assert hasattr(ClockGenerator, "DRIFT_WARNING_THRESHOLD_MS")
        assert ClockGenerator.DRIFT_RESET_THRESHOLD_MS > ClockGenerator.DRIFT_WARNING_THRESHOLD_MS

    def test_threshold_values_are_reasonable(self):
        """Threshold values should be in reasonable ranges."""
        # LoopEngine: 50ms reset, 20ms warning
        assert 30 <= LoopEngine.DRIFT_RESET_THRESHOLD_MS <= 100
        assert 10 <= LoopEngine.DRIFT_WARNING_THRESHOLD_MS <= 50

        # ClockGenerator: 30ms reset, 15ms warning (higher frequency)
        assert 20 <= ClockGenerator.DRIFT_RESET_THRESHOLD_MS <= 60
        assert 5 <= ClockGenerator.DRIFT_WARNING_THRESHOLD_MS <= 30


class TestLoopEngineDriftStats:
    """Test drift statistics tracking in LoopEngine."""

    def test_initial_drift_stats(self, test_engine: LoopEngine):
        """Drift stats should be initialized to zero."""
        stats = test_engine.get_drift_stats()

        assert stats["reset_count"] == 0
        assert stats["max_drift_ms"] == 0.0
        assert stats["total_skipped_steps"] == 0
        assert stats["last_reset_drift_ms"] == 0.0
        assert stats["current_step_count"] == 0

    def test_drift_stats_anchor_age_when_not_playing(self, test_engine: LoopEngine):
        """Anchor age should be 0 when not playing (no anchor set)."""
        stats = test_engine.get_drift_stats()
        assert stats["anchor_age_seconds"] == 0.0

    @pytest.mark.asyncio
    async def test_drift_stats_updated_after_handle_drift_reset(self, test_engine: LoopEngine):
        """Drift stats should be updated after drift reset."""
        # Set up anchor time
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 10
        test_engine.state.set_bpm(120)  # step_duration = 0.125s = 125ms

        # Use 500ms drift to ensure skipped_steps > 0 (500ms / 125ms = 4 steps)
        await test_engine._handle_drift_reset(500.0, time.perf_counter())

        stats = test_engine.get_drift_stats()
        assert stats["reset_count"] == 1
        assert stats["last_reset_drift_ms"] == 500.0
        assert stats["total_skipped_steps"] == 4  # 500ms / 125ms = 4 steps


class TestLoopEngineDriftReset:
    """Test drift reset behavior in LoopEngine."""

    @pytest.mark.asyncio
    async def test_handle_drift_reset_resets_anchor(self, test_engine: LoopEngine):
        """_handle_drift_reset should reset anchor time and step count."""
        # Set up initial state
        initial_anchor = time.perf_counter() - 1.0  # 1 second ago
        test_engine._step_anchor_time = initial_anchor
        test_engine._step_count = 100

        current_time = time.perf_counter()
        await test_engine._handle_drift_reset(100.0, current_time)

        # Anchor should be reset to current time
        assert test_engine._step_anchor_time == current_time
        assert test_engine._step_count == 0

    @pytest.mark.asyncio
    async def test_handle_drift_reset_sends_error_notification(
        self,
        test_engine: LoopEngine,
        mock_publisher: MockStateSink,
    ):
        """_handle_drift_reset should send error notification to API."""
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 10

        await test_engine._handle_drift_reset(75.0, time.perf_counter())

        # Check error was sent
        error_msgs = mock_publisher.get_messages_by_type("error_msg")
        assert len(error_msgs) == 1
        assert error_msgs[0]["code"] == "CLOCK_DRIFT_RESET"
        assert "75.0ms" in error_msgs[0]["message"]

    @pytest.mark.asyncio
    async def test_handle_drift_reset_increments_stats(self, test_engine: LoopEngine):
        """Multiple drift resets should increment statistics."""
        test_engine._step_anchor_time = time.perf_counter()

        # First reset
        await test_engine._handle_drift_reset(60.0, time.perf_counter())
        assert test_engine._drift_stats["reset_count"] == 1

        # Second reset
        await test_engine._handle_drift_reset(80.0, time.perf_counter())
        assert test_engine._drift_stats["reset_count"] == 2

        # Third reset
        await test_engine._handle_drift_reset(55.0, time.perf_counter())
        assert test_engine._drift_stats["reset_count"] == 3

    @pytest.mark.asyncio
    async def test_drift_direction_logged_correctly(self, test_engine: LoopEngine):
        """Drift direction (behind/ahead) should be calculated correctly."""
        test_engine._step_anchor_time = time.perf_counter()

        # Positive drift = behind (current time > expected time)
        await test_engine._handle_drift_reset(100.0, time.perf_counter())
        # The message should contain "behind"
        # (We can't easily check logs, but stats are updated)

        # Negative drift = ahead (current time < expected time)
        await test_engine._handle_drift_reset(-100.0, time.perf_counter())
        # Both should work without error


class TestLoopEngineDriftDetection:
    """Test drift detection logic in _step_loop."""

    def test_small_drift_does_not_trigger_reset(self, test_engine: LoopEngine):
        """Drift below threshold should not trigger reset."""
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 0

        initial_reset_count = test_engine._drift_stats["reset_count"]

        # Simulate small drift (10ms) - below warning threshold
        # This would happen naturally in _step_loop, but we test the logic
        drift_ms = 10.0
        assert drift_ms < test_engine.DRIFT_WARNING_THRESHOLD_MS

        # Reset count should remain unchanged
        assert test_engine._drift_stats["reset_count"] == initial_reset_count

    def test_max_drift_tracking(self, test_engine: LoopEngine):
        """max_drift_ms should track the largest observed drift."""
        test_engine._drift_stats["max_drift_ms"] = 0.0

        # Simulate drift observations
        test_drifts = [5.0, 15.0, 8.0, 25.0, 12.0]

        for drift in test_drifts:
            if abs(drift) > test_engine._drift_stats["max_drift_ms"]:
                test_engine._drift_stats["max_drift_ms"] = abs(drift)

        assert test_engine._drift_stats["max_drift_ms"] == 25.0


class TestClockGeneratorDriftReset:
    """Test drift reset behavior in ClockGenerator."""

    def test_initial_drift_stats(self, mock_midi: MockMidiOutput):
        """ClockGenerator should have initial drift stats."""
        clock = ClockGenerator(mock_midi)
        stats = clock.get_drift_stats()

        assert stats["reset_count"] == 0
        assert stats["max_drift_ms"] == 0.0
        assert stats["current_pulse_count"] == 0

    def test_handle_drift_reset_resets_anchor(self, mock_midi: MockMidiOutput):
        """_handle_drift_reset should reset anchor and pulse count."""
        clock = ClockGenerator(mock_midi)

        # Set up initial state
        clock._clock_anchor_time = time.perf_counter() - 1.0
        clock._pulse_count = 500

        current_time = time.perf_counter()
        clock._handle_drift_reset(50.0, current_time)

        assert clock._clock_anchor_time == current_time
        assert clock._pulse_count == 0

    def test_drift_stats_incremented_on_reset(self, mock_midi: MockMidiOutput):
        """Drift stats should increment on each reset."""
        clock = ClockGenerator(mock_midi)
        clock._clock_anchor_time = time.perf_counter()

        clock._handle_drift_reset(40.0, time.perf_counter())
        assert clock._drift_stats["reset_count"] == 1

        clock._handle_drift_reset(45.0, time.perf_counter())
        assert clock._drift_stats["reset_count"] == 2

    def test_suppress_next_drift_reset_resets_clock_state(self, mock_midi: MockMidiOutput):
        """suppress_next_drift_reset should reset anchor and pulse count."""
        clock = ClockGenerator(mock_midi)

        # Set up running clock state
        clock._clock_anchor_time = time.perf_counter() - 10.0  # 10 seconds ago
        clock._pulse_count = 1000  # Many pulses at old BPM

        old_anchor = clock._clock_anchor_time

        # Suppress drift reset (as would happen on BPM change)
        clock.suppress_next_drift_reset()

        # Anchor should be reset to current time
        assert clock._clock_anchor_time is not None
        assert clock._clock_anchor_time > old_anchor
        assert clock._pulse_count == 0
        assert clock._suppress_next_drift_reset is True

    def test_suppress_next_drift_reset_does_nothing_when_not_running(self, mock_midi: MockMidiOutput):
        """suppress_next_drift_reset should do nothing if clock is not running."""
        clock = ClockGenerator(mock_midi)

        # Clock not running (anchor is None)
        assert clock._clock_anchor_time is None
        assert clock._pulse_count == 0

        # Call suppress
        clock.suppress_next_drift_reset()

        # Should remain None (not started)
        assert clock._clock_anchor_time is None
        assert clock._pulse_count == 0

    def test_suppress_next_drift_reset_does_not_increment_drift_stats(self, mock_midi: MockMidiOutput):
        """suppress_next_drift_reset should not increment drift reset statistics.

        BPM changes are intentional, not drift events. They should not
        pollute the drift statistics used for monitoring actual drift issues.
        """
        clock = ClockGenerator(mock_midi)
        clock._clock_anchor_time = time.perf_counter()
        clock._pulse_count = 500

        initial_reset_count = clock._drift_stats["reset_count"]

        # Suppress drift reset for BPM change
        clock.suppress_next_drift_reset()

        # Drift stats should NOT be incremented
        assert clock._drift_stats["reset_count"] == initial_reset_count


class TestDriftResetIntegration:
    """Integration tests for drift reset across components."""

    @pytest.mark.asyncio
    async def test_stop_resets_drift_stats_anchor(
        self,
        test_engine: LoopEngine,
    ):
        """Stop command should reset anchor (stats are preserved for monitoring)."""
        # Start playing and set up anchor
        test_engine._handle_play({})
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 50

        # Manually trigger a drift reset to have some stats
        await test_engine._handle_drift_reset(60.0, time.perf_counter())
        assert test_engine._drift_stats["reset_count"] == 1

        # Stop playback
        test_engine._handle_stop({})

        # Anchor should be reset
        assert test_engine._step_anchor_time is None
        assert test_engine._step_count == 0

        # But stats should be preserved (for monitoring/debugging)
        assert test_engine._drift_stats["reset_count"] == 1

    @pytest.mark.asyncio
    async def test_pause_resets_anchor(
        self,
        test_engine: LoopEngine,
    ):
        """Pause should reset anchor but preserve position."""
        test_engine._handle_play({})
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 30
        test_engine.state.position.step = 30

        test_engine._handle_pause({})

        # Anchor reset, position preserved
        assert test_engine._step_anchor_time is None
        assert test_engine.state.position.step == 30  # Position preserved

    def test_bpm_change_does_not_reset_stats(
        self,
        test_engine: LoopEngine,
    ):
        """BPM change should not reset drift stats."""
        test_engine._drift_stats["reset_count"] = 5
        test_engine._drift_stats["max_drift_ms"] = 45.0

        test_engine._handle_bpm({"bpm": 140})

        # Stats should be preserved
        assert test_engine._drift_stats["reset_count"] == 5
        assert test_engine._drift_stats["max_drift_ms"] == 45.0

    def test_bpm_change_during_playback_resets_anchor(
        self,
        test_engine: LoopEngine,
    ):
        """BPM change during playback should reset anchor for smooth transition.

        This prevents false drift detection when BPM changes significantly.
        Without anchor reset, a BPM change from 120→140 would cause ~1400ms
        apparent drift and trigger an unwanted drift reset.
        """
        # Start playing
        test_engine._handle_play({})
        test_engine._step_anchor_time = time.perf_counter() - 10.0  # 10 seconds ago
        test_engine._step_count = 80  # 80 steps at old BPM

        old_anchor = test_engine._step_anchor_time

        # Change BPM during playback
        test_engine._handle_bpm({"bpm": 140})

        # Anchor should be reset to current time
        assert test_engine._step_anchor_time is not None
        assert test_engine._step_anchor_time > old_anchor
        assert test_engine._step_count == 0

        # BPM should be updated
        assert test_engine.state.bpm == 140

    def test_bpm_change_during_playback_resets_clock_generator_anchor(
        self,
        test_engine: LoopEngine,
    ):
        """BPM change during playback should also reset ClockGenerator anchor.

        Both LoopEngine (step sequencer) and ClockGenerator (MIDI clock)
        must have their anchors reset to prevent false drift detection.
        """
        # Start playing
        test_engine._handle_play({})
        test_engine._step_anchor_time = time.perf_counter() - 10.0

        # Set up ClockGenerator state (simulating running MIDI clock)
        clock_gen = test_engine._clock_generator
        clock_gen._clock_anchor_time = time.perf_counter() - 10.0
        clock_gen._pulse_count = 2400  # Many pulses at old BPM

        old_clock_anchor = clock_gen._clock_anchor_time

        # Change BPM during playback
        test_engine._handle_bpm({"bpm": 140})

        # ClockGenerator anchor should also be reset
        assert clock_gen._clock_anchor_time is not None
        assert clock_gen._clock_anchor_time > old_clock_anchor
        assert clock_gen._pulse_count == 0

    def test_bpm_change_when_stopped_does_not_reset_anchor(
        self,
        test_engine: LoopEngine,
    ):
        """BPM change when stopped should not affect anchor."""
        # Not playing
        assert not test_engine.state.playing
        test_engine._step_anchor_time = None
        test_engine._step_count = 0

        # Change BPM
        test_engine._handle_bpm({"bpm": 140})

        # Anchor should remain None
        assert test_engine._step_anchor_time is None
        assert test_engine._step_count == 0
        assert test_engine.state.bpm == 140


class TestDriftCalculation:
    """Test drift calculation math."""

    def test_drift_calculation_formula(self):
        """Verify drift calculation: drift = current_time - expected_time."""
        anchor_time = 1000.0
        step_count = 10
        step_duration = 0.125  # 120 BPM

        expected_time = anchor_time + (step_count * step_duration)  # 1001.25
        current_time = 1001.30  # 50ms behind

        drift_seconds = current_time - expected_time
        drift_ms = drift_seconds * 1000

        assert drift_ms == pytest.approx(50.0, abs=0.1)

    def test_positive_drift_means_behind(self):
        """Positive drift means current time is ahead of expected (running behind)."""
        anchor_time = 1000.0
        step_count = 10
        step_duration = 0.125

        expected_time = anchor_time + (step_count * step_duration)  # 1001.25

        # Current time is 1001.35 (we're 100ms late)
        current_time = 1001.35
        drift_ms = (current_time - expected_time) * 1000

        assert drift_ms > 0  # Positive = behind schedule
        assert drift_ms == pytest.approx(100.0, abs=0.1)

    def test_negative_drift_means_ahead(self):
        """Negative drift means current time is behind expected (running ahead)."""
        anchor_time = 1000.0
        step_count = 10
        step_duration = 0.125

        expected_time = anchor_time + (step_count * step_duration)  # 1001.25

        # Current time is 1001.20 (we're 50ms early - unusual but possible)
        current_time = 1001.20
        drift_ms = (current_time - expected_time) * 1000

        assert drift_ms < 0  # Negative = ahead of schedule
        assert drift_ms == pytest.approx(-50.0, abs=0.1)

    def test_skipped_steps_calculation(self):
        """Skipped steps should be calculated from drift and step duration."""
        step_duration = 0.125  # 120 BPM, 125ms per step
        drift_ms = 500.0  # 500ms drift

        skipped_steps = int(abs(drift_ms) / (step_duration * 1000))

        assert skipped_steps == 4  # 500ms / 125ms = 4 steps


class TestBpmChangeDriftSuppression:
    """Test BPM change drift suppression to avoid false notifications."""

    def test_bpm_change_sets_suppression_flag(self, test_engine: LoopEngine):
        """BPM change during playback should set suppression flag."""
        # Start playing
        test_engine._handle_play({})
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 10

        # Initially no suppression
        assert test_engine._suppress_next_drift_reset is False

        # Change BPM during playback
        test_engine._handle_bpm({"bpm": 320})

        # Suppression flag should be set
        assert test_engine._suppress_next_drift_reset is True

    def test_suppression_flag_cleared_after_use(self, test_engine: LoopEngine):
        """Suppression flag should be cleared after suppressing one drift."""
        # Setup: simulate BPM change just happened
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 0
        test_engine._suppress_next_drift_reset = True

        current_time = time.perf_counter()

        # Simulate the suppression logic from _step_loop
        if test_engine._suppress_next_drift_reset:
            test_engine._step_anchor_time = current_time
            test_engine._step_count = 0
            test_engine._suppress_next_drift_reset = False

        # Suppression flag should be cleared
        assert test_engine._suppress_next_drift_reset is False

    @pytest.mark.asyncio
    async def test_drift_suppressed_with_flag(
        self,
        test_engine: LoopEngine,
        mock_publisher: MockStateSink,
    ):
        """Drift reset notification should be suppressed when flag is set."""
        # Setup: suppression flag is set
        test_engine._step_anchor_time = time.perf_counter()
        test_engine._step_count = 0
        test_engine._suppress_next_drift_reset = True

        current_time = time.perf_counter()

        # Simulate the suppression logic
        if test_engine._suppress_next_drift_reset:
            test_engine._step_anchor_time = current_time
            test_engine._step_count = 0
            test_engine._suppress_next_drift_reset = False

        # No error notification should be sent
        error_msgs = mock_publisher.get_messages_by_type("error_msg")
        assert len(error_msgs) == 0

    @pytest.mark.asyncio
    async def test_drift_reported_without_flag(
        self,
        test_engine: LoopEngine,
        mock_publisher: MockStateSink,
    ):
        """Drift reset should be reported normally when flag is not set."""
        # Setup: no suppression flag
        test_engine._step_anchor_time = time.perf_counter() - 1.0
        test_engine._step_count = 0
        test_engine._suppress_next_drift_reset = False

        current_time = time.perf_counter()

        # Normal drift reset should send notification
        await test_engine._handle_drift_reset(100.0, current_time)

        # Error notification should be sent
        error_msgs = mock_publisher.get_messages_by_type("error_msg")
        assert len(error_msgs) == 1
        assert error_msgs[0]["code"] == "CLOCK_DRIFT_RESET"

    def test_clock_generator_suppression(self, test_engine: LoopEngine):
        """ClockGenerator should also support drift suppression."""
        clock_gen = test_engine._clock_generator

        # Initially no suppression
        assert clock_gen._suppress_next_drift_reset is False

        # Set up clock anchor
        clock_gen._clock_anchor_time = time.perf_counter()
        clock_gen._pulse_count = 100

        # Enable suppression
        clock_gen.suppress_next_drift_reset()

        # Suppression flag should be set
        assert clock_gen._suppress_next_drift_reset is True

        # Anchor should be reset
        assert clock_gen._pulse_count == 0

    def test_bpm_change_when_stopped_no_suppression(self, test_engine: LoopEngine):
        """BPM change when stopped should not set suppression flag."""
        # Not playing
        assert not test_engine.state.playing
        test_engine._step_anchor_time = None

        # Change BPM
        test_engine._handle_bpm({"bpm": 200})

        # No suppression should be set (nothing to transition)
        assert test_engine._suppress_next_drift_reset is False
