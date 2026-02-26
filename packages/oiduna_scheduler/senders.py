"""
Destination senders - send messages via OSC or MIDI.
"""

from __future__ import annotations
from typing import List, Any
from pythonosc import udp_client
import mido


class OscDestinationSender:
    """
    Sends messages to an OSC destination.

    Design:
    - Thin wrapper around pythonosc.udp_client
    - Converts params dict to OSC args [key, value, key, value, ...]
    - Configurable address (not hardcoded /dirt/play)

    Usage:
        >>> sender = OscDestinationSender(
        ...     host="127.0.0.1",
        ...     port=57120,
        ...     address="/dirt/play"
        ... )
        >>> sender.send_message({"s": "bd", "gain": 0.8})
    """

    def __init__(
        self,
        host: str,
        port: int,
        address: str,
        use_bundle: bool = False,
    ) -> None:
        """
        Initialize OSC sender.

        Args:
            host: OSC server host (e.g., "127.0.0.1")
            port: OSC server port (e.g., 57120)
            address: OSC address pattern (e.g., "/dirt/play")
            use_bundle: Whether to bundle same-timing messages
        """
        self.host = host
        self.port = port
        self.address = address
        self.use_bundle = use_bundle
        self._client = udp_client.SimpleUDPClient(host, port)

    def send_message(self, params: dict[str, Any]) -> None:
        """
        Send a single OSC message.

        Args:
            params: Parameter dictionary (e.g., {"s": "bd", "gain": 0.8})

        The params are converted to OSC args format:
        [key, value, key, value, ...]
        """
        # Convert dict to flat list: [key, value, key, value, ...]
        args: List[Any] = []
        for key, value in params.items():
            args.extend([key, value])

        self._client.send_message(self.address, args)

    def send_bundle(self, messages: List[dict[str, Any]]) -> None:
        """
        Send multiple messages as OSC bundle.

        Args:
            messages: List of parameter dictionaries

        TODO: Implement OSC bundle support with timing
        """
        # For now, send individually
        for msg in messages:
            self.send_message(msg)

    def __repr__(self) -> str:
        return (
            f"OscDestinationSender(host={self.host!r}, port={self.port}, "
            f"address={self.address!r})"
        )


class MidiDestinationSender:
    """
    Sends messages to a MIDI destination.

    Design:
    - Wraps mido output port
    - Handles note on/off, CC, pitch bend
    - Uses default_channel if message doesn't specify

    Usage:
        >>> sender = MidiDestinationSender(
        ...     port_name="USB MIDI 1",
        ...     default_channel=0
        ... )
        >>> sender.send_message({
        ...     "note": 60,
        ...     "velocity": 100,
        ...     "duration_ms": 250
        ... })
    """

    def __init__(
        self,
        port_name: str,
        default_channel: int = 0,
    ) -> None:
        """
        Initialize MIDI sender.

        Args:
            port_name: MIDI port name (from mido.get_output_names())
            default_channel: Default MIDI channel 0-15
        """
        self.port_name = port_name
        self.default_channel = default_channel
        self._port = mido.open_output(port_name)

    def send_message(self, params: dict[str, Any]) -> None:
        """
        Send MIDI message.

        Args:
            params: Parameter dictionary

        Supported message types (determined by params):
        - Note: {"note": 60, "velocity": 100, "duration_ms": 250, "channel": 0}
        - CC: {"cc": 74, "value": 64, "channel": 0}
        - Pitch bend: {"pitch_bend": 4096, "channel": 0}

        Channel is optional - uses default_channel if not specified.
        """
        channel = params.get("channel", self.default_channel)

        # Note message
        if "note" in params:
            note = params["note"]
            velocity = params.get("velocity", 100)
            duration_ms = params.get("duration_ms", 100)

            # Send note on
            self._port.send(mido.Message(
                "note_on",
                note=note,
                velocity=velocity,
                channel=channel
            ))

            # TODO: Schedule note off after duration_ms
            # For now, rely on external note-off scheduling
            # This requires integration with the loop engine's timing

        # CC message
        elif "cc" in params:
            cc = params["cc"]
            value = params.get("value", 0)
            self._port.send(mido.Message(
                "control_change",
                control=cc,
                value=value,
                channel=channel
            ))

        # Pitch bend message
        elif "pitch_bend" in params:
            pitch_bend = params["pitch_bend"]
            self._port.send(mido.Message(
                "pitchwheel",
                pitch=pitch_bend,
                channel=channel
            ))

    def send_bundle(self, messages: List[dict[str, Any]]) -> None:
        """
        Send multiple MIDI messages.

        Args:
            messages: List of parameter dictionaries

        MIDI doesn't have bundles - just sends sequentially.
        """
        for msg in messages:
            self.send_message(msg)

    def close(self) -> None:
        """Close MIDI port."""
        self._port.close()

    def __repr__(self) -> str:
        return (
            f"MidiDestinationSender(port_name={self.port_name!r}, "
            f"default_channel={self.default_channel})"
        )

    def __del__(self) -> None:
        """Ensure MIDI port is closed on cleanup."""
        if hasattr(self, "_port"):
            self._port.close()
