"""Tests for merge_changes function"""

import pytest
from oiduna_timeline.merger import merge_changes
from oiduna_timeline.models import ScheduledChange
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch


def create_test_change(
    target_step: int,
    num_messages: int,
    bpm: float = 120.0,
    pattern_length: float = 4.0,
) -> ScheduledChange:
    """Helper to create a test change"""
    messages = [
        ScheduledMessage("superdirt", i * 0.1, i, {"s": f"sound{i}"})
        for i in range(num_messages)
    ]
    batch = ScheduledMessageBatch(
        messages=tuple(messages),
        bpm=bpm,
        pattern_length=pattern_length,
    )
    return ScheduledChange(
        target_global_step=target_step,
        batch=batch,
        client_id="test_client",
    )


def test_merge_empty_list():
    """Test merging empty list returns empty batch"""
    result = merge_changes([])

    assert len(result.messages) == 0
    assert result.bpm == 120.0
    assert result.pattern_length == 4.0


def test_merge_single_change():
    """Test merging single change"""
    change = create_test_change(1000, num_messages=3, bpm=140.0)

    result = merge_changes([change])

    assert len(result.messages) == 3
    assert result.bpm == 140.0
    assert result.pattern_length == 4.0


def test_merge_multiple_changes():
    """Test merging multiple changes combines all messages"""
    change1 = create_test_change(1000, num_messages=3, bpm=120.0)
    change2 = create_test_change(1000, num_messages=2, bpm=140.0)
    change3 = create_test_change(1000, num_messages=5, bpm=160.0)

    result = merge_changes([change1, change2, change3])

    # All messages should be combined
    assert len(result.messages) == 3 + 2 + 5
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
    messages = [ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})]

    batch1 = ScheduledMessageBatch(messages=tuple(messages), pattern_length=2.0)
    batch2 = ScheduledMessageBatch(messages=tuple(messages), pattern_length=4.0)
    batch3 = ScheduledMessageBatch(messages=tuple(messages), pattern_length=8.0)

    change1 = ScheduledChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = ScheduledChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = ScheduledChange(target_global_step=1000, batch=batch3, client_id="c3")

    result = merge_changes([change1, change2, change3])

    assert result.pattern_length == 8.0


def test_merge_preserves_message_order():
    """Test that messages are merged in order"""
    # Create changes with identifiable messages
    msg1 = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd", "id": 1})
    msg2 = ScheduledMessage("superdirt", 0.0, 0, {"s": "sd", "id": 2})
    msg3 = ScheduledMessage("superdirt", 0.0, 0, {"s": "hh", "id": 3})

    batch1 = ScheduledMessageBatch(messages=(msg1,))
    batch2 = ScheduledMessageBatch(messages=(msg2,))
    batch3 = ScheduledMessageBatch(messages=(msg3,))

    change1 = ScheduledChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = ScheduledChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = ScheduledChange(target_global_step=1000, batch=batch3, client_id="c3")

    result = merge_changes([change1, change2, change3])

    assert len(result.messages) == 3
    assert result.messages[0].params["id"] == 1
    assert result.messages[1].params["id"] == 2
    assert result.messages[2].params["id"] == 3


def test_merge_destinations_auto_inferred():
    """Test that destinations are auto-inferred from messages"""
    msg1 = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    msg2 = ScheduledMessage("midi_device", 0.0, 0, {"note": 60})
    msg3 = ScheduledMessage("superdirt", 1.0, 1, {"s": "sd"})

    batch1 = ScheduledMessageBatch(messages=(msg1,))
    batch2 = ScheduledMessageBatch(messages=(msg2,))
    batch3 = ScheduledMessageBatch(messages=(msg3,))

    change1 = ScheduledChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = ScheduledChange(target_global_step=1000, batch=batch2, client_id="c2")
    change3 = ScheduledChange(target_global_step=1000, batch=batch3, client_id="c3")

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

    assert len(result.messages) == 100 * 10
    assert result.bpm == 120.0 + 99  # Last BPM


def test_merge_with_empty_batches():
    """Test merging changes that have empty message batches"""
    batch1 = ScheduledMessageBatch(messages=tuple())
    batch2 = ScheduledMessageBatch(messages=tuple())

    change1 = ScheduledChange(target_global_step=1000, batch=batch1, client_id="c1")
    change2 = ScheduledChange(target_global_step=1000, batch=batch2, client_id="c2")

    result = merge_changes([change1, change2])

    assert len(result.messages) == 0
    assert len(result.destinations) == 0
