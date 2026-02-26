"""MixerLine models for MARS DSL v5.

Represents a mixer bus/group that contains multiple tracks
and applies shared effects (reverb, delay, leslie) and dynamics
(limiter, compression).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MixerLineDynamics:
    """Dynamics processing for a MixerLine.

    Controls limiter and compression applied to all tracks
    in the MixerLine.
    """

    limiter: bool = True
    limiter_type: int = 1  # 0=off, 1=tanh, 2=compress
    compression_ratio: float = 1.0  # 1 = no compression
    compression_threshold: float = 1.0  # 1 = no compression

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "limiter": self.limiter,
            "limiter_type": self.limiter_type,
            "compression_ratio": self.compression_ratio,
            "compression_threshold": self.compression_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MixerLineDynamics:
        """Create from dictionary (deserialization)."""
        return cls(
            limiter=data.get("limiter", True),
            limiter_type=data.get("limiter_type", 1),
            compression_ratio=data.get("compression_ratio", 1.0),
            compression_threshold=data.get("compression_threshold", 1.0),
        )


@dataclass(frozen=True)
class MixerLineFx:
    """Spatial effects for a MixerLine.

    These effects are shared across all tracks in the MixerLine,
    providing consistent spatial characteristics.

    Note: This is separate from TrackFx which handles tone-shaping
    effects (filter, distortion, envelope, tremolo, phaser).
    """

    # Reverb
    reverb_room: float = 0.0  # Send amount
    reverb_size: float = 0.5  # Room size
    reverb_dry: float = 1.0  # Dry signal level

    # Delay
    delay_send: float = 0.0  # Send amount
    delay_time: float = 0.375  # Delay time in seconds
    delay_feedback: float = 0.4  # Feedback amount

    # Leslie
    leslie_rate: float = 0.0  # Rotation speed (0 = off)
    leslie_size: float = 0.0  # Effect depth

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "reverb_room": self.reverb_room,
            "reverb_size": self.reverb_size,
            "reverb_dry": self.reverb_dry,
            "delay_send": self.delay_send,
            "delay_time": self.delay_time,
            "delay_feedback": self.delay_feedback,
            "leslie_rate": self.leslie_rate,
            "leslie_size": self.leslie_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MixerLineFx:
        """Create from dictionary (deserialization)."""
        return cls(
            reverb_room=data.get("reverb_room", 0.0),
            reverb_size=data.get("reverb_size", 0.5),
            reverb_dry=data.get("reverb_dry", 1.0),
            delay_send=data.get("delay_send", 0.0),
            delay_time=data.get("delay_time", 0.375),
            delay_feedback=data.get("delay_feedback", 0.4),
            leslie_rate=data.get("leslie_rate", 0.0),
            leslie_size=data.get("leslie_size", 0.0),
        )


@dataclass(frozen=True)
class MixerLine:
    """MixerLine (bus/group) definition.

    A MixerLine groups multiple tracks together and applies
    shared spatial effects and dynamics processing.

    Signal Flow:
        Track Sound → Track Fx → MixerLine Dynamics → MixerLine Fx → Output

    Attributes:
        name: Unique identifier for this MixerLine
        include: Tuple of track names that belong to this MixerLine
        volume: Master volume (0.0 - 2.0)
        pan: Pan position (0.0 = L, 0.5 = C, 1.0 = R)
        mute: Mute state
        solo: Solo state
        output: Physical output channel (0-7)
        dynamics: Limiter/compression settings
        fx: Spatial effects (reverb, delay, leslie)
    """

    name: str
    include: tuple[str, ...] = field(default_factory=tuple)
    volume: float = 1.0
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    output: int = 0
    dynamics: MixerLineDynamics = field(default_factory=MixerLineDynamics)
    fx: MixerLineFx = field(default_factory=MixerLineFx)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "include": list(self.include),
            "volume": self.volume,
            "pan": self.pan,
            "mute": self.mute,
            "solo": self.solo,
            "output": self.output,
            "dynamics": self.dynamics.to_dict(),
            "fx": self.fx.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MixerLine:
        """Create from dictionary (deserialization)."""
        return cls(
            name=data["name"],
            include=tuple(data.get("include", [])),
            volume=data.get("volume", 1.0),
            pan=data.get("pan", 0.5),
            mute=data.get("mute", False),
            solo=data.get("solo", False),
            output=data.get("output", 0),
            dynamics=MixerLineDynamics.from_dict(data.get("dynamics", {})),
            fx=MixerLineFx.from_dict(data.get("fx", {})),
        )
