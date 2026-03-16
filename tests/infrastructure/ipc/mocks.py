"""Mock ZeroMQ infrastructure for IPC tests.

Provides MockZmqSocket and MockZmqContext to simulate ZeroMQ behavior
without requiring real sockets or network communication.
"""

from __future__ import annotations

import asyncio
from typing import Any


class MockZmqSocket:
    """Mock ZeroMQ socket for testing.

    Simulates socket behavior including connect, bind, send, recv, and poll operations.
    """

    def __init__(self, socket_type: int):
        """Initialize mock socket.

        Args:
            socket_type: Socket type (e.g., zmq.PUB, zmq.SUB)
        """
        self._socket_type = socket_type
        self._connected = False
        self._bound = False
        self._closed = False
        self._message_queue: list[bytes] = []
        self._sent_messages: list[bytes] = []
        self._options: dict[int, Any] = {}
        self._error_on_next_send: Exception | None = None
        self._error_on_next_recv: Exception | None = None

    def connect(self, address: str) -> None:
        """Simulate socket connection.

        Args:
            address: Connection address (e.g., "tcp://127.0.0.1:5556")
        """
        if self._closed:
            raise ValueError("Socket is closed")
        self._connected = True

    def bind(self, address: str) -> None:
        """Simulate socket binding.

        Args:
            address: Bind address (e.g., "tcp://127.0.0.1:5557")
        """
        if self._closed:
            raise ValueError("Socket is closed")
        self._bound = True

    def close(self) -> None:
        """Close the socket."""
        self._closed = True
        self._connected = False
        self._bound = False

    def setsockopt(self, option: int, value: Any) -> None:
        """Set socket option.

        Args:
            option: Socket option constant
            value: Option value
        """
        self._options[option] = value

    def setsockopt_string(self, option: int, value: str) -> None:
        """Set string socket option.

        Args:
            option: Socket option constant
            value: String option value
        """
        self._options[option] = value

    async def send(self, data: bytes) -> None:
        """Simulate sending data.

        Args:
            data: Bytes to send

        Raises:
            Exception: If error was injected via inject_send_error
        """
        if self._error_on_next_send:
            error = self._error_on_next_send
            self._error_on_next_send = None
            raise error

        if not (self._connected or self._bound):
            raise ValueError("Socket not connected or bound")
        if self._closed:
            raise ValueError("Socket is closed")

        self._sent_messages.append(data)

    async def recv(self) -> bytes:
        """Simulate receiving data.

        Returns:
            Bytes from message queue

        Raises:
            Exception: If error was injected via inject_recv_error
            ValueError: If no messages available
        """
        if self._error_on_next_recv:
            error = self._error_on_next_recv
            self._error_on_next_recv = None
            raise error

        if not self._message_queue:
            raise ValueError("No messages available")

        return self._message_queue.pop(0)

    async def poll(self, timeout: int = 0, flags: int = 0) -> int:
        """Simulate polling for events.

        Args:
            timeout: Poll timeout in milliseconds
            flags: Poll flags (e.g., zmq.POLLIN)

        Returns:
            Non-zero if messages available, 0 otherwise
        """
        if self._message_queue:
            return 1

        # Simulate timeout
        if timeout > 0:
            await asyncio.sleep(timeout / 1000.0)

        return 1 if self._message_queue else 0

    # Test helper methods

    def inject_message(self, data: bytes) -> None:
        """Inject a message into the receive queue (for testing).

        Args:
            data: Message bytes to inject
        """
        self._message_queue.append(data)

    def inject_send_error(self, error: Exception) -> None:
        """Inject an error for the next send operation (for testing).

        Args:
            error: Exception to raise on next send
        """
        self._error_on_next_send = error

    def inject_recv_error(self, error: Exception) -> None:
        """Inject an error for the next recv operation (for testing).

        Args:
            error: Exception to raise on next recv
        """
        self._error_on_next_recv = error

    def get_sent_messages(self) -> list[bytes]:
        """Get list of sent messages (for testing).

        Returns:
            List of sent message bytes
        """
        return self._sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent messages history (for testing)."""
        self._sent_messages.clear()

    @property
    def is_closed(self) -> bool:
        """Check if socket is closed."""
        return self._closed

    @property
    def is_connected(self) -> bool:
        """Check if socket is connected."""
        return self._connected

    @property
    def is_bound(self) -> bool:
        """Check if socket is bound."""
        return self._bound


class MockZmqContext:
    """Mock ZeroMQ context for testing.

    Simulates context behavior including socket creation and termination.
    """

    def __init__(self):
        """Initialize mock context."""
        self._terminated = False
        self._sockets: list[MockZmqSocket] = []

    def socket(self, socket_type: int) -> MockZmqSocket:
        """Create a mock socket.

        Args:
            socket_type: Socket type (e.g., zmq.PUB, zmq.SUB)

        Returns:
            MockZmqSocket instance
        """
        if self._terminated:
            raise ValueError("Context is terminated")

        sock = MockZmqSocket(socket_type)
        self._sockets.append(sock)
        return sock

    def term(self) -> None:
        """Terminate the context."""
        self._terminated = True
        for sock in self._sockets:
            if not sock.is_closed:
                sock.close()

    @property
    def is_terminated(self) -> bool:
        """Check if context is terminated."""
        return self._terminated

    def get_sockets(self) -> list[MockZmqSocket]:
        """Get list of created sockets (for testing).

        Returns:
            List of created socket instances
        """
        return self._sockets.copy()
