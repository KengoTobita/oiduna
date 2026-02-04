"""
Output Protocols for Three-Layer IR Architecture.

These protocols define the framework's public interfaces for audio/MIDI output.
Implementations can be provided by different backends (SuperDirt, MIDI hardware, etc.).

Design:
- OscOutputProtocol: For SuperDirt/OSC-based audio output
- MidiOutputProtocol: For MIDI hardware/software output

Usage:
    class MyOscBackend:
        def send_osc_event(self, event: OscEvent) -> bool:
            # Send to SuperDirt
            ...

    # Type checking ensures compatibility
    backend: OscOutputProtocol = MyOscBackend()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oiduna_core.models.output.output import MidiCCEvent, MidiNoteEvent, OscEvent


@runtime_checkable
class OscOutputProtocol(Protocol):
    """
    Protocol for OSC output destinations.

    This is the framework's standard interface for sending audio events
    to SuperDirt or compatible backends.

    Implementations:
        - OscSender (oiduna_loop): Real SuperDirt output via pythonosc
        - MockOscOutput: Test double for unit tests

    Example:
        >>> class MyBackend:
        ...     def send_osc_event(self, event: OscEvent) -> bool:
        ...         return self._client.send(event.to_osc_args())
        ...     def connect(self) -> None: ...
        ...     def disconnect(self) -> None: ...
        ...     @property
        ...     def is_connected(self) -> bool: ...
    """

    def send_osc_event(self, event: OscEvent) -> bool:
        """
        Send a pre-computed OscEvent.

        The event contains all pre-computed values (gain with velocity
        and modulation applied, sustain in seconds, etc.).

        Args:
            event: OscEvent from StepProcessor.process_step_v2()

        Returns:
            True if sent successfully, False otherwise
        """
        ...

    def connect(self) -> None:
        """Establish connection to the OSC target."""
        ...

    def disconnect(self) -> None:
        """Close connection to the OSC target."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether currently connected to OSC target."""
        ...


@runtime_checkable
class MidiOutputProtocol(Protocol):
    """
    Protocol for MIDI output destinations.

    This is the framework's standard interface for sending MIDI events
    to hardware or software synthesizers.

    Implementations:
        - MidiSender (oiduna_loop): Real MIDI output via mido
        - MockMidiOutput: Test double for unit tests

    Example:
        >>> class MyMidiBackend:
        ...     def send_note(self, event: MidiNoteEvent) -> bool:
        ...         self._port.send(note_on(event.channel, event.note, event.velocity))
        ...         # Schedule note-off after event.duration_ms
        ...         return True
    """

    def send_note(self, event: MidiNoteEvent) -> bool:
        """
        Send a MIDI note event.

        The event contains pre-computed values (transposed note,
        scaled velocity, duration in milliseconds).

        Args:
            event: MidiNoteEvent from StepProcessor.process_step_v2()

        Returns:
            True if sent successfully
        """
        ...

    def send_cc(self, event: MidiCCEvent) -> bool:
        """
        Send a MIDI Control Change event.

        Args:
            event: MidiCCEvent from StepProcessor.process_step_v2()

        Returns:
            True if sent successfully
        """
        ...

    def connect(self) -> bool:
        """
        Connect to MIDI output device.

        Returns:
            True if connected successfully
        """
        ...

    def disconnect(self) -> None:
        """Disconnect from MIDI output device."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether currently connected to MIDI output."""
        ...
