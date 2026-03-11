"""
Unit tests for SessionCompiler.
"""

import pytest
from oiduna_session import SessionCompiler, SessionContainer
from oiduna_models import PatternEvent
from oiduna_models import OscDestinationConfig


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
    client = container.clients.create("client_001", "Alice", "mars")

    # Add track with base params (no hardcoded track_id)
    track = container.tracks.create(
        track_name="kick",
        destination_id="superdirt",
        client_id=client.client_id,
        base_params={"sound": "bd", "orbit": 0}
    )

    # Add pattern with events (no hardcoded pattern_id)
    events = [
        PatternEvent(step=0, cycle=0.0, params={}),
        PatternEvent(step=64, cycle=1.0, params={"gain": 0.9}),
    ]
    pattern = container.patterns.create(
        track_id=track.track_id,
        pattern_name="main",
        client_id=client.client_id,
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
        assert len(batch.entries) == 0
        assert batch.bpm == 120.0

    def test_compile_with_active_pattern(self, container):
        """Test compiling session with active pattern."""
        batch = SessionCompiler.compile(container.session)
        assert len(batch.entries) == 2
        assert batch.bpm == 120.0

        # Get track_id dynamically
        track_id = list(container.session.tracks.keys())[0]

        # Check first message
        msg = batch.entries[0]
        assert msg.destination_id == "superdirt"
        assert msg.step == 0
        assert msg.cycle == 0.0
        assert msg.params["sound"] == "bd"
        assert msg.params["orbit"] == 0
        assert msg.params["track_id"] == track_id

        # Check second message (event params override base params)
        msg = batch.entries[1]
        assert msg.step == 64
        assert msg.cycle == 1.0
        assert msg.params["gain"] == 0.9
        assert msg.params["sound"] == "bd"  # Base param

    def test_compile_with_inactive_pattern(self, container):
        """Test inactive patterns are skipped."""
        # Get dynamic IDs
        track_id = list(container.session.tracks.keys())[0]
        pattern_id = list(container.session.tracks[track_id].patterns.keys())[0]

        # Set pattern inactive (flat API)
        container.patterns.update(pattern_id, active=False)

        batch = SessionCompiler.compile(container.session)
        assert len(batch.entries) == 0

    def test_compile_with_archived_pattern(self, container):
        """Test archived patterns are skipped (even if active=True)."""
        # Get dynamic IDs
        track_id = list(container.session.tracks.keys())[0]
        pattern_id = list(container.session.tracks[track_id].patterns.keys())[0]

        # Soft delete pattern (but keep active=True)
        container.patterns.update(pattern_id, archived=True)

        # Verify pattern still exists with archived=True
        pattern = container.patterns.get_by_id(pattern_id)
        assert pattern is not None
        assert pattern.archived is True
        assert pattern.active is True  # Still active but archived

        # Compile should skip archived patterns
        batch = SessionCompiler.compile(container.session)
        assert len(batch.entries) == 0

    def test_compile_multiple_tracks(self, container):
        """Test compiling multiple tracks."""
        # Get first client
        client_id = list(container.session.clients.keys())[0]
        
        # Add second track
        track2 = container.tracks.create(
            track_name="snare",
            destination_id="superdirt",
            client_id=client_id,
            base_params={"sound": "sd"}
        )
        container.patterns.create(
            track_id=track2.track_id,
            pattern_name="main",
            client_id=client_id,
            active=True,
            events=[PatternEvent(step=128, cycle=2.0, params={})]
        )

        batch = SessionCompiler.compile(container.session)
        assert len(batch.entries) == 3  # 2 from track_001 + 1 from track_002

    def test_compile_track(self, container):
        """Test compiling a single track."""
        # Get dynamic track_id
        track_id = list(container.session.tracks.keys())[0]

        entries = SessionCompiler.compile_track(container.session, track_id)
        assert len(entries) == 2

        msg = entries[0]
        assert msg.destination_id == "superdirt"
        assert msg.params["sound"] == "bd"
        assert msg.params["track_id"] == track_id

    def test_compile_track_not_found(self, container):
        """Test compiling nonexistent track."""
        with pytest.raises(KeyError):
            SessionCompiler.compile_track(container.session, "invalid")

    def test_param_merging(self, container):
        """Test base_params and event params merging."""
        # Event params should override base params
        batch = SessionCompiler.compile(container.session)
        msg = batch.entries[1]  # Second event has gain param

        assert msg.params["sound"] == "bd"  # From base_params
        assert msg.params["orbit"] == 0  # From base_params
        assert msg.params["gain"] == 0.9  # From event.params (override)


class TestSessionCompilerValidation:
    """Test destination validation in SessionCompiler."""

    def test_compile_with_invalid_destination_raises(self):
        """Track with non-existent destination raises ValueError."""
        container = SessionContainer()

        # Add client
        client = container.clients.create("client_001", "Alice", "mars")

        # Manually create track with invalid destination (bypass manager validation)
        from oiduna_models import Track
        container.session.tracks["0a1f"] = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="nonexistent",
            client_id=client.client_id,
            base_params={},
            patterns={}
        )

        with pytest.raises(ValueError, match="non-existent destinations"):
            SessionCompiler.compile(container.session)

    def test_compile_error_lists_invalid_tracks(self):
        """Error message lists all invalid track→destination."""
        container = SessionContainer()
        client = container.clients.create("client_001", "Alice", "mars")

        from oiduna_models import Track

        # Add two tracks with invalid destinations
        container.session.tracks["0a1f"] = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="dest1",
            client_id=client.client_id
        )
        container.session.tracks["3e2b"] = Track(
            track_id="3e2b",
            track_name="snare",
            destination_id="dest2",
            client_id=client.client_id
        )

        with pytest.raises(ValueError) as exc_info:
            SessionCompiler.compile(container.session)

        error_msg = str(exc_info.value)
        assert "0a1f→dest1" in error_msg
        assert "3e2b→dest2" in error_msg

    def test_compile_error_lists_available_destinations(self):
        """Error message includes available destinations."""
        container = SessionContainer()

        # Add a valid destination
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )
        container.destinations.add(dest)

        # Add client
        client = container.clients.create("client_001", "Alice", "mars")

        # Add track with invalid destination
        from oiduna_models import Track
        container.session.tracks["0a1f"] = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="invalid",
            client_id=client.client_id
        )

        with pytest.raises(ValueError) as exc_info:
            SessionCompiler.compile(container.session)

        error_msg = str(exc_info.value)
        assert "Available destinations:" in error_msg
        assert "superdirt" in error_msg

    def test_compile_with_valid_destination_succeeds(self):
        """Compile succeeds when all destinations exist."""
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
        client = container.clients.create("client_001", "Alice", "mars")

        # Add track with valid destination
        track = container.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id=client.client_id
        )

        # Should not raise
        batch = SessionCompiler.compile(container.session)
        assert batch is not None

    def test_compile_multiple_invalid_destinations(self):
        """Test error message with multiple invalid destinations."""
        container = SessionContainer()

        # Add some valid destinations
        for dest_id in ["superdirt", "midi_out"]:
            dest = OscDestinationConfig(
                id=dest_id,
                type="osc",
                host="127.0.0.1",
                port=57120,
                address="/dirt/play"
            )
            container.destinations.add(dest)

        client = container.clients.create("client_001", "Alice", "mars")

        from oiduna_models import Track

        # Add tracks with mix of valid and invalid destinations
        container.session.tracks["0a1f"] = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="superdirt",  # Valid
            client_id=client.client_id
        )
        container.session.tracks["3e2b"] = Track(
            track_id="3e2b",
            track_name="snare",
            destination_id="invalid1",  # Invalid
            client_id=client.client_id
        )
        container.session.tracks["5678"] = Track(
            track_id="5678",
            track_name="hihat",
            destination_id="invalid2",  # Invalid
            client_id=client.client_id
        )

        with pytest.raises(ValueError) as exc_info:
            SessionCompiler.compile(container.session)

        error_msg = str(exc_info.value)
        # Should list both invalid references
        assert "3e2b→invalid1" in error_msg
        assert "5678→invalid2" in error_msg
        # Should NOT list the valid one
        assert "0a1f" not in error_msg
