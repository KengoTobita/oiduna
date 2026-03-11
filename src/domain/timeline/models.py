"""
Scheduled change models for timeline scheduling.

Design principles:
- Immutable (frozen=True) for thread safety
- UUID-based identification for CRUD operations
- Includes metadata for collaboration and debugging
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid
import time

from oiduna.domain.schedule.models import LoopSchedule


@dataclass(frozen=True)
class CuedChange:
    """
    A single scheduled change in the timeline.

    Represents a pattern change scheduled to occur at a specific global step.
    Multiple changes can be scheduled for the same step and will be merged.

    Example:
        >>> from oiduna.domain.schedule.models import ScheduleEntry, LoopSchedule
        >>> msg = ScheduleEntry("superdirt", 0.0, 0, {"s": "bd"})
        >>> batch = LoopSchedule(messages=(msg,), bpm=140.0)
        >>> change = CuedChange(
        ...     target_global_step=1000,
        ...     batch=batch,
        ...     client_id="alice_001",
        ...     client_name="Alice",
        ...     description="Kick pattern"
        ... )
        >>> change.change_id  # Auto-generated UUID
        '123e4567-e89b-12d3-a456-426614174000'
    """

    target_global_step: int  # When to apply this change (cumulative step count)
    batch: LoopSchedule  # Messages to apply
    client_id: str  # Who scheduled this change
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique identifier
    client_name: str = ""  # Human-readable client name (for UI)
    description: str = ""  # User-provided description (for collaboration)
    cued_at: float = field(default_factory=time.time)  # Unix timestamp of scheduling
    sequence_number: int = 0  # Order within the same step (for merge order visualization)

    def __post_init__(self) -> None:
        """Validate the scheduled change."""
        if self.target_global_step < 0:
            raise ValueError(f"target_global_step must be non-negative, got {self.target_global_step}")
        if not self.client_id:
            raise ValueError("client_id cannot be empty")
        if len(self.description) > 200:
            raise ValueError(f"description too long: {len(self.description)} > 200 chars")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for API responses and SSE events.
        """
        return {
            "change_id": self.change_id,
            "target_global_step": self.target_global_step,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "description": self.description,
            "cued_at": self.cued_at,
            "sequence_number": self.sequence_number,
            "batch": self.batch.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CuedChange:
        """
        Create from dictionary (for deserialization).

        Args:
            data: Dictionary containing all required fields.

        Returns:
            CuedChange instance.
        """
        return cls(
            change_id=data["change_id"],
            target_global_step=data["target_global_step"],
            batch=LoopSchedule.from_dict(data["batch"]),
            client_id=data["client_id"],
            client_name=data.get("client_name", ""),
            description=data.get("description", ""),
            cued_at=data.get("cued_at", time.time()),
            sequence_number=data.get("sequence_number", 0),
        )
