"""Oiduna Loop IPC — protocols, serialization, and in-process implementations."""

from .in_process import InProcessStateProducer, NoopCommandConsumer
# from .serializer import IPCSerializer, SerializationFormat

__all__ = [
    # In-process implementations
    "NoopCommandConsumer",
    "InProcessStateProducer",
    # Serialization (commented out - requires msgpack)
    # "IPCSerializer",
    # "SerializationFormat",
]
