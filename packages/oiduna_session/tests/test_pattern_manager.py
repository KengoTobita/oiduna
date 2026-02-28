"""Direct tests for PatternManager."""
import pytest
from oiduna_models import Session, Event
from oiduna_session.managers import (
    ClientManager,
    DestinationManager,
    TrackManager,
    PatternManager,
)
from oiduna_models import OscDestinationConfig


@pytest.fixture
def managers():
    """Create managers with dependencies set up."""
    session = Session()
    cm = ClientManager(session)
    dm = DestinationManager(session)
    tm = TrackManager(session, destination_manager=dm, client_manager=cm)
    pm = PatternManager(session, track_manager=tm, client_manager=cm)

    # Setup
    dm.add(OscDestinationConfig(
        id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
    ))
    cm.create("c1", "Alice", "mars")
    tm.create("t1", "kick", "sd", "c1", {"sound": "bd"})

    return {"pattern": pm, "track": tm, "client": cm, "session": session}


class TestPatternManagerCreate:
    """Test pattern creation operations."""

    def test_create_pattern(self, managers):
        """Test creating a pattern."""
        pm = managers["pattern"]
        events = [Event(step=0, cycle=0.0, params={"gain": 0.8})]
        pattern = pm.create("t1", "p1", "main", "c1", True, events)
        assert pattern is not None
        assert pattern.pattern_id == "p1"
        assert pattern.pattern_name == "main"
        assert pattern.client_id == "c1"
        assert pattern.active is True
        assert len(pattern.events) == 1

    def test_create_pattern_without_events(self, managers):
        """Test creating a pattern without events."""
        pm = managers["pattern"]
        pattern = pm.create("t1", "p1", "main", "c1")
        assert pattern is not None
        assert pattern.events == []

    def test_create_pattern_invalid_track(self, managers):
        """Test creating a pattern on invalid track returns None."""
        pm = managers["pattern"]
        pattern = pm.create("invalid", "p1", "main", "c1")
        assert pattern is None

    def test_create_pattern_invalid_client_raises(self, managers):
        """Test that invalid client raises ValueError."""
        pm = managers["pattern"]
        with pytest.raises(ValueError, match="does not exist"):
            pm.create("t1", "p1", "main", "invalid")

    def test_create_duplicate_pattern_raises(self, managers):
        """Test that duplicate pattern ID raises ValueError."""
        pm = managers["pattern"]
        pm.create("t1", "p1", "main", "c1")
        with pytest.raises(ValueError, match="already exists"):
            pm.create("t1", "p1", "other", "c1")


class TestPatternManagerRetrieval:
    """Test pattern retrieval operations."""

    def test_get_pattern(self, managers):
        """Test getting a pattern by ID."""
        pm = managers["pattern"]
        created = pm.create("t1", "p1", "main", "c1")
        retrieved = pm.get("t1", "p1")
        assert retrieved is not None
        assert retrieved.pattern_id == created.pattern_id

    def test_get_pattern_invalid_track(self, managers):
        """Test getting a pattern from invalid track returns None."""
        pm = managers["pattern"]
        assert pm.get("invalid", "p1") is None

    def test_get_nonexistent_pattern(self, managers):
        """Test getting a nonexistent pattern returns None."""
        pm = managers["pattern"]
        assert pm.get("t1", "nonexistent") is None

    def test_list_patterns(self, managers):
        """Test listing all patterns in a track."""
        pm = managers["pattern"]
        pm.create("t1", "p1", "main", "c1")
        pm.create("t1", "p2", "variation", "c1")
        patterns = pm.list("t1")
        assert patterns is not None
        assert len(patterns) == 2
        assert {p.pattern_id for p in patterns} == {"p1", "p2"}

    def test_list_patterns_invalid_track(self, managers):
        """Test listing patterns from invalid track returns None."""
        pm = managers["pattern"]
        assert pm.list("invalid") is None

    def test_list_empty(self, managers):
        """Test listing patterns when none exist."""
        pm = managers["pattern"]
        patterns = pm.list("t1")
        assert patterns == []


class TestPatternManagerUpdate:
    """Test pattern update operations."""

    def test_update_pattern_active(self, managers):
        """Test updating pattern active state."""
        pm = managers["pattern"]
        pm.create("t1", "p1", "main", "c1", active=True)
        updated = pm.update("t1", "p1", active=False)
        assert updated is not None
        assert updated.active is False

    def test_update_pattern_events(self, managers):
        """Test updating pattern events."""
        pm = managers["pattern"]
        pm.create("t1", "p1", "main", "c1")
        new_events = [Event(step=0, cycle=0.0, params={"gain": 0.5})]
        updated = pm.update("t1", "p1", events=new_events)
        assert updated is not None
        assert len(updated.events) == 1
        assert updated.events[0].params["gain"] == 0.5

    def test_update_nonexistent_pattern(self, managers):
        """Test updating a nonexistent pattern returns None."""
        pm = managers["pattern"]
        assert pm.update("t1", "nonexistent", active=False) is None


class TestPatternManagerDeletion:
    """Test pattern deletion operations."""

    def test_delete_pattern(self, managers):
        """Test deleting a pattern."""
        pm = managers["pattern"]
        pm.create("t1", "p1", "main", "c1")
        assert pm.delete("t1", "p1") is True
        assert pm.get("t1", "p1") is None

    def test_delete_pattern_invalid_track(self, managers):
        """Test deleting a pattern from invalid track returns False."""
        pm = managers["pattern"]
        assert pm.delete("invalid", "p1") is False

    def test_delete_nonexistent_pattern(self, managers):
        """Test deleting a nonexistent pattern returns False."""
        pm = managers["pattern"]
        assert pm.delete("t1", "nonexistent") is False


class TestPatternManagerEvents:
    """Test event emission from PatternManager."""

    def test_pattern_created_event(self):
        """Test that pattern creation emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(session, destination_manager=dm, client_manager=cm)
        pm = PatternManager(session, MockEventSink(events), tm, cm)

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        tm.create("t1", "kick", "sd", "c1")
        events.clear()

        pm.create("t1", "p1", "main", "c1")

        assert len(events) == 1
        assert events[0]["type"] == "pattern_created"
        assert events[0]["data"]["pattern_id"] == "p1"

    def test_pattern_updated_event(self):
        """Test that pattern update emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(session, destination_manager=dm, client_manager=cm)
        pm = PatternManager(session, MockEventSink(events), tm, cm)

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        tm.create("t1", "kick", "sd", "c1")
        pm.create("t1", "p1", "main", "c1")
        events.clear()

        pm.update("t1", "p1", active=False)

        assert len(events) == 1
        assert events[0]["type"] == "pattern_updated"
        assert events[0]["data"]["pattern_id"] == "p1"

    def test_pattern_deleted_event(self):
        """Test that pattern deletion emits event."""
        session = Session()
        events = []
        cm = ClientManager(session)
        dm = DestinationManager(session)
        tm = TrackManager(session, destination_manager=dm, client_manager=cm)
        pm = PatternManager(session, MockEventSink(events), tm, cm)

        dm.add(OscDestinationConfig(
            id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
        ))
        cm.create("c1", "Alice")
        tm.create("t1", "kick", "sd", "c1")
        pm.create("t1", "p1", "main", "c1")
        events.clear()

        pm.delete("t1", "p1")

        assert len(events) == 1
        assert events[0]["type"] == "pattern_deleted"
        assert events[0]["data"]["pattern_id"] == "p1"


class MockEventSink:
    """Mock event sink for testing."""

    def __init__(self, events_list):
        self.events = events_list

    def _push(self, event: dict) -> None:
        self.events.append(event)
