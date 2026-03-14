"""Timeline repository for timeline data access."""

from typing import Optional
from oiduna.domain.models import Session
from oiduna.domain.timeline import CuedChange, CuedChangeTimeline
from .base import BaseRepository


class TimelineRepository(BaseRepository):
    """
    Repository for timeline data access.

    Timeline is managed via CuedChangeTimeline, not directly in Session.
    This repository delegates to CuedChangeTimeline for operations.
    """

    def __init__(self, session: Session | None = None) -> None:
        """
        Initialize the TimelineRepository.

        Args:
            session: Session object (not used, kept for consistency)
        """
        if session:
            super().__init__(session)
        else:
            # Create a dummy session for compatibility
            super().__init__(Session())
        self.timeline = CuedChangeTimeline()

    def add_change(
        self, change: CuedChange, current_global_step: int
    ) -> tuple[bool, str]:
        """
        Add a cued change to the timeline.

        Args:
            change: The change to schedule
            current_global_step: Current global step (for validation)

        Returns:
            (success, message) tuple
        """
        return self.timeline.add_change(change, current_global_step)

    def get_change_by_id(self, change_id: str) -> Optional[CuedChange]:
        """
        Get a cued change by ID.

        Args:
            change_id: UUID of the change

        Returns:
            CuedChange if found, None otherwise
        """
        return self.timeline.get_change_by_id(change_id)

    def cancel_change(self, change_id: str) -> tuple[bool, str]:
        """
        Cancel a cued change.

        Args:
            change_id: UUID of the change to cancel

        Returns:
            (success, message) tuple
        """
        return self.timeline.cancel_change(change_id)

    def update_change(
        self, change_id: str, new_change: CuedChange, current_global_step: int
    ) -> tuple[bool, str]:
        """
        Update an existing scheduled change.

        Args:
            change_id: The change UUID to update
            new_change: The new change data (must have same change_id)
            current_global_step: Current global step (for validation)

        Returns:
            (success, message) tuple
        """
        return self.timeline.update_change(change_id, new_change, current_global_step)

    def get_all_upcoming(
        self, current_global_step: int, limit: int = 100
    ) -> list[CuedChange]:
        """
        Get all upcoming cued changes.

        Args:
            current_global_step: Current global step
            limit: Maximum number to return

        Returns:
            List of upcoming changes, sorted by (target_step, sequence_number)
        """
        return self.timeline.get_all_upcoming(current_global_step, limit)
