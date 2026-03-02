"""
MARS Loop Protocols

Abstract interfaces for testability via dependency injection.
Uses typing.Protocol for structural subtyping (duck typing).
"""

from ..ipc.protocols import (
    CommandConsumer,
    CommandProducer,
    CommandSource,  # Legacy
    CommandSink,  # Legacy
    StateConsumer,
    StateProducer,
    StateSource,  # Legacy
    StateSink,  # Legacy
)

from .output import MidiOutput, OscOutput

__all__ = [
    # Output protocols
    "MidiOutput",
    "OscOutput",
    # IPC protocols (Producer/Consumer pattern)
    "CommandConsumer",
    "CommandProducer",
    "StateConsumer",
    "StateProducer",
    # Legacy IPC protocols (deprecated)
    "CommandSource",
    "CommandSink",
    "StateSource",
    "StateSink",
]
