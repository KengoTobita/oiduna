"""EventSequence and Event models for MARS DSL v5.

Represents Layer 3 of the 3-layer data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class Event:
    """Sequence event (a single trigger in the pattern).

    Represents one note/hit in a sequence at a specific step.
    """

    step: int  # 0-255
    velocity: float = 1.0  # 0.0-1.0
    note: int | None = None  # MIDI note number (for melodic patterns)
    gate: float = 1.0  # Gate length ratio

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "step": self.step,
            "velocity": self.velocity,
            "gate": self.gate,
        }
        if self.note is not None:
            result["note"] = self.note
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Create from dictionary (deserialization)."""
        return cls(
            step=data["step"],
            velocity=data.get("velocity", 1.0),
            note=data.get("note"),
            gate=data.get("gate", 1.0),
        )


@dataclass
class EventSequence:
    """Event sequence (indexed for O(1) lookup).

    Represents Layer 3 of the 3-layer data model.
    Contains pattern events with an index for fast step-based lookup.
    """

    track_id: str
    _events: tuple[Event, ...] = field(default_factory=tuple)
    _step_index: dict[int, list[int]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self._step_index and self._events:
            self._build_index()

    def _build_index(self) -> None:
        """Build step index for O(1) lookup."""
        self._step_index = {}
        for i, event in enumerate(self._events):
            self._step_index.setdefault(event.step, []).append(i)

    @classmethod
    def from_events(cls, track_id: str, events: list[Event]) -> EventSequence:
        """Create EventSequence from a list of events."""
        seq = cls(track_id=track_id, _events=tuple(events))
        seq._build_index()
        return seq

    def get_events_at(self, step: int) -> list[Event]:
        """Get events at a specific step (O(1))."""
        indices = self._step_index.get(step, [])
        return [self._events[i] for i in indices]

    def has_events_at(self, step: int) -> bool:
        """Check if there are events at a specific step."""
        return step in self._step_index

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    @property
    def steps_with_events(self) -> list[int]:
        """Get list of steps that have events (sorted)."""
        return sorted(self._step_index.keys())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "track_id": self.track_id,
            "events": [e.to_dict() for e in self._events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventSequence:
        """Create from dictionary (deserialization)."""
        events = [Event.from_dict(e) for e in data.get("events", [])]
        return cls.from_events(track_id=data["track_id"], events=events)
