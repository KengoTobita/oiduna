"""Integration tests for Transport layer.

Tests the integration between:
- DestinationRouter and senders (OSC/MIDI)
- ScheduleEntry routing to correct destinations
- Protocol validation before sending
- Multiple destinations handling
"""

import pytest
import sys
from pathlib import Path
from typing import Any

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from oiduna.infrastructure.routing.router import DestinationRouter
from oiduna.domain.schedule.models import ScheduleEntry
from infrastructure.routing.conftest import MockDestinationSender


class TestRouterWithMockSenders:
    """Test DestinationRouter with mock senders."""

    def test_route_single_message_to_destination(self):
        """Test routing single message to destination."""
        router = DestinationRouter()
        sender = MockDestinationSender("test_dest")

        router.register_destination("dest1", sender, protocol="osc")

        messages = [
            ScheduleEntry(
                destination_id="dest1",
                offset=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8}
            )
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1
        assert sent[0] == {"s": "bd", "gain": 0.8}

    def test_route_to_multiple_destinations(self):
        """Test routing messages to multiple destinations."""
        router = DestinationRouter()
        sender1 = MockDestinationSender("dest1")
        sender2 = MockDestinationSender("dest2")

        router.register_destination("dest1", sender1, protocol="osc")
        router.register_destination("dest2", sender2, protocol="osc")

        messages = [
            ScheduleEntry(destination_id="dest1", offset=0.0, step=0, params={"s": "bd"}),
            ScheduleEntry(destination_id="dest2", offset=0.0, step=0, params={"s": "sn"}),
            ScheduleEntry(destination_id="dest1", offset=0.0, step=64, params={"s": "hh"}),
        ]

        router.send_messages(messages)

        sent1 = sender1.get_messages()
        sent2 = sender2.get_messages()

        assert len(sent1) == 2
        assert sent1[0] == {"s": "bd"}
        assert sent1[1] == {"s": "hh"}

        assert len(sent2) == 1
        assert sent2[0] == {"s": "sn"}

    def test_unregistered_destination_silently_skipped(self):
        """Test messages to unregistered destinations are skipped."""
        router = DestinationRouter()
        sender = MockDestinationSender("dest1")

        router.register_destination("dest1", sender)

        messages = [
            ScheduleEntry(destination_id="dest1", offset=0.0, step=0, params={"s": "bd"}),
            ScheduleEntry(destination_id="unregistered", offset=0.0, step=0, params={"s": "sn"}),
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1  # Only dest1 message sent

    def test_protocol_validation_osc(self):
        """Test OSC protocol validation."""
        router = DestinationRouter()
        sender = MockDestinationSender("osc_dest")

        router.register_destination("osc_dest", sender, protocol="osc")

        messages = [
            ScheduleEntry(destination_id="osc_dest", offset=0.0, step=0, params={"s": "bd"}),  # Valid
            ScheduleEntry(destination_id="osc_dest", offset=0.0, step=64, params={"bad key": "x"}),  # Invalid (space in key)
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1  # Only valid message sent

    def test_protocol_validation_midi(self):
        """Test MIDI protocol validation."""
        router = DestinationRouter()
        sender = MockDestinationSender("midi_dest")

        router.register_destination("midi_dest", sender, protocol="midi")

        messages = [
            ScheduleEntry(destination_id="midi_dest", offset=0.0, step=0, params={"note": 60, "velocity": 100}),  # Valid
            ScheduleEntry(destination_id="midi_dest", offset=0.0, step=64, params={"note": 128}),  # Invalid (out of range)
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1  # Only valid message sent


class TestScheduleEntryValidation:
    """Test ScheduleEntry validation through routing."""

    def test_osc_message_with_valid_params(self):
        """Test OSC message with valid parameters passes validation."""
        router = DestinationRouter()
        sender = MockDestinationSender("superdirt")

        router.register_destination("superdirt", sender, protocol="osc")

        messages = [
            ScheduleEntry(
                destination_id="superdirt",
                offset=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8, "pan": 0.5}
            )
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1
        assert sent[0]["s"] == "bd"
        assert sent[0]["gain"] == 0.8

    def test_midi_message_with_valid_params(self):
        """Test MIDI message with valid parameters passes validation."""
        router = DestinationRouter()
        sender = MockDestinationSender("volca")

        router.register_destination("volca", sender, protocol="midi")

        messages = [
            ScheduleEntry(
                destination_id="volca",
                offset=0.0,
                step=0,
                params={"note": 60, "velocity": 100, "channel": 0}
            )
        ]

        router.send_messages(messages)

        sent = sender.get_messages()
        assert len(sent) == 1
        assert sent[0]["note"] == 60


class TestMultiDestinationScenario:
    """Test realistic multi-destination scenarios."""

    def test_superdirt_and_midi_destinations(self):
        """Test routing to both SuperDirt (OSC) and MIDI simultaneously."""
        router = DestinationRouter()
        osc_sender = MockDestinationSender("superdirt")
        midi_sender = MockDestinationSender("volca")

        router.register_destination("superdirt", osc_sender, protocol="osc")
        router.register_destination("volca", midi_sender, protocol="midi")

        # Mix of OSC and MIDI messages
        messages = [
            # Kick to SuperDirt
            ScheduleEntry(destination_id="superdirt", offset=0.0, step=0, params={"s": "bd"}),
            # Bass note to MIDI
            ScheduleEntry(destination_id="volca", offset=0.0, step=0, params={"note": 36}),
            # Hihat to SuperDirt
            ScheduleEntry(destination_id="superdirt", offset=0.0, step=32, params={"s": "hh"}),
            # Lead note to MIDI
            ScheduleEntry(destination_id="volca", offset=0.0, step=32, params={"note": 72}),
        ]

        router.send_messages(messages)

        osc_sent = osc_sender.get_messages()
        midi_sent = midi_sender.get_messages()

        assert len(osc_sent) == 2
        assert osc_sent[0] == {"s": "bd"}
        assert osc_sent[1] == {"s": "hh"}

        assert len(midi_sent) == 2
        assert midi_sent[0] == {"note": 36}
        assert midi_sent[1] == {"note": 72}

    def test_dynamic_destination_registration(self):
        """Test registering destinations dynamically."""
        router = DestinationRouter()

        # Start with one destination
        sender1 = MockDestinationSender("dest1")
        router.register_destination("dest1", sender1)

        messages = [
            ScheduleEntry(destination_id="dest1", offset=0.0, step=0, params={"s": "bd"}),
        ]

        router.send_messages(messages)
        assert len(sender1.get_messages()) == 1

        # Add another destination
        sender2 = MockDestinationSender("dest2")
        router.register_destination("dest2", sender2)

        messages = [
            ScheduleEntry(destination_id="dest1", offset=0.0, step=0, params={"s": "sn"}),
            ScheduleEntry(destination_id="dest2", offset=0.0, step=0, params={"s": "hh"}),
        ]

        router.send_messages(messages)

        # dest1 should have 2 total messages (1 old + 1 new)
        assert len(sender1.get_messages()) == 2
        # dest2 should have 1 message
        assert len(sender2.get_messages()) == 1

    def test_destination_replacement(self):
        """Test replacing a destination sender."""
        router = DestinationRouter()
        sender1 = MockDestinationSender("original")
        sender2 = MockDestinationSender("replacement")

        # Register original
        router.register_destination("dest", sender1)

        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=0, params={"s": "bd"}),
        ]

        router.send_messages(messages)
        assert len(sender1.get_messages()) == 1
        assert len(sender2.get_messages()) == 0

        # Replace with new sender
        router.register_destination("dest", sender2)

        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=0, params={"s": "sn"}),
        ]

        router.send_messages(messages)

        # New sender should receive message
        assert len(sender2.get_messages()) == 1
        # Original sender should not receive new message
        assert len(sender1.get_messages()) == 1
