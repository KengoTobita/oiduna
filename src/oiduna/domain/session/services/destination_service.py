"""Destination service for destination business logic."""

from typing import Optional
from oiduna.domain.models import DestinationConfig
from oiduna.domain.session.types import SessionChangePublisher
from oiduna.domain.session.repositories.destination_repository import (
    DestinationRepository,
)
from oiduna.domain.session.repositories.track_repository import TrackRepository
from .base import BaseService


class DestinationService(BaseService):
    """
    Service for destination business logic.

    Handles validation, event emission, and cascade checks.
    """

    def __init__(
        self,
        destination_repo: DestinationRepository,
        track_repo: TrackRepository,
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the DestinationService.

        Args:
            destination_repo: Repository for destination data access
            track_repo: Repository for track data access (for dependency checks)
            change_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(change_publisher)
        self.destination_repo = destination_repo
        self.track_repo = track_repo

    def add(self, destination_config: DestinationConfig) -> None:
        """
        Add a destination to the session.

        Args:
            destination_config: Destination configuration

        Raises:
            ValueError: If destination ID already exists
        """
        if self.destination_repo.exists(destination_config.id):
            raise ValueError(f"Destination {destination_config.id} already exists")

        self.destination_repo.save(destination_config)

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
        if not self.destination_repo.exists(destination_id):
            return False

        # Check if destination is in use by any tracks
        using_tracks = [
            track.track_id
            for track in self.track_repo.list_all()
            if track.destination_id == destination_id
        ]

        if using_tracks:
            raise ValueError(
                f"Cannot remove destination '{destination_id}': "
                f"in use by {len(using_tracks)} track(s): {using_tracks}. "
                f"Delete these tracks first, or assign them to a different destination."
            )

        self.destination_repo.delete(destination_id)

        # Emit event
        self._emit_change("destination_removed", {"destination_id": destination_id})

        return True

    def get(self, destination_id: str) -> Optional[DestinationConfig]:
        """
        Get a destination by ID.

        Args:
            destination_id: ID of the destination

        Returns:
            DestinationConfig if found, None otherwise
        """
        return self.destination_repo.get(destination_id)
