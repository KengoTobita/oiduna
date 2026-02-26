"""
Scheduled message models.

These use dataclasses (not Pydantic) for maximum runtime performance.
Validation happens in MARS - Oiduna trusts the input.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    """
    Lightweight scheduled message for routing to destinations.

    Design principles:
    - frozen=True for immutability (thread-safe, cacheable)
    - slots=True for minimal memory footprint
    - No validation - MARS is responsible for correctness
    - Generic params dict - no domain knowledge

    Example (SuperDirt message from MARS):
        >>> msg = ScheduledMessage(
        ...     destination_id="superdirt",
        ...     cycle=3.5,
        ...     step=56,
        ...     params={
        ...         "s": "bd",
        ...         "orbit": 0,
        ...         "gain": 0.8,
        ...         "pan": 0.5,
        ...         "delaySend": 0.2,  # MARS converted delay_send → delaySend
        ...         "room": 0.3,
        ...     }
        ... )

    Example (MIDI message from MARS):
        >>> msg = ScheduledMessage(
        ...     destination_id="volca_bass",
        ...     cycle=1.0,
        ...     step=0,
        ...     params={
        ...         "channel": 0,
        ...         "note": 36,  # MIDI note C2
        ...         "velocity": 100,
        ...         "duration_ms": 250,
        ...     }
        ... )
    """

    destination_id: str  # "superdirt", "volca_bass", etc.
    cycle: float  # Timing: cycle position (e.g., 3.5)
    step: int  # Timing: quantized step (0-255)
    params: dict[str, Any]  # Generic parameters - no type checking

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return {
            "destination_id": self.destination_id,
            "cycle": self.cycle,
            "step": self.step,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledMessage:
        """Create from dictionary (for JSON deserialization)."""
        return cls(
            destination_id=data["destination_id"],
            cycle=data["cycle"],
            step=data["step"],
            params=data["params"],
        )


@dataclass(frozen=True)
class ScheduledMessageBatch:
    """
    Batch of scheduled messages for a session.

    Sent from MARS to Oiduna via HTTP API.

    Example:
        >>> batch = ScheduledMessageBatch(
        ...     messages=[msg1, msg2, msg3],
        ...     bpm=120.0,
        ...     pattern_length=4.0
        ... )
        >>> batch_dict = batch.to_dict()  # For JSON
    """

    messages: tuple[ScheduledMessage, ...]  # All messages for session
    bpm: float = 120.0  # Tempo
    pattern_length: float = 4.0  # Pattern length in cycles

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "bpm": self.bpm,
            "pattern_length": self.pattern_length,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledMessageBatch:
        """Create from dictionary (for JSON deserialization)."""
        messages = [ScheduledMessage.from_dict(msg) for msg in data["messages"]]
        return cls(
            messages=tuple(messages),
            bpm=data.get("bpm", 120.0),
            pattern_length=data.get("pattern_length", 4.0),
        )
