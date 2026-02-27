"""Destination manager for session destinations."""

from typing import Optional
from oiduna_models import Session
from oiduna_destination.destination_models import DestinationConfig
from .base import BaseManager, EventSink


class DestinationManager(BaseManager):
    """
    Manages destination configurations in the session.

    Provides add, remove, and get operations for destinations.
    """

    def __init__(
        self,
        session: Session,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        """
        Initialize the DestinationManager.

        Args:
            session: The session object to manage
            event_sink: Optional event sink for emitting state changes
        """
        super().__init__(session, event_sink)

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

        Note: Does not check if tracks are using this destination.
        Caller should validate before removal if needed.

        Args:
            destination_id: ID of the destination to remove

        Returns:
            True if removed, False if not found
        """
        if destination_id in self.session.destinations:
            del self.session.destinations[destination_id]
            return True
        return False

    def get(self, destination_id: str) -> Optional[DestinationConfig]:
        """
        Get a destination by ID.

        Args:
            destination_id: ID of the destination

        Returns:
            DestinationConfig if found, None otherwise
        """
        return self.session.destinations.get(destination_id)
