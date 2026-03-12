"""
Unit tests for ConnectionMonitor service.
"""

import pytest
from oiduna.infrastructure.execution.services.connection_monitor import (
    ConnectionMonitor,
    ConnectionStatusNotifier,
)


class MockNotifier:
    """Mock notifier for testing."""

    def __init__(self):
        self.errors = []

    async def send_error(self, error_code: str, message: str) -> None:
        """Record error notifications."""
        self.errors.append({"code": error_code, "message": message})


class MockConnection:
    """Mock connection object."""

    def __init__(self, is_connected: bool = True):
        self._is_connected = is_connected

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._is_connected

    def set_connected(self, connected: bool) -> None:
        """Set connection status."""
        self._is_connected = connected


@pytest.fixture
def notifier():
    """Create mock notifier."""
    return MockNotifier()


@pytest.fixture
def monitor(notifier):
    """Create connection monitor with mock notifier."""
    return ConnectionMonitor(notifier=notifier)


@pytest.fixture
def midi_conn():
    """Create mock MIDI connection."""
    return MockConnection(is_connected=True)


@pytest.fixture
def osc_conn():
    """Create mock OSC connection."""
    return MockConnection(is_connected=True)


class TestConnectionMonitorBasics:
    """Test basic connection monitor operations."""

    def test_initialization(self, monitor):
        """Test monitor initializes with empty status."""
        status = monitor.get_status()
        assert status == {}

    def test_register_connection(self, monitor, midi_conn):
        """Test registering a connection."""
        monitor.register("midi", midi_conn)
        status = monitor.get_status()
        assert "midi" in status
        assert status["midi"] is True


class TestConnectionStatusTracking:
    """Test connection status tracking."""

    @pytest.mark.asyncio
    async def test_connection_stays_connected(self, monitor, notifier, midi_conn):
        """Test no notification when connection stays connected."""
        await monitor.check_connections({"midi": midi_conn})
        await monitor.check_connections({"midi": midi_conn})

        # No errors should be sent
        assert len(notifier.errors) == 0

    @pytest.mark.asyncio
    async def test_connection_lost_notification(self, monitor, notifier, midi_conn):
        """Test notification sent when connection is lost."""
        # Initial check - connection is up
        await monitor.check_connections({"midi": midi_conn})

        # Lose connection
        midi_conn.set_connected(False)
        await monitor.check_connections({"midi": midi_conn})

        # Should send error notification
        assert len(notifier.errors) == 1
        assert notifier.errors[0]["code"] == "CONNECTION_LOST_MIDI"
        assert "MIDI connection lost" in notifier.errors[0]["message"]

    @pytest.mark.asyncio
    async def test_multiple_connections(self, monitor, notifier, midi_conn, osc_conn):
        """Test monitoring multiple connections."""
        connections = {"midi": midi_conn, "osc": osc_conn}

        # Initial check - both connected
        await monitor.check_connections(connections)

        # Lose MIDI connection
        midi_conn.set_connected(False)
        await monitor.check_connections(connections)

        # Only MIDI error should be sent
        assert len(notifier.errors) == 1
        assert notifier.errors[0]["code"] == "CONNECTION_LOST_MIDI"

        # Lose OSC connection
        osc_conn.set_connected(False)
        await monitor.check_connections(connections)

        # Now both errors should be recorded
        assert len(notifier.errors) == 2
        assert notifier.errors[1]["code"] == "CONNECTION_LOST_OSC"

    @pytest.mark.asyncio
    async def test_reconnection_no_notification(self, monitor, notifier, midi_conn):
        """Test no notification when connection reconnects."""
        # Initial check
        await monitor.check_connections({"midi": midi_conn})

        # Lose connection
        midi_conn.set_connected(False)
        await monitor.check_connections({"midi": midi_conn})

        # Reconnect
        midi_conn.set_connected(True)
        await monitor.check_connections({"midi": midi_conn})

        # Only one error for the disconnect
        assert len(notifier.errors) == 1

    @pytest.mark.asyncio
    async def test_never_connected_no_notification(self, monitor, notifier):
        """Test no notification for connection that was never connected."""
        disconnected_conn = MockConnection(is_connected=False)

        # First check with disconnected connection
        await monitor.check_connections({"midi": disconnected_conn})

        # No error should be sent (was never connected before)
        assert len(notifier.errors) == 0


class TestStatusReporting:
    """Test status reporting."""

    @pytest.mark.asyncio
    async def test_get_status_reflects_current_state(self, monitor, midi_conn, osc_conn):
        """Test get_status returns current state."""
        connections = {"midi": midi_conn, "osc": osc_conn}

        await monitor.check_connections(connections)

        status = monitor.get_status()
        assert status["midi"] is True
        assert status["osc"] is True

        # Lose MIDI connection
        midi_conn.set_connected(False)
        await monitor.check_connections(connections)

        status = monitor.get_status()
        assert status["midi"] is False
        assert status["osc"] is True


class TestProtocolCompliance:
    """Test Protocol-based dependency injection."""

    @pytest.mark.asyncio
    async def test_works_without_notifier(self, midi_conn):
        """Test monitor works without a notifier."""
        monitor = ConnectionMonitor(notifier=None)

        # Should not raise even without notifier
        await monitor.check_connections({"midi": midi_conn})
        midi_conn.set_connected(False)
        await monitor.check_connections({"midi": midi_conn})

        # Status should still be tracked
        status = monitor.get_status()
        assert status["midi"] is False
