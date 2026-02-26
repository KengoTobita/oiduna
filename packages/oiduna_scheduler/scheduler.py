"""
Message scheduler - routes messages by timing (step).

Replaces StepProcessor's timing logic with generic message scheduling.
"""

from __future__ import annotations
from typing import Dict, List
from collections import defaultdict

from scheduler_models import ScheduledMessage, ScheduledMessageBatch


class MessageScheduler:
    """
    Schedule messages by step for playback.

    Design:
    - Lightweight: just dict lookups by step
    - No domain knowledge: treats all messages equally
    - Thread-safe for reads (immutable messages)

    Usage:
        >>> scheduler = MessageScheduler()
        >>> batch = ScheduledMessageBatch(...)
        >>> scheduler.load_messages(batch)
        >>> messages = scheduler.get_messages_at_step(0)
        >>> router.send_messages(messages)
    """

    def __init__(self) -> None:
        """Initialize empty scheduler."""
        # Map: step -> list of messages
        self._messages_by_step: Dict[int, List[ScheduledMessage]] = defaultdict(list)
        self._bpm: float = 120.0
        self._pattern_length: float = 4.0

    def load_messages(self, batch: ScheduledMessageBatch) -> None:
        """
        Load a batch of messages into the scheduler.

        Args:
            batch: Batch of scheduled messages from MARS

        This replaces any previously loaded messages.
        """
        # Clear existing messages
        self._messages_by_step.clear()

        # Store metadata
        self._bpm = batch.bpm
        self._pattern_length = batch.pattern_length

        # Index messages by step
        for msg in batch.messages:
            self._messages_by_step[msg.step].append(msg)

    def get_messages_at_step(self, step: int) -> List[ScheduledMessage]:
        """
        Get all messages scheduled for a given step.

        Args:
            step: Step number (0-255)

        Returns:
            List of messages (may be empty)

        Note: Returns list reference for performance.
              Caller should not modify the list.
        """
        return self._messages_by_step.get(step, [])

    def clear(self) -> None:
        """Clear all scheduled messages."""
        self._messages_by_step.clear()

    @property
    def bpm(self) -> float:
        """Current BPM."""
        return self._bpm

    @property
    def pattern_length(self) -> float:
        """Current pattern length in cycles."""
        return self._pattern_length

    @property
    def message_count(self) -> int:
        """Total number of scheduled messages."""
        return sum(len(msgs) for msgs in self._messages_by_step.values())

    @property
    def occupied_steps(self) -> set[int]:
        """Set of steps that have messages."""
        return set(self._messages_by_step.keys())
