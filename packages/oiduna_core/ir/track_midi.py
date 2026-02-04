"""TrackMidi model for MARS DSL v5.

Represents Layer 2 of the 3-layer data model for MIDI tracks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oiduna_core.modulation.modulation import Modulation


@dataclass
class TrackMidi:
    """MIDI track definition.

    Represents Layer 2 of the 3-layer data model for MIDI output.
    Contains channel settings, CC modulations, and special MIDI message modulations.
    """

    track_id: str
    channel: int  # 0-15
    velocity: int = 127  # Default max velocity (0-127)
    transpose: int = 0  # Semitone transpose
    mute: bool = False
    solo: bool = False
    cc_modulations: dict[int, Modulation] = field(default_factory=dict)
    # key: CC number (0-127), value: Modulation

    # Special MIDI channel message modulations
    pitch_bend_modulation: Modulation | None = None
    aftertouch_modulation: Modulation | None = None
    velocity_modulation: Modulation | None = None

    @property
    def id(self) -> str:
        """Get track ID."""
        return self.track_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "track_id": self.track_id,
            "channel": self.channel,
            "velocity": self.velocity,
            "transpose": self.transpose,
            "mute": self.mute,
            "solo": self.solo,
            "cc_modulations": {
                str(k): v.to_dict() for k, v in self.cc_modulations.items()
            },
        }
        if self.pitch_bend_modulation:
            result["pitch_bend_modulation"] = self.pitch_bend_modulation.to_dict()
        if self.aftertouch_modulation:
            result["aftertouch_modulation"] = self.aftertouch_modulation.to_dict()
        if self.velocity_modulation:
            result["velocity_modulation"] = self.velocity_modulation.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackMidi:
        """Create from dictionary (deserialization)."""
        pitch_bend = None
        if "pitch_bend_modulation" in data:
            pitch_bend = Modulation.from_dict(data["pitch_bend_modulation"])
        aftertouch = None
        if "aftertouch_modulation" in data:
            aftertouch = Modulation.from_dict(data["aftertouch_modulation"])
        velocity_mod = None
        if "velocity_modulation" in data:
            velocity_mod = Modulation.from_dict(data["velocity_modulation"])

        return cls(
            track_id=data["track_id"],
            channel=data["channel"],
            velocity=data.get("velocity", 127),
            transpose=data.get("transpose", 0),
            mute=data.get("mute", False),
            solo=data.get("solo", False),
            cc_modulations={
                int(k): Modulation.from_dict(v)
                for k, v in data.get("cc_modulations", {}).items()
            },
            pitch_bend_modulation=pitch_bend,
            aftertouch_modulation=aftertouch,
            velocity_modulation=velocity_mod,
        )
