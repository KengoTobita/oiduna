"""Pytest configuration for load tests."""

import os
import sys
from pathlib import Path
import pytest

# Add tests directory to path for imports
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

# Import mocks from IPC and transport tests
from infrastructure.ipc.mocks import MockZmqContext, MockZmqSocket
from infrastructure.transport.mocks import MockOscClient, MockMidiPort

# Check if load tests are enabled via environment variable
LOAD_TESTS_ENABLED = os.environ.get("RUN_LOAD_TESTS", "0") == "1"


# Configure load test marker to skip by default
def pytest_configure(config):
    """Register the load marker."""
    config.addinivalue_line(
        "markers", "load: marks tests as load tests (run separately with RUN_LOAD_TESTS=1)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip load tests unless RUN_LOAD_TESTS=1."""
    if LOAD_TESTS_ENABLED:
        return  # Don't skip anything if load tests are enabled

    skip_load = pytest.mark.skip(reason="Load tests disabled. Set RUN_LOAD_TESTS=1 to enable.")
    for item in items:
        if "load" in item.keywords:
            item.add_marker(skip_load)


# Fixtures for IPC tests
@pytest.fixture
def mock_zmq_context(monkeypatch):
    """Fixture that patches zmq.asyncio.Context with MockZmqContext."""
    try:
        import zmq
        import zmq.asyncio
        ZMQ_AVAILABLE = True
    except ImportError:
        ZMQ_AVAILABLE = False
        from unittest.mock import MagicMock
        zmq = MagicMock()

    contexts = []

    def mock_context_factory(*args, **kwargs):
        mock_ctx = MockZmqContext()
        contexts.append(mock_ctx)
        return mock_ctx

    if ZMQ_AVAILABLE:
        monkeypatch.setattr(zmq.asyncio, "Context", mock_context_factory)
    else:
        sys.modules['zmq'] = zmq
        sys.modules['zmq.asyncio'] = zmq.asyncio
        zmq.asyncio.Context = mock_context_factory
        zmq.PUB = 1
        zmq.SUB = 2
        zmq.POLLIN = 1
        zmq.SUBSCRIBE = 6
        zmq.ZMQError = Exception

    class ContextGetter:
        def get_sockets(self):
            all_sockets = []
            for ctx in contexts:
                all_sockets.extend(ctx.get_sockets())
            return all_sockets

    return ContextGetter()


# Fixtures for transport tests
@pytest.fixture
def mock_osc_client(monkeypatch):
    """Fixture that patches python-osc Client with MockOscClient."""
    clients = []

    def mock_client_factory(host: str, port: int):
        client = MockOscClient(host, port)
        clients.append(client)
        return client

    try:
        from pythonosc import udp_client
        monkeypatch.setattr(udp_client, "SimpleUDPClient", mock_client_factory)
    except ImportError:
        # Mock the entire module if not available
        from unittest.mock import MagicMock
        mock_module = MagicMock()
        mock_module.SimpleUDPClient = mock_client_factory
        sys.modules['pythonosc'] = MagicMock()
        sys.modules['pythonosc.udp_client'] = mock_module

    class ClientGetter:
        def get_client(self):
            return clients[0] if clients else None

        def get_all_clients(self):
            return clients

    return ClientGetter()


@pytest.fixture
def mock_mido(monkeypatch):
    """Fixture that patches mido with MockMidiPort."""
    ports = []

    def mock_open_output(name=None, **kwargs):
        port = MockMidiPort(name or "MockPort")
        ports.append(port)
        return port

    def mock_get_output_names():
        return ["Port1", "Port2", "Port3"]

    try:
        import mido
        monkeypatch.setattr(mido, "open_output", mock_open_output)
        monkeypatch.setattr(mido, "get_output_names", mock_get_output_names)
        monkeypatch.setattr(mido, "Message", MockMidiPort.MockMessage)
    except ImportError:
        # Mock the entire module if not available
        from unittest.mock import MagicMock
        mock_module = MagicMock()
        mock_module.open_output = mock_open_output
        mock_module.get_output_names = mock_get_output_names
        mock_module.Message = MockMidiPort.MockMessage
        sys.modules['mido'] = mock_module

    class PortGetter:
        def get_port(self):
            return ports[0] if ports else None

        def get_all_ports(self):
            return ports

    return PortGetter()
