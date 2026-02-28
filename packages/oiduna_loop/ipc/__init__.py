"""Oiduna Loop IPC — protocols, serialization, and in-process implementations."""

from .in_process import InProcessStateSink, NoopCommandSource
from .protocols import CommandSink, CommandSource, StateSink, StateSource
from .serializer import IPCSerializer, SerializationFormat

__all__ = [
    # In-process implementations
    "NoopCommandSource",
    "InProcessStateSink",
    # Protocols
    "CommandSink",
    "CommandSource",
    "StateSink",
    "StateSource",
    # Serialization
    "IPCSerializer",
    "SerializationFormat",
]
