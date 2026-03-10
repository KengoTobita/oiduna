"""
Oiduna data models using Pydantic.

This package contains the core hierarchical data models for Oiduna:
- Session: Top-level container for all state
- Track: Musical tracks with destination and base parameters
- Pattern: PatternEvent sequences within tracks
- PatternEvent: Individual scheduled musical events
- ClientInfo: Client authentication and metadata
- Environment: Global session settings (BPM, metadata)
"""

from .session import Session
from .track import Track
from .pattern import Pattern
from .events import PatternEvent
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
    "PatternEvent",
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
