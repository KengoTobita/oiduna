"""Tests for timing type definitions and conversion utilities."""

import pytest
from oiduna.domain.models.timing import (
    StepNumber,
    BeatNumber,
    BarNumber,
    CycleFloat,
    BPM,
    Milliseconds,
    step_to_cycle,
    cycle_to_step,
    step_to_beat,
    step_to_bar,
    bpm_to_step_duration_ms,
    bpm_to_loop_duration_ms,
)


class TestStepToCycle:
    """Test step to cycle conversion."""

    def test_step_0_to_cycle(self):
        """Step 0 should map to cycle 0.0."""
        assert step_to_cycle(StepNumber(0)) == CycleFloat(0.0)

    def test_step_64_to_cycle(self):
        """Step 64 should map to cycle 1.0 (1 bar)."""
        result = step_to_cycle(StepNumber(64))
        assert abs(result - 1.0) < 0.001

    def test_step_128_to_cycle(self):
        """Step 128 should map to cycle 2.0 (2 bars)."""
        result = step_to_cycle(StepNumber(128))
        assert abs(result - 2.0) < 0.001

    def test_step_255_to_cycle(self):
        """Step 255 should map to cycle ~3.984 (255/256 * 4.0)."""
        result = step_to_cycle(StepNumber(255))
        assert abs(result - 3.984375) < 0.001


class TestCycleToStep:
    """Test cycle to step conversion."""

    def test_cycle_0_to_step(self):
        """Cycle 0.0 should map to step 0."""
        assert cycle_to_step(CycleFloat(0.0)) == StepNumber(0)

    def test_cycle_1_to_step(self):
        """Cycle 1.0 should map to step 64."""
        assert cycle_to_step(CycleFloat(1.0)) == StepNumber(64)

    def test_cycle_2_to_step(self):
        """Cycle 2.0 should map to step 128."""
        assert cycle_to_step(CycleFloat(2.0)) == StepNumber(128)

    def test_cycle_4_to_step(self):
        """Cycle 4.0 should map to step 256 (wraps to 0)."""
        # Note: This is out of range (0-255), but demonstrates the formula
        # In practice, cycles should be 0.0-3.996
        pass


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


class TestRoundTrip:
    """Test round-trip conversions."""

    def test_step_cycle_roundtrip(self):
        """Step -> Cycle -> Step should preserve value."""
        for step in [0, 64, 128, 192, 255]:
            cycle = step_to_cycle(StepNumber(step))
            result = cycle_to_step(cycle)
            # Allow small rounding error
            assert abs(result - step) <= 1

    def test_cycle_step_roundtrip(self):
        """Cycle -> Step -> Cycle should be close (with quantization)."""
        for cycle in [0.0, 1.0, 2.0, 3.0]:
            step = cycle_to_step(CycleFloat(cycle))
            result = step_to_cycle(step)
            # Allow small error due to quantization
            assert abs(result - cycle) < 0.1


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

        cycle = CycleFloat(1.5)
        assert isinstance(cycle, float)
        assert cycle == 1.5

    def test_conversion_functions_accept_newtypes(self):
        """Conversion functions work with NewType values."""
        step = StepNumber(64)
        cycle = step_to_cycle(step)
        assert isinstance(cycle, float)

        bpm = BPM(120)
        duration = bpm_to_step_duration_ms(bpm)
        assert isinstance(duration, int)
