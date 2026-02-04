"""CompiledSession and ApplyCommand models for MARS DSL v5.

Represents the complete compiled output from the DSL parser.

v5 Changes:
- Added mixer_lines for routing and shared spatial effects
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .environment import Environment
from .mixer_line import MixerLine
from .scene import Scene
from .sequence import EventSequence
from .track import Track
from .track_midi import TrackMidi

# Apply timing type
ApplyTiming = Literal["now", "beat", "bar", "seq"]


@dataclass
class ApplyCommand:
    """Apply statement from DSL.

    Specifies when and what to apply to the runtime.
    """

    timing: ApplyTiming
    track_ids: list[str] = field(default_factory=list)
    scene_name: str | None = None  # For `apply scene "name"`

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timing": self.timing,
            "track_ids": self.track_ids,
            "scene_name": self.scene_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApplyCommand:
        """Create from dictionary (deserialization)."""
        return cls(
            timing=data["timing"],
            track_ids=data.get("track_ids", []),
            scene_name=data.get("scene_name"),
        )


@dataclass
class CompiledSession:
    """Compiled DSL session.

    The complete output from compiling a DSL source file.
    Contains all three layers of the data model plus mixer lines,
    scenes, and apply command.

    v5 Changes:
    - Added mixer_lines for routing and shared spatial effects
    """

    environment: Environment = field(default_factory=Environment)
    tracks: dict[str, Track] = field(default_factory=dict)
    tracks_midi: dict[str, TrackMidi] = field(default_factory=dict)
    mixer_lines: dict[str, MixerLine] = field(default_factory=dict)
    sequences: dict[str, EventSequence] = field(default_factory=dict)
    scenes: dict[str, Scene] = field(default_factory=dict)
    apply: ApplyCommand | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "environment": self.environment.to_dict(),
            "tracks": {k: v.to_dict() for k, v in self.tracks.items()},
            "tracks_midi": {k: v.to_dict() for k, v in self.tracks_midi.items()},
            "mixer_lines": {k: v.to_dict() for k, v in self.mixer_lines.items()},
            "sequences": {k: v.to_dict() for k, v in self.sequences.items()},
            "scenes": {k: v.to_dict() for k, v in self.scenes.items()},
            "apply": self.apply.to_dict() if self.apply else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompiledSession:
        """Create from dictionary (deserialization)."""
        apply_data = data.get("apply")
        return cls(
            environment=Environment.from_dict(data.get("environment", {})),
            tracks={k: Track.from_dict(v) for k, v in data.get("tracks", {}).items()},
            tracks_midi={
                k: TrackMidi.from_dict(v)
                for k, v in data.get("tracks_midi", {}).items()
            },
            mixer_lines={
                k: MixerLine.from_dict(v)
                for k, v in data.get("mixer_lines", {}).items()
            },
            sequences={
                k: EventSequence.from_dict(v)
                for k, v in data.get("sequences", {}).items()
            },
            scenes={k: Scene.from_dict(v) for k, v in data.get("scenes", {}).items()},
            apply=ApplyCommand.from_dict(apply_data) if apply_data else None,
        )
