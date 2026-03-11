"""Loop service - bridge between HTTP API and oiduna_loop engine"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from oiduna.infrastructure.execution import LoopEngine
from oiduna.application.factory import create_loop_engine
from oiduna.infrastructure.ipc.in_process import InProcessStateProducer

logger = logging.getLogger(__name__)


# Global instance (managed by lifespan)
_loop_service: "LoopService | None" = None


class LoopService:
    """Service for managing the loop engine lifecycle and state"""

    def __init__(self) -> None:
        self._engine: LoopEngine | None = None
        self._state_producer: InProcessStateProducer | None = None

    def initialize(
        self,
        osc_host: str = "127.0.0.1",
        osc_port: int = 57120,
        receive_port: int = 57121,
        midi_port_name: str | None = None,
        before_send_hooks: list | None = None,
    ) -> None:
        """
        Initialize the loop engine with in-process IPC.

        Args:
            osc_host: OSC host for SuperDirt
            osc_port: OSC port for SuperDirt
            receive_port: Receive port (not yet implemented)
            midi_port_name: MIDI port name
            before_send_hooks: Extension hooks from API layer
        """
        if self._engine is not None:
            return

        self._state_producer = InProcessStateProducer()
        self._engine = create_loop_engine(
            osc_host=osc_host,
            osc_port=osc_port,
            midi_port=midi_port_name,
            state_producer=self._state_producer,
            before_send_hooks=before_send_hooks,
        )
        # receive_port is for Phase 1 SuperDirt integration (not yet implemented)

    def get_engine(self) -> LoopEngine:
        """Get the loop engine instance"""
        if self._engine is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._engine

    def get_state_producer(self) -> InProcessStateProducer:
        """Get the state producer (for SSE endpoint)"""
        if self._state_producer is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._state_producer

    def connect_timeline(self, container) -> None:
        """
        Connect the SessionContainer's timeline to the LoopEngine.

        This should be called during app startup after the container is initialized.

        Args:
            container: SessionContainer with timeline manager
        """
        if self._engine is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        # Set the timeline from the container
        self._engine.set_timeline(container.timeline.timeline)
        logger.info("Timeline connected to LoopEngine")


def get_loop_service() -> LoopService:
    """
    FastAPI dependency to get the LoopService instance.

    This is the preferred way to access the LoopService in route handlers.

    Returns:
        LoopService instance

    Raises:
        RuntimeError: If service is not initialized
    """
    global _loop_service
    if _loop_service is None:
        raise RuntimeError("LoopService not initialized. Ensure app lifespan is running.")
    return _loop_service


@asynccontextmanager
async def lifespan(
    osc_host: str = "127.0.0.1",
    osc_port: int = 57120,
    receive_port: int = 57121,
    midi_port_name: str | None = None,
    before_send_hooks: list | None = None,
) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI.

    Args:
        osc_host: OSC host for SuperDirt
        osc_port: OSC port for SuperDirt
        receive_port: Receive port (not yet implemented)
        midi_port_name: MIDI port name
        before_send_hooks: Extension hooks from API layer
    """
    global _loop_service
    _loop_service = LoopService()
    _loop_service.initialize(
        osc_host=osc_host,
        osc_port=osc_port,
        receive_port=receive_port,
        midi_port_name=midi_port_name,
        before_send_hooks=before_send_hooks,
    )
    engine = _loop_service.get_engine()
    engine.start()
    engine_task = asyncio.create_task(engine.run())
    logger.info("Loop engine started")

    yield

    # Cleanup
    engine.stop()
    engine_task.cancel()
    try:
        await engine_task
    except asyncio.CancelledError:
        pass
    _loop_service = None
    logger.info("Loop engine stopped")
