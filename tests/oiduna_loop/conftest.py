"""
Pytest fixtures for oiduna_loop tests (v5).

Provides mock dependencies and test engine configurations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add packages to sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir / "packages"))

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.tests.mocks import MockCommandConsumer, MockMidiOutput, MockOscOutput, MockStateProducer


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
    # Register handlers as start() would do
    engine._register_handlers()
    return engine
