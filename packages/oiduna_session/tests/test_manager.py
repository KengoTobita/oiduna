"""
Unit tests for SessionManager.
"""

import pytest
from oiduna_session import SessionContainer
from oiduna_models import Event
from oiduna_models import OscDestinationConfig


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
        clients = container_with_client.clients.list()
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
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"}
        )
        assert track.track_id == "track_001"
        assert track.track_name == "kick"
        assert track.destination_id == "superdirt"
        assert track.client_id == "client_001"
        assert track.base_params == {"sound": "bd"}

    def test_create_track_invalid_destination(self, container_with_client):
        """Test creating track with invalid destination."""
        with pytest.raises(ValueError, match="does not exist"):
            container_with_client.tracks.create(
                track_id="track_001",
                track_name="kick",
                destination_id="invalid",
                client_id="client_001",
            )

    def test_create_track_invalid_client(self, container_with_destination):
        """Test creating track with invalid client."""
        with pytest.raises(ValueError, match="does not exist"):
            container_with_destination.tracks.create(
                track_id="track_001",
                track_name="kick",
                destination_id="superdirt",
                client_id="invalid",
            )

    def test_create_duplicate_track(self, container_with_client):
        """Test creating duplicate track fails."""
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        with pytest.raises(ValueError, match="already exists"):
            container_with_client.tracks.create(
                track_id="track_001",
                track_name="snare",
                destination_id="superdirt",
                client_id="client_001",
            )

    def test_get_track(self, container_with_client):
        """Test getting a track."""
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        track = container_with_client.tracks.get("track_001")
        assert track is not None
        assert track.track_id == "track_001"

    def test_update_track_base_params(self, container_with_client):
        """Test updating track base params."""
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"}
        )
        track = container_with_client.tracks.update_base_params(
            "track_001",
            {"gain": 0.8}
        )
        assert track.base_params == {"sound": "bd", "gain": 0.8}

    def test_delete_track(self, container_with_client):
        """Test deleting a track."""
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        assert container_with_client.tracks.delete("track_001") is True
        assert container_with_client.tracks.get("track_001") is None


class TestPatternCRUD:
    """Test pattern CRUD operations."""

    @pytest.fixture
    def container_with_track(self, container_with_client):
        """Manager with track."""
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        return container_with_client

    def test_create_pattern(self, container_with_track):
        """Test creating a pattern."""
        events = [Event(step=0, cycle=0.0, params={})]
        pattern = container_with_track.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=events
        )
        assert pattern is not None
        assert pattern.pattern_id == "pattern_001"
        assert pattern.pattern_name == "main"
        assert len(pattern.events) == 1

    def test_create_pattern_invalid_track(self, container_with_client):
        """Test creating pattern with invalid track."""
        result = container_with_client.patterns.create(
            track_id="invalid",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        assert result is None

    def test_get_pattern(self, container_with_track):
        """Test getting a pattern."""
        container_with_track.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        pattern = container_with_track.patterns.get("track_001", "pattern_001")
        assert pattern is not None
        assert pattern.pattern_id == "pattern_001"

    def test_update_pattern(self, container_with_track):
        """Test updating a pattern."""
        container_with_track.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
            active=True,
        )
        pattern = container_with_track.patterns.update(
            "track_001",
            "pattern_001",
            active=False,
            events=[Event(step=0, cycle=0.0, params={"gain": 0.9})]
        )
        assert pattern.active is False
        assert len(pattern.events) == 1

    def test_delete_pattern(self, container_with_track):
        """Test deleting a pattern."""
        container_with_track.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        assert container_with_track.patterns.delete("track_001", "pattern_001") is True
        assert container_with_track.patterns.get("track_001", "pattern_001") is None


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
        container_with_client.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )

        # Reset should clear everything
        container_with_client.reset()
        assert len(container_with_client.session.clients) == 0
        assert len(container_with_client.session.tracks) == 0
        assert len(container_with_client.session.destinations) == 0
