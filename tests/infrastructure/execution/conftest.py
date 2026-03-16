"""
Pytest fixtures for oiduna_loop tests (v5).

Provides mock dependencies and test engine configurations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add packages to sys.path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "packages"))

import pytest

from oiduna.infrastructure.execution import LoopEngine
from .mocks import MockCommandConsumer, MockMidiOutput, MockOscOutput, MockStateProducer


class MockDriftCorrector:
    """Mock DriftCorrector for testing."""

    def __init__(self):
        self.suppress_next_reset_called = False

    def suppress_next_reset(self):
        """Suppress next drift reset."""
        self.suppress_next_reset_called = True

    def reset(self):
        """Reset drift corrector."""
        pass

    def get_stats(self):
        """Get drift statistics."""
        return {
            "reset_count": 0,
            "max_drift_ms": 0.0,
            "current_count": 0,
            "total_skipped_steps": 0,
            "last_reset_drift_ms": 0.0,
            "anchor_age_seconds": 0.0,
        }


class MockClockGenerator:
    """Mock ClockGenerator for testing."""

    def __init__(self, midi=None):
        self.suppress_next_drift_reset_called = False
        self._midi = midi

    def suppress_next_drift_reset(self):
        """Suppress next drift reset."""
        self.suppress_next_drift_reset_called = True

    def send_stop(self):
        """Send MIDI stop message."""
        if self._midi:
            self._midi.send_stop()

    def send_start(self):
        """Send MIDI start message."""
        if self._midi:
            self._midi.send_start()

    def send_continue(self):
        """Send MIDI continue message."""
        if self._midi:
            self._midi.send_continue()


@pytest.fixture
def mock_drift_corrector():
    """Create a mock drift corrector."""
    return MockDriftCorrector()


@pytest.fixture
def mock_clock(mock_midi):
    """Create a mock clock generator."""
    return MockClockGenerator(midi=mock_midi)


@pytest.fixture
def mock_midi() -> MockMidiOutput:
    """Create a fresh MockMidiOutput for testing."""
    return MockMidiOutput()


@pytest.fixture
def mock_osc() -> MockOscOutput:
    """Create a fresh MockOscOutput for testing."""
    return MockOscOutput()


@pytest.fixture
def mock_commands() -> MockCommandConsumer:
    """Create a fresh MockCommandConsumer for testing."""
    return MockCommandConsumer()


@pytest.fixture
def mock_publisher() -> MockStateProducer:
    """Create a fresh MockStateProducer for testing."""
    return MockStateProducer()


@pytest.fixture
def test_engine(
    mock_osc: MockOscOutput,
    mock_midi: MockMidiOutput,
    mock_commands: MockCommandConsumer,
    mock_publisher: MockStateProducer,
    mock_drift_corrector: MockDriftCorrector,
    mock_clock: MockClockGenerator,
) -> LoopEngine:
    """
    Create a LoopEngine with all mock dependencies.

    This engine can be tested without any real I/O.
    """
    engine = LoopEngine(
        osc=mock_osc,
        midi=mock_midi,
        command_consumer=mock_commands,
        state_producer=mock_publisher,
    )
    # Inject mock drift corrector and clock generator
    engine._drift_corrector = mock_drift_corrector
    engine._clock_generator = mock_clock
    # Register handlers as start() would do
    engine._register_handlers()
    return engine


@pytest.fixture
def sample_session_data() -> dict[str, Any]:
    """
    Create sample session data for testing (new LoopSchedule format).

    Provides a minimal session with kick and hihat tracks for testing.
    """
    return {
        "messages": [
            # Kick on steps 0, 4, 8, 12
            {
                "destination_id": "superdirt",
                "offset": 0.0,
                "step": 0,
                "params": {"track_id": "kick", "s": "bd", "gain": 1.0},
            },
            {
                "destination_id": "superdirt",
                "offset": 0.0,
                "step": 64,
                "params": {"track_id": "kick", "s": "bd", "gain": 1.0},
            },
            # Hihat on steps 2, 6, 10, 14
            {
                "destination_id": "superdirt",
                "offset": 0.5,
                "step": 32,
                "params": {"track_id": "hihat", "s": "hh", "gain": 0.8},
            },
            {
                "destination_id": "superdirt",
                "offset": 0.5,
                "step": 96,
                "params": {"track_id": "hihat", "s": "hh", "gain": 0.8},
            },
        ],
        "bpm": 120.0,
        "pattern_length": 4.0,
    }
