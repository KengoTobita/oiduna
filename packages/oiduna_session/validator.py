"""
SessionValidator - business logic validation.

Validates operations that require cross-entity checks:
- Ownership verification
- Resource usage checks
- Constraint validation
"""

from typing import Optional
from oiduna_models import Session


class SessionValidator:
    """
    Business logic validation for session operations.

    Example:
        >>> validator = SessionValidator()
        >>> validator.check_track_ownership(session, "track_001", "client_001")
        True
    """

    @staticmethod
    def check_track_ownership(
        session: Session,
        track_id: str,
        client_id: str,
    ) -> bool:
        """
        Check if client owns a track.

        Args:
            session: Session state
            track_id: Track to check
            client_id: Client claiming ownership

        Returns:
            True if client owns track, False otherwise
        """
        track = session.tracks.get(track_id)
        if track is None:
            return False
        return track.client_id == client_id

    @staticmethod
    def check_pattern_ownership(
        session: Session,
        track_id: str,
        pattern_id: str,
        client_id: str,
    ) -> bool:
        """
        Check if client owns a pattern.

        Note: Pattern ownership is checked via pattern.client_id,
        not track.client_id (patterns can be owned by different clients).

        Args:
            session: Session state
            track_id: Parent track
            pattern_id: Pattern to check
            client_id: Client claiming ownership

        Returns:
            True if client owns pattern, False otherwise
        """
        track = session.tracks.get(track_id)
        if track is None:
            return False

        pattern = track.patterns.get(pattern_id)
        if pattern is None:
            return False

        return pattern.client_id == client_id

    @staticmethod
    def check_destination_in_use(
        session: Session,
        destination_id: str,
    ) -> list[str]:
        """
        Check which tracks are using a destination.

        Args:
            session: Session state
            destination_id: Destination to check

        Returns:
            List of track_ids using this destination
        """
        return [
            track_id
            for track_id, track in session.tracks.items()
            if track.destination_id == destination_id
        ]

    @staticmethod
    def get_client_resource_count(
        session: Session,
        client_id: str,
    ) -> dict[str, int]:
        """
        Count resources owned by a client.

        Args:
            session: Session state
            client_id: Client to check

        Returns:
            Dictionary with counts: {"tracks": N, "patterns": M}
        """
        tracks = [
            track
            for track in session.tracks.values()
            if track.client_id == client_id
        ]

        pattern_count = 0
        for track in tracks:
            pattern_count += sum(
                1
                for pattern in track.patterns.values()
                if pattern.client_id == client_id
            )

        return {
            "tracks": len(tracks),
            "patterns": pattern_count,
        }
