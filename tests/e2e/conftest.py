"""Pytest configuration for E2E tests."""

import os
import sys
from pathlib import Path

import pytest

# Add tests directory to path for imports
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

# Import mocks from existing test infrastructure
from infrastructure.ipc.mocks import MockZmqContext, MockZmqSocket
from infrastructure.transport.mocks import MockOscClient, MockMidiPort
from infrastructure.execution.mocks import (
    MockCommandConsumer,
    MockMidiOutput,
    MockOscOutput,
    MockStateProducer,
)

# Import E2E helpers
from e2e.helpers import E2EEngineManager

# Check if E2E tests are enabled via environment variable
E2E_TESTS_ENABLED = os.environ.get("RUN_E2E_TESTS", "0") == "1"
LONG_E2E_TESTS_ENABLED = os.environ.get("RUN_LONG_E2E_TESTS", "0") == "1"


# Configure E2E test markers
def pytest_configure(config):
    """Register E2E markers."""
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as E2E tests (run with RUN_E2E_TESTS=1)",
    )
    config.addinivalue_line(
        "markers",
        "stress: marks tests as stress tests (subset of e2e)",
    )
    config.addinivalue_line(
        "markers",
        "resilience: marks tests as resilience tests (subset of e2e)",
    )
    config.addinivalue_line(
        "markers",
        "long: marks tests as long-running E2E tests (run with RUN_LONG_E2E_TESTS=1)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip E2E tests unless explicitly enabled."""
    if not E2E_TESTS_ENABLED:
        skip_e2e = pytest.mark.skip(
            reason="E2E tests disabled. Set RUN_E2E_TESTS=1 to enable."
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)
        return

    # If E2E tests are enabled, check for long tests
    if not LONG_E2E_TESTS_ENABLED:
        skip_long = pytest.mark.skip(
            reason="Long E2E tests disabled. Set RUN_LONG_E2E_TESTS=1 to enable."
        )
        for item in items:
            if "long" in item.keywords:
                item.add_marker(skip_long)


# Fixtures for E2E tests
@pytest.fixture
def mock_osc() -> MockOscOutput:
    """Create mock OSC output."""
    return MockOscOutput()


@pytest.fixture
def mock_midi() -> MockMidiOutput:
    """Create mock MIDI output."""
    return MockMidiOutput()


@pytest.fixture
def mock_commands() -> MockCommandConsumer:
    """Create mock command consumer."""
    return MockCommandConsumer()


@pytest.fixture
def mock_publisher() -> MockStateProducer:
    """Create mock state publisher."""
    return MockStateProducer()


@pytest.fixture
def e2e_engine(
    mock_osc: MockOscOutput,
    mock_midi: MockMidiOutput,
    mock_commands: MockCommandConsumer,
    mock_publisher: MockStateProducer,
):
    """Create LoopEngine instance for E2E tests.

    Returns:
        LoopEngine configured with mocks
    """
    from oiduna.infrastructure.execution import LoopEngine

    engine = LoopEngine(
        osc=mock_osc,
        midi=mock_midi,
        command_consumer=mock_commands,
        state_producer=mock_publisher,
    )
    engine._register_handlers()
    return engine


@pytest.fixture
def e2e_engine_manager(
    e2e_engine,
    mock_commands: MockCommandConsumer,
):
    """Create E2EEngineManager for background execution tests.

    Returns:
        E2EEngineManager instance
    """
    return E2EEngineManager(
        engine=e2e_engine,
        command_injector=mock_commands,
    )
