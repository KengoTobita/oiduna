"""
Unit tests for Oiduna data models.
"""

import pytest
from pydantic import ValidationError
from oiduna.domain.models import (
    Session,
    Track,
    Pattern,
    PatternEvent,
    ClientInfo,
    Environment,
    IDGenerator,
)
from oiduna.domain.models import OscDestinationConfig


class TestPatternEvent:
    """Test PatternEvent model."""

    def test_create_event(self):
        """Test creating a valid event."""
        event = PatternEvent(
            step=0,
            offset=0.0,
            params={"gain": 0.8}
        )
        assert event.step == 0
        assert event.offset == 0.0
        assert event.params == {"gain": 0.8}

    def test_event_step_validation(self):
        """Test step must be 0-255."""
        with pytest.raises(ValidationError, match="step"):
            PatternEvent(step=-1, offset=0.0, params={})

        with pytest.raises(ValidationError, match="step"):
            PatternEvent(step=256, offset=0.0, params={})

    def test_event_offset_validation(self):
        """Test offset must be in [0.0, 1.0)."""
        with pytest.raises(ValidationError, match="offset"):
            PatternEvent(step=0, offset=-0.1, params={})

        with pytest.raises(ValidationError, match="offset"):
            PatternEvent(step=0, offset=1.0, params={})


class TestPattern:
    """Test Pattern model."""

    def test_create_pattern(self):
        """Test creating a valid pattern."""
        pattern = Pattern(
            pattern_id="3e2b",
            track_id="0a1f",
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=[
                PatternEvent(step=0, offset=0.0, params={}),
                PatternEvent(step=64, offset=0.0, params={"gain": 0.9}),
            ]
        )
        assert pattern.pattern_id == "3e2b"
        assert pattern.track_id == "0a1f"
        assert pattern.pattern_name == "main"
        assert pattern.client_id == "client_001"
        assert pattern.active is True
        assert pattern.archived is False
        assert len(pattern.events) == 2

    def test_pattern_default_values(self):
        """Test pattern defaults."""
        pattern = Pattern(
            pattern_id="3e2b",
            track_id="0a1f",
            pattern_name="main",
            client_id="client_001"
        )
        assert pattern.active is True
        assert pattern.archived is False
        assert pattern.events == []


class TestTrack:
    """Test Track model."""

    def test_create_track(self):
        """Test creating a valid track."""
        track = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd", "orbit": 0},
        )
        assert track.track_id == "0a1f"
        assert track.track_name == "kick"
        assert track.destination_id == "superdirt"
        assert track.client_id == "client_001"
        assert track.base_params == {"sound": "bd", "orbit": 0}

    def test_track_default_values(self):
        """Test track defaults."""
        track = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )
        assert track.base_params == {}
        assert track.patterns == {}

    @pytest.mark.parametrize("destination_id,description", [
        ("superdirt", "alphanumeric"),
        ("super_dirt", "with underscore"),
        ("osc-synth", "with hyphen"),
        ("super_dirt-v1", "with underscore and hyphen"),
    ])
    def test_valid_destination_id_formats(self, destination_id, description):
        """Test various valid destination ID formats."""
        track = Track(
            track_id="0a1f",
            track_name="test",
            destination_id=destination_id,
            client_id="c1"
        )
        assert track.destination_id == destination_id

    def test_invalid_destination_id_with_space(self):
        """Test destination_id with space raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Track(
                track_id="0a1f",
                track_name="kick",
                destination_id="super dirt",
                client_id="c1"
            )

    def test_invalid_destination_id_with_special_char(self):
        """Test destination_id with special character raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Track(
                track_id="0a1f",
                track_name="kick",
                destination_id="dest!",
                client_id="c1"
            )

    def test_invalid_destination_id_error_message(self):
        """Test error message includes helpful examples."""
        with pytest.raises(ValueError, match="superdirt.*midi_1.*osc-synth"):
            Track(
                track_id="0a1f",
                track_name="kick",
                destination_id="invalid dest!",
                client_id="c1"
            )


class TestClientInfo:
    """Test ClientInfo model."""

    def test_create_client(self):
        """Test creating a valid client."""
        token = ClientInfo.generate_token()
        client = ClientInfo(
            client_id="client_001",
            client_name="Alice",
            token=token,
            distribution="mars",
            metadata={"version": "0.1.0"}
        )
        assert client.client_id == "client_001"
        assert client.client_name == "Alice"
        assert client.token == token
        assert client.distribution == "mars"

    def test_generate_token(self):
        """Test token generation."""
        token = ClientInfo.generate_token()
        assert len(token) == 36  # UUID4 format
        assert token.count("-") == 4


class TestEnvironment:
    """Test Environment model."""

    def test_create_environment(self):
        """Test creating an environment."""
        env = Environment(
            bpm=140.0,
            metadata={"key": "Am"},
            initial_metadata={"created_at": "2026-02-28"}
        )
        assert env.bpm == 140.0
        assert env.metadata == {"key": "Am"}
        assert env.initial_metadata == {"created_at": "2026-02-28"}

    def test_environment_defaults(self):
        """Test environment defaults."""
        env = Environment()
        assert env.bpm == 120.0
        assert env.metadata == {}
        assert env.initial_metadata == {}

    def test_bpm_validation(self):
        """Test BPM range validation."""
        with pytest.raises(ValidationError, match="bpm"):
            Environment(bpm=10.0)  # Too low

        with pytest.raises(ValidationError, match="bpm"):
            Environment(bpm=1000.0)  # Too high


class TestSession:
    """Test Session model."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session()
        assert isinstance(session.environment, Environment)
        assert session.destinations == {}
        assert session.clients == {}
        assert session.tracks == {}

    def test_session_with_data(self):
        """Test session with populated data."""
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )
        client = ClientInfo(
            client_id="client_001",
            client_name="Alice",
            token=ClientInfo.generate_token(),
        )
        track = Track(
            track_id="0a1f",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )

        session = Session(
            destinations={"superdirt": dest},
            clients={"client_001": client},
            tracks={"0a1f": track},
        )

        assert len(session.destinations) == 1
        assert len(session.clients) == 1
        assert len(session.tracks) == 1


class TestIDGenerator:
    """Test IDGenerator."""

    def test_track_id_format(self):
        """Test track ID is 4-digit hexadecimal."""
        gen = IDGenerator()
        track_id = gen.generate_track_id()
        assert len(track_id) == 4
        assert all(c in "0123456789abcdef" for c in track_id)

    def test_pattern_id_format(self):
        """Test pattern ID is 4-digit hexadecimal."""
        gen = IDGenerator()
        pattern_id = gen.generate_pattern_id()
        assert len(pattern_id) == 4
        assert all(c in "0123456789abcdef" for c in pattern_id)

    def test_uniqueness(self):
        """Test generated IDs are unique within a session."""
        gen = IDGenerator()
        track_ids = [gen.generate_track_id() for _ in range(1000)]
        assert len(set(track_ids)) == 1000  # All unique

        pattern_ids = [gen.generate_pattern_id() for _ in range(1000)]
        assert len(set(pattern_ids)) == 1000

    def test_reset(self):
        """Test ID generator reset clears all pools."""
        gen = IDGenerator()
        gen.generate_track_id()
        gen.generate_pattern_id()

        gen.reset()

        assert len(gen._track_ids) == 0
        assert len(gen._pattern_ids) == 0
