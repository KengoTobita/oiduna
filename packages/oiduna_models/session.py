"""
Session model - top-level container for all Oiduna state.

A Session is the single source of truth for:
- Environment (BPM, metadata)
- Destinations (OSC/MIDI routing)
- Clients (authentication)
- Tracks (with Patterns and Events)
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from .environment import Environment
from .client import ClientInfo
from .track import Track
from .destination_models import DestinationConfig


class Session(BaseModel):
    """
    Complete session state - single source of truth.

    The Session contains all state for an Oiduna instance:
    - Environment: Global settings (BPM, metadata)
    - Destinations: Available output destinations
    - Clients: Connected clients with tokens
    - Tracks: Musical tracks with patterns
    - Version: Optimistic locking for concurrent updates

    Example:
        >>> session = Session(
        ...     environment=Environment(bpm=140.0),
        ...     destinations={
        ...         "superdirt": OscDestinationConfig(
        ...             id="superdirt",
        ...             type="osc",
        ...             host="127.0.0.1",
        ...             port=57120,
        ...             address="/dirt/play"
        ...         )
        ...     },
        ...     clients={},
        ...     tracks={}
        ... )
    """

    version: int = Field(
        default=0,
        description="Session version for optimistic locking (incremented on each sync)"
    )
    last_modified_by: Optional[str] = Field(
        default=None,
        description="Client ID who last modified the session"
    )
    last_modified_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last modification (UTC)"
    )

    environment: Environment = Field(
        default_factory=Environment,
        description="Global session environment (BPM, metadata)"
    )
    destinations: dict[str, DestinationConfig] = Field(
        default_factory=dict,
        description="Available destinations (key = destination_id)"
    )
    clients: dict[str, ClientInfo] = Field(
        default_factory=dict,
        description="Connected clients (key = client_id)"
    )
    tracks: dict[str, Track] = Field(
        default_factory=dict,
        description="Musical tracks (key = track_id)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "version": 0,
                    "last_modified_by": None,
                    "last_modified_at": None,
                    "environment": {
                        "bpm": 120.0,
                        "metadata": {},
                        "initial_metadata": {}
                    },
                    "destinations": {},
                    "clients": {},
                    "tracks": {}
                }
            ]
        }
    }
