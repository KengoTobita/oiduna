"""POST/GET /playback/* - Playback control endpoints"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_pipeline, get_container
from oiduna_api.extensions import ExtensionPipeline, ExtensionError
from oiduna_api.services.loop_service import LoopService, get_loop_service
from oiduna_session import SessionContainer, SessionCompiler

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================================================
# New Destination-Based API Models
# ================================================================

class ScheduleEntryRequest(BaseModel):
    """Individual scheduled message for destination-based API"""

    destination_id: str = Field(..., description="Destination ID (e.g., 'superdirt')")
    cycle: float = Field(..., description="Cycle position")
    step: int = Field(..., ge=0, le=255, description="Step number (0-255)")
    params: dict = Field(default_factory=dict, description="Generic parameters dict")


class SessionRequest(BaseModel):
    """Request body for POST /playback/session (new destination-based API)"""

    messages: list[ScheduleEntryRequest] = Field(
        default_factory=list,
        description="Scheduled messages for all destinations"
    )
    bpm: float = Field(default=120.0, gt=0, description="Beats per minute")
    pattern_length: float = Field(default=4.0, gt=0, description="Pattern length in cycles")


class BpmRequest(BaseModel):
    """Request to change BPM"""

    bpm: float = Field(gt=0, description="Beats per minute (must be positive)")


class StatusResponse(BaseModel):
    """Playback status response"""

    playing: bool
    playback_state: str
    bpm: float
    position: dict
    active_tracks: list[str]
    known_tracks: list[str]
    muted_tracks: list[str]
    soloed_tracks: list[str]


@router.post("/start")
async def start_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Start playback"""
    engine = loop_service.get_engine()
    result = engine.handle_play({})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.post("/stop")
async def stop_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Stop playback and reset position"""
    engine = loop_service.get_engine()
    result = engine.handle_stop({})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.post("/pause")
async def pause_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Pause playback"""
    engine = loop_service.get_engine()
    result = engine.handle_pause({})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.get("/status")
async def get_status(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Get current playback status"""
    return loop_service.get_engine().state.to_status_dict()


@router.post("/session")
async def load_session(
    req: SessionRequest,
    loop_service: LoopService = Depends(get_loop_service),
    pipeline: ExtensionPipeline = Depends(get_pipeline),
) -> dict:
    """Load a session using the new destination-based API.

    This is the new endpoint that accepts LoopSchedule format.
    Messages are generic and route to configured destinations.

    The request body contains:
    - messages: List of scheduled messages with destination_id, cycle, step, params
    - bpm: Tempo in beats per minute
    - pattern_length: Pattern length in cycles

    Extensions are applied to transform the payload before loading into the engine.

    Does not auto-play — call /playback/start to begin.
    """
    engine = loop_service.get_engine()

    # Convert Pydantic models to dict format for engine
    payload = {
        "messages": [
            {
                "destination_id": msg.destination_id,
                "cycle": msg.cycle,
                "step": msg.step,
                "params": msg.params,
            }
            for msg in req.messages
        ],
        "bpm": req.bpm,
        "pattern_length": req.pattern_length,
    }

    # Apply extension transformations
    try:
        payload = pipeline.apply(payload)
        logger.debug(f"Extension pipeline applied: {len(pipeline.extensions)} extensions")
    except ExtensionError as e:
        logger.error(f"Extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    result = engine._handle_session(payload)

    if not result.success:
        # Return 503 Service Unavailable if destinations not configured
        if "not loaded" in result.message or "not loaded" in result.message:
            raise HTTPException(status_code=503, detail=result.message)
        else:
            raise HTTPException(status_code=500, detail=result.message)

    return {
        "status": "ok",
        "message_count": len(req.messages),
        "bpm": req.bpm,
        "pattern_length": req.pattern_length,
    }


@router.post("/bpm")
async def set_bpm(
    req: BpmRequest,
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Change BPM (goes through engine for correct drift-anchor reset)"""
    engine = loop_service.get_engine()
    result = engine._handle_bpm({"bpm": req.bpm})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok", "bpm": req.bpm}


@router.post("/sync")
async def sync_session_to_engine(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
    loop_service: LoopService = Depends(get_loop_service),
    pipeline: ExtensionPipeline = Depends(get_pipeline),
    x_session_version: Annotated[Optional[int], Header()] = None,
) -> dict:
    """
    Sync session state to loop engine with optimistic locking.

    Compiles the current Session (tracks/patterns) into LoopSchedule
    and loads it into the loop engine.

    This endpoint ensures atomic updates using version-based optimistic locking:
    - Client sends the version number they started editing from
    - If the session has been modified by another client (version mismatch),
      returns 409 Conflict
    - On success, increments the version and updates metadata

    This endpoint should be called after:
    - Creating/updating tracks
    - Creating/updating patterns
    - Changing pattern active state

    Requires authentication.

    Example:
        POST /playback/sync
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
            X-Session-Version: 5

        Success Response (200):
        {
            "status": "synced",
            "version": 6,
            "message_count": 42,
            "bpm": 120.0
        }

        Conflict Response (409):
        {
            "detail": {
                "error": "session_conflict",
                "message": "Session was modified by bob_002",
                "current_version": 6,
                "your_version": 5,
                "last_modified_at": "2026-03-02T10:30:00Z"
            }
        }
    """
    # Verify authentication
    client = container.clients.get(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Version check (optimistic locking)
    if x_session_version is None:
        raise HTTPException(
            status_code=400,
            detail="X-Session-Version header is required"
        )
    client_version = x_session_version
    current_version = container.session.version
    if current_version != client_version:
        conflict_detail = {
            "error": "session_conflict",
            "message": f"Session was modified by {container.session.last_modified_by or 'another client'}",
            "current_version": current_version,
            "your_version": client_version,
            "last_modified_at": container.session.last_modified_at.isoformat() if container.session.last_modified_at else None,
        }
        logger.warning(
            f"Version conflict: client={x_client_id}, expected={client_version}, "
            f"current={current_version}, last_modified_by={container.session.last_modified_by}"
        )
        raise HTTPException(status_code=409, detail=conflict_detail)

    # Compile session to batch
    batch = SessionCompiler.compile(container.session)

    # Convert to payload format
    payload = {
        "messages": [msg.to_dict() for msg in batch.messages],
        "bpm": batch.bpm,
        "pattern_length": batch.pattern_length,
    }

    # Apply extension transformations
    try:
        payload = pipeline.apply(payload)
        logger.debug(f"Extension pipeline applied: {len(pipeline.extensions)} extensions")
    except ExtensionError as e:
        logger.error(f"Extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Load into engine
    engine = loop_service.get_engine()
    result = engine._handle_session(payload)

    if not result.success:
        if "not loaded" in result.message:
            raise HTTPException(status_code=503, detail=result.message)
        else:
            raise HTTPException(status_code=500, detail=result.message)

    # Update version metadata (successful sync)
    container.session.version += 1
    container.session.last_modified_by = x_client_id
    container.session.last_modified_at = datetime.now(timezone.utc)

    logger.info(
        f"Session synced: client={x_client_id}, version={container.session.version}, "
        f"messages={len(batch.messages)}"
    )

    return {
        "status": "synced",
        "version": container.session.version,
        "message_count": len(batch.messages),
        "bpm": batch.bpm,
    }
