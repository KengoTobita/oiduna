"""Track manager for session track management."""

from typing import Any, Optional
from oiduna_models import Session, Track
from .base import BaseManager, EventSink
from .client_manager import ClientManager
from .destination_manager import DestinationManager


class TrackManager(BaseManager):
    """
    Manages track CRUD operations in the session.

    Provides creation, retrieval, listing, updating, and deletion of tracks.
    Validates that destinations and clients exist before creating tracks.
    """

    def __init__(
        self,
        session: Session,
        event_sink: Optional[EventSink] = None,
        destination_manager: Optional[DestinationManager] = None,
        client_manager: Optional[ClientManager] = None,
    ) -> None:
        """
        Initialize the TrackManager.

        Args:
            session: The session object to manage
            event_sink: Optional event sink for emitting state changes
            destination_manager: Optional DestinationManager for validation
            client_manager: Optional ClientManager for validation
        """
        super().__init__(session, event_sink)
        self.destination_manager = destination_manager
        self.client_manager = client_manager

    def create(
        self,
        track_id: str,
        track_name: str,
        destination_id: str,
        client_id: str,
        base_params: Optional[dict[str, Any]] = None,
    ) -> Track:
        """
        Create a new track.

        Args:
            track_id: Unique track identifier
            track_name: Human-readable name
            destination_id: Target destination (must exist)
            client_id: Owner client ID (must exist)
            base_params: Base parameters for all events

        Returns:
            Created Track

        Raises:
            ValueError: If validation fails
        """
        # Validate destination exists
        if destination_id not in self.session.destinations:
            raise ValueError(f"Destination {destination_id} does not exist")

        # Validate client exists
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} does not exist")

        # Validate track_id unique
        if track_id in self.session.tracks:
            raise ValueError(f"Track {track_id} already exists")

        track = Track(
            track_id=track_id,
            track_name=track_name,
            destination_id=destination_id,
            client_id=client_id,
            base_params=base_params or {},
            patterns={},
        )

        self.session.tracks[track_id] = track

        # Emit event
        self._emit_event("track_created", {
            "track_id": track_id,
            "track_name": track_name,
            "client_id": client_id,
            "destination_id": destination_id,
        })

        return track

    def get(self, track_id: str) -> Optional[Track]:
        """
        Get track by ID.

        Args:
            track_id: ID of the track

        Returns:
            Track if found, None otherwise
        """
        return self.session.tracks.get(track_id)

    def list(self) -> list[Track]:
        """
        List all tracks.

        Returns:
            List of all Track objects
        """
        return list(self.session.tracks.values())

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
        track = self.session.tracks.get(track_id)
        if track is None:
            return None

        track.base_params.update(base_params)

        # Emit event
        self._emit_event("track_updated", {
            "track_id": track_id,
            "client_id": track.client_id,
            "updated_params": base_params,
        })

        return track

    def delete(self, track_id: str) -> bool:
        """
        Delete a track (including all its patterns).

        Args:
            track_id: ID of the track to delete

        Returns:
            True if deleted, False if not found
        """
        if track_id in self.session.tracks:
            track = self.session.tracks[track_id]
            del self.session.tracks[track_id]

            # Emit event
            self._emit_event("track_deleted", {
                "track_id": track_id,
                "client_id": track.client_id,
            })

            return True
        return False
