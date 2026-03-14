"""Tests for PatternService."""

import pytest
from typing import Any
from oiduna.domain.models import Session, IDGenerator, OscDestinationConfig, PatternEvent
from oiduna.domain.session.repositories import (
    PatternRepository,
    TrackRepository,
    DestinationRepository,
    ClientRepository,
)
from oiduna.domain.session.services import PatternService, TrackService, ClientService


class TestPatternService:
    """Test PatternService business logic operations."""

    def test_create_pattern(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test creating a new pattern."""
        sink, events = mock_event_sink
        id_gen = IDGenerator()

        # Setup repositories and services
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Create prerequisites
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo, sink)
        client_service.create("c1", "Alice")
        events.clear()

        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen, sink)
        track = track_service.create("kick", "sd", "c1")
        events.clear()

        # Create pattern service
        service = PatternService(pattern_repo, track_repo, client_repo, id_gen, sink)

        # Create pattern
        pattern = service.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="c1",
            active=True,
        )

        assert pattern.pattern_name == "main"
        assert pattern.track_id == track.track_id
        assert pattern.client_id == "c1"
        assert pattern.active is True
        assert pattern.archived is False
        assert pattern.pattern_id  # Should be generated
        assert len(pattern.pattern_id) == 4  # 4-digit hex

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "pattern_created"
        assert events[0]["data"]["pattern_name"] == "main"
        assert events[0]["data"]["active"] is True
        assert events[0]["data"]["archived"] is False

    def test_create_pattern_invalid_track_raises(self, session: Session) -> None:
        """Test that creating pattern with invalid track raises ValueError."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        client_repo = ClientRepository(session)

        # Create client only (no track)
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        with pytest.raises(ValueError, match="Track '9999' not found"):
            service.create("9999", "main", "c1")

    def test_create_pattern_invalid_client_raises(self, session: Session) -> None:
        """Test that creating pattern with invalid client raises ValueError."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Create track (no client)
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        with pytest.raises(ValueError, match="Client invalid_client does not exist"):
            service.create(track.track_id, "main", "invalid_client")

    def test_get_pattern_hierarchical(self, session: Session) -> None:
        """Test getting pattern by track_id and pattern_id."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create pattern
        created = service.create(track.track_id, "main", "c1")

        # Get pattern
        retrieved = service.get(track.track_id, created.pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_id == created.pattern_id
        assert retrieved.pattern_name == "main"

    def test_get_by_id_flat(self, session: Session) -> None:
        """Test getting pattern by pattern_id only (flat API)."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create pattern
        created = service.create(track.track_id, "main", "c1")

        # Get by ID only
        retrieved = service.get_by_id(created.pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_id == created.pattern_id

    def test_list_patterns_in_track(self, session: Session) -> None:
        """Test listing patterns in a track."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create multiple patterns
        p1 = service.create(track.track_id, "main", "c1")
        p2 = service.create(track.track_id, "fill", "c1")

        # List patterns
        patterns = service.list_patterns(track.track_id)
        assert patterns is not None
        assert len(patterns) == 2
        assert set(p.pattern_id for p in patterns) == {p1.pattern_id, p2.pattern_id}

    def test_list_patterns_filter_archived(self, session: Session) -> None:
        """Test listing patterns filters out archived patterns by default."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create patterns and archive one
        p1 = service.create(track.track_id, "main", "c1")
        p2 = service.create(track.track_id, "fill", "c1")
        service.delete(p2.pattern_id)  # Soft delete (archives)

        # List without archived
        patterns = service.list_patterns(track.track_id, include_archived=False)
        assert patterns is not None
        assert len(patterns) == 1
        assert patterns[0].pattern_id == p1.pattern_id

        # List with archived
        patterns_all = service.list_patterns(track.track_id, include_archived=True)
        assert patterns_all is not None
        assert len(patterns_all) == 2

    def test_list_all_patterns(self, session: Session) -> None:
        """Test listing all patterns across all tracks."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track1 = track_service.create("kick", "sd", "c1")
        track2 = track_service.create("snare", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create patterns in different tracks
        p1 = service.create(track1.track_id, "main", "c1")
        p2 = service.create(track2.track_id, "fill", "c1")

        # List all
        all_patterns = service.list_all()
        assert len(all_patterns) == 2
        assert set(p.pattern_id for p in all_patterns) == {p1.pattern_id, p2.pattern_id}

    def test_update_pattern_active(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating pattern active state."""
        sink, events = mock_event_sink
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen, sink)

        # Create pattern
        pattern = service.create(track.track_id, "main", "c1", active=True)
        events.clear()

        # Update active state
        updated = service.update(pattern.pattern_id, active=False)
        assert updated is not None
        assert updated.active is False

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "pattern_updated"
        assert events[0]["data"]["active"] is False

    def test_delete_pattern_soft_delete(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test soft deleting a pattern (sets archived=True)."""
        sink, events = mock_event_sink
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen, sink)

        # Create pattern
        pattern = service.create(track.track_id, "main", "c1")
        events.clear()

        # Delete (soft delete)
        result = service.delete(pattern.pattern_id)
        assert result is True

        # Pattern still exists but is archived
        retrieved = service.get_by_id(pattern.pattern_id)
        assert retrieved is not None
        assert retrieved.archived is True

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "pattern_archived"

    def test_update_pattern_restore_from_archive(self, session: Session) -> None:
        """Test restoring an archived pattern."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create and delete pattern
        pattern = service.create(track.track_id, "main", "c1")
        service.delete(pattern.pattern_id)

        # Restore
        restored = service.update(pattern.pattern_id, archived=False)
        assert restored is not None
        assert restored.archived is False

    def test_move_pattern_to_different_track(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test moving a pattern to a different track."""
        sink, events = mock_event_sink
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track1 = track_service.create("kick", "sd", "c1")
        track2 = track_service.create("snare", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen, sink)

        # Create pattern in track1
        pattern = service.create(track1.track_id, "main", "c1")
        events.clear()

        # Move to track2
        updated = service.update(pattern.pattern_id, track_id=track2.track_id)
        assert updated is not None
        assert updated.track_id == track2.track_id

        # Verify pattern moved
        assert pattern_repo.get(track1.track_id, pattern.pattern_id) is None
        assert pattern_repo.get(track2.track_id, pattern.pattern_id) is not None

        # Verify events (pattern_moved + pattern_updated)
        event_types = [e["type"] for e in events]
        assert "pattern_moved" in event_types
        assert "pattern_updated" in event_types

    def test_move_pattern_to_invalid_track_raises(self, session: Session) -> None:
        """Test that moving pattern to invalid track raises ValueError."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen)

        # Create pattern
        pattern = service.create(track.track_id, "main", "c1")

        # Try to move to invalid track
        with pytest.raises(ValueError, match="Track 9999 not found"):
            service.update(pattern.pattern_id, track_id="9999")

    def test_no_event_emission_when_no_publisher(self, session: Session) -> None:
        """Test that operations work without event publisher."""
        id_gen = IDGenerator()
        pattern_repo = PatternRepository(session)
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, pattern_repo)
        client_service.create("c1", "Alice")
        track_service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        track = track_service.create("kick", "sd", "c1")

        service = PatternService(pattern_repo, track_repo, client_repo, id_gen, None)

        # Create pattern without publisher
        pattern = service.create(track.track_id, "main", "c1")
        assert pattern.pattern_id

        # Delete without publisher
        result = service.delete(pattern.pattern_id)
        assert result is True
