"""E2E tests for engine startup and shutdown."""

import pytest

from e2e.helpers import E2EAssertions


@pytest.mark.e2e
@pytest.mark.asyncio
class TestStartupShutdown:
    """Test engine startup and shutdown cycles."""

    async def test_engine_startup_and_shutdown(self, e2e_engine):
        """Test clean startup and shutdown cycle."""
        # Arrange
        engine = e2e_engine

        # Act - Start
        engine.start()

        # Assert - Started
        assert engine.state is not None
        assert engine._osc.is_connected
        assert engine._command_consumer.is_connected
        assert engine._state_producer.is_connected

        # Act - Stop
        engine.stop()

        # Assert - Stopped
        assert not engine._running

    async def test_engine_restart_cycle(self, e2e_engine):
        """Test multiple start/stop cycles."""
        # Arrange
        engine = e2e_engine

        # Act & Assert - Multiple cycles
        for i in range(3):
            engine.start()
            assert engine._osc.is_connected, f"Cycle {i}: OSC not connected"
            assert engine._command_consumer.is_connected, f"Cycle {i}: Commands not connected"

            engine.stop()
            assert not engine._running, f"Cycle {i}: Engine still running"
