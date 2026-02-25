"""POST/GET /playback/* - Playback control endpoints"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_pipeline
from oiduna_api.extensions import ExtensionPipeline, ExtensionError
from oiduna_api.services.loop_service import LoopService, get_loop_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================================================
# New Destination-Based API Models
# ================================================================

class ScheduledMessageRequest(BaseModel):
    """Individual scheduled message for destination-based API"""

    destination_id: str = Field(..., description="Destination ID (e.g., 'superdirt')")
    cycle: float = Field(..., description="Cycle position")
    step: int = Field(..., ge=0, le=255, description="Step number (0-255)")
    params: dict = Field(default_factory=dict, description="Generic parameters dict")


class SessionRequest(BaseModel):
    """Request body for POST /playback/session (new destination-based API)"""

    messages: list[ScheduledMessageRequest] = Field(
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
    has_pending: bool
    scenes: list[str]
    current_scene: str | None


@router.post("/pattern")
async def load_pattern(
    body: dict,
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Load a compiled session pattern.

    The request body is a CompiledSession dict.
    Does not auto-play — call /playback/start to begin.
    """
    engine = loop_service.get_engine()
    result = engine._handle_compile(body)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.post("/start")
async def start_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Start playback"""
    engine = loop_service.get_engine()
    result = engine._handle_play({})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.post("/stop")
async def stop_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Stop playback and reset position"""
    engine = loop_service.get_engine()
    result = engine._handle_stop({})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}


@router.post("/pause")
async def pause_playback(
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """Pause playback"""
    engine = loop_service.get_engine()
    result = engine._handle_pause({})

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

    This is the new endpoint that accepts ScheduledMessageBatch format.
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
