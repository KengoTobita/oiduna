"""
Tests for heartbeat monitoring between mars-api and mars-loop.

TDD: Write tests first, then implement heartbeat functionality.
"""

from __future__ import annotations

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.tests.mocks import MockStateSink


class TestHeartbeatLoop:
    """Tests for heartbeat loop in LoopEngine."""

    def test_heartbeat_loop_method_exists(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """_heartbeat_loop method should exist."""
        assert hasattr(test_engine, "_heartbeat_loop")
        assert callable(test_engine._heartbeat_loop)

    @pytest.mark.asyncio
    async def test_heartbeat_loop_is_async(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """_heartbeat_loop should be an async method."""
        import asyncio
        result = test_engine._heartbeat_loop()
        assert asyncio.iscoroutine(result)
        # Cancel to avoid running indefinitely
        task = asyncio.create_task(result)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestHeartbeatInterval:
    """Tests for heartbeat interval configuration."""

    def test_heartbeat_interval_constant_exists(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """HEARTBEAT_INTERVAL constant should be defined."""
        assert hasattr(LoopEngine, "HEARTBEAT_INTERVAL")

    def test_heartbeat_interval_is_reasonable(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """HEARTBEAT_INTERVAL should be between 1 and 30 seconds."""
        interval = LoopEngine.HEARTBEAT_INTERVAL
        assert 1 <= interval <= 30


class TestSendHeartbeat:
    """Tests for send_heartbeat method."""

    def test_send_heartbeat_method_exists(
        self,
        test_engine: LoopEngine,
    ) -> None:
        """send_heartbeat method should exist."""
        assert hasattr(test_engine, "send_heartbeat")
        assert callable(test_engine.send_heartbeat)

    @pytest.mark.asyncio
    async def test_send_heartbeat_sends_message(
        self,
        test_engine: LoopEngine,
        mock_publisher: MockStateSink,
    ) -> None:
        """send_heartbeat should send a heartbeat message."""
        await test_engine.send_heartbeat()

        # Should have sent a heartbeat message
        heartbeats = mock_publisher.get_messages_by_type("heartbeat")
        assert len(heartbeats) == 1

    @pytest.mark.asyncio
    async def test_send_heartbeat_includes_timestamp(
        self,
        test_engine: LoopEngine,
        mock_publisher: MockStateSink,
    ) -> None:
        """send_heartbeat should include timestamp in payload."""
        await test_engine.send_heartbeat()

        heartbeats = mock_publisher.get_messages_by_type("heartbeat")
        assert len(heartbeats) == 1
        assert "timestamp" in heartbeats[0]


class TestMockStateSinkHeartbeat:
    """Tests for MockStateSink heartbeat tracking."""

    def test_mock_tracks_heartbeat_messages(
        self,
        mock_publisher: MockStateSink,
    ) -> None:
        """MockStateSink should track heartbeat messages via send()."""
        import asyncio

        async def send_hb():
            await mock_publisher.send("heartbeat", {"timestamp": 123.456})

        asyncio.get_event_loop().run_until_complete(send_hb())

        heartbeats = mock_publisher.get_messages_by_type("heartbeat")
        assert len(heartbeats) == 1
        assert heartbeats[0]["timestamp"] == 123.456
