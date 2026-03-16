"""Pytest fixtures for transport tests."""

import pytest

from .mocks import MockOscClient, MockMidiModule


@pytest.fixture
def mock_osc_client(monkeypatch):
    """Fixture that patches pythonosc.udp_client.SimpleUDPClient with MockOscClient."""
    mock_clients = []

    def mock_client_factory(host: str, port: int):
        client = MockOscClient(host, port)
        mock_clients.append(client)
        return client

    from pythonosc import udp_client
    monkeypatch.setattr(udp_client, "SimpleUDPClient", mock_client_factory)

    # Return a getter to access all created clients
    class ClientGetter:
        def get_client(self, index: int = 0):
            return mock_clients[index] if index < len(mock_clients) else None

        def get_all_clients(self):
            return mock_clients

    return ClientGetter()


@pytest.fixture
def mock_mido(monkeypatch):
    """Fixture that patches mido module with MockMidiModule."""
    mock_module = MockMidiModule()

    # Patch mido functions
    import mido
    monkeypatch.setattr(mido, "get_output_names", mock_module.get_output_names)
    monkeypatch.setattr(mido, "open_output", mock_module.open_output)

    return mock_module
