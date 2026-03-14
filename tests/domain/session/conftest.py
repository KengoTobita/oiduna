"""Test fixtures for session domain tests."""

from typing import Any
import pytest
from oiduna.domain.models import Session


@pytest.fixture
def session() -> Session:
    """Create a fresh Session instance for testing."""
    return Session()


@pytest.fixture
def mock_event_sink() -> tuple[Any, list[dict[str, Any]]]:
    """
    Create a mock event sink that captures published events.

    Returns:
        Tuple of (sink, events_list)
        - sink: Mock SessionChangePublisher that can be passed to services
        - events_list: List that accumulates all published events
    """
    events: list[dict[str, Any]] = []

    class MockEventSink:
        """Mock implementation of SessionChangePublisher protocol."""

        def publish(self, event: dict[str, Any]) -> None:
            """Capture the event in the events list."""
            events.append(event)

    return MockEventSink(), events
