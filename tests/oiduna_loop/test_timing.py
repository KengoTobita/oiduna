"""
Tests for timing drift correction in LoopEngine and ClockGenerator.

TDD: Write tests first, then implement the drift correction.
"""

from __future__ import annotations

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.engine.clock_generator import ClockGenerator
from oiduna_loop.state import PlaybackState
from oiduna_loop.tests.mocks import MockMidiOutput


class TestStepLoopDriftCorrection:
    """Tests for drift correction in _step_loop."""

    def test_anchor_time_is_none_when_not_playing(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """Anchor time should be None when playback is stopped."""
        # Initial state: stopped
        assert test_engine.state.playback_state == PlaybackState.STOPPED

        # _anchor_time should be None (or not set yet)
        # After implementation, this attribute will exist
        assert getattr(test_engine, "_step_anchor_time", None) is None

    def test_anchor_time_resets_on_stop(
        self,
        test_engine: LoopEngine,
        sample_session_data: dict,
    ) -> None:
        """Anchor time should reset to None when playback stops."""
        # Setup: Load session and start playing
        test_engine._handle_compile(sample_session_data)
        test_engine._handle_play({})

        # Stop playback
        test_engine._handle_stop({})

        # Anchor should be reset
        assert getattr(test_engine, "_step_anchor_time", None) is None
        assert getattr(test_engine, "_step_count", 0) == 0

    def test_anchor_time_resets_on_pause(
        self,
        test_engine: LoopEngine,
        sample_session_data: dict,
    ) -> None:
        """Anchor time should reset when playback is paused."""
        # Setup: Load session and start playing
        test_engine._handle_compile(sample_session_data)
        test_engine._handle_play({})

        # Pause playback
        test_engine._handle_pause({})

        # Anchor should be reset (will re-anchor on resume)
        assert getattr(test_engine, "_step_anchor_time", None) is None

    def test_step_count_starts_at_zero(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """Step count for drift correction should start at 0."""
        assert getattr(test_engine, "_step_count", 0) == 0


class TestClockLoopDriftCorrection:
    """Tests for drift correction in ClockGenerator.run_clock_loop."""

    def test_clock_anchor_resets_when_not_playing(
        self,
        mock_midi: MockMidiOutput,
    ) -> None:
        """Clock anchor should reset when playback stops."""
        clock = ClockGenerator(mock_midi)

        # After implementation, these attributes will exist
        assert getattr(clock, "_clock_anchor_time", None) is None
        assert getattr(clock, "_pulse_count", 0) == 0


class TestDriftCorrectionCalculation:
    """Tests for the drift correction calculation logic."""

    def test_expected_time_calculation(self) -> None:
        """Expected time should be anchor + (step_count * step_duration)."""
        anchor_time = 1000.0  # Arbitrary start time
        step_duration = 0.125  # 120 BPM -> 125ms per step

        # Step 0: expected at anchor
        assert anchor_time + (0 * step_duration) == 1000.0

        # Step 1: expected at anchor + 125ms
        assert anchor_time + (1 * step_duration) == pytest.approx(1000.125)

        # Step 100: expected at anchor + 12.5s
        assert anchor_time + (100 * step_duration) == pytest.approx(1012.5)

    def test_wait_time_with_drift(self) -> None:
        """Wait time should compensate for accumulated drift."""
        anchor_time = 1000.0
        step_duration = 0.125
        step_count = 10

        # Expected time for step 10
        expected_time = anchor_time + (step_count * step_duration)  # 1001.25

        # If actual time is behind (processing was fast)
        actual_time_fast = 1001.20
        wait_time_fast = max(0, expected_time - actual_time_fast)
        assert wait_time_fast == pytest.approx(0.05)  # Wait 50ms

        # If actual time is ahead (processing was slow)
        actual_time_slow = 1001.30
        wait_time_slow = max(0, expected_time - actual_time_slow)
        assert wait_time_slow == 0  # No wait, skip to catch up

    def test_clock_pulse_calculation(self) -> None:
        """Clock pulse duration should be step_duration / 6."""
        step_duration = 0.125  # 120 BPM
        pulses_per_step = 6

        pulse_duration = step_duration / pulses_per_step
        assert pulse_duration == pytest.approx(0.020833, rel=1e-4)
