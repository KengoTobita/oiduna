"""Pytest fixtures for IPC tests."""

import pytest

try:
    import zmq
    import zmq.asyncio
    ZMQ_AVAILABLE = True
except ImportError:
    # Create minimal mock constants when zmq is not available
    ZMQ_AVAILABLE = False

    class _ZmqMock:
        PUB = 1
        SUB = 2
        POLLIN = 1
        SUBSCRIBE = 6

    zmq = _ZmqMock()  # type: ignore

    class _ZmqAsyncioMock:
        Context = None
        Socket = None

    class _ZmqModuleMock:
        asyncio = _ZmqAsyncioMock()

    zmq.asyncio = _ZmqAsyncioMock()  # type: ignore

from .mocks import MockZmqContext, MockZmqSocket


@pytest.fixture
def mock_zmq_context(monkeypatch):
    """Fixture that patches zmq.asyncio.Context with MockZmqContext.

    Returns a new mock context for each test, and ensures that each call
    to Context() returns a new instance (to support multiple connect/disconnect cycles).
    """
    contexts = []

    def mock_context_factory(*args, **kwargs):
        # Create a new context for each call to Context()
        mock_ctx = MockZmqContext()
        contexts.append(mock_ctx)
        return mock_ctx

    if ZMQ_AVAILABLE:
        monkeypatch.setattr(zmq.asyncio, "Context", mock_context_factory)
    else:
        # When zmq is not available, we need to mock the entire module
        import sys
        from unittest.mock import MagicMock

        zmq_mock = MagicMock()
        zmq_mock.asyncio.Context = mock_context_factory
        zmq_mock.PUB = 1
        zmq_mock.SUB = 2
        zmq_mock.POLLIN = 1
        zmq_mock.SUBSCRIBE = 6
        zmq_mock.ZMQError = Exception

        sys.modules['zmq'] = zmq_mock
        sys.modules['zmq.asyncio'] = zmq_mock.asyncio

    # Return the first context created (for tests that need to inspect it)
    # The fixture creates contexts on-demand, so we'll return a getter
    class ContextGetter:
        def get_sockets(self):
            # Aggregate all sockets from all contexts
            all_sockets = []
            for ctx in contexts:
                all_sockets.extend(ctx.get_sockets())
            return all_sockets

    return ContextGetter()


@pytest.fixture
def mock_zmq_socket():
    """Fixture that provides a MockZmqSocket instance."""
    return MockZmqSocket(1)  # Use 1 (PUB) as socket type
