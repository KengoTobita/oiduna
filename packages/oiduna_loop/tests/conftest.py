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
    Create sample session data for testing (new ScheduledMessageBatch format).

    Provides a minimal session with kick and hihat tracks for testing.
    """
    return {
        "messages": [
            # Kick on steps 0, 4, 8, 12
            {
                "destination_id": "superdirt",
                "cycle": 0.0,
                "step": 0,
                "params": {"track_id": "kick", "s": "bd", "gain": 1.0},
            },
            {
                "destination_id": "superdirt",
                "cycle": 1.0,
                "step": 64,
                "params": {"track_id": "kick", "s": "bd", "gain": 1.0},
            },
            # Hihat on steps 2, 6, 10, 14
            {
                "destination_id": "superdirt",
                "cycle": 0.5,
                "step": 32,
                "params": {"track_id": "hihat", "s": "hh", "gain": 0.8},
            },
            {
                "destination_id": "superdirt",
                "cycle": 1.5,
                "step": 96,
                "params": {"track_id": "hihat", "s": "hh", "gain": 0.8},
            },
        ],
        "bpm": 120.0,
        "pattern_length": 4.0,
    }
