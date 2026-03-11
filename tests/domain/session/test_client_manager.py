"""Direct tests for ClientManager."""
import pytest
from oiduna.domain.models import Session
from oiduna.domain.session.managers.client_manager import ClientManager


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def client_manager(session):
    return ClientManager(session)


class TestClientManagerCreate:
    """Test client creation operations."""

    def test_create_client(self, client_manager):
        """Test creating a client."""
        client = client_manager.create("c1", "Alice", "mars")
        assert client.client_id == "c1"
        assert client.client_name == "Alice"
        assert client.distribution == "mars"
        assert len(client.token) == 36  # UUID length

    def test_create_client_with_metadata(self, client_manager):
        """Test creating a client with metadata."""
        metadata = {"version": "1.0", "os": "linux"}
        client = client_manager.create("c1", "Alice", "mars", metadata)
        assert client.metadata == metadata

    def test_create_duplicate_raises(self, client_manager):
        """Test that creating duplicate client raises ValueError."""
        client_manager.create("c1", "Alice")
        with pytest.raises(ValueError, match="already exists"):
            client_manager.create("c1", "Bob")


class TestClientManagerRetrieval:
    """Test client retrieval operations."""

    def test_get_client(self, client_manager):
        """Test getting a client by ID."""
        created = client_manager.create("c1", "Alice")
        retrieved = client_manager.get("c1")
        assert retrieved is not None
        assert retrieved.client_id == created.client_id
        assert retrieved.token == created.token

    def test_get_nonexistent_client(self, client_manager):
        """Test getting a nonexistent client returns None."""
        assert client_manager.get("nonexistent") is None

    def test_list_clients(self, client_manager):
        """Test listing all clients."""
        client_manager.create("c1", "Alice")
        client_manager.create("c2", "Bob")
        clients = client_manager.list_clients()
        assert len(clients) == 2
        assert {c.client_id for c in clients} == {"c1", "c2"}

    def test_list_empty(self, client_manager):
        """Test listing clients when none exist."""
        assert client_manager.list_clients() == []


class TestClientManagerDeletion:
    """Test client deletion operations."""

    def test_delete_client(self, client_manager):
        """Test deleting a client."""
        client_manager.create("c1", "Alice")
        assert client_manager.delete("c1") is True
        assert client_manager.get("c1") is None

    def test_delete_nonexistent_client(self, client_manager):
        """Test deleting a nonexistent client returns False."""
        assert client_manager.delete("nonexistent") is False

    def test_delete_resources(self, client_manager, session):
        """Test deleting all resources owned by a client."""
        from oiduna.domain.models import Track

        # Create client and track
        client_manager.create("c1", "Alice")
        track = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
            base_params={},
            patterns={},
        )
        session.tracks["0a1f"] = track

        # Delete resources
        result = client_manager.delete_resources("c1")
        assert result["tracks"] == 1
        assert result["patterns"] == 0
        assert "t1" not in session.tracks


class TestClientManagerEvents:
    """Test event emission from ClientManager."""

    def test_client_connected_event(self, session):
        """Test that client creation emits event."""
        events = []
        client_manager = ClientManager(session, event_publisher=MockEventSink(events))

        client_manager.create("c1", "Alice", "mars")

        assert len(events) == 1
        assert events[0]["type"] == "client_connected"
        assert events[0]["data"]["client_id"] == "c1"
        assert events[0]["data"]["client_name"] == "Alice"

    def test_client_disconnected_event(self, session):
        """Test that client deletion emits event."""
        events = []
        client_manager = ClientManager(session, event_publisher=MockEventSink(events))

        client_manager.create("c1", "Alice")
        events.clear()

        client_manager.delete("c1")

        assert len(events) == 1
        assert events[0]["type"] == "client_disconnected"
        assert events[0]["data"]["client_id"] == "c1"


class MockEventSink:
    """Mock event sink for testing."""

    def __init__(self, events_list):
        self.events = events_list

    def publish(self, event: dict) -> None:
        self.events.append(event)
