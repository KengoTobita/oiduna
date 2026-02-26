"""Tests for DestinationRouter."""

import pytest
from typing import List, Dict, Any
from collections import defaultdict

from scheduler_models import ScheduledMessage
from router import DestinationRouter


class MockDestinationSender:
    """Mock destination sender for testing."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.bundles: List[List[Dict[str, Any]]] = []

    def send_message(self, params: dict) -> None:
        """Record sent message."""
        self.messages.append(params)

    def send_bundle(self, messages: List[dict]) -> None:
        """Record sent bundle."""
        self.bundles.append(messages)


class TestDestinationRouter:
    """Tests for DestinationRouter class."""

    def test_init(self):
        """Test router initialization."""
        router = DestinationRouter()
        assert router.get_registered_destinations() == []

    def test_register_destination(self):
        """Test registering a destination."""
        router = DestinationRouter()
        sender = MockDestinationSender()

        router.register_destination("test_dest", sender)

        assert "test_dest" in router.get_registered_destinations()

    def test_unregister_destination(self):
        """Test unregistering a destination."""
        router = DestinationRouter()
        sender = MockDestinationSender()

        router.register_destination("test_dest", sender)
        assert "test_dest" in router.get_registered_destinations()

        router.unregister_destination("test_dest")
        assert "test_dest" not in router.get_registered_destinations()

    def test_send_single_message(self):
        """Test sending a single message."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("dest1", sender)

        msg = ScheduledMessage("dest1", 1.0, 0, {"s": "bd", "gain": 0.8})
        router.send_messages([msg])

        assert len(sender.messages) == 1
        assert sender.messages[0] == {"s": "bd", "gain": 0.8}

    def test_send_multiple_messages_same_destination(self):
        """Test sending multiple messages to same destination."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("dest1", sender)

        msg1 = ScheduledMessage("dest1", 1.0, 0, {"s": "bd"})
        msg2 = ScheduledMessage("dest1", 1.0, 0, {"s": "sn"})
        router.send_messages([msg1, msg2])

        assert len(sender.messages) == 2
        assert sender.messages[0] == {"s": "bd"}
        assert sender.messages[1] == {"s": "sn"}

    def test_send_messages_to_multiple_destinations(self):
        """Test sending messages to different destinations."""
        router = DestinationRouter()
        sender1 = MockDestinationSender()
        sender2 = MockDestinationSender()
        router.register_destination("dest1", sender1)
        router.register_destination("dest2", sender2)

        msg1 = ScheduledMessage("dest1", 1.0, 0, {"s": "bd"})
        msg2 = ScheduledMessage("dest2", 1.0, 0, {"note": 60})
        msg3 = ScheduledMessage("dest1", 1.0, 0, {"s": "sn"})

        router.send_messages([msg1, msg2, msg3])

        # dest1 should receive 2 messages
        assert len(sender1.messages) == 2
        assert sender1.messages[0] == {"s": "bd"}
        assert sender1.messages[1] == {"s": "sn"}

        # dest2 should receive 1 message
        assert len(sender2.messages) == 1
        assert sender2.messages[0] == {"note": 60}

    def test_send_to_unregistered_destination(self):
        """Test sending to unregistered destination (should skip silently)."""
        router = DestinationRouter()

        msg = ScheduledMessage("unknown_dest", 1.0, 0, {"s": "bd"})
        # Should not raise error
        router.send_messages([msg])

    def test_send_empty_list(self):
        """Test sending empty message list."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("dest1", sender)

        router.send_messages([])

        assert len(sender.messages) == 0

    def test_multiple_destinations(self):
        """Test router with multiple registered destinations."""
        router = DestinationRouter()
        sender1 = MockDestinationSender()
        sender2 = MockDestinationSender()
        sender3 = MockDestinationSender()

        router.register_destination("osc1", sender1)
        router.register_destination("midi1", sender2)
        router.register_destination("osc2", sender3)

        dests = router.get_registered_destinations()
        assert len(dests) == 3
        assert "osc1" in dests
        assert "midi1" in dests
        assert "osc2" in dests
