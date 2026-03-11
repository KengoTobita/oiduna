"""Tests for merge_changes function"""

import pytest
from oiduna_timeline.merger import merge_changes
from oiduna_timeline.models import CuedChange
from oiduna_scheduler.scheduler_models import ScheduleEntry, LoopSchedule


def create_test_change(
    target_step: int,
    num_messages: int,
    bpm: float = 120.0,
    pattern_length: float = 4.0,
) -> CuedChange:
    """Helper to create a test change"""
    entries = [
        ScheduleEntry("superdirt", i * 0.1, i, {"s": f"sound{i}"})
        for i in range(num_messages)
    ]
    batch = LoopSchedule(
        entries=tuple(entries),
        bpm=bpm,
        pattern_length=pattern_length,
    )
    return CuedChange(
        target_global_step=target_step,
        batch=batch,
        client_id="test_client",
    )


def test_merge_empty_list():
    """Test merging empty list returns empty batch"""
    result = merge_changes([])

    assert len(result.entries) == 0
    assert result.bpm == 120.0
    assert result.pattern_length == 4.0


def test_merge_single_change():
    """Test merging single change"""
    change = create_test_change(1000, num_messages=3, bpm=140.0)

    result = merge_changes([change])

    assert len(result.entries) == 3
    assert result.bpm == 140.0
    assert result.pattern_length == 4.0


def test_merge_multiple_changes():
    """Test merging multiple changes combines all messages"""
    change1 = create_test_change(1000, num_messages=3, bpm=120.0)
    change2 = create_test_change(1000, num_messages=2, bpm=140.0)
    change3 = create_test_change(1000, num_messages=5, bpm=160.0)

    result = merge_changes([change1, change2, change3])

    # All messages should be combined
    assert len(result.entries) == 3 + 2 + 5
    # Last BPM should win
    assert result.bpm == 160.0
    assert result.pattern_length == 4.0


def test_merge_uses_last_bpm():
    """Test that last change's BPM is used"""
    change1 = create_test_change(1000, num_messages=1, bpm=100.0)
    change2 = create_test_change(1000, num_messages=1, bpm=120.0)
    change3 = create_test_change(1000, num_messages=1, bpm=140.0)

    result = merge_changes([change1, change2, change3])

    assert result.bpm == 140.0


def test_merge_uses_last_pattern_length():
    """Test that last change's pattern_length is used"""
    messages = [ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})]

    batch1 = LoopSchedule(entries=tuple(messages), pattern_length=2.0)
    batch2 = LoopSchedule(entries=tuple(messages), pattern_length=4.0)
    batch3 = LoopSchedule(entries=tuple(messages), pattern_length=8.0)

    change1 = CuedChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = CuedChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = CuedChange(target_global_step=1000, batch=batch3, client_id="c3")

    result = merge_changes([change1, change2, change3])

    assert result.pattern_length == 8.0


def test_merge_preserves_message_order():
    """Test that messages are merged in order"""
    # Create changes with identifiable messages
    msg1 = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd", "id": 1})
    msg2 = ScheduleEntry("superdirt", 0.0, 0, {"s": "sd", "id": 2})
    msg3 = ScheduleEntry("superdirt", 0.0, 0, {"s": "hh", "id": 3})

    batch1 = LoopSchedule(entries=(msg1,))
    batch2 = LoopSchedule(entries=(msg2,))
    batch3 = LoopSchedule(entries=(msg3,))

    change1 = CuedChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = CuedChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = CuedChange(target_global_step=1000, batch=batch3, client_id="c3")

    result = merge_changes([change1, change2, change3])

    assert len(result.entries) == 3
    assert result.entries[0].params["id"] == 1
    assert result.entries[1].params["id"] == 2
    assert result.entries[2].params["id"] == 3


def test_merge_destinations_auto_inferred():
    """Test that destinations are auto-inferred from messages"""
    msg1 = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    msg2 = ScheduleEntry("midi_device", 0.0, 0, {"note": 60})
    msg3 = ScheduleEntry("superdirt", 1.0, 1, {"s": "sd"})

    batch1 = LoopSchedule(entries=(msg1,))
    batch2 = LoopSchedule(entries=(msg2,))
    batch3 = LoopSchedule(entries=(msg3,))

    change1 = CuedChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = CuedChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = CuedChange(target_global_step=1000, batch=batch3, client_id="c3")

    result = merge_changes([change1, change2, change3])

    # destinations should be auto-inferred
    assert "superdirt" in result.destinations
    assert "midi_device" in result.destinations
    assert len(result.destinations) == 2


def test_merge_large_number_of_changes():
    """Test merging many changes (performance/correctness)"""
    changes = [
        create_test_change(1000, num_messages=10, bpm=120.0 + i)
        for i in range(100)
    ]

    result = merge_changes(changes)

    assert len(result.entries) == 100 * 10
    assert result.bpm == 120.0 + 99  # Last BPM


def test_merge_with_empty_batches():
    """Test merging changes that have empty message batches"""
    batch1 = LoopSchedule(entries=tuple())
    batch2 = LoopSchedule(entries=tuple())

    change1 = CuedChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = CuedChange(target_global_step=1000, batch=batch2, client_id="c2")

    result = merge_changes([change1, change2])

    assert len(result.entries) == 0
    assert len(result.destinations) == 0
