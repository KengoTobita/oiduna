"""
Tests for connection status tracking and notification.

TDD: Write tests first, then implement connection status tracking.
"""

from __future__ import annotations

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.tests.mocks import MockMidiOutput, MockOscOutput, MockStateSink


class TestConnectionStatusTracking:
    """Tests for connection status tracking in LoopEngine."""

    def test_connection_status_initialized(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """Connection status dict should be initialized."""
        assert hasattr(test_engine, "_connection_status")
        assert isinstance(test_engine._connection_status, dict)

    def test_connection_status_has_midi_key(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """Connection status should have 'midi' key."""
        assert "midi" in test_engine._connection_status

    def test_connection_status_has_osc_key(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """Connection status should have 'osc' key."""
        assert "osc" in test_engine._connection_status


class TestConnectionStatusNotification:
    """Tests for connection status change notifications."""

    @pytest.mark.asyncio
    async def test_notify_on_midi_disconnect(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
        mock_publisher: MockStateSink,
    ) -> None:
        """Should send error when MIDI disconnects."""
        # Setup: MIDI was connected
        test_engine._connection_status["midi"] = True

        # Simulate disconnection
        mock_midi._connected = False

        # Check connections
        await test_engine._check_connections()

        # Should have sent an error
        errors = mock_publisher.get_messages_by_type("error_msg")
        assert len(errors) >= 1
        assert any("MIDI" in e.get("code", "") or "midi" in e.get("code", "").lower()
                   for e in errors)

    @pytest.mark.asyncio
    async def test_notify_on_osc_disconnect(
        self,
        test_engine: LoopEngine,
        mock_osc: MockOscOutput,
        mock_publisher: MockStateSink,
    ) -> None:
        """Should send error when OSC disconnects."""
        # Setup: OSC was connected
        test_engine._connection_status["osc"] = True

        # Simulate disconnection
        mock_osc._connected = False

        # Check connections
        await test_engine._check_connections()

        # Should have sent an error
        errors = mock_publisher.get_messages_by_type("error_msg")
        assert len(errors) >= 1
        assert any("OSC" in e.get("code", "") or "osc" in e.get("code", "").lower()
                   for e in errors)

    @pytest.mark.asyncio
    async def test_no_notification_when_already_disconnected(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
        mock_publisher: MockStateSink,
    ) -> None:
        """Should not send notification if status hasn't changed."""
        # Setup: MIDI was already disconnected
        test_engine._connection_status["midi"] = False
        mock_midi._connected = False

        # Check connections
        await test_engine._check_connections()

        # Should NOT have sent an error
        errors = mock_publisher.get_messages_by_type("error_msg")
        midi_errors = [e for e in errors if "midi" in e.get("code", "").lower()]
        assert len(midi_errors) == 0

    @pytest.mark.asyncio
    async def test_status_updates_after_check(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
    ) -> None:
        """Connection status should update after check."""
        # Setup: Status was connected
        test_engine._connection_status["midi"] = True

        # Simulate disconnection
        mock_midi._connected = False

        # Check connections
        await test_engine._check_connections()

        # Status should be updated
        assert test_engine._connection_status["midi"] is False


class TestCheckConnectionsMethod:
    """Tests for the _check_connections method."""

    def test_check_connections_method_exists(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """_check_connections method should exist."""
        assert hasattr(test_engine, "_check_connections")
        assert callable(test_engine._check_connections)

    @pytest.mark.asyncio
    async def test_check_connections_is_async(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """_check_connections should be an async method."""
        import asyncio
        result = test_engine._check_connections()
        assert asyncio.iscoroutine(result)
        await result  # Clean up the coroutine
