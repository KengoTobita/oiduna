"""E2E Engine Manager for background task management."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oiduna.infrastructure.execution import LoopEngine

logger = logging.getLogger(__name__)


class E2EEngineManager:
    """Manage LoopEngine lifecycle with timeout support and async loop management.

    This helper extends the StabilityTestEngine pattern with enhanced async support
    for E2E tests that need to run the engine in the background while performing
    other test operations.
    """

    def __init__(
        self,
        engine: LoopEngine,
        command_injector: Any | None = None,
    ):
        """Initialize E2E engine manager.

        Args:
            engine: Loop engine instance
            command_injector: Optional command injector (mock command source)
        """
        self.engine = engine
        self._command_injector = command_injector
        self._background_task: asyncio.Task[None] | None = None
        self._exceptions: list[Exception] = []
        self._stop_event = asyncio.Event()

    async def start_background(self) -> None:
        """Start engine in background task.

        The engine will run in the background, processing commands and steps
        until stop_background() is called.
        """
        if self._background_task is not None:
            raise RuntimeError("Engine already running in background")

        self.engine.start()
        self._stop_event.clear()
        self._background_task = asyncio.create_task(self._run_background())

    async def stop_background(self, timeout: float = 5.0) -> None:
        """Stop background engine task.

        Args:
            timeout: Maximum time to wait for graceful shutdown

        Raises:
            asyncio.TimeoutError: If shutdown takes longer than timeout
        """
        if self._background_task is None:
            return

        # Signal stop
        self._stop_event.set()
        self.engine.stop()

        # Wait for task to complete
        try:
            await asyncio.wait_for(self._background_task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Background task did not stop within {timeout}s, cancelling")
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        self._background_task = None

    async def run_for_duration(self, duration: float) -> None:
        """Run engine for a specific duration.

        Args:
            duration: Duration in seconds

        Raises:
            Exception: If any exception occurred during execution
        """
        await self.start_background()
        await asyncio.sleep(duration)
        await self.stop_background()

        # Check for exceptions
        if self._exceptions:
            raise self._exceptions[0]

    def inject_command(self, cmd_type: str, payload: dict[str, Any] | None = None) -> None:
        """Inject a command into the engine.

        Args:
            cmd_type: Command type (e.g., "play", "stop", "compile")
            payload: Command payload

        Raises:
            RuntimeError: If command injector not configured
        """
        if self._command_injector is None:
            raise RuntimeError("No command injector configured")

        self._command_injector.inject_command(cmd_type, payload or {})

    def get_exceptions(self) -> list[Exception]:
        """Get exceptions that occurred during background execution.

        Returns:
            List of exceptions
        """
        return self._exceptions.copy()

    def assert_no_exceptions(self) -> None:
        """Assert that no exceptions occurred during execution.

        Raises:
            AssertionError: If any exceptions occurred
        """
        if self._exceptions:
            exc_msgs = "\n".join(str(e) for e in self._exceptions)
            raise AssertionError(f"Background execution had {len(self._exceptions)} exceptions:\n{exc_msgs}")

    async def _run_background(self) -> None:
        """Background task that runs the engine loop.

        This simulates the main event loop processing, capturing any exceptions
        that occur during execution.
        """
        try:
            while not self._stop_event.is_set():
                # Process commands (similar to LoopEngine.run_async)
                try:
                    await self._command_consumer_step()
                except Exception as e:
                    logger.error(f"Error processing commands: {e}")
                    self._exceptions.append(e)

                # Small sleep to prevent busy loop
                await asyncio.sleep(0.001)

        except Exception as e:
            logger.error(f"Fatal error in background task: {e}")
            self._exceptions.append(e)

    async def _command_consumer_step(self) -> None:
        """Process one step of command consumption.

        This is a simplified version of the command processing loop
        for testing purposes.
        """
        if hasattr(self.engine, "_command_consumer"):
            await self.engine._command_consumer.process_commands()
