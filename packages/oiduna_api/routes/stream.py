"""
GET /stream - Server-Sent Events (SSE) endpoint.

This module provides an SSE endpoint for real-time event streaming.
It unifies two types of events into a single SSE stream:

1. StateProducer events (from Loop layer):
   - position, status, error, tracks, heartbeat

2. SessionChange notifications (from Session layer):
   - client_connected, track_created, pattern_updated, etc.

Note on terminology:
- "SSE Event" refers to the HTTP Server-Sent Events protocol format
- This is distinct from "PatternEvent" (musical events) and "SessionChange" (CRUD notifications)
"""

import asyncio
import json
import time

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from oiduna_api.services.loop_service import LoopService, get_loop_service
from oiduna_loop.ipc.in_process import InProcessStateProducer

router = APIRouter()

# Keep-alive heartbeat interval in seconds
_HEARTBEAT_INTERVAL = 15.0


async def _event_stream(sink: InProcessStateProducer):
    """
    Async generator that yields SSE-formatted events.

    Consumes events from InProcessStateProducer queue which contains:
    - StateProducer events (position, status, error from Loop layer)
    - SessionChange notifications (CRUD changes from Session layer)

    All events are formatted as Server-Sent Events (SSE) protocol strings.

    Yields:
        SSE-formatted event strings in the format:
        "event: {event_type}\\ndata: {json_data}\\n\\n"
    """
    # Send initial SSE connection event
    yield _sse_event("connected", {"timestamp": time.time()})

    while True:
        try:
            # Get next event from unified queue (StateProducer + SessionChange)
            event = await asyncio.wait_for(sink.queue.get(), timeout=_HEARTBEAT_INTERVAL)
            yield _sse_event(event["type"], event["data"])
        except asyncio.TimeoutError:
            # Keep-alive heartbeat (SSE protocol requirement)
            yield _sse_event("heartbeat", {"timestamp": time.time()})


def _sse_event(event_type: str, data: object) -> str:
    """
    Format a dict event into SSE (Server-Sent Events) protocol string.

    Args:
        event_type: Event type identifier (e.g., "position", "track_created")
        data: Event data to be JSON-serialized

    Returns:
        SSE-formatted string: "event: {type}\\ndata: {json}\\n\\n"

    Note:
        This converts internal events (StateProducer or SessionChange)
        into the SSE protocol format for HTTP streaming.
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("/stream")
async def stream_events(
    loop_service: LoopService = Depends(get_loop_service),
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) stream endpoint.

    Provides real-time streaming of all system events in SSE protocol format.
    This endpoint unifies two event sources into a single stream:

    1. StateProducer events (Loop layer state updates)
    2. SessionChange notifications (Session layer CRUD changes)

    SSE Event Types:

    StateProducer events (from Loop layer):
    - connected           — SSE connection established
    - position            — step/bar/beat position updates
    - status              — playback state changes (PLAYING/PAUSED/STOPPED)
    - tracks              — track list updates (legacy)
    - error               — engine errors
    - heartbeat           — keep-alive (every 15s)

    SessionChange notifications (from Session layer):
    - client_connected    — new client registered
    - client_disconnected — client removed
    - track_created       — track added to session
    - track_updated       — track base_params changed
    - track_deleted       — track removed
    - pattern_created     — pattern added to track
    - pattern_updated     — pattern active state or events changed
    - pattern_archived    — pattern archived (soft delete)
    - environment_updated — BPM or metadata changed

    Returns:
        StreamingResponse with text/event-stream media type.
        Events are formatted as SSE protocol:
        "event: {type}\\ndata: {json}\\n\\n"

    Note:
        "SSE Event" refers to the HTTP protocol format, distinct from:
        - PatternEvent: Musical timing events in the domain model
        - SessionChange: CRUD change notifications from Session layer
    """
    sink = loop_service.get_state_producer()
    return StreamingResponse(
        _event_stream(sink),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
