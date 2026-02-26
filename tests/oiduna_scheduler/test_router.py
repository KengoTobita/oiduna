"""Tests for DestinationRouter."""

import pytest
from typing import List, Dict, Any
from collections import defaultdict

from scheduler_models import ScheduledMessage
from router import DestinationRouter
from validators import OscValidator, MidiValidator


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

    def test_register_with_protocol(self):
        """Test registering destinations with protocol specification."""
        router = DestinationRouter()
        osc_sender = MockDestinationSender()
        midi_sender = MockDestinationSender()

        router.register_destination("superdirt", osc_sender, protocol="osc")
        router.register_destination("volca", midi_sender, protocol="midi")

        assert "superdirt" in router.get_registered_destinations()
        assert "volca" in router.get_registered_destinations()

    def test_validate_osc_message_valid(self):
        """Test that valid OSC messages are sent."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("superdirt", sender, protocol="osc")

        msg = ScheduledMessage("superdirt", 1.0, 0, {
            "s": "bd",
            "gain": 0.8,
            "pan": 0.5,
        })
        router.send_messages([msg])

        assert len(sender.messages) == 1
        assert sender.messages[0] == {"s": "bd", "gain": 0.8, "pan": 0.5}

    def test_validate_osc_message_invalid(self, caplog):
        """Test that invalid OSC messages are rejected and logged."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("superdirt", sender, protocol="osc")

        # Invalid OSC message: list params not supported
        msg = ScheduledMessage("superdirt", 1.0, 0, {
            "s": "bd",
            "notes": [60, 64, 67],  # Invalid: list
        })

        router.send_messages([msg])

        # Message should be rejected
        assert len(sender.messages) == 0
        # Should log warning
        assert "Invalid OSC message" in caplog.text

    def test_validate_midi_message_valid(self):
        """Test that valid MIDI messages are sent."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("volca", sender, protocol="midi")

        msg = ScheduledMessage("volca", 1.0, 0, {
            "channel": 0,
            "note": 60,
            "velocity": 100,
        })
        router.send_messages([msg])

        assert len(sender.messages) == 1
        assert sender.messages[0] == {"channel": 0, "note": 60, "velocity": 100}

    def test_validate_midi_message_invalid(self, caplog):
        """Test that invalid MIDI messages are rejected and logged."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("volca", sender, protocol="midi")

        # Invalid MIDI message: note out of range
        msg = ScheduledMessage("volca", 1.0, 0, {
            "note": 200,  # Invalid: > 127
            "velocity": 100,
        })

        router.send_messages([msg])

        # Message should be rejected
        assert len(sender.messages) == 0
        # Should log warning
        assert "Invalid MIDI message" in caplog.text

    def test_validate_mixed_valid_and_invalid(self, caplog):
        """Test that valid messages are sent while invalid ones are rejected."""
        router = DestinationRouter()
        sender = MockDestinationSender()
        router.register_destination("superdirt", sender, protocol="osc")

        msg1 = ScheduledMessage("superdirt", 1.0, 0, {"s": "bd", "gain": 0.8})  # Valid
        msg2 = ScheduledMessage("superdirt", 1.0, 1, {"s": "sn", "notes": [1, 2]})  # Invalid
        msg3 = ScheduledMessage("superdirt", 1.0, 2, {"s": "hh", "pan": 0.5})  # Valid

        router.send_messages([msg1, msg2, msg3])

        # Only valid messages should be sent
        assert len(sender.messages) == 2
        assert sender.messages[0] == {"s": "bd", "gain": 0.8}
        assert sender.messages[1] == {"s": "hh", "pan": 0.5}

    def test_custom_validators(self):
        """Test router with custom validators."""
        custom_osc = OscValidator()
        custom_midi = MidiValidator()
        router = DestinationRouter(osc_validator=custom_osc, midi_validator=custom_midi)
        sender = MockDestinationSender()
        router.register_destination("superdirt", sender, protocol="osc")

        msg = ScheduledMessage("superdirt", 1.0, 0, {"s": "bd"})
        router.send_messages([msg])

        assert len(sender.messages) == 1
