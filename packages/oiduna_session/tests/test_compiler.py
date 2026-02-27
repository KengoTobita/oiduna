"""
Unit tests for SessionCompiler.
"""

import pytest
from oiduna_session import SessionCompiler, SessionManager
from oiduna_models import Event
from oiduna_destination.destination_models import OscDestinationConfig


@pytest.fixture
def manager():
    """Create manager with test data."""
    manager = SessionManager()

    # Add destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    manager.add_destination(dest)

    # Add client
    manager.create_client("client_001", "Alice", "mars")

    # Add track with base params
    manager.create_track(
        track_id="track_001",
        track_name="kick",
        destination_id="superdirt",
        client_id="client_001",
        base_params={"sound": "bd", "orbit": 0}
    )

    # Add pattern with events
    events = [
        Event(step=0, cycle=0.0, params={}),
        Event(step=64, cycle=1.0, params={"gain": 0.9}),
    ]
    manager.create_pattern(
        track_id="track_001",
        pattern_id="pattern_001",
        pattern_name="main",
        client_id="client_001",
        active=True,
        events=events
    )

    return manager


class TestSessionCompiler:
    """Test session compiler."""

    def test_compile_empty_session(self):
        """Test compiling empty session."""
        manager = SessionManager()
        batch = SessionCompiler.compile(manager.session)
        assert len(batch.messages) == 0
        assert batch.bpm == 120.0

    def test_compile_with_active_pattern(self, manager):
        """Test compiling session with active pattern."""
        batch = SessionCompiler.compile(manager.session)
        assert len(batch.messages) == 2
        assert batch.bpm == 120.0

        # Check first message
        msg = batch.messages[0]
        assert msg.destination_id == "superdirt"
        assert msg.step == 0
        assert msg.cycle == 0.0
        assert msg.params["sound"] == "bd"
        assert msg.params["orbit"] == 0
        assert msg.params["track_id"] == "track_001"

        # Check second message (event params override base params)
        msg = batch.messages[1]
        assert msg.step == 64
        assert msg.cycle == 1.0
        assert msg.params["gain"] == 0.9
        assert msg.params["sound"] == "bd"  # Base param

    def test_compile_with_inactive_pattern(self, manager):
        """Test inactive patterns are skipped."""
        # Set pattern inactive
        manager.update_pattern("track_001", "pattern_001", active=False)

        batch = SessionCompiler.compile(manager.session)
        assert len(batch.messages) == 0

    def test_compile_multiple_tracks(self, manager):
        """Test compiling multiple tracks."""
        # Add second track
        manager.create_track(
            track_id="track_002",
            track_name="snare",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "sd"}
        )
        manager.create_pattern(
            track_id="track_002",
            pattern_id="pattern_002",
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=[Event(step=128, cycle=2.0, params={})]
        )

        batch = SessionCompiler.compile(manager.session)
        assert len(batch.messages) == 3  # 2 from track_001 + 1 from track_002

    def test_compile_track(self, manager):
        """Test compiling a single track."""
        messages = SessionCompiler.compile_track(manager.session, "track_001")
        assert len(messages) == 2

        msg = messages[0]
        assert msg.destination_id == "superdirt"
        assert msg.params["sound"] == "bd"
        assert msg.params["track_id"] == "track_001"

    def test_compile_track_not_found(self, manager):
        """Test compiling nonexistent track."""
        with pytest.raises(KeyError):
            SessionCompiler.compile_track(manager.session, "invalid")

    def test_param_merging(self, manager):
        """Test base_params and event params merging."""
        # Event params should override base params
        batch = SessionCompiler.compile(manager.session)
        msg = batch.messages[1]  # Second event has gain param

        assert msg.params["sound"] == "bd"  # From base_params
        assert msg.params["orbit"] == 0  # From base_params
        assert msg.params["gain"] == 0.9  # From event.params (override)
