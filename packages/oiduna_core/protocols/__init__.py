"""
Protocol interfaces for oiduna_core.

This module exports protocol definitions for:
- IPC communication (CommandSource, StateSink)
- Session IR (SessionIRProtocol)
"""

from oiduna_core.protocols.ipc import CommandSink, CommandSource, StateSink, StateSource
from oiduna_core.protocols.session import (
    SequenceProtocol,
    SessionIRProtocol,
    TrackProtocol,
)

__all__ = [
    # IPC protocols
    "CommandSink",
    "CommandSource",
    "StateSink",
    "StateSource",
    # Session IR protocols
    "SessionIRProtocol",
    "SequenceProtocol",
    "TrackProtocol",
]
