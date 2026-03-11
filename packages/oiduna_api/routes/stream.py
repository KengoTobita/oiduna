"""GET /stream - Server-Sent Events endpoint"""

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
    """Async generator that yields SSE-formatted events."""
    # Send initial connected event
    yield _sse_event("connected", {"timestamp": time.time()})

    while True:
        try:
            event = await asyncio.wait_for(sink.queue.get(), timeout=_HEARTBEAT_INTERVAL)
            yield _sse_event(event["type"], event["data"])
        except asyncio.TimeoutError:
            # Keep-alive heartbeat
            yield _sse_event("heartbeat", {"timestamp": time.time()})


def _sse_event(event_type: str, data: object) -> str:
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("/stream")
async def stream_events(
    loop_service: LoopService = Depends(get_loop_service),
) -> StreamingResponse:
    """SSE stream of engine events.

    Event types:
    Engine events:
    - connected           — emitted once on connection
    - position            — step/bar/beat updates
    - status              — playback state changes
    - tracks              — track list updates (legacy)
    - error               — engine errors
    - heartbeat           — keep-alive (every 15 s)

    Session events (Phase 3):
    - client_connected    — new client registered
    - client_disconnected — client removed
    - track_created       — track added to session
    - track_updated       — track base_params changed
    - track_deleted       — track removed
    - pattern_created     — pattern added to track
    - pattern_updated     — pattern active state or events changed
    - pattern_deleted     — pattern removed
    - environment_updated — BPM or metadata changed
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
