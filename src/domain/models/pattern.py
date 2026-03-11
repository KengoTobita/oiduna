"""
Pattern model representing a sequence of pattern events.

Patterns are owned by Tracks and can be activated/deactivated.
Multiple patterns can be active simultaneously on a single track.
"""

from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from .events import PatternEvent


class Pattern(BaseModel):
    """
    A pattern containing a sequence of musical events.

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
        ...         PatternEvent(step=0, cycle=0.0, params={}),
        ...         PatternEvent(step=64, cycle=1.0, params={"gain": 0.9})
        ...     ]
        ... )
    """

    # Immutable fields (set at creation)
    pattern_id: str = Field(
        ...,
        description="Unique pattern identifier (4-digit hex, e.g., '3e2b')"
    )
    track_id: str = Field(
        ...,
        description="Parent track ID (4-digit hex)"
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
        description="Whether this pattern is currently active (演奏ON/OFF)"
    )
    archived: bool = Field(
        default=False,
        description="Archive flag - archived patterns are hidden but can be restored"
    )
    events: list[PatternEvent] = Field(
        default_factory=list,
        description="Sequence of pattern events in this pattern"
    )

    @field_validator("pattern_id")
    @classmethod
    def validate_pattern_id_format(cls, v: str) -> str:
        """
        Validate pattern ID format (4-digit hexadecimal).

        Args:
            v: The pattern_id to validate

        Returns:
            The validated pattern_id

        Raises:
            ValueError: If pattern_id is not 4-digit hexadecimal
        """
        if not (len(v) == 4 and all(c in "0123456789abcdef" for c in v)):
            raise ValueError(
                f"pattern_id must be 4-digit hexadecimal (e.g., '3e2b'). "
                f"Got: '{v}'"
            )
        return v

    @field_validator("track_id")
    @classmethod
    def validate_track_id_format(cls, v: str) -> str:
        """
        Validate track ID format (4-digit hexadecimal).

        Args:
            v: The track_id to validate

        Returns:
            The validated track_id

        Raises:
            ValueError: If track_id is not 4-digit hexadecimal
        """
        if not (len(v) == 4 and all(c in "0123456789abcdef" for c in v)):
            raise ValueError(
                f"track_id must be 4-digit hexadecimal (e.g., '0a1f'). "
                f"Got: '{v}'"
            )
        return v

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
