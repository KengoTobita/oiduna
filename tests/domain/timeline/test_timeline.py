"""Tests for CuedChangeTimeline"""

import pytest
from oiduna.domain.timeline.timeline import CuedChangeTimeline
from oiduna.domain.timeline.models import CuedChange
from oiduna.domain.schedule import ScheduleEntry, LoopSchedule


def create_test_change(target_step: int, client_id: str = "c1", num_messages: int = 1) -> CuedChange:
    """Helper to create a test change"""
    messages = [
        ScheduleEntry("superdirt", 0.0, i, {"s": "bd"})
        for i in range(num_messages)
    ]
    batch = LoopSchedule(entries=tuple(messages))
    return CuedChange(
        target_global_step=target_step,
        batch=batch,
        client_id=client_id,
    )


def test_timeline_creation():
    """Test timeline initialization"""
    timeline = CuedChangeTimeline()
    assert timeline.size() == 0


def test_add_change_success():
    """Test adding a valid change"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000)

    success, msg = timeline.add_change(change, current_global_step=500)

    assert success is True
    assert msg == ""
    assert timeline.size() == 1


def test_add_change_rejects_past_step():
    """Test that changes for past steps are rejected"""
    timeline = CuedChangeTimeline()
    change = create_test_change(500)

    success, msg = timeline.add_change(change, current_global_step=1000)

    assert success is False
    assert "must be >" in msg
    assert timeline.size() == 0


def test_add_change_rejects_current_step():
    """Test that changes for current step are rejected"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000)

    success, msg = timeline.add_change(change, current_global_step=1000)

    assert success is False
    assert "must be >" in msg


def test_add_change_duplicate_id():
    """Test that duplicate change_id is rejected"""
    timeline = CuedChangeTimeline()
    change1 = create_test_change(1000)

    # Add first time
    success, _ = timeline.add_change(change1, current_global_step=500)
    assert success is True

    # Try to add same change again (same ID)
    success, msg = timeline.add_change(change1, current_global_step=500)
    assert success is False
    assert "already exists" in msg


def test_add_change_max_changes_per_step():
    """Test MAX_CHANGES_PER_STEP limit"""
    timeline = CuedChangeTimeline()

    # Add up to the limit
    for i in range(timeline.MAX_CHANGES_PER_STEP):
        change = create_test_change(1000, client_id=f"c{i}")
        success, _ = timeline.add_change(change, current_global_step=500)
        assert success is True

    # One more should fail
    change = create_test_change(1000, client_id="overflow")
    success, msg = timeline.add_change(change, current_global_step=500)
    assert success is False
    assert "MAX_CHANGES_PER_STEP" in msg


def test_add_change_max_messages_per_batch():
    """Test MAX_MESSAGES_PER_BATCH limit"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000, num_messages=timeline.MAX_MESSAGES_PER_BATCH + 1)

    success, msg = timeline.add_change(change, current_global_step=500)

    assert success is False
    assert "MAX_MESSAGES_PER_BATCH" in msg


def test_add_change_assigns_sequence_number():
    """Test that sequence numbers are assigned incrementally"""
    timeline = CuedChangeTimeline()

    change1 = create_test_change(1000, client_id="c1")
    change2 = create_test_change(1000, client_id="c2")
    change3 = create_test_change(2000, client_id="c3")

    timeline.add_change(change1, current_global_step=500)
    timeline.add_change(change2, current_global_step=500)
    timeline.add_change(change3, current_global_step=500)

    changes_at_1000 = timeline.get_changes_at(1000)
    assert len(changes_at_1000) == 2
    assert changes_at_1000[0].sequence_number < changes_at_1000[1].sequence_number


def test_get_changes_at():
    """Test retrieving changes at specific step"""
    timeline = CuedChangeTimeline()

    change1 = create_test_change(1000, client_id="c1")
    change2 = create_test_change(1000, client_id="c2")
    change3 = create_test_change(2000, client_id="c3")

    timeline.add_change(change1, current_global_step=500)
    timeline.add_change(change2, current_global_step=500)
    timeline.add_change(change3, current_global_step=500)

    changes_at_1000 = timeline.get_changes_at(1000)
    assert len(changes_at_1000) == 2

    changes_at_2000 = timeline.get_changes_at(2000)
    assert len(changes_at_2000) == 1

    changes_at_3000 = timeline.get_changes_at(3000)
    assert len(changes_at_3000) == 0


def test_get_changes_at_sorted_by_sequence():
    """Test that changes are returned sorted by sequence_number"""
    timeline = CuedChangeTimeline()

    # Add in reverse order
    change3 = create_test_change(1000, client_id="c3")
    change2 = create_test_change(1000, client_id="c2")
    change1 = create_test_change(1000, client_id="c1")

    timeline.add_change(change1, current_global_step=500)
    timeline.add_change(change2, current_global_step=500)
    timeline.add_change(change3, current_global_step=500)

    changes = timeline.get_changes_at(1000)
    assert len(changes) == 3
    # Should be sorted by sequence number (order added)
    assert changes[0].sequence_number < changes[1].sequence_number < changes[2].sequence_number


def test_get_change_by_id():
    """Test retrieving a change by its ID"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000, client_id="c1")

    timeline.add_change(change, current_global_step=500)

    retrieved = timeline.get_change_by_id(change.change_id)
    assert retrieved is not None
    assert retrieved.change_id == change.change_id
    assert retrieved.target_global_step == 1000


def test_get_change_by_id_not_found():
    """Test get_change_by_id returns None for unknown ID"""
    timeline = CuedChangeTimeline()

    retrieved = timeline.get_change_by_id("nonexistent-uuid")
    assert retrieved is None


def test_cancel_change():
    """Test cancelling a scheduled change"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000, client_id="c1")

    timeline.add_change(change, current_global_step=500)
    assert timeline.size() == 1

    success, msg = timeline.cancel_change(change.change_id)
    assert success is True
    assert msg == ""
    assert timeline.size() == 0

    # Verify it's gone
    retrieved = timeline.get_change_by_id(change.change_id)
    assert retrieved is None


def test_cancel_change_not_found():
    """Test cancelling a non-existent change"""
    timeline = CuedChangeTimeline()

    success, msg = timeline.cancel_change("nonexistent-uuid")
    assert success is False
    assert "not found" in msg


def test_update_change():
    """Test updating a scheduled change"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000, client_id="c1")

    timeline.add_change(change, current_global_step=500)

    # Create updated version
    new_change = create_test_change(2000, client_id="c1")
    # Must keep same ID
    from dataclasses import replace
    new_change = replace(new_change, change_id=change.change_id)

    success, msg = timeline.update_change(
        change.change_id,
        new_change,
        current_global_step=500,
    )

    assert success is True
    assert msg == ""

    # Verify update
    retrieved = timeline.get_change_by_id(change.change_id)
    assert retrieved is not None
    assert retrieved.target_global_step == 2000


def test_update_change_id_mismatch():
    """Test that update rejects ID mismatch"""
    timeline = CuedChangeTimeline()
    change = create_test_change(1000, client_id="c1")

    timeline.add_change(change, current_global_step=500)

    # Try to update with different ID
    new_change = create_test_change(2000, client_id="c1")

    success, msg = timeline.update_change(
        change.change_id,
        new_change,
        current_global_step=500,
    )

    assert success is False
    assert "mismatch" in msg


def test_cleanup_past():
    """Test cleanup of past changes"""
    timeline = CuedChangeTimeline()

    change1 = create_test_change(500, client_id="c1")
    change2 = create_test_change(1000, client_id="c2")
    change3 = create_test_change(1500, client_id="c3")

    timeline.add_change(change1, current_global_step=100)
    timeline.add_change(change2, current_global_step=100)
    timeline.add_change(change3, current_global_step=100)

    assert timeline.size() == 3

    # Cleanup past changes (current = 1200)
    removed = timeline.cleanup_past(1200)

    assert removed == 2  # change1 and change2 removed
    assert timeline.size() == 1

    # Verify only future change remains
    assert timeline.get_change_by_id(change3.change_id) is not None
    assert timeline.get_change_by_id(change1.change_id) is None
    assert timeline.get_change_by_id(change2.change_id) is None


def test_cleanup_past_no_changes():
    """Test cleanup when no changes are past"""
    timeline = CuedChangeTimeline()

    change = create_test_change(1000, client_id="c1")
    timeline.add_change(change, current_global_step=500)

    removed = timeline.cleanup_past(500)

    assert removed == 0
    assert timeline.size() == 1


def test_get_all_upcoming():
    """Test getting all upcoming changes"""
    timeline = CuedChangeTimeline()

    change1 = create_test_change(500, client_id="c1")
    change2 = create_test_change(1000, client_id="c2")
    change3 = create_test_change(1500, client_id="c3")

    timeline.add_change(change1, current_global_step=100)
    timeline.add_change(change2, current_global_step=100)
    timeline.add_change(change3, current_global_step=100)

    # Get all upcoming from step 600
    upcoming = timeline.get_all_upcoming(600, limit=100)

    assert len(upcoming) == 2  # change2 and change3
    assert upcoming[0].target_global_step == 1000
    assert upcoming[1].target_global_step == 1500


def test_get_all_upcoming_sorted():
    """Test that upcoming changes are sorted by step and sequence"""
    timeline = CuedChangeTimeline()

    # Add in mixed order
    change3 = create_test_change(2000, client_id="c3")
    change1 = create_test_change(1000, client_id="c1")
    change2 = create_test_change(1000, client_id="c2")

    timeline.add_change(change3, current_global_step=100)
    timeline.add_change(change1, current_global_step=100)
    timeline.add_change(change2, current_global_step=100)

    upcoming = timeline.get_all_upcoming(500, limit=100)

    assert len(upcoming) == 3
    # Should be sorted by step, then sequence
    assert upcoming[0].target_global_step == 1000
    assert upcoming[1].target_global_step == 1000
    assert upcoming[2].target_global_step == 2000
    assert upcoming[0].sequence_number < upcoming[1].sequence_number


def test_get_all_upcoming_limit():
    """Test limit parameter"""
    timeline = CuedChangeTimeline()

    for i in range(10):
        change = create_test_change(1000 + i * 100, client_id=f"c{i}")
        timeline.add_change(change, current_global_step=500)

    upcoming = timeline.get_all_upcoming(500, limit=5)

    assert len(upcoming) == 5
