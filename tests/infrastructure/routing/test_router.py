"""Tests for DestinationRouter.

Tests cover:
- Destination registration and unregistration
- Message routing (single and multiple destinations)
- Protocol validation (OSC/MIDI)
- Error handling (invalid messages, unregistered destinations)
- Helper methods (get_registered_destinations, has_destination)
"""

import pytest

from oiduna.infrastructure.routing.router import DestinationRouter
from oiduna.domain.schedule.models import ScheduleEntry
from oiduna.domain.schedule.validators import OscValidator, MidiValidator


class TestDestinationRegistration:
    """Test destination registration and unregistration."""

    def test_register_destination_osc(self, mock_sender):
        """Test registering OSC destination."""
        router = DestinationRouter()

        router.register_destination("superdirt", mock_sender, protocol="osc")

        assert router.has_destination("superdirt")
        assert "superdirt" in router.get_registered_destinations()

    def test_register_destination_midi(self, mock_sender):
        """Test registering MIDI destination."""
        router = DestinationRouter()

        router.register_destination("volca", mock_sender, protocol="midi")

        assert router.has_destination("volca")
        assert "volca" in router.get_registered_destinations()

    def test_register_multiple_destinations(self, mock_sender_factory):
        """Test registering multiple destinations."""
        router = DestinationRouter()
        sender1 = mock_sender_factory.create("sender1")
        sender2 = mock_sender_factory.create("sender2")

        router.register_destination("dest1", sender1, protocol="osc")
        router.register_destination("dest2", sender2, protocol="midi")

        destinations = router.get_registered_destinations()
        assert len(destinations) == 2
        assert "dest1" in destinations
        assert "dest2" in destinations

    def test_register_destination_default_protocol(self, mock_sender):
        """Test default protocol is 'osc'."""
        router = DestinationRouter()

        router.register_destination("default", mock_sender)

        # Protocol should default to "osc"
        assert router.has_destination("default")

    def test_unregister_destination(self, mock_sender):
        """Test unregistering destination."""
        router = DestinationRouter()
        router.register_destination("temp", mock_sender)

        assert router.has_destination("temp")

        router.unregister_destination("temp")

        assert not router.has_destination("temp")
        assert "temp" not in router.get_registered_destinations()

    def test_unregister_nonexistent_destination(self, mock_sender):
        """Test unregistering nonexistent destination does not error."""
        router = DestinationRouter()

        router.unregister_destination("nonexistent")  # Should not raise

        assert not router.has_destination("nonexistent")

    def test_register_replaces_existing(self, mock_sender_factory):
        """Test re-registering destination replaces the old one."""
        router = DestinationRouter()
        sender1 = mock_sender_factory.create("sender1")
        sender2 = mock_sender_factory.create("sender2")

        router.register_destination("dest", sender1, protocol="osc")
        router.register_destination("dest", sender2, protocol="midi")

        # Should still have only one destination with that ID
        assert len(router.get_registered_destinations()) == 1


class TestMessageRouting:
    """Test message routing to destinations."""

    def test_send_single_message_to_destination(self, mock_sender):
        """Test sending single message to destination."""
        router = DestinationRouter()
        router.register_destination("dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(
                destination_id="dest",
                offset=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8}
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1
        assert sent[0] == {"s": "bd", "gain": 0.8}

    def test_send_multiple_messages_same_destination(self, mock_sender):
        """Test sending multiple messages to same destination."""
        router = DestinationRouter()
        router.register_destination("dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=0, params={"s": "bd"}),
            ScheduleEntry(destination_id="dest", offset=0.0, step=64, params={"s": "sn"}),
            ScheduleEntry(destination_id="dest", offset=0.0, step=128, params={"s": "hh"}),
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 3
        assert sent[0] == {"s": "bd"}
        assert sent[1] == {"s": "sn"}
        assert sent[2] == {"s": "hh"}

    def test_send_messages_to_multiple_destinations(self, mock_sender_factory):
        """Test routing messages to multiple destinations."""
        router = DestinationRouter()
        sender1 = mock_sender_factory.create("sender1")
        sender2 = mock_sender_factory.create("sender2")

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

    def test_send_empty_message_list(self, mock_sender):
        """Test sending empty message list does nothing."""
        router = DestinationRouter()
        router.register_destination("dest", mock_sender)

        router.send_messages([])

        sent = mock_sender.get_messages()
        assert len(sent) == 0

    def test_send_to_unregistered_destination(self, mock_sender):
        """Test sending to unregistered destination is silently skipped."""
        router = DestinationRouter()
        router.register_destination("dest1", mock_sender)

        messages = [
            ScheduleEntry(destination_id="dest2", offset=0.0, step=0, params={"s": "bd"}),
        ]

        router.send_messages(messages)  # Should not raise

        sent = mock_sender.get_messages()
        assert len(sent) == 0  # Message to dest2 was skipped


class TestProtocolValidation:
    """Test OSC and MIDI protocol validation."""

    def test_osc_valid_message_sent(self, mock_sender):
        """Test valid OSC message is sent."""
        router = DestinationRouter()
        router.register_destination("osc_dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(
                destination_id="osc_dest",
                offset=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8}
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1

    def test_osc_invalid_message_skipped(self, mock_sender):
        """Test invalid OSC message is skipped."""
        router = DestinationRouter()
        router.register_destination("osc_dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(
                destination_id="osc_dest",
                offset=0.0,
                step=0,
                params={"invalid key": "value"}  # Space in key is forbidden
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 0  # Invalid message was skipped

    def test_osc_mixed_valid_invalid_messages(self, mock_sender):
        """Test that only valid OSC messages are sent."""
        router = DestinationRouter()
        router.register_destination("osc_dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(destination_id="osc_dest", offset=0.0, step=0, params={"s": "bd"}),  # Valid
            ScheduleEntry(destination_id="osc_dest", offset=0.0, step=64, params={"bad key": "x"}),  # Invalid
            ScheduleEntry(destination_id="osc_dest", offset=0.0, step=128, params={"s": "hh"}),  # Valid
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 2  # Only 2 valid messages
        assert sent[0] == {"s": "bd"}
        assert sent[1] == {"s": "hh"}

    def test_midi_valid_note_message_sent(self, mock_sender):
        """Test valid MIDI note message is sent."""
        router = DestinationRouter()
        router.register_destination("midi_dest", mock_sender, protocol="midi")

        messages = [
            ScheduleEntry(
                destination_id="midi_dest",
                offset=0.0,
                step=0,
                params={"note": 60, "velocity": 100}
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1
        assert sent[0] == {"note": 60, "velocity": 100}

    def test_midi_invalid_note_message_skipped(self, mock_sender):
        """Test invalid MIDI note message is skipped."""
        router = DestinationRouter()
        router.register_destination("midi_dest", mock_sender, protocol="midi")

        messages = [
            ScheduleEntry(
                destination_id="midi_dest",
                offset=0.0,
                step=0,
                params={"note": 128}  # Out of range (0-127)
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 0  # Invalid message was skipped

    def test_midi_valid_cc_message_sent(self, mock_sender):
        """Test valid MIDI CC message is sent."""
        router = DestinationRouter()
        router.register_destination("midi_dest", mock_sender, protocol="midi")

        messages = [
            ScheduleEntry(
                destination_id="midi_dest",
                offset=0.0,
                step=0,
                params={"cc": 7, "value": 127}
            )
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1


class TestHelperMethods:
    """Test helper methods."""

    def test_get_registered_destinations_empty(self):
        """Test get_registered_destinations with no destinations."""
        router = DestinationRouter()

        destinations = router.get_registered_destinations()

        assert destinations == []

    def test_get_registered_destinations_returns_list(self, mock_sender_factory):
        """Test get_registered_destinations returns list of IDs."""
        router = DestinationRouter()
        router.register_destination("dest1", mock_sender_factory.create())
        router.register_destination("dest2", mock_sender_factory.create())
        router.register_destination("dest3", mock_sender_factory.create())

        destinations = router.get_registered_destinations()

        assert len(destinations) == 3
        assert set(destinations) == {"dest1", "dest2", "dest3"}

    def test_has_destination_returns_true_when_registered(self, mock_sender):
        """Test has_destination returns True for registered destination."""
        router = DestinationRouter()
        router.register_destination("exists", mock_sender)

        assert router.has_destination("exists") is True

    def test_has_destination_returns_false_when_not_registered(self):
        """Test has_destination returns False for unregistered destination."""
        router = DestinationRouter()

        assert router.has_destination("nonexistent") is False

    def test_has_destination_after_unregister(self, mock_sender):
        """Test has_destination returns False after unregistering."""
        router = DestinationRouter()
        router.register_destination("temp", mock_sender)

        assert router.has_destination("temp") is True

        router.unregister_destination("temp")

        assert router.has_destination("temp") is False


class TestCustomValidators:
    """Test router with custom validators."""

    def test_router_with_custom_osc_validator(self, mock_sender):
        """Test router accepts custom OSC validator."""
        custom_validator = OscValidator()
        router = DestinationRouter(osc_validator=custom_validator)

        router.register_destination("dest", mock_sender, protocol="osc")

        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=0, params={"s": "bd"})
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1

    def test_router_with_custom_midi_validator(self, mock_sender):
        """Test router accepts custom MIDI validator."""
        custom_validator = MidiValidator()
        router = DestinationRouter(midi_validator=custom_validator)

        router.register_destination("dest", mock_sender, protocol="midi")

        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=0, params={"note": 60})
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 1


class TestOptimizationPaths:
    """Test optimization for single vs multiple destinations."""

    def test_single_destination_optimization_path(self, mock_sender):
        """Test single destination uses fast path."""
        router = DestinationRouter()
        router.register_destination("dest", mock_sender)

        # All messages to same destination
        messages = [
            ScheduleEntry(destination_id="dest", offset=0.0, step=i, params={"s": "bd"})
            for i in range(10)
        ]

        router.send_messages(messages)

        sent = mock_sender.get_messages()
        assert len(sent) == 10

    def test_multiple_destinations_grouping_path(self, mock_sender_factory):
        """Test multiple destinations uses grouping path."""
        router = DestinationRouter()
        sender1 = mock_sender_factory.create("sender1")
        sender2 = mock_sender_factory.create("sender2")

        router.register_destination("dest1", sender1)
        router.register_destination("dest2", sender2)

        # Messages to different destinations
        messages = [
            ScheduleEntry(destination_id="dest1", offset=0.0, step=0, params={"s": "bd"}),
            ScheduleEntry(destination_id="dest2", offset=0.0, step=0, params={"s": "sn"}),
            ScheduleEntry(destination_id="dest1", offset=0.0, step=64, params={"s": "hh"}),
            ScheduleEntry(destination_id="dest2", offset=0.0, step=64, params={"s": "cp"}),
        ]

        router.send_messages(messages)

        sent1 = sender1.get_messages()
        sent2 = sender2.get_messages()

        assert len(sent1) == 2
        assert len(sent2) == 2
