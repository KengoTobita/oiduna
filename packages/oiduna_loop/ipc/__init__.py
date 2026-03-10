"""Oiduna Loop IPC — protocols, serialization, and in-process implementations."""

from .in_process import InProcessStateSink, NoopCommandSource
from .serializer import IPCSerializer, SerializationFormat

__all__ = [
    # In-process implementations
    "NoopCommandSource",
    "InProcessStateSink",
    # Serialization
    "IPCSerializer",
    "SerializationFormat",
]
