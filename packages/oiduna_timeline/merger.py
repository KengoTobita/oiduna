"""
Merge logic for combining multiple scheduled changes.

When multiple changes are scheduled for the same step,
they are merged into a single LoopSchedule.
"""

from __future__ import annotations

from oiduna_scheduler.scheduler_models import LoopSchedule
from .models import CuedChange


def merge_changes(changes: list[CuedChange]) -> LoopSchedule:
    """
    Merge multiple scheduled changes into a single batch.

    Design decisions:
    - All messages are combined in order (by sequence_number)
    - The LAST change's BPM is used (most recent intention)
    - The LAST change's pattern_length is used
    - destinations are auto-inferred from messages (property)

    Args:
        changes: List of changes to merge (should be pre-sorted by sequence_number).

    Returns:
        A single LoopSchedule containing all messages.

    Example:
        >>> change1 = CuedChange(...)  # 3 messages, BPM 120
        >>> change2 = CuedChange(...)  # 2 messages, BPM 140
        >>> merged = merge_changes([change1, change2])
        >>> len(merged.entries)  # 5 messages
        5
        >>> merged.bpm  # 140 (from change2)
        140.0
    """
    if not changes:
        # Return empty schedule
        return LoopSchedule(
            entries=tuple(),
            bpm=120.0,
            pattern_length=4.0,
        )

    # Collect all entries in order
    all_entries = []
    for change in changes:
        all_entries.extend(change.batch.entries)

    # Use the last change's BPM and pattern_length
    last_batch = changes[-1].batch

    return LoopSchedule(
        entries=tuple(all_entries),
        bpm=last_batch.bpm,
        pattern_length=last_batch.pattern_length,
        # destinations is auto-inferred (property)
    )
