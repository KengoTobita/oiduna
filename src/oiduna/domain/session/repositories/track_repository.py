"""Track repository for session track data access."""

from typing import Optional
from oiduna.domain.models import Session, Track
from .base import BaseRepository


class TrackRepository(BaseRepository):
    """
    Repository for track CRUD operations.

    Provides direct access to session.tracks dictionary.
    No validation or event emission - pure data access only.
    """

    def save(self, track: Track) -> None:
        """
        Save a track to the session.

        Args:
            track: Track to save
        """
        self.session.tracks[track.track_id] = track

    def get(self, track_id: str) -> Optional[Track]:
        """
        Get track by ID.

        Args:
            track_id: ID of the track

        Returns:
            Track if found, None otherwise
        """
        return self.session.tracks.get(track_id)

    def exists(self, track_id: str) -> bool:
        """
        Check if track exists.

        Args:
            track_id: ID of the track

        Returns:
            True if track exists, False otherwise
        """
        return track_id in self.session.tracks

    def list_all(self) -> list[Track]:
        """
        List all tracks.

        Returns:
            List of all Track objects
        """
        return list(self.session.tracks.values())

    def delete(self, track_id: str) -> bool:
        """
        Delete a track.

        Note: This also deletes all patterns in the track (cascade delete)
        since patterns are stored in track.patterns dictionary.

        Args:
            track_id: ID of the track to delete

        Returns:
            True if deleted, False if not found
        """
        if track_id in self.session.tracks:
            del self.session.tracks[track_id]
            return True
        return False
