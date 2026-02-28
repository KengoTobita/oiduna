"""
IPC Protocols

Abstract interfaces for inter-process communication between oiduna_api and oiduna_loop.

This module defines four protocol interfaces:
- CommandSink: API side (sends commands to loop)
- CommandSource: Loop side (receives commands from API)
- StateSink: Loop side (sends state to API)
- StateSource: API side (receives state from loop)

Data Flow:
    oiduna_api                    oiduna_loop
    ──────────                    ───────────
    CommandSink  ─── ZMQ ───►  CommandSource
    StateSource  ◄── ZMQ ───   StateSink
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

# =============================================================================
# Command Channel: API → Loop
# =============================================================================


@runtime_checkable
class CommandSink(Protocol):
    """
    Command sender interface (API → Loop).

    Used by oiduna_api to send commands to oiduna_loop.

    Implementations:
        - CommandSender: Real ZeroMQ PUB socket
        - Mock: Test double for unit tests
    """

    def connect(self) -> None:
        """Connect to command bus."""
        ...

    def disconnect(self) -> None:
        """Disconnect from command bus."""
        ...

    def send(self, cmd_type: str, payload: dict[str, Any] | None = None) -> None:
        """
        Send a command.

        Args:
            cmd_type: Command type
            payload: Command payload
        """
        ...

    def send_compile(self, session_data: dict[str, Any]) -> None:
        """Send compiled session to loop."""
        ...

    def send_play(self) -> None:
        """Send play command."""
        ...

    def send_stop(self) -> None:
        """Send stop command."""
        ...

    def send_pause(self) -> None:
        """Send pause command."""
        ...

    def send_mute(self, track_id: str, mute: bool = True) -> None:
        """Send mute command."""
        ...

    def send_solo(self, track_id: str, solo: bool = True) -> None:
        """Send solo command."""
        ...

    def send_bpm(self, bpm: float) -> None:
        """Send BPM change command."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to command bus."""
        ...


@runtime_checkable
class CommandSource(Protocol):
    """
    Command receiver interface (API → Loop).

    Used by oiduna_loop to receive commands from oiduna_api.

    Implementations:
        - CommandReceiver: Real ZeroMQ SUB socket
        - MockCommandSource: Test double for unit tests
    """

    def connect(self) -> None:
        """Connect to command source."""
        ...

    def disconnect(self) -> None:
        """Disconnect from command source."""
        ...

    def register_handler(
        self,
        command_type: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """
        Register a handler for a command type.

        Args:
            command_type: Command type (e.g., "play", "stop", "compile")
            handler: Callback function taking payload dict, can return Any (including CommandResult)
        """
        ...

    async def receive(self) -> tuple[str, dict[str, Any]] | None:
        """
        Receive a command.

        Returns:
            (command_type, payload) tuple or None if no message
        """
        ...

    async def process_commands(self) -> int:
        """
        Process all pending commands.

        Returns:
            Number of commands processed
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to command source."""
        ...


# =============================================================================
# State Channel: Loop → API
# =============================================================================


@runtime_checkable
class StateSink(Protocol):
    """
    State publisher interface (Loop → API).

    Used by oiduna_loop to send state updates to oiduna_api.

    Implementations:
        - StatePublisher: Real ZeroMQ PUB socket
        - MockStateSink: Test double for unit tests
    """

    def connect(self) -> None:
        """Connect to state sink."""
        ...

    def disconnect(self) -> None:
        """Disconnect from state sink."""
        ...

    async def send(self, msg_type: str, payload: dict[str, Any]) -> None:
        """
        Send state message.

        Args:
            msg_type: Message type (e.g., "position", "status")
            payload: Message payload
        """
        ...

    async def send_position(
        self,
        position: dict[str, Any],
        bpm: float | None = None,
        transport: str | None = None,
    ) -> None:
        """
        Send position update.

        Args:
            position: Position data (step, bar, beat, etc.)
            bpm: Current BPM (optional, for UI sync)
            transport: Transport state (optional, for UI sync)
        """
        ...

    async def send_status(
        self,
        transport: str,
        bpm: float,
        active_tracks: list[str],
    ) -> None:
        """
        Send status update.

        Args:
            transport: Transport state ("playing", "stopped", "paused")
            bpm: Current BPM
            active_tracks: List of active track IDs
        """
        ...

    async def send_error(self, code: str, message: str) -> None:
        """
        Send error notification.

        Args:
            code: Error code
            message: Error message
        """
        ...

    async def send_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """
        Send track information for Monitor display.

        Args:
            tracks: List of track info dicts with track_id, sound, pattern
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to state sink."""
        ...


@runtime_checkable
class StateSource(Protocol):
    """
    State receiver interface (Loop → API).

    Used by oiduna_api to receive state updates from oiduna_loop.

    Implementations:
        - StateReceiver: Real ZeroMQ SUB socket
        - Mock: Test double for unit tests
    """

    def connect(self) -> None:
        """Connect to state bus."""
        ...

    def disconnect(self) -> None:
        """Disconnect from state bus."""
        ...

    async def receive(self, timeout: int = 100) -> tuple[str, dict[str, Any]] | None:
        """
        Receive a state message.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            (msg_type, payload) tuple or None if no message
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Whether connected to state bus."""
        ...
