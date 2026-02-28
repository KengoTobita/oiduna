"""
Unit tests for destination validation.

Tests the has_destination() method and destinations field in ScheduledMessageBatch.
"""

import pytest
from oiduna_scheduler.router import DestinationRouter
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch


class TestDestinationRouter:
    """Test DestinationRouter.has_destination() method."""

    def test_has_destination_returns_true_when_registered(self):
        """has_destination should return True for registered destinations."""
        router = DestinationRouter()
        # Register a mock destination by adding to _senders
        router._senders["superdirt"] = None  # Mock sender

        assert router.has_destination("superdirt") is True

    def test_has_destination_returns_false_when_not_registered(self):
        """has_destination should return False for unregistered destinations."""
        router = DestinationRouter()

        assert router.has_destination("nonexistent") is False

    def test_has_destination_multiple_destinations(self):
        """has_destination should work with multiple registered destinations."""
        router = DestinationRouter()
        router._senders["superdirt"] = None
        router._senders["midi"] = None

        assert router.has_destination("superdirt") is True
        assert router.has_destination("midi") is True
        assert router.has_destination("nonexistent") is False


class TestScheduledMessageBatchDestinations:
    """Test destinations field in ScheduledMessageBatch."""

    def test_destinations_field_serialization(self):
        """destinations field should serialize to list in to_dict()."""
        msg1 = ScheduledMessage(
            destination_id="superdirt",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )
        msg2 = ScheduledMessage(
            destination_id="midi",
            cycle=1.0,
            step=64,
            params={"note": 60},
        )

        batch = ScheduledMessageBatch(
            messages=(msg1, msg2),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset({"superdirt", "midi"}),
        )

        batch_dict = batch.to_dict()

        assert "destinations" in batch_dict
        assert set(batch_dict["destinations"]) == {"superdirt", "midi"}

    def test_destinations_field_deserialization(self):
        """destinations field should deserialize from list in from_dict()."""
        data = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": ["superdirt", "midi"],
        }

        batch = ScheduledMessageBatch.from_dict(data)

        assert batch.destinations == frozenset({"superdirt", "midi"})

    def test_destinations_backward_compatibility_infers_from_messages(self):
        """from_dict should infer destinations from messages if not present."""
        data = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                },
                {
                    "destination_id": "midi",
                    "cycle": 1.0,
                    "step": 64,
                    "params": {"note": 60},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            # No destinations field
        }

        batch = ScheduledMessageBatch.from_dict(data)

        # Should infer from messages
        assert batch.destinations == frozenset({"superdirt", "midi"})

    def test_destinations_default_empty_frozenset(self):
        """destinations field should default to empty frozenset."""
        batch = ScheduledMessageBatch(
            messages=(),
            bpm=120.0,
            pattern_length=4.0,
        )

        assert batch.destinations == frozenset()

    def test_destinations_round_trip_serialization(self):
        """destinations should survive round-trip serialization."""
        msg = ScheduledMessage(
            destination_id="superdirt",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )

        original = ScheduledMessageBatch(
            messages=(msg,),
            bpm=140.0,
            pattern_length=8.0,
            destinations=frozenset({"superdirt"}),
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ScheduledMessageBatch.from_dict(data)

        assert restored.destinations == original.destinations
        assert restored.bpm == original.bpm
        assert restored.pattern_length == original.pattern_length
        assert len(restored.messages) == len(original.messages)
