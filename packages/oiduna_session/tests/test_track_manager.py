"""Direct tests for TrackManager."""
import pytest
from oiduna_models import Session
from oiduna_session.managers import ClientManager, DestinationManager, TrackManager
from oiduna_models import OscDestinationConfig


@pytest.fixture
def managers():
    """Create managers with dependencies set up."""
    session = Session()
    cm = ClientManager(session)
    dm = DestinationManager(session)
    tm = TrackManager(
        session,
        id_generator=session._id_generator,
        destination_manager=dm,
        client_manager=cm
    )

    # Setup
    dm.add(OscDestinationConfig(
        id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
    ))
    cm.create("c1", "Alice", "mars")

    return {"track": tm, "client": cm, "dest": dm, "session": session}


class TestTrackManagerCreate:
    """Test track creation operations."""

    def test_create_track(self, managers):
        """Test creating a track with server-generated ID."""
        tm = managers["track"]
        track = tm.create("kick", "sd", "c1", {"sound": "bd"})
        # Validate hex ID format (4-digit, session-scoped)
        assert len(track.track_id) == 4
        assert all(c in "0123456789abcdef" for c in track.track_id)
        assert track.track_name == "kick"
        assert track.destination_id == "sd"
        assert track.client_id == "c1"
        assert track.base_params == {"sound": "bd"}

    def test_create_track_without_base_params(self, managers):
        """Test creating a track without base params."""
        tm = managers["track"]
        track = tm.create("kick", "sd", "c1")
        assert track.base_params == {}

    def test_create_track_invalid_destination_raises(self, managers):
        """Test that invalid destination raises ValueError."""
        tm = managers["track"]
        with pytest.raises(ValueError, match="does not exist"):
            tm.create("kick", "invalid", "c1", {})

    def test_create_track_invalid_client_raises(self, managers):
        """Test that invalid client raises ValueError."""
        tm = managers["track"]
        with pytest.raises(ValueError, match="does not exist"):
            tm.create("kick", "sd", "invalid", {})


class TestTrackManagerRetrieval:
    """Test track retrieval operations."""

    def test_get_track(self, managers):
        """Test getting a track by ID."""
        tm = managers["track"]
        created = tm.create("kick", "sd", "c1")
        retrieved = tm.get(created.track_id)
        assert retrieved is not None
        assert retrieved.track_id == created.track_id

    def test_get_nonexistent_track(self, managers):
        """Test getting a nonexistent track returns None."""
        tm = managers["track"]
        assert tm.get("ffff") is None

    def test_list_tracks(self, managers):
        """Test listing all tracks."""
        tm = managers["track"]
        track1 = tm.create("kick", "sd", "c1")
        track2 = tm.create("snare", "sd", "c1")
        tracks = tm.list()
        assert len(tracks) == 2
        assert {t.track_id for t in tracks} == {track1.track_id, track2.track_id}

    def test_list_empty(self, managers):
        """Test listing tracks when none exist."""
        tm = managers["track"]
        assert tm.list() == []


class TestTrackManagerUpdate:
    """Test track update operations."""

    def test_update_base_params(self, managers):
        """Test updating track base params."""
        tm = managers["track"]
        track = tm.create("kick", "sd", "c1", {"sound": "bd"})
        updated = tm.update_base_params(track.track_id, {"gain": 0.8})
        assert updated is not None
        assert updated.base_params["sound"] == "bd"
        assert updated.base_params["gain"] == 0.8

    def test_update_nonexistent_track(self, managers):
        """Test updating a nonexistent track returns None."""
        tm = managers["track"]
        assert tm.update_base_params("ffff", {"gain": 0.8}) is None


class TestTrackManagerDeletion:
    """Test track deletion operations."""

    def test_delete_track(self, managers):
        """Test deleting a track."""
        tm = managers["track"]
        track = tm.create("kick", "sd", "c1")
        assert tm.delete(track.track_id) is True
        assert tm.get(track.track_id) is None

    def test_delete_nonexistent_track(self, managers):
        """Test deleting a nonexistent track returns False."""
        tm = managers["track"]
        assert tm.delete("ffff") is False


class TestTrackManagerEvents:
    """Test event emission from TrackManager."""

    def test_track_created_event(self):
        """Test that track creation emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(
            session,
            event_publisher=MockEventSink(events),
            destination_manager=dm,
            client_manager=cm
        )

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        events.clear()

        track = tm.create("kick", "sd", "c1")

        assert len(events) == 1
        assert events[0]["type"] == "track_created"
        assert events[0]["data"]["track_id"] == track.track_id

    def test_track_updated_event(self):
        """Test that track update emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(
            session,
            event_publisher=MockEventSink(events),
            destination_manager=dm,
            client_manager=cm
        )

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        track = tm.create("kick", "sd", "c1")
        events.clear()

        tm.update_base_params(track.track_id, {"gain": 0.8})

        assert len(events) == 1
        assert events[0]["type"] == "track_updated"
        assert events[0]["data"]["track_id"] == track.track_id

    def test_track_deleted_event(self):
        """Test that track deletion emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(
            session,
            event_publisher=MockEventSink(events),
            destination_manager=dm,
            client_manager=cm
        )

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        track = tm.create("kick", "sd", "c1")
        events.clear()

        tm.delete(track.track_id)

        assert len(events) == 1
        assert events[0]["type"] == "track_deleted"
        assert events[0]["data"]["track_id"] == track.track_id


class MockEventSink:
    """Mock event sink for testing."""

    def __init__(self, events_list):
        self.events = events_list

    def publish(self, event: dict) -> None:
        self.events.append(event)
