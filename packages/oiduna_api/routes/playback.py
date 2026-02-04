"""POST/GET /playback/* - Playback control endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.services.loop_service import LoopService, get_loop_service

router = APIRouter()


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
