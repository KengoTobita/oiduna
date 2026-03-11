"""
Destination parameter type definitions.

Provides TypedDict definitions for destination-specific parameters
to improve type safety and editor autocomplete while maintaining
flexibility for custom destinations.

Note: These are TypedDict (not Pydantic models) to maintain dict
compatibility and zero runtime overhead. All fields are optional
(total=False) to allow flexible parameter combinations.
"""

from typing import TypedDict, Any

__all__ = [
    "SuperDirtParams",
    "SimpleMidiParams",
    "DestinationParams",
]


class SuperDirtParams(TypedDict, total=False):
    """SuperDirt-specific parameters.

    All fields are optional (total=False). Combine as needed for your sound.

    Common parameters:
        s: Sound name (e.g., "bd", "sn", "hh")
        n: Sample number within the sound (default: 0)
        gain: Volume level (0.0-2.0, recommended: 0.0-1.0)
        pan: Stereo position (0.0=left, 0.5=center, 1.0=right)
        speed: Playback speed (1.0=normal, 2.0=double, -1.0=reverse)

    Effects:
        room: Reverb send amount (0.0-1.0)
        size: Reverb room size (0.0-1.0)
        delay_send: Delay send amount (0.0-1.0)
        delay_time: Delay time in cycles (e.g., 0.25=quarter cycle)
        cutoff: Low-pass filter cutoff frequency in Hz (e.g., 1000)
        resonance: Filter resonance (0.0-1.0)

    Routing:
        orbit: Output orbit/bus number (0-11)

    Reference:
        https://tidalcycles.org/docs/patternlib/tutorials/superdirt_params/
    """

    # Sound selection
    s: str  # Sound name
    n: int  # Sample number

    # Basic parameters
    gain: float  # Volume (0.0-2.0)
    pan: float  # Pan (0.0-1.0)
    speed: float  # Playback speed
    unit: str  # Unit for frequency parameters ("rate" or "cycles")

    # Effects - Reverb
    room: float  # Reverb send (0.0-1.0)
    size: float  # Reverb size (0.0-1.0)
    dry: float  # Dry signal level (0.0-1.0)

    # Effects - Delay
    delay: float  # Delay mix (0.0-1.0)
    delay_send: float  # Delay send (0.0-1.0)
    delay_time: float  # Delay time in cycles
    delayfeedback: float  # Delay feedback (0.0-1.0)

    # Effects - Filter
    cutoff: float  # Low-pass cutoff in Hz
    resonance: float  # Filter resonance (0.0-1.0)
    hcutoff: float  # High-pass cutoff in Hz
    hresonance: float  # High-pass resonance (0.0-1.0)
    bandf: float  # Band-pass frequency in Hz
    bandq: float  # Band-pass Q factor

    # Effects - Distortion
    shape: float  # Waveshaping distortion (0.0-1.0)
    crush: float  # Bit crushing (1-16)

    # Routing
    orbit: int  # Output orbit (0-11)

    # Envelope
    attack: float  # Attack time in seconds
    hold: float  # Hold time in seconds
    release: float  # Release time in seconds

    # Pitch
    note: int | float  # MIDI note number or frequency
    octave: int  # Octave shift
    semitone: int  # Semitone shift

    # Advanced
    begin: float  # Sample start position (0.0-1.0)
    end: float  # Sample end position (0.0-1.0)
    loop: int  # Loop count
    cps: float  # Cycles per second (tempo)


class SimpleMidiParams(TypedDict, total=False):
    """Simplified MIDI parameters (flat structure).

    All fields are optional (total=False). Use appropriate combinations
    for Note On, Control Change, or Pitch Bend messages.

    Note: For MIDI protocol validation, use MidiParams from midi_helpers.
    This SimpleMidiParams provides a flat, easy-to-use structure for
    common MIDI parameters.

    Note On parameters:
        note: MIDI note number (0-127, 60=C4)
        velocity: Note velocity/volume (0-127)
        duration_ms: Note duration in milliseconds (default: until next note)
        channel: MIDI channel (0-15)

    Control Change parameters:
        cc: Control Change number (0-127)
        value: CC value (0-127)
        channel: MIDI channel (0-15)

    Pitch Bend parameters:
        pitch_bend: Pitch bend value (-8192 to 8191, 0=center)
        channel: MIDI channel (0-15)

    Reference:
        https://www.midi.org/specifications
    """

    # Note On/Off
    note: int  # MIDI note number (0-127)
    velocity: int  # Velocity (0-127)
    duration_ms: int  # Note duration in milliseconds

    # Control Change
    cc: int  # CC number (0-127)
    value: int  # CC value (0-127)

    # Pitch Bend
    pitch_bend: int  # Pitch bend (-8192 to 8191)

    # Program Change
    program: int  # Program number (0-127)

    # Channel
    channel: int  # MIDI channel (0-15)

    # Aftertouch
    aftertouch: int  # Channel aftertouch (0-127)
    poly_aftertouch: int  # Polyphonic aftertouch (0-127)


# Union type for all destination params
DestinationParams = SuperDirtParams | SimpleMidiParams | dict[str, Any]
"""Union type for all destination parameters.

Includes:
- SuperDirtParams: SuperDirt/TidalCycles parameters
- SimpleMidiParams: Simplified MIDI protocol parameters (flat structure)
- dict[str, Any]: Custom destination parameters

This type is primarily for documentation and editor autocomplete.
Runtime validation should be performed by DestinationSender implementations.

Note: For MIDI protocol validation with cc/nrpn dicts, use MidiParams
from midi_helpers module.
"""
