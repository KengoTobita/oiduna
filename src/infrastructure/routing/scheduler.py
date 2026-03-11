"""
Loop scheduler - executes loop schedule step-by-step.

Routes schedule entries to destinations based on timing (step).
"""

from __future__ import annotations
from collections import defaultdict

from oiduna.domain.schedule.models import ScheduleEntry, LoopSchedule


class LoopScheduler:
    """
    Executes loop schedule step-by-step.

    Like a conductor following a musical score - reads the schedule
    and sends entries to destinations at the right step.

    Design:
    - Lightweight: just dict lookups by step
    - No domain knowledge: treats all entries equally
    - Thread-safe for reads (immutable entries)

    Usage:
        >>> scheduler = LoopScheduler()
        >>> schedule = LoopSchedule(...)
        >>> scheduler.load_schedule(schedule)
        >>> entries = scheduler.get_entries_at_step(0)
        >>> router.send_entries(entries)
    """

    def __init__(self) -> None:
        """Initialize empty scheduler."""
        # Map: step -> list of entries
        self._entries_by_step: dict[int, list[ScheduleEntry]] = defaultdict(list)
        self._bpm: float = 120.0
        self._pattern_length: float = 4.0

    def load_schedule(self, schedule: LoopSchedule) -> None:
        """
        Load a loop schedule into the scheduler.

        Args:
            schedule: Loop schedule from MARS

        This replaces any previously loaded schedule.
        """
        # Clear existing entries
        self._entries_by_step.clear()

        # Store metadata
        self._bpm = schedule.bpm
        self._pattern_length = schedule.pattern_length

        # Index entries by step
        for entry in schedule.entries:
            self._entries_by_step[entry.step].append(entry)

    def get_entries_at_step(self, step: int) -> list[ScheduleEntry]:
        """
        Get all entries scheduled for a given step.

        Args:
            step: Step number (0-255)

        Returns:
            List of entries (may be empty)

        Note: Returns list reference for performance.
              Caller should not modify the list.
        """
        return self._entries_by_step.get(step, [])

    def clear(self) -> None:
        """Clear the loaded schedule."""
        self._entries_by_step.clear()

    @property
    def bpm(self) -> float:
        """Current BPM."""
        return self._bpm

    @property
    def pattern_length(self) -> float:
        """Current pattern length in cycles."""
        return self._pattern_length

    @property
    def entry_count(self) -> int:
        """Total number of schedule entries."""
        return sum(len(entries) for entries in self._entries_by_step.values())

    @property
    def occupied_steps(self) -> set[int]:
        """Set of steps that have entries."""
        return set(self._entries_by_step.keys())
