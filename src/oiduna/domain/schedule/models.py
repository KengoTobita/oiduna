"""
Loop schedule models.

These use dataclasses (not Pydantic) for maximum runtime performance.
Validation happens in MARS - Oiduna trusts the input.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """
    Single entry in the loop schedule.

    Represents one timed event (step + destination + params) in the 256-step loop.

    Design principles:
    - frozen=True for immutability (thread-safe, cacheable)
    - slots=True for minimal memory footprint
    - No validation - MARS is responsible for correctness
    - Generic params dict - no domain knowledge

    Example (SuperDirt entry from MARS):
        >>> entry = ScheduleEntry(
        ...     destination_id="superdirt",
        ...     step=56,
        ...     offset=0.5,
        ...     params={
        ...         "s": "bd",
        ...         "orbit": 0,
        ...         "gain": 0.8,
        ...         "pan": 0.5,
        ...         "delaySend": 0.2,  # MARS converted delay_send → delaySend
        ...         "room": 0.3,
        ...     }
        ... )

    Example (MIDI entry from MARS):
        >>> entry = ScheduleEntry(
        ...     destination_id="volca_bass",
        ...     step=0,
        ...     offset=0.0,
        ...     params={
        ...         "channel": 0,
        ...         "note": 36,  # MIDI note C2
        ...         "velocity": 100,
        ...         "duration_ms": 250,
        ...     }
        ... )
    """

    destination_id: str  # "superdirt", "volca_bass", etc.
    step: int  # Timing: quantized step (0-255)
    offset: float  # Timing: relative offset within step [0.0, 1.0)
    params: dict[str, Any]  # Generic parameters - no type checking

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return {
            "destination_id": self.destination_id,
            "step": self.step,
            "offset": self.offset,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduleEntry:
        """Create from dictionary (for JSON deserialization)."""
        return cls(
            destination_id=data["destination_id"],
            step=data["step"],
            offset=data.get("offset", 0.0),  # Default to 0.0 for backward compatibility
            params=data["params"],
        )


@dataclass(frozen=True)
class LoopSchedule:
    """
    256-step loop execution schedule (immutable timetable).

    Represents the complete execution plan for one loop iteration.
    Like a train timetable - once compiled, it's fixed and just executed step-by-step.

    Sent from MARS to Oiduna via HTTP API.

    Example:
        >>> schedule = LoopSchedule(
        ...     entries=[entry1, entry2, entry3],
        ...     bpm=120.0,
        ...     pattern_length=4.0
        ... )
        >>> schedule_dict = schedule.to_dict()  # For JSON
    """

    entries: tuple[ScheduleEntry, ...]  # All entries in the loop schedule
    bpm: float = 120.0  # Tempo
    pattern_length: float = 4.0  # Pattern length in cycles
    # destinations removed as field - now a cached property

    @property
    def destinations(self) -> frozenset[str]:
        """
        Auto-infer destination IDs from entries (cached).

        This optimization eliminates redundant storage - destinations
        are always derivable from the entries themselves.

        Returns:
            Frozenset of destination IDs referenced in schedule entries.
        """
        # Cache the result to avoid recomputation
        if not hasattr(self, '_cached_destinations'):
            # Use object.__setattr__ to bypass frozen dataclass restriction
            object.__setattr__(
                self,
                '_cached_destinations',
                frozenset(entry.destination_id for entry in self.entries)
            )
        return self._cached_destinations

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "bpm": self.bpm,
            "pattern_length": self.pattern_length,
            "destinations": list(self.destinations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopSchedule:
        """Create from dictionary (for JSON deserialization)."""
        # Support both old "messages" key and new "entries" key for compatibility
        entries_data = data.get("entries") or data.get("messages", [])
        entries = [ScheduleEntry.from_dict(entry) for entry in entries_data]

        # destinations is now a property, so we don't pass it to constructor
        return cls(
            entries=tuple(entries),
            bpm=data.get("bpm", 120.0),
            pattern_length=data.get("pattern_length", 4.0),
        )
