"""
Environment model for global session settings.

The Environment contains mutable global parameters like BPM and metadata,
as well as immutable initial metadata for reference.
"""

from typing import Any
from pydantic import BaseModel, Field


class Environment(BaseModel):
    """
    Global session environment settings.

    Mutable fields (via PATCH /session/environment):
        - bpm
        - metadata

    Immutable fields (set at session creation):
        - initial_metadata

    Example:
        >>> env = Environment(
        ...     bpm=120.0,
        ...     metadata={"key": "Am", "scale": "minor"},
        ...     initial_metadata={"created_by": "client_001"}
        ... )
    """

    # Mutable fields
    bpm: float = Field(
        default=120.0,
        gt=20.0,
        lt=999.0,
        description="Beats per minute (20-999)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Mutable session metadata (key, scale, etc.)"
    )

    # Immutable field (set at session creation)
    initial_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Immutable initial metadata (for reference)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "bpm": 120.0,
                    "metadata": {"key": "Am", "scale": "minor"},
                    "initial_metadata": {"created_at": "2026-02-28T10:00:00Z"}
                }
            ]
        }
    }
