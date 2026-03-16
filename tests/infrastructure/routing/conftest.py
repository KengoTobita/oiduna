"""Pytest fixtures for routing tests."""

import pytest
from typing import Any


class MockDestinationSender:
    """Mock implementation of DestinationSender protocol."""

    def __init__(self, name: str = "mock"):
        self.name = name
        self._messages: list[dict[str, Any]] = []
        self._bundles: list[list[dict[str, Any]]] = []

    def send_message(self, params: dict[str, Any]) -> None:
        """Record sent message."""
        self._messages.append(params.copy())

    def send_bundle(self, messages: list[dict[str, Any]]) -> None:
        """Record sent bundle."""
        self._bundles.append([msg.copy() for msg in messages])

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all sent messages."""
        return self._messages.copy()

    def get_bundles(self) -> list[list[dict[str, Any]]]:
        """Get all sent bundles."""
        return self._bundles.copy()

    def clear(self) -> None:
        """Clear all recorded messages."""
        self._messages.clear()
        self._bundles.clear()


@pytest.fixture
def mock_sender():
    """Fixture that provides a mock destination sender."""
    return MockDestinationSender()


@pytest.fixture
def mock_sender_factory():
    """Fixture that provides a factory for creating mock senders."""
    class Factory:
        def __init__(self):
            self.senders = []

        def create(self, name: str = "mock") -> MockDestinationSender:
            sender = MockDestinationSender(name)
            self.senders.append(sender)
            return sender

    return Factory()
