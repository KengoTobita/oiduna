"""
Output Protocols for oiduna_loop.

Extended interfaces for MIDI and OSC output, building on the framework
protocols defined in mars_common.protocols.

Relationship to mars_common protocols:
- OscOutput extends OscOutputProtocol with send_osc_event()
- MidiOutput extends MidiOutputProtocol with clock/transport methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oiduna_core.output.output import OscEvent

# Re-export framework protocols for convenience
from oiduna_core.protocols import MidiOutputProtocol, OscOutputProtocol

__all__ = [
    "MidiOutput",
    "OscOutput",
    "MidiOutputProtocol",
    "OscOutputProtocol",
]


@runtime_checkable
class MidiOutput(Protocol):
    """
    Extended MIDI output interface for oiduna_loop.

    Extends MidiOutputProtocol with:
    - Low-level note on/off methods
    - MIDI clock and transport messages
    - Port management

    Implementations:
        - MidiSender: Real MIDI output via mido
        - MockMidiOutput: Test double for unit tests
    """

    def connect(self) -> bool:
        """Connect to MIDI output device."""
        ...

    def disconnect(self) -> None:
        """Disconnect from MIDI output device."""
        ...

    def send_note_on(self, channel: int, note: int, velocity: int) -> bool:
        """Send MIDI note on message."""
        ...

    def send_note_off(self, channel: int, note: int) -> bool:
        """Send MIDI note off message."""
        ...

    def send_cc(self, channel: int, cc: int, value: int) -> bool:
        """Send MIDI Control Change message."""
        ...

    def send_pitch_bend(self, channel: int, value: int) -> bool:
        """Send MIDI Pitch Bend message."""
        ...

    def send_aftertouch(self, channel: int, value: int) -> bool:
        """Send MIDI Channel Aftertouch (Channel Pressure) message."""
        ...

    def send_clock(self) -> bool:
        """Send MIDI clock pulse (24 PPQ)."""
        ...

    def send_start(self) -> bool:
        """Send MIDI start message."""
        ...

    def send_stop(self) -> bool:
        """Send MIDI stop message."""
        ...

    def send_continue(self) -> bool:
        """Send MIDI continue message."""
        ...

    def all_notes_off(self, channel: int | None = None) -> bool:
        """Turn off all active notes."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to MIDI output."""
        ...

    @property
    def port_name(self) -> str | None:
        """Get current port name."""
        ...

    def set_port(self, port_name: str) -> bool:
        """Change MIDI output port."""
        ...


@runtime_checkable
class OscOutput(Protocol):
    """
    Extended OSC output interface for oiduna_loop.

    Implementations:
        - OscSender: Real OSC output via pythonosc
        - MockOscOutput: Test double for unit tests
    """

    def connect(self) -> None:
        """Initialize OSC connection."""
        ...

    def disconnect(self) -> None:
        """Close OSC connection."""
        ...

    def send_osc_event(self, event: OscEvent) -> bool:
        """
        Send a pre-computed OscEvent to SuperDirt.

        Args:
            event: Pre-computed OscEvent from StepProcessor.process_step_v2()

        Returns:
            True if sent successfully
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to OSC target."""
        ...
