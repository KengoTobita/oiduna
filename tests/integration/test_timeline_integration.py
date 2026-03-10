"""
Integration tests for timeline scheduling feature.

Tests the full flow from SessionContainer -> TimelineManager -> LoopEngine.
"""

import pytest
from oiduna_session import SessionContainer
from oiduna_timeline import ScheduledChange
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch
from oiduna_loop.engine.timeline_loader import TimelineLoader
from oiduna_scheduler.scheduler import MessageScheduler


@pytest.fixture
def container():
    """Create a SessionContainer with timeline"""
    return SessionContainer()


def test_timeline_end_to_end(container):
    """
    Test complete flow: schedule change -> apply at target step -> verify loaded.
    """
    # 1. Register a client
    client = container.clients.create("client_001", "Alice", "mars")
    assert client is not None

    # 2. Create a scheduled change
    messages = [
        ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"}),
        ScheduledMessage("superdirt", 0.5, 2, {"s": "sd"}),
    ]
    batch = ScheduledMessageBatch(messages=tuple(messages), bpm=140.0)

    success, msg, change_id = container.timeline.schedule_change(
        batch=batch,
        target_global_step=1000,
        client_id="client_001",
        client_name="Alice",
        description="Kick and snare pattern",
        current_global_step=500,
    )

    assert success is True
    assert change_id is not None
    assert msg == ""

    # 3. Verify change is stored
    change = container.timeline.get_change(change_id)
    assert change is not None
    assert change.target_global_step == 1000
    assert len(change.batch.messages) == 2

    # 4. Simulate applying the change at target step
    scheduler = MessageScheduler()
    applied = TimelineLoader.apply_changes_at_step(
        global_step=1000,
        timeline=container.timeline.timeline,
        message_scheduler=scheduler,
    )

    assert applied is True

    # 5. Verify messages were loaded into scheduler
    # The scheduler should have loaded the messages
    messages_at_0 = scheduler.get_messages_at_step(0)
    messages_at_2 = scheduler.get_messages_at_step(2)

    assert len(messages_at_0) == 1
    assert messages_at_0[0].params["s"] == "bd"

    assert len(messages_at_2) == 1
    assert messages_at_2[0].params["s"] == "sd"

    # 6. Verify cleanup happened (change should be removed)
    change_after = container.timeline.get_change(change_id)
    assert change_after is None


def test_multiple_changes_merge(container):
    """
    Test that multiple changes scheduled for same step are merged.
    """
    # Register clients
    container.clients.create("alice_001", "Alice", "mars")
    container.clients.create("bob_001", "Bob", "mars")

    # Schedule first change
    msg1 = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch1 = ScheduledMessageBatch(messages=(msg1,), bpm=120.0)
    success1, _, id1 = container.timeline.schedule_change(
        batch=batch1,
        target_global_step=1000,
        client_id="alice_001",
        client_name="Alice",
        description="Kick",
        current_global_step=500,
    )
    assert success1 is True

    # Schedule second change for same step
    msg2 = ScheduledMessage("superdirt", 0.5, 2, {"s": "sd"})
    batch2 = ScheduledMessageBatch(messages=(msg2,), bpm=140.0)
    success2, _, id2 = container.timeline.schedule_change(
        batch=batch2,
        target_global_step=1000,
        client_id="bob_001",
        client_name="Bob",
        description="Snare",
        current_global_step=500,
    )
    assert success2 is True

    # Apply at target step
    scheduler = MessageScheduler()
    applied = TimelineLoader.apply_changes_at_step(
        global_step=1000,
        timeline=container.timeline.timeline,
        message_scheduler=scheduler,
    )

    assert applied is True

    # Verify both messages were merged and loaded
    messages_at_0 = scheduler.get_messages_at_step(0)
    messages_at_2 = scheduler.get_messages_at_step(2)

    assert len(messages_at_0) == 1  # Alice's kick
    assert len(messages_at_2) == 1  # Bob's snare

    # Verify last BPM wins (Bob's 140.0)
    # Note: scheduler doesn't store BPM, but we can verify via the merge logic
    changes_at_1000 = container.timeline.timeline.get_changes_at(1000)
    # After cleanup, changes should be gone
    assert len(changes_at_1000) == 0


def test_cleanup_past_changes(container):
    """
    Test automatic cleanup of past scheduled changes.
    """
    container.clients.create("client_001", "Alice", "mars")

    # Schedule changes at different steps
    for step in [500, 1000, 1500, 2000]:
        msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
        batch = ScheduledMessageBatch(messages=(msg,))
        container.timeline.schedule_change(
            batch=batch,
            target_global_step=step,
            client_id="client_001",
            client_name="Alice",
            description=f"Pattern at {step}",
            current_global_step=100,
        )

    # Verify all 4 changes exist
    assert container.timeline.timeline.size() == 4

    # Apply at step 1200 (should cleanup steps 500 and 1000)
    scheduler = MessageScheduler()
    TimelineLoader.apply_changes_at_step(
        global_step=1200,
        timeline=container.timeline.timeline,
        message_scheduler=scheduler,
    )

    # Verify cleanup happened
    assert container.timeline.timeline.size() == 2  # Only 1500 and 2000 remain

    # Verify correct changes remain
    upcoming = container.timeline.get_all_upcoming(1200, limit=10)
    assert len(upcoming) == 2
    assert upcoming[0].target_global_step == 1500
    assert upcoming[1].target_global_step == 2000


def test_permission_checks(container):
    """
    Test that only the owner can cancel/update their changes.
    """
    # Register two clients
    container.clients.create("alice_001", "Alice", "mars")
    container.clients.create("bob_001", "Bob", "mars")

    # Alice schedules a change
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))
    success, _, change_id = container.timeline.schedule_change(
        batch=batch,
        target_global_step=1000,
        client_id="alice_001",
        client_name="Alice",
        description="Alice's pattern",
        current_global_step=500,
    )
    assert success is True

    # Bob tries to cancel Alice's change
    success, msg = container.timeline.cancel_change(change_id, "bob_001")
    assert success is False
    assert "Permission denied" in msg

    # Alice can cancel her own change
    success, msg = container.timeline.cancel_change(change_id, "alice_001")
    assert success is True
    assert msg == ""

    # Verify change is gone
    assert container.timeline.get_change(change_id) is None


def test_future_step_validation(container):
    """
    Test that scheduling for past/current step is rejected.
    """
    container.clients.create("client_001", "Alice", "mars")

    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    # Try to schedule for current step (should fail)
    success, error_msg, _ = container.timeline.schedule_change(
        batch=batch,
        target_global_step=1000,
        client_id="client_001",
        client_name="Alice",
        description="Test",
        current_global_step=1000,  # Same as target
    )

    assert success is False
    assert "must be >" in error_msg

    # Try to schedule for past step (should fail)
    success, error_msg, _ = container.timeline.schedule_change(
        batch=batch,
        target_global_step=500,
        client_id="client_001",
        client_name="Alice",
        description="Test",
        current_global_step=1000,  # Current is ahead
    )

    assert success is False
    assert "must be >" in error_msg

    # Valid future step should work
    success, error_msg, _ = container.timeline.schedule_change(
        batch=batch,
        target_global_step=2000,
        client_id="client_001",
        client_name="Alice",
        description="Test",
        current_global_step=1000,
    )

    assert success is True


def test_max_changes_per_step_limit(container):
    """
    Test that MAX_CHANGES_PER_STEP limit is enforced.
    """
    # Register multiple clients
    for i in range(15):
        container.clients.create(f"client_{i:03d}", f"User{i}", "mars")

    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    # Schedule up to the limit (10 changes per step)
    for i in range(10):
        success, _, _ = container.timeline.schedule_change(
            batch=batch,
            target_global_step=1000,
            client_id=f"client_{i:03d}",
            client_name=f"User{i}",
            description=f"Pattern {i}",
            current_global_step=500,
        )
        assert success is True

    # 11th change should fail
    success, error_msg, _ = container.timeline.schedule_change(
        batch=batch,
        target_global_step=1000,
        client_id="client_010",
        client_name="User10",
        description="Pattern 10",
        current_global_step=500,
    )

    assert success is False
    assert "MAX_CHANGES_PER_STEP" in error_msg


def test_update_change_integration(container):
    """
    Test updating a scheduled change via TimelineManager.
    """
    container.clients.create("alice_001", "Alice", "mars")

    # Schedule initial change
    msg1 = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch1 = ScheduledMessageBatch(messages=(msg1,), bpm=120.0)
    success, _, change_id = container.timeline.schedule_change(
        batch=batch1,
        target_global_step=1000,
        client_id="alice_001",
        client_name="Alice",
        description="Original pattern",
        current_global_step=500,
    )
    assert success is True

    # Update the change
    msg2 = ScheduledMessage("superdirt", 0.0, 0, {"s": "sd"})
    batch2 = ScheduledMessageBatch(messages=(msg2,), bpm=140.0)
    success, msg = container.timeline.update_change(
        change_id=change_id,
        new_batch=batch2,
        new_target_global_step=1500,
        new_description="Updated pattern",
        client_id="alice_001",
        current_global_step=500,
    )

    assert success is True
    assert msg == ""

    # Verify update
    updated = container.timeline.get_change(change_id)
    assert updated is not None
    assert updated.target_global_step == 1500
    assert updated.description == "Updated pattern"
    assert updated.batch.bpm == 140.0
    assert updated.batch.messages[0].params["s"] == "sd"


def test_empty_timeline_application(container):
    """
    Test that applying changes at a step with no changes is safe.
    """
    scheduler = MessageScheduler()

    # Apply at step with no changes
    applied = TimelineLoader.apply_changes_at_step(
        global_step=1000,
        timeline=container.timeline.timeline,
        message_scheduler=scheduler,
    )

    assert applied is False  # No changes applied

    # Verify scheduler is still empty
    for step in range(256):
        messages = scheduler.get_messages_at_step(step)
        assert len(messages) == 0


def test_sequence_number_ordering(container):
    """
    Test that sequence numbers maintain order for same-step changes.
    """
    # Register clients
    for i in range(5):
        container.clients.create(f"client_{i}", f"User{i}", "mars")

    # Schedule changes in specific order
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    change_ids = []
    for i in range(5):
        success, _, change_id = container.timeline.schedule_change(
            batch=batch,
            target_global_step=1000,
            client_id=f"client_{i}",
            client_name=f"User{i}",
            description=f"Pattern {i}",
            current_global_step=500,
        )
        assert success is True
        change_ids.append(change_id)

    # Get changes and verify ordering
    changes = container.timeline.timeline.get_changes_at(1000)
    assert len(changes) == 5

    # Sequence numbers should be increasing
    for i in range(4):
        assert changes[i].sequence_number < changes[i + 1].sequence_number

    # Verify they match insertion order
    for i, change_id in enumerate(change_ids):
        assert changes[i].change_id == change_id
