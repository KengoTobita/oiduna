"""Tests for scheduled message models."""

import pytest

from scheduler_models import ScheduledMessage, ScheduledMessageBatch


class TestScheduledMessage:
    """Tests for ScheduledMessage dataclass."""

    def test_create_message(self):
        """Test creating a scheduled message."""
        msg = ScheduledMessage(
            destination_id="superdirt",
            cycle=3.5,
            step=56,
            params={"s": "bd", "gain": 0.8}
        )

        assert msg.destination_id == "superdirt"
        assert msg.cycle == 3.5
        assert msg.step == 56
        assert msg.params == {"s": "bd", "gain": 0.8}

    def test_message_is_immutable(self):
        """Test that message is frozen (immutable)."""
        msg = ScheduledMessage(
            destination_id="test",
            cycle=1.0,
            step=0,
            params={}
        )

        with pytest.raises(AttributeError):
            msg.destination_id = "other"  # type: ignore

    def test_to_dict(self):
        """Test converting message to dictionary."""
        msg = ScheduledMessage(
            destination_id="superdirt",
            cycle=2.0,
            step=32,
            params={"s": "bd", "gain": 0.5}
        )

        result = msg.to_dict()

        assert result == {
            "destination_id": "superdirt",
            "cycle": 2.0,
            "step": 32,
            "params": {"s": "bd", "gain": 0.5}
        }

    def test_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "destination_id": "volca",
            "cycle": 1.5,
            "step": 24,
            "params": {"note": 60, "velocity": 100}
        }

        msg = ScheduledMessage.from_dict(data)

        assert msg.destination_id == "volca"
        assert msg.cycle == 1.5
        assert msg.step == 24
        assert msg.params == {"note": 60, "velocity": 100}

    def test_round_trip_serialization(self):
        """Test dict serialization round trip."""
        original = ScheduledMessage(
            destination_id="test",
            cycle=4.0,
            step=100,
            params={"foo": "bar", "value": 42}
        )

        data = original.to_dict()
        restored = ScheduledMessage.from_dict(data)

        assert restored.destination_id == original.destination_id
        assert restored.cycle == original.cycle
        assert restored.step == original.step
        assert restored.params == original.params


class TestScheduledMessageBatch:
    """Tests for ScheduledMessageBatch."""

    def test_create_batch(self):
        """Test creating a message batch."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {})
        msg2 = ScheduledMessage("dest2", 1.0, 16, {})

        batch = ScheduledMessageBatch(
            messages=(msg1, msg2),
            bpm=120.0,
            pattern_length=4.0
        )

        assert len(batch.messages) == 2
        assert batch.bpm == 120.0
        assert batch.pattern_length == 4.0

    def test_batch_is_immutable(self):
        """Test that batch is frozen."""
        batch = ScheduledMessageBatch(
            messages=(),
            bpm=120.0
        )

        with pytest.raises(AttributeError):
            batch.bpm = 140.0  # type: ignore

    def test_default_values(self):
        """Test batch default values."""
        batch = ScheduledMessageBatch(messages=())

        assert batch.bpm == 120.0
        assert batch.pattern_length == 4.0

    def test_to_dict(self):
        """Test converting batch to dictionary."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {"s": "bd"})
        msg2 = ScheduledMessage("dest2", 2.0, 16, {"note": 60})

        batch = ScheduledMessageBatch(
            messages=(msg1, msg2),
            bpm=140.0,
            pattern_length=8.0
        )

        result = batch.to_dict()

        assert result["bpm"] == 140.0
        assert result["pattern_length"] == 8.0
        assert len(result["messages"]) == 2
        assert result["messages"][0]["destination_id"] == "dest1"
        assert result["messages"][1]["destination_id"] == "dest2"

    def test_from_dict(self):
        """Test creating batch from dictionary."""
        data = {
            "messages": [
                {"destination_id": "d1", "cycle": 1.0, "step": 0, "params": {}},
                {"destination_id": "d2", "cycle": 2.0, "step": 16, "params": {}},
            ],
            "bpm": 130.0,
            "pattern_length": 2.0
        }

        batch = ScheduledMessageBatch.from_dict(data)

        assert len(batch.messages) == 2
        assert batch.bpm == 130.0
        assert batch.pattern_length == 2.0
        assert batch.messages[0].destination_id == "d1"
        assert batch.messages[1].destination_id == "d2"

    def test_from_dict_with_defaults(self):
        """Test from_dict uses default values when missing."""
        data = {
            "messages": []
        }

        batch = ScheduledMessageBatch.from_dict(data)

        assert batch.bpm == 120.0
        assert batch.pattern_length == 4.0

    def test_round_trip_serialization(self):
        """Test batch serialization round trip."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {"s": "bd", "gain": 0.8})
        msg2 = ScheduledMessage("dest2", 2.5, 40, {"note": 72})

        original = ScheduledMessageBatch(
            messages=(msg1, msg2),
            bpm=125.0,
            pattern_length=3.0
        )

        data = original.to_dict()
        restored = ScheduledMessageBatch.from_dict(data)

        assert len(restored.messages) == len(original.messages)
        assert restored.bpm == original.bpm
        assert restored.pattern_length == original.pattern_length

        for i, msg in enumerate(restored.messages):
            orig_msg = original.messages[i]
            assert msg.destination_id == orig_msg.destination_id
            assert msg.cycle == orig_msg.cycle
            assert msg.step == orig_msg.step
            assert msg.params == orig_msg.params
