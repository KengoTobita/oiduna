"""Tests for ClientService."""

import pytest
from typing import Any
from oiduna.domain.models import Session, ClientInfo, Track
from oiduna.domain.session.repositories import ClientRepository
from oiduna.domain.session.services import ClientService


class MockTrackRepository:
    """Mock TrackRepository for testing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, track_id: str) -> Track | None:
        return self.session.tracks.get(track_id)

    def list_all(self) -> list[Track]:
        return list(self.session.tracks.values())

    def delete(self, track_id: str) -> bool:
        if track_id in self.session.tracks:
            del self.session.tracks[track_id]
            return True
        return False


class MockPatternRepository:
    """Mock PatternRepository for testing."""

    pass


class TestClientService:
    """Test ClientService business logic operations."""

    def test_create_client(self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]) -> None:
        """Test creating a new client."""
        sink, events = mock_event_sink
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo, sink)

        client = service.create("c1", "Alice", "mars", {"version": "1.0"})

        assert client.client_id == "c1"
        assert client.client_name == "Alice"
        assert client.distribution == "mars"
        assert client.metadata == {"version": "1.0"}
        assert client.token  # Token should be generated

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "client_connected"
        assert events[0]["data"]["client_id"] == "c1"
        assert events[0]["data"]["client_name"] == "Alice"

    def test_create_duplicate_client_raises(self, session: Session) -> None:
        """Test that creating a duplicate client raises ValueError."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        service.create("c1", "Alice")

        with pytest.raises(ValueError, match="Client c1 already exists"):
            service.create("c1", "Bob")

    def test_get_client(self, session: Session) -> None:
        """Test getting a client."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        created = service.create("c1", "Alice")
        retrieved = service.get("c1")

        assert retrieved is not None
        assert retrieved.client_id == created.client_id
        assert retrieved.token == created.token

    def test_get_nonexistent_client(self, session: Session) -> None:
        """Test getting a nonexistent client returns None."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        assert service.get("nonexistent") is None

    def test_list_clients(self, session: Session) -> None:
        """Test listing all clients."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        service.create("c1", "Alice")
        service.create("c2", "Bob")

        clients = service.list_clients()
        assert len(clients) == 2
        assert set(c.client_id for c in clients) == {"c1", "c2"}

    def test_delete_client(self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]) -> None:
        """Test deleting a client."""
        sink, events = mock_event_sink
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo, sink)

        service.create("c1", "Alice")
        events.clear()  # Clear creation event

        result = service.delete("c1")

        assert result is True
        assert service.get("c1") is None

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "client_disconnected"
        assert events[0]["data"]["client_id"] == "c1"

    def test_delete_nonexistent_client(self, session: Session) -> None:
        """Test deleting a nonexistent client returns False."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        result = service.delete("nonexistent")
        assert result is False

    def test_delete_resources(self, session: Session) -> None:
        """Test deleting all resources owned by a client."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo)

        # Create client
        service.create("c1", "Alice")

        # Manually create tracks owned by this client (normally done by TrackService)
        from oiduna.domain.models import Pattern

        track1 = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0a1f": Pattern(
                    pattern_id="0a1f",
                    track_id="0001",
                    pattern_name="main",
                    client_id="c1"
                ),
                "0b2e": Pattern(
                    pattern_id="0b2e",
                    track_id="0001",
                    pattern_name="fill",
                    client_id="c1"
                ),
            },
        )
        track2 = Track(
            track_id="0002",
            track_name="snare",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0c3d": Pattern(
                    pattern_id="0c3d",
                    track_id="0002",
                    pattern_name="main",
                    client_id="c1"
                ),
            },
        )
        track3 = Track(
            track_id="0003",
            track_name="other",
            destination_id="sd",
            client_id="c2",  # Different client
        )

        session.tracks["0001"] = track1
        session.tracks["0002"] = track2
        session.tracks["0003"] = track3

        # Delete resources
        stats = service.delete_resources("c1")

        assert stats["tracks"] == 2
        assert stats["patterns"] == 3

        # Verify only c1's tracks were deleted
        assert "0001" not in session.tracks
        assert "0002" not in session.tracks
        assert "0003" in session.tracks

    def test_no_event_emission_when_no_publisher(self, session: Session) -> None:
        """Test that operations work without event publisher."""
        client_repo = ClientRepository(session)
        track_repo = MockTrackRepository(session)
        pattern_repo = MockPatternRepository()
        service = ClientService(client_repo, track_repo, pattern_repo, None)

        client = service.create("c1", "Alice")
        assert client.client_id == "c1"

        result = service.delete("c1")
        assert result is True
