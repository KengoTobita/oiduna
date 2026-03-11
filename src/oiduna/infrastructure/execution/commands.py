"""
Pydantic models for command validation.

Each command has a corresponding model that validates the payload structure.
This ensures type safety and provides clear error messages for invalid commands.
"""

from typing import Any

from pydantic import BaseModel, Field


class PlayCommand(BaseModel):
    """Play command payload (empty)."""

    pass


class StopCommand(BaseModel):
    """Stop command payload (empty)."""

    pass


class PauseCommand(BaseModel):
    """Pause command payload (empty)."""

    pass


class MuteCommand(BaseModel):
    """
    Mute/unmute track command payload.

    Fields:
        track_id: Track identifier
        mute: True to mute, False to unmute (default: True)
    """

    track_id: str
    mute: bool = True


class SoloCommand(BaseModel):
    """
    Solo/unsolo track command payload.

    Fields:
        track_id: Track identifier
        solo: True to solo, False to unsolo (default: True)
    """

    track_id: str
    solo: bool = True


class BpmCommand(BaseModel):
    """
    BPM change command payload.

    Fields:
        bpm: Beats per minute (must be positive)
    """

    bpm: float = Field(gt=0)


class MidiPortCommand(BaseModel):
    """
    MIDI port selection command payload.

    Fields:
        port_name: MIDI port name to connect to
    """

    port_name: str


class MidiPanicCommand(BaseModel):
    """MIDI panic command payload (empty)."""

    pass


class PanicCommand(BaseModel):
    """Full panic command payload (empty)."""

    pass
