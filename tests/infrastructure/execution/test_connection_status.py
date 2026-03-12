"""
Tests for connection status tracking and notification.

TDD: Write tests first, then implement connection status tracking.
"""

from __future__ import annotations

import pytest

from oiduna.infrastructure.execution import LoopEngine
from .mocks import MockMidiOutput, MockOscOutput, MockStateProducer


class TestConnectionStatusTracking:
    """Tests for connection status tracking in LoopEngine (Phase 2: delegated to ConnectionMonitor)."""

    def test_connection_monitor_initialized(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """ConnectionMonitor should be initialized."""
        assert hasattr(test_engine, "_connection_monitor")
        assert test_engine._connection_monitor is not None

    def test_connection_monitor_has_empty_status_initially(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """ConnectionMonitor status should be initially empty."""
        status = test_engine._connection_monitor.get_status()
        assert isinstance(status, dict)
        # Status is empty until first check

    def test_connection_status_after_check(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """ConnectionMonitor should track status after check (tested in service tests)."""
        # This is now tested in test_connection_monitor.py
        # LoopEngine delegates to ConnectionMonitor service
        pass


class TestConnectionStatusNotification:
    """Tests for connection status change notifications (Phase 2: delegated to ConnectionMonitor)."""

    @pytest.mark.asyncio
    async def test_notify_on_midi_disconnect(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
        mock_publisher: MockStateProducer,
    ) -> None:
        """Should send error when MIDI disconnects."""
        # First check to establish initial state
        await test_engine._connection_monitor.check_connections({
            "midi": mock_midi,
            "osc": test_engine._osc,
        })

        # Simulate disconnection
        mock_midi._connected = False

        # Check connections again
        await test_engine._connection_monitor.check_connections({
            "midi": mock_midi,
            "osc": test_engine._osc,
        })

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
        mock_publisher: MockStateProducer,
    ) -> None:
        """Should send error when OSC disconnects."""
        # First check to establish initial state
        await test_engine._connection_monitor.check_connections({
            "midi": test_engine._midi,
            "osc": mock_osc,
        })

        # Simulate disconnection
        mock_osc._connected = False

        # Check connections again
        await test_engine._connection_monitor.check_connections({
            "midi": test_engine._midi,
            "osc": mock_osc,
        })

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
        mock_publisher: MockStateProducer,
    ) -> None:
        """Should not send notification if status hasn't changed (tested in service tests)."""
        # This behavior is now tested in test_connection_monitor.py
        # ConnectionMonitor only notifies on state *changes*
        pass

    @pytest.mark.asyncio
    async def test_status_updates_after_check(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
    ) -> None:
        """Connection status should update after check."""
        # First check to establish initial state
        await test_engine._connection_monitor.check_connections({
            "midi": mock_midi,
            "osc": test_engine._osc,
        })

        # Simulate disconnection
        mock_midi._connected = False

        # Check connections again
        await test_engine._connection_monitor.check_connections({
            "midi": mock_midi,
            "osc": test_engine._osc,
        })

        # Status should be updated
        status = test_engine._connection_monitor.get_status()
        assert status["midi"] is False


class TestCheckConnectionsMethod:
    """Tests for connection monitoring (Phase 2: delegated to ConnectionMonitor)."""

    def test_connection_monitor_exists(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """ConnectionMonitor should exist."""
        assert hasattr(test_engine, "_connection_monitor")
        assert test_engine._connection_monitor is not None

    @pytest.mark.asyncio
    async def test_connection_monitor_check_is_async(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """ConnectionMonitor.check_connections should be async."""
        import asyncio
        result = test_engine._connection_monitor.check_connections({
            "midi": test_engine._midi,
            "osc": test_engine._osc,
        })
        assert asyncio.iscoroutine(result)
        await result  # Clean up the coroutine
