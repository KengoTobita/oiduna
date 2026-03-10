"""
MARS Loop Protocols

Abstract interfaces for testability via dependency injection.
Uses typing.Protocol for structural subtyping (duck typing).
"""

from ..ipc.protocols import (
    CommandConsumer,
    CommandProducer,
    StateConsumer,
    StateProducer,
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
]
