"""Pattern manager for session pattern management."""

from __future__ import annotations
from typing import Optional
from oiduna_models import Session, Pattern, Event
from .base import BaseManager, EventSink
from .track_manager import TrackManager
from .client_manager import ClientManager


class PatternManager(BaseManager):
    """
    Manages pattern CRUD operations in the session.

    Provides creation, retrieval, listing, updating, and deletion of patterns.
    Validates that tracks and clients exist before creating patterns.
    """

    def __init__(
        self,
        session: Session,
        event_sink: Optional[EventSink] = None,
        track_manager: Optional[TrackManager] = None,
        client_manager: Optional[ClientManager] = None,
    ) -> None:
        """
        Initialize the PatternManager.

        Args:
            session: The session object to manage
            event_sink: Optional event sink for emitting state changes
            track_manager: Optional TrackManager for track access
            client_manager: Optional ClientManager for validation
        """
        super().__init__(session, event_sink)
        self.track_manager = track_manager
        self.client_manager = client_manager

    def create(
        self,
        track_id: str,
        pattern_id: str,
        pattern_name: str,
        client_id: str,
        active: bool = True,
        events: Optional[list[Event]] = None,
    ) -> Optional[Pattern]:
        """
        Create a new pattern in a track.

        Args:
            track_id: Parent track ID
            pattern_id: Unique pattern identifier
            pattern_name: Human-readable name
            client_id: Owner client ID
            active: Whether pattern is active
            events: Initial events

        Returns:
            Created Pattern, or None if track not found

        Raises:
            ValueError: If validation fails
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return None

        # Validate client exists
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} does not exist")

        # Validate pattern_id unique within track
        if pattern_id in track.patterns:
            raise ValueError(
                f"Pattern {pattern_id} already exists in track {track_id}"
            )

        pattern = Pattern(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            client_id=client_id,
            active=active,
            events=events or [],
        )

        track.patterns[pattern_id] = pattern

        # Emit event
        self._emit_event("pattern_created", {
            "track_id": track_id,
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "client_id": client_id,
            "active": active,
            "event_count": len(pattern.events),
        })

        return pattern

    def get(
        self,
        track_id: str,
        pattern_id: str,
    ) -> Optional[Pattern]:
        """
        Get pattern by track and pattern ID.

        Args:
            track_id: Parent track ID
            pattern_id: Pattern ID

        Returns:
            Pattern if found, None otherwise
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return None
        return track.patterns.get(pattern_id)

    def list(self, track_id: str) -> Optional[list[Pattern]]:
        """
        List all patterns in a track.

        Args:
            track_id: Parent track ID

        Returns:
            List of patterns, or None if track not found
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return None
        return list(track.patterns.values())

    def update(
        self,
        track_id: str,
        pattern_id: str,
        active: Optional[bool] = None,
        events: Optional[list[Event]] = None,
    ) -> Optional[Pattern]:
        """
        Update pattern fields.

        Args:
            track_id: Parent track ID
            pattern_id: Pattern to update
            active: New active state (optional)
            events: New events list (optional)

        Returns:
            Updated Pattern, or None if not found
        """
        pattern = self.get(track_id, pattern_id)
        if pattern is None:
            return None

        if active is not None:
            pattern.active = active
        if events is not None:
            pattern.events = events

        # Emit event
        self._emit_event("pattern_updated", {
            "track_id": track_id,
            "pattern_id": pattern_id,
            "client_id": pattern.client_id,
            "active": pattern.active,
            "event_count": len(pattern.events),
        })

        return pattern

    def delete(
        self,
        track_id: str,
        pattern_id: str,
    ) -> bool:
        """
        Delete a pattern.

        Args:
            track_id: Parent track ID
            pattern_id: Pattern ID to delete

        Returns:
            True if deleted, False if not found
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return False

        if pattern_id in track.patterns:
            pattern = track.patterns[pattern_id]
            del track.patterns[pattern_id]

            # Emit event
            self._emit_event("pattern_deleted", {
                "track_id": track_id,
                "pattern_id": pattern_id,
                "client_id": pattern.client_id,
            })

            return True
        return False
