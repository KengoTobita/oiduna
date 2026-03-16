"""Integration tests for swing and micro-timing with offset."""

import pytest
import time
from oiduna.domain.schedule.models import ScheduleEntry


class TestSwingTiming:
    """Test swing timing accuracy with offset values."""

    def test_offset_range_validation(self):
        """Verify offset validation in ScheduleEntry creation."""
        # Valid offsets
        entry1 = ScheduleEntry("test", step=0, offset=0.0, params={})
        assert entry1.offset == 0.0

        entry2 = ScheduleEntry("test", step=0, offset=0.5, params={})
        assert entry2.offset == 0.5

        entry3 = ScheduleEntry("test", step=0, offset=0.999, params={})
        assert entry3.offset == 0.999

    def test_swing_pattern_structure(self):
        """Verify swing pattern (offset=0.5) structure."""
        # Create schedule with swing pattern
        entries = [
            ScheduleEntry("test", step=0, offset=0.0, params={"note": 60}),
            ScheduleEntry("test", step=0, offset=0.5, params={"note": 62}),
        ]

        # Verify both messages at same step, different offsets
        assert entries[0].step == entries[1].step
        assert entries[0].offset == 0.0
        assert entries[1].offset == 0.5

    def test_substep_subdivision(self):
        """Verify sub-step subdivision (triplet-like within one step)."""
        # 3 events within single step (triplet feel)
        entries = [
            ScheduleEntry("test", step=0, offset=0.0, params={"note": 60}),
            ScheduleEntry("test", step=0, offset=0.333, params={"note": 62}),
            ScheduleEntry("test", step=0, offset=0.666, params={"note": 64}),
        ]

        # Verify all at same step
        assert all(e.step == 0 for e in entries)

        # Verify offset progression
        assert entries[0].offset == 0.0
        assert entries[1].offset == 0.333
        assert entries[2].offset == 0.666

    def test_irregular_meter_timing(self):
        """Verify irregular meter (3/4 time) using step+offset."""
        # 3/4 time = 12 steps = 3 beats (in 4/4 grid)
        # Beat positions: 0, 4, 8 steps (quarter notes)
        # But we want 3/4 feel: 0, 5.333, 10.666 steps
        entries = [
            ScheduleEntry("test", step=0, offset=0.0, params={"note": 60}),     # Beat 1 at 0 steps
            ScheduleEntry("test", step=5, offset=0.333, params={"note": 62}),   # Beat 2 at 5.333 steps
            ScheduleEntry("test", step=10, offset=0.666, params={"note": 64}),  # Beat 3 at 10.666 steps
        ]

        # Verify absolute positions (step + offset)
        def absolute_position(entry):
            return entry.step + entry.offset

        assert absolute_position(entries[0]) == pytest.approx(0.0)
        assert absolute_position(entries[1]) == pytest.approx(5.333, abs=0.001)
        assert absolute_position(entries[2]) == pytest.approx(10.666, abs=0.001)

        # Verify equal spacing (4 steps apart in irregular meter)
        spacing1 = absolute_position(entries[1]) - absolute_position(entries[0])
        spacing2 = absolute_position(entries[2]) - absolute_position(entries[1])
        assert spacing1 == pytest.approx(spacing2, abs=0.001)

    def test_offset_to_dict_serialization(self):
        """Verify offset is properly serialized."""
        entry = ScheduleEntry("test", step=0, offset=0.5, params={})
        entry_dict = entry.to_dict()

        assert "offset" in entry_dict
        assert entry_dict["offset"] == 0.5
        assert "cycle" not in entry_dict  # Ensure old field is gone

    def test_offset_from_dict_deserialization(self):
        """Verify offset is properly deserialized with backward compatibility."""
        # New format with offset
        data = {
            "destination_id": "test",
            "step": 0,
            "offset": 0.5,
            "params": {}
        }
        entry = ScheduleEntry.from_dict(data)
        assert entry.offset == 0.5

        # Old format without offset (should default to 0.0)
        old_data = {
            "destination_id": "test",
            "step": 0,
            "params": {}
        }
        old_entry = ScheduleEntry.from_dict(old_data)
        assert old_entry.offset == 0.0


class TestBPMChangeWithOffset:
    """Test offset behavior with BPM changes."""

    def test_offset_unchanged_after_bpm_change(self):
        """Verify offset values remain identical after BPM change."""
        from oiduna.domain.schedule.models import LoopSchedule

        entries = [ScheduleEntry("sd", step=0, offset=0.66, params={})]

        schedule_120 = LoopSchedule(entries=tuple(entries), bpm=120.0)
        schedule_180 = LoopSchedule(entries=tuple(entries), bpm=180.0)

        # Offset values should be identical (BPM-independent)
        assert schedule_120.entries[0].offset == 0.66
        assert schedule_180.entries[0].offset == 0.66

    def test_absolute_timing_calculation(self):
        """Verify absolute timing calculation at different BPMs."""
        # Formula: absolute_time = step_duration * (step + offset)
        # step_duration = (60.0 / BPM) / 4

        # At 120 BPM: step_duration = 0.125s (125ms)
        # offset 0.5 → 62.5ms delay within step
        bpm_120_step_duration = (60.0 / 120.0) / 4
        assert bpm_120_step_duration == 0.125
        delay_120 = bpm_120_step_duration * 0.5
        assert delay_120 == pytest.approx(0.0625)  # 62.5ms

        # At 180 BPM: step_duration = 0.0833s (83.3ms)
        # offset 0.5 → 41.67ms delay within step
        bpm_180_step_duration = (60.0 / 180.0) / 4
        assert bpm_180_step_duration == pytest.approx(0.0833, abs=0.001)
        delay_180 = bpm_180_step_duration * 0.5
        assert delay_180 == pytest.approx(0.04166, abs=0.001)  # 41.67ms

        # Ratio should match BPM ratio
        ratio = delay_120 / delay_180
        bpm_ratio = 180.0 / 120.0
        assert ratio == pytest.approx(bpm_ratio, abs=0.01)
