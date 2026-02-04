"""
MARS Loop Command Receiver

ZeroMQ SUB socket for receiving commands from mars-api.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import zmq
import zmq.asyncio
from oiduna_core.ipc import IPCSerializer

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class CommandReceiver:
    """
    Receives commands from mars-api via ZeroMQ SUB socket.

    Commands include:
    - compile: Load compiled DSL session
    - play: Start playback
    - stop: Stop playback
    - pause: Pause playback
    - mute: Mute/unmute track
    - solo: Solo/unsolo track
    - bpm: Change BPM
    """

    DEFAULT_PORT = 5556

    def __init__(self, port: int = DEFAULT_PORT):
        self._port = port
        self._context: zmq.asyncio.Context | None = None
        self._socket: zmq.asyncio.Socket | None = None
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._serializer = IPCSerializer()

    def connect(self) -> None:
        """Connect to command publisher"""
        self._context = zmq.asyncio.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(f"tcp://127.0.0.1:{self._port}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all
        logger.info(f"Command receiver connected to port {self._port}")

    def disconnect(self) -> None:
        """Disconnect from command publisher"""
        if self._socket:
            self._socket.close()
            self._socket = None
        if self._context:
            self._context.term()
            self._context = None
        logger.info("Command receiver disconnected")

    def register_handler(
        self, command_type: str, handler: Callable[[dict[str, Any]], Any]
    ) -> None:
        """
        Register a handler for a command type

        Args:
            command_type: Command type string (e.g., "compile", "play")
            handler: Callback function taking payload dict, can return Any (including CommandResult)
        """
        self._handlers[command_type] = handler

    async def receive(self) -> tuple[str, dict[str, Any]] | None:
        """
        Receive a command (non-blocking with timeout)

        Returns:
            (command_type, payload) tuple or None if no message
        """
        if not self._socket:
            return None

        try:
            # Non-blocking poll
            if await self._socket.poll(timeout=1, flags=zmq.POLLIN):
                data = await self._socket.recv()
                msg_type, payload = self._serializer.deserialize_message(data)
                return msg_type, payload
        except zmq.ZMQError as e:
            logger.error(f"ZMQ receive error: {e}")
        except Exception as e:
            logger.error(f"Deserialization error: {e}")

        return None

    async def process_commands(self) -> int:
        """
        Process received commands using registered handlers

        Returns:
            Number of commands processed
        """
        processed = 0

        while True:
            result = await self.receive()
            if result is None:
                break

            cmd_type, payload = result
            handler = self._handlers.get(cmd_type)

            if handler:
                try:
                    handler(payload)
                    processed += 1
                except Exception as e:
                    logger.error(f"Handler error for '{cmd_type}': {e}")
            else:
                logger.warning(f"No handler for command type: {cmd_type}")

        return processed

    @property
    def is_connected(self) -> bool:
        return self._socket is not None
