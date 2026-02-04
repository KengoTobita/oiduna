"""
MARS Loop Protocols

Abstract interfaces for testability via dependency injection.
Uses typing.Protocol for structural subtyping (duck typing).

IPC protocols are imported from oiduna_core for consistency.
"""

from oiduna_core.protocols import CommandSource, StateSink

from .output import MidiOutput, OscOutput

__all__ = [
    "MidiOutput",
    "OscOutput",
    "CommandSource",
    "StateSink",
]
