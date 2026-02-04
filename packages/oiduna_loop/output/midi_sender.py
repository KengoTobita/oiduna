"""
MARS Loop MIDI Sender

Sends MIDI clock and notes to external devices.
"""

from __future__ import annotations

import logging

import mido
from mido import Message

logger = logging.getLogger(__name__)


class MidiSender:
    """MIDI Clock and Notes sender"""

    # MIDI Clock Messages
    CLOCK = 0xF8      # Timing Clock
    START = 0xFA      # Start
    CONTINUE = 0xFB   # Continue
    STOP = 0xFC       # Stop

    # Retry configuration (Phase 2: Connection recovery)
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 0.1  # seconds

    def __init__(self, port_name: str | None = None):
        """
        Initialize MIDI sender

        Args:
            port_name: MIDI port name. If None, uses first available.
        """
        self._port_name = port_name
        self._port: mido.ports.BaseOutput | None = None
        self._active_notes: dict[tuple[int, int], int] = {}  # (channel, note) -> velocity

    def connect(self) -> bool:
        """
        Connect to MIDI port

        Returns:
            True if connected successfully
        """
        try:
            available_ports = mido.get_output_names()

            if not available_ports:
                logger.warning("No MIDI output ports available")
                return False

            if self._port_name:
                if self._port_name not in available_ports:
                    logger.warning(f"MIDI port '{self._port_name}' not found")
                    return False
                port_name = self._port_name
            else:
                port_name = available_ports[0]

            self._port = mido.open_output(port_name)
            logger.info(f"MIDI connected to: {port_name}")
            return True

        except Exception as e:
            logger.error(f"MIDI connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Close MIDI port"""
        if self._port:
            # Send all notes off
            self.all_notes_off()
            self._port.close()
            self._port = None
            logger.info("MIDI disconnected")

    @property
    def is_connected(self) -> bool:
        return self._port is not None

    @property
    def port_name(self) -> str | None:
        """Get current port name"""
        return self._port_name

    def set_port(self, port_name: str) -> bool:
        """
        Change MIDI output port.

        Disconnects from current port and connects to the new one.

        Args:
            port_name: New MIDI port name

        Returns:
            True if successfully connected to new port
        """
        # Disconnect from current port if connected
        if self._port:
            self.disconnect()

        # Set new port name and connect
        self._port_name = port_name
        return self.connect()

    # ================================================================
    # Clock Messages
    # ================================================================

    def _send_system_realtime(self, status_byte: int, msg_name: str, log_msg: bool = False) -> bool:
        """
        Send MIDI system realtime message (Template Method).

        Args:
            status_byte: MIDI status byte (0xF8-0xFF)
            msg_name: Message name for error logging
            log_msg: Whether to log successful sends
        """
        if not self._port:
            return False
        try:
            self._port.send(Message.from_bytes([status_byte]))
            if log_msg:
                logger.debug(f"MIDI {msg_name} sent")
            return True
        except Exception as e:
            logger.error(f"MIDI {msg_name} error: {e}")
            return False

    def send_clock(self) -> bool:
        """Send MIDI clock pulse"""
        return self._send_system_realtime(self.CLOCK, "clock")

    def send_start(self) -> bool:
        """Send MIDI start message"""
        return self._send_system_realtime(self.START, "Start", log_msg=True)

    def send_stop(self) -> bool:
        """Send MIDI stop message"""
        return self._send_system_realtime(self.STOP, "Stop", log_msg=True)

    def send_continue(self) -> bool:
        """Send MIDI continue message"""
        return self._send_system_realtime(self.CONTINUE, "Continue", log_msg=True)

    # ================================================================
    # Note Messages
    # ================================================================

    def send_note_on(self, channel: int, note: int, velocity: int = 100) -> bool:
        """
        Send MIDI note on

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
        """
        if not self._port:
            return False
        try:
            msg = Message("note_on", channel=channel & 0x0F, note=note & 0x7F, velocity=velocity & 0x7F)
            self._port.send(msg)
            self._active_notes[(channel, note)] = velocity
            return True
        except Exception as e:
            logger.error(f"MIDI note_on error: {e}")
            return False

    def send_note_off(self, channel: int, note: int) -> bool:
        """
        Send MIDI note off

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
        """
        if not self._port:
            return False
        try:
            msg = Message("note_off", channel=channel & 0x0F, note=note & 0x7F, velocity=0)
            self._port.send(msg)
            self._active_notes.pop((channel, note), None)
            return True
        except Exception as e:
            logger.error(f"MIDI note_off error: {e}")
            return False

    def send_cc(self, channel: int, cc: int, value: int) -> bool:
        """
        Send MIDI Control Change message.

        Args:
            channel: MIDI channel (0-15)
            cc: CC number (0-127)
            value: CC value (0-127)
        """
        if not self._port:
            return False
        try:
            msg = Message(
                "control_change",
                channel=channel & 0x0F,
                control=cc & 0x7F,
                value=value & 0x7F,
            )
            self._port.send(msg)
            return True
        except Exception as e:
            logger.error(f"MIDI CC error: {e}")
            return False

    def send_pitch_bend(self, channel: int, value: int) -> bool:
        """
        Send MIDI Pitch Bend message.

        Args:
            channel: MIDI channel (0-15)
            value: Pitch bend value (-8192 to 8191)
        """
        if not self._port:
            return False
        try:
            # Clamp value to valid range
            clamped_value = max(-8192, min(8191, value))
            msg = Message("pitchwheel", channel=channel & 0x0F, pitch=clamped_value)
            self._port.send(msg)
            return True
        except Exception as e:
            logger.error(f"MIDI pitch_bend error: {e}")
            return False

    def send_aftertouch(self, channel: int, value: int) -> bool:
        """
        Send MIDI Channel Aftertouch (Channel Pressure) message.

        Args:
            channel: MIDI channel (0-15)
            value: Aftertouch value (0-127)
        """
        if not self._port:
            return False
        try:
            msg = Message("aftertouch", channel=channel & 0x0F, value=value & 0x7F)
            self._port.send(msg)
            return True
        except Exception as e:
            logger.error(f"MIDI aftertouch error: {e}")
            return False

    def all_notes_off(self, channel: int | None = None) -> bool:
        """
        Turn off all active notes

        Args:
            channel: Specific channel, or None for all channels
        """
        if not self._port:
            return False

        try:
            notes_to_off = list(self._active_notes.keys())
            for (ch, note) in notes_to_off:
                if channel is None or ch == channel:
                    self.send_note_off(ch, note)
            return True
        except Exception as e:
            logger.error(f"MIDI all_notes_off error: {e}")
            return False

    # ================================================================
    # Utility
    # ================================================================

    @staticmethod
    def list_ports() -> list[str]:
        """List available MIDI output ports"""
        return list(mido.get_output_names())
