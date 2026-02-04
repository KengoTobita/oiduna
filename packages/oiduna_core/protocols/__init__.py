"""
Protocol interfaces for oiduna_core.

This module exports protocol definitions for:
- IPC communication (CommandSource, StateSink)
- Output interfaces (MidiOutput, OscOutput)
- Session IR (SessionIRProtocol)
"""

from oiduna_core.protocols.common_output import MidiOutputProtocol, OscOutputProtocol
from oiduna_core.protocols.ipc import CommandSink, CommandSource, StateSink, StateSource
from oiduna_core.protocols.output import MidiOutput, OscOutput
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
    # Output protocols (common)
    "MidiOutputProtocol",
    "OscOutputProtocol",
    # Output protocols (extended)
    "MidiOutput",
    "OscOutput",
    # Session IR protocols
    "SessionIRProtocol",
    "SequenceProtocol",
    "TrackProtocol",
]
