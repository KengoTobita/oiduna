"""Mock transport infrastructure for testing.

Provides MockOscClient and MockMidiPort to simulate OSC and MIDI behavior
without requiring real network/hardware connections.
"""

from __future__ import annotations

from typing import Any


class MockOscClient:
    """Mock OSC client for testing.

    Records all sent OSC messages for verification.
    """

    def __init__(self, host: str, port: int):
        """Initialize mock OSC client.

        Args:
            host: OSC server host
            port: OSC server port
        """
        self.host = host
        self.port = port
        self._messages: list[tuple[str, list[Any]]] = []
        self._error_on_next_send: Exception | None = None

    def send_message(self, address: str, args: list[Any]) -> None:
        """Simulate sending an OSC message.

        Args:
            address: OSC address (e.g., "/dirt/play")
            args: List of OSC arguments

        Raises:
            Exception: If error was injected via inject_send_error
        """
        if self._error_on_next_send:
            error = self._error_on_next_send
            self._error_on_next_send = None
            raise error

        self._messages.append((address, args))

    def get_messages(self) -> list[tuple[str, list[Any]]]:
        """Get list of sent messages (for testing).

        Returns:
            List of (address, args) tuples
        """
        return self._messages.copy()

    def clear_messages(self) -> None:
        """Clear sent messages history (for testing)."""
        self._messages.clear()

    def inject_send_error(self, error: Exception) -> None:
        """Inject an error for the next send operation (for testing).

        Args:
            error: Exception to raise on next send
        """
        self._error_on_next_send = error


class MockMidiPort:
    """Mock MIDI output port for testing.

    Records all sent MIDI messages and tracks active notes.
    """

    def __init__(self, name: str):
        """Initialize mock MIDI port.

        Args:
            name: Port name
        """
        self.name = name
        self._messages: list[Any] = []
        self._closed = False
        self._error_on_next_send: Exception | None = None

    def send(self, message: Any) -> None:
        """Simulate sending a MIDI message.

        Args:
            message: MIDI message to send

        Raises:
            ValueError: If port is closed
            Exception: If error was injected via inject_send_error
        """
        if self._closed:
            raise ValueError("Port is closed")

        if self._error_on_next_send:
            error = self._error_on_next_send
            self._error_on_next_send = None
            raise error

        self._messages.append(message)

    def close(self) -> None:
        """Close the port."""
        self._closed = True

    def get_messages(self) -> list[Any]:
        """Get list of sent messages (for testing).

        Returns:
            List of MIDI messages
        """
        return self._messages.copy()

    def clear_messages(self) -> None:
        """Clear sent messages history (for testing)."""
        self._messages.clear()

    def inject_send_error(self, error: Exception) -> None:
        """Inject an error for the next send operation (for testing).

        Args:
            error: Exception to raise on next send
        """
        self._error_on_next_send = error

    @property
    def is_closed(self) -> bool:
        """Check if port is closed."""
        return self._closed


class MockMidiModule:
    """Mock mido module for testing."""

    def __init__(self):
        self._output_ports: list[str] = []
        self._opened_ports: dict[str, MockMidiPort] = {}

    def set_output_ports(self, ports: list[str]) -> None:
        """Set available output ports (for testing).

        Args:
            ports: List of port names
        """
        self._output_ports = ports

    def get_output_names(self) -> list[str]:
        """Get list of available output ports.

        Returns:
            List of port names
        """
        return self._output_ports.copy()

    def open_output(self, name: str) -> MockMidiPort:
        """Open a MIDI output port.

        Args:
            name: Port name

        Returns:
            MockMidiPort instance

        Raises:
            OSError: If port doesn't exist
        """
        if name not in self._output_ports:
            raise OSError(f"Port '{name}' not found")

        port = MockMidiPort(name)
        self._opened_ports[name] = port
        return port

    def get_opened_port(self, name: str) -> MockMidiPort | None:
        """Get an opened port (for testing).

        Args:
            name: Port name

        Returns:
            MockMidiPort instance or None
        """
        return self._opened_ports.get(name)
