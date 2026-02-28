"""
MARS Loop Protocols

Abstract interfaces for testability via dependency injection.
Uses typing.Protocol for structural subtyping (duck typing).
"""

from ..ipc.protocols import CommandSource, StateSink

from .output import MidiOutput, OscOutput

__all__ = [
    "MidiOutput",
    "OscOutput",
    "CommandSource",
    "StateSink",
]
