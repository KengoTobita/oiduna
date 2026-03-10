"""Destination manager for session destinations."""

from typing import Optional
from oiduna_models import Session
from oiduna_models import DestinationConfig
from oiduna_session.validator import SessionValidator
from .base import BaseManager, SessionEventPublisher


class DestinationManager(BaseManager):
    """
    Manages destination configurations in the session.

    Provides add, remove, and get operations for destinations.
    """

    def __init__(
        self,
        session: Session,
        event_publisher: Optional[SessionEventPublisher] = None,
    ) -> None:
        """
        Initialize the DestinationManager.

        Args:
            session: The session object to manage
            event_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(session, event_publisher)

    def add(self, destination_config: DestinationConfig) -> None:
        """
        Add a destination to the session.

        Args:
            destination_config: Destination configuration

        Raises:
            ValueError: If destination ID already exists
        """
        if destination_config.id in self.session.destinations:
            raise ValueError(f"Destination {destination_config.id} already exists")

        self.session.destinations[destination_config.id] = destination_config

    def remove(self, destination_id: str) -> bool:
        """
        Remove a destination.

        Args:
            destination_id: ID of the destination to remove

        Returns:
            True if removed, False if not found

        Raises:
            ValueError: If destination is in use by tracks
        """
        if destination_id not in self.session.destinations:
            return False

        # Check if destination is in use
        validator = SessionValidator()
        using_tracks = validator.check_destination_in_use(
            self.session, destination_id
        )

        if using_tracks:
            raise ValueError(
                f"Cannot remove destination '{destination_id}': "
                f"in use by {len(using_tracks)} track(s): {using_tracks}. "
                f"Delete these tracks first, or assign them to a different destination."
            )

        del self.session.destinations[destination_id]

        # Emit event
        self._emit_event("destination_removed", {
            "destination_id": destination_id,
        })

        return True

    def get(self, destination_id: str) -> Optional[DestinationConfig]:
        """
        Get a destination by ID.

        Args:
            destination_id: ID of the destination

        Returns:
            DestinationConfig if found, None otherwise
        """
        return self.session.destinations.get(destination_id)
