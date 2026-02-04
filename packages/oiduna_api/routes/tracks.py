"""GET/POST /tracks/* - Track management endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.services.loop_service import LoopService, get_loop_service

router = APIRouter()


class TrackInfo(BaseModel):
    """Track information"""

    id: str
    sound: str | None = None
    orbit: int
    gain: float
    pan: float
    muted: bool
    solo: bool
    length: int


class TracksResponse(BaseModel):
    """Response listing all tracks"""

    tracks: list[TrackInfo]


class MuteRequest(BaseModel):
    """Request to mute/unmute a track"""

    muted: bool = Field(..., description="True to mute, False to unmute")


class MuteResponse(BaseModel):
    """Response after muting/unmuting"""

    status: str
    track_id: str
    muted: bool


class SoloRequest(BaseModel):
    """Request to solo/unsolo a track"""

    solo: bool = Field(..., description="True to solo, False to unsolo")


class SoloResponse(BaseModel):
    """Response after soloing/unsoloing"""

    status: str
    track_id: str
    solo: bool


def _build_track_info(track_id: str, track: Any, seq: Any) -> TrackInfo:
    """
    Helper function to build TrackInfo from track and sequence data.

    Args:
        track_id: Track identifier
        track: Track object with params and meta
        seq: Sequence object with events

    Returns:
        TrackInfo object
    """
    return TrackInfo(
        id=track_id,
        sound=track.params.s,
        orbit=track.params.orbit,
        gain=track.params.gain,
        pan=track.params.pan,
        muted=track.meta.mute,
        solo=track.meta.solo,
        length=len(seq.events) if seq else 0,
    )


@router.get("", response_model=TracksResponse)
async def list_tracks(
    loop_service: LoopService = Depends(get_loop_service),
) -> TracksResponse:
    """List all tracks in the current session"""
    engine = loop_service.get_engine()
    state = engine.state
    eff = state.get_effective()

    tracks: list[TrackInfo] = []
    for track_id, track in eff.tracks.items():
        seq = eff.sequences.get(track_id)
        tracks.append(_build_track_info(track_id, track, seq))

    return TracksResponse(tracks=tracks)


@router.get("/{track_id}", response_model=TrackInfo)
async def get_track(
    track_id: str,
    loop_service: LoopService = Depends(get_loop_service),
) -> TrackInfo:
    """Get detailed information for a specific track"""
    engine = loop_service.get_engine()
    state = engine.state
    eff = state.get_effective()

    if track_id not in eff.tracks:
        raise HTTPException(status_code=404, detail=f"Track '{track_id}' not found")

    track = eff.tracks[track_id]
    seq = eff.sequences.get(track_id)

    return _build_track_info(track_id, track, seq)


@router.post("/{track_id}/mute", response_model=MuteResponse)
async def set_mute(
    track_id: str,
    req: MuteRequest,
    loop_service: LoopService = Depends(get_loop_service),
) -> MuteResponse:
    """Mute or unmute a track"""
    engine = loop_service.get_engine()
    result = engine._handle_mute({"track_id": track_id, "mute": req.muted})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return MuteResponse(status="ok", track_id=track_id, muted=req.muted)


@router.post("/{track_id}/solo", response_model=SoloResponse)
async def set_solo(
    track_id: str,
    req: SoloRequest,
    loop_service: LoopService = Depends(get_loop_service),
) -> SoloResponse:
    """Solo or unsolo a track"""
    engine = loop_service.get_engine()
    result = engine._handle_solo({"track_id": track_id, "solo": req.solo})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return SoloResponse(status="ok", track_id=track_id, solo=req.solo)
