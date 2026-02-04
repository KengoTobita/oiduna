"""
MARS Loop OSC Sender

Sends OSC messages to SuperDirt for audio playback.
Uses Output IR (Layer 3) via send_osc_event().
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pythonosc import udp_client

if TYPE_CHECKING:
    from oiduna_core.output.output import OscEvent

logger = logging.getLogger(__name__)


class OscSender:
    """SuperDirt OSC message sender"""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 57120  # SuperDirt default port
    ADDRESS = "/dirt/play"

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._host = host
        self._port = port
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
        Send an OSC message to SuperDirt

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

            self._client.send_message(self.ADDRESS, args)
            return True

        except Exception as e:
            logger.error(f"OSC send error: {e}")
            return False

    def send_osc_event(self, event: OscEvent) -> bool:
        """
        Send a pre-computed OscEvent to SuperDirt.

        This is the new Output IR (Layer 3) interface. The event contains
        all pre-computed values (gain with velocity/modulation applied,
        sustain in seconds, etc.) ready for direct transmission.

        Args:
            event: Pre-computed OscEvent from StepProcessor.process_step_v2()

        Returns:
            True if sent successfully

        Example:
            >>> step_output = processor.process_step_v2(state)
            >>> for osc_event in step_output.osc_events:
            ...     sender.send_osc_event(osc_event)
        """
        if not self._client:
            logger.warning("OSC client not connected")
            return False

        try:
            self._client.send_message(self.ADDRESS, event.to_osc_args())
            return True
        except Exception as e:
            logger.error(f"OSC send error: {e}")
            return False

    def send_silence(self, orbit: int = 0) -> bool:
        """Send silence command to an orbit"""
        return self.send({"s": "~", "orbit": orbit})

    @property
    def is_connected(self) -> bool:
        return self._client is not None
