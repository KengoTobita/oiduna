"""Pattern manager for session pattern management."""

from __future__ import annotations
from typing import Optional
from oiduna.domain.models import Session, Track, Pattern, PatternEvent, IDGenerator
from .base import BaseManager, SessionChangePublisher
from .track_manager import TrackManager
from .client_manager import ClientManager


class PatternManager(BaseManager):
    """
    Manages pattern CRUD operations in the session.

    Provides creation, retrieval, listing, updating, and deletion of patterns.
    Supports both flat API (by pattern_id) and hierarchical API (by track_id + pattern_id).
    Implements soft delete with `archived` flag.
    """

    def __init__(
        self,
        session: Session,
        event_publisher: Optional[SessionChangePublisher] = None,
        id_generator: Optional[IDGenerator] = None,
        track_manager: Optional[TrackManager] = None,
        client_manager: Optional[ClientManager] = None,
    ) -> None:
        """
        Initialize the PatternManager.

        Args:
            session: The session object to manage
            event_publisher: Optional event publisher for emitting state changes
            id_generator: Optional IDGenerator for creating unique pattern IDs
            track_manager: Optional TrackManager for track access
            client_manager: Optional ClientManager for validation
        """
        super().__init__(session, event_publisher)
        self.id_generator = id_generator or IDGenerator()
        self.track_manager = track_manager
        self.client_manager = client_manager

    def create(
        self,
        track_id: str,
        pattern_name: str,
        client_id: str,
        active: bool = True,
        events: Optional[list[PatternEvent]] = None,
    ) -> Optional[Pattern]:
        """
        Create a new pattern in a track with server-generated ID.

        Args:
            track_id: Parent track ID (required)
            pattern_name: Human-readable name
            client_id: Owner client ID
            active: Whether pattern is active
            events: Initial events

        Returns:
            Created Pattern with server-generated pattern_id, or None if track not found

        Raises:
            ValueError: If validation fails
        """
        track = self._validate_pattern_creation(track_id, client_id)
        if track is None:
            return None

        pattern = self._build_pattern(track_id, pattern_name, client_id, active, events)
        self._register_pattern(track, pattern)
        self._emit_pattern_created_event(pattern)
        return pattern

    def _validate_pattern_creation(self, track_id: str, client_id: str) -> Optional[Track]:
        """Validate that track and client exist."""
        track = self.session.tracks.get(track_id)
        if track is None:
            return None
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} does not exist")
        return track

    def _build_pattern(
        self,
        track_id: str,
        pattern_name: str,
        client_id: str,
        active: bool,
        events: Optional[list[PatternEvent]],
    ) -> Pattern:
        """Build a new Pattern object with generated ID."""
        pattern_id = self.id_generator.generate_pattern_id()
        return Pattern(
            pattern_id=pattern_id,
            track_id=track_id,
            pattern_name=pattern_name,
            client_id=client_id,
            active=active,
            archived=False,
            events=events or [],
        )

    def _register_pattern(self, track: Track, pattern: Pattern) -> None:
        """Register pattern in track."""
        track.patterns[pattern.pattern_id] = pattern

    def _emit_pattern_created_event(self, pattern: Pattern) -> None:
        """Emit pattern_created event."""
        self._emit_change("pattern_created", {
            "track_id": pattern.track_id,
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.pattern_name,
            "client_id": pattern.client_id,
            "active": pattern.active,
            "archived": pattern.archived,
            "event_count": len(pattern.events),
        })

    def get(
        self,
        track_id: str,
        pattern_id: str,
    ) -> Optional[Pattern]:
        """
        Get pattern by track and pattern ID (hierarchical API).

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

    def get_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """
        Get pattern by pattern_id only (flat API).

        Searches across all tracks in the session.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern if found (even if archived=True), None otherwise
        """
        for track in self.session.tracks.values():
            if pattern_id in track.patterns:
                return track.patterns[pattern_id]
        return None

    def list_patterns(self, track_id: str, include_archived: bool = False) -> Optional[list[Pattern]]:
        """
        List patterns in a track (hierarchical API).

        Args:
            track_id: Parent track ID
            include_archived: Include patterns with archived=True

        Returns:
            List of patterns, or None if track not found
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return None

        patterns = []
        for pattern in track.patterns.values():
            if include_archived or not pattern.archived:
                patterns.append(pattern)
        return patterns

    def list_all(self, include_archived: bool = False) -> list[Pattern]:
        """
        List all patterns across all tracks (flat API).

        Args:
            include_archived: Include patterns with archived=True

        Returns:
            List of all patterns in the session
        """
        all_patterns = []
        for track in self.session.tracks.values():
            for pattern in track.patterns.values():
                if include_archived or not pattern.archived:
                    all_patterns.append(pattern)
        return all_patterns

    def update(
        self,
        pattern_id: str,
        track_id: Optional[str] = None,
        active: Optional[bool] = None,
        archived: Optional[bool] = None,
        events: Optional[list[PatternEvent]] = None,
    ) -> Optional[Pattern]:
        """
        Update pattern fields (flat API).

        Can update pattern even if archived=True (for restoration).
        Can move pattern to different track via track_id parameter.

        Args:
            pattern_id: Pattern to update
            track_id: New track ID (moves pattern if different from current)
            active: New active state
            archived: New archived state (set to False to restore)
            events: New events list

        Returns:
            Updated Pattern, or None if not found

        Raises:
            ValueError: If new track_id doesn't exist
        """
        pattern = self.get_by_id(pattern_id)
        if pattern is None:
            return None

        # Track移動
        if track_id and track_id != pattern.track_id:
            self._move_pattern(pattern_id, track_id)

        # フィールド更新
        if active is not None:
            pattern.active = active
        if archived is not None:
            pattern.archived = archived
        if events is not None:
            pattern.events = events

        # Emit event
        self._emit_change("pattern_updated", {
            "pattern_id": pattern_id,
            "track_id": pattern.track_id,
            "client_id": pattern.client_id,
            "active": pattern.active,
            "archived": pattern.archived,
            "event_count": len(pattern.events),
        })

        return pattern

    def delete(self, pattern_id: str) -> bool:
        """
        Soft delete a pattern (set archived=True).

        Does not physically remove the pattern - just marks it as archived.
        Pattern can be restored via update(pattern_id, archived=False).

        Args:
            pattern_id: Pattern ID to delete

        Returns:
            True if marked archived, False if not found
        """
        pattern = self.get_by_id(pattern_id)
        if pattern is None:
            return False

        pattern.archived = True

        # Emit event
        self._emit_change("pattern_archived", {
            "pattern_id": pattern_id,
            "track_id": pattern.track_id,
            "client_id": pattern.client_id,
        })

        return True

    def _move_pattern(self, pattern_id: str, new_track_id: str) -> None:
        """
        Move pattern to a different track.

        Args:
            pattern_id: Pattern to move
            new_track_id: Destination track ID

        Raises:
            ValueError: If pattern not found or new track doesn't exist
        """
        # 1. Find and remove from current track
        old_pattern = None
        old_track_id = None
        for track_id, track in self.session.tracks.items():
            if pattern_id in track.patterns:
                old_pattern = track.patterns.pop(pattern_id)
                old_track_id = track_id
                break

        if not old_pattern:
            raise ValueError(f"Pattern {pattern_id} not found")

        # 2. Add to new track
        new_track = self.session.tracks.get(new_track_id)
        if not new_track:
            # Rollback: restore to old track
            if old_track_id:
                self.session.tracks[old_track_id].patterns[pattern_id] = old_pattern
            raise ValueError(f"Track {new_track_id} not found")

        # 3. Update track_id and add to new track
        old_pattern.track_id = new_track_id
        new_track.patterns[pattern_id] = old_pattern

        # Emit event
        self._emit_change("pattern_moved", {
            "pattern_id": pattern_id,
            "from_track_id": old_track_id,
            "to_track_id": new_track_id,
            "client_id": old_pattern.client_id,
        })
