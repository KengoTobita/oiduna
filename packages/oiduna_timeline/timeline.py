"""
Timeline management for scheduled changes.

Maintains a map of global step → list of scheduled changes,
with automatic cleanup and validation.
"""

from __future__ import annotations
from typing import Optional
from collections import defaultdict

from .models import ScheduledChange


class ScheduledChangeTimeline:
    """
    Timeline manager for scheduled pattern changes.

    Design principles:
    - Global step-based scheduling (cumulative counter, persists across stop/start)
    - Multiple changes per step are allowed (will be merged)
    - Automatic cleanup of past changes (every CLEANUP_INTERVAL steps)
    - Hard limits to prevent abuse (MAX_CHANGES_PER_STEP, MAX_MESSAGES_PER_BATCH)

    Example:
        >>> timeline = ScheduledChangeTimeline()
        >>> success, msg = timeline.add_change(change, current_global_step=500)
        >>> changes = timeline.get_changes_at(1000)
        >>> timeline.cleanup_past(1000)
    """

    MAX_CHANGES_PER_STEP = 10  # Maximum concurrent changes at same step
    MAX_MESSAGES_PER_BATCH = 5000  # Maximum messages in single batch
    CLEANUP_INTERVAL = 1000  # Cleanup past changes every N steps

    def __init__(self) -> None:
        """Initialize empty timeline."""
        self._timeline: dict[int, list[ScheduledChange]] = defaultdict(list)
        self._id_to_step: dict[str, int] = {}  # Fast lookup: change_id → step
        self._sequence_counter: int = 0  # Global sequence counter for ordering

    def add_change(
        self,
        change: ScheduledChange,
        current_global_step: int,
    ) -> tuple[bool, str]:
        """
        Add a scheduled change to the timeline.

        Args:
            change: The change to schedule.
            current_global_step: Current global step (for validation).

        Returns:
            (success, message) tuple.
            - success: True if added, False if rejected.
            - message: Error message if rejected, empty string if success.

        Validation:
        - target_global_step must be > current_global_step
        - MAX_CHANGES_PER_STEP limit
        - MAX_MESSAGES_PER_BATCH limit
        - No duplicate change_id
        """
        # Validate future step
        if change.target_global_step <= current_global_step:
            return False, f"target_global_step ({change.target_global_step}) must be > current ({current_global_step})"

        # Check for duplicate change_id
        if change.change_id in self._id_to_step:
            return False, f"change_id {change.change_id} already exists"

        # Check MAX_CHANGES_PER_STEP
        existing_changes = self._timeline[change.target_global_step]
        if len(existing_changes) >= self.MAX_CHANGES_PER_STEP:
            return False, f"MAX_CHANGES_PER_STEP ({self.MAX_CHANGES_PER_STEP}) exceeded at step {change.target_global_step}"

        # Check MAX_MESSAGES_PER_BATCH
        if len(change.batch.messages) > self.MAX_MESSAGES_PER_BATCH:
            return False, f"MAX_MESSAGES_PER_BATCH ({self.MAX_MESSAGES_PER_BATCH}) exceeded: {len(change.batch.messages)} messages"

        # Assign sequence number for this step
        self._sequence_counter += 1
        # Create new change with sequence number (dataclass is frozen, so we need to reconstruct)
        from dataclasses import replace
        change = replace(change, sequence_number=self._sequence_counter)

        # Add to timeline
        self._timeline[change.target_global_step].append(change)
        self._id_to_step[change.change_id] = change.target_global_step

        return True, ""

    def get_changes_at(self, global_step: int) -> list[ScheduledChange]:
        """
        Get all scheduled changes for a specific step.

        Args:
            global_step: The step to query.

        Returns:
            List of changes sorted by sequence_number (empty if none).
        """
        changes = self._timeline.get(global_step, [])
        return sorted(changes, key=lambda c: c.sequence_number)

    def get_change_by_id(self, change_id: str) -> Optional[ScheduledChange]:
        """
        Get a specific change by its ID.

        Args:
            change_id: The change UUID to look up.

        Returns:
            The ScheduledChange, or None if not found.
        """
        step = self._id_to_step.get(change_id)
        if step is None:
            return None

        changes = self._timeline.get(step, [])
        for change in changes:
            if change.change_id == change_id:
                return change

        return None

    def cancel_change(self, change_id: str) -> tuple[bool, str]:
        """
        Cancel a scheduled change by ID.

        Args:
            change_id: The change UUID to cancel.

        Returns:
            (success, message) tuple.
        """
        step = self._id_to_step.get(change_id)
        if step is None:
            return False, f"change_id {change_id} not found"

        # Remove from timeline
        changes = self._timeline[step]
        self._timeline[step] = [c for c in changes if c.change_id != change_id]

        # Clean up empty step
        if not self._timeline[step]:
            del self._timeline[step]

        # Remove from index
        del self._id_to_step[change_id]

        return True, ""

    def update_change(
        self,
        change_id: str,
        new_change: ScheduledChange,
        current_global_step: int,
    ) -> tuple[bool, str]:
        """
        Update an existing scheduled change.

        Args:
            change_id: The change UUID to update.
            new_change: The new change data (must have same change_id).
            current_global_step: Current global step (for validation).

        Returns:
            (success, message) tuple.

        Note:
            This is implemented as cancel + add to maintain consistency.
        """
        if change_id != new_change.change_id:
            return False, "change_id mismatch"

        # Cancel old change
        success, msg = self.cancel_change(change_id)
        if not success:
            return False, msg

        # Add new change
        success, msg = self.add_change(new_change, current_global_step)
        if not success:
            # Rollback not possible (we already deleted), so just return error
            return False, f"update failed: {msg}"

        return True, ""

    def cleanup_past(self, current_global_step: int) -> int:
        """
        Remove all changes with target_global_step < current_global_step.

        Args:
            current_global_step: The current global step.

        Returns:
            Number of changes removed.
        """
        removed_count = 0
        steps_to_remove = [
            step for step in self._timeline.keys()
            if step < current_global_step
        ]

        for step in steps_to_remove:
            changes = self._timeline[step]
            removed_count += len(changes)

            # Remove from index
            for change in changes:
                if change.change_id in self._id_to_step:
                    del self._id_to_step[change.change_id]

            # Remove from timeline
            del self._timeline[step]

        return removed_count

    def get_all_upcoming(self, current_global_step: int, limit: int = 100) -> list[ScheduledChange]:
        """
        Get all upcoming changes (target_global_step >= current).

        Args:
            current_global_step: The current global step.
            limit: Maximum number of changes to return.

        Returns:
            List of changes sorted by (target_global_step, sequence_number).
        """
        all_changes: list[ScheduledChange] = []

        for step in sorted(self._timeline.keys()):
            if step < current_global_step:
                continue

            all_changes.extend(self._timeline[step])

            if len(all_changes) >= limit:
                break

        # Sort by step, then by sequence number
        all_changes.sort(key=lambda c: (c.target_global_step, c.sequence_number))

        return all_changes[:limit]

    def size(self) -> int:
        """Get total number of scheduled changes."""
        return len(self._id_to_step)
