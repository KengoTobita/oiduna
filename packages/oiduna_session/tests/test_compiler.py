"""
Unit tests for SessionCompiler.
"""

import pytest
from oiduna_session import SessionCompiler, SessionContainer
from oiduna_models import Event
from oiduna_destination.destination_models import OscDestinationConfig


@pytest.fixture
def container():
    """Create container with test data."""
    container = SessionContainer()

    # Add destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)

    # Add client
    container.clients.create("client_001", "Alice", "mars")

    # Add track with base params
    container.tracks.create(
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
    container.patterns.create(
        track_id="track_001",
        pattern_id="pattern_001",
        pattern_name="main",
        client_id="client_001",
        active=True,
        events=events
    )

    return container


class TestSessionCompiler:
    """Test session compiler."""

    def test_compile_empty_session(self):
        """Test compiling empty session."""
        container = SessionContainer()
        batch = SessionCompiler.compile(container.session)
        assert len(batch.messages) == 0
        assert batch.bpm == 120.0

    def test_compile_with_active_pattern(self, container):
        """Test compiling session with active pattern."""
        batch = SessionCompiler.compile(container.session)
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

    def test_compile_with_inactive_pattern(self, container):
        """Test inactive patterns are skipped."""
        # Set pattern inactive
        container.patterns.update("track_001", "pattern_001", active=False)

        batch = SessionCompiler.compile(container.session)
        assert len(batch.messages) == 0

    def test_compile_multiple_tracks(self, container):
        """Test compiling multiple tracks."""
        # Add second track
        container.tracks.create(
            track_id="track_002",
            track_name="snare",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "sd"}
        )
        container.patterns.create(
            track_id="track_002",
            pattern_id="pattern_002",
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=[Event(step=128, cycle=2.0, params={})]
        )

        batch = SessionCompiler.compile(container.session)
        assert len(batch.messages) == 3  # 2 from track_001 + 1 from track_002

    def test_compile_track(self, container):
        """Test compiling a single track."""
        messages = SessionCompiler.compile_track(container.session, "track_001")
        assert len(messages) == 2

        msg = messages[0]
        assert msg.destination_id == "superdirt"
        assert msg.params["sound"] == "bd"
        assert msg.params["track_id"] == "track_001"

    def test_compile_track_not_found(self, container):
        """Test compiling nonexistent track."""
        with pytest.raises(KeyError):
            SessionCompiler.compile_track(container.session, "invalid")

    def test_param_merging(self, container):
        """Test base_params and event params merging."""
        # Event params should override base params
        batch = SessionCompiler.compile(container.session)
        msg = batch.messages[1]  # Second event has gain param

        assert msg.params["sound"] == "bd"  # From base_params
        assert msg.params["orbit"] == 0  # From base_params
        assert msg.params["gain"] == 0.9  # From event.params (override)
