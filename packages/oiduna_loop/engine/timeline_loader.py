"""
Timeline loader for applying scheduled changes in the Loop Engine.

Implements the Single Responsibility Principle by separating
timeline application logic from the main LoopEngine class.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oiduna_timeline import CuedChangeTimeline
    from oiduna_scheduler.scheduler import LoopScheduler


class TimelineLoader:
    """
    Static utility for applying timeline changes in the Loop Engine.

    Design:
    - Single responsibility: timeline application only
    - No state management (static methods)
    - Automatic cleanup on every application
    - Performance optimized (merge + single load_messages call)
    """

    @staticmethod
    def apply_changes_at_step(
        global_step: int,
        timeline: CuedChangeTimeline,
        message_scheduler: LoopScheduler,
    ) -> bool:
        """
        Apply all scheduled changes at the given global step.

        This method:
        1. Gets all changes scheduled for this step
        2. Merges them into a single batch (if multiple)
        3. Loads the merged batch into the LoopScheduler
        4. Performs automatic cleanup of past changes

        Args:
            global_step: The current global step.
            timeline: The timeline containing scheduled changes.
            message_scheduler: The scheduler to load messages into.

        Returns:
            True if changes were applied, False if no changes at this step.

        Performance:
        - O(1) lookup for changes at step
        - Single load_messages() call regardless of change count
        - Automatic cleanup every invocation (lightweight)
        """
        from oiduna_timeline import merge_changes

        # Get changes for this step
        changes = timeline.get_changes_at(global_step)

        # No changes - just cleanup and return
        if not changes:
            timeline.cleanup_past(global_step)
            return False

        # Merge changes into single batch
        merged_batch = merge_changes(changes)

        # Load into scheduler (single call for performance)
        message_scheduler.load_messages(merged_batch)

        # Immediate cleanup: Remove applied changes and all past changes
        # This ensures no history accumulates in memory
        for change in changes:
            timeline.cancel_change(change.change_id)
        timeline.cleanup_past(global_step)

        return True
