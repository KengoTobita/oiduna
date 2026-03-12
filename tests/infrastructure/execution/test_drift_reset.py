"""
Tests for drift reset functionality in LoopEngine and ClockGenerator.

Tests the Tidal-inspired auto-reset mechanism that prevents burst playback
after large clock drifts (e.g., CPU spikes, sleep/wake).
"""

from __future__ import annotations

import time

import pytest

from oiduna.infrastructure.execution import LoopEngine, PlaybackState
from oiduna.infrastructure.execution.clock_generator import ClockGenerator
from .mocks import MockMidiOutput, MockStateProducer


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


class TestClockGeneratorDriftReset:
    """Test drift reset behavior in ClockGenerator."""

    def test_initial_drift_stats(self, mock_midi: MockMidiOutput):
        """ClockGenerator should have initial drift stats."""
        clock = ClockGenerator(mock_midi)
        stats = clock.get_drift_stats()

        assert stats["reset_count"] == 0
        assert stats["max_drift_ms"] == 0.0
        assert stats["current_pulse_count"] == 0


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
