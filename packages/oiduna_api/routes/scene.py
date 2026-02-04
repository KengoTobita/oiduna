"""POST /scene/* - Scene management endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.services.loop_service import LoopService, get_loop_service

router = APIRouter()


class ActivateSceneRequest(BaseModel):
    """Request to activate a scene"""

    scene_id: str = Field(..., description="ID of the scene to activate")


class ActivateSceneResponse(BaseModel):
    """Response after activating a scene"""

    status: str
    scene_id: str
    applied_at: dict | None = None


@router.post("/activate", response_model=ActivateSceneResponse)
async def activate_scene(
    req: ActivateSceneRequest,
    loop_service: LoopService = Depends(get_loop_service),
) -> ActivateSceneResponse:
    """Activate a scene by ID"""
    engine = loop_service.get_engine()
    # BUG FIX: Use "name" instead of "scene"
    result = engine._handle_scene({"name": req.scene_id})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return ActivateSceneResponse(
        status="ok",
        scene_id=req.scene_id,
        applied_at={"step": engine.state.position.step, "beat": engine.state.position.beat},
    )
