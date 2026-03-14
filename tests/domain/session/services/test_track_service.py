"""Tests for TrackService."""

import pytest
from typing import Any
from oiduna.domain.models import Session, IDGenerator, OscDestinationConfig
from oiduna.domain.session.repositories import (
    TrackRepository,
    DestinationRepository,
    ClientRepository,
)
from oiduna.domain.session.services import TrackService, ClientService


class TestTrackService:
    """Test TrackService business logic operations."""

    def test_create_track(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test creating a new track."""
        sink, events = mock_event_sink

        # Setup repositories
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Create prerequisites
        dest_repo.save(
            OscDestinationConfig(
                id="superdirt", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None, sink)
        client_service.create("c1", "Alice")
        events.clear()

        # Create track service
        service = TrackService(track_repo, dest_repo, client_repo, id_gen, sink)

        # Create track
        track = service.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="c1",
            base_params={"sound": "bd", "orbit": 0},
        )

        assert track.track_name == "kick"
        assert track.destination_id == "superdirt"
        assert track.client_id == "c1"
        assert track.base_params == {"sound": "bd", "orbit": 0}
        assert track.track_id  # Should be generated
        assert len(track.track_id) == 4  # 4-digit hex

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "track_created"
        assert events[0]["data"]["track_name"] == "kick"
        assert events[0]["data"]["client_id"] == "c1"

    def test_create_track_invalid_destination_raises(self, session: Session) -> None:
        """Test that creating track with invalid destination raises ValueError."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Create client only (no destination)
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)

        with pytest.raises(ValueError, match="Destination invalid_dest does not exist"):
            service.create("kick", "invalid_dest", "c1")

    def test_create_track_invalid_client_raises(self, session: Session) -> None:
        """Test that creating track with invalid client raises ValueError."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Create destination only (no client)
        dest_repo.save(
            OscDestinationConfig(
                id="superdirt", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)

        with pytest.raises(ValueError, match="Client invalid_client does not exist"):
            service.create("kick", "superdirt", "invalid_client")

    def test_get_track(self, session: Session) -> None:
        """Test getting a track."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)

        # Create track
        created = service.create("kick", "sd", "c1")

        # Get track
        retrieved = service.get(created.track_id)
        assert retrieved is not None
        assert retrieved.track_id == created.track_id
        assert retrieved.track_name == "kick"

    def test_get_nonexistent_track(self, session: Session) -> None:
        """Test getting a nonexistent track returns None."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        assert service.get("9999") is None

    def test_list_tracks(self, session: Session) -> None:
        """Test listing all tracks."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)

        # Create multiple tracks
        track1 = service.create("kick", "sd", "c1")
        track2 = service.create("snare", "sd", "c1")

        tracks = service.list_tracks()
        assert len(tracks) == 2
        assert set(t.track_id for t in tracks) == {track1.track_id, track2.track_id}

    def test_update_base_params(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating track base_params."""
        sink, events = mock_event_sink

        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen, sink)

        # Create track
        track = service.create("kick", "sd", "c1", {"sound": "bd"})
        events.clear()

        # Update base_params
        updated = service.update_base_params(track.track_id, {"orbit": 1, "gain": 0.8})

        assert updated is not None
        assert updated.base_params == {"sound": "bd", "orbit": 1, "gain": 0.8}

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "track_updated"
        assert events[0]["data"]["track_id"] == track.track_id
        assert events[0]["data"]["updated_params"] == {"orbit": 1, "gain": 0.8}

    def test_update_base_params_nonexistent_track(self, session: Session) -> None:
        """Test updating base_params for nonexistent track returns None."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        result = service.update_base_params("9999", {"sound": "bd"})
        assert result is None

    def test_delete_track(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test deleting a track."""
        sink, events = mock_event_sink

        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen, sink)

        # Create track
        track = service.create("kick", "sd", "c1")
        events.clear()

        # Delete track
        result = service.delete(track.track_id)

        assert result is True
        assert service.get(track.track_id) is None

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "track_deleted"
        assert events[0]["data"]["track_id"] == track.track_id
        assert events[0]["data"]["patterns_deleted"] == 0

    def test_delete_track_with_patterns(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test deleting a track with patterns reports pattern count."""
        from oiduna.domain.models import Track, Pattern

        sink, events = mock_event_sink

        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        service = TrackService(track_repo, dest_repo, client_repo, id_gen, sink)

        # Manually create track with patterns
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0a1f": Pattern(
                    pattern_id="0a1f",
                    track_id="0001",
                    pattern_name="main",
                    client_id="c1",
                ),
                "0b2e": Pattern(
                    pattern_id="0b2e",
                    track_id="0001",
                    pattern_name="fill",
                    client_id="c1",
                ),
            },
        )
        track_repo.save(track)

        # Delete track
        result = service.delete("0001")

        assert result is True

        # Verify event emission with pattern count
        assert len(events) == 1
        assert events[0]["type"] == "track_deleted"
        assert events[0]["data"]["patterns_deleted"] == 2

    def test_delete_nonexistent_track(self, session: Session) -> None:
        """Test deleting a nonexistent track returns False."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        service = TrackService(track_repo, dest_repo, client_repo, id_gen)
        result = service.delete("9999")
        assert result is False

    def test_no_event_emission_when_no_publisher(self, session: Session) -> None:
        """Test that operations work without event publisher."""
        track_repo = TrackRepository(session)
        dest_repo = DestinationRepository(session)
        client_repo = ClientRepository(session)
        id_gen = IDGenerator()

        # Setup
        dest_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client_service = ClientService(client_repo, track_repo, None)
        client_service.create("c1", "Alice")

        service = TrackService(track_repo, dest_repo, client_repo, id_gen, None)

        # Create track without publisher
        track = service.create("kick", "sd", "c1")
        assert track.track_id

        # Delete without publisher
        result = service.delete(track.track_id)
        assert result is True
