"""Tests for /stream endpoint (Server-Sent Events)

Tests verify Phase 1 refactoring:
- SSE streaming functionality
- Event formatting
- Connection and heartbeat events

Note: Full stream tests are omitted because SSE streams are infinite and would hang.
We test the helper functions instead.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock


@pytest.mark.asyncio
async def test_sse_event_formatting():
    """Test SSE event formatting function"""
    from oiduna_api.routes.stream import _sse_event

    result = _sse_event("test_event", {"key": "value"})
    assert result == 'event: test_event\ndata: {"key": "value"}\n\n'


@pytest.mark.asyncio
async def test_sse_event_formatting_complex_data():
    """Test SSE event formatting with complex data"""
    from oiduna_api.routes.stream import _sse_event

    data = {"position": {"step": 0, "beat": 1, "bar": 2}, "bpm": 120}
    result = _sse_event("position", data)
    assert result.startswith("event: position\n")
    assert "data:" in result
    assert result.endswith("\n\n")
    assert "step" in result


@pytest.mark.asyncio
async def test_event_stream_connected_event(mock_loop_service):
    """Test that event stream sends initial connected event"""
    from oiduna_api.routes.stream import _event_stream

    # Create a mock queue that immediately raises TimeoutError (heartbeat)
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=asyncio.TimeoutError)

    sink = Mock()
    sink.queue = queue

    # Get just the first event (connected)
    gen = _event_stream(sink)
    first_event = await gen.__anext__()

    assert "event: connected" in first_event
    assert "data:" in first_event
    assert "timestamp" in first_event


@pytest.mark.asyncio
async def test_event_stream_with_queue_event(mock_loop_service):
    """Test that event stream processes queue events"""
    from oiduna_api.routes.stream import _event_stream

    # Create a mock queue with an event
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=[
        {"type": "position", "data": {"step": 0, "beat": 0}},
        asyncio.TimeoutError(),  # Trigger heartbeat on second call
    ])

    sink = Mock()
    sink.queue = queue

    # Collect events from the stream
    events = []
    async for event in _event_stream(sink):
        events.append(event)
        # Stop after connected + position + heartbeat
        if len(events) >= 3:
            break

    # Verify we got: connected, position, heartbeat
    assert len(events) == 3
    assert "event: connected" in events[0]
    assert "event: position" in events[1]
    assert "event: heartbeat" in events[2]
