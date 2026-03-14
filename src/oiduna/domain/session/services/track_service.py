"""Track service for track business logic."""

from typing import Any, Optional
from oiduna.domain.models import Track, IDGenerator
from oiduna.domain.session.types import SessionChangePublisher
from oiduna.domain.session.repositories.track_repository import TrackRepository
from oiduna.domain.session.repositories.destination_repository import (
    DestinationRepository,
)
from oiduna.domain.session.repositories.client_repository import ClientRepository
from .base import BaseService


class TrackService(BaseService):
    """
    Service for track business logic.

    Handles validation, ID generation, event emission, and cascade operations.
    Coordinates TrackRepository with DestinationRepository and ClientRepository.
    """

    def __init__(
        self,
        track_repo: TrackRepository,
        destination_repo: DestinationRepository,
        client_repo: ClientRepository,
        id_generator: IDGenerator,
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the TrackService.

        Args:
            track_repo: Repository for track data access
            destination_repo: Repository for destination validation
            client_repo: Repository for client validation
            id_generator: IDGenerator for creating unique track IDs
            change_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(change_publisher)
        self.track_repo = track_repo
        self.destination_repo = destination_repo
        self.client_repo = client_repo
        self.id_generator = id_generator

    def create(
        self,
        track_name: str,
        destination_id: str,
        client_id: str,
        base_params: Optional[dict[str, Any]] = None,
    ) -> Track:
        """
        Create a new track with server-generated ID.

        Args:
            track_name: Human-readable name
            destination_id: Target destination (must exist)
            client_id: Owner client ID (must exist)
            base_params: Base parameters for all events

        Returns:
            Created Track with server-generated track_id

        Raises:
            ValueError: If destination or client does not exist
        """
        # Validate destination and client exist
        if not self.destination_repo.exists(destination_id):
            raise ValueError(f"Destination {destination_id} does not exist")
        if not self.client_repo.exists(client_id):
            raise ValueError(f"Client {client_id} does not exist")

        # Generate track ID
        track_id = self.id_generator.generate_track_id()

        # Build track
        track = Track(
            track_id=track_id,
            track_name=track_name,
            destination_id=destination_id,
            client_id=client_id,
            base_params=base_params or {},
            patterns={},
        )

        # Save to repository
        self.track_repo.save(track)

        # Emit event
        self._emit_change(
            "track_created",
            {
                "track_id": track.track_id,
                "track_name": track.track_name,
                "client_id": track.client_id,
                "destination_id": track.destination_id,
            },
        )

        return track

    def get(self, track_id: str) -> Optional[Track]:
        """
        Get track by ID.

        Args:
            track_id: ID of the track

        Returns:
            Track if found, None otherwise
        """
        return self.track_repo.get(track_id)

    def list_tracks(self) -> list[Track]:
        """
        List all tracks.

        Returns:
            List of all Track objects
        """
        return self.track_repo.list_all()

    def update_base_params(
        self,
        track_id: str,
        base_params: dict[str, Any],
    ) -> Optional[Track]:
        """
        Update track base_params (shallow merge).

        Args:
            track_id: Track to update
            base_params: New parameters to merge

        Returns:
            Updated Track, or None if not found
        """
        track = self.track_repo.get(track_id)
        if track is None:
            return None

        # Shallow merge base_params
        track.base_params.update(base_params)

        # Save updated track
        self.track_repo.save(track)

        # Emit event
        self._emit_change(
            "track_updated",
            {
                "track_id": track_id,
                "client_id": track.client_id,
                "updated_params": base_params,
            },
        )

        return track

    def delete(self, track_id: str) -> bool:
        """
        Delete a track (including all its patterns).

        Cascade deletes all patterns in the track.
        Session-scoped IDs are automatically released when session ends.

        Args:
            track_id: ID of the track to delete

        Returns:
            True if deleted, False if not found
        """
        track = self.track_repo.get(track_id)
        if track is None:
            return False

        pattern_count = len(track.patterns)

        # Delete track (cascade deletes patterns)
        self.track_repo.delete(track_id)

        # Emit event
        self._emit_change(
            "track_deleted",
            {
                "track_id": track_id,
                "client_id": track.client_id,
                "patterns_deleted": pattern_count,
            },
        )

        return True
