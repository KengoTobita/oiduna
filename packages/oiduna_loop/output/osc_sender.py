"""
Generic OSC Sender

Sends OSC messages to any OSC destination (SuperDirt, Supernova, scsynth, etc.)
Uses ScheduledMessage architecture.
"""

from __future__ import annotations

import logging
from typing import Any

from pythonosc import udp_client

logger = logging.getLogger(__name__)


class OscSender:
    """Generic OSC message sender (works with any OSC destination)"""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 57120  # SuperDirt default port
    DEFAULT_ADDRESS = "/dirt/play"  # SuperDirt default address

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        address: str = DEFAULT_ADDRESS,
    ):
        self._host = host
        self._port = port
        self._address = address
        self._client: udp_client.SimpleUDPClient | None = None

    def connect(self) -> None:
        """Initialize OSC client"""
        self._client = udp_client.SimpleUDPClient(self._host, self._port)
        logger.info(f"OSC client connected to {self._host}:{self._port}")

    def disconnect(self) -> None:
        """Close OSC client"""
        self._client = None
        logger.info("OSC client disconnected")

    def send(self, params: dict[str, Any]) -> bool:
        """
        Send an OSC message to configured address

        Args:
            params: Dictionary of OSC parameters

        Returns:
            True if sent successfully
        """
        if not self._client:
            logger.warning("OSC client not connected")
            return False

        try:
            # Build OSC message with alternating param names and values
            args = []
            for key, value in params.items():
                args.append(key)
                args.append(value)

            self._client.send_message(self._address, args)
            return True

        except Exception as e:
            logger.error(f"OSC send error: {e}")
            return False


    @property
    def is_connected(self) -> bool:
        return self._client is not None
