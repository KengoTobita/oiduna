"""
Track model representing a musical track with patterns.

Tracks connect to destinations and have base parameters that apply
to all events in their patterns.
"""

from typing import Any
from pydantic import BaseModel, Field
from .pattern import Pattern


class Track(BaseModel):
    """
    A musical track containing patterns and routing to a destination.

    Tracks are the primary organizational unit:
    - Route to a specific destination (SuperDirt, MIDI device, etc.)
    - Have base_params applied to all events in all patterns
    - Contain multiple patterns that can be independently activated
    - Are owned by a client

    Immutable fields (set at creation):
        - track_id
        - track_name
        - destination_id
        - client_id

    Mutable fields (via PATCH):
        - base_params (shallow merge)
        - patterns (CRUD operations)

    Example:
        >>> track = Track(
        ...     track_id="track_001",
        ...     track_name="kick",
        ...     destination_id="superdirt",
        ...     client_id="client_001",
        ...     base_params={"sound": "bd", "orbit": 0},
        ...     patterns={}
        ... )
    """

    # Immutable fields (set at creation)
    track_id: str = Field(
        ...,
        min_length=1,
        description="Unique track identifier (e.g., track_001)"
    )
    track_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable track name"
    )
    destination_id: str = Field(
        ...,
        description="Target destination ID (must exist in session.destinations)"
    )
    client_id: str = Field(
        ...,
        description="Owner client ID (for ownership checks)"
    )

    # Mutable fields
    base_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Base parameters applied to all events in all patterns"
    )
    patterns: dict[str, Pattern] = Field(
        default_factory=dict,
        description="Patterns in this track (key = pattern_id)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "track_id": "track_001",
                    "track_name": "kick",
                    "destination_id": "superdirt",
                    "client_id": "client_001",
                    "base_params": {"sound": "bd", "orbit": 0},
                    "patterns": {}
                }
            ]
        }
    }
