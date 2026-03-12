"""
Connection Monitor Service

Monitors connection status for MIDI and OSC outputs and notifies on changes.

Martin Fowler patterns applied:
- Extract Class: Separated connection monitoring from LoopEngine
- Single Responsibility Principle: Only handles connection status tracking
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class ConnectionStatusNotifier(Protocol):
    """
    Protocol for connection status notifications.

    Allows ConnectionMonitor to notify about connection changes without
    coupling to specific notification implementations.
    """

    async def send_error(self, error_code: str, message: str) -> None:
        """
        Send an error notification.

        Args:
            error_code: Error code identifier (e.g., "CONNECTION_LOST_MIDI")
            message: Human-readable error message
        """
        ...


class ConnectionCheckable(Protocol):
    """
    Protocol for objects with connection status.

    Represents any component (MIDI, OSC) that can report connection status.
    """

    @property
    def is_connected(self) -> bool:
        """Return True if connected, False otherwise."""
        ...


class ConnectionMonitor:
    """
    Monitors connection status for output devices.

    Tracks MIDI and OSC connection status and sends notifications
    when connections are lost.

    Single responsibility: Connection status monitoring
    """

    def __init__(self, notifier: ConnectionStatusNotifier | None = None):
        """
        Initialize connection monitor.

        Args:
            notifier: Optional notifier for connection status changes
        """
        self._notifier = notifier
        self._status: dict[str, bool] = {}

    def register(self, name: str, checkable: ConnectionCheckable) -> None:
        """
        Register a connection to monitor.

        Args:
            name: Name of the connection (e.g., "midi", "osc")
            checkable: Object with is_connected property
        """
        self._status[name] = checkable.is_connected

    async def check_connections(
        self,
        connections: dict[str, ConnectionCheckable],
    ) -> None:
        """
        Check connection status and notify on changes.

        Args:
            connections: Dictionary of connection name to checkable object
                        (e.g., {"midi": midi_sender, "osc": osc_sender})
        """
        current_status = {
            name: conn.is_connected
            for name, conn in connections.items()
        }

        # Check for status changes and notify
        for name, connected in current_status.items():
            prev_connected = self._status.get(name, False)

            if prev_connected and not connected:
                # Was connected, now disconnected -> send error
                error_code = f"CONNECTION_LOST_{name.upper()}"
                message = f"{name.upper()} connection lost"

                if self._notifier:
                    await self._notifier.send_error(error_code, message)

                logger.warning(f"{name.upper()} connection lost")

        # Update stored status
        self._status.update(current_status)

    def get_status(self) -> dict[str, bool]:
        """
        Get current connection status.

        Returns:
            Dictionary of connection name to status (True = connected)
        """
        return self._status.copy()
