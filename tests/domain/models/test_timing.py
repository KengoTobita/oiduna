"""Tests for timing type definitions and conversion utilities."""

import pytest
from oiduna.domain.models.timing import (
    StepNumber,
    BeatNumber,
    BarNumber,
    BPM,
    Milliseconds,
    step_to_beat,
    step_to_bar,
    bpm_to_step_duration_ms,
    bpm_to_loop_duration_ms,
)


class TestStepToBeat:
    """Test step to beat conversion."""

    def test_step_0_to_beat(self):
        """Step 0 should map to beat 0."""
        assert step_to_beat(StepNumber(0)) == BeatNumber(0)

    def test_step_4_to_beat(self):
        """Step 4 should map to beat 1."""
        assert step_to_beat(StepNumber(4)) == BeatNumber(1)

    def test_step_16_to_beat(self):
        """Step 16 should map to beat 4."""
        assert step_to_beat(StepNumber(16)) == BeatNumber(4)

    def test_step_64_to_beat(self):
        """Step 64 should wrap to beat 0 (64 // 4 = 16, 16 % 16 = 0)."""
        assert step_to_beat(StepNumber(64)) == BeatNumber(0)


class TestStepToBar:
    """Test step to bar conversion."""

    def test_step_0_to_bar(self):
        """Step 0 should map to bar 0."""
        assert step_to_bar(StepNumber(0)) == BarNumber(0)

    def test_step_16_to_bar(self):
        """Step 16 should map to bar 1."""
        assert step_to_bar(StepNumber(16)) == BarNumber(1)

    def test_step_32_to_bar(self):
        """Step 32 should map to bar 2."""
        assert step_to_bar(StepNumber(32)) == BarNumber(2)

    def test_step_48_to_bar(self):
        """Step 48 should map to bar 3."""
        assert step_to_bar(StepNumber(48)) == BarNumber(3)

    def test_step_64_to_bar(self):
        """Step 64 should wrap to bar 0 (64 // 16 = 4, 4 % 4 = 0)."""
        assert step_to_bar(StepNumber(64)) == BarNumber(0)


class TestBPMToStepDuration:
    """Test BPM to step duration conversion."""

    def test_bpm_120_step_duration(self):
        """At 120 BPM, 1 step should be 125ms."""
        assert bpm_to_step_duration_ms(BPM(120)) == Milliseconds(125)

    def test_bpm_60_step_duration(self):
        """At 60 BPM, 1 step should be 250ms."""
        assert bpm_to_step_duration_ms(BPM(60)) == Milliseconds(250)

    def test_bpm_180_step_duration(self):
        """At 180 BPM, 1 step should be ~83ms."""
        assert bpm_to_step_duration_ms(BPM(180)) == Milliseconds(83)

    def test_bpm_240_step_duration(self):
        """At 240 BPM, 1 step should be ~62ms."""
        result = bpm_to_step_duration_ms(BPM(240))
        assert 62 <= result <= 63


class TestBPMToLoopDuration:
    """Test BPM to loop duration conversion."""

    def test_bpm_120_loop_duration(self):
        """At 120 BPM, 1 loop (256 steps) should be 32000ms (32 seconds)."""
        assert bpm_to_loop_duration_ms(BPM(120)) == Milliseconds(32000)

    def test_bpm_60_loop_duration(self):
        """At 60 BPM, 1 loop should be 64000ms (64 seconds)."""
        assert bpm_to_loop_duration_ms(BPM(60)) == Milliseconds(64000)

    def test_bpm_180_loop_duration(self):
        """At 180 BPM, 1 loop should be ~21333ms (~21.3 seconds)."""
        result = bpm_to_loop_duration_ms(BPM(180))
        assert 21333 <= result <= 21334


class TestTypeSafety:
    """Test that NewType provides type safety (documentation only).

    Note: These tests document the intended usage. mypy will catch
    type errors at static analysis time, not at runtime.
    """

    def test_newtype_runtime_behavior(self):
        """NewType has no runtime effect - values are still int/float."""
        step = StepNumber(42)
        assert isinstance(step, int)
        assert step == 42

    def test_conversion_functions_accept_newtypes(self):
        """Conversion functions work with NewType values."""
        bpm = BPM(120)
        duration = bpm_to_step_duration_ms(bpm)
        assert isinstance(duration, int)
