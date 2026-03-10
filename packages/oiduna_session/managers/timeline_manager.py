"""
Timeline manager for scheduled pattern changes.

Handles scheduling, cancellation, and permission checks for timeline changes.
"""

from __future__ import annotations
from typing import Optional

from oiduna_timeline import ScheduledChange, ScheduledChangeTimeline
from oiduna_scheduler.scheduler_models import ScheduledMessageBatch
from .base import BaseManager

# Timeline lookahead configuration (from LoopEngine ADR-0020)
TIMELINE_MIN_LOOKAHEAD = 8  # 2 beat minimum (~2sec @ BPM 120)


class TimelineManager(BaseManager):
    """
    Manages timeline-based scheduling of pattern changes.

    Responsibilities:
    - CRUD operations on scheduled changes (with permission checks)
    - SSE event emission for timeline updates
    - Integration with SessionContainer

    Example:
        >>> manager = TimelineManager(session, event_sink)
        >>> success, msg, change_id = manager.schedule_change(
        ...     batch, 1000, "alice_001", "Alice", "Kick pattern", 500
        ... )
    """

    def __init__(
        self,
        session,
        event_sink=None,
        timeline: Optional[ScheduledChangeTimeline] = None,
    ):
        """
        Initialize TimelineManager.

        Args:
            session: Session instance (for consistency with other managers)
            event_sink: Optional event sink for SSE notifications
            timeline: Optional timeline instance (creates new if None)
        """
        super().__init__(session, event_sink)
        self.timeline = timeline or ScheduledChangeTimeline()

    def schedule_change(
        self,
        batch: ScheduledMessageBatch,
        target_global_step: int,
        client_id: str,
        client_name: str,
        description: str,
        current_global_step: int,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Schedule a pattern change for a future global step.

        Args:
            batch: The message batch to apply
            target_global_step: When to apply (must be > current + MIN_LOOKAHEAD)
            client_id: Client who scheduled this
            client_name: Human-readable client name
            description: User-provided description
            current_global_step: Current engine global step

        Returns:
            (success, message, change_id) tuple
            - success: True if scheduled
            - message: Error message if failed
            - change_id: UUID of scheduled change (None if failed)
        """
        # Validate minimum lookahead (ADR-0020)
        min_target = current_global_step + TIMELINE_MIN_LOOKAHEAD
        if target_global_step < min_target:
            return (
                False,
                f"予約は最低{TIMELINE_MIN_LOOKAHEAD}ステップ先（global_step {min_target}以降）に設定してください。"
                f"現在: {current_global_step}, 指定: {target_global_step}",
                None,
            )

        # Create scheduled change
        change = ScheduledChange(
            target_global_step=target_global_step,
            batch=batch,
            client_id=client_id,
            client_name=client_name,
            description=description,
        )

        # Add to timeline
        success, msg = self.timeline.add_change(change, current_global_step)

        if not success:
            return False, msg, None

        # Emit SSE event
        self._emit_event("change_scheduled", change.to_dict())

        return True, "", change.change_id

    def cancel_change(
        self,
        change_id: str,
        client_id: str,
    ) -> tuple[bool, str]:
        """
        Cancel a scheduled change (with permission check).

        Args:
            change_id: UUID of change to cancel
            client_id: Client requesting cancellation

        Returns:
            (success, message) tuple
        """
        # Get the change to check ownership
        change = self.timeline.get_change_by_id(change_id)
        if change is None:
            return False, f"Change {change_id} not found"

        # Permission check: only owner can cancel
        if change.client_id != client_id:
            return False, f"Permission denied: change {change_id} owned by {change.client_id}"

        # Cancel the change
        success, msg = self.timeline.cancel_change(change_id)

        if success:
            # Emit SSE event
            self._emit_event("change_cancelled", {
                "change_id": change_id,
                "client_id": client_id,
            })

        return success, msg

    def update_change(
        self,
        change_id: str,
        new_batch: ScheduledMessageBatch,
        new_target_global_step: int,
        new_description: str,
        client_id: str,
        current_global_step: int,
    ) -> tuple[bool, str]:
        """
        Update a scheduled change (with permission check).

        Args:
            change_id: UUID of change to update
            new_batch: New message batch
            new_target_global_step: New target step
            new_description: New description
            client_id: Client requesting update
            current_global_step: Current engine global step

        Returns:
            (success, message) tuple
        """
        # Get the old change to check ownership
        old_change = self.timeline.get_change_by_id(change_id)
        if old_change is None:
            return False, f"Change {change_id} not found"

        # Permission check: only owner can update
        if old_change.client_id != client_id:
            return False, f"Permission denied: change {change_id} owned by {old_change.client_id}"

        # Create new change with same ID and client info
        new_change = ScheduledChange(
            change_id=change_id,
            target_global_step=new_target_global_step,
            batch=new_batch,
            client_id=old_change.client_id,  # Keep original owner
            client_name=old_change.client_name,
            description=new_description,
            scheduled_at=old_change.scheduled_at,  # Keep original timestamp
        )

        # Update in timeline
        success, msg = self.timeline.update_change(
            change_id,
            new_change,
            current_global_step,
        )

        if success:
            # Emit SSE event
            self._emit_event("change_updated", new_change.to_dict())

        return success, msg

    def get_change(self, change_id: str) -> Optional[ScheduledChange]:
        """
        Get a scheduled change by ID.

        Args:
            change_id: UUID of the change

        Returns:
            ScheduledChange or None if not found
        """
        return self.timeline.get_change_by_id(change_id)

    def get_all_upcoming(
        self,
        current_global_step: int,
        limit: int = 100,
    ) -> list[ScheduledChange]:
        """
        Get all upcoming changes.

        Args:
            current_global_step: Current engine global step
            limit: Maximum number to return

        Returns:
            List of upcoming changes, sorted by (target_step, sequence_number)
        """
        return self.timeline.get_all_upcoming(current_global_step, limit)
