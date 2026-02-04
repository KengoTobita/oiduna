"""Scene model for MARS DSL v5.

Represents a named snapshot of tracks, sequences, and environment settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .environment import Environment
from .sequence import EventSequence
from .track import Track
from .track_midi import TrackMidi


@dataclass
class Scene:
    """Scene definition.

    A scene is a named collection of tracks, sequences, and optionally
    environment settings. Scenes can be switched during performance
    using the `apply scene "name"` syntax.
    """

    name: str
    environment: Environment | None = None
    tracks: dict[str, Track] = field(default_factory=dict)
    tracks_midi: dict[str, TrackMidi] = field(default_factory=dict)
    sequences: dict[str, EventSequence] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "environment": self.environment.to_dict() if self.environment else None,
            "tracks": {k: v.to_dict() for k, v in self.tracks.items()},
            "tracks_midi": {k: v.to_dict() for k, v in self.tracks_midi.items()},
            "sequences": {k: v.to_dict() for k, v in self.sequences.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        """Create from dictionary (deserialization)."""
        env_data = data.get("environment")
        return cls(
            name=data["name"],
            environment=Environment.from_dict(env_data) if env_data else None,
            tracks={k: Track.from_dict(v) for k, v in data.get("tracks", {}).items()},
            tracks_midi={
                k: TrackMidi.from_dict(v)
                for k, v in data.get("tracks_midi", {}).items()
            },
            sequences={
                k: EventSequence.from_dict(v)
                for k, v in data.get("sequences", {}).items()
            },
        )
