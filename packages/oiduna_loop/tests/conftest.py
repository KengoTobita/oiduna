"""
Pytest fixtures for oiduna_loop tests (v5).

Provides mock dependencies and test engine configurations.
"""

from __future__ import annotations

from typing import Any

import pytest
from oiduna_core.models.environment import Environment
from oiduna_core.models.sequence import Event, EventSequence
from oiduna_core.models.session import CompiledSession
from oiduna_core.models.track import FxParams, Track, TrackMeta, TrackParams

from ..engine import LoopEngine
from .mocks import MockCommandSource, MockMidiOutput, MockOscOutput, MockStateSink


@pytest.fixture
def mock_midi() -> MockMidiOutput:
    """Create a fresh MockMidiOutput for testing."""
    return MockMidiOutput()


@pytest.fixture
def mock_osc() -> MockOscOutput:
    """Create a fresh MockOscOutput for testing."""
    return MockOscOutput()


@pytest.fixture
def mock_commands() -> MockCommandSource:
    """Create a fresh MockCommandSource for testing."""
    return MockCommandSource()


@pytest.fixture
def mock_publisher() -> MockStateSink:
    """Create a fresh MockStateSink for testing."""
    return MockStateSink()


@pytest.fixture
def test_engine(
    mock_osc: MockOscOutput,
    mock_midi: MockMidiOutput,
    mock_commands: MockCommandSource,
    mock_publisher: MockStateSink,
) -> LoopEngine:
    """
    Create a LoopEngine with all mock dependencies.

    This engine can be tested without any real I/O.
    """
    engine = LoopEngine(
        osc=mock_osc,
        midi=mock_midi,
        commands=mock_commands,
        publisher=mock_publisher,
    )
    # Register handlers as start() would do
    engine._register_handlers()
    return engine


@pytest.fixture
def sample_session_data() -> dict[str, Any]:
    """
    Sample compiled session data for testing (v5 format).

    Represents a minimal but complete session with two tracks.
    """
    return {
        "environment": {"bpm": 120.0},
        "tracks": {
            "kick": {
                "meta": {"track_id": "kick", "mute": False, "solo": False},
                "params": {"s": "bd"},
                "fx": {},
            },
            "hihat": {
                "meta": {"track_id": "hihat", "mute": False, "solo": False},
                "params": {"s": "hh"},
                "fx": {"room": 0.3},
            },
        },
        "sequences": {
            "kick": {
                "track_id": "kick",
                "events": [
                    {"step": 0, "velocity": 1.0},
                    {"step": 4, "velocity": 0.8},
                    {"step": 8, "velocity": 1.0},
                    {"step": 12, "velocity": 0.8},
                ],
            },
            "hihat": {
                "track_id": "hihat",
                "events": [
                    {"step": 2, "velocity": 0.5},
                    {"step": 6, "velocity": 0.5},
                    {"step": 10, "velocity": 0.5},
                    {"step": 14, "velocity": 0.5},
                ],
            },
        },
    }


@pytest.fixture
def sample_track() -> Track:
    """Create a sample Track for testing (v5)."""
    return Track(
        meta=TrackMeta(track_id="kick", mute=False, solo=False),
        params=TrackParams(s="bd"),
        fx=FxParams(),
    )


@pytest.fixture
def sample_session() -> CompiledSession:
    """Create a sample CompiledSession for testing (v5)."""
    kick_track = Track(
        meta=TrackMeta(track_id="kick", mute=False, solo=False),
        params=TrackParams(s="bd"),
        fx=FxParams(),
    )
    hihat_track = Track(
        meta=TrackMeta(track_id="hihat", mute=False, solo=False),
        params=TrackParams(s="hh"),
        fx=FxParams(room=0.3),
    )

    kick_events = [
        Event(step=0, velocity=1.0),
        Event(step=4, velocity=0.8),
        Event(step=8, velocity=1.0),
        Event(step=12, velocity=0.8),
    ]
    hihat_events = [
        Event(step=2, velocity=0.5),
        Event(step=6, velocity=0.5),
        Event(step=10, velocity=0.5),
        Event(step=14, velocity=0.5),
    ]

    return CompiledSession(
        environment=Environment(bpm=120.0),
        tracks={"kick": kick_track, "hihat": hihat_track},
        sequences={
            "kick": EventSequence.from_events("kick", kick_events),
            "hihat": EventSequence.from_events("hihat", hihat_events),
        },
    )
