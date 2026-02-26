"""
Destination configuration package.

This package handles validation and loading of destination configurations
(OSC and MIDI endpoints) for the Oiduna engine.

Design principle: Use Pydantic for validation at config-load time.
Runtime messages use lightweight dataclasses (see oiduna_scheduler).
"""

from destination_models import (
    DestinationConfig,
    OscDestinationConfig,
    MidiDestinationConfig,
)
from loader import load_destinations, load_destinations_from_file

__all__ = [
    "DestinationConfig",
    "OscDestinationConfig",
    "MidiDestinationConfig",
    "load_destinations",
    "load_destinations_from_file",
]
