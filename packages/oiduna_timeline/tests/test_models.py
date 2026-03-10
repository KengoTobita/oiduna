"""Tests for ScheduledChange model"""

import pytest
import time
from oiduna_timeline.models import ScheduledChange
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch


def test_scheduled_change_creation():
    """Test basic ScheduledChange creation"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,), bpm=140.0)

    change = ScheduledChange(
        target_global_step=1000,
        batch=batch,
        client_id="alice_001",
        client_name="Alice",
        description="Kick pattern"
    )

    assert change.target_global_step == 1000
    assert change.batch == batch
    assert change.client_id == "alice_001"
    assert change.client_name == "Alice"
    assert change.description == "Kick pattern"
    assert isinstance(change.change_id, str)
    assert len(change.change_id) == 36  # UUID length
    assert change.sequence_number == 0


def test_scheduled_change_uuid_generation():
    """Test that each change gets unique UUID"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    change1 = ScheduledChange(target_global_step=1000, batch=batch, client_id="c1")
    change2 = ScheduledChange(target_global_step=1000, batch=batch, client_id="c1")

    assert change1.change_id != change2.change_id


def test_scheduled_change_frozen():
    """Test that ScheduledChange is immutable"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))
    change = ScheduledChange(target_global_step=1000, batch=batch, client_id="c1")

    with pytest.raises(Exception):  # FrozenInstanceError
        change.target_global_step = 2000


def test_scheduled_change_validation_negative_step():
    """Test validation rejects negative target step"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    with pytest.raises(ValueError, match="target_global_step must be non-negative"):
        ScheduledChange(target_global_step=-1, batch=batch, client_id="c1")


def test_scheduled_change_validation_empty_client_id():
    """Test validation rejects empty client_id"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    with pytest.raises(ValueError, match="client_id cannot be empty"):
        ScheduledChange(target_global_step=1000, batch=batch, client_id="")


def test_scheduled_change_validation_long_description():
    """Test validation rejects description > 200 chars"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))
    long_desc = "x" * 201

    with pytest.raises(ValueError, match="description too long"):
        ScheduledChange(target_global_step=1000, batch=batch, client_id="c1", description=long_desc)


def test_scheduled_change_to_dict():
    """Test serialization to dictionary"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,), bpm=140.0)

    change = ScheduledChange(
        change_id="test-uuid",
        target_global_step=1000,
        batch=batch,
        client_id="alice_001",
        client_name="Alice",
        description="Test",
        scheduled_at=1234567890.0,
        sequence_number=5,
    )

    data = change.to_dict()

    assert data["change_id"] == "test-uuid"
    assert data["target_global_step"] == 1000
    assert data["client_id"] == "alice_001"
    assert data["client_name"] == "Alice"
    assert data["description"] == "Test"
    assert data["scheduled_at"] == 1234567890.0
    assert data["sequence_number"] == 5
    assert "batch" in data
    assert data["batch"]["bpm"] == 140.0


def test_scheduled_change_from_dict():
    """Test deserialization from dictionary"""
    data = {
        "change_id": "test-uuid",
        "target_global_step": 1000,
        "client_id": "alice_001",
        "client_name": "Alice",
        "description": "Test",
        "scheduled_at": 1234567890.0,
        "sequence_number": 5,
        "batch": {
            "messages": [
                {"destination_id": "superdirt", "cycle": 0.0, "step": 0, "params": {"s": "bd"}}
            ],
            "bpm": 140.0,
            "pattern_length": 4.0,
        }
    }

    change = ScheduledChange.from_dict(data)

    assert change.change_id == "test-uuid"
    assert change.target_global_step == 1000
    assert change.client_id == "alice_001"
    assert change.client_name == "Alice"
    assert change.description == "Test"
    assert change.scheduled_at == 1234567890.0
    assert change.sequence_number == 5
    assert len(change.batch.messages) == 1
    assert change.batch.bpm == 140.0


def test_scheduled_change_defaults():
    """Test default values"""
    msg = ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"})
    batch = ScheduledMessageBatch(messages=(msg,))

    change = ScheduledChange(
        target_global_step=1000,
        batch=batch,
        client_id="c1",
    )

    assert change.client_name == ""
    assert change.description == ""
    assert change.sequence_number == 0
    assert isinstance(change.scheduled_at, float)
    assert change.scheduled_at > 0
