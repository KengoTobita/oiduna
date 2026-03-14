"""Pattern repository for session pattern data access."""

from typing import Optional
from oiduna.domain.models import Session, Pattern
from .base import BaseRepository


class PatternRepository(BaseRepository):
    """
    Repository for pattern CRUD operations.

    Patterns are stored within tracks, so this repository
    accesses session.tracks[track_id].patterns.
    No validation or event emission - pure data access only.
    """

    def save_to_track(self, track_id: str, pattern: Pattern) -> None:
        """
        Save a pattern to a track.

        Args:
            track_id: Parent track ID
            pattern: Pattern to save

        Raises:
            ValueError: If track not found
        """
        if track_id not in self.session.tracks:
            raise ValueError(f"Track {track_id} not found")
        self.session.tracks[track_id].patterns[pattern.pattern_id] = pattern

    def get(self, track_id: str, pattern_id: str) -> Optional[Pattern]:
        """
        Get pattern by track_id and pattern_id (hierarchical API).

        Args:
            track_id: Parent track ID
            pattern_id: Pattern ID

        Returns:
            Pattern if found, None otherwise
        """
        track = self.session.tracks.get(track_id)
        if not track:
            return None
        return track.patterns.get(pattern_id)

    def get_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """
        Get pattern by pattern_id only (flat API).

        Searches across all tracks in the session.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern if found, None otherwise
        """
        for track in self.session.tracks.values():
            if pattern_id in track.patterns:
                return track.patterns[pattern_id]
        return None

    def list_in_track(self, track_id: str) -> list[Pattern]:
        """
        List all patterns in a track.

        Args:
            track_id: Parent track ID

        Returns:
            List of patterns in the track, empty list if track not found
        """
        track = self.session.tracks.get(track_id)
        if not track:
            return []
        return list(track.patterns.values())

    def list_all(self) -> list[tuple[str, Pattern]]:
        """
        List all patterns across all tracks.

        Returns:
            List of (track_id, pattern) tuples
        """
        result = []
        for track_id, track in self.session.tracks.items():
            for pattern in track.patterns.values():
                result.append((track_id, pattern))
        return result

    def remove_from_track(self, track_id: str, pattern_id: str) -> bool:
        """
        Remove a pattern from a track.

        Args:
            track_id: Parent track ID
            pattern_id: Pattern ID to remove

        Returns:
            True if removed, False if not found
        """
        track = self.session.tracks.get(track_id)
        if not track or pattern_id not in track.patterns:
            return False
        del track.patterns[pattern_id]
        return True
