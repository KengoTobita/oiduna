"""Tests for DestinationService."""

import pytest
from typing import Any
from oiduna.domain.models import Session, OscDestinationConfig, MidiDestinationConfig, Track
from oiduna.domain.session.repositories import DestinationRepository, TrackRepository
from oiduna.domain.session.services import DestinationService


class TestDestinationService:
    """Test DestinationService business logic operations."""

    def test_add_destination(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test adding a new destination."""
        sink, events = mock_event_sink
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo, sink)

        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )

        service.add(dest)

        # Verify it was saved
        retrieved = service.get("superdirt")
        assert retrieved is not None
        assert retrieved.id == "superdirt"

    def test_add_duplicate_destination_raises(self, session: Session) -> None:
        """Test that adding a duplicate destination raises ValueError."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )

        service.add(dest)

        with pytest.raises(ValueError, match="Destination superdirt already exists"):
            service.add(dest)

    def test_get_destination(self, session: Session) -> None:
        """Test getting a destination."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )
        service.add(dest)

        retrieved = service.get("superdirt")
        assert retrieved is not None
        assert retrieved.id == "superdirt"

    def test_get_nonexistent_destination(self, session: Session) -> None:
        """Test getting a nonexistent destination returns None."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        assert service.get("nonexistent") is None

    def test_remove_destination(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test removing a destination."""
        sink, events = mock_event_sink
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo, sink)

        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )
        service.add(dest)

        result = service.remove("superdirt")

        assert result is True
        assert service.get("superdirt") is None

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "destination_removed"
        assert events[0]["data"]["destination_id"] == "superdirt"

    def test_remove_nonexistent_destination(self, session: Session) -> None:
        """Test removing a nonexistent destination returns False."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        result = service.remove("nonexistent")
        assert result is False

    def test_remove_destination_in_use_raises(self, session: Session) -> None:
        """Test that removing a destination in use raises ValueError."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        # Add destination
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )
        service.add(dest)

        # Create a track that uses this destination
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="superdirt",
            client_id="c1",
        )
        track_repo.save(track)

        # Try to remove the destination
        with pytest.raises(
            ValueError, match="Cannot remove destination 'superdirt': in use by 1 track"
        ):
            service.remove("superdirt")

    def test_remove_destination_multiple_tracks_in_use(self, session: Session) -> None:
        """Test error message when multiple tracks use the destination."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo)

        # Add destination
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )
        service.add(dest)

        # Create multiple tracks
        track1 = Track(
            track_id="0001",
            track_name="kick",
            destination_id="superdirt",
            client_id="c1",
        )
        track2 = Track(
            track_id="0002",
            track_name="snare",
            destination_id="superdirt",
            client_id="c1",
        )
        track_repo.save(track1)
        track_repo.save(track2)

        # Try to remove the destination
        with pytest.raises(
            ValueError, match="Cannot remove destination 'superdirt': in use by 2 track"
        ):
            service.remove("superdirt")

    def test_no_event_emission_when_no_publisher(self, session: Session) -> None:
        """Test that operations work without event publisher."""
        dest_repo = DestinationRepository(session)
        track_repo = TrackRepository(session)
        service = DestinationService(dest_repo, track_repo, None)

        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )
        service.add(dest)

        result = service.remove("superdirt")
        assert result is True
