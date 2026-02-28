"""
Unit tests for SSE event emission from SessionManager.
"""

import pytest
from oiduna_session import SessionContainer
from oiduna_models import Event
from oiduna_models import OscDestinationConfig


class MockEventSink:
    """Mock event sink for testing."""

    def __init__(self):
        self.events = []

    def _push(self, event: dict) -> None:
        """Record pushed events."""
        self.events.append(event)

    def clear(self):
        """Clear recorded events."""
        self.events = []

    def get_events_by_type(self, event_type: str) -> list:
        """Get all events of a specific type."""
        return [e for e in self.events if e["type"] == event_type]


@pytest.fixture
def manager_with_sink():
    """Create container with mock event sink."""
    sink = MockEventSink()
    container = SessionContainer(event_sink=sink)

    # Add destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)

    return container, sink


class TestClientEvents:
    """Test client-related events."""

    def test_client_connected_event(self, manager_with_sink):
        """Test client_connected event is emitted."""
        container, sink = manager_with_sink

        container.clients.create("client_001", "Alice", "mars")

        events = sink.get_events_by_type("client_connected")
        assert len(events) == 1
        assert events[0]["data"]["client_id"] == "client_001"
        assert events[0]["data"]["client_name"] == "Alice"
        assert events[0]["data"]["distribution"] == "mars"

    def test_client_disconnected_event(self, manager_with_sink):
        """Test client_disconnected event is emitted."""
        container, sink = manager_with_sink

        container.clients.create("client_001", "Alice")
        sink.clear()

        container.clients.delete("client_001")

        events = sink.get_events_by_type("client_disconnected")
        assert len(events) == 1
        assert events[0]["data"]["client_id"] == "client_001"


class TestTrackEvents:
    """Test track-related events."""

    @pytest.fixture
    def container_with_client(self, manager_with_sink):
        """Create container with client."""
        container, sink = manager_with_sink
        container.clients.create("client_001", "Alice")
        sink.clear()
        return container, sink

    def test_track_created_event(self, container_with_client):
        """Test track_created event is emitted."""
        container, sink = container_with_client

        container.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001"
        )

        events = sink.get_events_by_type("track_created")
        assert len(events) == 1
        assert events[0]["data"]["track_id"] == "track_001"
        assert events[0]["data"]["track_name"] == "kick"
        assert events[0]["data"]["client_id"] == "client_001"
        assert events[0]["data"]["destination_id"] == "superdirt"

    def test_track_updated_event(self, container_with_client):
        """Test track_updated event is emitted."""
        container, sink = container_with_client

        container.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001"
        )
        sink.clear()

        container.tracks.update_base_params("track_001", {"gain": 0.8})

        events = sink.get_events_by_type("track_updated")
        assert len(events) == 1
        assert events[0]["data"]["track_id"] == "track_001"
        assert events[0]["data"]["updated_params"] == {"gain": 0.8}

    def test_track_deleted_event(self, container_with_client):
        """Test track_deleted event is emitted."""
        container, sink = container_with_client

        container.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001"
        )
        sink.clear()

        container.tracks.delete("track_001")

        events = sink.get_events_by_type("track_deleted")
        assert len(events) == 1
        assert events[0]["data"]["track_id"] == "track_001"


class TestPatternEvents:
    """Test pattern-related events."""

    @pytest.fixture
    def container_with_track(self, manager_with_sink):
        """Create container with track."""
        container, sink = manager_with_sink
        container.clients.create("client_001", "Alice")
        container.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001"
        )
        sink.clear()
        return container, sink

    def test_pattern_created_event(self, container_with_track):
        """Test pattern_created event is emitted."""
        container, sink = container_with_track

        container.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
            events=[Event(step=0, cycle=0.0, params={})]
        )

        events = sink.get_events_by_type("pattern_created")
        assert len(events) == 1
        assert events[0]["data"]["track_id"] == "track_001"
        assert events[0]["data"]["pattern_id"] == "pattern_001"
        assert events[0]["data"]["pattern_name"] == "main"
        assert events[0]["data"]["event_count"] == 1

    def test_pattern_updated_event(self, container_with_track):
        """Test pattern_updated event is emitted."""
        container, sink = container_with_track

        container.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001"
        )
        sink.clear()

        container.patterns.update("track_001", "pattern_001", active=False)

        events = sink.get_events_by_type("pattern_updated")
        assert len(events) == 1
        assert events[0]["data"]["pattern_id"] == "pattern_001"
        assert events[0]["data"]["active"] is False

    def test_pattern_deleted_event(self, container_with_track):
        """Test pattern_deleted event is emitted."""
        container, sink = container_with_track

        container.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001"
        )
        sink.clear()

        container.patterns.delete("track_001", "pattern_001")

        events = sink.get_events_by_type("pattern_deleted")
        assert len(events) == 1
        assert events[0]["data"]["pattern_id"] == "pattern_001"


class TestEnvironmentEvents:
    """Test environment-related events."""

    def test_environment_updated_event(self, manager_with_sink):
        """Test environment_updated event is emitted."""
        container, sink = manager_with_sink

        container.environment.update(bpm=140.0, metadata={"key": "Am"})

        events = sink.get_events_by_type("environment_updated")
        assert len(events) == 1
        assert events[0]["data"]["bpm"] == 140.0
        assert events[0]["data"]["metadata"] == {"key": "Am"}


class TestEventSinkOptional:
    """Test that operations work without event sink."""

    def test_operations_without_sink(self):
        """Test all operations work when event_sink is None."""
        container = SessionContainer(event_sink=None)

        # Add destination
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )
        container.destinations.add(dest)

        # All operations should work without error
        container.clients.create("client_001", "Alice")
        container.tracks.create(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001"
        )
        container.patterns.create(
            track_id="track_001",
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001"
        )
        container.tracks.update_base_params("track_001", {"gain": 0.8})
        container.patterns.update("track_001", "pattern_001", active=False)
        container.environment.update(bpm=140.0)

        # Verify operations succeeded
        assert container.clients.get("client_001") is not None
        assert container.tracks.get("track_001") is not None
        assert container.patterns.get("track_001", "pattern_001") is not None
