"""
PatternEvent model for scheduled musical events within patterns.

A PatternEvent represents a single musical event at a specific timing position.
PatternEvents are immutable once created.

Note: Previously named "Event" - renamed to PatternEvent in v3.1 to distinguish
from SessionEvent (CRUD operations) and SSE Event (HTTP streaming).
"""

from typing import Any
from pydantic import BaseModel, Field


class PatternEvent(BaseModel):
    """
    A single scheduled musical event within a pattern.

    PatternEvents are combined with Track.base_params to generate ScheduledMessages.
    They define precise timing (step, cycle) and sound parameters.

    Example:
        >>> event = PatternEvent(
        ...     step=0,
        ...     cycle=0.0,
        ...     params={"gain": 0.8, "pan": 0.5}
        ... )
    """

    step: int = Field(
        ...,
        ge=0,
        lt=256,
        description="Quantized step position (0-255 in 256-step grid)"
    )
    cycle: float = Field(
        ...,
        ge=0.0,
        description="Precise cycle position for timing"
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Event-specific parameters (merged with Track.base_params). "
            "For MIDI destinations, see midi_helpers module for validation."
        )
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "step": 0,
                    "cycle": 0.0,
                    "params": {"gain": 0.8}
                },
                {
                    "step": 64,
                    "cycle": 1.0,
                    "params": {"note": 48, "velocity": 100}
                }
            ]
        }
    }
