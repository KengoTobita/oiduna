"""Tests for OscDestinationSender and MidiDestinationSender.

Tests cover:
- OscDestinationSender: initialization, send_message, send_bundle
- MidiDestinationSender: initialization, send_message, send_bundle, close
- Message format conversion
- Default values
- Repr methods
"""

import pytest

from oiduna.infrastructure.transport.senders import (
    OscDestinationSender,
    MidiDestinationSender,
)


class TestOscDestinationSender:
    """Test OscDestinationSender."""

    def test_init_creates_client(self, mock_osc_client):
        """Test initialization creates OSC client."""
        sender = OscDestinationSender(
            host="192.168.1.100",
            port=9000,
            address="/custom/addr"
        )

        assert sender.host == "192.168.1.100"
        assert sender.port == 9000
        assert sender.address == "/custom/addr"
        assert sender.use_bundle is False

        # Verify client was created
        client = mock_osc_client.get_client()
        assert client is not None
        assert client.host == "192.168.1.100"
        assert client.port == 9000

    def test_init_with_use_bundle(self, mock_osc_client):
        """Test initialization with use_bundle flag."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play",
            use_bundle=True
        )

        assert sender.use_bundle is True

    def test_send_message_converts_params_to_args(self, mock_osc_client):
        """Test send_message converts params dict to OSC args format."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        sender.send_message({"s": "bd", "gain": 0.8})

        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 1
        address, args = messages[0]
        assert address == "/dirt/play"
        assert args == ["s", "bd", "gain", 0.8]

    def test_send_message_multiple_params(self, mock_osc_client):
        """Test send_message with multiple parameters."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        sender.send_message({
            "s": "sn",
            "n": 2,
            "gain": 0.5,
            "pan": 0.25
        })

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        # Args should alternate keys and values
        assert "s" in args and "sn" in args
        assert "n" in args and 2 in args
        assert "gain" in args and 0.5 in args
        assert "pan" in args and 0.25 in args

    def test_send_message_empty_params(self, mock_osc_client):
        """Test send_message with empty params dict."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        sender.send_message({})

        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 1
        _, args = messages[0]
        assert args == []

    def test_send_bundle_sends_multiple_messages(self, mock_osc_client):
        """Test send_bundle sends multiple messages."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        messages = [
            {"s": "bd", "gain": 0.8},
            {"s": "sn", "gain": 0.7},
            {"s": "hh", "gain": 0.6},
        ]

        sender.send_bundle(messages)

        client = mock_osc_client.get_client()
        sent_messages = client.get_messages()

        assert len(sent_messages) == 3
        assert sent_messages[0][1] == ["s", "bd", "gain", 0.8]
        assert sent_messages[1][1] == ["s", "sn", "gain", 0.7]
        assert sent_messages[2][1] == ["s", "hh", "gain", 0.6]

    def test_send_bundle_empty_list(self, mock_osc_client):
        """Test send_bundle with empty message list."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        sender.send_bundle([])

        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 0

    def test_repr(self, mock_osc_client):
        """Test __repr__ method."""
        sender = OscDestinationSender(
            host="192.168.1.100",
            port=9000,
            address="/custom/addr"
        )

        repr_str = repr(sender)

        assert "OscDestinationSender" in repr_str
        assert "192.168.1.100" in repr_str
        assert "9000" in repr_str
        assert "/custom/addr" in repr_str

    def test_custom_address_used(self, mock_osc_client):
        """Test that custom address is used for messages."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/tidal/play"
        )

        sender.send_message({"s": "bd"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        address, _ = messages[0]

        assert address == "/tidal/play"

    def test_send_unicode_params(self, mock_osc_client):
        """Test sending unicode string parameters."""
        sender = OscDestinationSender(
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )

        sender.send_message({"s": "音楽", "name": "Ødúná 🎵"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert "音楽" in args
        assert "Ødúná 🎵" in args


class TestMidiDestinationSender:
    """Test MidiDestinationSender."""

    def test_init_opens_port(self, mock_mido):
        """Test initialization opens MIDI port."""
        mock_mido.set_output_ports(["Port1", "Port2"])

        sender = MidiDestinationSender(
            port_name="Port1",
            default_channel=5
        )

        assert sender.port_name == "Port1"
        assert sender.default_channel == 5

        port = mock_mido.get_opened_port("Port1")
        assert port is not None
        assert port.name == "Port1"

    def test_init_default_channel(self, mock_mido):
        """Test initialization with default channel."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        assert sender.default_channel == 0

    def test_send_note_message(self, mock_mido):
        """Test sending note message."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "note": 60,
            "velocity": 100,
            "duration_ms": 250
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()

        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "note_on"
        assert msg.note == 60
        assert msg.velocity == 100
        assert msg.channel == 0

    def test_send_note_with_custom_channel(self, mock_mido):
        """Test sending note with custom channel."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "note": 60,
            "velocity": 100,
            "channel": 5
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.channel == 5

    def test_send_note_uses_default_channel(self, mock_mido):
        """Test note message uses default channel when not specified."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=7)

        sender.send_message({
            "note": 60,
            "velocity": 100
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.channel == 7

    def test_send_note_default_velocity(self, mock_mido):
        """Test note message uses default velocity."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        sender.send_message({"note": 60})

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.velocity == 100

    def test_send_cc_message(self, mock_mido):
        """Test sending CC message."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "cc": 74,
            "value": 64
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()

        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "control_change"
        assert msg.control == 74
        assert msg.value == 64
        assert msg.channel == 0

    def test_send_cc_with_custom_channel(self, mock_mido):
        """Test CC message with custom channel."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "cc": 7,
            "value": 127,
            "channel": 3
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.channel == 3

    def test_send_cc_default_value(self, mock_mido):
        """Test CC message uses default value."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        sender.send_message({"cc": 74})

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.value == 0

    def test_send_pitch_bend_message(self, mock_mido):
        """Test sending pitch bend message."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "pitch_bend": 4096
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()

        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "pitchwheel"
        assert msg.pitch == 4096
        assert msg.channel == 0

    def test_send_pitch_bend_with_custom_channel(self, mock_mido):
        """Test pitch bend with custom channel."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1", default_channel=0)

        sender.send_message({
            "pitch_bend": 4096,
            "channel": 9
        })

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        msg = messages[0]

        assert msg.channel == 9

    def test_send_bundle_sends_multiple_messages(self, mock_mido):
        """Test send_bundle sends multiple messages."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        messages = [
            {"note": 60, "velocity": 100},
            {"note": 64, "velocity": 80},
            {"note": 67, "velocity": 90},
        ]

        sender.send_bundle(messages)

        port = mock_mido.get_opened_port("Port1")
        sent_messages = port.get_messages()

        assert len(sent_messages) == 3
        assert sent_messages[0].note == 60
        assert sent_messages[1].note == 64
        assert sent_messages[2].note == 67

    def test_send_bundle_mixed_message_types(self, mock_mido):
        """Test send_bundle with mixed message types."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        messages = [
            {"note": 60, "velocity": 100},
            {"cc": 7, "value": 127},
            {"pitch_bend": 4096},
        ]

        sender.send_bundle(messages)

        port = mock_mido.get_opened_port("Port1")
        sent_messages = port.get_messages()

        assert len(sent_messages) == 3
        assert sent_messages[0].type == "note_on"
        assert sent_messages[1].type == "control_change"
        assert sent_messages[2].type == "pitchwheel"

    def test_send_bundle_empty_list(self, mock_mido):
        """Test send_bundle with empty message list."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")

        sender.send_bundle([])

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()

        assert len(messages) == 0

    def test_close_closes_port(self, mock_mido):
        """Test close() closes MIDI port."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")
        port = mock_mido.get_opened_port("Port1")

        assert not port.is_closed

        sender.close()

        assert port.is_closed

    def test_repr(self, mock_mido):
        """Test __repr__ method."""
        mock_mido.set_output_ports(["USB MIDI 1"])

        sender = MidiDestinationSender(
            port_name="USB MIDI 1",
            default_channel=5
        )

        repr_str = repr(sender)

        assert "MidiDestinationSender" in repr_str
        assert "USB MIDI 1" in repr_str
        assert "5" in repr_str

    def test_del_closes_port(self, mock_mido):
        """Test __del__ closes port on cleanup."""
        mock_mido.set_output_ports(["Port1"])

        sender = MidiDestinationSender(port_name="Port1")
        port = mock_mido.get_opened_port("Port1")

        assert not port.is_closed

        # Trigger __del__
        del sender

        assert port.is_closed
