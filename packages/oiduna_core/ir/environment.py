"""Environment and Chord models for Oiduna Framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oiduna_core.constants.steps import LOOP_STEPS


@dataclass
class Chord:
    """Chord definition for chord progression."""

    name: str
    length: int | None = None  # None = equal division


@dataclass
class Environment:
    """Performance environment settings.

    Represents Layer 1 of the 3-layer data model:
    - Layer 1: Environment (global settings)
    - Layer 2: Track (per-track settings)
    - Layer 3: EventSequence (pattern data)
    """

    bpm: float = 120.0
    scale: str = "C_major"
    default_gate: float = 1.0
    swing: float = 0.0
    loop_steps: int = LOOP_STEPS  # Fixed at 256
    chords: list[Chord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bpm": self.bpm,
            "scale": self.scale,
            "default_gate": self.default_gate,
            "swing": self.swing,
            "loop_steps": self.loop_steps,
            "chords": [{"name": c.name, "length": c.length} for c in self.chords],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Environment:
        """Create from dictionary (deserialization)."""
        chords = [
            Chord(name=c["name"], length=c.get("length"))
            for c in data.get("chords", [])
        ]
        return cls(
            bpm=data.get("bpm", 120.0),
            scale=data.get("scale", "C_major"),
            default_gate=data.get("default_gate", 1.0),
            swing=data.get("swing", 0.0),
            loop_steps=data.get("loop_steps", LOOP_STEPS),
            chords=chords,
        )
