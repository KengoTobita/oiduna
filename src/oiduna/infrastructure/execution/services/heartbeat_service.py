"""
Heartbeat Service

Manages periodic heartbeat messages and health monitoring tasks.

Martin Fowler patterns applied:
- Extract Class: Separated heartbeat logic from LoopEngine
- Single Responsibility Principle: Only handles periodic health monitoring
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Awaitable
from typing import Protocol

logger = logging.getLogger(__name__)


class HeartbeatPublisher(Protocol):
    """
    Protocol for heartbeat message publishing.

    Allows HeartbeatService to publish heartbeat without
    coupling to specific publisher implementations.
    """

    async def send(self, message_type: str, payload: dict) -> None:
        """
        Send a message.

        Args:
            message_type: Type of message (e.g., "heartbeat")
            payload: Message payload dictionary
        """
        ...


class HeartbeatService:
    """
    Manages periodic heartbeat messages and health monitoring.

    Sends periodic heartbeat messages to indicate the engine is alive.
    Supports registering custom tasks to run periodically alongside heartbeat.

    Single responsibility: Periodic health monitoring
    """

    DEFAULT_INTERVAL = 5.0  # seconds

    def __init__(
        self,
        publisher: HeartbeatPublisher | None = None,
        interval: float = DEFAULT_INTERVAL,
    ):
        """
        Initialize heartbeat service.

        Args:
            publisher: Optional publisher for heartbeat messages
            interval: Interval between heartbeats in seconds
        """
        self._publisher = publisher
        self._interval = interval
        self._tasks: list[Callable[[], Awaitable[None]]] = []

    def register_task(self, task: Callable[[], Awaitable[None]]) -> None:
        """
        Register a custom task to run with each heartbeat.

        Args:
            task: Async callable to execute periodically
        """
        self._tasks.append(task)

    async def send_heartbeat(self) -> None:
        """Send a single heartbeat message."""
        if self._publisher:
            await self._publisher.send("heartbeat", {
                "timestamp": time.perf_counter(),
            })

    async def run_loop(self, running_flag: Callable[[], bool]) -> None:
        """
        Run the heartbeat loop.

        Sends heartbeat messages and executes registered tasks
        at the configured interval while running_flag returns True.

        Args:
            running_flag: Callable returning True while loop should run
        """
        while running_flag():
            # Send heartbeat
            if self._publisher:
                await self.send_heartbeat()

            # Execute registered tasks
            for task in self._tasks:
                try:
                    await task()
                except Exception as e:
                    logger.error(f"Error in heartbeat task: {e}")

            # Wait for next interval
            await asyncio.sleep(self._interval)
