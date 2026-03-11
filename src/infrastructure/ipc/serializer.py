"""IPC Serializer for Oiduna Framework.

Provides msgpack-based serialization for efficient IPC communication
between oiduna_api and oiduna_loop.
"""

from __future__ import annotations

import json
from typing import Any, Literal, cast

import msgpack

# Serialization format type
SerializationFormat = Literal["json", "msgpack"]


class IPCSerializer:
    """IPC message serializer.

    Supports both msgpack (default, efficient) and JSON (fallback) formats.
    The format can be switched at runtime for debugging or compatibility.

    Usage:
        serializer = IPCSerializer()  # default: msgpack
        data = serializer.serialize({"type": "compile", "payload": {...}})
        msg = serializer.deserialize(data)

        # For debugging with JSON:
        serializer = IPCSerializer(format="json")
    """

    def __init__(self, format: SerializationFormat = "msgpack"):
        """Initialize serializer.

        Args:
            format: Serialization format ("msgpack" or "json")
        """
        self._format = format

    @property
    def format(self) -> SerializationFormat:
        """Get current serialization format."""
        return self._format

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize data to bytes.

        Args:
            data: Dictionary to serialize

        Returns:
            Serialized bytes
        """
        if self._format == "json":
            return json.dumps(data).encode("utf-8")
        return cast(bytes, msgpack.packb(data, use_bin_type=True))

    def deserialize(self, payload: bytes) -> dict[str, Any]:
        """Deserialize bytes to dictionary.

        Args:
            payload: Bytes to deserialize

        Returns:
            Deserialized dictionary
        """
        if self._format == "json":
            result = json.loads(payload.decode("utf-8"))
        else:
            result = msgpack.unpackb(payload, raw=False)

        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        return result

    def serialize_message(
        self,
        msg_type: str,
        payload: dict[str, Any] | None = None,
    ) -> bytes:
        """Serialize an IPC message with type and payload.

        This is a convenience method for the standard message format.

        Args:
            msg_type: Message type (e.g., "compile", "play", "position")
            payload: Message payload (optional)

        Returns:
            Serialized bytes
        """
        return self.serialize({
            "type": msg_type,
            "payload": payload or {},
        })

    def deserialize_message(self, data: bytes) -> tuple[str, dict[str, Any]]:
        """Deserialize an IPC message to type and payload.

        Args:
            data: Serialized message bytes

        Returns:
            Tuple of (message_type, payload)
        """
        msg = self.deserialize(data)
        return msg.get("type", ""), msg.get("payload", {})
