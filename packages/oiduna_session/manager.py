"""
SessionManager for in-memory session state management.

This is the single source of truth for all Oiduna state.
It provides CRUD operations for:
- Clients
- Tracks
- Patterns
- Environment
"""

from typing import Any, Optional, Protocol
from oiduna_models import (
    Session,
    Track,
    Pattern,
    Event,
    ClientInfo,
    Environment,
    IDGenerator,
)
from oiduna_destination.destination_models import DestinationConfig


class EventSink(Protocol):
    """Protocol for event sinks (e.g., InProcessStateSink)."""

    def _push(self, event: dict[str, Any]) -> None:
        """Push an event to the sink."""
        ...


class SessionManager:
    """
    In-memory session state management (singleton).

    Provides CRUD operations for all session entities while maintaining
    referential integrity and ownership rules.

    Optionally emits SSE events for state changes if event_sink is provided.

    Example:
        >>> manager = SessionManager()
        >>> client = manager.create_client("client_001", "Alice")
        >>> track = manager.create_track(
        ...     track_id="track_001",
        ...     track_name="kick",
        ...     destination_id="superdirt",
        ...     client_id="client_001"
        ... )
        >>> pattern = manager.create_pattern(
        ...     track_id="track_001",
        ...     pattern_id="pattern_001",
        ...     pattern_name="main",
        ...     client_id="client_001"
        ... )
    """

    def __init__(self, event_sink: Optional[EventSink] = None):
        self.session = Session()
        self.id_gen = IDGenerator()
        self.event_sink = event_sink

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an SSE event if event_sink is configured."""
        if self.event_sink:
            try:
                self.event_sink._push({"type": event_type, "data": data})
            except Exception:
                # Don't fail operations if event emission fails
                pass

    # =========================================================================
    # Client CRUD
    # =========================================================================

    def create_client(
        self,
        client_id: str,
        client_name: str,
        distribution: str = "unknown",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ClientInfo:
        """
        Create a new client.

        Args:
            client_id: Unique client identifier
            client_name: Human-readable name
            distribution: Client type (mars, web, mobile, etc.)
            metadata: Additional metadata

        Returns:
            Created ClientInfo with generated token

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.session.clients:
            raise ValueError(f"Client {client_id} already exists")

        client = ClientInfo(
            client_id=client_id,
            client_name=client_name,
            token=ClientInfo.generate_token(),
            distribution=distribution,
            metadata=metadata or {},
        )

        self.session.clients[client_id] = client

        # Emit event
        self._emit_event("client_connected", {
            "client_id": client_id,
            "client_name": client_name,
            "distribution": distribution,
        })

        return client

    def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """Get client by ID."""
        return self.session.clients.get(client_id)

    def list_clients(self) -> list[ClientInfo]:
        """List all clients."""
        return list(self.session.clients.values())

    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client.

        Note: Does not cascade delete tracks/patterns owned by this client.
        Call delete_client_resources() first if cascading delete is needed.

        Returns:
            True if deleted, False if not found
        """
        if client_id in self.session.clients:
            del self.session.clients[client_id]

            # Emit event
            self._emit_event("client_disconnected", {
                "client_id": client_id,
            })

            return True
        return False

    def delete_client_resources(self, client_id: str) -> dict[str, int]:
        """
        Delete all resources owned by a client (tracks and their patterns).

        Returns:
            Dictionary with counts: {"tracks": N, "patterns": M}
        """
        tracks_deleted = 0
        patterns_deleted = 0

        # Find and delete tracks owned by this client
        track_ids_to_delete = [
            track_id
            for track_id, track in self.session.tracks.items()
            if track.client_id == client_id
        ]

        for track_id in track_ids_to_delete:
            track = self.session.tracks[track_id]
            patterns_deleted += len(track.patterns)
            del self.session.tracks[track_id]
            tracks_deleted += 1

        return {"tracks": tracks_deleted, "patterns": patterns_deleted}

    # =========================================================================
    # Track CRUD
    # =========================================================================

    def create_track(
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

    def get_track(self, track_id: str) -> Optional[Track]:
        """Get track by ID."""
        return self.session.tracks.get(track_id)

    def list_tracks(self) -> list[Track]:
        """List all tracks."""
        return list(self.session.tracks.values())

    def update_track_base_params(
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

    def delete_track(self, track_id: str) -> bool:
        """
        Delete a track (including all its patterns).

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

    # =========================================================================
    # Pattern CRUD
    # =========================================================================

    def create_pattern(
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

    def get_pattern(
        self,
        track_id: str,
        pattern_id: str,
    ) -> Optional[Pattern]:
        """Get pattern by track and pattern ID."""
        track = self.session.tracks.get(track_id)
        if track is None:
            return None
        return track.patterns.get(pattern_id)

    def list_patterns(self, track_id: str) -> Optional[list[Pattern]]:
        """
        List all patterns in a track.

        Returns:
            List of patterns, or None if track not found
        """
        track = self.session.tracks.get(track_id)
        if track is None:
            return None
        return list(track.patterns.values())

    def update_pattern(
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
        pattern = self.get_pattern(track_id, pattern_id)
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

    def delete_pattern(
        self,
        track_id: str,
        pattern_id: str,
    ) -> bool:
        """
        Delete a pattern.

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

    # =========================================================================
    # Environment
    # =========================================================================

    def update_environment(
        self,
        bpm: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Environment:
        """
        Update environment settings.

        Args:
            bpm: New BPM (optional)
            metadata: Metadata to merge (optional)

        Returns:
            Updated Environment
        """
        updated_fields = {}
        if bpm is not None:
            self.session.environment.bpm = bpm
            updated_fields["bpm"] = bpm
        if metadata is not None:
            self.session.environment.metadata.update(metadata)
            updated_fields["metadata"] = metadata

        # Emit event
        if updated_fields:
            self._emit_event("environment_updated", updated_fields)

        return self.session.environment

    # =========================================================================
    # Destinations (Admin-only operations)
    # =========================================================================

    def add_destination(self, destination: DestinationConfig) -> None:
        """
        Add a destination to the session.

        Args:
            destination: Destination configuration

        Raises:
            ValueError: If destination ID already exists
        """
        if destination.id in self.session.destinations:
            raise ValueError(f"Destination {destination.id} already exists")

        self.session.destinations[destination.id] = destination

    def remove_destination(self, destination_id: str) -> bool:
        """
        Remove a destination.

        Note: Does not check if tracks are using this destination.
        Call validator.check_destination_in_use() first if needed.

        Returns:
            True if removed, False if not found
        """
        if destination_id in self.session.destinations:
            del self.session.destinations[destination_id]
            return True
        return False

    # =========================================================================
    # Session operations
    # =========================================================================

    def reset(self) -> None:
        """Reset session to empty state (admin operation)."""
        self.session = Session()
        self.id_gen.reset()

    def get_state(self) -> Session:
        """Get complete session state."""
        return self.session
