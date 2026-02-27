"""
Unit tests for SessionManager.
"""

import pytest
from oiduna_session import SessionManager
from oiduna_models import Event
from oiduna_destination.destination_models import OscDestinationConfig


@pytest.fixture
def manager():
    """Create a fresh SessionManager."""
    return SessionManager()


@pytest.fixture
def manager_with_destination(manager):
    """Manager with a destination."""
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    manager.add_destination(dest)
    return manager


@pytest.fixture
def manager_with_client(manager_with_destination):
    """Manager with destination and client."""
    manager_with_destination.create_client("client_001", "Alice", "mars")
    return manager_with_destination


class TestClientCRUD:
    """Test client CRUD operations."""

    def test_create_client(self, manager):
        """Test creating a client."""
        client = manager.create_client("client_001", "Alice", "mars")
        assert client.client_id == "client_001"
        assert client.client_name == "Alice"
        assert client.distribution == "mars"
        assert len(client.token) == 36

    def test_create_duplicate_client(self, manager):
        """Test creating duplicate client fails."""
        manager.create_client("client_001", "Alice")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_client("client_001", "Bob")

    def test_get_client(self, manager_with_client):
        """Test getting a client."""
        client = manager_with_client.get_client("client_001")
        assert client is not None
        assert client.client_id == "client_001"

    def test_get_nonexistent_client(self, manager):
        """Test getting nonexistent client."""
        assert manager.get_client("nonexistent") is None

    def test_list_clients(self, manager_with_client):
        """Test listing clients."""
        manager_with_client.create_client("client_002", "Bob")
        clients = manager_with_client.list_clients()
        assert len(clients) == 2
        assert {c.client_id for c in clients} == {"client_001", "client_002"}

    def test_delete_client(self, manager_with_client):
        """Test deleting a client."""
        assert manager_with_client.delete_client("client_001") is True
        assert manager_with_client.get_client("client_001") is None

    def test_delete_nonexistent_client(self, manager):
        """Test deleting nonexistent client."""
        assert manager.delete_client("nonexistent") is False


class TestTrackCRUD:
    """Test track CRUD operations."""

    def test_create_track(self, manager_with_client):
        """Test creating a track."""
        track = manager_with_client.create_track(
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

    def test_create_track_invalid_destination(self, manager_with_client):
        """Test creating track with invalid destination."""
        with pytest.raises(ValueError, match="does not exist"):
            manager_with_client.create_track(
                track_id="track_001",
                track_name="kick",
                destination_id="invalid",
                client_id="client_001",
            )

    def test_create_track_invalid_client(self, manager_with_destination):
        """Test creating track with invalid client."""
        with pytest.raises(ValueError, match="does not exist"):
            manager_with_destination.create_track(
                track_id="track_001",
                track_name="kick",
                destination_id="superdirt",
                client_id="invalid",
            )

    def test_create_duplicate_track(self, manager_with_client):
        """Test creating duplicate track fails."""
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        with pytest.raises(ValueError, match="already exists"):
            manager_with_client.create_track(
                track_id="track_001",
                track_name="snare",
                destination_id="superdirt",
                client_id="client_001",
            )

    def test_get_track(self, manager_with_client):
        """Test getting a track."""
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        track = manager_with_client.get_track("track_001")
        assert track is not None
        assert track.track_id == "track_001"

    def test_update_track_base_params(self, manager_with_client):
        """Test updating track base params."""
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"}
        )
        track = manager_with_client.update_track_base_params(
            "track_001",
            {"gain": 0.8}
        )
        assert track.base_params == {"sound": "bd", "gain": 0.8}

    def test_delete_track(self, manager_with_client):
        """Test deleting a track."""
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        assert manager_with_client.delete_track("track_001") is True
        assert manager_with_client.get_track("track_001") is None


class TestPatternCRUD:
    """Test pattern CRUD operations."""

    @pytest.fixture
    def manager_with_track(self, manager_with_client):
        """Manager with track."""
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        return manager_with_client

    def test_create_pattern(self, manager_with_track):
        """Test creating a pattern."""
        events = [Event(step=0, cycle=0.0, params={})]
        pattern = manager_with_track.create_pattern(
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

    def test_create_pattern_invalid_track(self, manager_with_client):
        """Test creating pattern with invalid track."""
        result = manager_with_client.create_pattern(
            track_id="invalid",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        assert result is None

    def test_get_pattern(self, manager_with_track):
        """Test getting a pattern."""
        manager_with_track.create_pattern(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        pattern = manager_with_track.get_pattern("track_001", "pattern_001")
        assert pattern is not None
        assert pattern.pattern_id == "pattern_001"

    def test_update_pattern(self, manager_with_track):
        """Test updating a pattern."""
        manager_with_track.create_pattern(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
            active=True,
        )
        pattern = manager_with_track.update_pattern(
            "track_001",
            "pattern_001",
            active=False,
            events=[Event(step=0, cycle=0.0, params={"gain": 0.9})]
        )
        assert pattern.active is False
        assert len(pattern.events) == 1

    def test_delete_pattern(self, manager_with_track):
        """Test deleting a pattern."""
        manager_with_track.create_pattern(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
        )
        assert manager_with_track.delete_pattern("track_001", "pattern_001") is True
        assert manager_with_track.get_pattern("track_001", "pattern_001") is None


class TestEnvironment:
    """Test environment operations."""

    def test_update_environment_bpm(self, manager):
        """Test updating BPM."""
        env = manager.update_environment(bpm=140.0)
        assert env.bpm == 140.0

    def test_update_environment_metadata(self, manager):
        """Test updating metadata."""
        env = manager.update_environment(metadata={"key": "Am"})
        assert env.metadata == {"key": "Am"}


class TestSessionReset:
    """Test session reset."""

    def test_reset(self, manager_with_client):
        """Test resetting session."""
        # Add a track first
        manager_with_client.create_track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )

        # Reset should clear everything
        manager_with_client.reset()
        assert len(manager_with_client.session.clients) == 0
        assert len(manager_with_client.session.tracks) == 0
        assert len(manager_with_client.session.destinations) == 0
