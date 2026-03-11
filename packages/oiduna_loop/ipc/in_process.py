"""
In-Process IPC for Oiduna

Replaces ZeroMQ-based IPC with in-process implementations.
API handlers call engine._handle_*() directly; engine publishes
events to an asyncio.Queue consumed by the SSE endpoint.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default queue size — drop-oldest keeps memory bounded
_DEFAULT_QUEUE_SIZE = 128


class NoopCommandConsumer:
    """No-op command consumer (CommandConsumer protocol).

    Implements CommandConsumer protocol.
    process_commands() always returns 0, so the _command_loop
    backoff path fires immediately and the task sleeps at full
    interval, consuming minimal CPU.
    """

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def register_handler(self, command: str, handler: Any) -> None:
        """No-op handler registration."""
        pass

    async def process_commands(self) -> int:
        return 0

    @property
    def is_connected(self) -> bool:
        """Always connected (no-op)."""
        return True

    def close(self) -> None:
        pass


class InProcessStateProducer:
    """In-process state producer and session event publisher.

    Implements two protocols:
    - StateProducer: Loop layer state updates (position, status, error, etc.)
    - SessionEventPublisher: Session layer CRUD events (track_created, pattern_updated, etc.)

    Backed by an asyncio.Queue that the SSE endpoint reads from.
    Both protocol types push events into the same unified queue.

    When the queue is full the oldest entry is dropped (drop-oldest)
    so a slow SSE consumer never back-pressures the engine loop.
    """

    def __init__(self, maxsize: int = _DEFAULT_QUEUE_SIZE) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)

    # ----------------------------------------------------------
    # Public accessors
    # ----------------------------------------------------------

    @property
    def queue(self) -> asyncio.Queue[dict[str, Any]]:
        return self._queue

    @property
    def is_connected(self) -> bool:
        """Always connected (in-process)."""
        return True

    # ----------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------

    def connect(self) -> None:
        """No-op connect (already initialized in __init__)."""
        pass

    def disconnect(self) -> None:
        """No-op disconnect."""
        pass

    def close(self) -> None:
        pass

    # ----------------------------------------------------------
    # StateProducer protocol methods
    # ----------------------------------------------------------

    async def send_position(
        self,
        position: dict[str, Any],
        bpm: float | None = None,
        transport: str | None = None,
    ) -> None:
        """Send position update with optional BPM and transport state."""
        data = dict(position)
        if bpm is not None:
            data["bpm"] = bpm
        if transport is not None:
            data["transport"] = transport
        self._push({"type": "position", "data": data})

    async def send_status(
        self,
        transport: str,
        bpm: float,
        active_tracks: list[str],
    ) -> None:
        """Send status update."""
        self._push({
            "type": "status",
            "data": {
                "transport": transport,
                "bpm": bpm,
                "active_tracks": active_tracks,
            }
        })

    async def send_error(self, code: str, message: str) -> None:
        """Send error notification."""
        self._push({
            "type": "error",
            "data": {
                "code": code,
                "message": message,
            }
        })

    async def send_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """Send track information."""
        self._push({"type": "tracks", "data": tracks})

    async def send(self, event_type: str, data: dict[str, Any]) -> None:
        """Generic send (for heartbeat and other events)."""
        self._push({"type": event_type, "data": data})

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _push(self, event: dict[str, Any]) -> None:
        """Push event, dropping oldest if queue is full (internal helper)."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # drop oldest
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    # ----------------------------------------------------------
    # SessionEventPublisher protocol method
    # ----------------------------------------------------------

    def publish(self, event: dict[str, Any]) -> None:
        """
        Publish a session event (SessionEventPublisher protocol).

        This method implements the SessionEventPublisher protocol,
        allowing Session layer managers to publish CRUD events.

        Args:
            event: Event dictionary with 'type' and 'data' keys
                Example: {"type": "track_created", "data": {...}}
        """
        self._push(event)
