"""
Unit tests for SessionManager.
"""

import pytest
from oiduna.domain.session import SessionContainer
from oiduna.domain.models import PatternEvent
from oiduna.domain.models import OscDestinationConfig


@pytest.fixture
def container():
    """Create a fresh SessionContainer."""
    return SessionContainer()


@pytest.fixture
def container_with_destination(container):
    """Manager with a destination."""
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)
    return container


@pytest.fixture
def container_with_client(container_with_destination):
    """Manager with destination and client."""
    container_with_destination.clients.create("client_001", "Alice", "mars")
    return container_with_destination


class TestClientCRUD:
    """Test client CRUD operations."""

    def test_create_client(self, container):
        """Test creating a client."""
        client = container.clients.create("client_001", "Alice", "mars")
        assert client.client_id == "client_001"
        assert client.client_name == "Alice"
        assert client.distribution == "mars"
        assert len(client.token) == 36

    def test_create_duplicate_client(self, container):
        """Test creating duplicate client fails."""
        container.clients.create("client_001", "Alice")
        with pytest.raises(ValueError, match="already exists"):
            container.clients.create("client_001", "Bob")

    def test_get_client(self, container_with_client):
        """Test getting a client."""
        client = container_with_client.clients.get("client_001")
        assert client is not None
        assert client.client_id == "client_001"

    def test_get_nonexistent_client(self, container):
        """Test getting nonexistent client."""
        assert container.clients.get("nonexistent") is None

    def test_list_clients(self, container_with_client):
        """Test listing clients."""
        container_with_client.clients.create("client_002", "Bob")
        clients = container_with_client.clients.list_clients()
        assert len(clients) == 2
        assert {c.client_id for c in clients} == {"client_001", "client_002"}

    def test_delete_client(self, container_with_client):
        """Test deleting a client."""
        assert container_with_client.clients.delete("client_001") is True
        assert container_with_client.clients.get("client_001") is None

    def test_delete_nonexistent_client(self, container):
        """Test deleting nonexistent client."""
        assert container.clients.delete("nonexistent") is False


class TestTrackCRUD:
    """Test track CRUD operations."""

    def test_create_track(self, container_with_client):
        """Test creating a track."""
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"}
        )
        # Validate track_id format (4-char hex, session-scoped)
        assert len(track.track_id) == 4
        assert all(c in "0123456789abcdef" for c in track.track_id)
        assert track.track_name == "kick"
        assert track.destination_id == "superdirt"
        assert track.client_id == "client_001"
        assert track.base_params == {"sound": "bd"}

    def test_create_track_invalid_destination(self, container_with_client):
        """Test creating track with invalid destination."""
        with pytest.raises(ValueError, match="does not exist"):
            container_with_client.tracks.create(
                track_name="kick",
                destination_id="invalid",
                client_id="client_001",
            )

    def test_create_track_invalid_client(self, container_with_destination):
        """Test creating track with invalid client."""
        with pytest.raises(ValueError, match="does not exist"):
            container_with_destination.tracks.create(
                track_name="kick",
                destination_id="superdirt",
                client_id="invalid",
            )

    def test_create_duplicate_track(self, container_with_client):
        """Test creating duplicate track fails."""
        track1 = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        # Cannot create duplicate with same ID - but we removed track_id param,
        # so each create() generates a unique ID. This test is no longer valid.
        # We'll test that multiple tracks can be created instead.
        track2 = container_with_client.tracks.create(
            track_name="snare",
            destination_id="superdirt",
            client_id="client_001",
        )
        assert track1.track_id != track2.track_id

    def test_get_track(self, container_with_client):
        """Test getting a track."""
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        retrieved = container_with_client.tracks.get(track.track_id)
        assert retrieved is not None
        assert retrieved.track_id == track.track_id

    def test_update_track_base_params(self, container_with_client):
        """Test updating track base params."""
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"}
        )
        updated = container_with_client.tracks.update_base_params(
            track.track_id,
            {"gain": 0.8}
        )
        assert updated.base_params == {"sound": "bd", "gain": 0.8}

    def test_delete_track(self, container_with_client):
        """Test deleting a track."""
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        assert container_with_client.tracks.delete(track.track_id) is True
        assert container_with_client.tracks.get(track.track_id) is None


class TestPatternCRUD:
    """Test pattern CRUD operations."""

    @pytest.fixture
    def container_with_track(self, container_with_client):
        """Manager with track."""
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        # Store track for use in tests
        container_with_client._test_track = track
        return container_with_client

    def test_create_pattern(self, container_with_track):
        """Test creating a pattern."""
        track = container_with_track._test_track
        events = [PatternEvent(step=0, cycle=0.0, params={})]
        pattern = container_with_track.patterns.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=events
        )
        assert pattern is not None
        # Validate pattern_id format (4-char hex, session-scoped)
        assert len(pattern.pattern_id) == 4
        assert all(c in "0123456789abcdef" for c in pattern.pattern_id)
        assert pattern.pattern_name == "main"
        assert pattern.track_id == track.track_id
        assert pattern.archived is False
        assert len(pattern.events) == 1

    def test_create_pattern_invalid_track(self, container_with_client):
        """Test creating pattern with invalid track."""
        with pytest.raises(ValueError, match="Track 'invalid' not found"):
            container_with_client.patterns.create(
                track_id="invalid",
                pattern_name="main",
                client_id="client_001",
            )

    def test_get_pattern(self, container_with_track):
        """Test getting a pattern."""
        track = container_with_track._test_track
        pattern = container_with_track.patterns.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="client_001",
        )
        retrieved = container_with_track.patterns.get(track.track_id, pattern.pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_id == pattern.pattern_id

    def test_update_pattern(self, container_with_track):
        """Test updating a pattern."""
        track = container_with_track._test_track
        pattern = container_with_track.patterns.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="client_001",
            active=True,
        )
        updated = container_with_track.patterns.update(
            pattern.pattern_id,
            active=False,
            events=[PatternEvent(step=0, cycle=0.0, params={"gain": 0.9})]
        )
        assert updated is not None
        assert updated.active is False
        assert len(updated.events) == 1

    def test_delete_pattern(self, container_with_track):
        """Test deleting a pattern."""
        track = container_with_track._test_track
        pattern = container_with_track.patterns.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="client_001",
        )
        assert container_with_track.patterns.delete(pattern.pattern_id) is True
        # Pattern still exists but with archived=True (soft delete)
        retrieved = container_with_track.patterns.get_by_id(pattern.pattern_id)
        assert retrieved is not None
        assert retrieved.archived is True


class TestEnvironment:
    """Test environment operations."""

    def test_update_environment_bpm(self, container):
        """Test updating BPM."""
        env = container.environment.update(bpm=140.0)
        assert env.bpm == 140.0

    def test_update_environment_metadata(self, container):
        """Test updating metadata."""
        env = container.environment.update(metadata={"key": "Am"})
        assert env.metadata == {"key": "Am"}


class TestSessionReset:
    """Test session reset."""

    def test_reset(self, container_with_client):
        """Test resetting session."""
        # Add a track first
        track = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )

        # Reset should clear everything
        container_with_client.reset()
        assert len(container_with_client.session.clients) == 0
        assert len(container_with_client.session.tracks) == 0
        assert len(container_with_client.session.destinations) == 0
