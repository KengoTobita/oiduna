"""
Pattern model representing a sequence of events.

Patterns are owned by Tracks and can be activated/deactivated.
Multiple patterns can be active simultaneously on a single track.
"""

from typing import Annotated
from pydantic import BaseModel, Field
from .events import Event


class Pattern(BaseModel):
    """
    A pattern containing a sequence of events.

    Patterns belong to a Track and can be toggled active/inactive.
    Only active patterns contribute to the compiled message batch.

    Immutable fields (set at creation):
        - pattern_id
        - pattern_name
        - client_id

    Mutable fields (via PATCH):
        - active
        - events

    Example:
        >>> pattern = Pattern(
        ...     pattern_id="pattern_001",
        ...     pattern_name="main_beat",
        ...     client_id="client_001",
        ...     active=True,
        ...     events=[
        ...         Event(step=0, cycle=0.0, params={}),
        ...         Event(step=64, cycle=1.0, params={"gain": 0.9})
        ...     ]
        ... )
    """

    # Immutable fields (set at creation)
    pattern_id: str = Field(
        ...,
        min_length=1,
        description="Unique pattern identifier (e.g., pattern_001)"
    )
    pattern_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable pattern name"
    )
    client_id: str = Field(
        ...,
        description="Owner client ID (for ownership checks)"
    )

    # Mutable fields
    active: bool = Field(
        default=True,
        description="Whether this pattern is currently active"
    )
    events: list[Event] = Field(
        default_factory=list,
        description="Sequence of events in this pattern"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pattern_id": "pattern_001",
                    "pattern_name": "kick_pattern",
                    "client_id": "client_001",
                    "active": True,
                    "events": [
                        {"step": 0, "cycle": 0.0, "params": {}},
                        {"step": 64, "cycle": 1.0, "params": {}}
                    ]
                }
            ]
        }
    }
