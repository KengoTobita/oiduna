"""
MARS Loop State Publisher

ZeroMQ PUB socket for publishing state to mars-api.
"""

from __future__ import annotations

import logging
from typing import Any

import zmq
import zmq.asyncio
from oiduna_core.ipc import IPCSerializer

logger = logging.getLogger(__name__)


class StatePublisher:
    """
    Publishes state to mars-api via ZeroMQ PUB socket.

    State messages include:
    - position: Current playback position (sent every step)
    - status: Playback status changes
    - error: Error notifications
    """

    DEFAULT_PORT = 5557

    def __init__(self, port: int = DEFAULT_PORT):
        self._port = port
        self._context: zmq.asyncio.Context | None = None
        self._socket: zmq.asyncio.Socket | None = None
        self._serializer = IPCSerializer()

    def connect(self) -> None:
        """Bind state publisher socket"""
        self._context = zmq.asyncio.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(f"tcp://127.0.0.1:{self._port}")
        logger.info(f"State publisher bound to port {self._port}")

    def disconnect(self) -> None:
        """Close state publisher socket"""
        if self._socket:
            self._socket.close()
            self._socket = None
        if self._context:
            self._context.term()
            self._context = None
        logger.info("State publisher disconnected")

    async def send(self, msg_type: str, payload: dict[str, Any]) -> None:
        """
        Send a state message

        Args:
            msg_type: Message type (position, status, error)
            payload: Message payload
        """
        if not self._socket:
            return

        data = self._serializer.serialize_message(msg_type, payload)

        try:
            await self._socket.send(data)
        except zmq.ZMQError as e:
            logger.error(f"ZMQ send error: {e}")

    async def send_position(
        self,
        position: dict[str, Any],
        bpm: float | None = None,
        transport: str | None = None,
    ) -> None:
        """
        Send position update

        Args:
            position: Position dict with step, bar, beat, timestamp
            bpm: Current BPM (optional, for UI sync)
            transport: Current transport state (optional, for UI sync)
        """
        payload = {**position}
        if bpm is not None:
            payload["bpm"] = bpm
        if transport is not None:
            payload["transport"] = transport
        await self.send("position", payload)

    async def send_status(
        self,
        transport: str,
        bpm: float,
        active_tracks: list[str],
    ) -> None:
        """
        Send status update

        Args:
            transport: Transport state ("playing", "stopped", "paused")
            bpm: Current BPM
            active_tracks: List of active track IDs
        """
        await self.send("status", {
            "transport": transport,
            "bpm": bpm,
            "active_tracks": active_tracks
        })

    async def send_error(self, code: str, message: str) -> None:
        """
        Send error notification

        Args:
            code: Error code
            message: Error message
        """
        await self.send("error_msg", {
            "code": code,
            "message": message
        })

    async def send_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """
        Send track information for Monitor display

        Args:
            tracks: List of track info dicts with track_id, sound, pattern
        """
        await self.send("tracks", {"tracks": tracks})

    @property
    def is_connected(self) -> bool:
        return self._socket is not None
