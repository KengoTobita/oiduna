"""
Unit tests for HeartbeatService.
"""

import asyncio
import pytest
from oiduna.infrastructure.execution.services.heartbeat_service import (
    HeartbeatService,
    HeartbeatPublisher,
)


class MockPublisher:
    """Mock publisher for testing."""

    def __init__(self):
        self.messages = []

    async def send(self, message_type: str, payload: dict) -> None:
        """Record sent messages."""
        self.messages.append({"type": message_type, "payload": payload})


@pytest.fixture
def publisher():
    """Create mock publisher."""
    return MockPublisher()


@pytest.fixture
def service(publisher):
    """Create heartbeat service with short interval for testing."""
    return HeartbeatService(publisher=publisher, interval=0.05)  # 50ms for fast tests


class TestHeartbeatServiceBasics:
    """Test basic heartbeat service operations."""

    def test_initialization(self, service):
        """Test service initializes correctly."""
        assert service._interval == 0.05

    @pytest.mark.asyncio
    async def test_send_single_heartbeat(self, service, publisher):
        """Test sending a single heartbeat."""
        await service.send_heartbeat()

        assert len(publisher.messages) == 1
        assert publisher.messages[0]["type"] == "heartbeat"
        assert "timestamp" in publisher.messages[0]["payload"]


class TestHeartbeatLoop:
    """Test heartbeat loop execution."""

    @pytest.mark.asyncio
    async def test_loop_sends_multiple_heartbeats(self, service, publisher):
        """Test loop sends heartbeats at regular intervals."""
        running = True

        async def run_for_a_while():
            nonlocal running
            await asyncio.sleep(0.15)  # Let it run for ~3 heartbeats
            running = False

        # Run loop and timer concurrently
        await asyncio.gather(
            service.run_loop(lambda: running),
            run_for_a_while(),
        )

        # Should have sent at least 2 heartbeats (0ms, 50ms, 100ms, 150ms)
        assert len(publisher.messages) >= 2
        assert all(msg["type"] == "heartbeat" for msg in publisher.messages)

    @pytest.mark.asyncio
    async def test_loop_stops_when_flag_false(self, service, publisher):
        """Test loop stops when running flag becomes False."""
        running = True

        async def stop_quickly():
            nonlocal running
            await asyncio.sleep(0.02)  # Stop before first heartbeat interval
            running = False

        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_quickly(),
        )

        # Should have minimal heartbeats (maybe 0-1)
        assert len(publisher.messages) <= 1


class TestCustomTasks:
    """Test custom task registration and execution."""

    @pytest.mark.asyncio
    async def test_register_and_execute_task(self, service):
        """Test custom tasks are executed with heartbeat."""
        task_executed = []

        async def custom_task():
            task_executed.append(True)

        service.register_task(custom_task)

        running = True

        async def stop_after_one():
            nonlocal running
            await asyncio.sleep(0.08)  # Let one heartbeat execute
            running = False

        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_after_one(),
        )

        # Task should have been executed at least once
        assert len(task_executed) >= 1

    @pytest.mark.asyncio
    async def test_multiple_tasks_executed(self, service):
        """Test multiple custom tasks are all executed."""
        task1_count = []
        task2_count = []

        async def task1():
            task1_count.append(1)

        async def task2():
            task2_count.append(1)

        service.register_task(task1)
        service.register_task(task2)

        running = True

        async def stop_after_one():
            nonlocal running
            await asyncio.sleep(0.08)
            running = False

        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_after_one(),
        )

        # Both tasks should have been executed
        assert len(task1_count) >= 1
        assert len(task2_count) >= 1

    @pytest.mark.asyncio
    async def test_task_error_does_not_stop_loop(self, service, publisher):
        """Test that an error in a custom task doesn't stop the heartbeat."""
        async def failing_task():
            raise RuntimeError("Task failed")

        service.register_task(failing_task)

        running = True

        async def stop_after_some():
            nonlocal running
            await asyncio.sleep(0.12)  # Let multiple heartbeats execute
            running = False

        # Should not raise despite task failure
        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_after_some(),
        )

        # Heartbeats should still be sent
        assert len(publisher.messages) >= 2


class TestProtocolCompliance:
    """Test Protocol-based dependency injection."""

    @pytest.mark.asyncio
    async def test_works_without_publisher(self):
        """Test service works without a publisher."""
        service = HeartbeatService(publisher=None, interval=0.05)

        running = True

        async def stop_quickly():
            nonlocal running
            await asyncio.sleep(0.08)
            running = False

        # Should not raise even without publisher
        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_quickly(),
        )

    @pytest.mark.asyncio
    async def test_task_executes_without_publisher(self):
        """Test custom tasks execute even without publisher."""
        service = HeartbeatService(publisher=None, interval=0.05)
        task_count = []

        async def custom_task():
            task_count.append(1)

        service.register_task(custom_task)

        running = True

        async def stop_after_one():
            nonlocal running
            await asyncio.sleep(0.08)
            running = False

        await asyncio.gather(
            service.run_loop(lambda: running),
            stop_after_one(),
        )

        # Task should still execute
        assert len(task_count) >= 1
