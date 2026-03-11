"""Track manager for session track management."""

from typing import Any, Optional
from oiduna_models import Session, Track, IDGenerator
from .base import BaseManager, SessionChangePublisher
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
        event_publisher: Optional[SessionChangePublisher] = None,
        id_generator: Optional[IDGenerator] = None,
        destination_manager: Optional[DestinationManager] = None,
        client_manager: Optional[ClientManager] = None,
    ) -> None:
        """
        Initialize the TrackManager.

        Args:
            session: The session object to manage
            event_publisher: Optional event publisher for emitting state changes
            id_generator: Optional IDGenerator for creating unique track IDs
            destination_manager: Optional DestinationManager for validation
            client_manager: Optional ClientManager for validation
        """
        super().__init__(session, event_publisher)
        self.id_generator = id_generator or IDGenerator()
        self.destination_manager = destination_manager
        self.client_manager = client_manager

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
            ValueError: If validation fails
        """
        self._validate_track_creation(destination_id, client_id)
        track = self._build_track(track_name, destination_id, client_id, base_params)
        self._register_track(track)
        self._emit_track_created_event(track)
        return track

    def _validate_track_creation(self, destination_id: str, client_id: str) -> None:
        """Validate that destination and client exist."""
        if destination_id not in self.session.destinations:
            raise ValueError(f"Destination {destination_id} does not exist")
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} does not exist")

    def _build_track(
        self,
        track_name: str,
        destination_id: str,
        client_id: str,
        base_params: Optional[dict[str, Any]],
    ) -> Track:
        """Build a new Track object with generated ID."""
        track_id = self.id_generator.generate_track_id()
        return Track(
            track_id=track_id,
            track_name=track_name,
            destination_id=destination_id,
            client_id=client_id,
            base_params=base_params or {},
            patterns={},
        )

    def _register_track(self, track: Track) -> None:
        """Register track in session."""
        self.session.tracks[track.track_id] = track

    def _emit_track_created_event(self, track: Track) -> None:
        """Emit track_created event."""
        self._emit_change("track_created", {
            "track_id": track.track_id,
            "track_name": track.track_name,
            "client_id": track.client_id,
            "destination_id": track.destination_id,
        })

    def get(self, track_id: str) -> Optional[Track]:
        """
        Get track by ID.

        Args:
            track_id: ID of the track

        Returns:
            Track if found, None otherwise
        """
        return self.session.tracks.get(track_id)

    def list_tracks(self) -> list[Track]:
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
        self._emit_change("track_updated", {
            "track_id": track_id,
            "client_id": track.client_id,
            "updated_params": base_params,
        })

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
        if track_id in self.session.tracks:
            track = self.session.tracks[track_id]
            pattern_count = len(track.patterns)

            # Cascade delete (patterns are removed with track)
            del self.session.tracks[track_id]

            # Emit event
            self._emit_change("track_deleted", {
                "track_id": track_id,
                "client_id": track.client_id,
                "patterns_deleted": pattern_count,
            })

            return True
        return False
