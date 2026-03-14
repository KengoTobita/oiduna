"""Pattern service for pattern business logic."""

from typing import Optional
from oiduna.domain.models import Pattern, PatternEvent, IDGenerator
from oiduna.domain.session.types import SessionChangePublisher
from oiduna.domain.session.repositories.pattern_repository import PatternRepository
from oiduna.domain.session.repositories.track_repository import TrackRepository
from oiduna.domain.session.repositories.client_repository import ClientRepository
from .base import BaseService


class PatternService(BaseService):
    """
    Service for pattern business logic.

    Handles validation, ID generation, event emission, and complex operations.
    Supports both hierarchical API (track_id + pattern_id) and flat API (pattern_id only).
    Implements soft delete with archived flag.
    """

    def __init__(
        self,
        pattern_repo: PatternRepository,
        track_repo: TrackRepository,
        client_repo: ClientRepository,
        id_generator: IDGenerator,
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the PatternService.

        Args:
            pattern_repo: Repository for pattern data access
            track_repo: Repository for track validation
            client_repo: Repository for client validation
            id_generator: IDGenerator for creating unique pattern IDs
            change_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(change_publisher)
        self.pattern_repo = pattern_repo
        self.track_repo = track_repo
        self.client_repo = client_repo
        self.id_generator = id_generator

    def create(
        self,
        track_id: str,
        pattern_name: str,
        client_id: str,
        active: bool = True,
        events: Optional[list[PatternEvent]] = None,
    ) -> Pattern:
        """
        Create a new pattern in a track with server-generated ID.

        Args:
            track_id: Parent track ID (required)
            pattern_name: Human-readable name
            client_id: Owner client ID
            active: Whether pattern is active
            events: Initial events

        Returns:
            Created Pattern with server-generated pattern_id

        Raises:
            ValueError: If validation fails (track not found or client doesn't exist)
        """
        # Validate track exists
        track = self.track_repo.get(track_id)
        if track is None:
            raise ValueError(f"Track '{track_id}' not found")

        # Validate client exists
        if not self.client_repo.exists(client_id):
            raise ValueError(f"Client {client_id} does not exist")

        # Generate pattern ID
        pattern_id = self.id_generator.generate_pattern_id()

        # Build pattern
        pattern = Pattern(
            pattern_id=pattern_id,
            track_id=track_id,
            pattern_name=pattern_name,
            client_id=client_id,
            active=active,
            archived=False,
            events=events or [],
        )

        # Save to repository
        self.pattern_repo.save_to_track(track_id, pattern)

        # Emit event
        self._emit_change(
            "pattern_created",
            {
                "track_id": pattern.track_id,
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.pattern_name,
                "client_id": pattern.client_id,
                "active": pattern.active,
                "archived": pattern.archived,
                "event_count": len(pattern.events),
            },
        )

        return pattern

    def get(self, track_id: str, pattern_id: str) -> Optional[Pattern]:
        """
        Get pattern by track and pattern ID (hierarchical API).

        Args:
            track_id: Parent track ID
            pattern_id: Pattern ID

        Returns:
            Pattern if found, None otherwise
        """
        return self.pattern_repo.get(track_id, pattern_id)

    def get_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """
        Get pattern by pattern_id only (flat API).

        Searches across all tracks in the session.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern if found (even if archived=True), None otherwise
        """
        return self.pattern_repo.get_by_id(pattern_id)

    def list_patterns(
        self, track_id: str, include_archived: bool = False
    ) -> Optional[list[Pattern]]:
        """
        List patterns in a track (hierarchical API).

        Args:
            track_id: Parent track ID
            include_archived: Include patterns with archived=True

        Returns:
            List of patterns, or None if track not found
        """
        if not self.track_repo.exists(track_id):
            return None

        patterns = self.pattern_repo.list_in_track(track_id)

        if include_archived:
            return patterns
        else:
            return [p for p in patterns if not p.archived]

    def list_all(self, include_archived: bool = False) -> list[Pattern]:
        """
        List all patterns across all tracks (flat API).

        Args:
            include_archived: Include patterns with archived=True

        Returns:
            List of all patterns in the session
        """
        all_patterns = self.pattern_repo.list_all()

        if include_archived:
            return [pattern for _, pattern in all_patterns]
        else:
            return [pattern for _, pattern in all_patterns if not pattern.archived]

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
        pattern = self.pattern_repo.get_by_id(pattern_id)
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

        # Save updated pattern
        self.pattern_repo.save_to_track(pattern.track_id, pattern)

        # Emit event
        self._emit_change(
            "pattern_updated",
            {
                "pattern_id": pattern_id,
                "track_id": pattern.track_id,
                "client_id": pattern.client_id,
                "active": pattern.active,
                "archived": pattern.archived,
                "event_count": len(pattern.events),
            },
        )

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
        pattern = self.pattern_repo.get_by_id(pattern_id)
        if pattern is None:
            return False

        pattern.archived = True

        # Save updated pattern
        self.pattern_repo.save_to_track(pattern.track_id, pattern)

        # Emit event
        self._emit_change(
            "pattern_archived",
            {
                "pattern_id": pattern_id,
                "track_id": pattern.track_id,
                "client_id": pattern.client_id,
            },
        )

        return True

    def _move_pattern(self, pattern_id: str, new_track_id: str) -> None:
        """
        Move pattern to a different track (internal method).

        Args:
            pattern_id: Pattern to move
            new_track_id: Destination track ID

        Raises:
            ValueError: If pattern not found or new track doesn't exist
        """
        # 1. Find pattern and current track
        pattern = self.pattern_repo.get_by_id(pattern_id)
        if pattern is None:
            raise ValueError(f"Pattern {pattern_id} not found")

        old_track_id = pattern.track_id

        # 2. Validate new track exists
        if not self.track_repo.exists(new_track_id):
            raise ValueError(f"Track {new_track_id} not found")

        # 3. Remove from old track
        removed = self.pattern_repo.remove_from_track(old_track_id, pattern_id)
        if not removed:
            raise ValueError(f"Failed to remove pattern {pattern_id} from track {old_track_id}")

        # 4. Update track_id and add to new track
        pattern.track_id = new_track_id
        try:
            self.pattern_repo.save_to_track(new_track_id, pattern)
        except Exception as e:
            # Rollback: restore to old track
            pattern.track_id = old_track_id
            self.pattern_repo.save_to_track(old_track_id, pattern)
            raise ValueError(f"Failed to move pattern to track {new_track_id}: {e}")

        # Emit event
        self._emit_change(
            "pattern_moved",
            {
                "pattern_id": pattern_id,
                "from_track_id": old_track_id,
                "to_track_id": new_track_id,
                "client_id": pattern.client_id,
            },
        )
