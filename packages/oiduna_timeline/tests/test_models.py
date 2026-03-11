"""Tests for CuedChange model"""

import pytest
import time
from oiduna_timeline.models import CuedChange
from oiduna_scheduler.scheduler_models import ScheduleEntry, LoopSchedule


def test_scheduled_change_creation():
    """Test basic CuedChange creation"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,), bpm=140.0)

    change = CuedChange(
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
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))

    change1 = CuedChange(target_global_step=1000, batch=batch, client_id="c1")
    change2 = CuedChange(target_global_step=1000, batch=batch, client_id="c1")

    assert change1.change_id != change2.change_id


def test_scheduled_change_frozen():
    """Test that CuedChange is immutable"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))
    change = CuedChange(target_global_step=1000, batch=batch, client_id="c1")

    with pytest.raises(Exception):  # FrozenInstanceError
        change.target_global_step = 2000


def test_scheduled_change_validation_negative_step():
    """Test validation rejects negative target step"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))

    with pytest.raises(ValueError, match="target_global_step must be non-negative"):
        CuedChange(target_global_step=-1, batch=batch, client_id="c1")


def test_scheduled_change_validation_empty_client_id():
    """Test validation rejects empty client_id"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))

    with pytest.raises(ValueError, match="client_id cannot be empty"):
        CuedChange(target_global_step=1000, batch=batch, client_id="")


def test_scheduled_change_validation_long_description():
    """Test validation rejects description > 200 chars"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))
    long_desc = "x" * 201

    with pytest.raises(ValueError, match="description too long"):
        CuedChange(target_global_step=1000, batch=batch, client_id="c1", description=long_desc)


def test_scheduled_change_to_dict():
    """Test serialization to dictionary"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,), bpm=140.0)

    change = CuedChange(
        change_id="test-uuid",
        target_global_step=1000,
        batch=batch,
        client_id="alice_001",
        client_name="Alice",
        description="Test",
        cued_at=1234567890.0,
        sequence_number=5,
    )

    data = change.to_dict()

    assert data["change_id"] == "test-uuid"
    assert data["target_global_step"] == 1000
    assert data["client_id"] == "alice_001"
    assert data["client_name"] == "Alice"
    assert data["description"] == "Test"
    assert data["cued_at"] == 1234567890.0
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
        "cued_at": 1234567890.0,
        "sequence_number": 5,
        "batch": {
            "messages": [
                {"destination_id": "superdirt", "cycle": 0.0, "step": 0, "params": {"s": "bd"}}
            ],
            "bpm": 140.0,
            "pattern_length": 4.0,
        }
    }

    change = CuedChange.from_dict(data)

    assert change.change_id == "test-uuid"
    assert change.target_global_step == 1000
    assert change.client_id == "alice_001"
    assert change.client_name == "Alice"
    assert change.description == "Test"
    assert change.cued_at == 1234567890.0
    assert change.sequence_number == 5
    assert len(change.batch.entries) == 1
    assert change.batch.bpm == 140.0


def test_scheduled_change_defaults():
    """Test default values"""
    msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
    batch = LoopSchedule(entries=(msg,))

    change = CuedChange(
        target_global_step=1000,
        batch=batch,
        client_id="c1",
    )

    assert change.client_name == ""
    assert change.description == ""
    assert change.sequence_number == 0
    assert isinstance(change.cued_at, float)
    assert change.cued_at > 0
