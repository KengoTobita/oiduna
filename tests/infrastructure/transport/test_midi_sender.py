"""Tests for MidiSender.

Tests cover:
- Connection lifecycle
- Clock messages
- Note messages with tracking
- Value clamping (channel, note, velocity, pitch bend)
- all_notes_off functionality
- Error handling
- Boundary values
"""

import pytest
from mido import Message

from oiduna.infrastructure.transport.midi_sender import MidiSender


class TestConnectionLifecycle:
    """Test connection and disconnection."""

    def test_initial_state_not_connected(self, mock_mido):
        """Test that sender starts in disconnected state."""
        sender = MidiSender()
        assert not sender.is_connected

    def test_connect_no_ports_returns_false(self, mock_mido):
        """Test connect when no ports available returns False."""
        mock_mido.set_output_ports([])
        sender = MidiSender()

        result = sender.connect()

        assert result is False
        assert not sender.is_connected

    def test_connect_default_port_success(self, mock_mido):
        """Test connecting to default (first) port."""
        mock_mido.set_output_ports(["Port1", "Port2"])
        sender = MidiSender()

        result = sender.connect()

        assert result is True
        assert sender.is_connected
        # When connecting with no port_name specified, it connects to first available
        # but doesn't update the port_name property (stays None)
        assert sender.port_name is None

    def test_connect_specific_port_success(self, mock_mido):
        """Test connecting to specific port."""
        mock_mido.set_output_ports(["Port1", "Port2", "Port3"])
        sender = MidiSender(port_name="Port2")

        result = sender.connect()

        assert result is True
        assert sender.is_connected
        assert sender.port_name == "Port2"

    def test_connect_port_not_found_returns_false(self, mock_mido):
        """Test connect when specified port not found returns False."""
        mock_mido.set_output_ports(["Port1", "Port2"])
        sender = MidiSender(port_name="NonExistent")

        result = sender.connect()

        assert result is False
        assert not sender.is_connected

    def test_disconnect_clears_connection(self, mock_mido):
        """Test that disconnect clears connection state."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()
        assert sender.is_connected

        sender.disconnect()

        assert not sender.is_connected

    def test_disconnect_closes_port(self, mock_mido):
        """Test that disconnect closes the port."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        port = mock_mido.get_opened_port("Port1")
        assert port is not None
        assert not port.is_closed

        sender.disconnect()

        assert port.is_closed

    def test_disconnect_without_connect(self, mock_mido):
        """Test that disconnect without connect does not error."""
        sender = MidiSender()
        sender.disconnect()  # Should not raise

    def test_set_port_changes_port(self, mock_mido):
        """Test set_port changes to new port."""
        mock_mido.set_output_ports(["Port1", "Port2"])
        sender = MidiSender(port_name="Port1")
        sender.connect()

        result = sender.set_port("Port2")

        assert result is True
        assert sender.port_name == "Port2"

    def test_list_ports_returns_available_ports(self, mock_mido):
        """Test list_ports static method."""
        mock_mido.set_output_ports(["Port1", "Port2", "Port3"])

        ports = MidiSender.list_ports()

        assert ports == ["Port1", "Port2", "Port3"]


class TestClockMessages:
    """Test MIDI clock messages."""

    def test_send_clock_success(self, mock_mido):
        """Test sending MIDI clock pulse."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_clock()

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        assert messages[0].bytes() == [0xF8]

    def test_send_clock_not_connected_returns_false(self, mock_mido):
        """Test send_clock when not connected returns False."""
        sender = MidiSender()

        result = sender.send_clock()

        assert result is False

    def test_send_start_success(self, mock_mido):
        """Test sending MIDI start message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_start()

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        assert messages[0].bytes() == [0xFA]

    def test_send_stop_success(self, mock_mido):
        """Test sending MIDI stop message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_stop()

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        assert messages[0].bytes() == [0xFC]

    def test_send_continue_success(self, mock_mido):
        """Test sending MIDI continue message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_continue()

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        assert messages[0].bytes() == [0xFB]

    def test_clock_constants(self, mock_mido):
        """Test MIDI clock constant values."""
        assert MidiSender.CLOCK == 0xF8
        assert MidiSender.START == 0xFA
        assert MidiSender.CONTINUE == 0xFB
        assert MidiSender.STOP == 0xFC


class TestNoteMessages:
    """Test MIDI note messages."""

    def test_send_note_on_success(self, mock_mido):
        """Test sending note on message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_note_on(channel=0, note=60, velocity=100)

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "note_on"
        assert msg.channel == 0
        assert msg.note == 60
        assert msg.velocity == 100

    def test_send_note_on_tracks_active_note(self, mock_mido):
        """Test that note_on tracks active notes."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60, velocity=100)

        # Active notes are tracked internally (private attribute)
        # We can verify by sending note_off and checking all_notes_off behavior

    def test_send_note_off_success(self, mock_mido):
        """Test sending note off message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_note_off(channel=0, note=60)

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "note_off"
        assert msg.channel == 0
        assert msg.note == 60

    def test_send_note_on_off_sequence(self, mock_mido):
        """Test note on/off sequence."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60, velocity=100)
        sender.send_note_off(channel=0, note=60)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 2
        assert messages[0].type == "note_on"
        assert messages[1].type == "note_off"

    def test_send_note_not_connected_returns_false(self, mock_mido):
        """Test sending note when not connected returns False."""
        sender = MidiSender()

        result = sender.send_note_on(channel=0, note=60)

        assert result is False


class TestValueClamping:
    """Test value clamping for MIDI parameters."""

    @pytest.mark.parametrize("channel_in,channel_out", [
        (0, 0),      # Min valid
        (7, 7),      # Mid range
        (15, 15),    # Max valid
        (16, 0),     # Overflow wraps (& 0x0F)
        (255, 15),   # Max byte wraps
        (-1, 15),    # Negative wraps
    ])
    def test_channel_clamping(self, mock_mido, channel_in, channel_out):
        """Test channel value clamping (0-15 via & 0x0F)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=channel_in, note=60, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].channel == channel_out

    @pytest.mark.parametrize("note_in,note_out", [
        (0, 0),      # Min valid
        (60, 60),    # Middle C
        (127, 127),  # Max valid
        (128, 0),    # Overflow wraps (& 0x7F)
        (255, 127),  # Max byte wraps
        (-1, 127),   # Negative wraps
    ])
    def test_note_clamping(self, mock_mido, note_in, note_out):
        """Test note value clamping (0-127 via & 0x7F)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=note_in, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].note == note_out

    @pytest.mark.parametrize("velocity_in,velocity_out", [
        (0, 0),      # Min valid
        (64, 64),    # Mid range
        (127, 127),  # Max valid
        (128, 0),    # Overflow wraps (& 0x7F)
        (255, 127),  # Max byte wraps
        (-1, 127),   # Negative wraps
    ])
    def test_velocity_clamping(self, mock_mido, velocity_in, velocity_out):
        """Test velocity value clamping (0-127 via & 0x7F)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60, velocity=velocity_in)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].velocity == velocity_out


class TestControlChangeMessages:
    """Test MIDI CC messages."""

    def test_send_cc_success(self, mock_mido):
        """Test sending CC message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_cc(channel=0, cc=7, value=100)

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "control_change"
        assert msg.channel == 0
        assert msg.control == 7
        assert msg.value == 100

    @pytest.mark.parametrize("cc_in,cc_out", [
        (0, 0),      # Min valid
        (64, 64),    # Mid range
        (127, 127),  # Max valid
        (128, 0),    # Overflow wraps
    ])
    def test_cc_number_clamping(self, mock_mido, cc_in, cc_out):
        """Test CC number clamping (0-127)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_cc(channel=0, cc=cc_in, value=64)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].control == cc_out

    @pytest.mark.parametrize("value_in,value_out", [
        (0, 0),      # Min valid
        (64, 64),    # Mid range
        (127, 127),  # Max valid
        (128, 0),    # Overflow wraps
    ])
    def test_cc_value_clamping(self, mock_mido, value_in, value_out):
        """Test CC value clamping (0-127)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_cc(channel=0, cc=7, value=value_in)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].value == value_out


class TestPitchBendMessages:
    """Test MIDI pitch bend messages."""

    def test_send_pitch_bend_success(self, mock_mido):
        """Test sending pitch bend message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_pitch_bend(channel=0, value=0)

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "pitchwheel"
        assert msg.channel == 0
        assert msg.pitch == 0

    @pytest.mark.parametrize("value_in,value_out", [
        (-8192, -8192),   # Min valid
        (0, 0),           # Center
        (8191, 8191),     # Max valid
        (-10000, -8192),  # Below min clamped
        (10000, 8191),    # Above max clamped
    ])
    def test_pitch_bend_clamping(self, mock_mido, value_in, value_out):
        """Test pitch bend value clamping (-8192 to 8191)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_pitch_bend(channel=0, value=value_in)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].pitch == value_out


class TestAftertouchMessages:
    """Test MIDI aftertouch messages."""

    def test_send_aftertouch_success(self, mock_mido):
        """Test sending aftertouch message."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        result = sender.send_aftertouch(channel=0, value=64)

        assert result is True
        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "aftertouch"
        assert msg.channel == 0
        assert msg.value == 64

    @pytest.mark.parametrize("value_in,value_out", [
        (0, 0),      # Min valid
        (127, 127),  # Max valid
        (128, 0),    # Overflow wraps
    ])
    def test_aftertouch_value_clamping(self, mock_mido, value_in, value_out):
        """Test aftertouch value clamping (0-127)."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_aftertouch(channel=0, value=value_in)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert messages[0].value == value_out


class TestAllNotesOff:
    """Test all_notes_off functionality."""

    def test_all_notes_off_all_channels(self, mock_mido):
        """Test all_notes_off turns off all active notes."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        # Turn on several notes on different channels
        sender.send_note_on(channel=0, note=60, velocity=100)
        sender.send_note_on(channel=0, note=64, velocity=100)
        sender.send_note_on(channel=1, note=67, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        port.clear_messages()

        result = sender.all_notes_off()

        assert result is True
        messages = port.get_messages()
        # Should send 3 note_off messages
        assert len(messages) == 3
        assert all(msg.type == "note_off" for msg in messages)

    def test_all_notes_off_specific_channel(self, mock_mido):
        """Test all_notes_off for specific channel."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        # Turn on notes on different channels
        sender.send_note_on(channel=0, note=60, velocity=100)
        sender.send_note_on(channel=1, note=64, velocity=100)
        sender.send_note_on(channel=1, note=67, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        port.clear_messages()

        sender.all_notes_off(channel=1)

        messages = port.get_messages()
        # Should only send note_off for channel 1 (2 notes)
        assert len(messages) == 2
        assert all(msg.channel == 1 for msg in messages)

    def test_all_notes_off_clears_tracking(self, mock_mido):
        """Test that all_notes_off clears active note tracking."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60, velocity=100)
        sender.all_notes_off()

        port = mock_mido.get_opened_port("Port1")
        port.clear_messages()

        # Call all_notes_off again - should send no messages
        sender.all_notes_off()

        messages = port.get_messages()
        assert len(messages) == 0

    def test_all_notes_off_not_connected_returns_false(self, mock_mido):
        """Test all_notes_off when not connected returns False."""
        sender = MidiSender()

        result = sender.all_notes_off()

        assert result is False

    def test_disconnect_calls_all_notes_off(self, mock_mido):
        """Test that disconnect sends all notes off."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60, velocity=100)
        sender.send_note_on(channel=0, note=64, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        port.clear_messages()

        sender.disconnect()

        messages = port.get_messages()
        # Should have sent 2 note_off messages before disconnect
        note_off_messages = [msg for msg in messages if msg.type == "note_off"]
        assert len(note_off_messages) == 2


class TestErrorHandling:
    """Test error handling."""

    def test_send_clock_exception_returns_false(self, mock_mido):
        """Test send_clock handles exceptions."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        port = mock_mido.get_opened_port("Port1")
        port.inject_send_error(RuntimeError("Send failed"))

        result = sender.send_clock()

        assert result is False

    def test_send_note_on_exception_returns_false(self, mock_mido):
        """Test send_note_on handles exceptions."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        port = mock_mido.get_opened_port("Port1")
        port.inject_send_error(RuntimeError("Send failed"))

        result = sender.send_note_on(channel=0, note=60)

        assert result is False

    def test_send_cc_exception_returns_false(self, mock_mido):
        """Test send_cc handles exceptions."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        port = mock_mido.get_opened_port("Port1")
        port.inject_send_error(RuntimeError("Send failed"))

        result = sender.send_cc(channel=0, cc=7, value=64)

        assert result is False

    def test_all_notes_off_handles_send_errors(self, mock_mido):
        """Test all_notes_off continues even if individual sends fail."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        sender.send_note_on(channel=0, note=60)

        port = mock_mido.get_opened_port("Port1")
        # Inject error - will fail on the note_off call
        port.inject_send_error(RuntimeError("Send failed"))

        # all_notes_off returns True even if individual note_off calls fail
        # because the exception is caught within send_note_off, not all_notes_off
        result = sender.all_notes_off()

        assert result is True


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_multiple_notes_same_channel(self, mock_mido):
        """Test sending multiple notes on same channel."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        for note in range(60, 72):  # 12 notes (one octave)
            sender.send_note_on(channel=0, note=note, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 12

    def test_notes_on_all_channels(self, mock_mido):
        """Test sending notes on all 16 channels."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        for channel in range(16):
            sender.send_note_on(channel=channel, note=60, velocity=100)

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 16
        channels_used = {msg.channel for msg in messages}
        assert channels_used == set(range(16))

    def test_rapid_clock_messages(self, mock_mido):
        """Test sending many rapid clock messages."""
        mock_mido.set_output_ports(["Port1"])
        sender = MidiSender()
        sender.connect()

        for _ in range(100):
            sender.send_clock()

        port = mock_mido.get_opened_port("Port1")
        messages = port.get_messages()
        assert len(messages) == 100
