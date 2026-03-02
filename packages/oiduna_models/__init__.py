"""
Oiduna data models using Pydantic.

This package contains the core hierarchical data models for Oiduna:
- Session: Top-level container for all state
- Track: Musical tracks with destination and base parameters
- Pattern: Event sequences within tracks
- Event: Individual scheduled events
- ClientInfo: Client authentication and metadata
- Environment: Global session settings (BPM, metadata)
"""

from .session import Session
from .track import Track
from .pattern import Pattern
from .events import Event
from .client import ClientInfo
from .environment import Environment
from .id_generator import IDGenerator
from .destination_models import (
    OscDestinationConfig,
    MidiDestinationConfig,
    DestinationConfig,
)
from .loader import load_destinations, load_destinations_from_file
from .midi_helpers import (
    MidiParams,
    MidiValidationError,
    validate_midi_params,
    is_valid_midi_params,
)

__all__ = [
    "Session",
    "Track",
    "Pattern",
    "Event",
    "ClientInfo",
    "Environment",
    "IDGenerator",
    "OscDestinationConfig",
    "MidiDestinationConfig",
    "DestinationConfig",
    "load_destinations",
    "load_destinations_from_file",
    "MidiParams",
    "MidiValidationError",
    "validate_midi_params",
    "is_valid_midi_params",
]
