"""
Unit tests for Oiduna data models.
"""

import pytest
from pydantic import ValidationError
from oiduna_models import (
    Session,
    Track,
    Pattern,
    Event,
    ClientInfo,
    Environment,
    IDGenerator,
)
from oiduna_models import OscDestinationConfig


class TestEvent:
    """Test Event model."""

    def test_create_event(self):
        """Test creating a valid event."""
        event = Event(
            step=0,
            cycle=0.0,
            params={"gain": 0.8}
        )
        assert event.step == 0
        assert event.cycle == 0.0
        assert event.params == {"gain": 0.8}

    def test_event_step_validation(self):
        """Test step must be 0-255."""
        with pytest.raises(ValidationError, match="step"):
            Event(step=-1, cycle=0.0, params={})

        with pytest.raises(ValidationError, match="step"):
            Event(step=256, cycle=0.0, params={})

    def test_event_cycle_validation(self):
        """Test cycle must be >= 0."""
        with pytest.raises(ValidationError, match="cycle"):
            Event(step=0, cycle=-1.0, params={})


class TestPattern:
    """Test Pattern model."""

    def test_create_pattern(self):
        """Test creating a valid pattern."""
        pattern = Pattern(
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001",
            active=True,
            events=[
                Event(step=0, cycle=0.0, params={}),
                Event(step=64, cycle=1.0, params={"gain": 0.9}),
            ]
        )
        assert pattern.pattern_id == "pattern_001"
        assert pattern.pattern_name == "main"
        assert pattern.client_id == "client_001"
        assert pattern.active is True
        assert len(pattern.events) == 2

    def test_pattern_default_values(self):
        """Test pattern defaults."""
        pattern = Pattern(
            pattern_id="pattern_001",
            pattern_name="main",
            client_id="client_001"
        )
        assert pattern.active is True
        assert pattern.events == []


class TestTrack:
    """Test Track model."""

    def test_create_track(self):
        """Test creating a valid track."""
        track = Track(
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd", "orbit": 0},
        )
        assert track.track_id == "track_001"
        assert track.track_name == "kick"
        assert track.destination_id == "superdirt"
        assert track.client_id == "client_001"
        assert track.base_params == {"sound": "bd", "orbit": 0}

    def test_track_default_values(self):
        """Test track defaults."""
        track = Track(
            track_id="track_001",
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
            track_id="t1",
            track_name="test",
            destination_id=destination_id,
            client_id="c1"
        )
        assert track.destination_id == destination_id

    def test_invalid_destination_id_with_space(self):
        """Test destination_id with space raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Track(
                track_id="t1",
                track_name="kick",
                destination_id="super dirt",
                client_id="c1"
            )

    def test_invalid_destination_id_with_special_char(self):
        """Test destination_id with special character raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Track(
                track_id="t1",
                track_name="kick",
                destination_id="dest!",
                client_id="c1"
            )

    def test_invalid_destination_id_error_message(self):
        """Test error message includes helpful examples."""
        with pytest.raises(ValueError, match="superdirt.*midi_1.*osc-synth"):
            Track(
                track_id="t1",
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
            track_id="track_001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
        )

        session = Session(
            destinations={"superdirt": dest},
            clients={"client_001": client},
            tracks={"track_001": track},
        )

        assert len(session.destinations) == 1
        assert len(session.clients) == 1
        assert len(session.tracks) == 1


class TestIDGenerator:
    """Test IDGenerator."""

    def test_track_id_generation(self):
        """Test track ID generation."""
        gen = IDGenerator()
        assert gen.next_track_id() == "track_001"
        assert gen.next_track_id() == "track_002"
        assert gen.next_track_id() == "track_003"

    def test_pattern_id_generation(self):
        """Test pattern ID generation."""
        gen = IDGenerator()
        assert gen.next_pattern_id() == "pattern_001"
        assert gen.next_pattern_id() == "pattern_002"

    def test_reset(self):
        """Test ID generator reset."""
        gen = IDGenerator()
        gen.next_track_id()
        gen.next_pattern_id()
        gen.reset()
        assert gen.next_track_id() == "track_001"
        assert gen.next_pattern_id() == "pattern_001"
