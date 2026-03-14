"""
Step Executor Service

Handles execution of a single loop step including:
- Timeline lookahead application
- Message retrieval and filtering
- Extension hook processing
- Message routing
- Periodic state updates

Martin Fowler patterns applied:
- Extract Class: Separated step execution logic from LoopEngine
- Single Responsibility Principle: Only handles step execution pipeline
- Protocol-based Dependency Injection: Loose coupling to dependencies
"""

from __future__ import annotations

import logging
from typing import Protocol, Any
from collections.abc import Callable

logger = logging.getLogger(__name__)


class MessageScheduler(Protocol):
    """Protocol for message scheduling (LoopScheduler)."""

    @property
    def message_count(self) -> int:
        """Total number of scheduled messages."""
        ...

    def get_messages_at_step(self, step: int) -> list[Any]:
        """Get messages scheduled at a specific step."""
        ...


class MessageRouter(Protocol):
    """Protocol for message routing (DestinationRouter)."""

    def send_messages(self, messages: list[Any]) -> None:
        """Send messages to configured destinations."""
        ...


class StatePublisher(Protocol):
    """Protocol for state publishing (StateProducer)."""

    async def send_position(
        self, position: dict[str, Any], bpm: float, transport: str
    ) -> None:
        """Publish current position state."""
        ...

    async def send_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """Publish track information."""
        ...

    async def send_error(self, error_code: str, message: str) -> None:
        """Send error notification."""
        ...


class MessageFilter(Protocol):
    """Protocol for message filtering and state access (RuntimeState)."""

    def filter_messages(self, messages: list[Any]) -> list[Any]:
        """Filter messages based on mute/solo state."""
        ...

    @property
    def position(self) -> Any:
        """Current playback position."""
        ...

    @property
    def playback_state(self) -> Any:
        """Current playback state."""
        ...


class TimelineProvider(Protocol):
    """Protocol for timeline access."""

    @property
    def timeline(self) -> Any:
        """Current timeline with cued changes."""
        ...

    @property
    def global_step(self) -> int:
        """Global step counter (cumulative)."""
        ...


class StepExecutor:
    """
    Executes a single step of the loop engine.

    Responsibilities:
    - Apply timeline changes with lookahead
    - Retrieve and filter messages
    - Apply extension hooks
    - Send messages to router
    - Publish periodic updates

    Martin Fowler Extract Class pattern applied.
    Phase 2 pattern (DriftCorrector) consistency maintained.
    """

    # Timeline lookahead configuration (ADR-0020)
    TIMELINE_LOOKAHEAD_STEPS = 32  # 2 bar lookahead
    TIMELINE_MIN_LOOKAHEAD = 8  # 2 beat minimum

    def __init__(
        self,
        message_scheduler: MessageScheduler,
        message_router: MessageRouter,
        state_publisher: StatePublisher,
        message_filter: MessageFilter,
        timeline_provider: TimelineProvider,
        session_loaded_check: Callable[[], bool],
        get_tracks_info: Callable[[], list[dict[str, Any]]],
        position_update_interval: str = "beat",
        before_send_hooks: list[Callable[[list[Any], float, int], list[Any]]] | None = None,
    ):
        """
        Initialize step executor.

        Args:
            message_scheduler: Scheduler for retrieving messages
            message_router: Router for sending messages
            state_publisher: Publisher for state updates
            message_filter: Filter for mute/solo processing
            timeline_provider: Provider for timeline and global_step access
            session_loaded_check: Function to check if session is loaded
            get_tracks_info: Function to get track information
            position_update_interval: "beat" or "bar" for position updates
            before_send_hooks: Optional list of message transformation hooks
        """
        self._message_scheduler = message_scheduler
        self._message_router = message_router
        self._state_publisher = state_publisher
        self._message_filter = message_filter
        self._timeline_provider = timeline_provider
        self._session_loaded_check = session_loaded_check
        self._get_tracks_info = get_tracks_info
        self._position_update_interval = position_update_interval
        self._before_send_hooks = before_send_hooks or []

    async def execute_step(self, current_step: int, current_bpm: float) -> None:
        """
        Execute the complete step processing pipeline.

        Pipeline stages:
        1. Apply timeline changes with lookahead
        2. Get and filter messages for current step
        3. Apply extension hooks
        4. Send messages to router
        5. Publish periodic updates

        Args:
            current_step: Current step number (0-15 within bar)
            current_bpm: Current BPM for hook processing
        """
        try:
            # Stage 1: Apply timeline changes with lookahead (ADR-0020)
            await self._apply_timeline_lookahead()

            # Stage 2: Get and filter messages
            messages = self._get_filtered_messages(current_step)

            if messages:
                # Stage 3: Apply extension hooks
                messages = self._apply_hooks(messages, current_step, current_bpm)
                # Stage 4: Send to destination router
                self._send_messages(messages, current_step)

            # Stage 5: Publish periodic updates
            await self._publish_periodic_updates(current_step, current_bpm)

        except Exception as e:
            logger.error(f"Step processing error: {e}")
            await self._state_publisher.send_error("STEP_ERROR", str(e))

    async def _apply_timeline_lookahead(self) -> None:
        """
        Apply timeline changes with lookahead.

        Load messages N steps ahead to avoid blocking critical path (ADR-0020).
        """
        timeline = self._timeline_provider.timeline
        if timeline:
            future_global_step = (
                self._timeline_provider.global_step + self.TIMELINE_LOOKAHEAD_STEPS
            )
            # Import here to avoid circular dependency
            from ..timeline_loader import TimelineLoader

            TimelineLoader.apply_changes_at_step(
                future_global_step,
                timeline,
                self._message_scheduler,
            )

    def _get_filtered_messages(self, current_step: int) -> list[Any]:
        """
        Get and filter messages for current step.

        Args:
            current_step: Current step number

        Returns:
            Filtered list of messages for current step
        """
        # Check if session is loaded and messages exist
        if (
            not self._session_loaded_check()
            or self._message_scheduler.message_count == 0
        ):
            return []

        # Get scheduled messages
        scheduled_messages = self._message_scheduler.get_messages_at_step(current_step)
        if not scheduled_messages:
            return []

        # Filter by mute/solo state
        return self._message_filter.filter_messages(scheduled_messages)

    def _apply_hooks(
        self, messages: list[Any], current_step: int, current_bpm: float
    ) -> list[Any]:
        """
        Apply extension hooks to messages.

        Args:
            messages: List of scheduled messages
            current_step: Current step number
            current_bpm: Current BPM

        Returns:
            Modified messages after applying all hooks
        """
        for hook in self._before_send_hooks:
            messages = hook(messages, current_bpm, current_step)
        return messages

    def _send_messages(self, messages: list[Any], current_step: int) -> None:
        """
        Send messages to destination router.

        Args:
            messages: List of scheduled messages to send
            current_step: Current step number (for logging)
        """
        if messages:
            logger.debug(
                f"Step {current_step}: sending {len(messages)} "
                "scheduled messages via destination router"
            )
            self._message_router.send_messages(messages)

    async def _publish_periodic_updates(
        self, current_step: int, current_bpm: float
    ) -> None:
        """
        Publish periodic updates (position, tracks info).

        Args:
            current_step: Current step number
            current_bpm: Current BPM
        """
        # Publish position based on configured interval
        # "beat": every 4 steps (quarter note)
        # "bar": every 16 steps (full bar)
        interval = 16 if self._position_update_interval == "bar" else 4
        if current_step % interval == 0:
            # Get position from RuntimeState
            position_dict = self._message_filter.position.to_dict()
            transport_state = self._message_filter.playback_state.value
            await self._state_publisher.send_position(
                position_dict,
                bpm=current_bpm,
                transport=transport_state,
            )

        # Send tracks info at bar boundaries for Monitor page sync
        if current_step % 16 == 0:
            await self._state_publisher.send_tracks(self._get_tracks_info())
